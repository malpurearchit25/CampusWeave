$ErrorActionPreference='Stop'
$projectPath=$PSScriptRoot
$pidFile=Join-Path $projectPath 'work\server.pid'
if (Test-Path -LiteralPath $pidFile) {
    $serverId=[int](Get-Content -LiteralPath $pidFile)
    $server=Get-CimInstance Win32_Process -Filter "ProcessId=$serverId" -ErrorAction SilentlyContinue
    if ($server -and $server.ExecutablePath -eq (Join-Path $projectPath '.venv\Scripts\python.exe') -and $server.CommandLine -match 'app.py') {
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$serverId" | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'app.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId }
        Stop-Process -Id $serverId
    }
}
# Database shutdown is graceful; committed data remains on disk.
& (Join-Path $projectPath '.venv\Scripts\python.exe') (Join-Path $projectPath 'scripts\stop_databases.py')
Write-Host 'CampusWeave stopped.'
