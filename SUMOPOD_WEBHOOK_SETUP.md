# SUMOPOD WAHA Webhook Configuration

## Current Status
- ✅ Cloud Run deployed: `https://saas-bot-643221888510.asia-southeast2.run.app`
- ⚠️ Webhook needs to be configured in SUMOPOD
- ❌ API update failed (401 Unauthorized - API key issue)

## Webhook URL yang Perlu Diset
```
https://saas-bot-643221888510.asia-southeast2.run.app/webhook
```

## Setup Otomatis (RECOMMENDED)
Script ini akn mengkonfigurasi Cloud Run dan Webhook SUMOPOD sekaligus dengan aman.

1.  **Jalankan Script**:
    ```powershell
    .\setup_sumopod_secure.ps1
    ```
2.  **Masukkan API Key**: Paste API Key SUMOPOD Anda saat diminta (input akan tersembunyi).
3.  **Ikuti Prompt**: Pilih `Y` untuk update Cloud Run dan `Y` untuk set Webhook.

---

## Option 1: Via SUMOPOD Dashboard (Manual)

Karena Anda menggunakan layanan SUMOPOD, cara termudah adalah via dashboard mereka:

1. **Buka SUMOPOD Dashboard**
   - URL: `https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id/dashboard`
   - Login dengan kredensial SUMOPOD Anda

2. **Cari Webhook Settings**
   - Biasanya di menu Session atau Configuration
   - Cari field untuk Webhook URL

3. **Set Webhook URL**
   - Masukkan: `https://saas-bot-643221888510.asia-southeast2.run.app/webhook`
   - Events: pilih `message` dan `session.status` (jika ada option)

4. **Save dan Restart Session** (jika diperlukan)

---

## Option 2: Via API (Jika Punya API Key yang Benar)

Jika Anda punya API key yang benar dari SUMOPOD:

### PowerShell Command:
```powershell
$API_KEY = "YOUR_SUMOPOD_API_KEY_HERE"  # Ganti dengan API key dari SUMOPOD
$WEBHOOK_URL = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"

$body = @{
    config = @{
        webhook = @{
            url = $WEBHOOK_URL
            events = @("message", "session.status")
        }
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id/api/sessions/default" `
    -Method Patch `
    -Headers @{
        "X-Api-Key" = $API_KEY
        "Content-Type" = "application/json"
    } `
    -Body $body
```

### Bash/curl Command:
```bash
curl -X PATCH 'https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id/api/sessions/default' \
  -H 'X-Api-Key: YOUR_SUMOPOD_API_KEY_HERE' \
  -H 'Content-Type: application/json' \
  -d '{
    "config": {
      "webhook": {
        "url": "https://saas-bot-643221888510.asia-southeast2.run.app/webhook",
        "events": ["message", "session.status"]
      }
    }
  }'
```

---

## Option 3: Tanya SUMOPOD Support

Jika dashboard tidak ada opsi webhook atau API key tidak tersedia:

1. Contact SUMOPOD support
2. Berikan mereka webhook URL: `https://saas-bot-643221888510.asia-southeast2.run.app/webhook`
3. Minta mereka untuk set webhook untuk session Anda

---

## Verifikasi Webhook Berhasil

Setelah webhook di-set, test dengan:

1. **Kirim pesan WhatsApp**: `/ping`
2. **Check Cloud Run logs**:
   ```powershell
   gcloud run logs read saas-bot --region asia-southeast2 --limit 20
   ```
3. **Check apakah bot merespons**

---

## Informasi Penting

- **SUMOPOD URL**: `https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id`
- **Session Name**: `default` (atau sesuai yang Anda gunakan)
- **Webhook URL**: `https://saas-bot-643221888510.asia-southeast2.run.app/webhook`
- **Bot Service**: Cloud Run (asia-southeast2)

---

## Next Steps

1. Set webhook via salah satu option di atas
2. Test bot dengan mengirim `/ping` via WhatsApp
3. Jika ada masalah, check logs di Cloud Run
