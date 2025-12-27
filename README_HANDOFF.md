# Handoff Notes

## Current Setup (December 2025)

### Architecture
- **Bot Platform**: Google Cloud Run (asia-southeast2 - Jakarta)
- **WhatsApp API**: WAHA Plus hosted by SUMOPOD
- **AI**: Google Gemini API
- **Project**: UMKM TANGSEL (gen-lang-client-0887245898)

### Service URLs
- **Bot**: https://saas-bot-643221888510.asia-southeast2.run.app
- **Webhook**: https://saas-bot-643221888510.asia-southeast2.run.app/webhook
- **SUMOPOD WAHA**: https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id

### Key Scripts
- `deploy_to_cloudrun.ps1` - Deploy bot to Cloud Run
- `update_sumopod_webhook.ps1` - Configure SUMOPOD webhook
- `SUMOPOD_WEBHOOK_SETUP.md` - Complete setup guide

### Environment Variables Needed
- `GEMINI_API_KEY` - Google Gemini API key
- `WAHA_API_KEY` - SUMOPOD API key
- `SUPER_ADMIN_WA` - Admin WhatsApp number
- `DATABASE_URL` - PostgreSQL connection (optional, defaults to SQLite)

### Migration History
1. ❌ VPS IDCloudHost + Local WAHA (deprecated)
2. ❌ WuzAPI (deprecated)
3. ❌ Aldino Go-Whatsapp (deprecated)
4. ✅ **Current**: SUMOPOD WAHA Plus + Cloud Run

### Notes
- All legacy scripts removed (VPS, WuzAPI, Aldino)
- Project cleaned to only SUMOPOD + Cloud Run files
- Webhook must be configured in SUMOPOD to point to Cloud Run
- Bot responds to `/ping`, `/daftar`, `/status`, `/help`
