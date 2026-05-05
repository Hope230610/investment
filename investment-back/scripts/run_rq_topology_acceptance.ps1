param(
    [string]$BackendUrl = "http://localhost:8000",
    [string]$FrontendUrl = "http://localhost:3000",
    [string]$RedisUrl = "redis://localhost:6379/0",
    [string]$User = "testuser",
    [string]$Password = "testpassword123",
    [string]$StockId = "SH600519",
    [string]$StockName = "贵州茅台",
    [int]$PostMaxSeconds = 10,
    [int]$PollTimeoutSeconds = 180,
    [switch]$SkipFrontendCheck
)

$ErrorActionPreference = "Stop"

$BackRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $BackRoot ".venv\Scripts\python.exe"
$PythonExe = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

function Invoke-Step($Name, [scriptblock]$Block) {
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    $global:LASTEXITCODE = 0
    & $Block
    if ($global:LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $global:LASTEXITCODE"
    }
}

function Invoke-JsonRequest(
    [string]$Method,
    [string]$Uri,
    [object]$Body = $null,
    [hashtable]$Headers = @{}
) {
    $params = @{
        Method = $Method
        Uri = $Uri
        Headers = $Headers
    }
    if ($null -ne $Body) {
        $params.ContentType = "application/json; charset=utf-8"
        $params.Body = ($Body | ConvertTo-Json -Depth 20 -Compress)
    }
    Invoke-RestMethod @params
}

function Get-AuthToken() {
    $loginBody = @{ username = $User; password = $Password }
    try {
        $login = Invoke-JsonRequest -Method "POST" -Uri "$BackendUrl/api/v1/user/login" -Body $loginBody
        return $login.access_token
    } catch {
        Write-Host "Login failed; attempting to register the acceptance user." -ForegroundColor Yellow
        $register = Invoke-JsonRequest -Method "POST" -Uri "$BackendUrl/api/v1/user/register" -Body $loginBody
        return $register.access_token
    }
}

function Test-RqJobForAnalysis([string]$AnalysisId) {
    $env:REDIS_URL = $RedisUrl
    $env:ANALYSIS_ID = $AnalysisId
    & $PythonExe -c @"
import os
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry, DeferredJobRegistry

redis_conn = Redis.from_url(os.environ["REDIS_URL"], decode_responses=False)
queue = Queue("analysis", connection=redis_conn)
analysis_id = os.environ["ANALYSIS_ID"]

job_ids = set(queue.job_ids)
for registry_cls in (StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry, DeferredJobRegistry):
    job_ids.update(registry_cls("analysis", connection=redis_conn).get_job_ids())

matched = []
for job_id in job_ids:
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        continue
    args = " ".join(str(arg) for arg in (job.args or ()))
    if analysis_id in args:
        matched.append((job_id, job.get_status(refresh=True)))

if not matched:
    raise SystemExit(f"no RQ job found for analysis_id={analysis_id}")

for job_id, status in matched:
    print(f"rq_job={job_id} status={status}")
"@
}

$env:RQ_ASYNC = "false"
$env:REDIS_URL = $RedisUrl

Invoke-Step "Environment guard" {
    if ($env:RQ_ASYNC -ne "false") {
        throw "RQ_ASYNC must be false for production topology acceptance"
    }
    Write-Host "RQ_ASYNC=$env:RQ_ASYNC"
    Write-Host "REDIS_URL=$env:REDIS_URL"
    Write-Host "BackendUrl=$BackendUrl"
    Write-Host "FrontendUrl=$FrontendUrl"
}

Invoke-Step "Redis ping" {
    & $PythonExe -c "from redis import Redis; import os; r=Redis.from_url(os.environ['REDIS_URL']); assert r.ping() is True; print('redis=healthy')"
}

Invoke-Step "Backend health" {
    $health = Invoke-JsonRequest -Method "GET" -Uri "$BackendUrl/health"
    if ($health.status -ne "healthy") {
        throw "backend health is not healthy: $($health | ConvertTo-Json -Compress)"
    }
    $health | ConvertTo-Json -Compress
}

