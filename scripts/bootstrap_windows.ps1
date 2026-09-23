[CmdletBinding()]
param(
    [switch]$InstallPython,
    [switch]$InstallFFmpeg,
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $ProjectRoot ".venv"
$PreferredPython = "3.14"

function Stop-Bootstrap([string]$Message) { Write-Error $Message; exit 1 }
function Test-Command([string]$Name) { return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

if ($env:OS -ne "Windows_NT") { Stop-Bootstrap "This bootstrap script supports Windows only." }
Write-Output "== Transcripta Windows bootstrap =="

$PythonCommand = $null
if (Test-Command "py") {
    $PreviousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $null = & py -$PreferredPython -c "import sys; print(sys.version)" 2>&1
    if ($LASTEXITCODE -eq 0) { $PythonCommand = @("py", "-$PreferredPython") }
    if (-not $PythonCommand) {
        $null = & py -3.12 -c "import sys; print(sys.version)" 2>&1
        if ($LASTEXITCODE -eq 0) { $PythonCommand = @("py", "-3.12") }
    }
    $ErrorActionPreference = $PreviousPreference
}
if (-not $PythonCommand -and (Test-Command "python")) {
    $CurrentVersion = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($CurrentVersion -in @("3.14", "3.12")) { $PythonCommand = @("python") }
}
if (-not $PythonCommand) {
    if ($InstallPython -and (Test-Command "winget")) {
        Write-Output "Installing Python $PreferredPython through winget..."
        & winget install --id Python.Python.3.14 --exact --source winget --accept-package-agreements --accept-source-agreements
        & py -$PreferredPython -c "import sys; print(sys.version)"
        if ($LASTEXITCODE -eq 0) { $PythonCommand = @("py", "-$PreferredPython") }
    }
    if (-not $PythonCommand) {
        Stop-Bootstrap "Python 3.14 (preferred) or 3.12 was not found. Install Python 3.14 through the official installer or run this script later with -InstallPython when winget is available. Existing Python installations are preserved."
    }
}

if (Test-Path (Join-Path $Venv "Scripts\python.exe")) {
    $VenvVersion = & (Join-Path $Venv "Scripts\python.exe") -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($VenvVersion -notin @("3.14", "3.12")) {
        Stop-Bootstrap "Existing .venv uses Python $VenvVersion. It was not deleted. Move or remove it deliberately, then rerun with Python 3.14 or 3.12."
    }
} else {
    Write-Output "Creating virtual environment with $($PythonCommand -join ' ')..."
    if ($PythonCommand.Count -eq 1) { & $PythonCommand[0] -m venv $Venv }
    else { & $PythonCommand[0] $PythonCommand[1] -m venv $Venv }
}

$Python = Join-Path $Venv "Scripts\python.exe"
& $Python --version
& $Python -m pip install --upgrade pip setuptools wheel
& $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
if (Test-Path (Join-Path $ProjectRoot "requirements-dev.txt")) {
    & $Python -m pip install -r (Join-Path $ProjectRoot "requirements-dev.txt")
}
& $Python -m pip check

if (-not (Test-Command "ffmpeg") -or -not (Test-Command "ffprobe")) {
    Write-Warning "FFmpeg/FFprobe are not on PATH. Development needs them for bounded chunk extraction."
    if ($InstallFFmpeg -and (Test-Command "winget")) {
        Write-Output "Installing FFmpeg through winget..."
        & winget install --id Gyan.FFmpeg --exact --source winget --accept-package-agreements --accept-source-agreements
    }
}

Push-Location $ProjectRoot
try {
    & $Python -m scripts.diagnose
    if ($RunTests) { & $Python -m pytest -v }
} finally {
    Pop-Location
}
Write-Output "Bootstrap completed. Run scripts/gpu_smoke.py with a real speech audio file to verify GPU inference."
