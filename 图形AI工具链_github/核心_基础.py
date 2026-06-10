"""
基础配置、全局信号、状态管理
"""
import sys
import os
from pathlib import Path
from enum import Enum, auto
from PySide6.QtCore import QObject, Signal, QStandardPaths
import _tools as tools
import json
import uuid
import base64
from datetime import datetime, timezone

# ========== 版本配置 ==========
PY版本要求 = (3, 11)
QT版本要求 = (6, 6, 0)
应用名 = "AI工具链"
应用版本 = "1.0.0"

# ========== 路径 ==========
def 取应用目录() -> Path:
    return Path(__file__).parent.parent

def 取插件目录() -> Path:
    目录 = Path(tools.search_folder_in(1,"插件"))
    目录.mkdir(exist_ok=True)
    return 目录

def 取配置目录() -> Path:
    目标路径 = Path(tools.search_folder_in("图形AI工具链_github","AI工具链配置"))
    目标路径.mkdir(parents=True, exist_ok=True)
    return 目标路径

# ========== 画布配置 ==========
画布网格大小 = 20
画布最小缩放 = 0.1
画布最大缩放 = 5.0

# ========== 节点配置 ==========
节点宽度 = 180
节点高度 = 80

# ========== 状态枚举 ==========
class 流程状态(Enum):
    空闲 = auto()
    运行中 = auto()
    暂停 = auto()
    单步 = auto()
    错误 = auto()

class 节点状态(Enum):
    空闲 = "#808080" # 刚创建未初始化
    就绪 = "#00AA00" # 初始化完成运行正常可以传入内容
    运行中 = "#0088FF" # 正在工作阻塞后续内容传入
    等待中 = "#FFAA00" # 正在等待例如其他数据或者工具返回
    错误 = "#FF0000" # 插件错误
    禁用 = "#404040" # 插件被禁用,用于处理恶意代码

# ========== 全局信号 ==========
class 全局信号(QObject):
    # 节点
    节点创建 = Signal(str, object)
    节点删除 = Signal(str)
    节点选中 = Signal(str)
    节点移动 = Signal(str, object)
    节点状态变更 = Signal(str, str)
    # 连线
    连线创建 = Signal(str, str, str, str)
    连线删除 = Signal(object)
    # 流程
    流程启动 = Signal()
    流程停止 = Signal()
    流程暂停 = Signal()
    # 插件
    插件加载 = Signal(str, object)
    插件卸载 = Signal(str)
    插件错误 = Signal(str, str)
    # 进程
    进程启动 = Signal(str, int)
    进程结束 = Signal(str, int)
    进程输出 = Signal(str, object)
    进程错误 = Signal(str, str)
    # 日志
    日志输出 = Signal(str, str)
    # 新增：数据传递请求信号
    请求传递数据 = Signal(str, dict)  # 源节点ID, 协议包
信号 = 全局信号()


