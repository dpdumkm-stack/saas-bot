# Safe Deployment Script with Auto-Rollback
# Usage: .\safe_deploy.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SAFE DEPLOYMENT SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Get current revision for rollback
Write-Host "[Step 1/5] Backing up current revision..." -ForegroundColor Yellow

try {
    $current_revision = gcloud run revisions list `
        --service=saas-bot `
        --region=asia-southeast2 `
        --limit=1 `
        --format="value(name)" 2>$null
    
    if ($current_revision) {
        Write-Host "Current revision: $current_revision" -ForegroundColor Green
        $rollback_cmd = "gcloud run services update-traffic saas-bot --to-revisions=$current_revision=100 --region=asia-southeast2"
    }
    else {
        Write-Host "No existing revision found (first deployment?)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "Could not get current revision: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""

# 2. Run automated tests
Write-Host "[Step 2/5] Running automated tests..." -ForegroundColor Yellow

$test_files = @(
    "test_register_trx.py",
    "test_multitenancy_isolation.py",
    "test_anti_spam.py"
)

$all_tests_passed = $true

foreach ($test in $test_files) {
    if (Test-Path $test) {
        Write-Host "  Running $test..." -ForegroundColor Gray
        python $test 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  $test PASSED" -ForegroundColor Green
        }
        else {
            Write-Host "  $test FAILED" -ForegroundColor Red
            $all_tests_passed = $false
        }
    }
}

if (-not $all_tests_passed) {
    Write-Host ""
    Write-Host "TESTS FAILED! Aborting deployment." -ForegroundColor Red
    Write-Host "Fix the failing tests before deploying to production." -ForegroundColor Yellow
    exit 1
}

Write-Host "All tests passed!" -ForegroundColor Green
Write-Host ""

# 3. Confirm deployment
Write-Host "[Step 3/5] Ready to deploy..." -ForegroundColor Yellow
Write-Host "This will deploy to: https://saas-bot-643221888510.asia-southeast2.run.app" -ForegroundColor White
Write-Host ""
$confirm = Read-Host "Continue with deployment? (y/n)"

if ($confirm -ne "y") {
    Write-Host "Deployment cancelled by user." -ForegroundColor Yellow
    exit 0
}

Write-Host ""

# 4. Deploy to Cloud Run
Write-Host "[Step 4/5] Deploying to Cloud Run..." -ForegroundColor Yellow
Write-Host "This may take 3-5 minutes..." -ForegroundColor Gray
Write-Host ""

.\deploy_to_cloudrun.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Deployment FAILED!" -ForegroundColor Red
    Write-Host "Check the error messages above." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Deployment completed!" -ForegroundColor Green
Write-Host ""

# 5. Health check
Write-Host "[Step 5/5] Running health check..." -ForegroundColor Yellow
Write-Host "Waiting 10 seconds for service to stabilize..." -ForegroundColor Gray
Start-Sleep -Seconds 10

try {
    $health_response = Invoke-WebRequest `
        -Uri "https://saas-bot-643221888510.asia-southeast2.run.app/" `
        -Method GET `
        -UseBasicParsing `
        -TimeoutSec 10
    
    if ($health_response.StatusCode -eq 200) {
        Write-Host "Health check PASSED (HTTP 200)" -ForegroundColor Green
    }
    else {
        Write-Host "Health check returned HTTP $($health_response.StatusCode)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "Health check FAILED!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    
    if ($current_revision) {
        Write-Host "ROLLING BACK to previous version..." -ForegroundColor Yellow
        
        Invoke-Expression $rollback_cmd
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Rollback successful! Service restored to: $current_revision" -ForegroundColor Green
        }
        else {
            Write-Host "Rollback FAILED! Manual intervention required." -ForegroundColor Red
        }
    }
    else {
        Write-Host "No previous revision to rollback to." -ForegroundColor Yellow
    }
    
    exit 1
}

# Success!
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Service URL: https://saas-bot-643221888510.asia-southeast2.run.app" -ForegroundColor White
Write-Host "Cloud Console: https://console.cloud.google.com/run?project=gen-lang-client-0887245898" -ForegroundColor White
Write-Host ""

if ($current_revision) {
    Write-Host "Rollback command (if needed):" -ForegroundColor Yellow
    Write-Host $rollback_cmd -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "Monitor logs for 15 minutes to ensure stability" -ForegroundColor Yellow
Write-Host "To view logs: gcloud logging read 'resource.type=cloud_run_revision' --limit=50" -ForegroundColor Gray
Write-Host ""
