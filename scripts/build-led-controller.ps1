$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $repoRoot 'led_controller')
try {
    $ErrorActionPreference = 'Continue'
    python -m PyInstaller --noconfirm --windowed --onefile --name YSF4Pro_LED_Controller --distpath ../output/led_controller --workpath ../tmp/led_controller_build --specpath ../tmp --paths . app.py
    $buildCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($buildCode -ne 0) { throw 'LED controller packaging failed' }
} finally { Pop-Location }
