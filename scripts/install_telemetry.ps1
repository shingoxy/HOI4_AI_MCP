param(
    [string]$UserDir = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Paradox Interactive\Hearts of Iron IV')
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$modRoot = Join-Path $projectRoot 'mod\codex_telemetry'
$modDir = Join-Path $UserDir 'mod'
$launcherFile = Join-Path $modDir 'codex_telemetry.mod'
$modPath = $modRoot.Replace('\', '/')
$descriptor = "name=`"Codex Read-only Telemetry`"`npath=`"$modPath`"`nsupported_version=`"1.19.3`"`n"

if (-not (Test-Path -LiteralPath (Join-Path $modRoot 'descriptor.mod'))) {
    throw "Mod source missing: $modRoot"
}
New-Item -ItemType Directory -Path $modDir -Force | Out-Null
if (Test-Path -LiteralPath $launcherFile) {
    $existing = Get-Content -LiteralPath $launcherFile -Raw
    if ($existing -ne $descriptor) {
        throw "Existing launcher descriptor differs: $launcherFile"
    }
} else {
    [System.IO.File]::WriteAllText($launcherFile, $descriptor, [System.Text.UTF8Encoding]::new($false))
}
Write-Output "Telemetry Mod descriptor: $launcherFile"
Write-Output "Mod source: $modRoot"
