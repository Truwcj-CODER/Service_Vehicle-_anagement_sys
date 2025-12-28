@echo off
echo ========================================
echo    KHOI DONG SERVER FASTAPI
echo ========================================
echo.

cd /d "%~dp0"

echo Dang kiem tra Python...
python --version
if errorlevel 1 (
    echo LOI: Python chua duoc cai dat!
    pause
    exit /b 1
)

echo.
echo Dang kiem tra MySQL...
netstat -ano | findstr :3306 >nul
if errorlevel 1 (
    echo CANH BAO: MySQL co the chua chay trong XAMPP!
    echo Hay kiem tra XAMPP Control Panel.
    echo.
)

echo.
echo Dang khoi dong server...
echo.
echo ========================================
echo  Truy cap tai: http://localhost:5000
echo ========================================
echo.
echo Nhan CTRL+C de dung server
echo.

python app.py

pause

