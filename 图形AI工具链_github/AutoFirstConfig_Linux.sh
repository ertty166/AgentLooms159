#!/bin/bash

# 1. 显式设置环境变量，防止中文路径或输出乱码
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8

echo "========================================"
echo "      多智能体协作系统 - 初始化向导"
echo "========================================"
echo ""

# ============ 第一阶段：配置 Python ============
PYTHON_VERSION="3.11.8"
# 华为云 Python 3.11.8 镜像源
PYTHON_URL="https://mirrors.huaweicloud.com/python/3.11.8/python-3.11.8-amd64.exe"

echo "[阶段 1/3] Python 环境检测"

# 先让用户输入路径
read -p "请输入 Python 3.11.8 的完整路径: " PYTHON_PATH

# 检查用户输入的路径是否存在
if [ ! -f "$PYTHON_PATH" ]; then
    echo ""
    echo "[错误] 找不到指定的 Python 路径: $PYTHON_PATH"
    echo ""
    echo "[提示] 请检查路径是否正确，或点击下方链接下载安装"
    echo "下载链接: $PYTHON_URL"
    echo ""
    
    # 尝试自动打开浏览器（适配 Linux 常见的 xdg-open 和 macOS 的 open）
    if command -v xdg-open &> /dev/null; then
        xdg-open "$PYTHON_URL"
    elif command -v open &> /dev/null; then
        open "$PYTHON_URL"
    fi
    
    echo "已为你打开下载页面，请安装后重新运行本脚本"
    exit 1
fi

echo "[成功] Python 路径确认完毕"
echo ""

# ============ 第二阶段：配置 Ollama ============
echo "========================================"
echo "     [阶段 2/3] Ollama 环境配置"
echo "========================================"
echo ""

OLLAMA_CMD="ollama"

echo "[检测中] 正在检查 Ollama 是否已安装"
if ! command -v $OLLAMA_CMD &> /dev/null; then
    echo "[提示] 未检测到 Ollama"
    echo "正在为你打开官方下载页面，请下载并安装..."
    echo "下载链接: https://ollama.com/download"
    echo ""
    
    # 打开 Ollama 官方下载页
    if command -v xdg-open &> /dev/null; then
        xdg-open "https://ollama.com/download"
    elif command -v open &> /dev/null; then
        open "https://ollama.com/download"
    fi
    
    read -p "安装完成后，请按回车键继续..."
    
    # 再次检测
    if ! command -v $OLLAMA_CMD &> /dev/null; then
        echo "[警告] 未检测到 Ollama 运行环境，部分功能将受限"
        echo "请手动启动 Ollama 后再运行本工具"
    else
        echo "[成功] Ollama 安装检测通过"
    fi
else
    echo "[成功] Ollama 环境就绪"
fi
echo ""

# ============ 第三阶段：项目依赖与运行 ============
echo "========================================"
echo "     [阶段 3/3] 项目环境部署"
echo "========================================"
echo ""

# 创建虚拟环境
if [ -d "venv" ]; then
    echo "[提示] 虚拟环境已存在，跳过创建"
else
    echo "[创建] 正在创建 Python 虚拟环境"
    "$PYTHON_PATH" -m venv venv
    if [ $? -ne 0 ]; then
        echo "[错误] 虚拟环境创建失败"
        exit 1
    fi
    echo "[成功] 虚拟环境创建完成"
fi
echo ""

# 激活并安装依赖
echo "[安装] 正在激活虚拟环境并安装项目依赖"
source venv/bin/activate

echo "[安装] 正在升级 pip"
python -m pip install --upgrade pip > /dev/null 2>&1

if [ -f "requirements.txt" ]; then
    echo "[安装] 正在通过 requirements.txt 安装依赖库"
    python -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[警告] 部分依赖库安装可能失败，请检查网络"
    fi
else
    echo "[警告] 未找到 requirements.txt 文件，跳过依赖安装"
fi
echo ""

# 运行初始化脚本
echo "[运行] 正在启动初始化脚本"
if [ -f "初始化.py" ]; then
    python "初始化.py"
    if [ $? -ne 0 ]; then
        echo "[错误] 初始化脚本运行出错"
        exit 1
    fi
else
    echo "[错误] 找不到 初始化.py 文件"
    exit 1
fi

echo ""
echo "========================================"
echo "      系统初始化与启动全部完成！"
echo "========================================"