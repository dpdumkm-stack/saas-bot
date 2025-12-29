$ErrorActionPreference = "Stop"

function Show-Header {
    Clear-Host
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Setup Midtrans Keys for SaaS Bot" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

Show-Header

# 1. Ask for Keys
Write-Host "Silakan masukkan Key dari Midtrans Dashboard (Sandbox):" -ForegroundColor Yellow
$ServerKey = Read-Host "Masukkan Server Key (contoh: SB-Mid-server-...)"
$ClientKey = Read-Host "Masukkan Client Key (contoh: SB-Mid-client-...)"

if ([string]::IsNullOrWhiteSpace($ServerKey) -or [string]::IsNullOrWhiteSpace($ClientKey)) {
    Write-Host "❌ Error: Key tidak boleh kosong!" -ForegroundColor Red
    exit 1
}

# 2. Update Cloud Run
Write-Host "`nSedang mengupdate Cloud Run (ini mungkin memakan waktu 1-2 menit)..." -ForegroundColor Yellow

# Fix for gcloud python location if needed
$env:CLOUDSDK_PYTHON = "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\platform\bundled_python\python.exe"
if (-not (Test-Path $env:CLOUDSDK_PYTHON)) {
    $env:CLOUDSDK_PYTHON = "python"
}

$ServiceName = "saas-bot"
$ProjectID = "gen-lang-client-0887245898"
$Region = "asia-southeast2"

cmd /c "gcloud run services update $ServiceName --project $ProjectID --region $Region --update-env-vars MIDTRANS_SERVER_KEY=$ServerKey,MIDTRANS_CLIENT_KEY=$ClientKey,MIDTRANS_IS_PRODUCTION=False"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ SUKSES! Midtrans Keys berhasil disimpan di Cloud Run." -ForegroundColor Green
    Write-Host "Bot sekarang siap menerima pembayaran (Mode Sandbox)." -ForegroundColor Green
}
else {
    Write-Host "`n❌ Gagal mengupdate Cloud Run. Coba lagi." -ForegroundColor Red
}

Write-Host "`nTekan Enter untuk keluar..."
Read-Host
