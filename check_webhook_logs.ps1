# Check Cloud Run logs untuk webhook requests
$PROJECT_ID = "gen-lang-client-0887245898"
$SERVICE_NAME = "saas-bot"
$REGION = "asia-southeast2"

Write-Host "=== Checking Cloud Run Webhook Logs ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service: $SERVICE_NAME" -ForegroundColor Gray
Write-Host "Project: $PROJECT_ID" -ForegroundColor Gray
Write-Host "Region: $REGION" -ForegroundColor Gray
Write-Host ""
Write-Host "Fetching latest logs..." -ForegroundColor Yellow
Write-Host ""

# Get logs with webhook-related content
$filter = "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND (textPayload=~`"webhook`" OR textPayload=~`"/webhook`" OR httpRequest.requestUrl=~`"/webhook`")"

try {
    # Get recent logs
    $logs = gcloud logging read $filter `
        --limit=20 `
        --format=json `
        --project=$PROJECT_ID 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error fetching logs. Trying alternative method..." -ForegroundColor Yellow
        Write-Host ""
        
        # Fallback: get all recent logs
        $allLogs = gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" `
            --limit=50 `
            --format=json `
            --project=$PROJECT_ID | ConvertFrom-Json
        
        if ($allLogs) {
            Write-Host "✅ Found $($allLogs.Count) recent log entries" -ForegroundColor Green
            Write-Host ""
            
            # Filter for webhook-related logs
            $webhookLogs = $allLogs | Where-Object { 
                ($_.textPayload -match "webhook") -or 
                ($_.textPayload -match "/webhook") -or
                ($_.httpRequest.requestUrl -match "/webhook")
            }
            
            if ($webhookLogs) {
                Write-Host "🎯 Found $($webhookLogs.Count) webhook-related log(s):" -ForegroundColor Green
                Write-Host ""
                
                foreach ($log in $webhookLogs | Select-Object -First 10) {
                    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
                    Write-Host "Time: " -NoNewline -ForegroundColor White
                    Write-Host $log.timestamp -ForegroundColor Cyan
                    
                    Write-Host "Severity: " -NoNewline -ForegroundColor White
                    $color = switch ($log.severity) {
                        "ERROR" { "Red" }
                        "WARNING" { "Yellow" }
                        "INFO" { "Green" }
                        default { "White" }
                    }
                    Write-Host $log.severity -ForegroundColor $color
                    
                    if ($log.httpRequest) {
                        Write-Host "HTTP Request:" -ForegroundColor White
                        Write-Host "  Method: $($log.httpRequest.requestMethod)" -ForegroundColor Gray
                        Write-Host "  URL: $($log.httpRequest.requestUrl)" -ForegroundColor Gray
                        Write-Host "  Status: $($log.httpRequest.status)" -ForegroundColor Gray
                    }
                    
                    if ($log.textPayload) {
                        Write-Host "Message:" -ForegroundColor White
                        $message = $log.textPayload
                        if ($message.Length -gt 500) {
                            $message = $message.Substring(0, 500) + "..."
                        }
                        Write-Host "  $message" -ForegroundColor Gray
                    }
                    Write-Host ""
                }
            }
            else {
                Write-Host "⚠️  No webhook-related logs found in recent entries" -ForegroundColor Yellow
                Write-Host ""
                Write-Host "Latest 5 logs (any type):" -ForegroundColor White
                Write-Host ""
                
                foreach ($log in $allLogs | Select-Object -First 5) {
                    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
                    Write-Host "$($log.timestamp) [$($log.severity)]" -ForegroundColor Cyan
                    if ($log.textPayload) {
                        $msg = $log.textPayload
                        if ($msg.Length -gt 200) { $msg = $msg.Substring(0, 200) + "..." }
                        Write-Host "  $msg" -ForegroundColor Gray
                    }
                }
            }
        }
        else {
            Write-Host "❌ No logs found" -ForegroundColor Red
        }
    }
    
}
catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Yellow
Write-Host "1. Kirim pesan ke WhatsApp bot Anda (contoh: /ping)" -ForegroundColor White
Write-Host "2. Tunggu beberapa detik" -ForegroundColor White
Write-Host "3. Jalankan script ini lagi untuk melihat webhook logs" -ForegroundColor White
Write-Host ""
Write-Host "Untuk melihat semua logs (bukan hanya webhook):" -ForegroundColor Yellow
Write-Host "  gcloud logging read `"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME`" --limit=20 --project=$PROJECT_ID" -ForegroundColor Gray
