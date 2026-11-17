$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $repoRoot 'upper_controller')
try {
    # PyInstaller logs progress to stderr; Windows PowerShell 5 must not
    # treat its informational output as a terminating script error.
    $ErrorActionPreference = 'Continue'
    python -m PyInstaller --noconfirm --windowed --onefile --name YSF4Pro_Controller --distpath ../output/upper_controller --workpath ../tmp/upper_controller_build --specpath ../tmp --paths . app.py
    $buildCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($buildCode -ne 0) { throw 'Controller packaging failed' }
} finally {
    Pop-Location
}
