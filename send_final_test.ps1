# Send Final Test Message
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SENDING FINAL TEST MESSAGE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$body = @{
    chatId  = "6287751920005@c.us"
    text    = "Test final setelah fix - bot should respond!"
    session = "session_01kdw5dvr5119e6bdxay5bkfqn"
} | ConvertTo-Json

Write-Host "Sending test message..." -ForegroundColor Cyan
try {
    Invoke-RestMethod -Uri "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id/api/sendText" `
        -Method Post `
        -Headers @{
        "X-Api-Key"    = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15 | Out-Null
    
    Write-Host "[OK] Message sent!" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] Could not send: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting 15 seconds for webhook & response..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "Fetching latest logs..." -ForegroundColor Cyan
Write-Host ""

gcloud run services logs read saas-bot --region asia-southeast2 --limit 50 | Select-String -Pattern "migration|WEBHOOK|Sending to WAHA|ERROR" | Select-Object -Last 20

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Check logs above for:" -ForegroundColor White
Write-Host "  - Migration messages" -ForegroundColor Gray
Write-Host "  - WEBHOOK RAW (received)" -ForegroundColor Gray
Write-Host "  - Bot response" -ForegroundColor Gray
Write-Host "  - Any errors" -ForegroundColor Gray
