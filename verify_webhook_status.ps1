# Simple Webhook Verification Test
$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  WEBHOOK VERIFICATION TEST" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Load from .env file
if (Test-Path ".\.env") {
    Get-Content ".\.env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        }
    }
    Write-Host "[+] Loaded configuration from .env" -ForegroundColor Green
}
else {
    Write-Host "[!] .env file not found" -ForegroundColor Yellow
}

$SUMOPOD_API_KEY = $env:WAHA_API_KEY
$SUMOPOD_URL = $env:WAHA_BASE_URL
$WEBHOOK_URL = $env:WAHA_WEBHOOK_URL
$WEBHOOK_SECRET = $env:WEBHOOK_SECRET

if (-not $SUMOPOD_API_KEY -or -not $SUMOPOD_URL) {
    Write-Host "[X] Missing WAHA_API_KEY or WAHA_BASE_URL in .env" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  SUMOPOD URL: $SUMOPOD_URL" -ForegroundColor Gray
Write-Host "  Webhook URL: $WEBHOOK_URL" -ForegroundColor Gray
Write-Host ""

# Test 1: Check SUMOPOD Sessions
Write-Host "[Test 1/3] Checking SUMOPOD sessions..." -ForegroundColor Cyan
try {
    $sessions = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions?all=true" `
        -Headers @{"X-Api-Key" = $SUMOPOD_API_KEY } `
        -TimeoutSec 10
    
    Write-Host "  [OK] SUMOPOD API accessible" -ForegroundColor Green
    
    if ($sessions -is [array]) {
        Write-Host "  Found $($sessions.Count) session(s):" -ForegroundColor Yellow
        foreach ($s in $sessions) {
            Write-Host "     - $($s.name) [Status: $($s.status)]" -ForegroundColor White
            
            if ($s.config.webhooks -and $s.config.webhooks.Count -gt 0) {
                $webhook = $s.config.webhooks[0]
                Write-Host "       Webhook: $($webhook.url)" -ForegroundColor Gray
                Write-Host "       Events: $($webhook.events -join ', ')" -ForegroundColor Gray
            }
            else {
                Write-Host "       [!] No webhook configured" -ForegroundColor Red
            }
        }
    }
    else {
        Write-Host "  [!] No sessions found" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  [X] Failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: Test Cloud Run Endpoint
Write-Host "[Test 2/3] Testing Cloud Run webhook endpoint..." -ForegroundColor Cyan
try {
    $mockPayload = @{
        event   = "session.status"
        session = "test"
        payload = @{
            status = "WORKING"
        }
    } | ConvertTo-Json

    $headers = @{
        "Content-Type" = "application/json"
        "X-Header-2"   = $WEBHOOK_SECRET
    }

    $webhookResponse = Invoke-RestMethod -Uri $WEBHOOK_URL `
        -Method Post `
        -Headers $headers `
        -Body $mockPayload `
        -TimeoutSec 10

    Write-Host "  [OK] Webhook endpoint accessible" -ForegroundColor Green
    Write-Host "  Response: $($webhookResponse | ConvertTo-Json -Compress)" -ForegroundColor Gray
}
catch {
    Write-Host "  [X] Webhook test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 3: Simulate Message
Write-Host "[Test 3/3] Testing message simulation..." -ForegroundColor Cyan
try {
    $testMessage = @{
        event   = "message"
        session = "default"
        payload = @{
            from = "628123456789@c.us"
            body = "/ping"
            type = "chat"
        }
    } | ConvertTo-Json

    $headers = @{
        "Content-Type" = "application/json"
        "X-Header-2"   = $WEBHOOK_SECRET
    }

    $messageResponse = Invoke-RestMethod -Uri $WEBHOOK_URL `
        -Method Post `
        -Headers $headers `
        -Body $testMessage `
        -TimeoutSec 10

    Write-Host "  [OK] Message processed" -ForegroundColor Green
    Write-Host "  Response: $($messageResponse | ConvertTo-Json -Compress)" -ForegroundColor Gray
}
catch {
    Write-Host "  [!] Message test: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Verify in SUMOPOD dashboard:" -ForegroundColor Yellow
Write-Host "  Webhook URL should be: $WEBHOOK_URL" -ForegroundColor Green
Write-Host "  Events: message, session.status" -ForegroundColor Green
Write-Host ""
