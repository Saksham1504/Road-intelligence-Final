Set-Location "$PSScriptRoot\frontend"
if (-not (Test-Path ".\node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm install
}
npm run dev -- --host 0.0.0.0 --port 5174
