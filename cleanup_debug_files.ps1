$FilesToDelete = @(
    "investigate_broadcast_status.py",
    "trigger_live_test.py",
    "debug_job_43.py",
    "verify_runtime.py",
    "migrate_broadcast_tables.py"
)

Write-Host "🧹 Starting Safe Cleanup (Debug Files Only)..." -ForegroundColor Cyan

$deletedCount = 0
foreach ($file in $FilesToDelete) {
    if (Test-Path $file) {
        Remove-Item -Path $file -Force -ErrorAction SilentlyContinue
        Write-Host "  ✅ Deleted: $file" -ForegroundColor Gray
        $deletedCount++
    }
}

Write-Host "`n✨ Cleanup Complete. Removed $deletedCount files." -ForegroundColor Green
Write-Host "⚠️  Note: Database was NOT touched to preserve production data." -ForegroundColor Yellow
