# Test SUMOPOD API Endpoints
$API_KEY = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$SESSION_NAME = "saas-bot"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"

Write-Host "Testing SUMOPOD webhook configuration methods..." -ForegroundColor Cyan
Write-Host ""

# Method 1: Try updating webhook config via sessions/:{name}/webhook
Write-Host "[Method 1] POST to /api/sessions/$SESSION_NAME/webhook" -ForegroundColor Yellow
try {
    $body = @{
        url    = $WEBHOOK_URL
        events = @("message", "session.status")
    } | ConvertTo-Json -Depth 5
    
    $result = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME/webhook" `
        -Method Post `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15
    
    Write-Host "✅ Success!" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 10
    exit 0
}
catch {
    Write-Host "❌ Failed: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host ""

# Method 2: Try PUT instead of PATCH
Write-Host "[Method 2] PUT to /api/sessions/$SESSION_NAME" -ForegroundColor Yellow
try {
    $body = @{
        name   = $SESSION_NAME
        config = @{
            webhook = @{
                url    = $WEBHOOK_URL
                events = @("message", "session.status")
            }
        }
    } | ConvertTo-Json -Depth 5
    
    $result = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
        -Method Put `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15
    
    Write-Host "✅ Success!" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 10
    exit 0
}
catch {
    Write-Host "❌ Failed: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host ""

# Method 3: Check API version - maybe /api/v1/sessions?
Write-Host "[Method 3] PATCH to /api/v1/sessions/$SESSION_NAME" -ForegroundColor Yellow
try {
    $body = @{
        config = @{
            webhook = @{
                url    = $WEBHOOK_URL
                events = @("message", "session.status")
            }
        }
    } | ConvertTo-Json -Depth 5
    
    $result = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/v1/sessions/$SESSION_NAME" `
        -Method Patch `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15
    
    Write-Host "✅ Success!" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 10
    exit 0
}
catch {
    Write-Host "❌ Failed: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "All methods failed. Possible solutions:" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Configure webhook via SUMOPOD dashboard" -ForegroundColor White
Write-Host "   - Login to SUMOPOD dashboard" -ForegroundColor White
Write-Host "   - Find session 'saas-bot' settings" -ForegroundColor White
Write-Host "   - Set webhook URL manually" -ForegroundColor White
Write-Host ""
Write-Host "2. Contact SUMOPOD support" -ForegroundColor White
Write-Host "   - Ask for correct API endpoint to set webhook" -ForegroundColor White
Write-Host "   - Or request them to set it for you" -ForegroundColor White
Write-Host ""
Write-Host "Webhook URL to use:" -ForegroundColor Cyan
Write-Host "  $WEBHOOK_URL" -ForegroundColor Green
