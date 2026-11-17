param([switch]$Flash)
$ErrorActionPreference = 'Stop'
$toolFile = Join-Path $env:LOCALAPPDATA 'STM32Tools/manifest.json'
if (!(Test-Path -LiteralPath $toolFile)) { throw "Tool manifest missing: $toolFile" }
$toolset = Get-Content -LiteralPath $toolFile -Raw | ConvertFrom-Json
$bins = @('gcc','cmake','ninja','openocd') | ForEach-Object { Split-Path -Parent $toolset.$_.exe }
$env:PATH = ($bins -join ';') + ';' + $env:PATH
$buildDir = Join-Path $PSScriptRoot 'build/Debug'
$toolchain = Join-Path $PSScriptRoot 'cmake/gcc-arm-none-eabi.cmake'
& $toolset.cmake.exe -S $PSScriptRoot -B $buildDir -G Ninja "-DCMAKE_TOOLCHAIN_FILE=$toolchain" -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $toolset.cmake.exe --build $buildDir --parallel
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($Flash) {
    $elf = (Join-Path $buildDir 'YS_F4Pro_LED_Keys.elf').Replace('\','/')
    & $toolset.openocd.exe -f interface/cmsis-dap.cfg -c 'transport select swd' -f target/stm32f4x.cfg -c 'adapter speed 1000' -c "program {$elf} verify reset exit"
    exit $LASTEXITCODE
}
