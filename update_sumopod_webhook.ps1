# Update SUMOPOD Webhook to Cloud Run
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Update SUMOPOD Webhook" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"
$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"

Write-Host "Webhook URL: $WEBHOOK_URL" -ForegroundColor Yellow
Write-Host "SUMOPOD URL: $SUMOPOD_URL" -ForegroundColor Yellow
Write-Host ""

# Ask for API key
$API_KEY = Read-Host "Masukkan API key SUMOPOD Anda"

if ([string]::IsNullOrWhiteSpace($API_KEY)) {
    Write-Host "❌ API key tidak boleh kosong!" -ForegroundColor Red
    exit 1
}

Write-Host ""

Write-Host "Mengecek sesi yang tersedia..." -ForegroundColor Yellow
$sessionName = "default"

try {
    $sessions = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions?all=true" `
        -Headers @{"X-Api-Key" = $API_KEY } `
        -TimeoutSec 15 -ErrorAction Stop

    if ($sessions -and $sessions.Count -gt 0) {
        # Ambil session pertama
        $sessionName = $sessions[0].name
        Write-Host "✅ Ditemukan sesi aktif: $sessionName" -ForegroundColor Green
    }
    elseif ($sessions -and $sessions.name) {
        # Single object response
        $sessionName = $sessions.name
        Write-Host "✅ Ditemukan sesi aktif: $sessionName" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️ Tidak ada sesi ditemukan. Mencoba membuat sesi 'saas-bot'..." -ForegroundColor Yellow
        $sessionName = "saas-bot"
        # Optional: Auto-create logic here if needed, but for now just fallback
    }
}
catch {
    Write-Host "⚠️ Gagal mengecek sesi: $($_.Exception.Message). Mengasumsikan 'default'." -ForegroundColor Yellow
}

Write-Host "Mengupdate konfigurasi webhook untuk sesi: $sessionName" -ForegroundColor Yellow


try {
    $body = @{
        config = @{
            webhook = @{
                url    = $WEBHOOK_URL
                events = @("message", "session.status")
            }
        }
    } | ConvertTo-Json -Depth 5

    Write-Host "Sending PATCH request..." -ForegroundColor Cyan
    
    Write-Host "Mengirim request PATCH ke sesi '$sessionName'..." -ForegroundColor Cyan
    
    $response = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$sessionName" `
        -Method Patch `
        -Headers @{
        "X-Api-Key"    = $API_KEY
        "Content-Type" = "application/json"
    } `
        -Body $body `
        -TimeoutSec 20
    
    Write-Host ""
    Write-Host "✅ Request sent successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 10
    
    Write-Host ""
    Write-Host "Verifying webhook configuration..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    
    $verify = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions/$sessionName" `
        -Headers @{"X-Api-Key" = $API_KEY } `
        -TimeoutSec 15
    
    Write-Host ""
    Write-Host "Current Session Configuration:" -ForegroundColor Cyan
    $verify | ConvertTo-Json -Depth 10
    
    Write-Host ""
    
    if ($verify.config.webhook.url -eq $WEBHOOK_URL) {
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  ✅ Webhook Updated Successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Webhook sekarang mengarah ke Cloud Run!" -ForegroundColor White
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Kirim pesan /ping via WhatsApp" -ForegroundColor White
        Write-Host "2. Bot seharusnya merespons dari Cloud Run" -ForegroundColor White
        Write-Host "3. Monitor logs: gcloud run logs read saas-bot --region asia-southeast2 --limit 20" -ForegroundColor White
    }
    else {
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host "  ⚠️ Webhook Mungkin Tidak Terupdate" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Expected: $WEBHOOK_URL" -ForegroundColor White
        Write-Host "Got: $($verify.config.webhook.url)" -ForegroundColor White
        Write-Host ""
        Write-Host "Periksa output JSON di atas untuk detail." -ForegroundColor Cyan
    }
}
catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  ❌ Failed to Update Webhook" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    
    $errorDetails = $_.Exception.Message
    if ($_.ErrorDetails.Message) {
        $errorDetails = $_.ErrorDetails.Message
    }
    
    Write-Host "Error: $errorDetails" -ForegroundColor Yellow
    Write-Host ""
    
    if ($errorDetails -match "401" -or $errorDetails -match "Unauthorized") {
        Write-Host "Kemungkinan penyebab:" -ForegroundColor White
        Write-Host "  - API key tidak valid" -ForegroundColor White
        Write-Host "  - API key salah untuk session ini" -ForegroundColor White
        Write-Host "  - Session 'default' tidak ada di SUMOPOD" -ForegroundColor White
        Write-Host ""
        Write-Host "Coba:" -ForegroundColor Cyan
        Write-Host "  1. Verifikasi API key dari dashboard SUMOPOD" -ForegroundColor White
        Write-Host "  2. Cek nama session yang benar (mungkin bukan 'default')" -ForegroundColor White
    }
    else {
        Write-Host "Kemungkinan penyebab:" -ForegroundColor White
        Write-Host "  - SUMOPOD server tidak merespons" -ForegroundColor White
        Write-Host "  - Network issue" -ForegroundColor White
        Write-Host "  - Session tidak ada atau tidak aktif" -ForegroundColor White
    }
}
