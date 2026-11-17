param([switch]$Flash)
$ErrorActionPreference='Stop'
$tools=Get-Content (Join-Path $env:LOCALAPPDATA 'STM32Tools/manifest.json') -Raw | ConvertFrom-Json
$env:PATH=((@('gcc','cmake','ninja','openocd') | ForEach-Object {Split-Path -Parent $tools.$_.exe}) -join ';')+';'+$env:PATH
$buildDir=Join-Path $PSScriptRoot 'build/Debug'
& $tools.cmake.exe -S $PSScriptRoot -B $buildDir -G Ninja "-DCMAKE_TOOLCHAIN_FILE=$PSScriptRoot/cmake/gcc-arm-none-eabi.cmake" -DCMAKE_BUILD_TYPE=Debug
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
& $tools.cmake.exe --build $buildDir --parallel
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
if($Flash){
    $elf=(Join-Path $buildDir 'YS_F4Pro_Combined.elf').Replace('\','/')
    & $tools.openocd.exe -f interface/cmsis-dap.cfg -c 'transport select swd' -f target/stm32f4x.cfg -c 'adapter speed 1000' -c "program {$elf} verify reset exit"
    exit $LASTEXITCODE
}
