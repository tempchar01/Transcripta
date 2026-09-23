param(
    [switch]$Installer,
    [string]$Python = 'python',
    [string]$ISCC = 'ISCC.exe'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$specPath = Join-Path $projectRoot 'packaging\transcripta.spec'

Push-Location $projectRoot
try {
    # Resolve before the isolated PyInstaller PATH removes the Python directory.
    $Python = (Get-Command $Python -ErrorAction Stop).Source
    $env:PYTHONPATH = $projectRoot
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $projectRoot 'build\pyinstaller-cache'
    $env:LOCALAPPDATA = Join-Path $projectRoot 'build\test-user'
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
    & $Python scripts/generate_app_icon.py --source assets/branding/transcripta-icon.png --output assets/branding/generated/app_icon.ico
    if ($LASTEXITCODE -ne 0) { throw 'Application icon generation failed' }
    # Remove only the exact generated one-folder target, never source or user data.
    $target = [IO.Path]::GetFullPath((Join-Path $projectRoot 'dist\Transcripta'))
    if ($target -ne [IO.Path]::Combine($projectRoot, 'dist', 'Transcripta')) { throw 'Invalid build target' }
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
    New-Item -ItemType Directory -Path (Join-Path $projectRoot 'build') -Force | Out-Null
    & $Python -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed' }
    & $Python scripts/release_audit.py --output build/source-audit.json --licenses build/release-licenses
    if ($LASTEXITCODE -ne 0) { throw 'Release audit failed' }
    $testTemp = Join-Path $projectRoot ("build\\pytest-release-" + [guid]::NewGuid().ToString("N"))
    & $Python -m pytest -p no:cacheprovider --basetemp $testTemp -m 'not gpu_runtime' --junitxml=build/tests.xml
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    # Keep developer tools (Poppler, Qt SDKs, CUDA Toolkit) from leaking
    # same-named DLLs into the standalone dependency analysis.
    $originalPath = $env:PATH
    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    & $Python -m PyInstaller --noconfirm --clean $specPath
    $env:PATH = $originalPath
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
    $smokeConfig = Join-Path $projectRoot 'build\packaged-smoke-config.json'
    @{report=(Join-Path $projectRoot 'build\packaged-smoke.json'); screenshot=(Join-Path $projectRoot 'build\packaged-smoke.png')} | ConvertTo-Json | Set-Content -LiteralPath $smokeConfig -Encoding utf8
    Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    $env:QT_QPA_PLATFORM = 'windows'
    $smoke = Start-Process -FilePath (Join-Path $target 'Transcripta.exe') -ArgumentList @('--release-check', ('"' + $smokeConfig + '"')) -WindowStyle Hidden -PassThru -Wait
    if ($smoke.ExitCode -ne 0) { throw 'Packaged smoke check failed; see build/packaged-smoke.json and test-user logs' }
    if ($Installer) {
        $version = & $Python -c "import runpy; print(runpy.run_path('app/release.py')['VERSION'])"
        & $ISCC "/DProductVersion=$version" (Join-Path $projectRoot 'installer\Transcripta.iss')
        if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
        $setup = Join-Path $projectRoot "release\Transcripta-$version-Windows-x64-Setup.exe"
        $hashAlgorithm = [System.Security.Cryptography.SHA256]::Create()
        $hashStream = [IO.File]::OpenRead($setup)
        try { $hash = [Convert]::ToHexString($hashAlgorithm.ComputeHash($hashStream)).ToLowerInvariant() }
        finally { $hashStream.Dispose(); $hashAlgorithm.Dispose() }
        "$hash  $([IO.Path]::GetFileName($setup))" | Set-Content -LiteralPath "$setup.sha256" -Encoding ascii
    }
}
finally { Pop-Location }
