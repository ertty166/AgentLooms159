import base64
import json
import sys
import uuid
import copy
import queue
from datetime import datetime, timezone
import threading


class 插件公用:
    def __init__(self, 插件名称: str, 独立运行调试: bool, 
                 呼叫关键词: str = "", 插件版本: str = "1.0.0", 
                 插件作者: str = "", 分片策略类型="否"):
        self.插件名 = 插件名称
        self.独立 = 独立运行调试
        self.呼叫关键词 = 呼叫关键词
        self.插件版本 = 插件版本
        self.插件作者 = 插件作者
        self.运行标识 = f"运行_{uuid.uuid4().hex[:12]}"
        # ==== 协议包信息临时存储 ====
        self._当前会话标识 = "" # 用于存储当前会话标识
        self._当前消息标识 = "" # 用于存储当前正处理的消息标识
        self.下游插件信息典 = None
        self.接收缓存队列 = queue.Queue(128)
        self.能否开工 = False
        self.分片策略类型 = 分片策略类型
        self.发送锁 = threading.Lock() # 注意不能用可再入锁,因为底层发送方法是同一个
        # ========== 全局字段类型配置 ==========
        self._状态处理中判断典 = {
            True: ["运行中"],
            False: ["就绪", "空闲", "错误", "禁用"]
        }
        self.字段类型配置 = {
            # 协议头层级
            "协议头.版本": "str",
            "协议头.消息标识": "str",
            "协议头.时间戳": "str",
            "协议头.插件信息.插件名称": "str",
            "协议头.插件信息.呼叫关键词": "str",
            "协议头.插件信息.运行标识": "str",
            "协议头.插件信息.插件版本": "str",
            "协议头.插件信息.插件作者": "str",
            "协议头.路由信息.源节点": "str",
            "协议头.路由信息.源端口": "str",
            "协议头.路由信息.目标节点": "str",
            "协议头.路由信息.目标端口": "str",
            "协议头.路由信息.会话标识": "str",
            "协议头.路由信息.初始节点": "str",
            "协议头.传输方式": "str",
            "协议头.消息类型": "str",
            "协议头.控制指令": "str",
            "协议头.优先级": "int",
            "协议头.扩展头.消息树信息.合并标识": "bool",
            "协议头.扩展头.消息树信息.深度": "int",
            "协议头.扩展头.消息树信息.分支序号": "int",
            "协议头.扩展头.消息树信息.序列索引": "int",
            "协议头.扩展头.消息树信息.完成标识": "bool",
            
            # 协议体层级
            "协议体.数据容器.str": "str",
            "协议体.数据容器.int": "int",
            "协议体.数据容器.float": "float",
            "协议体.数据容器.bool": "bool",
            "协议体.数据容器.list": "list",
            "协议体.数据容器.dict": "dict",
            "协议体.数据容器.bytes": "bytes",
            "协议体.数据容器.none": "none",
            "协议体.数据元信息.原始类型": "str",
            "协议体.数据元信息.编码方式": "str",
            "协议体.数据元信息.数据大小": "int",
            "协议体.数据元信息.是否需要回复": "bool",
            "协议体.上下文数据.历史数据": "list",
            "协议体.上下文数据.节点状态": "dict",
            "协议体.上下文数据.全局变量": "dict",
            "协议体.上下文数据.缓存数据": "any",
            "协议体.扩展体": "dict",
            
            # 协议尾层级
            "协议尾.消息分片.当前": "int",
            "协议尾.消息分片.总共": "int",
            "协议尾.扩展尾": "dict"
        }

        # ========== 字段处理策略配置 ==========
        self.字段策略 = {
            # 路由信息 - 优先透传（会话连续性关键）
            "协议头.路由信息.目标节点": "优先透传",
            "协议头.路由信息.目标端口": "优先透传",
            "协议头.路由信息.会话标识": "优先透传",
            "协议头.路由信息.初始节点": "优先透传",
            "协议头.路由信息.源节点": "优先透传",
            "协议头.路由信息.源端口": "优先透传",
            
            # 插件信息 - 优先修改（当前插件身份）
            "协议头.插件信息.插件名称": "优先修改",
            "协议头.插件信息.呼叫关键词": "优先修改",
            "协议头.插件信息.运行标识": "优先修改",
            "协议头.插件信息.插件版本": "优先修改",
            "协议头.插件信息.插件作者": "优先修改",
            
            # 消息元信息 - 优先修改
            "协议头.消息类型": "优先修改",
            "协议头.消息标识": "优先透传",
            "协议头.传输方式": "优先修改",
            "协议头.控制指令": "优先修改",
            "协议头.时间戳": "优先修改",
            "协议头.版本": "优先修改",
            "协议头.优先级": "优先修改",
            
            # 数据容器 - 强制修改
            "协议体.数据容器": "强制修改",
            "协议体.数据元信息.原始类型": "优先修改",
            "协议体.数据元信息.编码方式": "优先修改",
            "协议体.数据元信息.数据大小": "优先修改",
            "协议尾.消息分片": "优先透传",
            "协议头.扩展头.消息树信息.合并标识": "优先透传",
        }

    # ========== 会话标识管理 ==========
    
    def 取当前会话标识(self) -> str:
        """获取当前会话标识"""
        return self._当前会话标识

    def 设置当前会话标识(self, 会话标识: str):
        """设置当前会话标识（从输入协议包提取后调用）"""
        self._当前会话标识 = 会话标识

    def 清空当前会话标识(self):
        """清空当前会话标识（会话结束时调用）"""
        self._当前会话标识 = ""
    
    def 取当前消息标识(self) -> str:
        """获取当前会话标识"""
        return self._当前消息标识

    def 设置当前消息标识(self, 消息标识: str):
        """设置当前会话标识（从输入协议包提取后调用）"""
        self._当前消息标识 = 消息标识

    def 清空当前消息标识(self):
        """清空当前会话标识（会话结束时调用）"""
        self._当前消息标识 = ""

    def 提取会话标识(self, 协议包: dict) -> str:
        """从任意协议包中提取会话标识（静态工具方法）"""
        return 协议包.get("协议头", {}).get("路由信息", {}).get("会话标识", "")

    # ========== 字段路径操作核心方法 ==========

    def 获取字段值(self, 协议包: dict, 字段路径: str) -> any:
        """
        根据点分隔路径获取字段值
        路径不存在返回 None
        """
        if not 协议包 or not isinstance(协议包, dict):
            return None
        
        路径列表 = 字段路径.split(".")
        当前层级 = 协议包
        
        for 层级名 in 路径列表:
            if not isinstance(当前层级, dict):
                return None
            当前层级 = 当前层级.get(层级名)
            if 当前层级 is None:
                return None
        
        return 当前层级

    def 设置字段值(self, 协议包: dict, 字段路径: str, 新值: any, 自动创建: bool = True) -> bool:
        """
        根据点分隔路径设置字段值
        自动创建缺失的中间层级
        成功返回 True，失败返回 False
        """
        if not 协议包 or not isinstance(协议包, dict):
            return False
        
        路径列表 = 字段路径.split(".")
        当前层级 = 协议包
        
        # 遍历到倒数第二层
        for 层级名 in 路径列表[:-1]:
            if 层级名 not in 当前层级:
                if not 自动创建:
                    return False
                当前层级[层级名] = {}
            elif not isinstance(当前层级[层级名], dict):
                # 中间层级不是字典，无法继续
                if not 自动创建:
                    return False
                # 强制替换为字典（破坏性操作，但符合"自动创建"语义）
                当前层级[层级名] = {}
            当前层级 = 当前层级[层级名]
        
        # 设置最终值
        最终层级名 = 路径列表[-1]
        当前层级[最终层级名] = 新值
        return True

    def 删除字段值(self, 协议包: dict, 字段路径: str) -> bool:
        """
        根据点分隔路径删除字段值
        成功返回 True，不存在也返回 True（幂等）
        """
        if not 协议包 or not isinstance(协议包, dict):
            return False
        
        路径列表 = 字段路径.split(".")
        当前层级 = 协议包
        
        # 遍历到倒数第二层
        for 层级名 in 路径列表[:-1]:
            if not isinstance(当前层级, dict) or 层级名 not in 当前层级:
                return True  # 路径不存在，视为已删除
            当前层级 = 当前层级[层级名]
        
        # 删除最终值
        最终层级名 = 路径列表[-1]
        if isinstance(当前层级, dict) and 最终层级名 in 当前层级:
            del 当前层级[最终层级名]
        return True

    def 检查字段类型(self, 值: any, 期望类型: str) -> bool:
        """
        检查值是否符合期望类型
        """
        if 期望类型 == "str":
            return isinstance(值, str)
        elif 期望类型 == "int":
            return isinstance(值, int)
        elif 期望类型 == "float":
            return isinstance(值, (int, float))
        elif 期望类型 == "bool":
            return isinstance(值, bool)
        elif 期望类型 == "list":
            return isinstance(值, list)
        elif 期望类型 == "dict":
            return isinstance(值, dict)
        elif 期望类型 == "bytes":
            return isinstance(值, (bytes, str))  # base64编码后可能是str
        elif 期望类型 == "none":
            return 值 is None
        elif 期望类型 == "any":
            return True
        return False
    # ========== 四层处理核心方法 ==========
    def 处理字段(self, 协议包: dict, 字段路径: str, 新值: any, 
                 类型检查: bool = True, 强制策略: str = None) -> tuple:
        """
        四层处理：优先修改 → 优先透传 → 优先销毁 → 强制修改
        提示:强制策略如果不传入,会调用全局字典拿取那里的策略(四项之一)
        返回: (成功否: bool, 消息: str)
        成功时直接修改传入的协议包（引用修改）
        """
        # 确定策略
        策略 = 强制策略 if 强制策略 else self.字段策略.get(字段路径, "优先修改")
        当前值 = self.获取字段值(协议包, 字段路径)
        期望类型 = self.字段类型配置.get(字段路径, "any")
        
        # 类型检查（如果启用）
        if 类型检查 and 新值 is not None:
            if not self.检查字段类型(新值, 期望类型):
                # 类型不匹配，根据策略处理
                if 策略 == "强制修改":
                    return False, f"强制修改失败: {字段路径} 期望 {期望类型}, 实际 {type(新值)}"
                # 其他策略：进入透传或销毁分支
        
        # ========== 第1层: 优先修改 ==========
        if 策略 == "优先修改":
            # 尝试修改，无论当前值是否存在
            成功 = self.设置字段值(协议包, 字段路径, 新值, 自动创建=True)
            if 成功:
                return True, f"优先修改成功: {字段路径}"
            # 修改失败，进入优先透传
            if 当前值 is not None:
                return True, f"优先修改失败，透传原值: {字段路径}"
            # 透传也没值，进入优先销毁
        
        # ========== 第2层: 优先透传 ==========
        elif 策略 == "优先透传":
            if 当前值 is not None:
                # 有值就透传，不修改
                return True, f"优先透传成功: {字段路径}"
            # 没值，尝试用新值修改
            成功 = self.设置字段值(协议包, 字段路径, 新值, 自动创建=True)
            if 成功:
                return True, f"优先透传(原值空，已修改): {字段路径}"
            # 修改也失败，进入优先销毁
        
        # ========== 第3层: 优先销毁 ==========
        elif 策略 == "优先销毁":
            self.删除字段值(协议包, 字段路径)
            # 或者设为 None
            self.设置字段值(协议包, 字段路径, None, 自动创建=True)
            return True, f"优先销毁成功: {字段路径}"
        
        # ========== 第4层: 强制修改 ==========
        elif 策略 == "强制修改":
            成功 = self.设置字段值(协议包, 字段路径, 新值, 自动创建=True)
            if 成功:
                return True, f"强制修改成功: {字段路径}"
            return False, f"强制修改失败: {字段路径}"
        
        else:
            return False, f"未知策略: {策略}"
        
        # 兜底：如果前面没返回，尝试销毁
        self.删除字段值(协议包, 字段路径)
        self.设置字段值(协议包, 字段路径, None, 自动创建=True)
        return True, f"兜底销毁: {字段路径}"

    def 批量处理字段(self, 协议包: dict, 字段列表: list) -> tuple:
        """
        批量处理多个字段
        字段列表: [(字段路径, 新值, 强制策略), ...]
        返回: (全部成功否: bool, 详细结果: list)
        """
        详细结果 = []
        全部成功 = True
        
        for 字段项 in 字段列表:
            if len(字段项) == 2:
                字段路径, 新值 = 字段项
                强制策略 = None
            else:
                字段路径, 新值, 强制策略 = 字段项
            
            成功, 消息 = self.处理字段(协议包, 字段路径, 新值, 强制策略=强制策略)
            详细结果.append((字段路径, 成功, 消息))
            if not 成功:
                全部成功 = False
        
        return 全部成功, 详细结果
    # ========== 协议包构建 ==========
    def _构建协议包(self, 消息类型: str, 数据内容=None, 
                   原始类型: str = "str", 控制指令: str = "",
                   目标节点: str = "", 传输方式: str = "私密", 
                   消息标识=None, 消息分片=None) -> dict:
        """内部方法：构建标准协议包,自动处理当前会话标识"""
        时间戳 = datetime.now(timezone.utc).astimezone().isoformat()
        
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
        
        if 数据内容 is not None:
            if 原始类型 == "str" and isinstance(数据内容, str):
                数据容器["str"] = 数据内容
            elif 原始类型 == "int" and isinstance(数据内容, int):
                数据容器["int"] = 数据内容
            elif 原始类型 == "float" and isinstance(数据内容, float):
                数据容器["float"] = 数据内容
            elif 原始类型 == "bool" and isinstance(数据内容, bool):
                数据容器["bool"] = 数据内容
            elif 原始类型 == "list" and isinstance(数据内容, list):
                数据容器["list"] = 数据内容
            elif 原始类型 == "dict" and isinstance(数据内容, dict):
                数据容器["dict"] = 数据内容
            elif 原始类型 == "bytes" and isinstance(数据内容, bytes):
                数据容器["bytes"] = base64.b64encode(数据内容).decode('ascii')
            else:
                return "错误,某个插件原始类型不支持或者数据类型不支持"
        
        数据大小 = len(json.dumps(数据容器, ensure_ascii=False).encode('utf-8'))
        
        return {
            "协议头": {
                "版本": "2.0.0",
                "消息标识": 消息标识 if 消息标识 else str(uuid.uuid4())[:16], # self._当前消息标识
                "时间戳": 时间戳,
                "插件信息": {
                    "插件名称": self.插件名,
                    "呼叫关键词": self.呼叫关键词,
                    "运行标识": self.运行标识,
                    "插件版本": self.插件版本,
                    "插件作者": self.插件作者
                },
                "路由信息": {
                    "源节点": self.运行标识,
                    "源端口": "输出",
                    "目标节点": 目标节点,
                    "目标端口": "输入",
                    "会话标识": self._当前会话标识,
                    "目标节点类型":None
                },
                "传输方式": 传输方式,
                "消息类型": 消息类型,
                "控制指令": 控制指令,
                "优先级": 0,
                "扩展头": {
                    "消息树信息": {
                        "合并标识": False
                    }
                }
            },
            "协议体": {
                "数据容器": 数据容器,
                "数据元信息": {
                    "原始类型": 原始类型,
                    "编码方式": "utf-8",
                    "数据大小": 数据大小,
                    "是否需要回复": False
                },
                "上下文数据": {
                    "历史数据": [],
                    "节点状态": {},
                    "全局变量": {},
                    "缓存数据": None
                },
                "扩展体": {}
            },
            "协议尾": {
                "扩展尾": {},
                "消息分片": 消息分片
            }
        }

    def _实际发送协议包(self, 发送协议包: dict):
        """实际执行发送的底层方法"""
        json字符串 = json.dumps(发送协议包, ensure_ascii=False)
        with self.发送锁:
            if self.独立:
                print(json字符串)
            else:
                print(self.base64编码(json字符串))
            sys.stdout.flush()
    # ========== 分片发送专用方法 ==========
    def 分片判断发送(self, 协议包: dict, 块标记: str = "```") -> bool:
        """
        判断是否需要分片发送
        需要分片则执行分片发送，返回 True
        不需要分片则返回 False（调用方应直接发送）
        """
        # 提取数据内容
        _, 纯数据 = self.解析数据容器(协议包.get("协议体", {}))
        
        if not isinstance(纯数据, str):
            # 不是字符串，无法分片
            return False
        
        # 提取反引号块
        反引号块列表 = self.提取标记内内容(纯数据, 块标记)
        
        if not 反引号块列表:
            # 没有反引号块，不需要分片
            return False
        
        # 检查是否已有分片信息（避免重复分片）
        现有分片 = self.提取消息分片(协议包.get("协议尾", {}))
        if 现有分片 and isinstance(现有分片, dict):
            # 已有分片信息，可能是透传的分片，直接发送
            return False
        
        # 需要分片，执行分片发送
        self._执行分片发送(协议包, 反引号块列表, 纯数据, 块标记)
        return True

    def _执行分片发送(self, 基础协议包: dict, 反引号块列表: list, 
                      原始数据: str, 块标记: str) -> None:
        """
        执行实际的分片发送
        基于传入的协议包，修改数据内容和分片信息后发送
        """
        共用消息标识 = 基础协议包.get("协议头", {}).get("消息标识", str(uuid.uuid4())[:16])
        总索引 = len(反引号块列表) - 1
        
        for 当前索引, 块内容 in enumerate(反引号块列表):
            # 深拷贝基础协议包（每个分片独立）
            分片协议包 = copy.deepcopy(基础协议包)
            
            # 构建分片数据（带插件前缀）
            分片数据 = f"``{self.插件名}``:\n{块内容}"
            
            # 处理分片协议包的字段
            字段列表 = [
                # 数据内容
                ("协议体.数据容器.str", 分片数据, "优先修改"),
                # 消息标识（同一批分片共享）
                ("协议头.消息标识", 共用消息标识, "优先修改"),
                # 分片信息
                ("协议尾.消息分片", {"当前": 当前索引, "总共": 总索引}, "优先修改"),
                # 合并标识设为 False（分片需要合并）
                ("协议头.扩展头.消息树信息.合并标识", False, "优先修改"),
            ]
            
            # 批量处理字段
            全部成功, 详细结果 = self.批量处理字段(分片协议包, 字段列表)
            
            if not 全部成功:
                # 记录错误但继续发送（避免阻塞）
                错误消息 = "; ".join([f"{路径}: {消息}" for 路径, 成功, 消息 in 详细结果 if not 成功])
                self.发送日志("警告", f"分片 {当前索引}/{总索引} 字段处理部分失败: {错误消息}")
            
            # 发送分片
            self._实际发送协议包(分片协议包)

    # ========== 对外接口：发送输出（统一入口） ==========

    def 发送输出(self, 结果, 呼叫关键词: str = None, 
                 原始类型: str = "str", 传输方式: str = "私密",
                 消息标识: str = None, 消息分片: dict = None,
                 透传协议包: dict = None,
                 启用分片: bool = True,
                 块标记: str = "```",
                 调试: bool = False):
        """
        发送输出到主进程（统一入口）
        
        处理流程:
            1. 准备基础协议包（透传或新建）
            2. 批量处理字段（按策略配置）
            3. 判断是否需要分片
            4. 发送（分片或单条）
        """
        if not 呼叫关键词 or not isinstance(呼叫关键词, str):
            呼叫关键词 = "" # 这是该数据来源插件的呼叫关键词
        if isinstance(结果,str):
            结果 = self.过滤输出数据(结果)
        if self.独立: # 独立运行调试
            带前缀结果 = f"``{self.插件名}``:\n{呼叫关键词}{结果}" if isinstance(结果, str) else 结果
            print(f"输出:\n{结果}")
        
        else:
            # ========== 步骤1: 准备基础协议包 ==========
            if isinstance(透传协议包, dict):
                # 透传模式：深拷贝基础包
                基础包 = copy.deepcopy(透传协议包)
            else:
                # 无透传包，报错（20260418: 必须有透传协议包）
                self.发送日志("错误", "发送输出: 必须有透传协议包")
                return
            
            # ========== 步骤2: 准备字段列表 ==========
            字段列表 = []
            
            # 数据内容字段（优先修改）
            if 结果 is not None:
                带前缀结果 = f"``{self.插件名}``:\n{呼叫关键词}{结果}" if isinstance(结果, str) else 结果
                # self.发送日志("调试",f"带前缀结果:{带前缀结果}",) # 20260501
                if 原始类型 == "str" and isinstance(结果, str):
                    字段列表.append(("协议体.数据容器.str", 带前缀结果, "优先修改"))
                elif 原始类型 == "int" and isinstance(结果, int):
                    字段列表.append(("协议体.数据容器.int", 结果, "优先修改"))
                elif 原始类型 == "float" and isinstance(结果, float):
                    字段列表.append(("协议体.数据容器.float", 结果, "优先修改"))
                elif 原始类型 == "bool" and isinstance(结果, bool):
                    字段列表.append(("协议体.数据容器.bool", 结果, "优先修改"))
                elif 原始类型 == "list" and isinstance(结果, list):
                    字段列表.append(("协议体.数据容器.list", 结果, "优先修改"))
                elif 原始类型 == "dict" and isinstance(结果, dict):
                    字段列表.append(("协议体.数据容器.dict", 结果, "优先修改"))
                elif 原始类型 == "bytes" and isinstance(结果, bytes):
                    字段列表.append(("协议体.数据容器.bytes", base64.b64encode(结果).decode('ascii'), "优先修改"))
            
            # 消息类型（优先修改）
            字段列表.append(("协议头.消息类型", "输出"))
            
            # 传输方式（优先修改，如果指定了）
            if 传输方式: # and not(结果.strip() == "/help"): # 20260423
                字段列表.append(("协议头.传输方式", 传输方式, "优先修改"))
            #elif 结果.strip() == "/help" and not 消息分片: # 20260423
                #字段列表.append(("协议头.传输方式", "广播", "优先修改"))
            # 消息标识（优先修改，如果指定了）
            if 消息标识:
                字段列表.append(("协议头.消息标识", 消息标识, "优先透传"))
            
            # 插件信息（优先修改）
            字段列表.extend([
                ("协议头.插件信息.插件名称", self.插件名, "优先修改"),
                ("协议头.插件信息.运行标识", self.运行标识,"优先修改"),
                ("协议头.插件信息.插件版本", self.插件版本,"优先修改"),
                ("协议头.插件信息.插件作者", self.插件作者,"优先修改"),
                ("协议头.插件信息.呼叫关键词", self.呼叫关键词,"优先修改"),
                ("协议头.时间戳", datetime.now(timezone.utc).astimezone().isoformat(), "优先修改"),
                ("协议尾.消息分片", 消息分片, "优先透传") # 消息分片(透传)
            ])
            # 合并标识（强制修改）
            字段列表.append(("协议头.扩展头.消息树信息.合并标识", False, "强制修改"))
            
            # ========== 步骤3: 批量处理字段 ==========
            全部成功, 详细结果 = self.批量处理字段(基础包, 字段列表)
            
            if 调试:
                for 路径, 成功, 消息 in 详细结果:
                    self.发送日志("调试", f"字段处理: {路径} - {消息}")
            
            if not 全部成功:
                错误消息 = "; ".join([f"{路径}: {消息}" for 路径, 成功, 消息 in 详细结果 if not 成功])
                self.发送日志("错误", f"发送输出字段处理失败: {错误消息}")
                return
            
            # ========== 步骤4: 判断分片并发送 ==========
            if 启用分片 and self.分片策略类型=="是" and False: # 20260429关闭插件断分片
                已分片 = self.分片判断发送(基础包, 块标记)
                if 已分片:
                    return  # 分片发送已完成
            # 单条发送
            self._实际发送协议包(基础包)
    # ========== 其他发送方法 ==========
    def 发送日志(self, 级别: str, 消息: str, 透传协议包: dict = None):
        """发送日志到主进程"""
        带前缀消息 = f"``{self.插件名}``:{消息}"
        if self.独立:
            print(f"日志:\n级别:{级别},\n内容:{带前缀消息}")
        else:
            if 透传协议包:
                基础包 = copy.deepcopy(透传协议包)
                字段列表 = [
                    ("协议头.消息类型", "日志", "强制修改"),
                    ("协议体.数据容器.str", 带前缀消息, "强制修改"),
                    ("协议体.扩展体.日志级别", 级别, "强制修改"),
                ]
                self.批量处理字段(基础包, 字段列表)
                self._实际发送协议包(基础包)
            else:
                发送协议包 = self._构建协议包(
                    消息类型="日志",
                    数据内容=带前缀消息,
                    原始类型="str"
                )
                发送协议包["协议体"]["扩展体"]["日志级别"] = 级别
                self._实际发送协议包(发送协议包)

    def _状态_判断并更新临时信息(self,状态值:str):
        """如果状态值是表示这个消息结束的列表中值,那么清空临时消息标识和会话标识"""
        if 状态值 in self._状态处理中判断典[False]: # 判断当前插件是否处理完了某消息
            self.清空当前会话标识()
            self.清空当前消息标识()
            return True
        else:
            return False

    def 发送状态(self, 状态值: str, 透传协议包: dict = None):
        """发送状态到主进程"""
        if self.独立:
            print(f"状态:\n内容:{状态值}")
        else:
            if 透传协议包:
                发送协议包 = copy.deepcopy(透传协议包)
            else:
                发送协议包 = self._构建协议包(
                    消息类型="状态",
                    数据内容=状态值,
                    原始类型="str",
                    消息标识=self._当前消息标识,
                )
            字段列表 = [
                    ("协议头.消息类型", "状态", "优先修改"),
                    ("协议体.数据容器.str", 状态值, "优先修改"),
                    ("协议头.消息标识", self._当前消息标识, "优先修改")
                ]
            self.批量处理字段(发送协议包, 字段列表)
            self._实际发送协议包(发送协议包)
        # 如果状态值是某些表示当前插件完成了任务(不管是报错还是正常),那么回收这一轮的会话标识和消息标识
        清除了吗 = self._状态_判断并更新临时信息(状态值)

    def 发送事件(self, 事件名: str, 数据=None, 透传协议包: dict = None):
        """发送自定义事件到主进程"""
        if self.独立:
            print(f"事件:\n{数据}")
        else:
            if 透传协议包:
                基础包 = copy.deepcopy(透传协议包)
                字段列表 = [
                    ("协议头.消息类型", "事件"),
                    ("协议体.数据容器.str", str(数据) if 数据 else ""),
                    ("协议体.扩展体.事件名", 事件名),
                ]
                self.批量处理字段(基础包, 字段列表)
                self._实际发送协议包(基础包)
            else:
                数据类型 = "str" if 数据 is None else type(数据).__name__
                发送协议包 = self._构建协议包(
                    消息类型="事件",
                    数据内容=数据,
                    原始类型=数据类型,
                    消息标识 = self._当前消息标识
                )
                发送协议包["协议体"]["扩展体"]["事件名"] = 事件名
                self._实际发送协议包(发送协议包)

    def 更新下游信息(self, 协议包:dict=None): # 20260424
        """主程序启动时向下游发送的本插件的上下游信息,在这里被结构化存储"""
        if not 协议包:
            return None
        下游插件信息典 = self.获取字段值(协议包, "协议体.数据容器.dict")
        self.下游插件信息典 = copy.deepcopy(下游插件信息典)
        self.发送日志("调试",f"下游信息字典已更新为:{json.dumps(self.下游插件信息典, indent=2, ensure_ascii=False)}")
    
    def 过滤输出数据(self,数据:str):
        """去掉重复前缀"""
        if not 数据:
            return 数据
        else:
            前缀 = f"``{self.插件名}``:\n"
            while True:
                原数据 = 数据
                数据 = 数据.removeprefix(前缀)
                if 数据 == 原数据:
                    break
            return 数据

    def 获取下游信息(self)->dict|None:
        """返还下游信息字典,{id[str]:插件信息典[dict]}
            或者 None"""
        if self.下游插件信息典 and isinstance(self.下游插件信息典, dict):
            return self.下游插件信息典
        else:
            return None

    def AI_获取下游信息(self)->str:
        """这个方法对接AI使用它会整理这些字典并拼接成一个字符串
        哪怕没有字典也会通过其他方式返还字符串,
        放心大胆的用:将它的传输结果交给AI让AI去知道下游有什么"""
        总文本串 = "这是你下游的插件信息:\n"
        if isinstance(self.下游插件信息典, dict) and self.下游插件信息典:
            序号 = 0
            for 节点ID, 节点信息 in self.下游插件信息典.items():
                插件简介 = 节点信息.get("简介", None)
                if 插件简介 and isinstance(插件简介, str):
                    插件信息 = f"第{序号}个插件:{插件简介}\n"
                    总文本串+=插件信息
                    序号 += 1
            if 序号 > 0:
                return 总文本串
            else:
                return "你现在不能调用任何工具,因为你的下游现在没有插件"
        else:
            return "你现在不能调用任何工具,因为目前你的下游没有插件"
        
    def 获取下游工具介绍列表(self)->list: # 20260507
        """传回ollama标准tools参数格式的全部下游工具调用介绍列表"""
        总工具介绍列表 = []
        if isinstance(self.下游插件信息典, dict) and self.下游插件信息典:
            for 节点ID, 节点信息 in self.下游插件信息典.items():
                工具介绍 = 节点信息.get("工具介绍", None)
                if 工具介绍 and isinstance(工具介绍, list):
                    总工具介绍列表.extend(工具介绍)
        self.发送日志("调试",f"插件获取下游工具介绍列表:{self.下游插件信息典}")
        return 总工具介绍列表

    def 解析输入协议包(self, 输入行: str) -> dict|None:
        """
        解析主进程发来的输入（新协议格式）
        自动提取并保存会话标识
        返回解析后的协议包字典
        同时更新下游信息字典
        """
        try:
            try:
                解码后 = self.base64解码(输入行.strip())
            except:
                解码后 = 输入行.strip()
            # 解码成python字典
            输入协议包 = json.loads(解码后)
            if isinstance(输入协议包, dict) and "协议头" in 输入协议包:
                # 关键：提取并保存会话标识
                会话标识 = self.获取字段值(输入协议包, "协议头.路由信息.会话标识")
                消息类型 = self.获取字段值(输入协议包, "协议头.消息类型")
                消息标识 = self.获取字段值(输入协议包, "协议头.消息标识")
                if 会话标识:
                    self.设置当前会话标识(会话标识) # 20260427
                if 消息标识:
                    self.设置当前消息标识(消息标识)
                if 消息类型 == "下游信息":
                    self.更新下游信息(输入协议包)
                return 输入协议包
            return None
        except Exception as e:
            return None

    def 判断是否更新运行状态(self,协议包:dict=None)->tuple[bool,list]:
        """如果需要更新则会返回要添加的的字段策略列表"""
        if not 协议包:
            return False, []
        自己节点ID = self.获取字段值(协议包, "协议头.路由信息.目标节点") # 因为路由信息会在将包发送给这个插件之前更新那里的目标节点为这个节点的ID
        初始节点 = self.获取字段值(协议包, "协议头.路由信息.初始节点")
        消息分片 = self.获取字段值(协议包, "协议尾.消息分片")
        合并标识 = self.获取字段值(协议包, "协议头.扩展头.消息树信息.合并标识")
        if 初始节点 == 自己节点ID and not 消息分片:
            return True, [
                ("协议头.扩展头.消息树信息.完成标识", True, "优先修改")
            ]
        return False, []

    def _兼容旧格式(self, 旧数据: dict) -> dict:
        """将旧格式数据转换为新协议格式"""
        消息类型 = 旧数据.get("类型", "数据")
        数据内容 = 旧数据.get("数据") or 旧数据.get("内容", "")
        
        类型映射 = {
            "输出": "输出",
            "日志": "日志",
            "状态": "状态",
            "错误": "事件",
            "事件": "事件",
            "数据": "数据",
            "历史数据": "历史"
        }
        
        return self._构建协议包(
            消息类型=类型映射.get(消息类型, "数据"),
            数据内容=数据内容,
            原始类型="str"
        )
    
    def 提取输入数据(self, 输入协议包: dict):
        """
        从输入协议包中提取纯数据
        返回: (数据类型, 数据值)
        """
        协议体 = 输入协议包.get("协议体", {})
        容器 = 协议体.get("数据容器", {})
        
        优先级 = ["bytes", "str", "list", "dict", "int", "float", "bool", "none"]
        
        for 类型名 in 优先级:
            值 = 容器.get(类型名)
            if 值 is not None and 值 != "" and 值 != [] and 值 != {}:
                if 类型名 == "bytes" and isinstance(值, str):
                    return 类型名, base64.b64decode(值)
                return 类型名, 值
        
        return "none", None
    
    def 发送控制响应(self, 控制指令: str, 结果: str, 
                     是否成功: bool = True, 透传协议包: dict = None):
        """发送控制指令响应"""
        if self.独立:
            print(结果)
            return
            
        if 透传协议包:
            基础包 = copy.deepcopy(透传协议包)
            字段列表 = [
                ("协议头.消息类型", "控制"),
                ("协议头.控制指令", 控制指令),
                ("协议体.数据容器.str", 结果),
                ("协议体.扩展体.执行结果", "成功" if 是否成功 else "失败"),
            ]
            self.批量处理字段(基础包, 字段列表)
            self._实际发送协议包(基础包)
        else:
            发送协议包 = self._构建协议包(
                消息类型="控制",
                数据内容=结果,
                原始类型="str",
                控制指令=控制指令
            )
            发送协议包["协议体"]["扩展体"]["执行结果"] = "成功" if 是否成功 else "失败"
            self._实际发送协议包(发送协议包)
    # ========== 工具方法 ==========
    def 解析数据容器(self, 协议体: dict):
        """
        从协议体中解析出第一个非空的数据
        返回: (类型名, 值) 或 (None, None)
        """
        容器 = 协议体.get("数据容器", {}) if isinstance(协议体, dict) else {}
        优先级 = ["bytes", "str", "list", "dict", "int", "float", "bool", "none"]
        
        for 类型名 in 优先级:
            值 = 容器.get(类型名)
            if 值 is not None and 值 != "" and 值 != [] and 值 != {}:
                if 类型名 == "bytes" and isinstance(值, str):
                    return 类型名, base64.b64decode(值)
                return 类型名, 值
        
        return None, None

    def 移除标记间内容(self, 开头标记: str, 结尾标记: str, 字符串数据: str) -> str:
        """移除两端包含标记本身在内的标记间内容"""
        while 开头标记 in 字符串数据 and 结尾标记 in 字符串数据:
            头 = 字符串数据.find(开头标记)
            尾 = 字符串数据.find(结尾标记, 头 + len(开头标记))
            if 头 == -1 or 尾 == -1:
                break
            字符串数据 = 字符串数据[:头] + 字符串数据[尾 + len(结尾标记):]
        return 字符串数据
    
    def 处理历史数据(self, 历史数据: list):
        """需要子类重写覆盖"""
        pass
    
    def base64解码(self, base64字符串: str) -> str:
        """将Base64字符串解码为UTF-8文本"""
        try:
            return base64.b64decode(base64字符串.encode('utf-8')).decode('utf-8')
        except Exception:
            return base64字符串
    
    def base64编码(self, 文本字符串: str) -> str:
        """将文本编码为Base64字符串"""
        return base64.b64encode(文本字符串.encode('utf-8')).decode('utf-8')
    
    def 拼接回调关键词(self, 数据: str, 完整协议包: dict = {}, 调试: bool = False) -> str:
        """
        传入完整协议包和你原来的数据字符串，会将呼叫关键词拼在数据首，然后返回
        """
        回调关键词 = 完整协议包.get("协议头", {}).get("插件信息", {}).get("呼叫关键词", None)
        if 调试:
            self.发送日志("调试", f"回调关键词已拼接: {str(回调关键词)}")
        return str(回调关键词 + 数据) if 回调关键词 else 数据

    def 提取回调关键词(self, 协议包: dict = None, 调试: bool = False):
        """提取呼叫关键词"""
        if not 协议包:
            return ""
        协议头 = 协议包.get("协议头", None)
        回调关键词 = 协议头.get("插件信息", {}).get("呼叫关键词", None) if isinstance(协议头, dict) else None
        呼叫关键词 = 回调关键词 if 回调关键词 else ""
        if 调试:
            self.发送日志("调试", f"提取回调关键词: {str(呼叫关键词)}")
        return 呼叫关键词

    def 提取标记内内容(self, 文本: str, 标记: str = "```") -> list:
        """
        提取文本中标记之间的内容
        使用索引遍历方法：第1个和第2个配一对取中间，第3个和第4个配一对取中间
        如果最后剩一个则舍弃
        返回: 按出现顺序排列的块内容列表
        """
        if not isinstance(文本, str):
            return []
            
        标记长度 = len(标记)
        所有索引 = []
        当前位置 = 0
        
        while True:
            找到位置 = 文本.find(标记, 当前位置)
            if 找到位置 == -1:
                break
            所有索引.append(找到位置)
            当前位置 = 找到位置 + 标记长度
        
        内容列表 = []
        索引计数 = len(所有索引)
        
        for 起始指针 in range(0, 索引计数 - 1, 2):
            起始位置 = 所有索引[起始指针]
            结束位置 = 所有索引[起始指针 + 1]
            块起始 = 起始位置 + 标记长度
            块内容 = 文本[块起始:结束位置]
            内容列表.append(块内容.strip())
        
        return 内容列表

    def 提取消息分片(self, 协议尾: dict = {}) -> dict:
        """提取消息分片，如果有，返回消息分片字典"""
        if not isinstance(协议尾, dict):
            return None
        消息分片字典 = 协议尾.get("消息分片")
        if isinstance(消息分片字典, dict):
            return 消息分片字典
        return None
    
    def 提取消息标识(self, 协议头: dict = {}) -> str:
        """提取消息标识"""
        if not isinstance(协议头, dict):
            return None
        消息标识 = 协议头.get("消息标识")
        if isinstance(消息标识, str):
            return 消息标识
        return None
    
    def 提取JSON字典(输入字符串, 提示词1, 提示词2): # 返回 list !!!不是字典
        def _convert_yes_no_to_bool(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    data[key] = _convert_yes_no_to_bool(value)  # 递归遍历字典所有层级
                return data
            elif isinstance(data, list):
                return [_convert_yes_no_to_bool(item) for item in data]  # 递归遍历列表所有层级
            elif isinstance(data, str):
                clean_data = data.strip()
                if clean_data == "是":
                    return True
                elif clean_data == "否":
                    return False
                else:
                    return data
            else:
                return data
        工具调用字典列表 = []
        当前起始位置 = 0
        提示词1长度 = len(提示词1)
        提示词2长度 = len(提示词2)
        输入字符串长度 = len(输入字符串)
        字典序号 = 0
        try:
            while 当前起始位置 < 输入字符串长度:
                提示词1索引 = 输入字符串.find(提示词1, 当前起始位置)
                if 提示词1索引 == -1:
                    break
                JSON起始索引 = 提示词1索引 + 提示词1长度

                提示词2计数 = 0
                目标提示词2索引 = -1
                临时位置 = JSON起始索引
                while True:
                    临时提示词2索引 = 输入字符串.find(提示词2, 临时位置)
                    if 临时提示词2索引 == -1:
                        break
                    下一个提示词1索引 = 输入字符串.find(提示词1, 临时位置, 临时提示词2索引)
                    if 下一个提示词1索引 != -1:
                        提示词2计数 += 1
                        临时位置 = 临时提示词2索引 + 提示词2长度
                    else:
                        if 提示词2计数 == 0:
                            目标提示词2索引 = 临时提示词2索引
                            break
                        else:
                            提示词2计数 -= 1
                            临时位置 = 临时提示词2索引 + 提示词2长度
                if 目标提示词2索引 == -1:
                    当前起始位置 = 提示词1索引 + 提示词1长度
                    continue
                # 3. 提取外层完整JSON并解析（提取字典后再进行布尔值转换）
                JSON字符串 = 输入字符串[JSON起始索引:目标提示词2索引].strip()
                if JSON字符串:
                    工具字典 = json.loads(JSON字符串)  # 先提取（解析）外层字典
                    工具字典 = _convert_yes_no_to_bool(工具字典)  # 后转换布尔值，不限制递归层级
                    工具调用字典列表.append(工具字典)
                # 4. 更新起始位置，处理下一个块
                当前起始位置 = 目标提示词2索引 + 提示词2长度
                字典序号 += 1
            return 工具调用字典列表
        except Exception as e:
            return [f"[#promot]JSON解析异常,解析{字典序号}号索引的工具字典时出现问题(索引从0开始)：{e}[#promot]"]

class 危险指令校验器:
    """危险指令校验器 - 最简实现"""
    # 类级别字典，存储危险指令匹配规则
    危险指令字典 = {
        "rm": True,           # Linux删除
        "del": True,          # Windows删除
        "delete": True,       # 通用删除
        "rmdir": True,        # 删除目录
        "rd": True,           # Windows删除目录
        "remove": True,       # 通用移除
        "format": True,       # 格式化
        "mkfs": True,         # Linux格式化
        #"dd": False,           # 磁盘写入
        ">/dev/null": True,   # 重定向到空
        ":(){:|:&};:": True,  # Fork炸弹
        "chmod": True,        # 修改权限
        "chown": True,        # 修改所有者
        "reg": True,          # Windows注册表
        "regedit": True,      # 注册表编辑
        "nc": True,           # netcat
        "netcat": True,       # netcat全称
        "wget": True,         # 下载工具
        "curl": True,         # 下载工具
    }
    @classmethod # 这个装饰器将方法绑定到类本身,使我不需要实例化就能使用方法
    def 添加危险指令(cls, 指令: str) -> None:
        """添加危险指令"""
        cls.危险指令字典[指令.lower()] = True
    @classmethod
    def 移除危险指令(cls, 指令: str) -> None:
        """移除危险指令"""
        cls.危险指令字典.pop(指令.lower(), None)
    @classmethod
    def 获取所有危险指令(cls) -> list:
        """获取当前所有危险指令（返回副本）"""
        return cls.危险指令字典.copy().keys()
    @classmethod
    def 校验(cls, 指令字符串: str) -> tuple[bool,list]:
        """
        校验字符串是否包含危险指令
        传入: 字符串
        返回: ( bool (True=安全, False=危险) , 犯的忌讳命令 (str) )
        """
        if not 指令字符串 or not isinstance(指令字符串, str):
            return True, []
        小写字符串 = 指令字符串.lower()
        非法命令列表 = []
        for 危险指令 in cls.危险指令字典:
            if 危险指令 in 小写字符串:
                非法命令列表.append(危险指令)
        if 非法命令列表:
            return False, 非法命令列表
        else:
            return True, 非法命令列表

class 上下文管理器():
    """管理上下文长度,总对话轮数,历史嵌套列表,主要方法:覆盖历史()"""
    def __init__(self, 上下文限制=None, 历史=None, 对话轮数:int=0):
        self.上下文限制长度 = 上下文限制 or 65535
        self.上下文 = ""
        self.历史 = 历史 if 历史 else []  # 列表嵌套元组 [(user0, AI0), (user1, AI1)]
        self.初始历史 = 历史 if 历史 else []
        self.对话轮数 = 对话轮数

    def 覆盖历史(self, 新历史完整列表):
        # 找出新增的历史项（从旧历史长度之后的新项）
        旧长度 = len(self.历史)
        新增项列表 = 新历史完整列表[旧长度:]
        # 将新增项添加到历史和全局上下文中
        for 对话元组 in 新增项列表:
            self.对话轮数 += 1
            self.历史.append(对话元组)
            # 将用户和AI的对话内容添加到全局上下文
            用户话, AI话 = 对话元组
            self.上下文 += 用户话 + AI话
        # 检查总长度是否超出限制，超出则循环移除最早的项
        while len(self.上下文) > self.上下文限制长度 and len(self.历史) > 1:
            # 移除最早的历史项（第0项）
            最早项 = self.历史.pop(0)
            用户话, AI话 = 最早项
            # 从全局上下文中删除对应的内容
            要删除的字符串 = 用户话 + AI话
            self.上下文 = self.上下文.replace(要删除的字符串, "", 1)
        return self.历史

    def 获取当前长度(self):
        """获取当前上下文总长度"""
        return len(self.上下文)
    def 获取历史数量(self):
        """获取当前历史保留的对话轮数"""
        return len(self.历史)
    def 获取对话轮数(self):
        """获取全部进行过的对话总轮数,包含已被删除项"""
        return self.对话轮数

插件公用实例 = 插件公用("#NoNe",False,"#NoNe","#NoNe","#NoNe")