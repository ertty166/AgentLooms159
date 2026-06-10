"""
移动端展示节点网络服务
手机端网络服务类 + 加密工具 + 文言映射
"""

import base64
import json
import threading
import urllib.request
import urllib.error
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from PySide6.QtCore import QObject, Signal

# 移动端可能没有核心_日志，使用print兜底
class _日志:
    @staticmethod
    def 调试(msg, *args):
        print(f"[DEBUG] {msg}", *args)
    @staticmethod
    def 信息(msg, *args):
        print(f"[INFO] {msg}", *args)
    @staticmethod
    def 警告(msg, *args):
        print(f"[WARN] {msg}", *args)
    @staticmethod
    def 错误(msg, *args):
        print(f"[ERROR] {msg}", *args)

try:
    from 核心_日志 import 日志
except ImportError:
    日志 = _日志()


# ========== 文言键名映射表 ==========
文言键名映射 = {
    "type": "类",
    "message": "书",
    "template": "模",
    "history": "史",
    "sync": "同",
    "status": "态",
    "content": "文",
    "sender": "寄",
    "receiver": "收",
    "timestamp": "时",
    "node_id": "号",
    "data": "据",
    "send": "发",
    "receive": "受",
    "update": "更",
    "delete": "删",
    "clear": "清",
    "add": "增",
    "service_online": "通",
    "service_offline": "断",
    "heartbeat": "脉",
    "error": "谬",
}

# 反向映射表
文言反向映射 = {v: k for k, v in 文言键名映射.items()}


class 文言映射:
    """键名编码/解码工具类"""

    @staticmethod
    def 编码键名(数据字典: dict) -> dict:
        """将字典中的英文键名替换为文言键名"""
        结果 = {}
        for 键, 值 in 数据字典.items():
            新键 = 文言键名映射.get(键, 键)
            if isinstance(值, dict):
                结果[新键] = 文言映射.编码键名(值)
            elif isinstance(值, list):
                结果[新键] = 文言映射._编码列表(值)
            else:
                结果[新键] = 值
        return 结果

    @staticmethod
    def 解码键名(数据字典: dict) -> dict:
        """将字典中的文言键名还原为英文键名"""
        结果 = {}
        for 键, 值 in 数据字典.items():
            新键 = 文言反向映射.get(键, 键)
            if isinstance(值, dict):
                结果[新键] = 文言映射.解码键名(值)
            elif isinstance(值, list):
                结果[新键] = 文言映射._解码列表(值)
            else:
                结果[新键] = 值
        return 结果

    @staticmethod
    def _编码列表(列表数据: list) -> list:
        结果 = []
        for 项 in 列表数据:
            if isinstance(项, dict):
                结果.append(文言映射.编码键名(项))
            elif isinstance(项, list):
                结果.append(文言映射._编码列表(项))
            else:
                结果.append(项)
        return 结果

    @staticmethod
    def _解码列表(列表数据: list) -> list:
        结果 = []
        for 项 in 列表数据:
            if isinstance(项, dict):
                结果.append(文言映射.解码键名(项))
            elif isinstance(项, list):
                结果.append(文言映射._解码列表(项))
            else:
                结果.append(项)
        return 结果


