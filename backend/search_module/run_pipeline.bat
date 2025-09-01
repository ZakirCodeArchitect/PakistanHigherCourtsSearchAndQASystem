@echo off
echo.
echo ========================================
echo    COMPLETE DATA PROCESSING PIPELINE
echo ========================================
echo.
echo This will run the complete pipeline after scraping new data
echo.
pause

echo.
echo Starting pipeline...
python run_complete_pipeline.py

echo.
echo Pipeline completed!
pause
