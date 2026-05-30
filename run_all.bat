@echo off
chcp 65001 >nul
cd /d "%~dp0"

if "%1"=="" (
    echo 用法: run_all.bat ^<slot^>
    echo slot: morning / midday / close / us_close
    echo 示例: run_all.bat close
    exit /b
)

python -m auto_pilot.main %1

if %ERRORLEVEL% equ 0 (
    echo [OK] 完成
) else (
    if %ERRORLEVEL% equ 1 echo [ERROR] 失败
)
pause
