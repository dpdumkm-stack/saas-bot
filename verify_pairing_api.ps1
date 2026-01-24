# verify_pairing_api.ps1
$ErrorActionPreference = "Stop"

# Deployment URL from logs:
$BaseUrl = "https://saas-bot-643221888510.asia-southeast2.run.app"

Function Test-Endpoint {
    param($Url, $Method = "GET", $Body = $null)
    Write-Host "Testing $Url ($Method)..." -NoNewline
    try {
        if ($Body) {
            $response = Invoke-WebRequest -Uri $Url -Method $Method -Body ($Body | ConvertTo-Json) -ContentType "application/json" -UseBasicParsing
        }
        else {
            $response = Invoke-WebRequest -Uri $Url -Method $Method -UseBasicParsing
        }
        Write-Host " OK ($($response.StatusCode))" -ForegroundColor Green
        return $response
    }
    catch {
        Write-Host " FAILED ($($_))" -ForegroundColor Red
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader $_.Exception.Response.GetResponseStream()
            Write-Host "Body: $($reader.ReadToEnd())" -ForegroundColor Yellow
        }
    }
}

# 1. Health Check
Test-Endpoint "$BaseUrl/health"

# 2. Test Pairing Code Request (using a dummy session to see if logic holds)
# This expects backend to try and talk to WAHA
$testSession = "session_test_pairing_verification"
$body = @{
    session_name = $testSession
}

Write-Host "`nRequesting pairing code for '$testSession'..."
$res = Test-Endpoint "$BaseUrl/api/pairing/request-code" "POST" $body

if ($res) {
    try {
        $json = $res.Content | ConvertFrom-Json
        Write-Host "Response Status: $($json.status)"
        Write-Host "Message: $($json.message)"
        
        if ($json.code) {
            Write-Host "✅ PAIRING CODE RECEIVED: $($json.code)" -ForegroundColor Green
        }
        else {
            Write-Host "✅ RESPONSE RECEIVED (Expected failure as session '$testSession' likely doesn't exist in WAHA yet)" -ForegroundColor Cyan
            Write-Host "This confirms the endpoint is reachable and logic is executing." 
        }
    }
    catch {
        Write-Host "WARNING: Could not parse JSON response: $($res.Content)" -ForegroundColor Yellow
    }
}
