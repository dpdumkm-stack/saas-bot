---
description: Debugging Menyeluruh & Tuntas (Zero Downtime + Protocol Zero Error)
---

1.  **🛡️ Shielded Scope & Safety (Protocol Zero Error Check)**:
    -   **Non-Destructive Check**: Pastikan TIDAK ada penghapusan data/tabel saat debug. READ-ONLY lebih diutamakan.
    -   **Dependency Scan**: Cek variabel/import yang hilang sebelum inject script debug.
    -   **Isolation**: Pastikan script debug hanya berdampak pada `toko_id` test atau dummy data.
    -   **Reversibility**: Siapkan rencana rollback instan jika script debug menyebabkan load tinggi.
    -   **Backup Plan**: Jika harus merubah state DB, WAJIB backup dulu.

2.  **🧪 Reproduction & Hypothesis (Scientific Method)**:
    -   **Reproduce Locally**: Coba reproduksi issue di environment local jika memungkinkan.
    -   **Isolated Test**: Buat script test terpisah (e.g. `tests/debug_issue.py`) untuk memvalidasi bug tanpa mengganggu user lain.
    -   **Formulate Hypothesis**: Tuliskan hipotesis penyebab masalah sebelum mulai coding ("Saya menduga X terjadi karena Y").

3.  **🧠 Surgical Implementation (Mode Bedah)**:
    -   **Minimal Touch**: Ubah hanya baris yang perlu. Jangan overwrite file penuh.
    -   **Preserve Logic**: Pastikan fitur existing (Anti-Spam, Validation, Security) TIDAK terhapus.
    -   **Logs Injection**: Tambahkan logs (`logging.info/error`) yang informatif.

4.  **✅ Verification & Deploy**:
    -   **Local Mock**: Test script fix secara lokal sebelum deploy.
    -   **Deploy**: Jalankan `deploy_to_cloudrun.ps1` (jika fix memerlukan update kode).
    -   **Health Check**: Verifikasi endpoint/fitur aktif setelah deploy/patch.

5.  **📝 Reporting & Documentation**:
    -   **Root Cause Analysis (RCA)**: Jelaskan KENAPA bug terjadi (teknis).
    -   **Action Taken**: Jelaskan APA yang diubah.
    -   **Future Prevention**: Sarankan cara mencegah bug serupa.
    -   **Update Roadmap**: Catat perbaikan di ROADMAP.md (Section Debugging/Bugfix).

// turbo-all
