# Script untuk memasukkan SUMOPOD API Key ke .env
# Penggunaan: .\set_sumopod_key.ps1

param(
    [string]$ApiKey
)

$envFile = ".env"

# Jika API key tidak diberikan sebagai parameter, minta input
if (-not $ApiKey) {
    Write-Host "=== SUMOPOD API Key Setup ===" -ForegroundColor Cyan
    Write-Host ""
    $ApiKey = Read-Host "Masukkan SUMOPOD API Key Anda"
}

# Validasi input
if (-not $ApiKey -or $ApiKey.Trim() -eq "") {
    Write-Host "Error: API Key tidak boleh kosong!" -ForegroundColor Red
    exit 1
}

# Bersihkan whitespace
$ApiKey = $ApiKey.Trim()

# Baca file .env jika ada
$envContent = @()
$keyExists = $false

if (Test-Path $envFile) {
    $envContent = Get-Content $envFile
    
    # Cek apakah SUMOPOD_API_KEY sudah ada
    for ($i = 0; $i -lt $envContent.Length; $i++) {
        if ($envContent[$i] -match "^SUMOPOD_API_KEY=") {
            # Update key yang sudah ada
            $envContent[$i] = "SUMOPOD_API_KEY=$ApiKey"
            $keyExists = $true
            Write-Host "[OK] SUMOPOD_API_KEY berhasil diupdate!" -ForegroundColor Green
            break
        }
    }
    
    # Jika belum ada, tambahkan di akhir file
    if (-not $keyExists) {
        $envContent += "SUMOPOD_API_KEY=$ApiKey"
        Write-Host "[OK] SUMOPOD_API_KEY berhasil ditambahkan!" -ForegroundColor Green
    }
    
    # Simpan kembali ke file
    $envContent | Set-Content $envFile -Encoding UTF8
}
else {
    # Buat file .env baru
    "SUMOPOD_API_KEY=$ApiKey" | Set-Content $envFile -Encoding UTF8
    Write-Host "[OK] File .env berhasil dibuat dengan SUMOPOD_API_KEY!" -ForegroundColor Green
}

Write-Host ""
Write-Host "API Key tersimpan di: $envFile" -ForegroundColor Gray
Write-Host "Jangan lupa restart aplikasi Anda untuk menerapkan perubahan." -ForegroundColor Yellow
