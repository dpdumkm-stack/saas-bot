# SaaS Bot - WhatsApp Automation for UMKM

Bot otomatis WhatsApp untuk manajemen langganan UMKM, diintegrasikan dengan Google Gemini AI.

## Arsitektur Saat Ini

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   WhatsApp      │ ◄─────► │  WAHA Plus       │ ◄─────► │   Cloud Run     │
│   (End Users)   │         │  (SUMOPOD)       │         │   (Bot API)     │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                   webhook                         │
                                                                   │
                                                          ┌────────▼────────┐
                                                          │  Google Gemini  │
                                                          │      AI         │
                                                          └─────────────────┘
```

### Komponen
- **Bot Application**: Flask app di Google Cloud Run (asia-southeast2)
- **WhatsApp API**: WAHA Plus (hosted by SUMOPOD)
- **AI Engine**: Google Gemini API
- **Database**: PostgreSQL (Cloud SQL) atau SQLite lokal

## Quick Start

### 1. Deploy ke Cloud Run

```powershell
# Pastikan sudah login ke Google Cloud
gcloud auth login

# Set project
gcloud config set project gen-lang-client-0887245898

# Deploy
.\deploy_to_cloudrun.ps1
```

Service URL akan ditampilkan setelah deployment berhasil.

### 2. Konfigurasi Webhook SUMOPOD

Jalankan script untuk update webhook:

```powershell
.\update_sumopod_webhook.ps1
```

Script akan meminta API key SUMOPOD dan otomatis mengonfigurasi webhook.

**Manual Setup**: Lihat panduan lengkap di [`SUMOPOD_WEBHOOK_SETUP.md`](SUMOPOD_WEBHOOK_SETUP.md)

### 3. Environment Variables

Set di Cloud Run atau file `.env`:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here
SUPER_ADMIN_WA=6281234567890@c.us
WAHA_API_KEY=your_sumopod_api_key

# Optional (sudah ada default)
WAHA_BASE_URL=https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id
DATABASE_URL=postgresql://user:pass@host/db
```

Update di Cloud Run:
```powershell
gcloud run services update saas-bot --region asia-southeast2 \
  --update-env-vars GEMINI_API_KEY=xxx,WAHA_API_KEY=yyy
```

## Testing

Kirim pesan WhatsApp ke nomor yang terdaftar di SUMOPOD:

```
/ping
```

Bot harus merespons dengan status dan informasi sistem.

## Monitoring Logs

```powershell
# Latest logs
gcloud run logs read saas-bot --region asia-southeast2 --limit 20

# Follow logs (real-time)
gcloud run logs tail saas-bot --region asia-southeast2
```

## Struktur Project

```
saas_bot/
├── bot/                          # Core bot application
│   ├── app/                      # Flask app
│   │   ├── routes/              # API routes (webhook, admin, api)
│   │   ├── services/            # Services (WAHA, Gemini, store)
│   │   ├── models/              # Database models
│   │   └── config.py            # Configuration
│   └── requirements.txt         # Python dependencies
├── Dockerfile                    # Cloud Run container
├── deploy_to_cloudrun.ps1       # Deployment script
├── update_sumopod_webhook.ps1   # Webhook configuration
└── SUMOPOD_WEBHOOK_SETUP.md     # Setup documentation
```

## Commands

Bot mendukung command berikut (via WhatsApp):

- `/ping` - Cek status bot
- `/daftar` - Registrasi toko baru
- `/status` - Cek status langganan
- `/help` - Bantuan

## Development

### Local Testing

```powershell
cd saas_bot
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r bot\requirements.txt
python -m bot.app
```

### Test Webhook Locally

```powershell
python test_webhook.py
```

## Troubleshooting

### Bot tidak merespons

1. Cek webhook di SUMOPOD sudah benar
2. Cek logs Cloud Run untuk error
3. Verify WAHA session status

### Webhook Error

```powershell
# Verify webhook config
.\update_sumopod_webhook.ps1
```

### Cloud Run Error

```powershell
# Check service status
gcloud run services describe saas-bot --region asia-southeast2

# View recent errors  
gcloud run logs read saas-bot --region asia-southeast2 --limit 50
```

## Support

- WAHA Documentation: https://waha.devlike.pro
- SUMOPOD Support: (contact SUMOPOD)
- Google Cloud Run Docs: https://cloud.google.com/run/docs
