"""
移动端展示节点UI
手机端PySide6 UI程序（独立运行）

布局：竖屏，底部导航栏三Tab
- Tab 1 - 历史页面
- Tab 2 - 对话页面
- Tab 3 - 模板页面
"""

import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QScrollArea, QSplitter, QMessageBox,
    QFrame, QSizePolicy, QDialog, QLineEdit, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QShortcut, QKeySequence

# 导入网络服务
try:
    from 移动端展示节点网络服务 import 移动端展示节点网络服务
except ImportError:
    import os
    # 尝试添加父目录到路径
    当前目录 = os.path.dirname(os.path.abspath(__file__))
    if 当前目录 not in sys.path:
        sys.path.insert(0, 当前目录)
    from 移动端展示节点网络服务 import 移动端展示节点网络服务


class 移动端展示节点UI(QMainWindow):
    """移动端展示节点主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("📡 展示节点 - 移动端")
        self.setMinimumSize(360, 640)
        self.resize(400, 700)

        # 数据存储
        self.历史数据: list = []       # [{"类型": "接收"/"发送", "内容": str, "时间": str}]
        self.模板数据: list = []       # [str, str, ...]
        self.选中模板索引: int = -1
        self._上次选中项 = None

        # 网络服务
        self.网络服务 = None
        self._服务端在线 = False

        self._初始化UI()
        self._初始化网络服务()

    def _初始化UI(self):
        """初始化用户界面"""
        中央部件 = QWidget()
        self.setCentralWidget(中央部件)
        主布局 = QVBoxLayout(中央部件)
        主布局.setContentsMargins(0, 0, 0, 0)
        主布局.setSpacing(0)

        # ========== 顶部状态栏 ==========
        self.状态栏 = QFrame()
        self.状态栏.setFixedHeight(40)
        self.状态栏.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                color: white;
            }
        """)
        状态栏布局 = QHBoxLayout(self.状态栏)
        状态栏布局.setContentsMargins(10, 0, 10, 0)

        self.状态标签 = QLabel("🟡 未连接")
        self.状态标签.setStyleSheet("color: white; font-size: 13px;")
        状态栏布局.addWidget(self.状态标签)
        状态栏布局.addStretch()

        # 网络开关按钮
        self.网络开关按钮 = QPushButton("📡 启动服务")
        self.网络开关按钮.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.网络开关按钮.clicked.connect(self._切换网络服务)
        状态栏布局.addWidget(self.网络开关按钮)

        主布局.addWidget(self.状态栏)

        # ========== 页面内容区域 (QStackedWidget) ==========
        self.页面堆叠 = QStackedWidget()
        self.页面堆叠.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 创建三个页面
        self._创建历史页面()
        self._创建对话页面()
        self._创建模板页面()

        主布局.addWidget(self.页面堆叠)

        # ========== 底部导航栏 ==========
        self.导航栏 = QFrame()
        self.导航栏.setFixedHeight(56)
        self.导航栏.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                border-top: 1px solid #2c3e50;
            }
            QPushButton {
                background-color: transparent;
                color: #bdc3c7;
                border: none;
                font-size: 13px;
                padding: 5px;
            }
            QPushButton:hover { color: #ecf0f1; }
            QPushButton:checked, QPushButton:pressed {
                color: #3498db;
                font-weight: bold;
            }
        """)

        导航布局 = QHBoxLayout(self.导航栏)
        导航布局.setContentsMargins(0, 0, 0, 0)
        导航布局.setSpacing(0)

        self.历史按钮 = QPushButton("📜 历史")
        self.历史按钮.setCheckable(True)
        self.历史按钮.clicked.connect(lambda: self._切换页面(0))

        self.对话按钮 = QPushButton("💬 对话")
        self.对话按钮.setCheckable(True)
        self.对话按钮.clicked.connect(lambda: self._切换页面(1))

        self.模板按钮 = QPushButton("📋 模板")
        self.模板按钮.setCheckable(True)
        self.模板按钮.clicked.connect(lambda: self._切换页面(2))

        for 按钮 in [self.历史按钮, self.对话按钮, self.模板按钮]:
            按钮.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            导航布局.addWidget(按钮)

        主布局.addWidget(self.导航栏)

        # 默认选中对话页面
        self._切换页面(1)

    # ========== 历史页面 ==========
    def _创建历史页面(self):
        页面 = QWidget()
        布局 = QVBoxLayout(页面)
        布局.setContentsMargins(5, 5, 5, 5)
        布局.setSpacing(5)

        # 上部：历史列表
        self.历史列表 = QListWidget()
        self.历史列表.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        self.历史列表.currentItemChanged.connect(self._历史列表选择变更)
        布局.addWidget(self.历史列表)

        # 中部：内容详情（只读）
        self.历史详情框 = QTextEdit()
        self.历史详情框.setReadOnly(True)
        self.历史详情框.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.历史详情框.setPlaceholderText("点击上方列表项查看详情...")
        self.历史详情框.setMaximumHeight(200)
        布局.addWidget(self.历史详情框)

        # 下部：按钮区域
        按钮容器 = QWidget()
        按钮布局 = QHBoxLayout(按钮容器)
        按钮布局.setContentsMargins(0, 0, 0, 0)

        删除选中按钮 = QPushButton("删除选中")
        删除选中按钮.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        删除选中按钮.clicked.connect(self._删除选中历史)

        清空全部按钮 = QPushButton("清空全部")
        清空全部按钮.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
        清空全部按钮.clicked.connect(self._清空全部历史)

        按钮布局.addWidget(删除选中按钮)
        按钮布局.addWidget(清空全部按钮)
        布局.addWidget(按钮容器)

        self.页面堆叠.addWidget(页面)

    # ========== 对话页面 ==========
    def _创建对话页面(self):
        页面 = QWidget()
        布局 = QVBoxLayout(页面)
        布局.setContentsMargins(5, 5, 5, 5)
        布局.setSpacing(5)

        # 上部：滚动消息区域（气泡模式）
        self.消息区域 = QScrollArea()
        self.消息区域.setWidgetResizable(True)
        self.消息区域.setStyleSheet("""
            QScrollArea {
                background-color: #e5e5e5;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        self.消息区域.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.消息容器 = QWidget()
        self.消息布局 = QVBoxLayout(self.消息容器)
        self.消息布局.setAlignment(Qt.AlignTop)
        self.消息布局.setSpacing(8)
        self.消息布局.setContentsMargins(8, 8, 8, 8)
        self.消息区域.setWidget(self.消息容器)

        布局.addWidget(self.消息区域)

        # 中部：多行输入框
        self.消息输入框 = QTextEdit()
        self.消息输入框.setPlaceholderText("输入消息... (Ctrl+Enter发送)")
        self.消息输入框.setMaximumHeight(100)
        self.消息输入框.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
        """)
        布局.addWidget(self.消息输入框)

        # 下部：发送按钮
        发送按钮 = QPushButton("发送 (Ctrl+Enter)")
        发送按钮.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:pressed { background-color: #219a52; }
        """)
        发送按钮.clicked.connect(self._发送消息)
        布局.addWidget(发送按钮)

        # Ctrl+Enter 快捷键
        快捷键 = QShortcut(QKeySequence("Ctrl+Return"), self.消息输入框)
        快捷键.activated.connect(self._发送消息)

        self.页面堆叠.addWidget(页面)

    # ========== 模板页面 ==========
    def _创建模板页面(self):
        页面 = QWidget()
        布局 = QVBoxLayout(页面)
        布局.setContentsMargins(5, 5, 5, 5)
        布局.setSpacing(5)

        # 上部：模板列表
        self.模板列表 = QListWidget()
        self.模板列表.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        self.模板列表.itemClicked.connect(self._模板点击处理)
        布局.addWidget(self.模板列表)

        # 中部：模板编辑输入框
        self.模板输入框 = QTextEdit()
        self.模板输入框.setPlaceholderText("在此编辑模板内容...")
        self.模板输入框.setMaximumHeight(100)
        self.模板输入框.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        布局.addWidget(self.模板输入框)

        # 下部：三个按钮
        按钮容器 = QWidget()
        按钮布局 = QHBoxLayout(按钮容器)
        按钮布局.setContentsMargins(0, 0, 0, 0)
        按钮布局.setSpacing(5)

        删除模板按钮 = QPushButton("删除模板")
        删除模板按钮.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        删除模板按钮.clicked.connect(self._删除模板)

        保存模板按钮 = QPushButton("保存模板")
        保存模板按钮.setStyleSheet("""
            QPushButton {
                background-color: #8e44ad;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #9b59b6; }
        """)
        保存模板按钮.clicked.connect(self._保存模板)

        清空模板按钮 = QPushButton("清空模板")
        清空模板按钮.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #d35400; }
        """)
        清空模板按钮.clicked.connect(self._清空模板)

        按钮布局.addWidget(删除模板按钮)
        按钮布局.addWidget(保存模板按钮)
        按钮布局.addWidget(清空模板按钮)
        布局.addWidget(按钮容器)

        self.页面堆叠.addWidget(页面)

    # ========== 页面切换 ==========
    def _切换页面(self, 页面索引: int):
        """切换当前显示的页面"""
        self.页面堆叠.setCurrentIndex(页面索引)

        # 更新导航按钮状态
        self.历史按钮.setChecked(页面索引 == 0)
        self.对话按钮.setChecked(页面索引 == 1)
        self.模板按钮.setChecked(页面索引 == 2)

    # ========== 网络服务 ==========
    def _初始化网络服务(self):
        """初始化移动端网络服务"""
        self.网络服务 = 移动端展示节点网络服务()
        self.网络服务.收到数据.connect(self._处理收到数据)
        self.网络服务.服务状态变更.connect(self._处理服务状态变更)
        self.网络服务.发送失败.connect(self._处理发送失败)
        self.网络服务.服务端离线.connect(self._处理服务端离线)

    def _切换网络服务(self):
        """切换网络服务的开关状态"""
        if self.网络服务.是否运行中():
            # 关闭服务
            self.网络服务.发送服务离线通知()
            self.网络服务.停止服务()
        else:
            # 启动服务
            if self.网络服务.启动服务():
                self.网络服务.发送服务上线通知()

    def _处理服务状态变更(self, 运行中: bool):
        """处理网络服务状态变更"""
        if 运行中:
            self.状态标签.setText("🟢 服务运行中")
            self.网络开关按钮.setText("📡 停止服务")
            self.网络开关按钮.setStyleSheet("""
                QPushButton {
                    background-color: #c0392b;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover { background-color: #e74c3c; }
            """)
        else:
            self.状态标签.setText("🟡 未连接")
            self.网络开关按钮.setText("📡 启动服务")
            self.网络开关按钮.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover { background-color: #2ecc71; }
            """)

    def _处理收到数据(self, 数据: dict):
        """处理从主机端收到的数据"""
        消息类型 = 数据.get("type", "")

        if 消息类型 == "message":
            内容 = data.get("content", "")
            if 内容:
                self._添加接收消息(内容)

        elif 消息类型 == "service_online":
            self._服务端在线 = True
            self.状态标签.setText("🟢 主机端在线")

        elif 消息类型 == "service_offline":
            self._服务端在线 = False
            self.状态标签.setText("🟡 主机端离线")

        elif 消息类型 == "heartbeat":
            self._服务端在线 = True

        elif 消息类型 == "sync":
            # 同步数据
            同步数据 = data.get("data", {})
            self._处理同步数据(同步数据)

    def _处理同步数据(self, 数据: dict):
        """处理同步数据包"""
        操作 = 数据.get("操作")
        if 操作 == "history":
            # 同步历史记录
            self.历史数据 = 数据.get("内容", [])
            self._刷新历史列表()
        elif 操作 == "templates":
            # 同步模板
            self.模板数据 = 数据.get("内容", [])
            self._刷新模板列表()

    def _处理发送失败(self, 错误信息: str):
        """处理发送失败"""
        self.状态标签.setText(f"🔴 发送失败")
        QTimer.singleShot(3000, lambda: self.状态标签.setText("🟡 未连接"))

    def _处理服务端离线(self):
        """检测到主机端离线"""
        self._服务端在线 = False
        self.状态标签.setText("🟡 主机端离线")

    # ========== 消息操作 ==========
    def _发送消息(self):
        """发送消息到主机端"""
        基础内容 = self.消息输入框.toPlainText().strip()
        if not 基础内容:
            return

        当前时间 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 检查模板
        最终内容 = 基础内容
        模板前缀 = ""
        if self.选中模板索引 >= 0 and self.选中模板索引 < len(self.模板数据):
            模板前缀 = self.模板数据[self.选中模板索引]
            最终内容 = 模板前缀 + f"``人``:\n{基础内容}"

        # 添加到历史
        数据项 = {
            "类型": "发送",
            "内容": 最终内容,
            "时间": 当前时间,
            "原始输入": 基础内容,
            "使用模板": 模板前缀 if 模板前缀 else None
        }
        self.历史数据.append(数据项)

        # 添加气泡
        self._添加消息气泡(最终内容, "发送", 当前时间)

        # 清空输入
        self.消息输入框.clear()

        # 通过网络发送
        if self.网络服务 and self.网络服务.是否运行中():
            self.网络服务.发送消息(最终内容, "展示_mobile")

        # 刷新历史列表
        self._刷新历史列表()

    def _添加接收消息(self, 内容: str):
        """添加接收到的消息"""
        当前时间 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        数据项 = {
            "类型": "接收",
            "内容": 内容,
            "时间": 当前时间
        }
        self.历史数据.append(数据项)
        self._添加消息气泡(内容, "接收", 当前时间)
        self._刷新历史列表()

    def _添加消息气泡(self, 内容: str, 类型: str, 时间戳: str):
        """添加消息气泡到消息区域"""
        # 计算最大宽度
        对话框宽度 = self.消息区域.viewport().width()
        最大气泡宽度 = int(对话框宽度 * 0.75)

        # 气泡标签
        气泡 = QLabel(内容)
        气泡.setWordWrap(True)
        气泡.setTextInteractionFlags(Qt.TextSelectableByMouse)

        if 类型 == "接收":
            背景色 = "white"
            文字色 = "black"
            对齐 = Qt.AlignLeft
        else:
            背景色 = "#95ec69"
            文字色 = "black"
            对齐 = Qt.AlignRight

        气泡.setStyleSheet(f"""
            QLabel {{
                background-color: {背景色};
                color: {文字色};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }}
        """)
        气泡.setMaximumWidth(最大气泡宽度)
        气泡.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 时间戳
        时间标签 = QLabel(时间戳)
        时间标签.setStyleSheet("color: #999; font-size: 10px; padding: 2px 5px;")
        时间标签.setAlignment(对齐)

        # 行容器
        行容器 = QWidget()
        行布局 = QHBoxLayout(行容器)
        行布局.setContentsMargins(0, 0, 0, 0)
        行布局.setSpacing(5)

        if 类型 == "接收":
            行布局.addWidget(气泡, 0, Qt.AlignLeft)
            行布局.addStretch()
        else:
            行布局.addStretch()
            行布局.addWidget(气泡, 0, Qt.AlignRight)

        # 时间容器
        时间容器 = QWidget()
        时间布局 = QHBoxLayout(时间容器)
        时间布局.setContentsMargins(0, 0, 0, 0)
        if 类型 == "接收":
            时间布局.addWidget(时间标签, 0, Qt.AlignLeft)
            时间布局.addStretch()
        else:
            时间布局.addStretch()
            时间布局.addWidget(时间标签, 0, Qt.AlignRight)

        self.消息布局.addWidget(行容器)
        self.消息布局.addWidget(时间容器)

        # 滚动到底部
        QTimer.singleShot(10, lambda: self.消息区域.verticalScrollBar().setValue(
            self.消息区域.verticalScrollBar().maximum()
        ))

    # ========== 历史页面操作 ==========
    def _历史列表选择变更(self, 当前项, 前一项):
        """历史列表选择变更"""
        if 当前项 is None:
            self.历史详情框.clear()
            return
        索引 = 当前项.data(Qt.UserRole)
        if 0 <= 索引 < len(self.历史数据):
            数据 = self.历史数据[索引]
            显示内容 = f"[{数据['类型']}] {数据['时间']}\n\n{数据['内容']}"
            self.历史详情框.setPlainText(显示内容)

    def _刷新历史列表(self):
        """刷新历史列表显示"""
        self.历史列表.clear()
        for 索引, 数据 in enumerate(self.历史数据):
            预览 = 数据["内容"][:25] + "..." if len(数据["内容"]) > 25 else 数据["内容"]
            项 = QListWidgetItem(f"[{数据['类型']}] {预览}")
            项.setData(Qt.UserRole, 索引)
            self.历史列表.addItem(项)

    def _删除选中历史(self):
        """删除选中的历史记录"""
        当前项 = self.历史列表.currentItem()
        if 当前项 is None:
            QMessageBox.warning(self, "警告", "请先选择一项")
            return

        索引 = 当前项.data(Qt.UserRole)
        if 0 <= 索引 < len(self.历史数据):
            self.历史数据.pop(索引)
            self._刷新历史列表()
            self.历史详情框.clear()

            # 清空并重建消息气泡区域
            while self.消息布局.count():
                项 = self.消息布局.takeAt(0)
                if 项.widget():
                    项.widget().deleteLater()

            # 重建气泡
            for 数据 in self.历史数据:
                self._添加消息气泡(数据["内容"], 数据["类型"], 数据["时间"])

    def _清空全部历史(self):
        """清空全部历史记录"""
        if not self.历史数据:
            return

        回复 = QMessageBox.question(
            self, "确认清空",
            f"确定清空全部 {len(self.历史数据)} 条历史记录吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )

        if 回复 == QMessageBox.Yes:
            self.历史数据.clear()
            self._刷新历史列表()
            self.历史详情框.clear()

            # 清空消息气泡区域
            while self.消息布局.count():
                项 = self.消息布局.takeAt(0)
                if 项.widget():
                    项.widget().deleteLater()

    # ========== 模板页面操作 ==========
    def _模板点击处理(self, 项):
        """模板列表点击处理（支持再次点击取消选中）"""
        if 项 is None:
            return

        if self._上次选中项 == 项:
            self.模板列表.setCurrentItem(None)
            self.选中模板索引 = -1
            self._上次选中项 = None
        else:
            self.选中模板索引 = 项.data(Qt.UserRole)
            self._上次选中项 = 项

    def _刷新模板列表(self):
        """刷新模板列表显示"""
        self.模板列表.clear()
        for i, 模板 in enumerate(self.模板数据):
            预览 = 模板[:25] + "..." if len(模板) > 25 else 模板
            项 = QListWidgetItem(预览)
            项.setData(Qt.UserRole, i)
            self.模板列表.addItem(项)

    def _删除模板(self):
        """删除选中的模板"""
        if self.选中模板索引 < 0 or self.选中模板索引 >= len(self.模板数据):
            QMessageBox.warning(self, "警告", "请先选择要删除的模板")
            return

        回复 = QMessageBox.question(
            self, "确认删除",
            "确定要删除选中的模板吗？",
            QMessageBox.Yes | QMessageBox.No
        )

        if 回复 == QMessageBox.Yes:
            self.模板数据.pop(self.选中模板索引)
            self._刷新模板列表()
            self.选中模板索引 = -1
            self._上次选中项 = None

    def _保存模板(self):
        """保存新模板"""
        模板内容 = self.模板输入框.toPlainText().strip()
        if not 模板内容:
            QMessageBox.warning(self, "警告", "模板内容不能为空")
            return

        self.模板数据.append(模板内容)
        self._刷新模板列表()
        self.模板输入框.clear()
        QMessageBox.information(self, "成功", "模板已保存")

    def _清空模板(self):
        """清空所有模板"""
        if not self.模板数据:
            QMessageBox.information(self, "提示", "模板列表已经是空的")
            return

        回复 = QMessageBox.question(
            self, "确认清空",
            f"确定要清空所有 {len(self.模板数据)} 个模板吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )

        if 回复 == QMessageBox.Yes:
            self.模板数据.clear()
            self._刷新模板列表()
            self.选中模板索引 = -1
            self._上次选中项 = None

    def closeEvent(self, event):
        """关闭窗口时清理"""
        if self.网络服务:
            self.网络服务.发送服务离线通知()
            self.网络服务.停止服务()
        event.accept()


def main():
    """主函数 - 独立运行入口"""
    应用 = QApplication(sys.argv)

    # 设置全局字体
    字体 = QFont("Microsoft YaHei", 10)
    应用.setFont(字体)

    # 设置全局样式
    应用.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QDialog {
            background-color: #f5f5f5;
        }
    """)

    窗口 = 移动端展示节点UI()
    窗口.show()
    sys.exit(应用.exec())


if __name__ == "__main__":
    main()
