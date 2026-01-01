# Quick Database Column Check & Fix via Supabase
Write-Host "Checking if SQL migration ran successfully..." -ForegroundColor Cyan
Write-Host ""
Write-Host "If you see 'column does not exist' error in logs," -ForegroundColor Yellow
Write-Host "it means SQL didn't run or needs service restart." -ForegroundColor Yellow
Write-Host ""
Write-Host "SOLUTION:" -ForegroundColor Green
Write-Host ""
Write-Host "1. Go to Supabase Dashboard SQL Editor" -ForegroundColor White
Write-Host "2. Run this command to VERIFY columns exist:" -ForegroundColor White
Write-Host ""
Write-Host "SELECT column_name FROM information_schema.columns WHERE table_name = 'customer';" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. If 'last_interaction' NOT in list, run migration again:" -ForegroundColor White
Write-Host ""
Write-Host @"
ALTER TABLE customer ADD COLUMN IF NOT EXISTS last_interaction TIMESTAMP DEFAULT NOW();
ALTER TABLE customer ADD COLUMN IF NOT EXISTS followup_status VARCHAR(20) DEFAULT 'NONE';
ALTER TABLE customer ADD COLUMN IF NOT EXISTS last_context TEXT DEFAULT '';
"@ -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Restart Cloud Run service to clear cache:" -ForegroundColor White
Write-Host ""
Write-Host "gcloud run services update saas-bot --region asia-southeast2 --no-traffic --tag=test" -ForegroundColor Cyan
Write-Host "gcloud run services update-traffic saas-bot --region asia-southeast2 --to-latest" -ForegroundColor Cyan
Write-Host ""
Write-Host "OR simpler:" -ForegroundColor Yellow
Write-Host "Just trigger new request after SQL runs - Cloud Run will reload." -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ADDITIONAL ISSUE FOUND:" -ForegroundColor Red
Write-Host "WAHA API returning 401 Unauthorized" -ForegroundColor Red
Write-Host ""
Write-Host "This means SUMOPOD API key might be wrong or session changed." -ForegroundColor Yellow
Write-Host "Check WAHA_API_KEY in Cloud Run environment variables." -ForegroundColor Yellow
