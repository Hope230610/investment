param(
    [switch]$Full,
    [switch]$ListOnly,
    [switch]$PrepareDb,
    [switch]$MockMarket,
    [string]$BackendUrl = "http://localhost:8000",
    [string]$FrontendUrl = "http://localhost:3000",
    [string]$User = "testuser",
    [string]$Password = "testpassword123",
    [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"

function Invoke-Step($Name, [scriptblock]$Block) {
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    $global:LASTEXITCODE = 0
    & $Block
    if ($global:LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $global:LASTEXITCODE"
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$frontRoot = Resolve-Path (Join-Path $repoRoot "investment-front")
$backRoot = Resolve-Path (Join-Path $repoRoot "investment-back")

if ($PrepareDb -and [string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $DatabaseUrl = $env:DATABASE_URL
    if ([string]::IsNullOrWhiteSpace($DatabaseUrl) -or ($DatabaseUrl -notmatch '(?i)(test|e2e)')) {
        $DatabaseUrl = "postgresql://postgres:123456@localhost:5432/investment_e2e"
    }
}

if (-not [string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $env:DATABASE_URL = $DatabaseUrl
}
$env:DEBUG = "true"
$env:ENVIRONMENT = "development"

if ($MockMarket) {
    $env:E2E_MOCK_MARKET = "true"
    $env:MOCK_MARKET_DATA = "true"
    # Ensure Playwright starts a backend with the mock env instead of silently
    # reusing a real-market server from a previous run.
    $env:E2E_REUSE_SERVERS = "false"
} else {
    Remove-Item Env:\E2E_MOCK_MARKET -ErrorAction SilentlyContinue
    Remove-Item Env:\MOCK_MARKET_DATA -ErrorAction SilentlyContinue
}

Invoke-Step "Backend compile" {
    Push-Location $backRoot
    python -m compileall src tests scripts
    Pop-Location
}

Invoke-Step "Backend tests" {
    Push-Location $backRoot
    pytest -q
    Pop-Location
}

if ($PrepareDb) {
    Invoke-Step "Prepare E2E database" {
        Push-Location $backRoot
        python scripts/prepare_e2e_db.py --username $User --password $Password
        Pop-Location
    }
}

Invoke-Step "Frontend lint" {
    Push-Location $frontRoot
    npm run --silent lint
    Pop-Location
}

Invoke-Step "Frontend unit tests" {
    Push-Location $frontRoot
    npm run --silent test -- --run
    Pop-Location
}

Invoke-Step "Frontend build" {
    Push-Location $frontRoot
    npm run --silent build
    Pop-Location
}

$env:E2E_API_URL = $BackendUrl
$env:E2E_BASE_URL = $FrontendUrl
$env:E2E_USER = $User
$env:E2E_PASS = $Password
$env:BACKEND_BASE_URL = $BackendUrl

Invoke-Step "Playwright list" {
    Push-Location $frontRoot
    npm run --silent test:e2e -- --list
    Pop-Location
}

if ($ListOnly -and -not $Full) {
    Write-Host "`nListOnly complete. Use -Full to run the full E2E suite." -ForegroundColor Yellow
    exit 0
}

if ($Full) {
    Invoke-Step "Playwright full E2E" {
        Push-Location $frontRoot
        npm run --silent test:e2e
        Pop-Location
    }
} else {
    Write-Host "`nSkipped full E2E. Re-run with -Full after the test database/account are ready." -ForegroundColor Yellow
}
