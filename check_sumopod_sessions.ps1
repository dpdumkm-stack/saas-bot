# Check SUMOPOD Sessions
$API_KEY = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"

Write-Host "Checking available sessions in SUMOPOD..." -ForegroundColor Cyan
Write-Host ""

try {
    $sessions = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions" `
        -Headers @{"X-Api-Key" = $API_KEY } `
        -TimeoutSec 15
    
    Write-Host "Available Sessions:" -ForegroundColor Green
    Write-Host ""
    
    if ($sessions.Count -eq 0) {
        Write-Host "No sessions found!" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "You need to create a session first in SUMOPOD dashboard." -ForegroundColor White
    }
    else {
        $sessions | ForEach-Object {
            Write-Host "  - Session Name: $($_.name)" -ForegroundColor White
            Write-Host "    Status: $($_.status)" -ForegroundColor Cyan
            Write-Host "    Webhook: $($_.config.webhook.url)" -ForegroundColor Yellow
            Write-Host ""
        }
    }
}
catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Response: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
}
