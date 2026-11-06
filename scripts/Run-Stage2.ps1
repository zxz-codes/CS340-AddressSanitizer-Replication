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
else { $arguments += '--defer-host-review' }
& wsl.exe -d $Distribution --exec python3 @arguments
if ($LASTEXITCODE -ne 0) { throw 'Stage 2 failed; inspect records/stage2.' }
if (-not $PrecheckOnly) {
    $relativeRecord = (Get-Content -Raw -LiteralPath "$projectRoot/tmp/stage2-pending-record.txt").Trim()
    if ($relativeRecord -notmatch '^records/stage2/[0-9TZ-]+[a-f0-9]+$') { throw 'Invalid pending record path.' }
    $recordPath = Join-Path $projectRoot $relativeRecord
    $protocol = Get-Content -Raw -LiteralPath "$recordPath/protocol.json" | ConvertFrom-Json
    Get-WinEvent -ListLog System -ErrorAction Stop | Out-Null
    $queryEnd = Get-Date
    $sleepEvents = @(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Microsoft-Windows-Kernel-Power';Id=42,107,506,507;StartTime=[datetime]::Parse($protocol.started_utc);EndTime=$queryEnd} -ErrorAction SilentlyContinue | Select-Object TimeCreated,Id,Message)
    @{applicable=$true;passed=($sleepEvents.Count -eq 0);events=$sleepEvents;started_utc=$protocol.started_utc;query_ended_utc=$queryEnd.ToUniversalTime().ToString('o');query_context='Windows host PowerShell'} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 "$recordPath/environment/host-sleep-review.json"
    if ($sleepEvents.Count -ne 0) { throw 'Host sleep interrupted experiment; entire batch excluded.' }
    & wsl.exe -d $Distribution --exec python3 "$linuxRoot/scripts/run_stage2.py" --finalize-record "$linuxRoot/$relativeRecord"
    if ($LASTEXITCODE -ne 0) { throw 'Stage 2 final verification failed.' }
}
} finally {
    [void][Stage2ExecutionState]::SetThreadExecutionState([uint32]2147483648)
}
