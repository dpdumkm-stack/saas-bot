$ErrorActionPreference = "Stop"

# Fix for gcloud python issue
if (-not $env:CLOUDSDK_PYTHON) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        $env:CLOUDSDK_PYTHON = $py.Source
    }
}

Write-Host "Fetching logs from Cloud Run..." -ForegroundColor Yellow
gcloud run services logs read saas-bot --region asia-southeast2 --limit 100