# ========== 状态管理器 ==========
class 状态管理器(QObject):
    流程状态变更 = Signal(object)
    节点状态变更 = Signal(str, object)
    选中变更 = Signal(list)
    
    def __init__(self):
        super().__init__()
        self._流程状态 = 流程状态.空闲
        self._节点状态: dict = {}
        self._选中节点: set = set()
        self._节点数据: dict = {} # 20260424 # {节点ID:[数据1,数据2]}
        self._连线: dict = {}
        self._节点对象: dict = {}  # 新增：存储节点实例引用
    
    # 流程状态
    @property
    def 流程状态值(self):
        return self._流程状态
    
    def 置流程状态(self, 状态):
        if self._流程状态 != 状态:
            self._流程状态 = 状态
            self.流程状态变更.emit(状态)
    
    # 节点状态
    def 取节点状态(self, 节点ID: str):
        return self._节点状态.get(节点ID, 节点状态.空闲)
    
    def 置节点状态(self, 节点ID: str, 状态):
        if self._节点状态.get(节点ID) != 状态:
            self._节点状态[节点ID] = 状态
            self.节点状态变更.emit(节点ID, 状态)
    
    # 选中管理
    def 选中节点(self, 节点ID: str, 清空其他=True):
        if 清空其他:
            self._选中节点.clear()
        self._选中节点.add(节点ID)
        self.选中变更.emit(list(self._选中节点))
    
    def 取消选中(self, 节点ID: str):
        self._选中节点.discard(节点ID)
        self.选中变更.emit(list(self._选中节点))
    
    def 清空选中(self):
        self._选中节点.clear()
        self.选中变更.emit([])
    
    def 是否选中(self, 节点ID: str) -> bool:
        return 节点ID in self._选中节点
    
    @property
    def 选中列表(self) -> list:
        return list(self._选中节点)
    
    # 节点数据
    def 置节点数据(self, 节点ID: str, 数据):
        """能缓存一个数据列表"""
        数据列表 = self._节点数据.get(节点ID, None)
        if not isinstance(数据列表,list) or 数据 is None:
            # 无论是初始化还是销毁信息,都是在这里将它设置为空,数据是None这是销毁信号
            self._节点数据[节点ID] = []
        else:
            self._节点数据[节点ID].append(数据)
    
    def 取节点数据(self, 节点ID: str)->list:
        """返回该节点缓存的数据列表"""
        return self._节点数据.get(节点ID)
    
    # 节点对象管理（新增）
    def 注册节点(self, 节点ID: str, 节点对象):
        self._节点对象[节点ID] = 节点对象
    
    def 取节点对象(self, 节点ID: str):
        return self._节点对象.get(节点ID)
    
    def 所有节点(self) -> dict:
        return self._节点对象.copy()
    
    # 连线管理
    def 添加连线(self, 连线ID: str, 起点节点: str, 起点端口: str, 终点节点: str, 终点端口: str):
        self._连线[连线ID] = {
            "起点节点": 起点节点, "起点端口": 起点端口,
            "终点节点": 终点节点, "终点端口": 终点端口
        }
    
    def 删除连线(self, 连线ID: str):
        self._连线.pop(连线ID, None)
    
    def 取连线信息(self, 连线ID: str):
        return self._连线.get(连线ID)
    
    def 所有连线(self) -> dict:
        return self._连线.copy()

    def 取下游节点(self, 节点ID: str) -> list:
        """返回 [(节点ID, 端口名), ...] 包含端口信息"""
        结果 = []
        for c in self._连线.values():
            if c["起点节点"] == 节点ID:
                结果.append((c["终点节点"], c["终点端口"]))
        return 结果
    
    def 取上游节点(self, 节点ID: str) -> list:
        """返回 [(节点ID, 端口名), ...] 包含端口信息"""
        结果 = []
        for c in self._连线.values():
            if c["终点节点"] == 节点ID:
                结果.append((c["起点节点"], c["起点端口"]))
        return 结果
    
    def 取开始节点列表(self) -> list:
        """返回所有开始节点ID"""
        return [nid for nid, node in self._节点对象.items() 
                if getattr(node, '类型', None) == '开始']

