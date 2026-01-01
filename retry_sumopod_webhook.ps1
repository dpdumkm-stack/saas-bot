# Try Different SUMOPOD Webhook Config Approaches
$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$SESSION_NAME = "default"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"

# Ask for API key securely
$API_KEY = Read-Host "Masukkan SUMOPOD API Key"
if ([string]::IsNullOrWhiteSpace($API_KEY)) {
    Write-Host "❌ API key tidak boleh kosong!" -ForegroundColor Red
    exit 1
}

Write-Host "Trying alternative webhook configuration methods..." -ForegroundColor Cyan
Write-Host ""

# Get current session
$current = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
    -Headers @{"X-Api-Key" = $API_KEY }
Write-Host "Current session status: $($current.status)" -ForegroundColor Yellow
Write-Host ""

# Attempt 1: Stop session first, then reconfigure
Write-Host "[Attempt 1] Stop, reconfigure, restart approach" -ForegroundColor Yellow
try {
    # Stop
    Write-Host "  Stopping session..." -ForegroundColor Gray
    Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME/stop" `
        -Method Post `
        -Headers @{"X-Api-Key" = $API_KEY } `
        -TimeoutSec 15 | Out-Null
    
    Start-Sleep -Seconds 3
    
    # Update config
    Write-Host "  Updating config with webhook..." -ForegroundColor Gray
    $body = @{
        config = @{
            webhook = @{
                url    = $WEBHOOK_URL
                events = @("message", "session.status")
            }
        }
    } | ConvertTo-Json -Depth 5
    
    Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
        -Method Put `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15 | Out-Null
    
    Start-Sleep -Seconds 2
    
    # Start
    Write-Host "  Starting session..." -ForegroundColor Gray
    Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME/start" `
        -Method Post `
        -Headers @{"X-Api-Key" = $API_KEY } `
        -TimeoutSec 15 | Out-Null
    
    Start-Sleep -Seconds 3
    
    # Verify
    $verify = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
        -Headers @{"X-Api-Key" = $API_KEY }
    
    if ($verify.config.webhook.url -eq $WEBHOOK_URL) {
        Write-Host "  ✅ SUCCESS with stop/start method!" -ForegroundColor Green
        Write-Host ""
        $verify | ConvertTo-Json -Depth 10
        exit 0
    }
    else {
        Write-Host "  ❌ Webhook still not set" -ForegroundColor Red
    }
}
catch {
    Write-Host "  ❌ Failed: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host ""

# Attempt 2: Different JSON structure
Write-Host "[Attempt 2] Alternative JSON structure" -ForegroundColor Yellow
try {
    $body = @"
{
  "config": {
    "webhook": {
      "url": "$WEBHOOK_URL",
      "events": ["message", "session.status"]
    }
  }
}
"@
    
    $result = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
        -Method Put `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15
    
    Start-Sleep -Seconds 2
    
    $verify = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
        -Headers @{"X-Api-Key" = $API_KEY }
    
    if ($verify.config.webhook.url -eq $WEBHOOK_URL) {
        Write-Host "  ✅ SUCCESS with alternative JSON!" -ForegroundColor Green
        Write-Host ""
        $verify | ConvertTo-Json -Depth 10
        exit 0
    }
    else {
        Write-Host "  ❌ Webhook still not set" -ForegroundColor Red
    }
}
catch {
    Write-Host "  ❌ Failed: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host ""

# Attempt 3: Maybe it needs the full config object
Write-Host "[Attempt 3] Full config with all fields" -ForegroundColor Yellow
try {
    $body = @{
        name   = $SESSION_NAME
        config = @{
            proxy   = $null
            webhook = @{
                url           = $WEBHOOK_URL
                events        = @("message", "session.status")
                hmac          = $null
                retries       = $null
                customHeaders = $null
            }
        }
    } | ConvertTo-Json -Depth 10
    
    $result = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
        -Method Put `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15
    
    Start-Sleep -Seconds 2
    
    $verify = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
        -Headers @{"X-Api-Key" = $API_KEY }
    
    if ($verify.config.webhook.url -eq $WEBHOOK_URL) {
        Write-Host "  ✅ SUCCESS with full config!" -ForegroundColor Green
        Write-Host ""
        $verify | ConvertTo-Json -Depth 10
        exit 0
    }
    else {
        Write-Host "  ❌ Webhook still not set" -ForegroundColor Red
    }
}
catch {
    Write-Host "  ❌ Failed: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Red
Write-Host "  All attempts failed" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""
Write-Host "SUMOPOD mungkin tidak support webhook config via API." -ForegroundColor Yellow
Write-Host "Silakan set via dashboard atau contact SUMOPOD support." -ForegroundColor Yellow
Write-Host ""
Write-Host "Webhook URL to use:" -ForegroundColor Cyan
Write-Host "  $WEBHOOK_URL" -ForegroundColor Green
