@echo off

echo Installing PIX file format support...

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

set INSTALL_DIR=%~dp0
set INSTALL_DIR=%INSTALL_DIR:~0,-1%

echo Install directory: %INSTALL_DIR%

reg add "HKCR\.pix" /ve /d "PIXFile" /f
reg add "HKCR\.pix" /v "Content Type" /d "image/pix" /f
reg add "HKCR\.pix" /v "PerceivedType" /d "image" /f

reg add "HKCR\PIXFile" /ve /d "PIX Image File" /f
reg add "HKCR\PIXFile\DefaultIcon" /ve /d "%%SystemRoot%%\System32\imageres.dll,-67" /f

reg add "HKCR\PIXFile\shell" /ve /d "open" /f
reg add "HKCR\PIXFile\shell\open" /ve /d "&View" /f
reg add "HKCR\PIXFile\shell\open\command" /ve /d "\"%INSTALL_DIR%\view.bat\" \"%%1\"" /f

reg add "HKCR\PIXFile\shell\edit" /ve /d "&Edit with PIX Editor" /f
reg add "HKCR\PIXFile\shell\edit\command" /ve /d "\"%INSTALL_DIR%\editor.bat\" \"%%1\"" /f

reg add "HKCR\Applications\view.bat" /v "FriendlyAppName" /d "PIX Viewer" /f
reg add "HKCR\Applications\view.bat\shell\open\command" /ve /d "\"%INSTALL_DIR%\view.bat\" \"%%1\"" /f
reg add "HKCR\Applications\view.bat\SupportedTypes" /v ".pix" /d "" /f

reg add "HKCR\Applications\editor.bat" /v "FriendlyAppName" /d "PIX Editor" /f
reg add "HKCR\Applications\editor.bat\shell\open\command" /ve /d "\"%INSTALL_DIR%\editor.bat\" \"%%1\"" /f
reg add "HKCR\Applications\editor.bat\SupportedTypes" /v ".pix" /d "" /f

reg add "HKCR\Applications\to_pix.bat" /v "FriendlyAppName" /d "Convert to PIX" /f
reg add "HKCR\Applications\to_pix.bat\shell\open\command" /ve /d "\"%INSTALL_DIR%\to_pix.bat\" \"%%1\"" /f
reg add "HKCR\Applications\to_pix.bat\SupportedTypes" /v ".pix" /d "" /f

reg add "HKCR\Applications\from_pix.bat" /v "FriendlyAppName" /d "Convert to PNG" /f
reg add "HKCR\Applications\from_pix.bat\shell\open\command" /ve /d "\"%INSTALL_DIR%\from_pix.bat\" \"%%1\"" /f
reg add "HKCR\Applications\from_pix.bat\SupportedTypes" /v ".pix" /d "" /f

reg add "HKCR\.pix\OpenWithList\view.bat" /f
reg add "HKCR\.pix\OpenWithList\editor.bat" /f
reg add "HKCR\.pix\OpenWithList\from_pix.bat" /f
reg add "HKCR\.png\OpenWithList\to_pix.bat" /f
reg add "HKCR\.pix\OpenWithProgids" /v "PIXFile" /d "" /f

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pix\UserChoice" /v "Hash" /d "" /f
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pix\UserChoice" /v "ProgId" /d "PIXFile" /f

taskkill /f /im explorer.exe >nul 2>&1
timeout /t 2 >nul
start explorer.exe

ie4uinit.exe -show >nul 2>&1
ie4uinit.exe -ClearIconCache >nul 2>&1

echo.
echo PIX file format installed successfully!
echo.
echo To uninstall, run uninstall_pix.bat as administrator.
pause