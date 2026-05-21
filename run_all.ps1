$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$javaRoot = Join-Path $root "java_stats_service"
$javaOut = Join-Path $javaRoot "out"
$javaSrc = Join-Path $javaRoot "src\StatsServer.java"

if (!(Test-Path $javaOut)) {
    New-Item -ItemType Directory -Path $javaOut | Out-Null
}

javac -encoding UTF-8 -d $javaOut $javaSrc

$javaRunning = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue
if (!$javaRunning) {
    Start-Process -FilePath java -ArgumentList @("-cp", $javaOut, "StatsServer") -WorkingDirectory $javaRoot -WindowStyle Hidden
}

$env:JAVA_STATS_BASE_URL = "http://127.0.0.1:8081"
$env:PYTHONIOENCODING = "utf-8"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
