$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$runtimePath = Join-Path $projectPath 'runtime'
$workPath = Join-Path $projectPath 'work'
New-Item -ItemType Directory -Path $workPath -Force | Out-Null
function Listening([int]$port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
}
if (!(Test-Path -LiteralPath (Join-Path $projectPath '.env'))) {
    throw 'Local configuration is missing. Follow README.md setup instructions before starting.'
}
if (!(Listening 3307)) {
    $mysqlPath = Join-Path $runtimePath 'mysql-8.4.13-winx64'
    if (Test-Path -LiteralPath (Join-Path $mysqlPath 'bin\mysqld.exe')) {
        $baseArg = '--basedir=' + $mysqlPath.Replace('\','/')
        $dataArg = '--datadir=' + (Join-Path $runtimePath 'data').Replace('\','/')
        $logArg = '--log-error=' + (Join-Path $runtimePath 'mysql.log').Replace('\','/')
        $mysqlProcess = Start-Process -FilePath (Join-Path $mysqlPath 'bin\mysqld.exe') -ArgumentList '--no-defaults',$baseArg,$dataArg,'--port=3307','--bind-address=127.0.0.1','--mysqlx=OFF',$logArg -WindowStyle Hidden -PassThru
        $mysqlProcess.Id | Set-Content -LiteralPath (Join-Path $runtimePath 'mysql.pid')
    }
}
if (!(Listening 27018)) {
    $mongoPath = Join-Path $runtimePath 'mongodb-win32-x86_64-windows-8.0.29\bin\mongod.exe'
    if (Test-Path -LiteralPath $mongoPath) {
        $dataArg = '--dbpath=' + (Join-Path $runtimePath 'mongo-data').Replace('\','/')
        $logArg = '--logpath=' + (Join-Path $runtimePath 'mongo.log').Replace('\','/')
        $mongoProcess = Start-Process -FilePath $mongoPath -ArgumentList $dataArg,'--bind_ip=127.0.0.1','--port=27018','--auth',$logArg -WindowStyle Hidden -PassThru
        $mongoProcess.Id | Set-Content -LiteralPath (Join-Path $runtimePath 'mongo.pid')
    }
}
$pythonPath = Join-Path $projectPath '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Create the Python virtual environment and install requirements.txt first.' }
if (!(Listening 5050)) {
    $serverProcess = Start-Process -FilePath $pythonPath -ArgumentList 'app.py' -WorkingDirectory $projectPath -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $workPath 'server.out.log') -RedirectStandardError (Join-Path $workPath 'server.err.log')
    $serverProcess.Id | Set-Content -LiteralPath (Join-Path $workPath 'server.pid')
}
$ready = $false
for ($attempt=0; $attempt -lt 25; $attempt++) {
    try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:5050/health' -TimeoutSec 2; if ($health.status -eq 'ok') { $ready=$true; break } } catch { }
    Start-Sleep -Milliseconds 500
}
if (!$ready) { throw 'The application did not become ready. Inspect work/server.err.log and runtime/mysql.log.' }
Write-Host 'CampusWeave is ready: http://127.0.0.1:5050'
Write-Host 'Demo login: admin / CampusDemo!2026'
