@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

REM First try Windows Python launcher; fall back to python.exe in PATH.
where py >nul 2>&1
if not errorlevel 1 (
    py -3 start.py %*
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :done
)
where python >nul 2>&1
if not errorlevel 1 (
    python start.py %*
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :done
)
echo [XATO] Python 3.10+ topilmadi. https://www.python.org/downloads/
set "EXIT_CODE=1"
:done
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
