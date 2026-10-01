param(
    [string]$Game = 'D:\Software\Steam\steamapps\common\Hearts of Iron IV'
)

$ErrorActionPreference = 'Stop'
$userDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\Hearts of Iron IV'
$selection = Join-Path $userDir 'dlc_load.json'
$backup = "$selection.codex-telemetry-backup"
$descriptor = Join-Path $userDir 'mod\codex_telemetry.mod'
$log = Join-Path $userDir 'logs\game.log'

if (Get-Process -Name hoi4 -ErrorAction SilentlyContinue) { throw 'HOI4 is already running.' }
if (-not (Test-Path -LiteralPath (Join-Path $Game 'hoi4.exe'))) { throw "Game not found: $Game" }
if (-not (Test-Path -LiteralPath $descriptor)) { throw 'Install the Telemetry Mod first.' }
if (-not (Test-Path -LiteralPath $selection)) { throw "Mod selection not found: $selection" }
if (Test-Path -LiteralPath $backup) { throw "Inspect existing backup before launch: $backup" }

$original = [System.IO.File]::ReadAllBytes($selection)
[System.IO.File]::WriteAllBytes($backup, $original)
try {
    $config = [System.Text.Encoding]::UTF8.GetString($original) | ConvertFrom-Json
    $config.enabled_mods = @('mod/codex_telemetry.mod')
    [System.IO.File]::WriteAllText(
        $selection, ($config | ConvertTo-Json -Compress), [System.Text.UTF8Encoding]::new($false)
    )
    $started = Get-Date
    $process = Start-Process -FilePath (Join-Path $Game 'hoi4.exe') `
        -WorkingDirectory $Game -WindowStyle Normal -PassThru
    Write-Output "HOI4 launched: PID $($process.Id)"

    $deadline = $started.AddSeconds(120)
    $loaded = $false
    while ((Get-Date) -lt $deadline) {
        if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).LastWriteTime -gt $started) {
            $tail = Get-Content -LiteralPath $log -Tail 80 -ErrorAction SilentlyContinue
            if ($tail -match 'Loading map|Executing|codex_telemetry') {
                $loaded = $true
                break
            }
        }
        if ($process.HasExited) { break }
        Start-Sleep -Seconds 1
    }
    Write-Output "Game startup log observed: $loaded"
} finally {
    [System.IO.File]::WriteAllBytes($selection, $original)
    Remove-Item -LiteralPath $backup
    Write-Output 'Original Mod selection restored.'
}
