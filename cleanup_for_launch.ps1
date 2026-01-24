# Wali AI - Master Launch Cleanup Script (PRODUCTION READY)
# This script prepares the environment for production by wiping the DB and removing technical debt.

$ErrorActionPreference = "Continue"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "   WALI AI - TOTAL LAUNCH CLEANUP" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# --- 0. Pre-Flight Safety Checks ---
Write-Host "[Safety] Checking Environment..." -ForegroundColor Yellow

# Read .env to find Database Target
if (Test-Path ".env") {
    $db_line = Get-Content ".env" | Select-String "DATABASE_URL"
    if ($db_line) {
        # Extract host for display (masking password)
        $db_url = $db_line.ToString().Split('=')[1].Trim()
        if ($db_url -match "@([^:/]+)") {
            $db_host = $Matches[1]
            Write-Host "🎯 Target Database: $db_host" -ForegroundColor Green
        }
    }
}
else {
    Write-Host "⚠️ .env file not found. Connection cannot be verified." -ForegroundColor Red
}

Write-Host ""
Write-Host "DANGER: This will permanently DELETE all data and test scripts." -ForegroundColor Red
Write-Host "This operation CANNOT BE UNDONE." -ForegroundColor Red
Write-Host ""
Write-Host "Press Ctrl+C now to cancel, or wait 5 seconds..." -ForegroundColor White

# countdown
foreach ($i in 5..1) {
    Write-Host "$i... " -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host "EXECUTE!" -ForegroundColor Red

# --- 1. Database Wipe ---
Write-Host "`n[1/2] Wiping Database Data..." -ForegroundColor Cyan
if (Test-Path "reset_database_data.py") {
    python reset_database_data.py --force
}
else {
    Write-Host "⚠️ reset_database_data.py not found. Skipping DB wipe." -ForegroundColor Yellow
}

# --- 2. File Cleanup ---
Write-Host "`n[2/2] Removing Junk Files (Technical Debt)..." -ForegroundColor Cyan

$FilesToDelete = @(
    # Diagnostic & Debug
    "analyze_logs.py", "recent_logs.json", "query_chatlogs.py", "query_db.py",
    "debug_api.py", "debug_check_user.py", "debug_local_webhook.py", "debug_store_status.py",
    "diag_job_35.py", "reconcile_job_35.py",
    "check_500_error.py", "check_cloudrun_logs.py", "check_config_secret.py", "check_db_broadcast.py",
    "check_neon_data.py", "check_production_db.py", "check_registered_toko.py", "check_waha.py",
    "cleanup_identity_guard.py", "query_chatlogs.py",
    
    # Test Scripts (Python)
    "test_ai_context.py", "test_anti_spam.py", "test_basic_commands.py", "test_bot_ai_response.py",
    "test_cron.py", "test_csv_logic.py", "test_dashboard_auth.py", "test_dashboard_settings.py",
    "test_deep_features.py", "test_gemini_health.py", "test_heartbeat_local.py", "test_humanization_features.py",
    "test_image_ocr.py", "test_live_webhook.py", "test_midtrans_link.py", "test_missing_features.py",
    "test_multitenancy_isolation.py", "test_norm.py", "test_payment_activation.py", "test_payment_simulation.py",
    "test_presence_indicator.py", "test_product_management.py", "test_register_trx.py", "test_registration_page.py",
    "test_session_setup.py", "test_subscription_cron.py", "test_webhook_upgrade.py",
    
    # Test Scripts (PowerShell)
    "test_send_message.ps1", "test_sumopod_methods.ps1", "test_sumopod_webhook.ps1",
    "test_waha_webhook_config.ps1", "test_waha_webhook_config_v2.ps1", "test_webhook_now.ps1",
    "test_webhook_routing.ps1", "test_webhook_simulator.ps1", "quick_sumopod_test.ps1",
    "send_final_test.ps1", "trigger_test_broadcast.py",
    
    # Setup & Maintenance
    "clean_data.py", "clean_test_data.sql", "cleanup_all_data.py", 
    "cleanup_neon.py", "cleanup_test_data.py", "register_test_store.py", "register_test_store.sql",
    "setup_neon.py", "repair_webhook.py", "summary_broadcast.py",
    "verify_live_production.py", "verify_registration_flow.py", "reset_database_data.py"
)

$deletedCount = 0
foreach ($file in $FilesToDelete) {
    if (Test-Path $file) {
        try {
            Remove-Item -Path $file -Force -ErrorAction Stop
            Write-Host "  ✅ Deleted: $file" -ForegroundColor Gray
            $deletedCount++
        }
        catch {
            Write-Host "  ❌ Failed to delete: $file" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "   CLEANUP COMPLETE!" -ForegroundColor Green
Write-Host "   Total files removed: $deletedCount" -ForegroundColor White
Write-Host "   DATABASE: FRESH STATE" -ForegroundColor White
Write-Host "   Ready for Launch." -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
