# Deploy SaaS Bot to Cloud Run
# Project: UMKM TANGSEL (gen-lang-client-0887245898)

# Fix for gcloud python location
$env:CLOUDSDK_PYTHON = "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\platform\bundled_python\python.exe"
if (-not (Test-Path $env:CLOUDSDK_PYTHON)) {
    # Fallback to standard python if bundled not found
    $env:CLOUDSDK_PYTHON = "python"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Deploying SaaS Bot to Cloud Run" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if gcloud is configured
Write-Host "[1/4] Checking gcloud configuration..." -ForegroundColor Yellow
$project = gcloud config get-value project 2>$null
if ($project -ne "gen-lang-client-0887245898") {
    Write-Host "Setting project to gen-lang-client-0887245898..." -ForegroundColor Yellow
    gcloud config set project gen-lang-client-0887245898
}

Write-Host "[2/4] Verifying authentication..." -ForegroundColor Yellow
$account = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
if (-not $account) {
    Write-Host "ERROR: Not authenticated. Please run 'gcloud auth login' first." -ForegroundColor Red
    exit 1
}
Write-Host "Authenticated as: $account" -ForegroundColor Green

Write-Host "[3/4] Checking required files..." -ForegroundColor Yellow
if (-not (Test-Path "Dockerfile")) {
    Write-Host "ERROR: Missing required file: Dockerfile" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "bot")) {
    Write-Host "ERROR: Missing bot directory" -ForegroundColor Red
    exit 1
}
Write-Host "All required files present" -ForegroundColor Green

Write-Host "[4/4] Deploying to Cloud Run..." -ForegroundColor Yellow
Write-Host ""
Write-Host "This will:" -ForegroundColor Cyan
Write-Host "  - Build Docker image from source" -ForegroundColor White
Write-Host "  - Push to Google Container Registry" -ForegroundColor White
Write-Host "  - Deploy to Cloud Run (asia-southeast2)" -ForegroundColor White
Write-Host "  - Allow unauthenticated access (for webhooks)" -ForegroundColor White
Write-Host ""

# Deploy using Cloud Build + Cloud Run
# Read env vars from .env file securely
$envFile = Join-Path $PSScriptRoot ".env"
$dbUrl = ""
$geminiKey = ""
$wahaKey = ""
$superAdmin = ""

if (Test-Path $envFile) {
    $content = Get-Content $envFile
    foreach ($line in $content) {
        if ($line -match "^DATABASE_URL=(.+)$") { $dbUrl = $matches[1] }
        if ($line -match "^GEMINI_API_KEY=(.+)$") { $geminiKey = $matches[1] }
        if ($line -match "^WAHA_API_KEY=(.+)$") { $wahaKey = $matches[1] }
        if ($line -match "^SUPER_ADMIN_WA=(.+)$") { $superAdmin = $matches[1] }
    }
}

if (-not $dbUrl) { Write-Host "WARNING: DATABASE_URL not found in .env" -ForegroundColor Yellow }
if (-not $geminiKey) { Write-Host "WARNING: GEMINI_API_KEY not found in .env" -ForegroundColor Yellow }

# Construct Env Vars String
$envVars = "DATABASE_URL=$dbUrl,GEMINI_API_KEY=$geminiKey,WAHA_API_KEY=$wahaKey,SUPER_ADMIN_WA=$superAdmin"

# Deploy using Cloud Build + Cloud Run
gcloud run deploy saas-bot `
    --source . `
    --region asia-southeast2 `
    --allow-unauthenticated `
    --platform managed `
    --set-env-vars "$envVars"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Deployment Successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Note the service URL from the output above" -ForegroundColor White
    Write-Host "2. Update your WAHA webhook URL to point to: https://YOUR-SERVICE-URL/webhook" -ForegroundColor White
    Write-Host "3. Test with /ping command in WhatsApp" -ForegroundColor White
}
else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  Deployment Failed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check the error messages above and try again." -ForegroundColor Yellow
}
