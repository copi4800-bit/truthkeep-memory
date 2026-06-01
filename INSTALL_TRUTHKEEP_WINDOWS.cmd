@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo ============================================================
echo  TruthKeep Enterprise Easy Installer - Windows
echo ============================================================
echo  Local-only. No HTTP daemon. No open ports. OpenClaw MCP stdio.
echo.

where python >nul 2>nul
if errorlevel 1 goto no_python

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 goto old_python

python -m pip install --upgrade pip
if errorlevel 1 goto pip_fail

python -m pip install -e .
if errorlevel 1 goto install_fail

python -m truthkeep.cli easy install
if errorlevel 1 goto setup_fail

python -m truthkeep.cli openclaw install
if errorlevel 1 goto openclaw_fail

python -m truthkeep.cli openclaw doctor
if errorlevel 1 goto doctor_fail

echo.
echo [OK] TruthKeep is installed and OpenClaw Easy Mode is ready.
echo Restart OpenClaw, then use: memory_status, memory_remember, memory_recall, memory_correct, memory_profile
echo.
pause
exit /b 0

:no_python
echo [ERROR] Python was not found. Install Python 3.11+ and tick "Add Python to PATH".
pause
exit /b 1

:old_python
echo [ERROR] Python 3.11+ is required.
pause
exit /b 1

:pip_fail
echo [ERROR] pip upgrade failed. Check internet/proxy/permissions.
pause
exit /b 1

:install_fail
echo [ERROR] TruthKeep package install failed.
pause
exit /b 1

:setup_fail
echo [ERROR] TruthKeep Easy Mode setup failed.
pause
exit /b 1

:openclaw_fail
echo [ERROR] OpenClaw configuration failed.
pause
exit /b 1

:doctor_fail
echo [ERROR] OpenClaw doctor found a problem. Run: python -m truthkeep.cli repair
pause
exit /b 1
