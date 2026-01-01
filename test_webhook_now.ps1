# Panduan Test Webhook SUMOPOD
# Setelah webhook di-set via dashboard

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Test Webhook SUMOPOD" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Langkah 1: Kirim Pesan Test" -ForegroundColor Yellow
Write-Host "  1. Buka WhatsApp di HP Anda" -ForegroundColor White
Write-Host "  2. Kirim pesan ke nomor bot: +62 812-1940-0496" -ForegroundColor White
Write-Host "  3. Ketik pesan: /ping" -ForegroundColor Cyan
Write-Host ""

Write-Host "Langkah 2: Check Logs Cloud Run" -ForegroundColor Yellow
Write-Host "  Tunggu 5-10 detik, lalu jalankan:" -ForegroundColor White
Write-Host "    .\check_logs.ps1" -ForegroundColor Cyan
Write-Host ""

Write-Host "Yang Harus Terlihat di Logs:" -ForegroundColor Yellow
Write-Host "  - 'Received webhook from WAHA'" -ForegroundColor Gray
Write-Host "  - 'Message received: /ping'" -ForegroundColor Gray
Write-Host "  - 'Sent reply to: [nomor Anda]'" -ForegroundColor Gray
Write-Host ""

Write-Host "Jika Berhasil:" -ForegroundColor Green
Write-Host "  - Bot akan balas otomatis" -ForegroundColor White
Write-Host "  - Logs Cloud Run menunjukkan aktivitas" -ForegroundColor White
Write-Host "  - Setup SELESAI!" -ForegroundColor White
Write-Host ""

Write-Host "Jika Tidak Berhasil:" -ForegroundColor Red
Write-Host "  - Pastikan webhook URL benar di dashboard:" -ForegroundColor White
Write-Host "    https://saas-bot-643221888510.asia-southeast2.run.app/webhook" -ForegroundColor Cyan
Write-Host "  - Pastikan events sudah dipilih: message, session.status" -ForegroundColor White
Write-Host "  - Check apakah Cloud Run service running" -ForegroundColor White
Write-Host ""

Write-Host "Siap test? Kirim pesan /ping sekarang!" -ForegroundColor Green
Write-Host ""
Write-Host "Setelah kirim pesan, tekan Enter untuk check logs..." -ForegroundColor Yellow
Read-Host

# Check logs
Write-Host ""
Write-Host "Fetching latest logs from Cloud Run..." -ForegroundColor Cyan
Write-Host ""

if (-not $env:CLOUDSDK_PYTHON) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $env:CLOUDSDK_PYTHON = $py.Source
    }
}

gcloud run services logs read saas-bot --region asia-southeast2 --limit 30
