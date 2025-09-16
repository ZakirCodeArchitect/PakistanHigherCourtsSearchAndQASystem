@echo off
echo Activating virtual environment...
cd /d "%~dp0"
call qa_venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)
echo Virtual environment activated successfully!
echo Current directory: %cd%
echo Python path: %VIRTUAL_ENV%
echo You can now run Django commands like: python manage.py runserver
cmd /k
