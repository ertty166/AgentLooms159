@echo off
title 系统主程序启动器
chcp 65001 > nul

:: 1. 激活虚拟环境
call venv\Scripts\activate.bat

:: 2. 检查激活是否成功
if errorlevel 1 (
    echo "[错误] 虚拟环境激活失败，请检查 venv 文件夹是否存在"
    pause
    exit /b
)

:: 3. 运行与 venv 同级的目标 Python 文件
echo "[正在启动] 系统主程序..."
python "入口.py"

:: 4. 程序退出后暂停，防止窗口闪退
echo.
pause