# Deploy SaaS Bot to Cloud Run
# Project: UMKM TANGSEL (gen-lang-client-0887245898)

# Fix for gcloud python location
$env:CLOUDSDK_PYTHON = "C:\Users\p\AppData\Local\Programs\Python\Python311\python.exe"
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

Write-Host ""
Write-Host "[3.5/4] Running Automated Smoke Tests..." -ForegroundColor Yellow

# 1. Syntax Guard
Write-Host "Checking Python syntax..." -ForegroundColor White
$pyFiles = Get-ChildItem -Path "bot" -Filter "*.py" -Recurse
foreach ($file in $pyFiles) {
    & $env:CLOUDSDK_PYTHON -m py_compile $file.FullName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Syntax error found in $($file.FullName)" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✅ Syntax check passed!" -ForegroundColor Green

# 2. Unit Tests (Optional but recommended)
# 2. Unit Tests (Optional but recommended)
Write-Host "Running unit tests (pytest)..." -ForegroundColor White
& $env:CLOUDSDK_PYTHON -m pytest tests/test_broadcast.py --collect-only > $null 2>&1
if ($LASTEXITCODE -eq 0) {
    & $env:CLOUDSDK_PYTHON -m pytest tests/test_broadcast.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Unit tests failed! Fix them before deploying." -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Unit tests passed!" -ForegroundColor Green
}
else {
    Write-Host "⚠️  No tests found or pytest not installed. Skipping unit tests..." -ForegroundColor Yellow
}

Write-Host "[4/4] Deploying to Cloud Run..." -ForegroundColor Yellow
Write-Host ""
Write-Host "This will:" -ForegroundColor Cyan
Write-Host "  - Build Docker image from source" -ForegroundColor White
Write-Host "  - Push to Google Container Registry" -ForegroundColor White
Write-Host "  - Deploy to Cloud Run (asia-southeast2)" -ForegroundColor White
Write-Host "  - Allow unauthenticated access (for webhooks)" -ForegroundColor White
Write-Host ""

# Read env vars from .env file
$envFile = Join-Path $PSScriptRoot ".env"
$envVarsList = @()

if (Test-Path $envFile) {
    $content = Get-Content $envFile
    foreach ($line in $content) {
        $line = $line.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match "^([^=]+)=(.*)$") {
            $key = $matches[1].Trim()
            $val = $matches[2].Trim()
            # Remove quotes if present
            if ($val -match "^`".*`"$") { $val = $val.Substring(1, $val.Length - 2) }
            elseif ($val -match "^'.*'$") { $val = $val.Substring(1, $val.Length - 2) }
            $envVarsList += "$key=$val"
        }
    }
}

# Construct Env Vars String
# We join them with commas as required by gcloud --set-env-vars
$envVars = $envVarsList -join ","

if (-not $envVars) {
    Write-Host "WARNING: No environment variables found in .env" -ForegroundColor Yellow
}

# Deploy using Cloud Build + Cloud Run (Explicit Dockerfile Build)
Write-Host "Building Container Image..." -ForegroundColor Yellow
gcloud builds submit --tag gcr.io/gen-lang-client-0887245898/saas-bot .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build Failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Deploying Container..." -ForegroundColor Yellow
gcloud run deploy saas-bot `
    --image gcr.io/gen-lang-client-0887245898/saas-bot `
    --region asia-southeast2 `
    --allow-unauthenticated `
    --platform managed `
    --set-env-vars "$envVars"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Deployment Successful!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Service URL: https://saas-bot-643221888510.asia-southeast2.run.app" -ForegroundColor White
}
else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  Deployment Failed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check the error messages above and try again." -ForegroundColor Yellow
}
