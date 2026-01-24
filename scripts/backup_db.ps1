# Database Backup Script
# Runs daily to backup PostgreSQL database

param(
    [string]$BackupDir = "backups",
    [switch]$UploadToCloud
)

# Load environment variables
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}

$DATABASE_URL = $env:DATABASE_URL
$DATE = Get-Date -Format "yyyy-MM-dd_HHmm"
$BACKUP_FILE = "$BackupDir/db_backup_$DATE.sql"

# Create backup directory if not exists
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

Write-Host "🔄 Starting database backup..."

try {
    # Backup using pg_dump (requires PostgreSQL client tools)
    # For Neon/remote PostgreSQL
    pg_dump $DATABASE_URL -f $BACKUP_FILE
    
    if ($LASTEXITCODE -eq 0) {
        $size = (Get-Item $BACKUP_FILE).Length / 1KB
        Write-Host "✅ Backup successful: $BACKUP_FILE ($([math]::Round($size, 2)) KB)"
        
        # Optional: Upload to Google Cloud Storage
        if ($UploadToCloud) {
            Write-Host "☁️  Uploading to Google Cloud Storage..."
            gsutil cp $BACKUP_FILE gs://saas-bot-backups/
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Cloud backup successful"
            }
            else {
                Write-Host "⚠️  Cloud upload failed"
            }
        }
        
        # Keep only last 7 backups (save space)
        Get-ChildItem $BackupDir -Filter "db_backup_*.sql" | 
        Sort-Object LastWriteTime -Descending | 
        Select-Object -Skip 7 | 
        Remove-Item -Force
        
        Write-Host "✅ Cleanup complete (kept last 7 backups)"
    }
    else {
        Write-Host "❌ Backup failed with exit code: $LASTEXITCODE"
        exit 1
    }
}
catch {
    Write-Host "❌ Backup error: $_"
    exit 1
}
