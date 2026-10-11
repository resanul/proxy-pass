@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo ProxyPilot v1.0 - Windows EXE builder
echo ========================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.11+ from python.org and enable the launcher.
  pause
  exit /b 1
)
py -3 -m venv .venv
if errorlevel 1 goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean --onefile --windowed --name ProxyPilot --version-file version_info.txt src\proxypilot.py
if errorlevel 1 goto :error
echo.
echo Build successful: dist\ProxyPilot.exe
echo Copy dist\ProxyPilot.exe to your deployment package.
pause
exit /b 0
:error
echo.
echo Build failed. Review the error output above.
pause
exit /b 1
