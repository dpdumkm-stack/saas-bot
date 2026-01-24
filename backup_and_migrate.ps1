# Database Migration Script with Backup
# Usage: .\backup_and_migrate.ps1 migrations\001_add_column.sql

param(
    [Parameter(Mandatory = $true)]
    [string]$MigrationFile
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  🗄️ DATABASE MIGRATION SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validate migration file exists
if (-not (Test-Path $MigrationFile)) {
    Write-Host "❌ Migration file not found: $MigrationFile" -ForegroundColor Red
    exit 1
}

Write-Host "📄 Migration file: $MigrationFile" -ForegroundColor White
Write-Host ""

# 1. Create backup point
Write-Host "[Step 1/4] 📸 Creating backup point..." -ForegroundColor Yellow

$backup_timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "✅ Backup timestamp: $backup_timestamp" -ForegroundColor Green
Write-Host "   (Neon keeps automatic point-in-time backups)" -ForegroundColor Gray
Write-Host ""

# 2. Show migration SQL
Write-Host "[Step 2/4] 📋 Migration SQL Preview:" -ForegroundColor Yellow
Write-Host "---" -ForegroundColor Gray
$migration_sql = Get-Content $MigrationFile -Raw
Write-Host $migration_sql -ForegroundColor Cyan
Write-Host "---" -ForegroundColor Gray
Write-Host ""

# 3. Confirm execution
$confirm = Read-Host "Execute this migration on PRODUCTION? (y/n)"

if ($confirm -ne "y") {
    Write-Host "Migration cancelled by user." -ForegroundColor Yellow
    exit 0
}

Write-Host ""

# 4. Run migration
Write-Host "[Step 3/4] ⚙️ Executing migration..." -ForegroundColor Yellow

# Check if run_migration.py exists
if (-not (Test-Path "run_migration.py")) {
    # Create run_migration.py if it doesn't exist
    Write-Host "Creating run_migration.py helper..." -ForegroundColor Gray
    
    $migration_runner = @"
import sys
import os
from app.extensions import db
from app import create_app

if len(sys.argv) < 2:
    print("Usage: python run_migration.py <migration_file>")
    sys.exit(1)

migration_file = sys.argv[1]

if not os.path.exists(migration_file):
    print(f"Error: {migration_file} not found")
    sys.exit(1)

app = create_app()

with app.app_context():
    try:
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        print(f"Executing migration: {migration_file}")
        db.session.execute(sql)
        db.session.commit()
        
        print("✅ Migration successful!")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
"@
    
    Set-Content -Path "run_migration.py" -Value $migration_runner
}

# Add bot directory to path
$env:PYTHONPATH = Join-Path $PSScriptRoot "bot"

python run_migration.py $MigrationFile

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Migration FAILED!" -ForegroundColor Red
    Write-Host "Database is unchanged (transaction rolled back)." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To restore from backup (if needed):" -ForegroundColor Yellow
    Write-Host "1. Go to: https://console.neon.tech" -ForegroundColor Gray
    Write-Host "2. Select database → Restore" -ForegroundColor Gray
    Write-Host "3. Choose time: $backup_timestamp" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "✅ Migration executed successfully!" -ForegroundColor Green
Write-Host ""

# 5. Verify schema (optional)
Write-Host "[Step 4/4] 🔍 Verification..." -ForegroundColor Yellow
Write-Host "Migration complete. Recommended next steps:" -ForegroundColor White
Write-Host "1. Verify schema manually via database console" -ForegroundColor Gray
Write-Host "2. Monitor application for errors (15 minutes)" -ForegroundColor Gray
Write-Host "3. Deploy new code that uses migrated schema" -ForegroundColor Gray
Write-Host ""

# Success
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ MIGRATION SUCCESSFUL!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Backup reference: $backup_timestamp" -ForegroundColor White
Write-Host "🔄 Rollback: https://console.neon.tech (restore to backup time)" -ForegroundColor Yellow
Write-Host ""
