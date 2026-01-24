---
description: Eksekusi Aman dengan "Protocol Zero Error" (Validasi Safety, Backup, Eksekusi, Deploy)
---

1.  **🛡️ Pre-Flight Safety Protocol (Wajib Sebelum Coding)**:
    -   **Non-Destructive Check**: Pastikan TIDAK ada penghapusan data/tabel (Add-Only). Jika harus hapus, WAJIB buat script backup dulum.
    -   **Dependency Scan**: Cek variabel/import yang hilang (Mencegah `UnboundLocalError`).
    -   **Isolation**: Pastikan perubahan tidak bocor ke tenant/merchant lain (`toko_id` filter).
    -   **Reversibility**: Pikirkan "Jika ini gagal, bagaimana cara undo dalam 1 menit?".

2.  **🧠 Surgical Implementation (Mode Bedah)**:
    -   **Minimal Touch**: Gunakan `replace_file_content` hanya pada blok yang relevan. Jangan overwrite file penuh jika tidak perlu.
    -   **Conserve Logic**: Pastikan validasi/security existing tidak terhapus saat edit.

3.  **✅ Verification & Deploy**:
    -   **Local Mock**: Jika memungkinkan, test logic secara lokal (script python simpel) sebelum deploy.
    -   **Deploy**: Jalankan `deploy_to_cloudrun.ps1`.
    -   **Health Check**: Verifikasi endpoint/fitur aktif setelah deploy.

4.  **📝 Reporting**:
    -   Konfirmasi status ke user (Sukses/Gagal + RCA jika ada error).
    -   Update `ROADMAP.md` dengan status terbaru.
    -   jika melakukan debuging, laukan dengan menyeluruh dan tuntas dan zero downtime

// turbo-all