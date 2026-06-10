"""
主窗口
"""
import uuid
import json
from pathlib import Path
import time
from datetime import datetime, timezone
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QPlainTextEdit, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox, QInputDialog,
    QMenuBar, QToolBar, QStatusBar, QMenu,
)
from PySide6.QtGui import QUndoStack
from PySide6.QtCore import Qt, QTimer, QSettings, QSize, QPoint, QMimeData
from PySide6.QtGui import QAction, QKeySequence, QDrag

from 核心_基础 import 信号, 流程状态, 节点状态, 状态, 取配置目录, 应用名, 应用版本
from 核心_日志 import 日志
from 核心_插件引擎 import 插件管理, 进程管理, 护栏, 消息树管理, 插件交互管理, 插件信息 # 后面这两个是类本身,用来做判断的,千万不要拿去用
from 界面_画布 import 画布
from 核心_基础 import 协议包装器
from 插件._插件公用 import 插件公用实例

import base64
import traceback

class 插件树(QTreeWidget):
    def __init__(self, 父=None):
        super().__init__(父)
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeWidget.DragOnly)
        self.setSelectionMode(QTreeWidget.SingleSelection)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
        插件名 = item.data(0, Qt.UserRole)
        if not 插件名:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(插件名)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)


样式表 = """
QMainWindow { background-color: #2d2d2d; }
QMenuBar { background-color: #3d3d3d; color: #ffffff; }
QMenuBar::item:selected { background-color: #505050; }
QMenu { background-color: #3d3d3d; color: #ffffff; border: 1px solid #505050; }
QMenu::item:selected { background-color: #505050; }
QToolBar { background-color: #3d3d3d; border: none; spacing: 5px; }
QToolButton { background-color: transparent; color: #ffffff; border: none; padding: 5px; }
QToolButton:hover { background-color: #505050; border-radius: 3px; }
QDockWidget { color: #ffffff; }
QDockWidget::title { background-color: #3d3d3d; padding: 5px; }
QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: none; font-family: Consolas, monospace; font-size: 10pt; }
QListWidget, QTreeWidget { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d; outline: none; }
QListWidget::item:selected, QTreeWidget::item:selected { background-color: #094771; }
QStatusBar { background-color: #007acc; color: #ffffff; }
QLineEdit { background-color: #1e1e1e; color: #ffffff; border: 1px solid #505050; padding: 3px; }
QPushButton { background-color: #0e639c; color: #ffffff; border: none; padding: 5px 15px; border-radius: 3px; }
QPushButton:hover { background-color: #1177bb; }
"""

日志颜色 = {
    "DEBUG": "#808080", "INFO": "#00AA00", "WARNING": "#FFAA00",
    "ERROR": "#FF0000", "CRITICAL": "#FF00FF"
}


