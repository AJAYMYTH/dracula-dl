@echo off
:: 🧛 The Dracula — Python PATH Fix Script
:: Run this ONCE as Administrator to fix "python not found" permanently

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  🧛 The Dracula — Python PATH Fix               ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: Set Python path
set PYTHON_DIR=C:\Users\javal\AppData\Local\Programs\Python\Python314
set PYTHON_SCRIPTS=%PYTHON_DIR%\Scripts

:: Add to system PATH for this session
set PATH=%PYTHON_DIR%;%PYTHON_SCRIPTS%;%PATH%

:: Permanently add to User PATH via setx
setx PATH "%PYTHON_DIR%;%PYTHON_SCRIPTS%;%PATH%" >nul 2>&1
echo  [OK] Python added to PATH permanently.

:: Disable Windows App Execution Alias for python/python3
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\python.exe" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\python3.exe" /f >nul 2>&1
echo  [OK] Python App Execution Aliases cleared.

:: Verify
echo.
echo  Testing python command...
"%PYTHON_DIR%\python.exe" --version
echo.
echo  Testing dracula tool...
"%PYTHON_DIR%\python.exe" "C:\Users\javal\Videos\Dracula\dracula.py" --help

echo.
echo  ══════════════════════════════════════════════════
echo  [DONE] All fixed! Open a NEW terminal and run:
echo         python dracula.py
echo         dracula
echo  ══════════════════════════════════════════════════
echo.
pause
