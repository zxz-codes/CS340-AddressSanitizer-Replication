param([int]$Runs = 5, [string]$Distribution = 'Ubuntu-22.04')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$projectRoot = Split-Path -Parent $PSScriptRoot
$linuxRoot = (& wsl.exe -d $Distribution --exec wslpath -u $projectRoot | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Unable to start Ubuntu.' }
& wsl.exe -d $Distribution --exec python3 "$linuxRoot/scripts/run_stage1.py" --runs $Runs
if ($LASTEXITCODE -ne 0) { throw 'Stage 1 failed. Inspect the new records/stage1 directory.' }
