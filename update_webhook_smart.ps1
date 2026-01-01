# Smart SUMOPOD Webhook Updater
# Otomatis pilih session yang WORKING

param(
    [string]$ApiKey = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
)

$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Smart Webhook Updater" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Get all sessions
Write-Host "[1/4] Fetching sessions..." -ForegroundColor Yellow
try {
    $sessions = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions?all=true" `
        -Headers @{"X-Api-Key" = $ApiKey } `
        -TimeoutSec 15
}
catch {
    Write-Host "[ERROR] Failed to fetch sessions" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Gray
    exit 1
}

# Step 2: Find WORKING session
Write-Host "[2/4] Finding WORKING session..." -ForegroundColor Yellow

$workingSession = $null
$sessionName = $null

if ($sessions -is [array]) {
    # Multiple sessions - find the first WORKING one
    foreach ($s in $sessions) {
        Write-Host "  - $($s.name): $($s.status)" -ForegroundColor Gray
        if ($s.status -eq "WORKING" -and -not $workingSession) {
            $workingSession = $s
            $sessionName = $s.name
        }
    }
}
elseif ($sessions.name) {
    # Single session
    Write-Host "  - $($sessions.name): $($sessions.status)" -ForegroundColor Gray
    if ($sessions.status -eq "WORKING") {
        $workingSession = $sessions
        $sessionName = $sessions.name
    }
}

if (-not $workingSession) {
    Write-Host ""
    Write-Host "[ERROR] No WORKING session found!" -ForegroundColor Red
    Write-Host "All sessions must be in WORKING status to set webhook." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[OK] Selected session: $sessionName (WORKING)" -ForegroundColor Green
Write-Host ""

# Step 3: Update webhook
Write-Host "[3/4] Updating webhook for session: $sessionName" -ForegroundColor Yellow

$body = @{
    config = @{
        webhook = @{
            url    = $WEBHOOK_URL
            events = @("message", "session.status")
        }
    }
} | ConvertTo-Json -Depth 5

try {
    $updateResponse = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$sessionName" `
        -Method Patch `
        -Headers @{
        "X-Api-Key"    = $ApiKey
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 20
    
    Write-Host "[OK] Update request sent" -ForegroundColor Green
    Start-Sleep -Seconds 3
    
}
catch {
    Write-Host "[ERROR] Failed to update webhook" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Gray
    
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Gray
    }
    exit 1
}

# Step 4: Verify
Write-Host ""
Write-Host "[4/4] Verifying webhook configuration..." -ForegroundColor Yellow

try {
    $verify = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$sessionName" `
        -Headers @{"X-Api-Key" = $ApiKey } `
        -TimeoutSec 15
    
    Write-Host ""
    
    if ($verify.config.webhook.url -eq $WEBHOOK_URL) {
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  SUCCESS!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Session: $sessionName" -ForegroundColor Cyan
        Write-Host "Webhook URL: $($verify.config.webhook.url)" -ForegroundColor White
        Write-Host "Events: $($verify.config.webhook.events -join ', ')" -ForegroundColor White
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "  1. Kirim pesan test ke WhatsApp bot Anda" -ForegroundColor Gray
        Write-Host "  2. Pesan seharusnya diterima oleh Cloud Run" -ForegroundColor Gray
        Write-Host "  3. Check logs: .\check_logs.ps1" -ForegroundColor Gray
        Write-Host ""
    }
    else {
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host "  WARNING" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Expected: $WEBHOOK_URL" -ForegroundColor Gray
        Write-Host "Got: $($verify.config.webhook.url)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Webhook might not be properly set." -ForegroundColor Yellow
    }
    
}
catch {
    Write-Host "[ERROR] Failed to verify webhook" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Gray
}
