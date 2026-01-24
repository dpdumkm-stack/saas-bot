# Gemini Monitoring Setup Guide

## 🤖 Gemini API Monitoring

### 1. Manual Health Check

**Test Gemini connectivity:**
```powershell
python test_gemini_health.py
```

**Expected output:**
```
✅ GEMINI API WORKING!
```

**If error:**
- Check API key in `.env`
- Check quota: https://aistudio.google.com/app/apikey
- Verify network connection

---

### 2. Automatic Error Monitoring

**Already enabled!** Gemini failures automatically:
- ✅ Log to Cloud Logging
- ✅ Track error count (5 failures in 5 mins = alert)
- ✅ Send WhatsApp alert to admin (SUPER_ADMIN_WA)

**Location:** `bot/app/routes/webhook.py:305-330`

**Alert message:**
```
🚨 ALERT: GEMINI_FAILURE

Error terjadi 5x dalam 5 menit!

Details: Failed for toko 628xxx: [error details]

Check logs: https://console.cloud.google.com/logs
```

---

### 3. Fallback Behavior

**When Gemini is down, bot will:**
- ✅ Still reply to customers (not silent)
- ✅ Use contextual fallback messages:
  - Quota exceeded → "Sistem sedang ramai sekali 😅"
  - Auth error → "Ada gangguan teknis, tim sudah diberitahu"
  - Generic error → "Ada gangguan teknis sebentar ya kak 🙏"

**Customer doesn't see:**
- ❌ Technical error messages
- ❌ Silent failures
- ❌ Stack traces

---

### 4. Cloud Monitoring Alert (Optional)

**Setup custom alert for Gemini failures:**

1. Go to: https://console.cloud.google.com/monitoring/alerting

2. Create Policy:
   ```yaml
   Condition Type: Log match
   
   Filter:
     resource.type="cloud_run_revision"
     textPayload=~"GEMINI_FAILURE"
   
   Threshold: > 5 matches in 5 minutes
   
   Notification: your-email@gmail.com
   ```

---

### 5. Quota Monitoring

**Check Gemini quota usage:**
1. Go to: https://aistudio.google.com/app/apikey
2. Click on your API key
3. View "Usage" metrics

**Free tier limits:**
- 15 requests/minute
- 1,500 requests/day
- 1 million tokens/day

**Upgrade if needed:**
- Pay-per-use: $0.00025/1K chars (very cheap)
- No monthly fee

---

### 6. Common Gemini Issues

#### Issue 1: Quota Exceeded
**Symptom:** "Quota exceeded" or "Rate limit"

**Fix:**
- Wait 1 minute (resets per minute)
- Or upgrade to pay-as-you-go
- Or reduce traffic

#### Issue 2: API Key Invalid
**Symptom:** "API key invalid" or "Authentication failed"

**Fix:**
```powershell
# Check .env file
cat .env | Select-String "GEMINI"

# Update API key
# Get new key from: https://aistudio.google.com/app/apikey
```

#### Issue 3: Model Not Found
**Symptom:** "Model not found"

**Fix:**
- Check model name in `.env`
- Use: `gemini-1.5-flash` (recommended)
- Or: `gemini-1.5-pro` (slower, more capable)

---

### 7. Testing After Deployment

**Verify Gemini working in production:**

1. Send test message via WhatsApp to bot
2. Check response is AI-generated (not fallback)
3. Check logs for any errors:
   ```powershell
   gcloud logging read "GEMINI" --limit=20
   ```

---

### 8. Emergency Fallback (If Gemini Down Long-Term)

**Option 1: Use Claude/GPT-4 (requires code change)**
- Replace `get_gemini_response()` with OpenAI API
- ~1 hour effort

**Option 2: Use pre-defined responses**
- Create FAQ database
- Match keywords → canned responses
- ~2 hours effort

**Option 3: Disable AI, manual mode**
- Forward all messages to owner
- Quick fix, low quality

**For now:** Gemini is very reliable (99.9% uptime), jadi tidak perlu panic plan.

---

## ✅ Quick Checklist

Before production:
- [ ] Run `python test_gemini_health.py` - should PASS
- [ ] Verify GEMINI_API_KEY in `.env`
- [ ] Verify quota not exceeded
- [ ] Test fallback message (disconnect internet, send message)

After production:
- [ ] Monitor Cloud Logs for GEMINI_FAILURE
- [ ] Check admin WhatsApp for alerts
- [ ] Review quota usage weekly

---

**Status:** 🟢 Gemini monitoring FULLY AUTOMATED!
