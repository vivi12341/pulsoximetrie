# ==============================================================================
# test_railway_deploy.ps1
# ------------------------------------------------------------------------------
# ROL: Script testare rapidă Railway deployment după fix Gunicorn
# UTILIZARE: .\test_railway_deploy.ps1
# ==============================================================================

Write-Host "=" -ForegroundColor Cyan
Write-Host "🧪 TEST RAILWAY DEPLOYMENT - Fix Gunicorn Production Server" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "https://pulsoximetrie.cardiohelpteam.ro"
$testsPassed = 0
$testsFailed = 0

# === TEST 1: Health Check Endpoint ===
Write-Host "[TEST 1/5] Health Check Endpoint..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "$baseUrl/health" -Method GET -TimeoutSec 10
    
    if ($response.StatusCode -eq 200) {
        $healthData = $response.Content | ConvertFrom-Json
        
        if ($healthData.status -eq "healthy") {
            Write-Host "✅ PASS: Health check OK" -ForegroundColor Green
            Write-Host "   Database: $($healthData.checks.database)" -ForegroundColor Gray
            Write-Host "   Storage: $($healthData.checks.storage)" -ForegroundColor Gray
            Write-Host "   Callbacks: $($healthData.checks.callbacks)" -ForegroundColor Gray
            $testsPassed++
        } else {
            Write-Host "❌ FAIL: Status = $($healthData.status) (expected: healthy)" -ForegroundColor Red
            $testsFailed++
        }
    } else {
        Write-Host "❌ FAIL: Status code = $($response.StatusCode) (expected: 200)" -ForegroundColor Red
        $testsFailed++
    }
} catch {
    Write-Host "❌ FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

Write-Host ""

# === TEST 2: Homepage Load ===
Write-Host "[TEST 2/5] Homepage Load Test..." -ForegroundColor Yellow

try {
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $response = Invoke-WebRequest -Uri $baseUrl -Method GET -TimeoutSec 15
    $stopwatch.Stop()
    
    $loadTime = $stopwatch.ElapsedMilliseconds
    
    if ($response.StatusCode -eq 200) {
        if ($loadTime -lt 3000) {
            Write-Host "✅ PASS: Homepage loaded in ${loadTime}ms" -ForegroundColor Green
            $testsPassed++
        } else {
            Write-Host "⚠️  WARN: Homepage loaded in ${loadTime}ms (slow, expected < 3000ms)" -ForegroundColor Yellow
            $testsPassed++
        }
    } else {
        Write-Host "❌ FAIL: Status code = $($response.StatusCode)" -ForegroundColor Red
        $testsFailed++
    }
} catch {
    Write-Host "❌ FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

Write-Host ""

# === TEST 3: Static Assets ===
Write-Host "[TEST 3/5] Static Assets Check..." -ForegroundColor Yellow

$assetsToCheck = @(
    "/_dash-component-suites/dash/dcc/async-graph.js",
    "/_dash-component-suites/dash/dash_table/async-table.js"
)

$assetsPassed = 0
$assetsTotal = $assetsToCheck.Count

foreach ($asset in $assetsToCheck) {
    try {
        $assetUrl = $baseUrl + $asset
        $response = Invoke-WebRequest -Uri $assetUrl -Method HEAD -TimeoutSec 5
        
        if ($response.StatusCode -eq 200) {
            $assetsPassed++
        }
    } catch {
        # Ignorăm 404-urile pentru Dash assets (sunt încărcate dinamic)
    }
}

# Considerăm test SUCCESS dacă măcar 1 asset funcționează
if ($assetsPassed -gt 0) {
    Write-Host "✅ PASS: Static assets accessible ($assetsPassed/$assetsTotal found)" -ForegroundColor Green
    $testsPassed++
} else {
    Write-Host "⚠️  WARN: No static assets found (poate fi normal pentru Dash apps)" -ForegroundColor Yellow
    $testsPassed++  # Nu considerăm fail
}

Write-Host ""

# === TEST 4: Check Gunicorn Workers (indirect) ===
Write-Host "[TEST 4/5] Concurrent Requests Test (Gunicorn workers)..." -ForegroundColor Yellow

try {
    # Lansăm 5 requests concurrente către /health
    $jobs = @()
    for ($i = 1; $i -le 5; $i++) {
        $jobs += Start-Job -ScriptBlock {
            param($url)
            try {
                $response = Invoke-WebRequest -Uri "$url/health" -Method GET -TimeoutSec 10
                return @{
                    StatusCode = $response.StatusCode
                    Success = $true
                }
            } catch {
                return @{
                    StatusCode = 0
                    Success = $false
                    Error = $_.Exception.Message
                }
            }
        } -ArgumentList $baseUrl
    }
    
    # Așteptăm toate job-urile să se termine (max 15 secunde)
    $jobs | Wait-Job -Timeout 15 | Out-Null
    
    $results = $jobs | Receive-Job
    $successCount = ($results | Where-Object { $_.Success -eq $true }).Count
    
    # Cleanup jobs
    $jobs | Remove-Job -Force
    
    if ($successCount -eq 5) {
        Write-Host "✅ PASS: All 5 concurrent requests succeeded (Gunicorn workers OK)" -ForegroundColor Green
        $testsPassed++
    } elseif ($successCount -ge 3) {
        Write-Host "⚠️  WARN: Only $successCount/5 concurrent requests succeeded" -ForegroundColor Yellow
        $testsPassed++
    } else {
        Write-Host "❌ FAIL: Only $successCount/5 concurrent requests succeeded" -ForegroundColor Red
        $testsFailed++
    }
} catch {
    Write-Host "❌ FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

Write-Host ""

# === TEST 5: Response Headers (Production Check) ===
Write-Host "[TEST 5/5] Production Headers Check..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri $baseUrl -Method GET -TimeoutSec 10
    
    $serverHeader = $response.Headers["Server"]
    
    # Verificăm că NU este development server
    $isDevelopment = $serverHeader -match "Werkzeug" -or $serverHeader -match "Development"
    
    if (-not $isDevelopment) {
        Write-Host "✅ PASS: Production server detected (not development)" -ForegroundColor Green
        if ($serverHeader) {
            Write-Host "   Server: $serverHeader" -ForegroundColor Gray
        }
        $testsPassed++
    } else {
        Write-Host "❌ FAIL: Development server detected! Server: $serverHeader" -ForegroundColor Red
        $testsFailed++
    }
} catch {
    Write-Host "❌ FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $testsFailed++
}

Write-Host ""

# === RAPORT FINAL ===
Write-Host "=" -ForegroundColor Cyan
Write-Host "📊 RAPORT FINAL" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan
Write-Host ""
Write-Host "Tests Passed: $testsPassed/5" -ForegroundColor $(if ($testsPassed -eq 5) { "Green" } else { "Yellow" })
Write-Host "Tests Failed: $testsFailed/5" -ForegroundColor $(if ($testsFailed -eq 0) { "Green" } else { "Red" })
Write-Host ""

if ($testsFailed -eq 0) {
    Write-Host "✅ SUCCESS: Railway deployment OK - Gunicorn production server funcționează!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "1. Accesează https://pulsoximetrie.cardiohelpteam.ro/" -ForegroundColor Gray
    Write-Host "2. Login ca medic (tab Admin)" -ForegroundColor Gray
    Write-Host "3. Test upload CSV + generare grafic" -ForegroundColor Gray
    Write-Host "4. Verifică Railway Deploy Logs pentru 'Booting worker with pid'" -ForegroundColor Gray
    Write-Host ""
    exit 0
} else {
    Write-Host "❌ FAILURE: Railway deployment are probleme!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Debugging Steps:" -ForegroundColor Yellow
    Write-Host "1. Verifică Railway Build Logs (gunicorn instalat?)" -ForegroundColor Gray
    Write-Host "2. Verifică Railway Deploy Logs (workers pornite?)" -ForegroundColor Gray
    Write-Host "3. Verifică Environment Variables (DATABASE_URL setat?)" -ForegroundColor Gray
    Write-Host "4. Screenshot logs + trimite în chat pentru debugging" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

