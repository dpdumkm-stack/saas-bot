# Test kirim pesan via SUMOPOD API
$API_KEY = "PxXAFORGhD2JnP8aBL6hGhvH4tbBi4SU"
$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$SESSION = "session_01kdw5dvr5119e6bdxay5bkfqn"

Write-Host "Testing direct message send..." -ForegroundColor Yellow
Write-Host ""

# Get your phone number (ganti dengan nomor HP Anda)
$targetPhone = Read-Host "Masukkan nomor HP Anda (format: 628xxx, tanpa +)"

$chatId = "$targetPhone@c.us"

$body = @{
    chatId  = $chatId
    text    = "Test dari SUMOPOD API - Bot online!"
    session = $SESSION
} | ConvertTo-Json

Write-Host "Sending message to $chatId..." -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sendText" `
        -Method Post `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 15
    
    Write-Host "[OK] Message sent!" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 5
    
    Write-Host ""
    Write-Host "Check HP Anda, seharusnya ada pesan dari +62 812-1940-0496" -ForegroundColor Cyan
    
}
catch {
    Write-Host "[FAIL] Send failed" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Gray
    
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Gray
    }
}
