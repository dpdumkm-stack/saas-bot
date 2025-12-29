$ErrorActionPreference = "Stop"

function Show-Header {
    Clear-Host
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "   UPDATE CLOUD RUN ENV VAR (WAHA_API_KEY)" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
}

# Fix for gcloud python issue
if (-not $env:CLOUDSDK_PYTHON) {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $py = Get-Command python
        $env:CLOUDSDK_PYTHON = $py.Source
    }
}

function Get-ApiKey {
    Write-Host "Masukkan WAHA_API_KEY yang BENAR (Input Hidden):" -ForegroundColor Yellow
    $key = Read-Host -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($key)
    $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    return $PlainPassword
}

Show-Header
$ApiKey = Get-ApiKey

if (-not $ApiKey) {
    Write-Host "API Key kosong."
    exit
}

Write-Host "Updating Cloud Run 'saas-bot'..." -ForegroundColor Yellow
gcloud run services update saas-bot `
    --region asia-southeast2 `
    --project  gen-lang-client-0887245898 `
    --set-env-vars "^@^WAHA_API_KEY=$ApiKey"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ SUCCESS! Env Var Updated." -ForegroundColor Green
}
else {
    Write-Host "❌ FAILED." -ForegroundColor Red
}
