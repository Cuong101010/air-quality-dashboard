@echo off
echo ========================================================
echo   Air Quality Dashboard - Local Development Server
echo ========================================================
echo.

set TF_ENABLE_ONEDNN_OPTS=0
set TF_CPP_MIN_LOG_LEVEL=2

echo [1/2] Kich hoat moi truong ao (.venv)...
call .venv\Scripts\activate.bat

echo [2/2] Dang khoi dong may chu Flask...
echo (Bam Ctrl+C de dung may chu)
echo.
python app.py

pause