class 主窗(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{应用名} v{应用版本}")
        self.setGeometry(100, 100, 1400, 900)
        
        self.撤销栈 = QUndoStack(self)
        self.当前文件 = None
        self.最近文件 = []
        self.自动保存定时器 = None
        
        # 插件历史数据存储: {节点ID: [["写入", "..."], ["输出", "..."], ...]}
        self.插件历史数据 = {}
        
        self._初始化界面()
        self._初始化菜单()
        self._初始化工具栏()
        self._初始化状态栏()
        self._初始化停靠窗()
        self._初始化信号()
        self._加载设置()
        
        插件管理.刷新()
        self._设置自动保存()
        
        日志.信息(f"{应用名} 已启动")
    
    def _初始化界面(self):
        self.画布 = 画布(self)
        self.setCentralWidget(self.画布)
        self.setStyleSheet(样式表)
    
    def _初始化菜单(self):
        菜单栏 = self.menuBar()
        
        文件 = 菜单栏.addMenu("文件(&F)")
        文件.addAction("新建", self._新建, QKeySequence.New)
        文件.addAction("打开...", self._打开, QKeySequence.Open)
        文件.addAction("保存", self._保存, QKeySequence.Save)
        文件.addAction("另存为...", self._另存为, QKeySequence.SaveAs)
        文件.addSeparator()
        self.最近菜单 = 文件.addMenu("最近文件")
        文件.addSeparator()
        文件.addAction("退出", self.close, QKeySequence.Quit)
        
        编辑 = 菜单栏.addMenu("编辑(&E)")
        编辑.addAction(self.撤销栈.createUndoAction(self, "撤销"))
        编辑.addAction(self.撤销栈.createRedoAction(self, "重做"))
        编辑.addSeparator()
        编辑.addAction("删除", self._删除选中, QKeySequence.Delete)
        
        流程 = 菜单栏.addMenu("流程(&R)")
        流程.addAction("开始运行", self._开始运行, "F5")
        流程.addAction("停止运行", self._停止运行, "Shift+F5")
        流程.addAction("单步执行", self._单步执行, "F10")
        
        插件菜单 = 菜单栏.addMenu("插件(&P)")
        插件菜单.addAction("创建插件模板...", self._创建插件)
        插件菜单.addAction("刷新插件列表", self._刷新插件)
        
        设置 = 菜单栏.addMenu("设置(&S)")
        自动保存 = 设置.addAction("自动保存")
        自动保存.setCheckable(True)
        自动保存.setChecked(True)
        自动保存.triggered.connect(self._切换自动保存)
        
        帮助 = 菜单栏.addMenu("帮助(&H)")
        帮助.addAction("关于", self._关于)
    
    def _初始化工具栏(self):
        工具栏 = QToolBar("主工具栏", self)
        工具栏.setObjectName("主工具栏")
        self.addToolBar(工具栏)
        
        工具栏.addAction("▶ 运行", self._开始运行)
        工具栏.addAction("⏹ 停止", self._停止运行)
        工具栏.addSeparator()
        工具栏.addAction("🔍+", lambda: self.画布.scale(1.2, 1.2))
        工具栏.addAction("🔍-", lambda: self.画布.scale(0.8, 0.8))
        工具栏.addAction("🔍 fit", lambda: self.画布.fitInView(self.画布.场景.itemsBoundingRect(), Qt.KeepAspectRatio))
    
    def _初始化状态栏(self):
        self.状态栏 = QStatusBar(self)
        self.setStatusBar(self.状态栏)
        self.状态栏.showMessage("就绪")
    
    def _初始化停靠窗(self):
        self.插件停靠 = QDockWidget("插件列表", self)
        self.插件停靠.setObjectName("插件列表")
        self.插件树 = 插件树()
        self.插件树.setHeaderLabel("插件")
        self.插件树.itemDoubleClicked.connect(self._插件双击)
        self.插件停靠.setWidget(self.插件树)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.插件停靠)
        self._更新插件树()
        
        self.日志停靠 = QDockWidget("日志", self)
        self.日志停靠.setObjectName("日志")
        self.日志面板 = QPlainTextEdit()
        self.日志面板.setReadOnly(True)
        self.日志面板.setMaximumBlockCount(10000)
        self.日志停靠.setWidget(self.日志面板)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.日志停靠)
        
        self.resizeDocks([self.日志停靠], [200], Qt.Vertical)
    
    def _进程启动(self, 节点ID: str, PID: int):
        """进程启动后，自动发送缓存的数据"""
        self.下游信息发送(节点ID)
        缓存数据列 = 状态.取节点数据(节点ID)
        if 缓存数据列:
            # 缓存的是已构建的JSON字符串，直接发送
            失败数 = 0
            for 缓存数据 in 缓存数据列:
                if not 进程管理.发送_数据(节点ID, 缓存数据, 已是协议包=True):
                    失败数 += 1
            if 失败数 != 0:
                日志.调试(f"节点 {节点ID} 发送缓存数据 `` 失败 ``, 失败数量:{失败数} ") 
            else:
                状态.置节点数据(节点ID, None)
                日志.调试(f"节点 {节点ID} 发送缓存数据`成功`")

    def 下游信息发送(self, 节点ID:str):
        """向插件发送它的下游插件的消息字典"""
        # 20260424 # 向插件发送下游节点
        下游节点ID列表 = 状态.取下游节点(节点ID)
        插件信息实例 = 进程管理.取插件信息(节点ID)
        if isinstance(插件信息实例,插件信息):
            插件名称 = 插件信息实例.名称
        下游插件信息典 = {}
        for 下节点ID, _ in 下游节点ID列表:
            节点信息实例 = 进程管理._插件管理.get(下节点ID, {}).get("插件信息", None)
            if isinstance(节点信息实例,插件信息):
                节点信息实例.初始化插件信息_信息典() # 20260424 初始化插件信息字典,原来那套逻辑那个字典里只有空的默认值
                插件信息典 = 节点信息实例.插件信息_信息典
                日志.调试(f"插件的信息典:{插件信息典}", 节点ID)
                下游插件信息典[下节点ID] = 插件信息典
        日志.调试(f"的全部下游插件信息典:{json.dumps(下游插件信息典, indent=2,ensure_ascii=False)}", 节点ID)
        try:
            下游信息更新协议包 = 协议包装器.构建协议包(
                    插件名称= 插件名称 or "#NoNe",
                    运行标识="#NoNe",
                    消息类型="下游信息",
                    传输方式="私密",
                    目标节点=节点ID,
                    数据内容=下游插件信息典,  # {id[str]:插件信息典[dict]}
                )
            日志.调试(f"节点 {节点ID} 下游信息更新协议包已构建:\n包:{json.dumps(下游信息更新协议包, indent=2, ensure_ascii=False)}")
            进程管理.发送_数据(节点ID,下游信息更新协议包,False,True)
            # 状态.置节点数据(节点ID, 协议包装器.打包为JSON(下游信息更新协议包))
            日志.调试(f"节点 {节点ID} 下游信息更新协议包已发送:\n包:{json.dumps(下游信息更新协议包, indent=2, ensure_ascii=False)}")
        except Exception as e:
            日志.错误(f"主程序向节点发送下游信息时错误:{traceback.format_exc()}",节点ID)
    def _初始化信号(self):
        信号.日志输出.connect(self._日志输出)
        状态.流程状态变更.connect(self._流程状态变更)
        状态.节点状态变更.connect(self._节点状态变更)
        插件管理.列表变更.connect(self._更新插件树)
        进程管理.插件下传.connect(self._插件下传) # 参数(节点ID,原始协议包JSON字典本体) (str,dict) # 插件交互管理.进程输出 -> 插件管理器.插件下传 -> self._进程输出 #20260410
        进程管理.进程错误.connect(self._进程错误)
        进程管理.进程启动.connect(self._进程启动)
        信号.请求传递数据.connect(self._on请求传递数据) # 界面_画布.py -> 展示节点 -> _弹出完整窗口
        self.画布.节点创建信号.connect(lambda ID, 项: 状态.置节点状态(ID, 节点状态.空闲))
        self.画布.连线创建信号.connect(lambda a, b, c, d: 状态.添加连线(f"{a}:{b}->{c}:{d}", a, b, c, d))

    def _on请求传递数据(self, 源节点ID: str, 协议包:dict):
        """链接`信号.请求传递数据`,调用_传递数据方法,目前只允许插件节点使用它"""
        if 协议包:
            self._传递数据(源节点ID,发送协议包=协议包)
        else:
            日志.警告("该节点`_on请求传递数据`传入协议包为空", 源节点ID)

    def _设置自动保存(self):
        self.自动保存定时器 = QTimer(self)
        self.自动保存定时器.timeout.connect(self._自动保存)
        self.自动保存定时器.start(30000)
        self.自动保存定时器.stop()
    
    def _加载设置(self):
        设置 = QSettings(str(取配置目录() / "设置.ini"), QSettings.IniFormat)
        if 设置.value("窗口/几何"):
            self.restoreGeometry(设置.value("窗口/几何"))
        if 设置.value("窗口/状态"):
            self.restoreState(设置.value("窗口/状态"))
        self.最近文件 = 设置.value("文件/最近", []) or []
        if isinstance(self.最近文件, str):
            self.最近文件 = [self.最近文件]
    
    def _保存设置(self):
        设置 = QSettings(str(取配置目录() / "设置.ini"), QSettings.IniFormat)
        设置.setValue("窗口/几何", self.saveGeometry())
        设置.setValue("窗口/状态", self.saveState())
        设置.setValue("文件/最近", self.最近文件)
    
    def _更新插件树(self):
        self.插件树.clear()
        for 分类, 插件列表 in sorted(插件管理.按分类().items()):
            分类项 = QTreeWidgetItem(self.插件树)
            分类项.setText(0, 分类)
            分类项.setExpanded(True)
            for 插件项 in sorted(插件列表, key=lambda p: p.名称):
                项 = QTreeWidgetItem(分类项)
                项.setText(0, 插件项.名称)
                项.setData(0, Qt.UserRole, 插件项.名称)
                项.setToolTip(0, 插件项.描述 or "无描述")
    
    def _更新最近菜单(self):
        self.最近菜单.clear()
        if not self.最近文件:
            self.最近菜单.addAction("无").setEnabled(False)
            return
        for 路径 in self.最近文件[:10]:
            动作 = self.最近菜单.addAction(Path(路径).name)
            动作.triggered.connect(lambda checked, p=路径: self._打开文件(p))
        self.最近菜单.addSeparator()
        self.最近菜单.addAction("清空", lambda: setattr(self, '最近文件', []) or self._更新最近菜单())
    
    def _新建(self):
        self.画布.清空画布()
        self.当前文件 = None
        self.插件历史数据.clear()
        self.setWindowTitle(f"{应用名} v{应用版本} - 未命名")
    
    def _打开(self):
        路径, _ = QFileDialog.getOpenFileName(self, "打开", "", "JSON (*.json);;所有文件 (*.*)")
        if 路径:
            self._打开文件(路径)
    
    def _打开文件(self, 路径: str):
        try:
            with open(路径, 'r', encoding='utf-8') as f:
                数据 = json.load(f)
                self.画布.导入字典(数据)
            
            self.插件历史数据 = 数据.get("插件历史数据", {})
            日志.信息(f"加载插件历史数据: {len(self.插件历史数据)} 个节点")
            
            self.当前文件 = 路径
            if 路径 not in self.最近文件:
                self.最近文件.insert(0, 路径)
            self.setWindowTitle(f"{应用名} v{应用版本} - {Path(路径).name}")
            日志.信息(f"打开: {路径}")
        except Exception as e:
            QMessageBox.critical(self, "失败", f"无法打开:\n{e}")
    
    def _保存(self):
        if self.当前文件:
            self._保存到(self.当前文件)
        else:
            self._另存为()
    
    def _另存为(self):
        路径, _ = QFileDialog.getSaveFileName(self, "保存", "", "JSON (*.json);;所有文件 (*.*)")
        if 路径:
            if not 路径.endswith('.json'):
                路径 += '.json'
            self._保存到(路径)
    
    def _保存到(self, 路径: str):
        try:
            数据 = self.画布.导出字典()
            数据["插件历史数据"] = self.插件历史数据
            with open(路径, 'w', encoding='utf-8') as f:
                json.dump(数据, f, indent=2, ensure_ascii=False)
            self.当前文件 = 路径
            if 路径 not in self.最近文件:
                self.最近文件.insert(0, 路径)
            self.setWindowTitle(f"{应用名} v{应用版本} - {Path(路径).name}")
            日志.信息(f"保存: {路径}")
        except Exception as e:
            QMessageBox.critical(self, "失败", f"无法保存:\n{e}")
    
    def _自动保存(self):
        if self.当前文件:
            self._保存到(self.当前文件)
            日志.调试("自动保存完成")
    
    def _删除选中(self):
        for 节点ID in 状态.选中列表:
            信号.节点删除.emit(节点ID)
            if 节点ID in self.插件历史数据:
                del self.插件历史数据[节点ID]
    
    def _开始运行(self):
        状态.置流程状态(流程状态.运行中)
        信号.流程启动.emit()
        日志.信息("流程开始运行")
        for 节点ID, 节点项 in self.画布._节点.items():
            if 节点项.类型 == "开始":
                数据 = 节点项.输出数据
                # 开始节点自己处理协议包
                开始节点协议包 = 协议包装器.构建协议包(
                    源节点=节点ID,
                    插件名称="系统自发",
                    初始节点=节点ID,  # 设置初始节点为自己
                    数据内容=数据,
                    目标节点=None,  # 由路由决定
                    消息类型="输出"
                )
                # 先交给消息树管理器处理(更新消息树消息)
                处理后协议包列表 = 消息树管理.处理输出(开始节点协议包, self.节点ID)
                for 处理后协议包 in 处理后协议包列表:
                    日志.调试(f"开始节点:输出->\n{json.dumps(处理后协议包, indent=2, ensure_ascii=False)}", self.节点ID)
                    self._传递数据(节点ID, 处理后协议包) # 20260420
                
            elif 节点项.类型 == "插件":
                插件信息实例 = 插件管理.取插件(节点项.插件名)
                if 插件信息实例 and 插件信息实例.有效:
                    历史记录 = []
                    if 节点ID in self.插件历史数据:
                        raw_history = self.插件历史数据[节点ID]
                        for item in raw_history:
                            if isinstance(item, list) and len(item) >= 2:
                                历史记录.append({
                                    "方向": item[0],
                                    "内容": item[1],
                                    "时间": datetime.now().isoformat()
                                })
                    
                    if 历史记录:
                        历史协议包 = 协议包装器.构建协议包(
                            插件名称=节点项.插件名,
                            运行标识="#NoNe",
                            消息类型="历史",
                            传输方式="私密",
                            目标节点=节点ID,
                            数据内容=None,
                            历史数据=历史记录,
                            
                        )
                        状态.置节点数据(节点ID, 协议包装器.打包为JSON(历史协议包))
                        日志.调试(f"节点 {节点ID} 历史数据协议包已缓存")

                    进程管理.创建进程(节点ID, 插件信息实例.路径)

    def _传递数据(self, 源节点ID: str,发送协议包:dict|None=None): # 20260410
        """统一的数据传递入口，使用新协议格式
        - 原始协议包传入 协议包JSON-Python字典
        - 用于主程序内置节点的输出封装,不能删除!!!
        - 不能删除!!!"""
        if not 发送协议包: # 20260415
            return
        数据类型,数据 = 插件公用实例.提取输入数据(发送协议包)
        总下游列表 = 状态.取下游节点(源节点ID)
        # 调用路由器向下发送消息    # `挂钩 - 2`
        下游列表 =  路由器.策略路由(发送协议包,总下游列表) # 20260414

        日志.调试(f"节点 {源节点ID} 传递数据到 {len(下游列表)} 个下游,\n列表:{下游列表},\n数据:{数据}")
        源节点 = self.画布._节点.get(源节点ID)
        源端口 = "输出"

        for 目标信息 in 下游列表: # 20260414 
            if isinstance(目标信息, tuple):
                目标ID, 目标端口 = 目标信息
            else:
                目标ID = 目标信息
                目标端口 = "输入"
            目标节点 = self.画布._节点.get(目标ID)
            if not 目标节点 or not 目标节点.scene():
                continue
            # 优先使用原始协议包JSON字典
            if not 发送协议包:
                日志.错误("这个节点没有发送包装好的协议包,'_传递数据'方法不会自主包装数据", 源节点ID)

            # 向节点发送数据
            if 目标节点.类型 == "插件": # ==== 插件节点 ==== (JSONdict)
                self._更新插件历史(目标ID,数据) # 主窗管理上下文历史
                插件交互 = 进程管理._插件管理.get(目标ID, {}).get("插件交互管理", None) # 获取插件交互管理实例 # 20260414
                if isinstance(插件交互,插件交互管理):
                    # 调用实例的发送数据方法向该插件写入
                    发送协议包 = 消息树管理.路由信息更新(目标ID,发送协议包) # 20260416 # 透传目标节点合并标识或者新建目标节点合并标识

                    插件交互.发送数据(发送协议包,已是协议包=True)

                    if not 进程管理.是否运行(目标ID):
                        日志.调试(f"插件节点 {目标ID} 未运行,数据已缓存至'写入队列'")

                else: # 未获取到该实例无法进行任何与插件的操作    
                    日志.警告(f"'插件交互管理'实例不存在: {目标ID}", 目标ID)
    
            elif 目标节点.类型 == "判断": # ==== 判断节点 ==== (数据str)
                try:
                    结果 = 目标节点.处理输入数据(数据)
                    if 结果 is not None:
                        self._传递数据(目标ID, 发送协议包)
                except Exception as e:
                    日志.错误(f"判断节点 {目标ID} 处理异常: {e}")
                    
            elif 目标节点.类型 == "展示": # ==== 展示节点 ==== (数据str)
                try:
                    日志.调试(f"展示节点接收到了:{数据}")
                    目标节点.处理输入数据(数据)
                except Exception as e:
                    日志.错误(f"展示节点 {目标ID} 处理异常: {e}")
                    
            elif 目标节点.类型 == "开始": # ==== 开始节点 ==== (数据str)
                # 开始节点直接处理字符串
                try:
                    目标节点.处理输入(str(数据))
                except Exception as e:
                    日志.错误(f"开始节点 {目标ID} 处理异常: {e}")

    def _更新插件历史(self,插件ID,数据):
        """界面_主窗.py管理历史,在JSON工作流保存的时候会一同保存"""
        if 插件ID not in self.插件历史数据:
            self.插件历史数据[插件ID] = []
        self.插件历史数据[插件ID].append(["写入", str(数据)])

    def _插件下传(self, 节点ID: str, JSON字典本体:dict): # 20260410
        """这里的数据是上游的原始协议包json本体"""
        数据类型,数据 = 插件公用实例.提取输入数据(JSON字典本体)
        if 数据:
            if 节点ID in self.画布._节点 and self.画布._节点[节点ID].类型 == "插件":
                if 节点ID not in self.插件历史数据:
                    self.插件历史数据[节点ID] = []
                self.插件历史数据[节点ID].append(["输出", str(数据)])
                # 日志.调试(f"输出包: {json.dumps(JSON字典本体, indent=2, ensure_ascii=False)}...",节点ID) # 20260416
            # 调用一个重要方法'_传递数据()'
            self._传递数据(节点ID, 发送协议包=JSON字典本体) # 2026/4/10
        else:
            日志.警告("输出协议体,数据容器中没有数据",节点ID)

    def _停止运行(self):
        状态.置流程状态(流程状态.空闲)
        信号.流程停止.emit()
        日志.信息("流程已停止")
        进程管理.停止全部()
    
    def _单步执行(self):
        状态.置流程状态(流程状态.单步)
        信号.流程暂停.emit()
        日志.信息("单步执行")
    
    def _创建插件(self):
        名称, 确定 = QInputDialog.getText(self, "创建插件", "插件名称:")
        if 确定 and 名称:
            描述, _ = QInputDialog.getText(self, "创建插件", "描述:")
            路径 = 插件管理.保存模板(名称, 描述)
            if 路径:
                QMessageBox.information(self, "成功", f"已创建:\n{路径}")
            else:
                QMessageBox.warning(self, "失败", "文件已存在或创建失败")
    
    def _刷新插件(self):
        插件管理.刷新()
        self._更新插件树()
    
    def _切换自动保存(self, 启用):
        if 启用:
            self.自动保存定时器.start()
        else:
            self.自动保存定时器.stop()
    
    def _关于(self):
        QMessageBox.about(self, f"关于 {应用名}",
            f"<h2>{应用名} v{应用版本}</h2><p>AI工具链可视化编排平台</p><p>基于 PySide6</p>")
    
    def _插件双击(self, 项: QTreeWidgetItem, 列: int):
        插件名 = 项.data(0, Qt.UserRole)
        if 插件名:
            self.画布.创建插件节点(self.画布.viewport().rect().center(), 插件名)
    
    def _日志输出(self, 级别: str, 消息: str):
        颜色 = 日志颜色.get(级别, "#FFFFFF")
        self.日志面板.appendHtml(f'<span style="color: {颜色}">[{级别}] {消息}</span>')
    
    def _流程状态变更(self, 状态值):
        名称 = {流程状态.空闲: "空闲", 流程状态.运行中: "运行中", 流程状态.暂停: "暂停",
               流程状态.单步: "单步", 流程状态.错误: "错误"}.get(状态值, "未知")
        self.状态栏.showMessage(f"状态: {名称}")
    
    def _节点状态变更(self, 节点ID: str, 状态值):
        节点项 = self.画布._节点.get(节点ID, None)
        if 节点项:
            节点项.置状态(状态值)
    
    def _进程错误(self, 节点ID: str, 错误: str):
        日志.错误(f"错误: {错误}", 节点ID)
        状态.置节点状态(节点ID, 节点状态.错误)
    
    def closeEvent(self, 事件):
        self._保存设置()
        进程管理.停止全部()
        回复 = QMessageBox.question(self, "确认", "确定退出？", QMessageBox.Yes | QMessageBox.No)
        if 回复 == QMessageBox.Yes:
            日志.信息("程序退出")
            事件.accept()
        else:
            事件.ignore()

