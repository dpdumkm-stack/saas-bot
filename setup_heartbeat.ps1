# setup_heartbeat.ps1
# Automates Google Cloud Scheduler setup to ping the heartbeat endpoint.

$PROJECT_ID = "saas-bot-643221888510"
$LOCATION = "asia-southeast2"
$SERVICE_URL = "https://saas-bot-643221888510.asia-southeast2.run.app"
$CRON_NAME = "saas-bot-heartbeat"
$SCHEDULE = "*/5 * * * *"  # Every 5 minutes

Write-Host "🚀 Setting up Cloud Scheduler for $CRON_NAME..." -ForegroundColor Cyan

# Check if job already exists
$job = gcloud scheduler jobs list --location=$LOCATION --format="value(name)" --filter="name:$CRON_NAME"

if ($job) {
    Write-Host "🔄 Updating existing job..." -ForegroundColor Yellow
    gcloud scheduler jobs update http $CRON_NAME `
        --location=$LOCATION `
        --schedule="$SCHEDULE" `
        --uri="$SERVICE_URL/api/cron/heartbeat" `
        --http-method=GET `
        --time-zone="Asia/Jakarta" `
        --description="Keep Cloud Run alive and monitor workers"
}
else {
    Write-Host "✨ Creating new job..." -ForegroundColor Green
    gcloud scheduler jobs create http $CRON_NAME `
        --location=$LOCATION `
        --schedule="$SCHEDULE" `
        --uri="$SERVICE_URL/api/cron/heartbeat" `
        --http-method=GET `
        --time-zone="Asia/Jakarta" `
        --description="Keep Cloud Run alive and monitor workers"
}

Write-Host "✅ Heartbeat scheduler setup complete!" -ForegroundColor Green
Write-Host "🔗 Endpoint: $SERVICE_URL/api/cron/heartbeat"
