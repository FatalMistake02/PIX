@echo off
echo Uninstalling PIX file format support...

reg delete "HKCR\.pix" /f >nul 2>&1

reg delete "HKCR\PIXFile" /f >nul 2>&1

reg delete "HKLM\SOFTWARE\Classes\Applications\view.bat" /f >nul 2>&1

reg delete "HKLM\SOFTWARE\Classes\.pix" /f >nul 2>&1

taskkill /f /im explorer.exe >nul 2>&1
start explorer.exe

echo.
echo PIX file format uninstalled successfully!
echo.
pause