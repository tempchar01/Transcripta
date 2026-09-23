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
Get-ChildItem Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY,Env:NO_PROXY,Env:SSL_CERT_FILE,Env:REQUESTS_CA_BUNDLE -ErrorAction SilentlyContinue |
    Format-Table -AutoSize
if (-not (Get-ChildItem Env:HTTP_PROXY,Env:HTTPS_PROXY,Env:ALL_PROXY,Env:SSL_CERT_FILE,Env:REQUESTS_CA_BUNDLE -ErrorAction SilentlyContinue)) {
    Write-Output "No proxy or certificate override environment variables are set."
}

Write-Output "`n== Python / pip =="
try { py -0p 2>&1 } catch { Write-Output "Python launcher unavailable: $($_.Exception.Message)" }
try {
    python -c "import ssl, certifi, sys; print('Executable:', sys.executable); print('OpenSSL:', ssl.OPENSSL_VERSION); print('Verify paths:', ssl.get_default_verify_paths()); print('certifi:', certifi.where())"
    python -m pip --version
    python -m pip config debug
    python -m pip config list -v
} catch { Write-Output "Python/pip probe failed: $($_.Exception.Message)" }

Write-Output "`n== HTTPS reachability (certificate verification remains enabled) =="
try {
    $response = Invoke-WebRequest -Uri $Target -UseBasicParsing -TimeoutSec 15
    Write-Output "PowerShell HTTPS: PASS ($($response.StatusCode))"
} catch {
    Write-Output "PowerShell HTTPS: FAIL"
    Write-Output $_.Exception.ToString()
}
if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
    Write-Output "`ncurl.exe HTTPS:"
    & curl.exe -I --connect-timeout 15 $Target 2>&1
} else {
    Write-Output "curl.exe is not available."
}

Write-Output "`n== Windows package tooling =="
if (Get-Command winget -ErrorAction SilentlyContinue) { winget --version } else { Write-Output "winget is not installed or unavailable." }

Write-Output "`n== Interpretation =="
Write-Output "Do not use --trusted-host and do not disable certificate verification."
Write-Output "If the HTTP exception contains SocketError 10013 or curl cannot connect before TLS negotiation, the terminal/sandbox network policy is blocking TCP egress rather than rejecting a certificate."
Write-Output "This script does not change certificates, proxy settings, Python, or Windows configuration."
