#!/bin/bash

# 1. 激活虚拟环境
source venv/bin/activate

# 2. 检查激活是否成功
if [ $? -ne 0 ]; then
    echo "[错误] 虚拟环境激活失败，请检查 venv 文件夹是否存在"
    exit 1
fi

# 3. 运行与 venv 同级的目标 Python 文件
echo "[正在启动] 系统主程序..."
python "入口.py"