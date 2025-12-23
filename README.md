# 🤖 WhatsApp SaaS Bot - Panduan Lengkap

> Bot WhatsApp multi-tenant untuk UMKM dengan AI Gemini, dijalankan menggunakan Docker

---

## 📋 Daftar Isi

1. [Tentang Aplikasi](#tentang-aplikasi)
2. [Prasyarat](#prasyarat)
3. [Instalasi](#instalasi)
4. [Konfigurasi](#konfigurasi)
5. [Menjalankan Aplikasi](#menjalankan-aplikasi)
6. [Menghubungkan WhatsApp](#menghubungkan-whatsapp)
7. [Menggunakan Bot](#menggunakan-bot)
8. [Dashboard Web](#dashboard-web)
9. [Perintah Docker](#perintah-docker)
10. [Troubleshooting](#troubleshooting)
11. [Backup & Restore](#backup--restore)

---

## 🎯 Tentang Aplikasi

Aplikasi ini adalah bot WhatsApp berbasis SaaS yang memungkinkan multiple toko/bisnis menggunakan satu nomor WhatsApp untuk:
- ✅ Melayani pelanggan dengan AI (Gemini)
- ✅ Manajemen produk
- ✅ Tracking pesanan
- ✅ Manajemen customer
- ✅ Dashboard web untuk monitoring

### Arsitektur

```
┌─────────────────┐
│  WhatsApp User  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   WAHA Service  │ ← Koneksi WhatsApp (Port 3000)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Bot App       │ ← Logika bisnis + AI (Port 5000)
│   (Python)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   SQLite DB     │ ← Data toko, produk, customer
└─────────────────┘
```

---

## 🔧 Prasyarat

### Yang Harus Sudah Terinstal:

1. **Docker Desktop** (Windows)
   - Download: https://www.docker.com/products/docker-desktop
   - Minimum: 4GB RAM available untuk Docker
   - Pastikan WSL2 sudah aktif (untuk Windows)

2. **API Keys**
   - **Gemini API Key**: https://aistudio.google.com/app/apikey
   - Gratis dengan quota yang cukup besar

3. **Nomor WhatsApp**
   - Nomor yang akan digunakan untuk bot
   - **PENTING**: Jangan gunakan nomor WhatsApp Business yang sudah terverifikasi
   - Bisa gunakan nomor baru atau nomor pribadi

---

## 📥 Instalasi

### Langkah 1: Clone/Download Project

Jika Anda sudah punya folder `c:\saas_bot`, skip langkah ini.

### Langkah 2: Verifikasi Struktur Folder

Pastikan struktur folder seperti ini:

```
c:\saas_bot\
├── .env                  # Konfigurasi environment
├── .env.example          # Template konfigurasi
├── docker-compose.yml    # Orchestrasi container
├── dockerfile            # Build image untuk bot
├── main.py               # Kode utama aplikasi
├── requirements.txt      # Dependencies Python
├── restart.sh            # Script restart (opsional)
├── templates/            # HTML templates
└── README.md            # File ini
```

### Langkah 3: Install Docker Desktop

1. Download Docker Desktop untuk Windows
2. Jalankan installer
3. Restart komputer jika diminta
4. Buka Docker Desktop
5. Tunggu sampai status: **"Engine running"** ✅

---

## ⚙️ Konfigurasi

### File `.env`

File `.env` Anda saat ini:

```env
# --- GEMINI AI ---
GEMINI_API_KEY=AIzaSyC4_ty5rsP2eMfG-vafFHBEnMhZRRfK6Oo

# --- ADMIN SUPER ---
SUPER_ADMIN_WA=6281219400496

# --- FLASK SECRET KEY ---
SECRET_KEY=

# --- WAHA CONFIGURATION ---
WAHA_BASE_URL=http://waha:3000
MASTER_SESSION=default

# --- SYSTEM LIMITS ---
TARGET_LIMIT_USER=500
WARNING_THRESHOLD=450
```

### Penjelasan Konfigurasi:

| Variable | Penjelasan | Contoh |
|----------|------------|--------|
| `GEMINI_API_KEY` | API key dari Google AI Studio | `AIzaSy...` |
| `SUPER_ADMIN_WA` | Nomor WA admin (tanpa +) | `6281234567890` |
| `SECRET_KEY` | Key untuk session Flask (kosongkan = auto) | (kosong) |
| `WAHA_BASE_URL` | URL internal WAHA service | `http://waha:3000` |
| `MASTER_SESSION` | Nama session WhatsApp | `default` |
| `TARGET_LIMIT_USER` | Max users per toko | `500` |
| `WARNING_THRESHOLD` | Warning saat mendekati limit | `450` |

> ⚠️ **PENTING**: Jangan share file `.env` ke public! Berisi API key rahasia.

---

## 🚀 Menjalankan Aplikasi

### Langkah 1: Buka PowerShell/CMD

```powershell
# Masuk ke folder project
cd c:\saas_bot
```

### Langkah 2: Start Container

```powershell
# Jalankan semua service
docker-compose up -d
```

**Output yang diharapkan:**
```
Creating network "saas_bot_default" with the default driver
Creating waha_service ... done
Creating saas_bot_app ... done
```

> 🕐 **Waktu**: Pertama kali bisa 3-5 menit (download image + build)

### Langkah 3: Cek Status Container

```powershell
docker-compose ps
```

**Output yang diharapkan:**
```
     Name                   Command               State           Ports
--------------------------------------------------------------------------------
saas_bot_app    python main.py                   Up      0.0.0.0:5000->5000/tcp
waha_service    docker-entrypoint.sh node ...    Up      0.0.0.0:3000->3000/tcp
```

Status harus **"Up"** untuk kedua container.

### Langkah 4: Cek Log (Opsional)

```powershell
# Lihat log bot
docker-compose logs bot_app

# Follow log realtime
docker-compose logs -f bot_app

# Tekan Ctrl+C untuk stop follow
```

---

## 📱 Menghubungkan WhatsApp

### Langkah 1: Akses WAHA Dashboard

1. Buka browser
2. Kunjungi: **http://localhost:3000**
3. Anda akan melihat WAHA API page

### Langkah 2: Start Session WhatsApp

Gunakan API untuk start session:

```powershell
# Menggunakan curl (install dulu jika belum ada)
curl -X POST http://localhost:3000/api/sessions/start `
  -H "Content-Type: application/json" `
  -d '{"name": "default"}'
```

**Atau gunakan Postman/Browser:**

- **Method**: POST
- **URL**: `http://localhost:3000/api/sessions/start`
- **Body** (JSON):
  ```json
  {
    "name": "default"
  }
  ```

### Langkah 3: Dapatkan QR Code

```powershell
# Mendapatkan QR code
curl http://localhost:3000/api/sessions/default/auth/qr
```

**Atau buka di browser:**
- **URL**: `http://localhost:3000/api/sessions/default/auth/qr`

Akan muncul **gambar QR Code**.

### Langkah 4: Scan QR Code

1. Buka WhatsApp di HP
2. Pilih **Menu** (3 titik) → **Linked Devices** / **Perangkat Tertaut**
3. Tap **Link a Device** / **Tautkan Perangkat**
4. Scan QR code yang muncul di browser

### Langkah 5: Verifikasi Koneksi

```powershell
# Cek status session
curl http://localhost:3000/api/sessions/default
```

Status harus **"WORKING"** atau **"CONNECTED"**.

---

## 💬 Menggunakan Bot

### Sebagai Super Admin

Kirim pesan ke nomor WhatsApp bot dengan perintah:

#### 1. Registrasi Toko Baru

```
/daftar_toko
```

Bot akan memandu Anda untuk:
1. Nama toko
2. Email toko
3. Password toko

#### 2. Set Nomor Sebagai Admin Toko

```
/set_admin_toko <store_id>
```

Contoh:
```
/set_admin_toko 1
```

#### 3. Lihat Statistik Global

```
/stats_global
```

### Sebagai Admin Toko

Setelah nomor Anda jadi admin toko:

#### Tambah Produk
```
/tambah_produk
```

Format:
```
Nama: Sepatu Nike Air
Harga: 500000
Stok: 10
Kategori: Sepatu
```

#### Lihat Produk
```
/lihat_produk
```

#### Edit Produk
```
/edit_produk [ID]
```

#### Hapus Produk
```
/hapus_produk [ID]
```

#### Lihat Customer
```
/lihat_customer
```

#### Statistik Toko
```
/stats_toko
```

### Sebagai Customer

Customer cukup chat biasa, AI akan merespons:

```
Halo, ada produk apa aja?
```

```
Saya mau pesan Sepatu Nike Air 2 pcs
```

---

## 🌐 Dashboard Web

### Akses Dashboard

Buka browser: **http://localhost:5000**

### Fitur Dashboard

1. **Home** (`/`)
   - Overview sistem
   - Status health check

2. **Health Check** (`/health`)
   - Status aplikasi
   - Koneksi database
   - Koneksi WAHA
   - Info sistem

3. **API Endpoints** (akan dijelaskan jika ada)

---

## 🐳 Perintah Docker

### Container Management

```powershell
# Start semua service
docker-compose up -d

# Stop semua service
docker-compose down

# Restart semua service
docker-compose restart

# Restart service tertentu
docker-compose restart bot_app

# Stop tanpa hapus container
docker-compose stop

# Start container yang di-stop
docker-compose start
```

### Logs & Monitoring

```powershell
# Lihat log semua service
docker-compose logs

# Log service tertentu
docker-compose logs bot_app
docker-compose logs waha

# Follow log (realtime)
docker-compose logs -f bot_app

# Log 100 baris terakhir
docker-compose logs --tail=100 bot_app
```

### Rebuild & Update

```powershell
# Rebuild aplikasi setelah ubah kode
docker-compose up -d --build

# Pull image terbaru
docker-compose pull

# Rebuild tanpa cache
docker-compose build --no-cache
```

### Cleanup

```powershell
# Hapus semua container + network
docker-compose down

# Hapus container + volumes (HATI-HATI: data hilang!)
docker-compose down -v

# Hapus unused images
docker image prune -a
```

---

## 🔧 Troubleshooting

### Problem 1: Container Tidak Start

**Gejala:**
```
Error starting container: port is already allocated
```

**Solusi:**
```powershell
# Cek aplikasi yang pakai port 3000 atau 5000
netstat -ano | findstr :3000
netstat -ano | findstr :5000

# Stop aplikasi yang bentrok atau ubah port di docker-compose.yml
```

### Problem 2: WAHA Tidak Terhubung

**Gejala:**
- QR code tidak muncul
- Session status: FAILED

**Solusi:**
```powershell
# Restart WAHA service
docker-compose restart waha

# Hapus data session lama
Remove-Item -Recurse -Force .\waha_data\*

# Start ulang
docker-compose up -d
```

### Problem 3: Bot Tidak Merespon

**Gejala:**
- Pesan terkirim tapi bot diam

**Solusi:**
```powershell
# Cek log untuk error
docker-compose logs bot_app

# Pastikan Gemini API key valid
# Cek .env file

# Restart bot
docker-compose restart bot_app
```

### Problem 4: Database Error

**Gejala:**
```
sqlite3.OperationalError: database is locked
```

**Solusi:**
```powershell
# Stop semua container
docker-compose down

# Hapus file lock
Remove-Item saas_umkm.db-journal -ErrorAction SilentlyContinue

# Start ulang
docker-compose up -d
```

### Problem 5: Container Keluar Terus (Exit)

**Gejala:**
```
saas_bot_app    Exited (1)
```

**Solusi:**
```powershell
# Lihat log error
docker-compose logs bot_app

# Cek dependency di requirements.txt
# Rebuild dari awal
docker-compose down
docker-compose up -d --build
```

### Problem 6: Memory Tinggi

**Gejala:**
- Docker Desktop memakan banyak RAM

**Solusi:**
1. Buka Docker Desktop
2. Settings → Resources
3. Turunkan Memory limit (misal ke 2GB)
4. Apply & Restart

---

## 💾 Backup & Restore

### Backup Manual

```powershell
# Backup database
Copy-Item saas_umkm.db backups\saas_umkm_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db

# Backup semua data penting
Compress-Archive -Path saas_umkm.db,waha_data,.env -DestinationPath backup_$(Get-Date -Format 'yyyyMMdd').zip
```

### Restore Database

```powershell
# Stop bot terlebih dahulu
docker-compose stop bot_app

# Restore dari backup
Copy-Item backups\saas_umkm_backup_20241222_120000.db saas_umkm.db

# Start kembali
docker-compose start bot_app
```

### Auto Backup (Built-in)

Bot sudah punya fitur auto backup setiap 24 jam ke folder `backups/`.

---

## 📊 Monitoring

### Health Check Endpoint

```powershell
# Cek kesehatan aplikasi
curl http://localhost:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "waha": "connected",
  "uptime": "2 hours",
  "timestamp": "2024-12-22T03:23:00"
}
```

### Database Stats

```powershell
# Login ke container
docker exec -it saas_bot_app bash

# Cek ukuran database
ls -lh saas_umkm.db

# Keluar
exit
```

---

## 📝 Catatan Penting

### Keamanan

1. ⚠️ **Jangan commit file `.env` ke Git**
2. ⚠️ **Ganti SECRET_KEY untuk production**
3. ⚠️ **Backup database secara berkala**
4. ⚠️ **Simpan API key di tempat aman**

### Performance

- **RAM**: Minimal 4GB untuk Docker
- **Disk**: Minimal 5GB free space
- **Network**: Koneksi internet stabil untuk WhatsApp

### Limit

- Default: 500 users per toko
- Bisa diubah di `.env` → `TARGET_LIMIT_USER`
- WhatsApp limit: ~1000 pesan/hari (unofficial)

---

## 🆘 Bantuan Lebih Lanjut

### Log Files

- **Bot Log**: `bot_saas.log`
- **Docker Log**: `docker-compose logs`

### Resources

- **WAHA Docs**: https://waha.devlike.pro/
- **Gemini AI**: https://ai.google.dev/
- **Docker Docs**: https://docs.docker.com/

### Contact

- **Super Admin WA**: 6281219400496 (dari `.env`)

---

## 📜 License

Aplikasi ini untuk keperluan pribadi/bisnis. Pastikan mematuhi:
- Terms of Service WhatsApp
- Google AI Studio Terms
- Docker License

---

**Selamat menggunakan! 🎉**

Jika ada pertanyaan, silakan hubungi super admin atau cek troubleshooting guide di atas.
