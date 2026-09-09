Set-Location "$PSScriptRoot\backend"
if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    $env:DATABASE_URL = "postgresql+psycopg2://sih_admin:sih12345@localhost:5432/road_intelligence"
}
 $python = ".\.venv\Scripts\python.exe"
 $pythonReady = Test-Path $python
 if ($pythonReady) {
     & $python -c "import sys" 2>$null
     $pythonReady = $LASTEXITCODE -eq 0
 }
if (-not $pythonReady) {
    Write-Host "Creating virtual environment..."
    py -3 -m venv .venv --clear
}
& $python -m pip install -r requirements.txt
& $python -m uvicorn main:app --host 0.0.0.0 --port 8000
