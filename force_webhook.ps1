# Force Set Webhook SUMOPOD
$API_KEY = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$SESSION = "session_01kdw5dvr5119e6bdxay5bkfqn"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"

Write-Host "Forcing webhook update..." -ForegroundColor Yellow
Write-Host ""

# Method 1: Try via environment PUT
$envBody = @{
    WAHA_WEBHOOK_URL    = $WEBHOOK_URL
    WAHA_WEBHOOK_EVENTS = "message,session.status"
} | ConvertTo-Json

try {
    Write-Host "[Attempt 1] Setting via environment..." -ForegroundColor Cyan
    Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION/env" `
        -Method Put `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $envBody `
        -TimeoutSec 10
    
    Write-Host "[OK] Environment updated" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] Environment method: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Method 2: Restart session to pick up webhook from dashboard
Write-Host "[Attempt 2] Restarting session..." -ForegroundColor Cyan
try {
    # Stop
    Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION/stop" `
        -Method Post `
        -Headers @{"X-Api-Key" = $API_KEY } `
        -TimeoutSec 10 | Out-Null
    
    Write-Host "  Stopped..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    # Start
    Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION/start" `
        -Method Post `
        -Headers @{"X-Api-Key" = $API_KEY } `
        -TimeoutSec 10 | Out-Null
    
    Write-Host "  Started..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    Write-Host "[OK] Session restarted" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] Restart: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Checking current config..." -ForegroundColor Yellow

$check = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION" `
    -Headers @{"X-Api-Key" = $API_KEY }

$check | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "If config still empty, webhook MUST be set via:" -ForegroundColor Yellow
Write-Host "  SUMOPOD Dashboard or SUMOPOD Support" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
