@echo off
echo 🏛️ Pakistan Higher Courts Search & QA System - Frontend
echo ======================================================
echo.

echo Starting Django development server...
echo.

cd ..
python manage.py runserver

echo.
echo Frontend is now running at: http://localhost:8000
echo Login with: admin / admin123
echo.
pause
