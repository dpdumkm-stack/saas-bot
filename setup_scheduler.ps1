# Setup Cloud Scheduler for SaaS Bot
# Heartbeat (Keep-Alive) & Daily Checks

# Fix for gcloud python location
$env:CLOUDSDK_PYTHON = "C:\Users\p\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path $env:CLOUDSDK_PYTHON)) {
    $env:CLOUDSDK_PYTHON = "python"
}

$SERVICE_URL = "https://saas-bot-643221888510.asia-southeast2.run.app"
$LOCATION = "asia-southeast2"
$CRON_SECRET = "RahasiaNegara123"

Write-Host "Setting up Cloud Scheduler..." -ForegroundColor Cyan

# 1. Hearthbeat (Every 5 mins)
Write-Host "Creating 'saas-bot-heartbeat'..." -ForegroundColor Yellow
gcloud scheduler jobs create http saas-bot-heartbeat `
    --schedule="*/5 * * * *" `
    --uri="$SERVICE_URL/api/cron/heartbeat" `
    --http-method=GET `
    --location=$LOCATION `
    --description="Keep Cloud Run instance warm for background workers" `
    --quiet 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Job might already exist, trying update..." -ForegroundColor Yellow
    gcloud scheduler jobs update http saas-bot-heartbeat `
        --schedule="*/5 * * * *" `
        --uri="$SERVICE_URL/api/cron/heartbeat" `
        --http-method=GET `
        --location=$LOCATION `
        --quiet
}

# 2. Daily Checks (Every day at 07:00 WIB / 00:00 UTC)
Write-Host "Creating 'saas-bot-daily-checks'..." -ForegroundColor Yellow
gcloud scheduler jobs create http saas-bot-daily-checks `
    --schedule="0 0 * * *" `
    --uri="$SERVICE_URL/api/cron/daily_checks" `
    --http-method=GET `
    --headers="X-App-Cron-Secret=$CRON_SECRET" `
    --location=$LOCATION `
    --description="Daily subscription expiry checks and cleanup" `
    --quiet 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Job might already exist, trying update..." -ForegroundColor Yellow
    gcloud scheduler jobs update http saas-bot-daily-checks `
        --schedule="0 0 * * *" `
        --uri="$SERVICE_URL/api/cron/daily_checks" `
        --http-method=GET `
        --headers="X-App-Cron-Secret=$CRON_SECRET" `
        --location=$LOCATION `
        --quiet
}

Write-Host "✅ Scheduler Setup Completed!" -ForegroundColor Green
gcloud scheduler jobs list --location=$LOCATION
