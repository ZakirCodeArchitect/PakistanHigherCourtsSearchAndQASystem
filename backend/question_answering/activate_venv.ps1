Write-Host "Activating virtual environment..." -ForegroundColor Green
Set-Location $PSScriptRoot
& ".\qa_venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to activate virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to continue"
    exit 1
}
Write-Host "Virtual environment activated successfully!" -ForegroundColor Green
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
Write-Host "Python path: $env:VIRTUAL_ENV" -ForegroundColor Yellow
Write-Host "You can now run Django commands like: python manage.py runserver" -ForegroundColor Cyan
