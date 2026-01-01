# Test full webhook flow
Write-Host "Silakan kirim pesan '/ping' dari HP Anda ke:" -ForegroundColor Cyan
Write-Host "+62 812-1940-0496" -ForegroundColor Green
Write-Host ""
Write-Host "Menunggu 15 detik..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "Checking logs..." -ForegroundColor Cyan
gcloud run services logs read saas-bot --region asia-southeast2 --limit 50
