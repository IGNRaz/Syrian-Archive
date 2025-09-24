@echo off
REM Syrian Archive API Test Runner for Windows
REM This batch file provides easy commands to run different types of tests

setlocal enabledelayedexpansion

if "%1"=="" goto :help
if "%1"=="help" goto :help
if "%1"=="--help" goto :help
if "%1"=="-h" goto :help

if "%1"=="all" goto :all
if "%1"=="django" goto :django
if "%1"=="standalone" goto :standalone
if "%1"=="install" goto :install
if "%1"=="server" goto :server
if "%1"=="quick" goto :quick

goto :help

:help
echo.
echo Syrian Archive API Test Runner
echo ==================================
echo.
echo Usage: test.bat [command]
echo.
echo Commands:
echo   all        - Run all tests (Django + Standalone)
echo   django     - Run only Django integrated tests
echo   standalone - Run only standalone HTTP tests
echo   install    - Install test dependencies
echo   server     - Start Django server and run all tests
echo   quick      - Quick test run (Django tests only)
echo   help       - Show this help message
echo.
echo Examples:
echo   test.bat all
echo   test.bat django
echo   test.bat server
echo.
goto :end

:install
echo Installing test dependencies...
python -m pip install -r test_requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    goto :end
)
echo Dependencies installed successfully!
goto :end

:all
echo Running all tests...
python run_tests.py
goto :end

:django
echo Running Django integrated tests...
python run_tests.py --django-only
goto :end

:standalone
echo Running standalone HTTP tests...
echo Make sure Django server is running at http://127.0.0.1:8000
python run_tests.py --standalone-only
goto :end

:server
echo Starting Django server and running all tests...
python run_tests.py --start-server
goto :end

:quick
echo Running quick Django tests...
python manage.py test tests.test_api_comprehensive --verbosity=2
goto :end

:end
endlocal