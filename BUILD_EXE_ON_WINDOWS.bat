@echo off
setlocal
cd /d "%~dp0"
echo Installing build dependency...
py -m pip install --upgrade pip
py -m pip install pyinstaller
if errorlevel 1 goto failed
echo Building Windows application...
py -m PyInstaller --noconfirm --clean --onefile --windowed --name Universal_Android_Service_Tool universal_android_service_tool.py
if errorlevel 1 goto failed
copy /Y profiles.json dist\profiles.json >nul
echo.
echo SUCCESS: dist\Universal_Android_Service_Tool.exe
echo Keep profiles.json in the same folder as the EXE.
pause
exit /b 0
:failed
echo.
echo Build failed. Install Python 3.10+ and ensure the "py" launcher is available.
pause
exit /b 1