class 路由管理器:
    """基于关键词匹配的路由，只选一个插件节点，其他普通节点全保留"""
    def __init__(self, 模型路径=None):
        self.插件信息典 = 进程管理._插件管理  # {节点ID: {"插件交互管理":..., "插件信息":...}}
        self.路由策略方法典 = { # 字典的顺序代表路由策略的优先级 # 20260421
            "展示节点路由":self._策略_展示节点路由,
            "关键词匹配":self._策略_关键词匹配
        }

    def 策略路由(self, 协议包: dict = None, 总下游列表: list = None) -> list:
        """
        从下游列表中只选一个关键词匹配的插件节点，其他普通节点全部保留
        返回: [(节点ID, 端口名), ...] 包含所有普通节点 + 最多1个插件节点
        """
        if not 协议包 or not 总下游列表:
            return 总下游列表 or []
        日志.调试(f"策略路由():总下游列表:{总下游列表}")
        _, 数据 = 护栏.提取输入数据(协议包)
        日志.调试(f"策略路由():提取出的数据{数据},\n类别:{type(数据)}")
        if not isinstance(数据, str):
            return 总下游列表  # 数据不是字符串，无法匹配关键词，全部放行

        for 介绍, 策略方法 in self.路由策略方法典.items():
            # 遍历策略字典, 直到有成功的
            条件成立否, 新下游列表 = 策略方法(协议包, 总下游列表)
            if 条件成立否:
                return 新下游列表

        # 没有任何一种路由是成立的, 极大概率是因为消息有问题
        日志.警告(f"策略路由():没有一种路由策略是成立的,大概率是消息有问题")
        return None

    def _策略_展示节点路由(self, 协议包:dict, 总下游列表: list)->list:
        """具有反引号快但是未被分片的协议包路由给展示节点"""
        # 解析出数据字符串
        目标节点类型 = 消息树管理._获取字段值(协议包,"协议头.路由信息.目标节点类型")
        if 目标节点类型 is not None:
            if 目标节点类型 == "展示":
                # 分离插件节点和普通节点
                展示节点列表 = []
                for 目标信息 in 总下游列表:
                    节点ID = 目标信息[0] if isinstance(目标信息, tuple) else 目标信息

                    节点对象 = 状态.取节点对象(节点ID)
                    节点类型 = getattr(节点对象, "类型", None)
                    if 节点类型 == "展示":
                        展示节点列表.append(目标信息)
                return True,展示节点列表
        return False,None

    def _策略_关键词匹配(self,协议包:dict, 总下游列表: list)->list:
        # 解析出数据字符串
        _, 数据 = 护栏.提取输入数据(协议包)
        if not isinstance(数据, str):
            return True,总下游列表  # 数据不是字符串，无法匹配关键词，全部放行
        # 分离插件节点和普通节点
        插件节点列表 = []
        普通节点列表 = []
        for 目标信息 in 总下游列表:
            节点ID = 目标信息[0] if isinstance(目标信息, tuple) else 目标信息
            端口名 = 目标信息[1] if isinstance(目标信息, tuple) else "输入"
            # 检查是否是插件节点（在进程管理器中注册的就是插件节点）
            if 节点ID in self.插件信息典:
                插件节点列表.append((节点ID, 端口名))
            else:
                普通节点列表.append((节点ID, 端口名))
        # 从插件节点中找第一个关键词匹配的
        选中插件节点 = None
        for 节点ID, 端口名 in 插件节点列表:
            字典 = self.插件信息典.get(节点ID, {})
            插件信息对象 = 字典.get("插件信息")

            if isinstance(插件信息对象, 插件信息):
                关键词 = 插件信息对象.关键词.strip()
                已过滤数据 = 护栏.移除标记间内容("``","``:\n",数据).strip()
                if 已过滤数据.startswith(关键词):
                    选中插件节点 = (节点ID, 端口名)
                    日志.调试(f"关键词路由选中插件: {节点ID}, 关键词: {关键词}")
                    break  # 只选第一个匹配的
        # 合并结果：所有普通节点 + 最多1个选中的插件节点
        更改后下游列表 = 普通节点列表.copy()
        if 选中插件节点:
            更改后下游列表.append(选中插件节点)
        return True, 更改后下游列表

    def _策略_help广播(self,协议包:dict, 总下游列表: list)->list:
        # 解析出数据字符串
        _, 数据 = 护栏.提取输入数据(协议包)
        if not isinstance(数据, str):
            return False, 总下游列表  # 数据不是字符串，无法匹配关键词，全部放行
        if 插件公用实例.移除标记间内容("``", "``:", 数据).strip() == "/help":
            return True, 总下游列表
        else:
            return False, None
    
    def _策略_向量路由(self,协议包:dict, 总下游列表: list)->list:
        """预留:使用几个权重层进行相似度计算然后提取出最相似的那个插件进行路由"""
        pass

路由器 = 路由管理器()
