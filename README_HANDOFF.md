# 🚀 Panduan Pemilik SaaS Bot (Handoff)

Selamat! Sistem Bot WhatsApp Anda sudah siap digunakan.

## 1. Status Sistem
- **Bot Engine**: `WAHA (WebJS)` + `Python Flask`
- **Database**: `saas_umkm.db` (SQLite)
- **Backup**: Otomatis tiap 6 jam ke folder `backups/`
- **Struktur**: Modular (`app/` folder)

## 2. Cara Menjalankan
Sistem berjalan otomatis di Docker. Jika PC restart/mati:
1. Buka Terminal/PowerShell.
2. Masuk ke folder: `cd c:\saas_bot`
3. Jalankan: `docker-compose up -d`

## 3. Fitur Utama
### a. Admin Dashboard
- **QR Scan**: `http://localhost:5000/admin/qr` (Gunakan browser di HP/PC).
- **Reset Koneksi**: Jika bot mati, klik tombol merah **[Reset Koneksi]** di halaman QR.

### b. Perintah Bot (Owner)
Kirim pesan ke nomor bot sendiri:
- `/menu [Nama] [Harga]` : Tambah dagangan.
- `/broadcast [Pesan] #all` : Kirim promo ke semua pelanggan.
- `/remote` : Dapatkan link dashboard stok/harga.
- `/mt on` : Nyalakan mode maintenance (hanya owner bisa chat).

### c. Pelanggan
- Pelanggan chat -> Dijawab AI (Gemini).
- Pelanggan kirim bukti transfer -> Dicek otomatis.

## 4. Troubleshooting
Jika QR tidak muncul atau bot diam:
1. Buka `http://localhost:5000/admin/qr`.
2. Klik tombol **[Reset Koneksi]**.
3. Tunggu 10-20 detik, refresh halaman.

---
*Dibuat oleh Tim Developer @ 2025*
