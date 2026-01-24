# Emergency Rollback Script
# Reverts to previous Cloud Run revision

param(
    [string]$ServiceName = "saas-bot",
    [string]$Region = "asia-southeast2",
    [string]$Revision = ""  # Leave empty to auto-select previous
)

Write-Host "🔄 EMERGENCY ROLLBACK INITIATED" -ForegroundColor Yellow
Write-Host ""

# Get current and previous revisions
Write-Host "Fetching deployment history..."
$revisions = gcloud run revisions list --service=$ServiceName --region=$Region --format="value(name)" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to fetch revisions" -ForegroundColor Red
    exit 1
}

$revisionList = $revisions -split "`n" | Where-Object { $_ -match '\S' }

if ($revisionList.Count -lt 2) {
    Write-Host "❌ No previous revision found to rollback to" -ForegroundColor Red
    exit 1
}

$currentRevision = $revisionList[0]
$previousRevision = if ($Revision) { $Revision } else { $revisionList[1] }

Write-Host "Current:  $currentRevision" -ForegroundColor Cyan
Write-Host "Rollback: $previousRevision" -ForegroundColor Green
Write-Host ""

# Confirm rollback
$confirm = Read-Host "Proceed with rollback? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "❌ Rollback cancelled" -ForegroundColor Yellow
    exit 0
}

# Execute rollback
Write-Host ""
Write-Host "⏳ Rolling back to $previousRevision..."

gcloud run services update-traffic $ServiceName `
    --region=$Region `
    --to-revisions="$previousRevision=100"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ ROLLBACK SUCCESSFUL" -ForegroundColor Green
    Write-Host "Service URL: https://$ServiceName-$Region.run.app"
    Write-Host ""
    Write-Host "⚠️  REMEMBER TO:" -ForegroundColor Yellow
    Write-Host "1. Verify service is working"
    Write-Host "2. Check logs for errors"
    Write-Host "3. Investigate root cause"
}
else {
    Write-Host ""
    Write-Host "❌ ROLLBACK FAILED" -ForegroundColor Red
    Write-Host "Manual intervention required!"
    exit 1
}
