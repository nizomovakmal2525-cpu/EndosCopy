$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $root "src\StatsServer.java"
$out = Join-Path $root "out"

if (!(Test-Path $out)) {
    New-Item -ItemType Directory -Path $out | Out-Null
}

javac -encoding UTF-8 -d $out $src
java -cp $out StatsServer
