# Deploy to Cloud Run with Database Migration
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deploy + Migrate Database" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Fix gcloud python issue
if (-not $env:CLOUDSDK_PYTHON) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $env:CLOUDSDK_PYTHON = $py.Source
    }
}

Write-Host "[1/3] Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy saas-bot `
    --source . `
    --region asia-southeast2 `
    --allow-unauthenticated `
    --set-env-vars="MIGRATE_DB=true"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Deploy failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/3] Checking migration logs..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

gcloud run services logs read saas-bot --region asia-southeast2 --limit 50 | Select-String -Pattern "migration|migrate|ALTER TABLE" -Context 2

Write-Host ""
Write-Host "[3/3] Verifying service health..." -ForegroundColor Yellow
$url = "https://saas-bot-643221888510.asia-southeast2.run.app/health"
try {
    $response = Invoke-RestMethod -Uri $url -TimeoutSec 10
    Write-Host "[OK] Service is healthy" -ForegroundColor Green
    $response | ConvertTo-Json
}
catch {
    Write-Host "[WARNING] Health check failed, but service may still be working" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Deploy Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next: Send test message to WhatsApp bot" -ForegroundColor Cyan
