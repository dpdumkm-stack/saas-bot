# ================================================================================
# CRITICAL: SUMOPOD WEBHOOK NOT CONFIGURED
# ================================================================================

## PROBLEM IDENTIFIED:
Webhook SUMOPOD tidak aktif. Pesan /ping tidak sampai ke Cloud Run karena:
- Session config kosong (webhook URL tidak ter-set)
- SUMOPOD API tidak support set webhook via API
- Webhook HARUS di-set via Dashboard SUMOPOD

## SOLUTION: Set Webhook Via Dashboard

### Step-by-Step Instructions:

1. **Buka SUMOPOD Dashboard**
   URL: https://sumopod.my.id/dashboard
   (atau https://app.sumopod.my.id)

2. **Login dengan akun Anda**

3. **Pilih Instance/Project Anda**
   Instance ID: waha-2sl8ak8iil6s
   Region: sgp-kresna

4. **Cari Session yang WORKING**
   Session Name: session_01kdw5dvr5119e6bdxay5bkfqn
   Status: WORKING
   WhatsApp Number: +62 812-1940-0496

5. **Set Webhook Configuration**
   Lokasi biasanya di:
   - Settings > Webhook
   - atau Configuration > Webhook
   - atau Session Settings > Webhook

6. **Masukkan Data Webhook:**
   ```
   Webhook URL: https://saas-bot-643221888510.asia-southeast2.run.app/webhook
   
   Events (pilih):
   ☑ message
   ☑ session.status
   
   Method: POST
   Headers: (kosongkan, tidak perlu)
   ```

7. **Save dan Restart Session** (jika diminta)

8. **Verify**
   Kirim test message ke +62 812-1940-0496
   Kemudian check logs:
   ```powershell
   gcloud run services logs read saas-bot --region asia-southeast2 --limit 20
   ```

## ALTERNATIVE: Contact SUMOPOD Support

Jika dashboard tidak ada opsi webhook, contact SUMOPOD support:

**Email**: support@sumopod.my.id
**Message**:
```
Subject: Setup Webhook untuk Session

Halo SUMOPOD Team,

Saya perlu bantuan untuk set webhook pada instance saya:
- Instance: waha-2sl8ak8iil6s (sgp-kresna)
- Session: session_01kdw5dvr5119e6bdxay5bkfqn
- Webhook URL: https://saas-bot-643221888510.asia-southeast2.run.app/webhook
- Events: message, session.status

Mohon bantuannya untuk mengkonfigurasi webhook ini.

Terima kasih!
```

## VERIFICATION COMMAND

Setelah webhook di-set, verify dengan:
```powershell
# Send test message
# Lalu check logs
.\check_logs.ps1

# Atau manual
gcloud run services logs read saas-bot --region asia-southeast2 --limit 30
```

Harus muncul log "WEBHOOK RAW:" jika webhook berhasil.
