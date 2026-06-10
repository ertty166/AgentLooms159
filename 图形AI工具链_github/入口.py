"""
AI工具链可视化编排平台 - 入口
"""
import sys
import os
import io
os.environ["PYTHONIOENCODING"] = "utf-8"

if sys.version_info < (3, 11):
    print(f"错误: 需要 Python 3.11+, 当前: {sys.version_info.major}.{sys.version_info.minor}")
    sys.exit(1)

from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QApplication

from 核心_基础 import 应用名
from 核心_日志 import 日志
from 界面_主窗 import 主窗

def 初始化编码():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    os.environ["PYTHONIOENCODING"] = "utf-8"

def main():
    初始化编码()
    
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling) # 新版本已自动开启
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps) # 新版本已自动开启
    
    应用 = QApplication(sys.argv)
    应用.setApplicationName(应用名)
    应用.setApplicationVersion("1.0.0")
    
    窗口 = 主窗()
    窗口.show()
    
    日志.信息(f"{应用名} 启动成功")
    
    sys.exit(应用.exec())

if __name__ == "__main__":
    main()
