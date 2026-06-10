"""
日志系统
"""
import logging
import sys
import datetime
import threading
import os
from PySide6.QtCore import QObject, Signal
from 核心_基础 import 信号


class 日志处理器(logging.Handler):
    def __init__(self):
        super().__init__()
    
    def emit(self, 记录):
        消息 = self.format(记录)
        信号.日志输出.emit(记录.levelname, 消息)


class 毫秒格式器(logging.Formatter):
    """自定义格式器，支持毫秒显示"""
    
    def formatTime(self, record, datefmt=None):
        """重写时间格式化，支持毫秒"""
        ct = datetime.datetime.fromtimestamp(record.created)
        
        if datefmt:
            # 将 %f 替换为毫秒（3位）
            if '%f' in datefmt:
                # 获取毫秒（微秒的前3位）
                ms = f"{ct.microsecond:06d}"[:3]
                datefmt = datefmt.replace('%f', ms)
            return ct.strftime(datefmt)
        else:
            # 默认格式
            return ct.strftime("%H:%M:%S.") + f"{ct.microsecond:06d}"[:3]


class 日志管理器(QObject):
    def __init__(self):
        super().__init__()
        self._记录器 = logging.getLogger("AI工具链")
        self._记录器.setLevel(logging.DEBUG)
        self._写入锁 = threading.Lock()
        # 确保日志目录存在
        self._日志目录 = "日志"
        os.makedirs(self._日志目录, exist_ok=True)
        
        # 获取今日日志文件路径
        self._日志文件路径 = self._获取日志文件路径()
        
        # 初始化时清空今日日志文件（覆盖模式）
        self._初始化日志文件()
        
        # 控制台输出（带毫秒）
        控制台 = logging.StreamHandler(sys.stdout)
        控制台.setFormatter(毫秒格式器(
            "%(asctime)s - %(levelname)s - %(message)s", 
            "%H:%M:%S.%f"  # %f 会被替换为3位毫秒
        ))
        self._记录器.addHandler(控制台)
        
        # Qt信号输出（带毫秒）
        Qt处理器 = 日志处理器()
        Qt处理器.setFormatter(毫秒格式器(
            "[%(asctime)s] %(levelname)s: %(message)s", 
            "%H:%M:%S.%f"  # %f 会被替换为3位毫秒
        ))
        self._记录器.addHandler(Qt处理器)
    
    def _获取日志文件路径(self) -> str:
        """根据当前日期生成日志文件路径"""
        今日日期 = datetime.datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self._日志目录, f"{今日日期}.log")
    
    def _初始化日志文件(self):
        """初始化时清空今日日志文件（覆盖模式写入空内容）"""
        with open(self._日志文件路径, 'w', encoding='utf-8') as f:
            f.write("")  # 覆盖清空
    
    def _写入文件日志(self, 级别: str, 消息: str):
        """将日志追加写入文件"""
        时间戳 = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        日志行 = f"[{时间戳}] {级别}: {消息}\n"
        #with self._写入锁:
        with open(self._日志文件路径, 'a', encoding='utf-8') as f:
            f.write(日志行)
    
    def 调试(self, 消息: str, 节点ID: str = None):
        前缀 = f"[{节点ID}] " if 节点ID else ""
        完整消息 = f"{前缀}{消息}"
        self._记录器.debug(完整消息)
        self._写入文件日志("DEBUG", 完整消息)
    
    def 信息(self, 消息: str, 节点ID: str = None):
        前缀 = f"[{节点ID}] " if 节点ID else ""
        完整消息 = f"{前缀}{消息}"
        self._记录器.info(完整消息)
        self._写入文件日志("INFO", 完整消息)
    
    def 警告(self, 消息: str, 节点ID: str = None):
        前缀 = f"[{节点ID}] " if 节点ID else ""
        完整消息 = f"{前缀}{消息}"
        self._记录器.warning(完整消息)
        self._写入文件日志("WARNING", 完整消息)
    
    def 错误(self, 消息: str, 节点ID: str = None):
        前缀 = f"[{节点ID}] " if 节点ID else ""
        完整消息 = f"{前缀}{消息}"
        self._记录器.error(完整消息)
        self._写入文件日志("ERROR", 完整消息)


日志 = 日志管理器()