class 偶奇加密器:
    """偶奇拆分加密/解密工具类"""

    @staticmethod
    def 加密(数据字典: dict) -> list:
        """
        加密流程:
        原始字典 -> json.dumps -> UTF-8字节 -> base64编码 -> Base64字符串S
        -> 偶数索引字符(0,2,4...) -> 字符串A
        -> 奇数索引字符(1,3,5...) -> 字符串B
        返回: [字符串A, 字符串B]
        """
        try:
            json字符串 = json.dumps(数据字典, ensure_ascii=False)
            utf8字节 = json字符串.encode('utf-8')
            base64字符串 = base64.b64encode(utf8字节).decode('utf-8')

            偶数字符 = base64字符串[::2]   # 索引 0, 2, 4...
            奇数字符 = base64字符串[1::2]  # 索引 1, 3, 5...

            return [偶数字符, 奇数字符]
        except Exception as e:
            日志.错误(f"偶奇加密失败: {e}")
            return ["", ""]

    @staticmethod
    def 解密(载荷: list) -> dict:
        """
        解密流程:
        接收载荷: [字符串A, 字符串B]
        -> 交错合并: A[0], B[0], A[1], B[1], A[2], B[2]...
        -> 还原Base64字符串 -> base64解码 -> UTF-8解码 -> json.loads -> 原始字典
        """
        try:
            if not isinstance(载荷, list) or len(载荷) != 2:
                日志.调试(f"解密载荷格式不正确: {载荷}")
                return {}

            字符串A, 字符串B = 载荷[0], 载荷[1]

            # 边界处理：两字符串均为空
            if not 字符串A and not 字符串B:
                return {}

            # 交错合并
            合并字符 = []
            最大长度 = max(len(字符串A), len(字符串B))
            for i in range(最大长度):
                if i < len(字符串A):
                    合并字符.append(字符串A[i])
                if i < len(字符串B):
                    合并字符.append(字符串B[i])

            base64字符串 = ''.join(合并字符)

            if not base64字符串:
                return {}

            utf8字节 = base64.b64decode(base64字符串)
            json字符串 = utf8字节.decode('utf-8')
            数据字典 = json.loads(json字符串)

            return 数据字典

        except Exception as e:
            日志.调试(f"偶奇解密失败: {e}, 载荷: {载荷}")
            return {}


# ========== HTTP请求处理器 ==========
class 移动端请求处理器(BaseHTTPRequestHandler):
    """处理来自主机端的POST请求"""

    数据回调 = None
    服务引用 = None

    def log_message(self, format, *args):
        pass

    def _发送响应(self, 状态码: int = 200, 响应体: bytes = b'{}'):
        self.send_response(状态码)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(响应体)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            内容长度 = int(self.headers.get('Content-Length', 0))
            if 内容长度 == 0:
                self._发送响应(400)
                return

            请求体 = self.rfile.read(内容长度).decode('utf-8')
            请求数据 = json.loads(请求体)

            载荷 = 请求数据.get("payload")
            if not 载荷:
                self._发送响应(400)
                return

            解密字典 = 偶奇加密器.解密(载荷)
            if not 解密字典:
                self._发送响应(400)
                return

            原始字典 = 文言映射.解码键名(解密字典)

            # 检查是否为杀死开关指令
            消息类型 = 原始字典.get("type")
            if 消息类型 == "kill_switch":
                日志.警告("收到杀死开关指令！正在永久禁用网络服务...")
                if 移动端请求处理器.服务引用:
                    移动端请求处理器.服务引用._杀死开关激活 = True
                    移动端请求处理器.服务引用.停止服务()
                if 移动端请求处理器.数据回调:
                    移动端请求处理器.数据回调(原始字典)
                self._发送响应(200, json.dumps({"status": "killed"}).encode())
                return

            if 移动端请求处理器.数据回调:
                移动端请求处理器.数据回调(原始字典)

            self._发送响应(200)

        except Exception as e:
            日志.调试(f"处理POST请求出错: {e}")
            self._发送响应(500)


