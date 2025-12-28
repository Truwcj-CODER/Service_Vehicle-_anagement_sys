@echo off
echo ========================================
echo    KIEM TRA MYSQL TRONG XAMPP
echo ========================================
echo.

echo [1] Dang kiem tra port 3306...
netstat -ano | findstr :3306 >nul
if %errorlevel% equ 0 (
    echo ✅ SUCCESS: MySQL dang chay tren port 3306
    netstat -ano | findstr :3306
    echo.
    goto :test_connection
) else (
    echo ❌ LOI: MySQL KHONG dang chay!
    echo.
    echo 🔧 Giai phap:
    echo    1. Mo XAMPP Control Panel
    echo    2. Click [Start] o dong MySQL
    echo    3. Cho MySQL start xong (mau xanh)
    echo    4. Chay lai script nay
    echo.
    goto :end
)

:test_connection
echo [2] Dang test ket noi MySQL...
mysql -u root -e "SELECT 'MySQL dang chay!' as status;" 2>nul
if %errorlevel% equ 0 (
    echo ✅ SUCCESS: Ket noi MySQL thanh cong!
    echo.
    echo ✅ MySQL da san sang!
    echo    Ban co the chay server: python app.py
) else (
    echo ❌ LOI: Khong ket noi duoc MySQL
    echo.
    echo 🔧 Thu ket noi co password:
    mysql -u root -p -e "SELECT 'Test' as status;" 2>nul
    if %errorlevel% equ 0 (
        echo ✅ MySQL co password - can nhap password
    ) else (
        echo ❌ Van khong ket noi duoc
    )
)

:end
echo.
echo ========================================
pause

