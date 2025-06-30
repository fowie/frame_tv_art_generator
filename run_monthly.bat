@echo off
REM Frame TV Art Generator - Monthly Batch Script
REM This script can be scheduled to run monthly using Windows Task Scheduler

echo ========================================
echo Frame TV Art Generator - Monthly Run
echo ========================================
echo Starting at %date% %time%

REM Change to the script directory
cd /d "%~dp0"

REM Set your Bing authentication cookie here
REM Get this from https://www.bing.com/create browser cookies (_U value)
set BING_COOKIE=YOUR_BING_COOKIE_HERE

REM Check if cookie is set
if "%BING_COOKIE%"=="YOUR_BING_COOKIE_HERE" (
    echo ERROR: Please set your Bing authentication cookie in this script
    echo Edit run_monthly.bat and replace YOUR_BING_COOKIE_HERE with your actual cookie
    echo.
    echo To get your cookie:
    echo 1. Go to https://www.bing.com/create
    echo 2. Sign in with Microsoft account
    echo 3. Open Developer Tools ^(F12^)
    echo 4. Go to Application/Storage - Cookies - bing.com
    echo 5. Copy the '_U' cookie value
    pause
    exit /b 1
)

REM Run the art generation
echo Running art generation...
python main.py --run --cookie "%BING_COOKIE%" --num-images 5

REM Check if successful
if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo SUCCESS: Art generation completed!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR: Art generation failed!
    echo Check the logs directory for details
    echo ========================================
)

echo Completed at %date% %time%

REM Uncomment the line below if you want to see the results when run manually
REM pause
