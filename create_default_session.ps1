$API_KEY = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"
$SESSION_NAME = "default"

Write-Host "Creating session '$SESSION_NAME' with webhook..." -ForegroundColor Cyan

$body = @{
    name   = $SESSION_NAME
    config = @{
        webhook = @{
            url    = $WEBHOOK_URL
            events = @("message", "session.status")
        }
    }
} | ConvertTo-Json -Depth 5

try {
    $response = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions" -Method Post -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } -Body $body
    Write-Host "✅ Session created successfully!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 5
}
catch {
    Write-Host "❌ Failed to create session: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
}
