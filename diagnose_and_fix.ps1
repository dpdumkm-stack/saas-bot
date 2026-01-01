# ================================================================================
# COMPLETE DIAGNOSTIC & FIX FOR WEBHOOK ISSUE
# ================================================================================

$API_KEY = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$SESSION = "session_01kdw5dvr5119e6bdxay5bkfqn"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Webhook Diagnostic & Fix" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check session status
Write-Host "[1/5] Checking session status..." -ForegroundColor Yellow
$session = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION" `
    -Headers @{"X-Api-Key" = $API_KEY }

Write-Host "  Session: $($session.name)" -ForegroundColor White
Write-Host "  Status: $($session.status)" -ForegroundColor White
Write-Host "  WhatsApp: $($session.me.id)" -ForegroundColor White
Write-Host "  Config webhook: $(if($session.config.webhook.url){$session.config.webhook.url}else{'NOT SET'})" -ForegroundColor $(if ($session.config.webhook.url) { 'Green' }else { 'Red' })
Write-Host ""

# Step  2: Try to set webhook via  multiple methods
Write-Host "[2/5] Attempting to set webhook..." -ForegroundColor Yellow

# Try Method A: Direct config update
$configBody = @{
    webhook = @{
        url    = $WEBHOOK_URL
        events = @("message", "session.status")
    }
} | ConvertTo-Json -Depth 5

try {
    $result = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION/config/webhook" `
        -Method Post `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $configBody `
        -TimeoutSec 10 -ErrorAction Stop
    
    Write-Host "  [SUCCESS] Webhook set via API!" -ForegroundColor Green
    $webhookSet = $true
}
catch {
    Write-Host "  [Method A Failed] $($_.Exception.Message)" -ForegroundColor Gray
    $ webhookSet = $false
}

Write-Host ""

# Step 3: Verify webhook
Write-Host "[3/5] Verifying webhook..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

$verify = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION" `
    -Headers @{"X-Api-Key" = $API_KEY }

if ($verify.config.webhook.url -eq $WEBHOOK_URL) {
    Write-Host "  [OK] Webhook verified: $WEBHOOK_URL" -ForegroundColor Green
    $webhookWorking = $true
}
else {
    Write-Host "  [FAILED] Webhook NOT set in session config" -ForegroundColor Red
    $webhookWorking = $false
}

Write-Host ""

# Step 4: Test webhook by sending yourself a message
Write-Host "[4/5] Would you like to test by sending a message to yourself? (y/n)" -ForegroundColor Yellow
$testChoice = Read-Host

if ($testChoice -eq 'y') {
    $yourPhone = Read-Host "Enter your phone (format 628xxx, no +)"
    
    $testBody = @{
        chatId  = "$yourPhone@c.us"
        text    = "Test webhook - jika terima ini, bot online!"
        session = $SESSION
    } | ConvertTo-Json
    
    try {
        Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sendText" `
            -Method Post `
            -Headers @{
            "X-Api-Key"    = $API_KEY
            "Content-Type" = "application/json"
        } `
            -Body $testBody `
            -TimeoutSec 10 | Out-Null
        
        Write-Host "  [OK] Test message sent to your WhatsApp" -ForegroundColor Green
    }
    catch {
        Write-Host "  [FAIL] Could not send test message" -ForegroundColor Red
    }
}

Write-Host ""

# Step 5: Final verdict
Write-Host "[5/5] Final Status:" -ForegroundColor Yellow
Write-Host ""

if ($webhookWorking) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  WEBHOOK IS WORKING!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next: Send /ping to +62 812-1940-0496" -ForegroundColor Cyan
    Write-Host "Then check logs: .\check_logs.ps1" -ForegroundColor Cyan
}
else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  WEBHOOK NOT WORKING - MANUAL ACTION REQUIRED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "SUMOPOD tidak support set webhook via API." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Silakan set webhook secara MANUAL:" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 1: Via SUMOPOD Dashboard" -ForegroundColor Cyan
    Write-Host "  1. Login ke https://sumopod.my.id/dashboard" -ForegroundColor Gray
    Write-Host "  2. Pilih instance: waha-2sl8ak8iil6s" -ForegroundColor Gray
    Write-Host "  3. Pilih session: $SESSION" -ForegroundColor Gray
    Write-Host "  4. Set Webhook URL: $WEBHOOK_URL" -ForegroundColor Gray
    Write-Host "  5. Events: message, session.status" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 2: Contact SUMOPOD Support" -ForegroundColor Cyan
    Write-Host "  Email: support@sumopod.my.id" -ForegroundColor Gray
    Write-Host "  Request: Set webhook untuk session $SESSION" -ForegroundColor Gray
    Write-Host "  URL: $WEBHOOK_URL" -ForegroundColor Gray
}

Write-Host ""