# 建议放在 核心_基础.py 末尾
"""2026/4/7/10:47"""
class 协议包装器:
    """将各种数据包装为标准通信协议格式"""
    @staticmethod
    def 构建协议包( # 20260416
        插件名称: str = "",
        呼叫关键词: str = "",
        运行标识: str = None,
        消息类型: str = "数据",  # 数据|控制|事件|日志|历史|心跳|配置
        传输方式: str = "私密",  # 广播|私密
        源节点: str = None,
        源端口: str = None,
        初始节点: str = None,
        目标节点: str = None,
        目标端口: str = None,
        会话标识: str = None,
        数据内容=None,  # 任意Python对象
        原始类型: str = "str",
        编码方式: str = "utf-8",
        控制指令: str = "",  # 启动|停止|暂停|恢复|重置|状态查询
        历史数据: list = None,
        节点状态: dict = None,
        全局变量: dict = None,
        优先级: int = 0,
        是否需要回复: bool = False
    ) -> dict:
        """构建完整的协议包字典"""
        # 生成时间戳（ISO 8601格式，带时区）
        时间戳 = datetime.now(timezone.utc).astimezone().isoformat()
        
        # 构建数据容器（8个标准字段，全部存在，空值保留）
        数据容器 = {
            "str": "",
            "int": None,
            "float": None,
            "bool": None,
            "list": [],
            "dict": {},
            "bytes": "",
            "none": None
        }
        
        # 根据原始类型填充对应字段
        if 数据内容 is not None:
            if isinstance(数据内容, str):
                数据容器["str"] = 数据内容
            elif isinstance(数据内容, int):
                数据容器["int"] = 数据内容
            elif isinstance(数据内容, float):
                数据容器["float"] = 数据内容
            elif isinstance(数据内容, bool):
                数据容器["bool"] = 数据内容
            elif isinstance(数据内容, list):
                数据容器["list"] = 数据内容
            elif isinstance(数据内容, dict):
                数据容器["dict"] = 数据内容
            elif isinstance(数据内容, bytes):
                数据容器["bytes"] = base64.b64encode(数据内容).decode('ascii')
            elif 原始类型 == "none" or 数据内容 is None:
                数据容器["none"] = None
            else:
                # 类型不匹配，强制转字符串
                数据容器["str"] = str(数据内容)
                原始类型 = "str"
        
        # 计算数据大小
        数据大小 = len(json.dumps(数据容器, ensure_ascii=False).encode('utf-8'))
        
        return {
            "协议头": {
                "版本": "2.0.0",
                "消息标识": str(uuid.uuid4())[:16],
                "时间戳": 时间戳,
                "插件信息": {
                    "插件名称": 插件名称,
                    "呼叫关键词": 呼叫关键词,
                    "运行标识": 运行标识,
                    "插件版本": None,
                    "插件作者": None
                },
                "路由信息": {
                    "源节点": 源节点,
                    "源端口": 源端口,
                    "目标节点": 目标节点,
                    "目标端口": 目标端口,
                    "会话标识": None, # 会话标识, # 20260417 # 这个由消息树那边去管理负责
                    "初始节点": 初始节点, # 20260417
                    "目标节点类型":None # 默认没有目标节点类型
                },
                "传输方式": 传输方式,
                "消息类型": 消息类型,
                "控制指令": 控制指令,
                "优先级": 优先级,
                "扩展头": {
                    "消息树信息":{
                        "合并标识":False
                        }
                }
            },
            "协议体": {
                "数据容器": 数据容器,
                "数据元信息": {
                    "原始类型": 原始类型,
                    "编码方式": 编码方式,
                    "数据大小": 数据大小,
                    "是否需要回复": 是否需要回复
                },
                "上下文数据": {
                    "历史数据": 历史数据 if 历史数据 is not None else [],
                    "节点状态": 节点状态 if 节点状态 is not None else {},
                    "全局变量": 全局变量 if 全局变量 is not None else {},
                    "缓存数据": None
                },
                "扩展体": {}
            },
            "协议尾": {
                "扩展尾": {}
            }
        }
    
    @staticmethod
    def 打包为JSON(目标协议包: dict) -> str:
        """将协议包转为JSON字符串"""
        return json.dumps(目标协议包, ensure_ascii=False, separators=(',', ':'))
    
    @staticmethod
    def 解析数据容器(协议体: dict):
        """
        从协议体中解析出第一个非空的数据
        返回: (类型名, 值) 或 (None, None)
        """
        容器 = 协议体.get("数据容器", {})
        # 按优先级遍历
        优先级 = ["bytes", "str", "list", "dict", "int", "float", "bool", "none"]
        
        for 类型名 in 优先级:
            值 = 容器.get(类型名)
            # 检查是否非空
            if 值 is not None and 值 != "" and 值 != [] and 值 != {}:
                # bytes需要解码
                if 类型名 == "bytes" and isinstance(值, str):
                    import base64
                    return 类型名, base64.b64decode(值)
                return 类型名, 值
        
        return None, None
    
    @staticmethod
    def 提取纯数据(目标协议包: dict):
        """快捷方法：直接从完整协议包中提取纯数据"""
        协议体 = 目标协议包.get("协议体", {})
        return 协议包装器.解析数据容器(协议体)

状态 = 状态管理器()