# Quick SUMOPOD Test - Langsung pakai API key dari parameter
param(
    [string]$ApiKey = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
)

$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SUMOPOD Connection Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    Write-Host "Testing connection to SUMOPOD..." -ForegroundColor Yellow
    
    $sessions = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions?all=true" `
        -Headers @{"X-Api-Key" = $ApiKey } `
        -TimeoutSec 10
    
    Write-Host "[OK] Connected to SUMOPOD!" -ForegroundColor Green
    Write-Host ""
    
    if ($sessions -is [array] -and $sessions.Count -gt 0) {
        Write-Host "Found $($sessions.Count) session(s):" -ForegroundColor Yellow
        foreach ($s in $sessions) {
            Write-Host "  - Name: $($s.name)" -ForegroundColor White
            Write-Host "    Status: $($s.status)" -ForegroundColor Cyan
            if ($s.config.webhook.url) {
                Write-Host "    Webhook: $($s.config.webhook.url)" -ForegroundColor Gray
            }
            else {
                Write-Host "    Webhook: (not set)" -ForegroundColor Gray
            }
            Write-Host ""
        }
    }
    elseif ($sessions.name) {
        Write-Host "Found 1 session:" -ForegroundColor Yellow
        Write-Host "  - Name: $($sessions.name)" -ForegroundColor White
        Write-Host "    Status: $($sessions.status)" -ForegroundColor Cyan
        if ($sessions.config.webhook.url) {
            Write-Host "    Webhook: $($sessions.config.webhook.url)" -ForegroundColor Gray
        }
        else {
            Write-Host "    Webhook: (not set)" -ForegroundColor Gray
        }
        Write-Host ""
    }
    else {
        Write-Host "[WARNING] No sessions found" -ForegroundColor Yellow
        Write-Host ""
    }
    
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Target Webhook URL:" -ForegroundColor Cyan
    Write-Host "$WEBHOOK_URL" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Green
    
}
catch {
    Write-Host "[ERROR] Failed to connect to SUMOPOD" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Gray
    
    if ($_.Exception.Message -match "401" -or $_.Exception.Message -match "Unauthorized") {
        Write-Host ""
        Write-Host "Possible cause: Invalid API key" -ForegroundColor Yellow
    }
    exit 1
}
