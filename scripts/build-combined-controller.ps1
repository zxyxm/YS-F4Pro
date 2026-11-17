$ErrorActionPreference='Stop'
$repoRoot=Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $repoRoot 'combined_controller')
try {
    $ErrorActionPreference='Continue'
    python -m PyInstaller --noconfirm --windowed --onefile --name YSF4Pro_Combined --distpath ../output/combined_controller --workpath ../tmp/combined_controller_build --specpath ../tmp --paths . app.py
    $buildCode=$LASTEXITCODE
    $ErrorActionPreference='Stop'
    if($buildCode -ne 0){throw 'Combined controller packaging failed'}
} finally {Pop-Location}
