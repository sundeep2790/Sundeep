@echo off
:: ============================================================
:: DataRescue - Windows Build Script
:: Run this from the repo root OR from the build\ directory.
:: Requirements: Python 3.11, pyinstaller (pip install -r requirements.txt)
:: ============================================================
setlocal

:: Resolve paths relative to this script's location
set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..
set SPEC=%SCRIPT_DIR%datarescue_win.spec
set DIST_DIR=%SCRIPT_DIR%dist
set WORK_DIR=%SCRIPT_DIR%work

:: Force working directory to script directory (build/) so relative paths in spec file resolve correctly
cd /d "%SCRIPT_DIR%"

echo.
echo ============================================================
echo  DataRescue for Windows - Build Pipeline
echo ============================================================
echo  Repo root : %REPO_ROOT%
echo  Spec file : %SPEC%
echo  Output    : %DIST_DIR%\DataRescue\
echo ============================================================
echo.

:: 1. Check Python and PyInstaller
echo [1/5] Checking Python launcher and PyInstaller...
set PYTHON_CMD=python
python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=py
    ) else (
        echo     ERROR: Python or py launcher not found on PATH!
        pause
        exit /b 1
    )
)
echo     Using python command: %PYTHON_CMD%

%PYTHON_CMD% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo     PyInstaller not found. Installing from requirements.txt...
    %PYTHON_CMD% -m pip install pyinstaller==6.6.0 --quiet
)
echo     PyInstaller OK

:: 2. Clean previous build artefacts
echo [2/5] Cleaning previous build artefacts...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
echo     OK

:: 3. Run PyInstaller
echo [3/5] Running PyInstaller (this takes 1-3 minutes)...
%PYTHON_CMD% -m PyInstaller "%SPEC%" ^
    --distpath "%DIST_DIR%" ^
    --workpath "%WORK_DIR%" ^
    --clean ^
    --noconfirm
if errorlevel 1 (
    echo.
    echo  ERROR: PyInstaller failed. Check the output above for details.
    pause
    exit /b 1
)
echo     OK - Output folder: %DIST_DIR%\DataRescue\

:: 4. Quick smoke-test: verify key files exist
echo [4/5] Verifying PyInstaller output...
if not exist "%DIST_DIR%\DataRescue\DataRescue.exe" (
    echo  ERROR: DataRescue.exe not found in output folder!
    pause
    exit /b 1
)
if not exist "%DIST_DIR%\DataRescue\_internal\binaries\win\photorec.exe" (
    if not exist "%DIST_DIR%\DataRescue\binaries\win\photorec.exe" (
        echo  WARNING: photorec.exe not found in output - recovery engine may not work.
    )
)
echo     OK

:: 5. Compile the Installer using Inno Setup if found
echo [5/5] Checking for Inno Setup compiler (ISCC.exe)...
set ISCC_PATH=

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else if exist "%USERPROFILE%\AppData\Local\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%USERPROFILE%\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
) else (
    rem Try checking PATH
    where ISCC.exe >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=*" %%I in ('where ISCC.exe') do (
            set "ISCC_PATH=%%I"
        )
    )
)

if "%ISCC_PATH%"=="" (
    echo     WARNING: Inno Setup compiler (ISCC.exe) not found.
    echo     To create the installer setup wizard, install Inno Setup 6 and run:
    echo     ISCC.exe "%SCRIPT_DIR%datarescue_installer.iss"
) else (
    echo     Found Inno Setup at: "%ISCC_PATH%"
    echo     Compiling installer (this takes a few seconds)...
    "%ISCC_PATH%" "%SCRIPT_DIR%datarescue_installer.iss"
    if errorlevel 1 (
        echo     ERROR: Inno Setup compilation failed!
        pause
        exit /b 1
    ) else (
        echo     OK - Installer generated successfully:
        echo     %SCRIPT_DIR%installer\DataRescue_Setup_1.0.0.exe
    )
)

echo.
echo ============================================================
echo  Build and Packaging COMPLETE.
echo ============================================================
echo.

:: Open installer folder in Explorer
if exist "%SCRIPT_DIR%installer" (
    explorer "%SCRIPT_DIR%installer"
) else (
    explorer "%DIST_DIR%\DataRescue\"
)
pause
endlocal

