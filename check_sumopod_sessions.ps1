# Check all SUMOPOD sessions
$API_KEY = $env:SUMOPOD_API_KEY
if (-not $API_KEY) {
    # Fallback to .env file
    if (Test-Path ".env") {
        $envContent = Get-Content ".env"
        foreach ($line in $envContent) {
            if ($line -match "^SUMOPOD_API_KEY=(.+)$") {
                $API_KEY = $matches[1].Trim()
                break
            }
        }
    }
}

if (-not $API_KEY) {
    Write-Host "Error: SUMOPOD_API_KEY not found!" -ForegroundColor Red
    exit 1
}

$SUMOPOD_URL = "https://waha-2sl8ak8iil6s.sgp-kresna.sumopod.my.id"

Write-Host "=== Checking SUMOPOD Sessions ===" -ForegroundColor Cyan
Write-Host ""

# Get all sessions
Write-Host "Fetching all sessions from SUMOPOD..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$SUMOPOD_URL/api/sessions?all=true" `
        -Method Get `
        -Headers @{
        "X-Api-Key" = $API_KEY
    } `
        -TimeoutSec 15
    
    if ($response -and $response.Count -gt 0) {
        Write-Host "✅ Found $($response.Count) session(s):" -ForegroundColor Green
        Write-Host ""
        
        foreach ($session in $response) {
            Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
            Write-Host "Session Name: " -NoNewline -ForegroundColor White
            Write-Host $session.name -ForegroundColor Cyan
            
            Write-Host "Status: " -NoNewline -ForegroundColor White
            Write-Host $session.status -ForegroundColor $(if ($session.status -eq 'WORKING') { 'Green' } else { 'Yellow' })
            
            if ($session.config -and $session.config.webhooks) {
                Write-Host "Webhooks: " -ForegroundColor White
                $session.config.webhooks | ForEach-Object {
                    Write-Host "  - URL: $($_.url)" -ForegroundColor Gray
                    Write-Host "    Events: $($_.events -join ', ')" -ForegroundColor Gray
                }
            }
            else {
                Write-Host "Webhooks: " -NoNewline -ForegroundColor White
                Write-Host "Not configured" -ForegroundColor Red
            }
            Write-Host ""
        }
        
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Yellow
        Write-Host "1. Pilih session yang ingin dikonfigurasi" -ForegroundColor White
        Write-Host "2. Update webhook untuk session tersebut" -ForegroundColor White
        
    }
    else {
        Write-Host "⚠️  No sessions found!" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Anda mungkin perlu membuat session baru terlebih dahulu." -ForegroundColor White
        Write-Host "Atau verifikasi API key Anda sudah benar." -ForegroundColor White
    }
    
}
catch {
    Write-Host "❌ Failed to fetch sessions!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}
