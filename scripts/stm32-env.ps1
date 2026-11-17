$ErrorActionPreference = 'Stop'
$toolsRoot = Join-Path $env:LOCALAPPDATA 'STM32Tools'
$manifestPath = Join-Path $toolsRoot 'manifest.json'
if (!(Test-Path -LiteralPath $manifestPath)) {
    throw "STM32 tools manifest missing: $manifestPath"
}
$stm32Tools = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$toolBins = @('gcc', 'cmake', 'ninja', 'openocd') | ForEach-Object {
    Split-Path -Parent $stm32Tools.$_.exe
}
$env:PATH = ($toolBins -join ';') + ';' + $env:PATH
