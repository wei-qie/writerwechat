@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PYTHON_PATH=python
set SCRIPT_DIR=%CD%

echo ========================================
echo  创建 Windows 定时任务
echo ========================================
echo.
echo 将创建5个定时任务：
echo   1. 基市红绿灯_美股收盘 - 每天 05:00
echo   2. 基市红绿灯_盘前预览 - 每天 09:25
echo   3. 基市红绿灯_午间收盘 - 每天 11:30
echo   4. 基市红绿灯_收盘总结 - 每天 15:00
echo   5. 基市红绿灯_全时段   - 手动执行所有时段
echo.
echo 注意：周末不开市时，数据源可能返回空值
echo.

schtasks /create /tn "基市红绿灯_美股收盘" /tr "cd /d %SCRIPT_DIR% && %PYTHON_PATH% -m auto_pilot.main us_close" /sc daily /st 05:00 /f
schtasks /create /tn "基市红绿灯_盘前预览" /tr "cd /d %SCRIPT_DIR% && %PYTHON_PATH% -m auto_pilot.main morning" /sc daily /st 09:25 /f
schtasks /create /tn "基市红绿灯_午间收盘" /tr "cd /d %SCRIPT_DIR% && %PYTHON_PATH% -m auto_pilot.main midday" /sc daily /st 11:30 /f
schtasks /create /tn "基市红绿灯_收盘总结" /tr "cd /d %SCRIPT_DIR% && %PYTHON_PATH% -m auto_pilot.main close" /sc daily /st 15:00 /f

echo.
echo 定时任务创建完成！
echo 可在"任务计划程序"中查看和管理。
echo.
echo 手动运行示例：
echo   python -m auto_pilot.main close
echo.
pause
