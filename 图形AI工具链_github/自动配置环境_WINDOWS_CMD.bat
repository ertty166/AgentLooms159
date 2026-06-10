@echo off
:: ==========================================
:: 防闪退“金钟罩”
:: ==========================================
if not defined _IN_K_MODE (
    set "_IN_K_MODE=1"
    cmd /k ""%~f0" %*"
    exit /b
)
:: ==========================================

:: 设置编码为 UTF-8 以支持中文
chcp 65001 > nul
title 图形化AI工作流编排器 - 智能初始化向导

echo ========================================
echo      图形化AI工作流编排器 - 智能初始化
echo ========================================
echo.

:: ============ 第一阶段：配置 Python ============
set PYTHON_PATH=
set PYTHON_VERSION=3.11.8
set PYTHON_URL=https://mirrors.huaweicloud.com/python/3.11.8/python-3.11.8-amd64.exe

echo [阶段 1/3] Python 环境检测

:: 1. 先让用户输入路径
set /p PYTHON_PATH="请输入 Python3.11.8 的完整安装路径(例如->D:\Python安装位置\python-3.11.8\python.exe):"

:: 2. 检查用户输入的路径是否存在
if not exist "%PYTHON_PATH%" (
    echo.
    echo [错误] 找不到指定的 Python 路径: "%PYTHON_PATH%"
    echo.
    echo "[提示] 请检查路径是否正确，或点击下方链接下载安装"
    echo.
    :: 打开下载链接
    start "" "%PYTHON_URL%"
    echo.
    echo "已为你打开下载页面，请安装后重新运行本脚本"
    goto :END_SCRIPT
)

echo "[成功] Python 路径确认"
echo.


:: ============ 第二阶段：配置 Ollama ============
echo.
echo ========================================
echo      [阶段 2/3] Ollama 环境配置
echo ========================================
echo.

set OLLAMA_CMD=ollama

echo "[检测中] 正在检查 Ollama 是否已安装"
%OLLAMA_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo "[提示] 未检测到 Ollama。"
    echo "正在为你打开官方下载页面，请下载 Windows 版本并安装"
    echo "下载链接: https://ollama.com/download"
    echo.
    start https://ollama.com/download
    
    pause
    echo "[验证] 正在检查安装结果"
    
    %OLLAMA_CMD% --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo "[警告] 未检测到 Ollama 运行环境，部分功能将受限。"
        echo "请手动启动 Ollama 后再运行本工具。"
    ) else (
        echo "[成功] Ollama 安装检测通过。"
    )
) else (
    echo "[成功] Ollama 环境就绪。"
)

:: ============ 第三阶段：项目依赖与运行 ============
echo.
echo ========================================
echo      [阶段 3/3] 项目环境部署
echo ========================================
echo.

:: 创建虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo "[提示] 虚拟环境已存在，跳过创建。
) else (
    echo "[创建] 正在创建 Python 虚拟环境"
    "%PYTHON_PATH%" -m venv venv
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败。
        goto :END_SCRIPT
    )
    echo "[成功] 虚拟环境创建完成。"
)
echo.

:: 激活并安装依赖
call venv\Scripts\activate.bat
echo "[安装] 正在升级 pip"
python -m pip install --upgrade pip >nul 2>&1

if exist "requirements.txt" (
    echo "[安装] 正在安装 Python 依赖库"
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [警告] 依赖库安装可能失败，请检查网络。
    )
) else (
    echo "[警告] 未找到 requirements.txt。"
)

echo.
echo "[运行] 正在启动初始化脚本"
if exist "初始化.py" (
    python "初始化.py"
) else (
    echo "[错误] 找不到 初始化.py 文件。"
)

:END_SCRIPT
echo.
echo ========================================
echo      流程已结束
echo ========================================
pause >nul