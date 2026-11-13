[CmdletBinding()]
param(
    [string]$Target = "https://pypi.org/simple/"
)

$ErrorActionPreference = "Continue"
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
Write-Output "== Transcripta network diagnosis (read-only) =="
Write-Output "Time: $((Get-Date).ToString('o'))"
try { Get-TimeZone | Format-List Id,DisplayName } catch { Write-Output "Time zone probe failed: $($_.Exception.Message)" }
try { w32tm /query /status 2>&1 } catch { Write-Output "Windows time service probe failed: $($_.Exception.Message)" }

Write-Output "`n== Proxy and certificate environment =="
# Only presence is reported: proxy URLs can contain embedded credentials.
$networkVariableNames = @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE')
foreach ($name in $networkVariableNames) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrEmpty($value)) { Write-Output "$name : not set" }
    else { Write-Output "$name : configured (value redacted)" }
}

Write-Output "`n== Python / pip =="
try { py -0p 2>&1 } catch { Write-Output "Python launcher unavailable: $($_.Exception.Message)" }
try {
    python -c "import ssl, certifi, sys; print('Executable:', sys.executable); print('OpenSSL:', ssl.OPENSSL_VERSION); print('Verify paths:', ssl.get_default_verify_paths()); print('certifi:', certifi.where())"
    python -m pip --version
    # pip config commands can print credentials from index URLs or environment variables.
    Write-Output "pip configuration values: redacted (inspect locally if required)"
} catch { Write-Output "Python/pip probe failed: $($_.Exception.Message)" }

Write-Output "`n== HTTPS reachability (certificate verification remains enabled) =="
try {
    $response = Invoke-WebRequest -Uri $Target -UseBasicParsing -TimeoutSec 15
    Write-Output "PowerShell HTTPS: PASS ($($response.StatusCode))"
} catch {
    Write-Output "PowerShell HTTPS: FAIL"
    Write-Output ("PowerShell HTTPS error type: " + $_.Exception.GetType().Name)
}
if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
    Write-Output "`ncurl.exe HTTPS:"
    & curl.exe -I --connect-timeout 15 --silent --show-error $Target 2>&1 | ForEach-Object { if ($_ -match "^(HTTP/|date:|content-type:)") { $_ } }
} else {
    Write-Output "curl.exe is not available."
}

Write-Output "`n== Windows package tooling =="
if (Get-Command winget -ErrorAction SilentlyContinue) { winget --version } else { Write-Output "winget is not installed or unavailable." }

Write-Output "`n== Interpretation =="
Write-Output "Do not use --trusted-host and do not disable certificate verification."
Write-Output "If the HTTP exception contains SocketError 10013 or curl cannot connect before TLS negotiation, the terminal/sandbox network policy is blocking TCP egress rather than rejecting a certificate."
Write-Output "This script does not change certificates, proxy settings, Python, or Windows configuration."
