param([string]$Distribution = 'Ubuntu-22.04')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$projectRoot = Split-Path -Parent $PSScriptRoot
$linuxRoot = (& wsl.exe -d $Distribution --exec wslpath -u $projectRoot | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot start WSL. Install Ubuntu 22.04 first.' }
$proxy = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
if ($proxy.ProxyEnable -eq 1 -and $proxy.ProxyServer -match '^(127\.0\.0\.1|localhost):[0-9]+$') {
    $proxyUrl = 'http://' + $proxy.ProxyServer
    & wsl.exe -d $Distribution -u root --exec env "http_proxy=$proxyUrl" "https_proxy=$proxyUrl" bash "$linuxRoot/scripts/setup-asan.sh" $linuxRoot
} else {
    & wsl.exe -d $Distribution -u root --exec bash "$linuxRoot/scripts/setup-asan.sh" $linuxRoot
}
if ($LASTEXITCODE -ne 0) { throw 'ASan setup failed. See records/setup.' }