# ========== 移动端主服务类 ==========
class 移动端展示节点网络服务(QObject):
    """手机终端展示节点网络服务"""

    # 信号定义
    收到数据 = Signal(dict)
    服务状态变更 = Signal(bool)
    发送失败 = Signal(str)
    服务端离线 = Signal()       # 检测到主机端关闭/发送失败

    def __init__(self, 父=None, 目标域名: str = None, 监听端口: int = 8766):
        super().__init__(父)
        self.监听端口 = 监听端口
        self.目标端口 = 8765  # 主机端监听端口
        self.目标域名 = 目标域名 or "https://txaigil_zsjd.cpolar.top"
        self.HTTP服务 = None
        self.服务线程 = None
        self._运行中 = False
        self._杀死开关激活 = False

        # 设置请求处理器的回调
        移动端请求处理器.数据回调 = self._处理收到数据
        移动端请求处理器.服务引用 = self

    def _处理收到数据(self, 数据: dict):
        """内部方法：处理收到的数据，发射信号"""
        self.收到数据.emit(数据)

    def 启动服务(self) -> bool:
        """启动HTTP Server (0.0.0.0:8766)"""
        if self._杀死开关激活:
            日志.错误("启动服务失败：杀死开关已激活，网络服务被永久禁用")
            self.发送失败.emit("网络服务已被永久禁用（杀死开关）")
            return False

        if self._运行中:
            日志.调试("服务已经在运行中")
            return True

        try:
            self.HTTP服务 = HTTPServer(("0.0.0.0", self.监听端口), 移动端请求处理器)
            self.服务线程 = threading.Thread(target=self._运行服务, daemon=True)
            self.服务线程.start()
            self._运行中 = True
            self.服务状态变更.emit(True)
            日志.信息(f"移动端展示节点网络服务已启动: 0.0.0.0:{self.监听端口}")
            return True
        except Exception as e:
            日志.错误(f"启动服务失败: {e}")
            self.发送失败.emit(f"启动服务失败: {e}")
            return False

    def _运行服务(self):
        """在线程中运行HTTP服务"""
        try:
            self.HTTP服务.serve_forever()
        except Exception as e:
            日志.调试(f"服务运行异常: {e}")

    def 停止服务(self):
        """停止HTTP Server"""
        if not self._运行中:
            return

        self._运行中 = False

        if self.HTTP服务:
            try:
                self.HTTP服务.shutdown()
                self.HTTP服务.server_close()
            except Exception as e:
                日志.调试(f"关闭服务出错: {e}")
            self.HTTP服务 = None

        self.服务线程 = None
        self.服务状态变更.emit(False)
        日志.信息("移动端展示节点网络服务已停止")

    def 发送数据(self, 数据字典: dict) -> bool:
        """
        向主机端POST数据（异步，不等待响应）
        Fire-and-Forget模式
        """
        if self._杀死开关激活:
            日志.警告("发送数据失败：杀死开关已激活")
            return False

        if not self._运行中:
            日志.调试("服务未运行，无法发送数据")
            return False

        def _发送任务():
            try:
                # 1. 文言键名编码
                编码字典 = 文言映射.编码键名(数据字典)

                # 2. 偶奇加密
                加密载荷 = 偶奇加密器.加密(编码字典)

                # 3. 构建请求体
                请求体 = {
                    "timestamp": datetime.now().isoformat(),
                    "payload": 加密载荷
                }
                json数据 = json.dumps(请求体, ensure_ascii=False).encode('utf-8')

                # 4. 构建请求
                请求 = urllib.request.Request(
                    f"{self.目标域名}:{self.目标端口}/",
                    data=json数据,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )

                # 5. 发送（Fire-and-Forget）
                urllib.request.urlopen(请求, timeout=5)
                日志.调试(f"数据已发送: {数据字典.get('type', 'unknown')}")

            except urllib.error.URLError as e:
                日志.调试(f"发送数据失败(网络错误): {e}")
                self.发送失败.emit(str(e))
                self.服务端离线.emit()
            except Exception as e:
                日志.调试(f"发送数据失败: {e}")
                self.发送失败.emit(str(e))
                self.服务端离线.emit()

        # 在线程中异步发送
        线程 = threading.Thread(target=_发送任务, daemon=True)
        线程.start()
        return True

    def 发送服务上线通知(self):
        """发送服务上线通知给主机端"""
        self.发送数据({
            "type": "service_online",
            "node_id": "mobile_host",
            "timestamp": datetime.now().isoformat()
        })

    def 发送服务离线通知(self):
        """发送服务离线通知给主机端"""
        self.发送数据({
            "type": "service_offline",
            "node_id": "mobile_host",
            "timestamp": datetime.now().isoformat()
        })

    def 发送消息(self, 内容: str, 节点ID: str = ""):
        """发送消息内容给主机端"""
        return self.发送数据({
            "type": "message",
            "content": 内容,
            "node_id": 节点ID or "展示_mobile",
            "timestamp": datetime.now().isoformat()
        })

    def 是否运行中(self) -> bool:
        """检查服务是否正在运行"""
        return self._运行中


# ========== 便捷函数 ==========
def 构建传输包(数据字典: dict) -> dict:
    """构建完整传输包"""
    编码字典 = 文言映射.编码键名(数据字典)
    加密载荷 = 偶奇加密器.加密(编码字典)
    return {
        "timestamp": datetime.now().isoformat(),
        "payload": 加密载荷
    }


def 解析传输包(传输包: dict) -> dict:
    """解析完整传输包"""
    载荷 = 传输包.get("payload")
    if not 载荷:
        return {}
    解密字典 = 偶奇加密器.解密(载荷)
    return 文言映射.解码键名(解密字典)
