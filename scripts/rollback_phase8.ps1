# Phase 8 Migration Rollback Script
# Use this to undo Phase 8 table creation if needed

Write-Host "============================================" -ForegroundColor Yellow
Write-Host "  Phase 8 Rollback Script" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Yellow
Write-Host ""

Write-Host "⚠️  WARNING: This will DELETE the following tables:" -ForegroundColor Red
Write-Host "   - broadcast_blacklist" -ForegroundColor Red
Write-Host "   - scheduled_broadcast" -ForegroundColor Red
Write-Host "   - broadcast_template" -ForegroundColor Red
Write-Host ""

$confirmation = Read-Host "Type 'DELETE' to confirm rollback"

if ($confirmation -ne "DELETE") {
    Write-Host "❌ Rollback cancelled" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Executing rollback..." -ForegroundColor Yellow

python -c @"
from app import app, db

with app.app_context():
    try:
        # Drop tables in reverse order (to handle foreign keys)
        db.session.execute(db.text('DROP TABLE IF EXISTS broadcast_template CASCADE'))
        db.session.execute(db.text('DROP TABLE IF EXISTS scheduled_broadcast CASCADE'))
        db.session.execute(db.text('DROP TABLE IF EXISTS broadcast_blacklist CASCADE'))
        db.session.commit()
        
        print('✅ Rollback successful')
        print('Tables dropped: broadcast_blacklist, scheduled_broadcast, broadcast_template')
    except Exception as e:
        print(f'❌ Rollback failed: {e}')
        db.session.rollback()
"@

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  Rollback Complete" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "❌ Rollback failed! Check errors above." -ForegroundColor Red
}
