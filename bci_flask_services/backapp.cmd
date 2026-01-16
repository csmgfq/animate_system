@echo off
echo ========================================
echo   BCI Flask Service Startup
echo ========================================

cd /d "%~dp0"
echo Current directory: %cd%

echo.
echo Starting Flask service (conda env: bci)...
conda run -n bci --no-capture-output python app.py

echo.
echo Program exited
pause
