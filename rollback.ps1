# Quick Rollback Script
# Usage: .\rollback.ps1

Write-Host "========================================" -ForegroundColor Red
Write-Host "  🔄 EMERGENCY ROLLBACK" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""

# Get list of recent revisions
Write-Host "📋 Fetching recent revisions..." -ForegroundColor Yellow
Write-Host ""

$revisions = gcloud run revisions list `
    --service=saas-bot `
    --region=asia-southeast2 `
    --limit=5 `
    --format="table(name,status,deployed)" 2>$null

if (-not $revisions) {
    Write-Host "❌ Could not fetch revisions!" -ForegroundColor Red
    exit 1
}

Write-Host $revisions
Write-Host ""

# Get current traffic distribution
Write-Host "🚦 Current traffic distribution:" -ForegroundColor Yellow
$current_traffic = gcloud run services describe saas-bot `
    --region=asia-southeast2 `
    --format="value(status.traffic)" 2>$null

Write-Host $current_traffic
Write-Host ""

# Prompt for revision to rollback to
Write-Host "Select revision number (1 = most recent, 2 = previous, etc):" -ForegroundColor Cyan
$selection = Read-Host "Enter number"

if (-not $selection -or $selection -notmatch '^\d+$') {
    Write-Host "Invalid selection" -ForegroundColor Red
    exit 1
}

# Get the selected revision name
$revision_list = gcloud run revisions list `
    --service=saas-bot `
    --region=asia-southeast2 `
    --limit=$selection `
    --format="value(name)" 2>$null

$target_revision = ($revision_list -split "`n")[-1]

if (-not $target_revision) {
    Write-Host "❌ Could not find revision!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎯 Target revision: $target_revision" -ForegroundColor Green
Write-Host ""

# Confirm rollback
Write-Host "⚠️  This will rollback production to: $target_revision" -ForegroundColor Yellow
$confirm = Read-Host "Continue? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "Rollback cancelled" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "🔄 Rolling back..." -ForegroundColor Yellow

gcloud run services update-traffic saas-bot `
    --to-revisions="$target_revision=100" `
    --region=asia-southeast2

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✅ ROLLBACK SUCCESSFUL!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service restored to: $target_revision" -ForegroundColor White
    Write-Host "URL: https://saas-bot-643221888510.asia-southeast2.run.app" -ForegroundColor White
    Write-Host ""
    Write-Host "Verify service is working correctly." -ForegroundColor Yellow
}
else {
    Write-Host ""
    Write-Host "❌ ROLLBACK FAILED!" -ForegroundColor Red
    Write-Host "Check error messages above." -ForegroundColor Yellow
}
