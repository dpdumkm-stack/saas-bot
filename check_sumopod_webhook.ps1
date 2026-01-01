# Simple SUMOPOD Webhook Checker & Updater
# Cara pakai: .\check_sumopod_webhook.ps1

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SUMOPOD Webhook Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"

Write-Host "Cloud Run Webhook: $WEBHOOK_URL" -ForegroundColor Yellow
Write-Host ""

# Ask for API key
$API_KEY = Read-Host "Masukkan SUMOPOD API Key"
if ([string]::IsNullOrWhiteSpace($API_KEY)) {
    Write-Host "❌ API key kosong. Script dihentikan." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Langkah 1: Cek session yang tersedia..." -ForegroundColor Cyan

try {
    $sessions = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions?all=true" `
        -Headers @{"X-Api-Key" = $API_KEY } `
        -TimeoutSec 10
    
    Write-Host "✅ Berhasil terhubung ke SUMOPOD" -ForegroundColor Green
    
    if ($sessions -is [array] -and $sessions.Count -gt 0) {
        Write-Host "Ditemukan $($sessions.Count) session:" -ForegroundColor Yellow
        foreach ($s in $sessions) {
            Write-Host "  - $($s.name) [$($s.status)]" -ForegroundColor White
        }
    }
    elseif ($sessions.name) {
        Write-Host "Ditemukan 1 session: $($sessions.name) [$($sessions.status)]" -ForegroundColor Yellow
    }
    else {
        Write-Host "⚠️ Tidak ada session ditemukan" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Gagal terhubung ke SUMOPOD" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Kemungkinan penyebab:" -ForegroundColor Yellow
    Write-Host "  - API key salah" -ForegroundColor Gray
    Write-Host "  - URL SUMOPOD salah" -ForegroundColor Gray
    Write-Host "  - Network/firewall issue" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LANGKAH SELANJUTNYA:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Untuk mengupdate webhook, Anda punya 3 opsi:" -ForegroundColor White
Write-Host ""
Write-Host "OPSI 1: Via Dashboard SUMOPOD (PALING MUDAH)" -ForegroundColor Green
Write-Host "  1. Buka https://sumopod.my.id/dashboard" -ForegroundColor Gray
Write-Host "  2. Login dengan akun Anda" -ForegroundColor Gray
Write-Host "  3. Pilih instance waha-2sl8ak8iil6s" -ForegroundColor Gray
Write-Host "  4. Masuk ke Settings > Webhook" -ForegroundColor Gray
Write-Host "  5. Set webhook URL ke:" -ForegroundColor Gray
Write-Host "     $WEBHOOK_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "OPSI 2: Contact SUMOPOD Support" -ForegroundColor Yellow
Write-Host "  Minta mereka set webhook URL untuk instance Anda" -ForegroundColor Gray
Write-Host ""
Write-Host "OPSI 3: Coba update via API (jalankan script lain)" -ForegroundColor Yellow
Write-Host "  .\update_sumopod_webhook.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "Webhook URL yang perlu di-set:" -ForegroundColor Cyan
Write-Host "$WEBHOOK_URL" -ForegroundColor Green
Write-Host ""