Invoke-Step "Backend readiness" {
    $ready = Invoke-JsonRequest -Method "GET" -Uri "$BackendUrl/ready"
    if ($ready.status -ne "ready") {
        throw "backend readiness is not ready: $($ready | ConvertTo-Json -Compress)"
    }
    if ($ready.checks.redis -ne "healthy" -or $ready.checks.worker_mode -ne "rq") {
        throw "backend readiness did not report rq/redis healthy: $($ready | ConvertTo-Json -Compress)"
    }
    $ready | ConvertTo-Json -Compress
}

if (-not $SkipFrontendCheck) {
    Invoke-Step "Frontend reachability" {
        $response = Invoke-WebRequest -Uri $FrontendUrl -Method Get -UseBasicParsing
        if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
            throw "frontend returned HTTP $($response.StatusCode)"
        }
        Write-Host "frontend=reachable status=$($response.StatusCode)"
    }
}

$token = $null
Invoke-Step "Acceptance user auth" {
    $token = Get-AuthToken
    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "authentication did not return an access token"
    }
    Write-Host "auth=ok user=$User"
}

$analysisId = $null
$createStatus = $null
Invoke-Step "Create analysis task through API" {
    $headers = @{ Authorization = "Bearer $token" }
    $payload = @{
        stock_id = $StockId
        scenario = "single_stock_check"
        scenario_payload = @{
            stock_name = $StockName
            intent = "rq-topology-acceptance"
        }
    }

    $elapsed = Measure-Command {
        $script:createResponse = Invoke-JsonRequest -Method "POST" -Uri "$BackendUrl/api/v1/analysis" -Body $payload -Headers $headers
    }

    if ($elapsed.TotalSeconds -gt $PostMaxSeconds) {
        throw "POST /analysis took $([math]::Round($elapsed.TotalSeconds, 2))s; expected quick enqueue under ${PostMaxSeconds}s"
    }
    $analysisId = $script:createResponse.id
    $createStatus = $script:createResponse.status
    if ([string]::IsNullOrWhiteSpace($analysisId)) {
        throw "analysis create did not return an id: $($script:createResponse | ConvertTo-Json -Compress)"
    }
    Write-Host "analysis_id=$analysisId create_status=$createStatus post_seconds=$([math]::Round($elapsed.TotalSeconds, 2))"
}

Invoke-Step "RQ job is present for analysis task" {
    Test-RqJobForAnalysis -AnalysisId $analysisId
}

Invoke-Step "Poll analysis until worker terminal state" {
    $headers = @{ Authorization = "Bearer $token" }
    $deadline = (Get-Date).AddSeconds($PollTimeoutSeconds)
    $lastStatus = $null
    $terminal = @("ready", "partial_ready", "failed")
    while ((Get-Date) -lt $deadline) {
        $result = Invoke-JsonRequest -Method "GET" -Uri "$BackendUrl/api/v1/analysis/$analysisId" -Headers $headers
        $lastStatus = $result.status
        Write-Host "analysis_status=$lastStatus"
        if ($terminal -contains $lastStatus) {
            if ($lastStatus -eq "failed") {
                $flags = ($result.degrade_flags | ConvertTo-Json -Compress)
                throw "analysis reached failed terminal state; frontend/API must surface this explainably. degrade_flags=$flags"
            }
            $card = $result.decision_card
            if ($null -eq $card -or [string]::IsNullOrWhiteSpace($card.headline_judgement)) {
                throw "terminal analysis response did not include a renderable decision card"
            }
            if ($null -eq $card.supporting_evidence -or $null -eq $card.counter_evidence -or $null -eq $card.invalidation_conditions) {
                throw "terminal analysis response missing evidence/counter-evidence/invalidation fields"
            }
            Write-Host "analysis_terminal=$lastStatus"
            return
        }
        Start-Sleep -Seconds 2
    }
    throw "analysis did not reach a terminal state within ${PollTimeoutSeconds}s; last_status=$lastStatus"
}

Write-Host "`nRQ topology acceptance passed." -ForegroundColor Green
Write-Host "Verified: Redis ping, /health, /ready rq+redis, quick API enqueue, RQ job presence, independent worker terminal result, frontend reachability."
Write-Host "Worker command expected during this run:"
Write-Host "  cd F:\investment\investment-back; `$env:RQ_ASYNC='false'; `$env:REDIS_URL='$RedisUrl'; python -m src.workers"
