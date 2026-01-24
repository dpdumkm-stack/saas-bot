# Update Cloud Run Environment Variables Only
# Project: UMKM TANGSEL (gen-lang-client-0887245898)

$SERVICE_NAME = "saas-bot"
$REGION = "asia-southeast2"
$PROJECT_ID = "gen-lang-client-0887245898"

# Fix for gcloud python location (Copied from deploy script)
$env:CLOUDSDK_PYTHON = "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\platform\bundled_python\python.exe"
if (-not (Test-Path $env:CLOUDSDK_PYTHON)) {
    $env:CLOUDSDK_PYTHON = "python"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Updating Cloud Run Env Vars Only" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Read .env
Write-Host "[1/2] Reading .env file..." -ForegroundColor Yellow
$envFile = Join-Path $PSScriptRoot ".env"
$envVarsList = @()

if (Test-Path $envFile) {
    $content = Get-Content $envFile
    foreach ($line in $content) {
        $line = $line.Trim()
        # Regex to capture KEY=VALUE, handling potential quotes
        if ($line -and -not $line.StartsWith("#") -and $line -match "^([^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            
            # Simple quote strip if surrounding quotes exist
            if ($val -match "^`".*`"$") { $val = $val.Substring(1, $val.Length - 2) }
            elseif ($val -match "^'.*'$") { $val = $val.Substring(1, $val.Length - 2) }
            
            # Verify specific keys if needed, or just push all
            $envVarsList += "$key=$val"
        }
    }
}

if ($envVarsList.Count -eq 0) {
    Write-Host "ERROR: No variables found in .env!" -ForegroundColor Red
    exit 1
}

$envVarsString = $envVarsList -join ","

# 2. Update Cloud Run
Write-Host "[2/2] Updating Config for service '$SERVICE_NAME'..." -ForegroundColor Yellow
Write-Host "Keys to be updated locally found: $($envVarsList.Count)" -ForegroundColor Gray

# Using 'gcloud run services update' which is faster than full deploy
gcloud run services update $SERVICE_NAME `
    --region $REGION `
    --project $PROJECT_ID `
    --set-env-vars "$envVarsString"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Environment Variables Updated Successfully!" -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "❌ Update Failed." -ForegroundColor Red
}
