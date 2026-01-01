# Test Different HTTP Methods for SUMOPOD
param(
    [string]$ApiKey = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
)

$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"
$SESSION = "session_01kdw5dvr5119e6bdxay5bkfqn"

Write-Host "Testing different HTTP methods for SUMOPOD API..." -ForegroundColor Cyan
Write-Host ""

$body = @{
    config = @{
        webhook = @{
            url    = $WEBHOOK_URL
            events = @("message", "session.status")
        }
    }
} | ConvertTo-Json -Depth 5

# Test 1: PUT method
Write-Host "[Test 1] Trying PUT method..." -ForegroundColor Yellow
try {
    $result = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION" `
        -Method Put `
        -Headers @{
        "X-Api-Key"    = $ApiKey
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15
    
    Write-Host "[OK] PUT method works!" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 5
    
    # Verify
    Start-Sleep -Seconds 2
    $verify = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION" `
        -Headers @{"X-Api-Key" = $ApiKey }
    
    if ($verify.config.webhook.url -eq $WEBHOOK_URL) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  SUCCESS WITH PUT METHOD!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        exit 0
    }
}
catch {
    Write-Host "[FAIL] PUT doesn't work: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 2: POST to config endpoint
Write-Host "[Test 2] Trying POST to /config endpoint..." -ForegroundColor Yellow
try {
    $result = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION/config" `
        -Method Post `
        -Headers @{
        "X-Api-Key"    = $ApiKey
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15
    
    Write-Host "[OK] POST to /config works!" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 5
    
    # Verify
    Start-Sleep -Seconds 2
    $verify = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION" `
        -Headers @{"X-Api-Key" = $ApiKey }
    
    if ($verify.config.webhook.url -eq $WEBHOOK_URL) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  SUCCESS WITH POST /config!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        exit 0
    }
}
catch {
    Write-Host "[FAIL] POST /config doesn't work: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 3: Check available API routes
Write-Host "[Test 3] Checking OpenAPI/Swagger docs..." -ForegroundColor Yellow
try {
    $api = Invoke-RestMethod -Uri "$SUMOPOD_URL/api" -TimeoutSec 10
    Write-Host "[OK] API info retrieved" -ForegroundColor Green
    $api | ConvertTo-Json -Depth 3
}
catch {
    Write-Host "[FAIL] No API docs available" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "All automatic methods failed." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "SUMOPOD mungkin menggunakan metode konfigurasi yang berbeda." -ForegroundColor White
Write-Host ""
Write-Host "Solusi terbaik:" -ForegroundColor Cyan
Write-Host "  1. Set webhook via SUMOPOD Dashboard" -ForegroundColor White
Write-Host "  2. Atau contact SUMOPOD support untuk bantuan API" -ForegroundColor White
Write-Host ""
Write-Host "Webhook URL yang perlu di-set:" -ForegroundColor Cyan
Write-Host "  $WEBHOOK_URL" -ForegroundColor Green
Write-Host ""
