# 🚀 AUTOMATION TOOLS - Quick Reference

## 📋 Available Scripts

### 1. **safe_deploy.ps1** - Safe Production Deployment
**Usage:**
```powershell
.\safe_deploy.ps1
```

**What it does:**
- ✅ Backs up current revision (for rollback)
- ✅ Runs automated tests (test_register_trx, test_multitenancy, test_anti_spam)
- ✅ Asks for confirmation
- ✅ Deploys to Cloud Run
- ✅ Runs health check
- ✅ Auto-rollback if health check fails

**When to use:** Every production deployment

---

### 2. **backup_and_migrate.ps1** - Database Migration
**Usage:**
```powershell
.\backup_and_migrate.ps1 migrations\001_add_column.sql
```

**What it does:**
- ✅ Records backup timestamp (for Neon restore)
- ✅ Shows migration SQL preview
- ✅ Asks for confirmation
- ✅ Executes migration
- ✅ Provides rollback instructions if fails

**When to use:** Any database schema changes

**Example migration file:**
```sql
-- migrations/001_add_email_column.sql
ALTER TABLE toko ADD COLUMN email VARCHAR(255);
CREATE INDEX idx_toko_email ON toko(email);
```

---

### 3. **rollback.ps1** - Emergency Rollback
**Usage:**
```powershell
.\rollback.ps1
```

**What it does:**
- ✅ Shows last 5 revisions
- ✅ Shows current traffic distribution
- ✅ Lets you select which revision to rollback to
- ✅ Executes rollback

**When to use:** When production has critical issues

---

### 4. **cleanup_test_data.py** - Clean Test Data
**Usage:**
```powershell
python cleanup_test_data.py
```

**What it does:**
- ✅ Removes test stores (phone numbers starting with 628)
- ✅ Removes test subscriptions
- ✅ Removes stores with "test" in name
- ✅ Shows remaining data count

**When to use:** Before running tests to avoid data accumulation

---

## 🛡️ Error Monitoring (Automatic)

### ErrorMonitor Service
**Location:** `bot/app/services/error_monitoring.py`

**Usage in code:**
```python
from app.services.error_monitoring import ErrorMonitor

# Example 1: Gemini failure
try:
    response = get_gemini_response(...)
except Exception as e:
    ErrorMonitor.log_error("GEMINI_FAILURE", str(e), "CRITICAL")

# Example 2: Database error
try:
    db.session.commit()
except Exception as e:
    db.session.rollback()
    ErrorMonitor.log_error("DATABASE_ERROR", str(e), "CRITICAL")

# Example 3: WAHA error
try:
    kirim_waha(chat_id, message)
except Exception as e:
    ErrorMonitor.log_error("WAHA_ERROR", str(e), "ERROR")
```

**Features:**
- Tracks error count (5 errors in 5 minutes = alert)
- Sends WhatsApp alert to admin (SUPER_ADMIN_WA)
- Auto-resets counters hourly

**To enable auto-reset:**
Setup Cloud Scheduler (one-time):
```bash
gcloud scheduler jobs create http error-counter-reset \
  --schedule="0 * * * *" \
  --uri="https://saas-bot-643221888510.asia-southeast2.run.app/api/cron/hourly_cleanup?key=RahasiaNegara123" \
  --http-method=GET \
  --location=asia-southeast2
```

---

## 🏥 Health Check Endpoint

**URL:** `https://saas-bot-643221888510.asia-southeast2.run.app/api/health`

**Response (healthy):**
```json
{
  "timestamp": "2026-01-16T00:00:00",
  "status": "healthy",
  "checks": {
    "database": "OK",
    "waha": "OK"
  }
}
```

**Use for:**
- Automated monitoring (UptimeRobot, etc)
- Load balancer health checks
- Manual verification after deployment

---

## 📊 Monitoring Setup Checklist

### Essential (Do Now):
- [ ] Run `.\safe_deploy.ps1` for first production deployment
- [ ] Setup UptimeRobot monitoring on `/api/health`
- [ ] Setup Cloud Run error rate alert (via Cloud Console)
- [ ] Test rollback procedure (`.\rollback.ps1`)

### Week 1:
- [ ] Setup Cloud Scheduler for hourly cleanup
- [ ] Add ErrorMonitor to critical code paths
- [ ] Monitor logs daily

### Week 2+:
- [ ] Create custom dashboards (optional)
- [ ] Setup Slack/email alerts (optional)

---

## 🚨 Emergency Procedures

### If Deployment Fails:
```powershell
# Rollback immediately
.\rollback.ps1
```

### If Database Migration Fails:
1. Check error message (migration rolled back automatically)
2. Fix SQL file
3. Run again: `.\backup_and_migrate.ps1 migrations\fixed.sql`

### If Production Has Errors:
1. Check health: `https://saas-bot-643221888510.asia-southeast2.run.app/api/health`
2. View logs: `gcloud logging read "resource.type=cloud_run_revision" --limit=50`
3. If critical: `.\rollback.ps1`

---

## 📞 Support Resources

- **Cloud Console:** https://console.cloud.google.com/run
- **Logs:** https://console.cloud.google.com/logs
- **Database:** https://console.neon.tech
- **Status Page:** https://saas-bot-643221888510.asia-southeast2.run.app/status (create later)

---

## 🎯 Next Steps

1. **Test safe deployment:**
   ```powershell
   .\safe_deploy.ps1
   ```

2. **Setup external monitoring:**
   - UptimeRobot: https://uptimerobot.com
   - Monitor: /api/health endpoint

3. **Enable error alerts:**
   - Setup Cloud Scheduler (see above)

4. **Familiarize with rollback:**
   ```powershell
   .\rollback.ps1  # (test in non-critical time)
   ```

**Ready for production! 🚀**
