param([ValidateSet('configure', 'build')][string]$Action = 'build')
. "$PSScriptRoot/stm32-env.ps1"
$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceDir = Join-Path $repoRoot 'firmware/YS_F4Pro_Stepper'
$buildDir = Join-Path $sourceDir 'build/Debug'
if (!(Test-Path -LiteralPath "$sourceDir/CMakeLists.txt")) {
    throw "Generate the CubeMX CMake project at $sourceDir first. See the VS Code setup guide in docs/."
}
$toolchain = Join-Path $sourceDir 'cmake/gcc-arm-none-eabi.cmake'
if (!(Test-Path -LiteralPath $toolchain)) {
    throw "CubeMX GCC toolchain file missing: $toolchain"
}
& $stm32Tools.cmake.exe -S $sourceDir -B $buildDir -G Ninja "-DCMAKE_TOOLCHAIN_FILE=$toolchain" -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($Action -eq 'build') {
    & $stm32Tools.cmake.exe --build $buildDir --parallel
    exit $LASTEXITCODE
}
