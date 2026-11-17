. "$PSScriptRoot/stm32-env.ps1"
& "$PSScriptRoot/stm32-build.ps1" -Action build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$repoRoot = Split-Path -Parent $PSScriptRoot
$elf = (Join-Path $repoRoot 'firmware/YS_F4Pro_Stepper/build/Debug/YS_F4Pro_Stepper.elf').Replace('\','/')
& $stm32Tools.openocd.exe -f interface/cmsis-dap.cfg -c 'transport select swd' -f target/stm32f4x.cfg -c 'adapter speed 1000' -c "program {$elf} verify reset exit"
exit $LASTEXITCODE
