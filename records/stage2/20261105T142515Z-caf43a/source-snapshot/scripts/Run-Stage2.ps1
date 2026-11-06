param([switch]$PrecheckOnly, [string]$Distribution = 'Ubuntu-22.04')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not ('Stage2ExecutionState' -as [type])) {
    Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class Stage2ExecutionState {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint flags);
}
'@
}
$previousExecutionState = [Stage2ExecutionState]::SetThreadExecutionState([uint32]2147483651)
if ($previousExecutionState -eq 0) { throw 'Unable to prevent idle sleep during measurement.' }
try {
$power = Get-CimInstance Win32_Battery | Select-Object BatteryStatus,EstimatedChargeRemaining
@{ captured_at = (Get-Date).ToString('o'); battery = @($power); idle_sleep_prevention = 'Process-scoped ES_SYSTEM_REQUIRED + ES_DISPLAY_REQUIRED; no power policy change' } | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 "$projectRoot/config/stage2-host-power.json"
$linuxRoot = (& wsl.exe -d $Distribution --exec wslpath -u $projectRoot | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Unable to start Ubuntu.' }
$arguments = @("$linuxRoot/scripts/run_stage2.py")
if ($PrecheckOnly) { $arguments += '--precheck-only' }
& wsl.exe -d $Distribution --exec python3 @arguments
if ($LASTEXITCODE -ne 0) { throw 'Stage 2 failed; inspect records/stage2.' }
} finally {
    [void][Stage2ExecutionState]::SetThreadExecutionState([uint32]2147483648)
}
