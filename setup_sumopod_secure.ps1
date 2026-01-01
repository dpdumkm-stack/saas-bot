
$ErrorActionPreference = "Stop"
function Show-Header {
    Clear-Host
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "   SUMOPOD WAHA INTEGRATION SETUP - SECURE" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
}

# Simple Python Detection
try {
    if (-not $env:CLOUDSDK_PYTHON) {
        $pyCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pyCmd) {
            $env:CLOUDSDK_PYTHON = $pyCmd.Source
            Write-Host "Using Python: $($pyCmd.Source)" -ForegroundColor Gray
        }
    }
}
catch {
    Write-Host "Warning: Python detection failed, skipping." -ForegroundColor Gray
}

function Get-ApiKey {
    Write-Host "Masukkan WAHA_API_KEY Anda (Input akan disembunyikan):" -ForegroundColor Yellow
    $key = Read-Host -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($key)
    $PlainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    return $PlainPassword
}

function Update-CloudRun {
    param($ApiKey)
    Write-Host ""
    Write-Host "[1/3] Updating Cloud Run Environment..." -ForegroundColor Yellow
    
    $account = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
    if (-not $account) {
        Write-Host "Gcloud not logged in. Please login..." -ForegroundColor Yellow
        gcloud auth login
    }

    $ProjectID = "gen-lang-client-0887245898"
    $Region = "asia-southeast2"
    $Service = "saas-bot"

    Write-Host "   Setting WAHA_API_KEY for $Service..."
    
    gcloud run services update $Service `
        --region $Region `
        --project $ProjectID `
        --set-env-vars "^@^WAHA_API_KEY=$ApiKey" `
        --quiet

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   SUCCESS: Cloud Run updated." -ForegroundColor Green
    }
    else {
        Write-Host "   FAILED: Cloud Run update." -ForegroundColor Red
        return $false
    }
    return $true
}

function Set-Webhook {
    param($ApiKey)
    Write-Host ""
    Write-Host "[2/3] Configuring SUMOPOD Webhook..." -ForegroundColor Yellow
    
    $BaseUrl = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"
    $WebhookUrl = "https://saas-bot-643221888510.asia-southeast2.run.app/webhook"
    
    $Url = "$BaseUrl/api/sessions/default"
    
    $BodyObj = @{
        config = @{
            webhook = @{
                url    = $WebhookUrl
                events = @("message", "session.status")
            }
        }
    }
    $JsonBody = $BodyObj | ConvertTo-Json -Depth 5

    try {
        $Response = Invoke-RestMethod -Uri $Url -Method Patch -Headers @{
            "X-Api-Key"    = $ApiKey
            "Content-Type" = "application/json"
        } -Body $JsonBody -ErrorAction Stop
        
        Write-Host "   SUCCESS: Webhook updated!" -ForegroundColor Green
    }
    catch {
        Write-Host "   Failed to patch, trying to create session..." -ForegroundColor Yellow
        $err = $_
        
        $CreateUrl = "$BaseUrl/api/sessions"
        $CreateBodyObj = @{
            name   = "default"
            config = @{
                webhook = @{
                    url    = $WebhookUrl
                    events = @("message", "session.status")
                }
            }
        }
        $CreateJsonBody = $CreateBodyObj | ConvertTo-Json -Depth 5
        
        try {
            Invoke-RestMethod -Uri $CreateUrl -Method Post -Headers @{
                "X-Api-Key"    = $ApiKey
                "Content-Type" = "application/json"
            } -Body $CreateJsonBody
            Write-Host "   SUCCESS: Session created with webhook!" -ForegroundColor Green
        }
        catch {
            Write-Host "   ERROR: Failed to create session. $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
    return $true
}

function Test-Setup {
    Write-Host ""
    Write-Host "[3/3] Verifying Setup..." -ForegroundColor Yellow
    Write-Host "   Please send '/ping' to your WhatsApp bot now."
    Write-Host "   Check logs: gcloud run logs read saas-bot --region asia-southeast2" -ForegroundColor Gray
}

# --- MAIN ---
Show-Header
$ApiKey = Get-ApiKey

if (-not $ApiKey) {
    Write-Host "Error: API Key is required."
    exit
}

$updateCloud = Read-Host "Update Cloud Run Env Var? (Y/N)"
if ($updateCloud -eq "Y" -or $updateCloud -eq "y") {
    Update-CloudRun -ApiKey $ApiKey
}

$setWebhook = Read-Host "Set SUMOPOD Webhook? (Y/N)"
if ($setWebhook -eq "Y" -or $setWebhook -eq "y") {
    Set-Webhook -ApiKey $ApiKey
}

Test-Setup
Write-Host ""
Write-Host "DONE." -ForegroundColor Cyan
