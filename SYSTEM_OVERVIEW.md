# Dokumentasi Sistem SaaS Bot UMKM (Hybrid Turbo)

Dokumen ini menjelaskan alur kerja, fitur, dan arsitektur sistem SaaS Bot yang dirancang untuk membantu UMKM mengelola pesanan mereka via WhatsApp dengan bantuan AI.

---

## 🚀 1. Alur Sistem (Hybrid Turbo Flow)

Sistem ini menggunakan pendekatan **Hybrid Turbo** untuk mempercepat proses onboarding merchant baru:
- **Pendaftaran via Web**: Memudahkan pemilihan paket dan pembayaran.
- **Aktivasi via WhatsApp**: Memudahkan koneksi bot tanpa scan QR yang rumit.

### 📋 Tahap A: Pendaftaran (Web)
1. **Landing Page**: Calon pengguna (Merchant) membuka website, melihat fitur, dan memilih paket:
    - **Starter**: Rp 99rb/bln
    - **Business**: Rp 199rb/bln
    - **Pro**: Rp 349rb/bln
2. **Form Data**: Mengisi Nama Toko, Kategori (F&B, Jasa, Retail), dan No. WA.
3. **Pembayaran**: Sistem membuat invoice via Midtrans (support QRIS, VA, E-Wallet).

### 🔑 Tahap B: Aktivasi (Hybrid Handoff)
1. **Sukses Bayar**: Setelah pembayaran dikonfirmasi, Merchant diarahkan ke **Halaman Sukses**.
2. **Get Pairing Code**: Halaman ini akan memanggil API `/api/get-pairing-code` secara otomatis.
3. **Display Code**: Merchant akan melihat **8-Digit Kode Unik** (misal: `ABC1-2345`).
4. **Input di HP**:
    - Merchant buka WhatsApp di HP Toko.
    - Masuk ke Perangkat Tertaut > Tautkan Perangkat.
    - Pilih opsi **"Tautkan dengan nomor telepon saja"**.
    - Masukkan Kode 8-Digit tersebut.
5. **Connected**: WAHA Plus akan mendeteksi koneksi dan sesi bot merchant aktif.

### 🤖 Tahap C: Pengoperasian
1. **Sapaan Awal**: Bot menyapa Merchant ("Halo Bos! Bot Toko [Nama] siap kerja!").
2. **Setup Menu**: Merchant menambahkan menu via chat (`/menu`).
3. **Customer Chat**: Pelanggan chat ke nomor toko, Bot AI (Gemini) menjawab.

---

## ⭐ 2. Fitur Utama

### 🏢 Untuk Merchant (Pemilik Toko)
*   **AI Auto-Reply**: Menjawab pertanyaan umum (jam buka, lokasi, stok) secara natural menggunakan Google Gemini Flash.
*   **Menu Manager**: Tambah/Hapus produk langsung dari chat.
    *   Command: `/menu [Nama Produk] [Harga]`
*   **Order Handling**: Mencatat pesanan dan menghitung total otomatis.
*   **Payment Validation**: AI Vision mengecek foto bukti transfer (Asli/Palsu/Nominal).
*   **Mass Broadcast**: Kirim pesan promo ke seluruh database pelanggan toko.
    *   Command: `/broadcast [Isi Pesan]`
*   **Human Handoff**: Bot otomatis diam jika mendeteksi percakapan butuh manusia atau perintah manual.

### 🛍️ Untuk Customer (Pelanggan)
*   **24/7 Service**: Jawaban instan jam berapapun.
*   **Catalogue Info**: Mendapatkan info lengkap produk tanpa menunggu.
*   **Easy Checkout**: Proses pemesanan dipandu langkah demi langkah.

### 🔧 Fitur Teknis (Backend)
*   **Multi-Tenancy**: Satu bot melayani banyak toko. Data tiap toko terisolasi berdasarkan Sesi WAHA.
*   **Stability**: Menggunakan **WAHA Plus** (SUMOPOD) yang lebih stabil dibanding library gratisan.
*   **Scalable**: Hosting di **Google Cloud Run** (Serverless), auto-scale sesuai traffic.

---

## 📚 3. Daftar Perintah (Commands)

### Perintah Pendaftaran (Public)
| Command | Fungsi |
| :--- | :--- |
| `/daftar` | Memulai proses pendaftaran baru (manual chat flow/backup). |
| `/ping` | Cek apakah bot online. |
| `/help` | Menampilkan bantuan umum. |

### Perintah Manajemen Toko (Owner Only)
*Hanya bisa diakses oleh nomor pemilik toko yang terdaftar.*

| Command | Deskripsi | Contoh |
| :--- | :--- | :--- |
| `/menu` | Menambah produk baru ke database toko. | `/menu Nasi Goreng 15000` |
| `/broadcast` | Kirim pesan massal ke semua pelanggan toko. | `/broadcast Promo Merdeka diskon 17%!` |
| `/gantinama` | Mengubah nama toko di sistem/invoice. | `/gantinama Bakso Mas Roy` |
| `/kode` | Meminta ulang Kode Pairing jika terputus. | `/kode` |
| `/scan` | (Alternatif) Meminta QR Code jika pairing code gagal. | `/scan` |
| `/unreg` | Menghapus seluruh data toko dan langganan (Reset). | `/unreg` |
| `/batal` | Membatalkan proses pendaftaran yang sedang berjalan. | `/batal` |

---

## ⚠️ 4. Troubleshooting Umum

**Masalah: Kode Pairing tidak muncul di halaman sukses.**
*   **Penyebab**: Sesi WAHA belum siap atau limit request.
*   **Solusi**:
    1. Refresh halaman sukses.
    2. Cek apakah pembayaran sudah berstatus `settlement`.
    3. Merchant bisa ketik `/kode` manual di chat bot utama.

**Masalah: Bot tidak balas chat pelanggan.**
*   **Penyebab**: Sesi terputus atau saldo Kuota AI habis.
*   **Solusi**:
    1. Owner ketik `/ping` ke nomor bot.
    2. Cek menu Perangkat Tertaut di HP Owner, pastikan status "Aktif".

**Masalah: Bukti transfer valid tapi ditolak.**
*   **Penyebab**: Foto buram atau format struk tidak dikenali AI.
*   **Solusi**: Konfirmasi manual oleh Owner, lalu tandai pesanan selesai.

---
*Dokumen ini akan diperbarui seiring penambahan fitur baru.*
