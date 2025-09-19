@echo off
setlocal EnableDelayedExpansion
title EY Dashboard - Universal Launcher
color 0a

echo ========================================
echo    EY DASHBOARD UNIVERSAL LAUNCHER
echo ========================================
echo.

:: Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Check if we're running from a network drive
echo %SCRIPT_DIR% | findstr /C:":" >nul
if errorlevel 1 (
    echo ⚠️  Running from network drive detected
) else (
    echo %SCRIPT_DIR% | findstr /R "^[A-Z]:" >nul
    if not errorlevel 1 (
        echo %SCRIPT_DIR:~0,1% | findstr /R "[X-Z]" >nul
        if not errorlevel 1 (
            echo ⚠️  Potential network drive detected: %SCRIPT_DIR:~0,1%:
        )
    )
)

echo 📁 Project location: %SCRIPT_DIR%
echo.

:: Step 1: Find Python
echo Step 1: Locating Python...
echo ----------------------------------------

set "PYTHON_EXE="

:: Try python in PATH first
python --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        set "PYTHON_EXE=%%i"
        goto :found_python
    )
)

:: Try py launcher
py --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('where py 2^>nul') do (
        set "PYTHON_EXE=%%i"
        goto :found_python
    )
)

:: Search common directories
echo 🔍 Searching for Python installations...

:: Check AppData Local
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\python.exe" (
        set "PYTHON_EXE=%%D\python.exe"
        goto :found_python
    )
)

:: Check Program Files
for /d %%D in ("%PROGRAMFILES%\Python*") do (
    if exist "%%D\python.exe" (
        set "PYTHON_EXE=%%D\python.exe"
        goto :found_python
    )
)

:: No Python found
echo ❌ Python not found
echo.
echo Please install Python from: https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation
goto :end

:found_python
echo ✅ Found Python: !PYTHON_EXE!

:: Get Python version
for /f "tokens=2" %%v in ('"!PYTHON_EXE!" --version 2^>^&1') do set "PYTHON_VERSION=%%v"
echo 🐍 Version: !PYTHON_VERSION!
echo.

:: Step 2: Setup environment
echo Step 2: Environment Setup...
echo ----------------------------------------

:: Determine local cache directory for virtual environment
set "LOCAL_VENV_DIR=%LOCALAPPDATA%\EYDashboard\venv"
echo 🏠 Using local virtual environment: !LOCAL_VENV_DIR!

:: Create local directory if it doesn't exist
if not exist "%LOCALAPPDATA%\EYDashboard" (
    mkdir "%LOCALAPPDATA%\EYDashboard"
    echo 📁 Created local cache directory
)

:: Check if virtual environment exists
if not exist "!LOCAL_VENV_DIR!\Scripts\python.exe" (
    echo 🔧 Creating virtual environment...
    "!PYTHON_EXE!" -m venv "!LOCAL_VENV_DIR!"
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        echo 💡 Trying alternative method...
        
        :: Try without venv module
        "!PYTHON_EXE!" -c "import venv; venv.create('!LOCAL_VENV_DIR!', with_pip=True)"
        if errorlevel 1 (
            echo ❌ Virtual environment creation failed
            echo 🚫 Running with system Python instead
            set "VENV_PYTHON=!PYTHON_EXE!"
            goto :install_requirements
        )
    )
    echo ✅ Virtual environment created
)

:: Set virtual environment Python
set "VENV_PYTHON=!LOCAL_VENV_DIR!\Scripts\python.exe"
if not exist "!VENV_PYTHON!" (
    echo ⚠️  Virtual environment Python not found, using system Python
    set "VENV_PYTHON=!PYTHON_EXE!"
)

:install_requirements
echo.
echo Step 3: Installing Requirements...
echo ----------------------------------------

:: Check if requirements.txt exists
if not exist "%SCRIPT_DIR%requirements.txt" (
    echo ⚠️  requirements.txt not found, skipping...
    goto :launch_django
)

echo 📦 Installing Python packages...
"!VENV_PYTHON!" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo ⚠️  Pip upgrade failed, continuing anyway...
)

"!VENV_PYTHON!" -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet
if errorlevel 1 (
    echo ⚠️  Some packages failed to install, trying to continue...
) else (
    echo ✅ Requirements installed successfully
)

:launch_django
echo.
echo Step 4: Launching Django Server...
echo ----------------------------------------

:: Verify manage.py exists
if not exist "%SCRIPT_DIR%manage.py" (
    echo ❌ manage.py not found in %SCRIPT_DIR%
    echo Please ensure you're running from the correct directory
    goto :end
)

:: Change to script directory (important for Django)
cd /d "%SCRIPT_DIR%"

echo 🚀 Starting Django development server on port 8001...
echo 🌐 Dashboard will be available at: http://127.0.0.1:8001
echo.

:: Start Django server
"!VENV_PYTHON!" manage.py runserver 8001

:: If we get here, the server has stopped
echo.
echo ✅ Django server stopped

goto :end

:end
echo.
echo Press any key to exit...
pause >nul
