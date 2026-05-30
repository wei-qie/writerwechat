@echo off
chcp 65001 >nul
cd /d "%~dp0"

if "%1"=="" (
    echo 用法: publish_wechat.bat ^<slot^>
    echo slot: morning / midday / close / us_close
    echo.
    echo 首次使用前请先设置环境变量：
    echo   set WECHAT_APP_ID=你的AppID
    echo   set WECHAT_APP_SECRET=你的AppSecret
    echo.
    echo 也可在公众号后台 → 开发 → 基本配置 中获取
    echo.
    pause
    exit /b
)

python -m auto_pilot.main %1 --wechat

if %ERRORLEVEL% equ 0 (
    echo [OK] 草稿已创建，请登录微信公众平台后台 → 草稿箱 查看
) else (
    echo [ERROR] 失败
)
pause
