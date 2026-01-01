# Update SUMOPOD Webhook - Working Method

function Load-Env {
    param($envFile = ".env")
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match "^\s*([^#=]+?)\s*=\s*(.*)\s*$") {
                $name = $matches[1]
                $value = $matches[2]
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
        Write-Host "✅ Loaded configuration from .env" -ForegroundColor Green
    }
}

Load-Env

$API_KEY = $env:WAHA_API_KEY
if ([string]::IsNullOrWhiteSpace($API_KEY)) {
    Write-Host "⚠️  WAHA_API_KEY not found in environment or .env" -ForegroundColor Yellow
    $API_KEY = Read-Host "Please enter your SUMOPOD API Key"
}

$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$SESSION_NAME = "default"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Update SUMOPOD Webhook" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# First, get current session config
Write-Host "Getting current session configuration..." -ForegroundColor Yellow
$current = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
    -Headers @{"X-Api-Key" = $API_KEY }

Write-Host "Current Status: $($current.status)" -ForegroundColor Cyan
Write-Host "Current Engine: $($current.engine.engine)" -ForegroundColor Cyan
Write-Host ""

# Update with webhook config
Write-Host "Updating webhook configuration..." -ForegroundColor Yellow
$body = @{
    name   = $SESSION_NAME
    config = @{
        engine  = $current.engine.engine  # Keep existing engine
        webhook = @{
            url    = $WEBHOOK_URL
            events = @("message", "session.status")
        }
    }
} | ConvertTo-Json -Depth 5

try {
    $result = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
        -Method Put `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15
    
    Write-Host "✅ Request sent!" -ForegroundColor Green
    Write-Host ""
    
    # Wait and verify
    Start-Sleep -Seconds 3
    
    Write-Host "Verifying configuration..." -ForegroundColor Yellow
    $verify = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$SESSION_NAME" `
        -Headers @{"X-Api-Key" = $API_KEY }
    
    Write-Host ""
    Write-Host "Updated Configuration:" -ForegroundColor Cyan
    $verify | ConvertTo-Json -Depth 10
    
    Write-Host ""
    
    if ($verify.config.webhook.url -eq $WEBHOOK_URL) {
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  ✅ Webhook Configured Successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Webhook URL: $WEBHOOK_URL" -ForegroundColor White
        Write-Host "Session Status: $($verify.status)" -ForegroundColor White
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Kirim pesan /ping via WhatsApp ke session ini" -ForegroundColor White
        Write-Host "2. Bot harus merespons dari Cloud Run" -ForegroundColor White
        Write-Host "3. Check logs: gcloud run logs read saas-bot --region asia-southeast2" -ForegroundColor White
    }
    else {
        Write-Host "⚠️ Webhook URL mungkin tidak ter-set dengan benar" -ForegroundColor Yellow
        Write-Host "Expected: $WEBHOOK_URL" -ForegroundColor White
        Write-Host "Got: $($verify.config.webhook.url)" -ForegroundColor White
    }
}
catch {
    Write-Host "❌ Error: $($_.ErrorDetails.Message)" -ForegroundColor Red
}
