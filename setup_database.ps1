# Script untuk Setup Database (Supabase)
# Usage: .\setup_database.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SETUP DATABASE (SUPABASE / POSTGRES)  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Input Connection String
Write-Host "`nLangkah 1: Salin Connection String dari Supabase"
Write-Host "Format: postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres" -ForegroundColor Gray
$RawUrl = Read-Host -Prompt "Paste URL (biarkan [YOUR-PASSWORD] tetap ada)"

if ([string]::IsNullOrWhiteSpace($RawUrl)) {
    Write-Host "Error: URL tidak boleh kosong!" -ForegroundColor Red
    exit 1
}

# 2. Input Password (Safe Encode)
Write-Host "`nLangkah 2: Masukkan Password Database Anda"
Write-Host "(Akan kami encode otomatis agar aman dari karakter spesial seperti @, #, /)" -ForegroundColor Gray
$RawPass = Read-Host -Prompt "Password Asli" -AsSecureString
$PlainPass = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($RawPass))

# 3. Process URL
# Use .NET Uri logic or simple string replacement
# Supabase default: ...:[YOUR-PASSWORD]@...
if ($RawUrl.Contains("[YOUR-PASSWORD]")) {
    $EncodedPass = [uri]::EscapeDataString($PlainPass)
    $FinalUrl = $RawUrl.Replace("[YOUR-PASSWORD]", $EncodedPass)
}
else {
    # If user already pasted with password, warn them
    Write-Host "`n⚠️  Warning: URL Anda tidak memiliki placeholder [YOUR-PASSWORD]." -ForegroundColor Yellow
    Write-Host "Kami akan mencoba mendeteksi dan mengganti password lama dengan yang baru (encoded)."
    
    try {
        # Try to parse user info
        $Uri = [System.Uri]$RawUrl
        $UserInfo = $Uri.UserInfo # format: user:pass
        if ($UserInfo -match ":(.*)") {
            $OldPass = $Matches[1]
            $EncodedPass = [uri]::EscapeDataString($PlainPass)
            $FinalUrl = $RawUrl.Replace($OldPass, $EncodedPass)
        }
        else {
            $FinalUrl = $RawUrl # Fallback
        }
    }
    catch {
        Write-Host "Gagal parsing otomatis. Menggunakan URL mentah." -ForegroundColor Red
        $FinalUrl = $RawUrl
    }
}

Write-Host "`nURL Final yang akan dipakai:" -ForegroundColor Cyan
Write-Host $FinalUrl.Replace($EncodedPass, "*****") -ForegroundColor Gray # Hide pass in log

try {
    # Check Python first (helper from previous scripts)
    if ($env:CLOUDSDK_PYTHON) {
        if (-not (Test-Path $env:CLOUDSDK_PYTHON)) {
            Write-Host "⚠️ Warning: CLOUDSDK_PYTHON points to missing file. Unsetting..." -ForegroundColor Yellow
            $env:CLOUDSDK_PYTHON = $null
        }
    }
    
    gcloud run services update saas-bot `
        --update-env-vars "DATABASE_URL=$FinalUrl" `
        --project gen-lang-client-0887245898 `
        --region asia-southeast2 `
        --quiet
        
    Write-Host "`n✅ SUKSES! Database berhasil terhubung." -ForegroundColor Green
    Write-Host "Bot akan restart otomatis dan membuat tabel-tabel baru di Supabase."
    Write-Host "Tunggu 1-2 menit sebelum mencoba akses bot lagi."
}
catch {
    Write-Host "`n❌ Error saat update Cloud Run:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nTips: Pastikan Anda sudah login (gcloud auth login) dan koneksi internet lancar."
}
