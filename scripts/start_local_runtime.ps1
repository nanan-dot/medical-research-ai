[CmdletBinding()]
param(
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$logDirectory = Join-Path $projectRoot "work\runtime-logs"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Project Python runtime not found: $python"
}
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

function Start-SuwenProcess {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [string]$Executable,
        [Parameter(Mandatory)] [string[]]$Arguments,
        [Parameter(Mandatory)] [string]$Signature,
        [Parameter(Mandatory)] [string]$WorkingDirectory
    )
    $running = Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine.Contains($Signature)
    } | Select-Object -First 1
    if ($running) {
        Write-Host "$Name already running (PID $($running.ProcessId))"
        return
    }
    $stdout = Join-Path $logDirectory "$Name.stdout.log"
    $stderr = Join-Path $logDirectory "$Name.stderr.log"
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    Write-Host "$Name started (PID $($process.Id))"
}

$env:PYTHONPATH = ""
Start-SuwenProcess "api" $python @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") "uvicorn app.main:app" $projectRoot
Start-SuwenProcess "document-worker" $python @("-m", "app.cli.document_task_worker") "app.cli.document_task_worker" $projectRoot
Start-SuwenProcess "anchor-worker" $python @("-m", "app.cli.document_anchor_worker") "app.cli.document_anchor_worker" $projectRoot
Start-SuwenProcess "layout-worker" $python @("-m", "app.cli.document_layout_worker") "app.cli.document_layout_worker" $projectRoot
Start-SuwenProcess "translation-worker" $python @("-m", "app.cli.medical_translation_worker") "app.cli.medical_translation_worker" $projectRoot

if (-not $NoFrontend) {
    Start-SuwenProcess "frontend" $npm @("run", "dev", "--", "--host", "127.0.0.1") "vite --host 127.0.0.1" (Join-Path $projectRoot "frontend")
}

Write-Host "Runtime logs: $logDirectory"
Write-Host "Reader: http://127.0.0.1:5173"
Write-Host "API health: http://127.0.0.1:8000/api/v1/health"
