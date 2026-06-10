"""
画布组件 - 节点、连线、端口
"""
# 创建主分割器（三栏布局）
import uuid
from typing import Optional, Dict, List
from PySide6.QtWidgets import (QTextEdit,QSplitter, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLabel,
    QLineEdit, QScrollArea, QFrame, QSizePolicy,QGraphicsView, QGraphicsScene,QGraphicsItem, QGraphicsRectItem, 
    QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsTextItem,QGraphicsItemGroup, QGraphicsProxyWidget, QLineEdit, 
    QMenu, QMessageBox, QInputDialog, QGraphicsPolygonItem, QListWidgetItem, QDialog
)
from datetime import datetime
from PySide6.QtCore import (Qt, QRectF, QPointF, QLineF, Signal, QPoint, QMimeData, QSizeF, QEvent,
                            QTimer, )
from PySide6.QtGui import (QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QTextCursor, QPolygonF, QKeyEvent,
                           QFontMetrics, QKeySequence, QShortcut)

from 核心_插件引擎 import 进程管理, 消息树管理 # 通讯插件
from 核心_基础 import 信号, 节点状态, 状态, 协议包装器
from 核心_日志 import 日志

import _tools as tools
import json

# 导入展示节点网络服务
try:
    from 展示节点网络服务 import 展示节点网络服务
except ImportError:
    展示节点网络服务 = None

# ========== 颜色配置 ==========
画布背景色 = QColor(45, 45, 45)
网格颜色 = QColor(60, 60, 60)
连线颜色 = QColor(150, 150, 150)
连线选中色 = QColor(100, 200, 100)
输入端口色 = QColor(100, 200, 100)
输出端口色 = QColor(200, 100, 100)
端口悬停色 = QColor(255, 255, 100)
按钮颜色 = QColor(80, 80, 80)
按钮悬停色 = QColor(100, 100, 100)
按钮按下色 = QColor(60, 60, 60)

# ========== 网格 ==========
class 网格(QGraphicsItem):
    def __init__(self, 大小=5000, 格子=20):
        super().__init__()
        self.大小 = 大小
        self.格子 = 格子
        self.setZValue(-1000)
    
    def boundingRect(self):
        return QRectF(-self.大小/2, -self.大小/2, self.大小, self.大小)
    
    def paint(self, 画笔, 选项, 部件=None):
        画笔.setPen(QPen(网格颜色, 0.5))
        for x in range(-self.大小//2, self.大小//2 + 1, self.格子):
            画笔.drawLine(x, -self.大小//2, x, self.大小//2)
        for y in range(-self.大小//2, self.大小//2 + 1, self.格子):
            画笔.drawLine(-self.大小//2, y, self.大小//2, y)

# ========== 连线 ==========
class 连线(QGraphicsPathItem):
    """独立类，直接来自场景"""
    def __init__(self, 起点端口=None, 终点端口=None, 连线ID=None):
        super().__init__()
        self.连线ID = 连线ID or str(uuid.uuid4().hex[:8])  # 生成唯一ID
        self.起点端口 = 起点端口
        self.终点端口 = 终点端口
        self.临时终点 = None
        self.setZValue(0)
        self.setPen(QPen(连线颜色, 2))
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.更新路径()
    
    def 更新路径(self):
        if not self.起点端口:
            return
        
        起点 = self.起点端口.scenePos() + self.起点端口.boundingRect().center()
        
        if self.终点端口:
            终点 = self.终点端口.scenePos() + self.终点端口.boundingRect().center()
        elif self.临时终点:
            终点 = self.临时终点
        else:
            return
        
        路径 = QPainterPath()
        路径.moveTo(起点)
        
        dx = abs(终点.x() - 起点.x())
        控制距离 = max(dx * 0.5, 50)
        
        控制1 = QPointF(起点.x() + 控制距离, 起点.y())
        控制2 = QPointF(终点.x() - 控制距离, 终点.y())
        
        路径.cubicTo(控制1, 控制2, 终点)
        self.setPath(路径)
    
    def 置临时终点(self, 位置):
        self.临时终点 = 位置
        self.更新路径()
    
    def 完成(self, 终点端口):
        self.终点端口 = 终点端口
        self.临时终点 = None
        self.更新路径()

    def 移除连线自己(self):
        """从两端端口移除这条连线的引用"""
        # 安全地从起点端口移除
        try:
            if self.起点端口 and hasattr(self.起点端口, '连线列表'):
                if self in self.起点端口.连线列表:
                    self.起点端口.连线列表.remove(self)
                    日志.调试(f"从起点端口移除连线")
        except Exception as e:
            日志.调试(f"从起点端口移除连线失败: {e}")
        # 安全地从终点端口移除  
        try:
            if self.终点端口 and hasattr(self.终点端口, '连线列表'):
                if self in self.终点端口.连线列表:
                    self.终点端口.连线列表.remove(self)
                    日志.调试(f"从终点端口移除连线")
        except Exception as e:
            日志.调试(f"从终点端口移除连线失败: {e}")
        # 清空引用，帮助垃圾回收
        self.起点端口 = None
        self.终点端口 = None

    def paint(self, 画笔, 选项, 部件=None):
        if self.isSelected():
            self.setPen(QPen(连线选中色, 3))
        else:
            self.setPen(QPen(连线颜色, 2))
        super().paint(画笔, 选项, 部件)

# ========== 端口 ==========
端口圆点直径 = 12
class 端口(QGraphicsEllipseItem):
    def __init__(self, 名称: str, 类型: str, 父类=None):
        super().__init__(0, 0, 端口圆点直径, 端口圆点直径, 父类)
        self.名称 = 名称
        self.类型 = 类型  # "输入" 或 "输出"
        self.连线列表: List[连线] = []
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.更新颜色()
    
    def 更新颜色(self):
        if self.类型 == "输入":
            self.setBrush(QBrush(输入端口色))
        else:
            self.setBrush(QBrush(输出端口色))
        self.setPen(QPen(Qt.black, 1))
    
    def hoverEnterEvent(self, 事件):
        self.setBrush(QBrush(端口悬停色))
        super().hoverEnterEvent(事件)
    
    def hoverLeaveEvent(self, 事件):
        self.更新颜色()
        super().hoverLeaveEvent(事件)
    
    def 添加连线(self, 连线项):
        self.连线列表.append(连线项)
    
    def 可连接(self, 其他) -> bool:
        """检查两个端口是否可以连接"""
        if self.类型 == 其他.类型:
            return False  # 同类型不能连接（输入连输入、输出连输出）
        if self.parentItem() == 其他.parentItem():
            return False  # 同一节点不能自连
        if 其他.类型 == "输入" and len(其他.连线列表) > 0:
            return False  # 输入端口只能有一个连接
        return True
    
    def 删除端口自己(self,端口名称: str,节点项):
        """只负责将自己从节点字典中移除"""
        if 端口名称 in 节点项.输入端口:
            节点项.输入端口.pop(端口名称)
        if 端口名称 in 节点项.输出端口:
            节点项.输出端口.pop(端口名称)
    
    def itemChange(self, 变化, 值):
        if 变化 == QGraphicsItem.ItemScenePositionHasChanged:
            for 连线 in self.连线列表:
                连线.更新路径()
        return super().itemChange(变化, 值)

# ========== 添加按钮控件 ==========
添加端口按钮直径 = 6
class 添加端口按钮(QGraphicsRectItem):
    """节点两侧的添加按钮"""
    def __init__(self, 方向: str, 父节点=None):
        """方向: "左" 或 "右" """
        super().__init__(0, 0, 添加端口按钮直径, 添加端口按钮直径, parent=父节点)
        self.方向 = 方向
        self.父节点 = 父节点
        self.setZValue(15)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self._悬停 = False
        self._按下 = False
        self.更新外观()
    
    def 更新外观(self):
        if self._按下:
            颜色 = 按钮按下色
        elif self._悬停:
            颜色 = 按钮悬停色
        else:
            颜色 = 按钮颜色
        
        self.setBrush(QBrush(颜色))
        self.setPen(QPen(QColor(120, 120, 120), 1))
    
    def hoverEnterEvent(self, 事件):
        self._悬停 = True
        self.更新外观()
        super().hoverEnterEvent(事件)
    
    def hoverLeaveEvent(self, 事件):
        self._悬停 = False
        self._按下 = False
        self.更新外观()
        super().hoverLeaveEvent(事件)
    
    def mousePressEvent(self, 事件):
        if 事件.button() == Qt.LeftButton:
            self._按下 = True
            self.更新外观()
            事件.accept()
    
    def mouseReleaseEvent(self, 事件):
        if 事件.button() == Qt.LeftButton and self._按下:
            self._按下 = False
            self.更新外观()
            事件.accept()

# ========== 节点基类 ==========
class 节点(QGraphicsItemGroup):
    def __init__(self, 节点ID: str, 类型: str, 名称: str = "", 端口距离=None):
        super().__init__()
        self.节点ID = 节点ID
        self.类型 = 类型
        self.名称 = 名称 or 类型
        self.状态 = 节点状态.空闲
        self.端口距离 = 端口距离 if isinstance(端口距离, int) else 7
        self.输入端口: Dict[str, 端口] = {}
        self.输出端口: Dict[str, 端口] = {}
        self.端口圆点直径 = 端口圆点直径 
        
        self.左侧按钮: Optional[添加端口按钮] = None
        self.右侧按钮: Optional[添加端口按钮] = None
        
        self.setZValue(1)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        self._is_dragging = False
        self._drag_start_pos = QPointF()
        
        self._初始化()
    
    def _初始化(self):
        pass
    
    def 计算端口位置(self, 端口类型):
        y位置 = 0
        if 端口类型 == "输入":
            y位置 = (len(self.输入端口) * (self.端口圆点直径 + 2)) + (self.端口圆点直径 / 2)
        elif 端口类型 == "输出":
            y位置 = (len(self.输出端口) * (self.端口圆点直径 + 2)) + (self.端口圆点直径 / 2)
        return y位置

    def 添加输入端口(self, 名称: str=None):
        if 名称 is None:
            名称 = tools.随机起名(名首="In",查重集=set(self.输入端口))
        端口项 = 端口(名称, "输入", self)
        y位置 = self.计算端口位置("输入")
        端口项.setPos(-self.端口距离 - self.端口圆点直径, y位置)
        self.输入端口[名称] = 端口项
    
    def 添加输出端口(self, 名称: str=None):
        if 名称 is None:
            名称 = tools.随机起名(名首="Out",查重集=set(self.输出端口))
        端口项 = 端口(名称, "输出", self)
        y位置 = self.计算端口位置("输出")
        端口项.setPos(self.boundingRect().width() + self.端口距离, y位置)
        self.输出端口[名称] = 端口项

    def 删除端口(self, 名称: str):
        if 名称 in self.输入端口:
            del self.输入端口[名称]
        if 名称 in self.输出端口:
            del self.输出端口[名称]

    def 创建左右按钮(self, 节点宽度: float, 节点高度: float):
        self.左侧按钮 = 添加端口按钮("左", self)
        左按钮y = (节点高度 + 2)
        self.左侧按钮.setPos(2, 左按钮y)
        
        self.右侧按钮 = 添加端口按钮("右", self)
        右按钮y = (节点高度 + 2)
        self.右侧按钮.setPos(节点宽度-2-添加端口按钮直径, 右按钮y)
        
        self.addToGroup(self.左侧按钮)
        self.addToGroup(self.右侧按钮)
    
    def 置状态(self, 状态值):
        self.状态 = 状态值
        self._更新外观()
    
    def _更新外观(self):
        pass
    
    def 取端口(self, 名称: str, 类型: str = None):
        if 类型 == "输入" or 类型 is None:
            if 名称 in self.输入端口:
                return self.输入端口[名称]
        if 类型 == "输出" or 类型 is None:
            if 名称 in self.输出端口:
                return self.输出端口[名称]
        return None

    def itemChange(self, 变化, 值):
        if 变化 == QGraphicsItem.ItemPositionHasChanged:
            for 端口项 in list(self.输入端口.values()) + list(self.输出端口.values()):
                for 连 in 端口项.连线列表:
                    连.更新路径()
        return super().itemChange(变化, 值)
    
    def mousePressEvent(self, 事件):
        if 事件.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = self.mapToScene(事件.pos()) - self.pos()
            self.setCursor(Qt.ClosedHandCursor)
            
            状态.选中节点(self.节点ID, not (事件.modifiers() & Qt.ControlModifier))
            信号.节点选中.emit(self.节点ID)
            
            事件.accept()
            return
        
        super().mousePressEvent(事件)
    
    def mouseMoveEvent(self, 事件):
        if not self._is_dragging:
            super().mouseMoveEvent(事件)
            return
        
        当前场景坐标 = self.mapToScene(事件.pos())
        新位置 = 当前场景坐标 - self._drag_start_pos
        self.setPos(新位置)
        信号.节点移动.emit(self.节点ID, 新位置)
        事件.accept()
    
    def mouseReleaseEvent(self, 事件):
        if 事件.button() == Qt.LeftButton and self._is_dragging:
            self._is_dragging = False
            self.unsetCursor()
            事件.accept()
            return
        
        super().mouseReleaseEvent(事件)
    
    def contextMenuEvent(self, 事件):
        菜单 = QMenu()
        重命名 = 菜单.addAction("重命名")
        重命名.triggered.connect(self._重命名)
        菜单.addSeparator()
        删除 = 菜单.addAction("删除")
        删除.triggered.connect(self._删除)
        菜单.exec(事件.screenPos())
    
    def _重命名(self):
        新名称, 确定 = QInputDialog.getText(None, "重命名", "新名称:", text=self.名称)
        if 确定 and 新名称:
            self.名称 = 新名称
            self._更新名称()
    
    def _更新名称(self):
        pass
    
    def _删除(self):
        回复 = QMessageBox.question(None, "确认", f"删除 '{self.名称}'？", QMessageBox.Yes | QMessageBox.No)
        if 回复 == QMessageBox.Yes:
            信号.节点删除.emit(self.节点ID)
# ========== 开始节点 ==========
class 开始节点(节点):
    """他不需要打包数据,
    但是他的数据实例负责存储在运行后它将要发送的消息str,
    打包数据+切片由调用它的地方来完成"""
    def __init__(self, 节点ID: str, 名称: str = "开始"):
        self.输出数据 = ""
        super().__init__(节点ID, "开始", 名称)
        
    
    def _初始化(self):
        宽度, 高度 = 160, 60
        self.主体 = QGraphicsRectItem(0, 0, 宽度, 高度)
        self.主体.setBrush(QBrush(QColor(100, 150, 100)))
        self.主体.setPen(QPen(QColor(100, 100, 100), 2))
        self.addToGroup(self.主体)
        
        self.创建左右按钮(宽度, 高度)
        
        self.名称标签 = QGraphicsTextItem(self.名称)
        self.名称标签.setPos(10, 5)
        self.addToGroup(self.名称标签)
        
        # 用 QGraphicsTextItem 显示数据，点击弹出编辑框
        self.数据标签 = QGraphicsTextItem(self.输出数据 or "点击输入数据...")
        self.数据标签.setPos(10, 25)
        self.数据标签.setDefaultTextColor(QColor(50, 50, 50))
        # 设置固定宽度，自动换行
        self.数据标签.setTextWidth(140)
        self.addToGroup(self.数据标签)
        
        # 设置光标为手型，提示可点击
        self.数据标签.setCursor(Qt.IBeamCursor)
        
        self.添加输出端口("输出")
    
    def mousePressEvent(self, 事件):
        # 检查点击位置是否在数据标签上
        数据标签本地坐标 = self.数据标签.mapFromParent(事件.pos())
        if self.数据标签.contains(数据标签本地坐标):
            self._弹出编辑对话框()
            事件.accept()
            return
        
        super().mousePressEvent(事件)
    
    def _弹出编辑对话框(self):
        """弹出输入对话框编辑内容"""
        # 创建多行输入对话框（如果数据较长）
        对话框 = QInputDialog(self.scene().views()[0] if self.scene() else None)
        对话框.setWindowTitle(f"编辑 {self.名称}")
        对话框.setLabelText("输入初始数据:")
        对话框.setTextValue(self.输出数据)
        对话框.setTextEchoMode(QLineEdit.Normal)
        
        # 调整大小以适应长文本
        对话框.resize(400, 200)
        
        # 显示对话框并获取结果
        if 对话框.exec() == QInputDialog.Accepted:
            新文本 = 对话框.textValue()
            self.处理输入(新文本)
    
    def 处理输入(self, 文本: str):
        """处理输入文本"""
        if not isinstance(文本, str):
            return
            
        self.输出数据 = 文本
        显示文本 = 文本 if 文本 else "点击输入数据..." # 更新显示标签
        self.数据标签.setPlainText(显示文本)
        信号.节点状态变更.emit(self.节点ID, 文本) # 触发状态变更信号
        日志.信息(f"开始节点 '{self.名称}' 处理输入: {文本[:50]}{'...' if len(文本) > 50 else ''}") # 日志记录
    
    def _更新名称(self):
        self.名称标签.setPlainText(self.名称)
    
    def _更新外观(self):
        颜色 = QColor(self.状态.value) if hasattr(self.状态, 'value') else QColor(100, 150, 100)
        self.主体.setBrush(QBrush(颜色))
# ========== 插件节点 ==========
class 插件节点(节点):
    """它的UI界面只负责显示外观状态,
    它的主要逻辑由底层数据互通来实现"""
    def __init__(self, 节点ID: str, 插件名: str, 名称: str = ""):
        self.插件名 = 插件名
        super().__init__(节点ID, "插件", 名称 or 插件名)
    
    def _初始化(self):
        宽度, 高度 = 180, 80
        
        self.主体 = QGraphicsRectItem(0, 0, 宽度, 高度)
        self.主体.setBrush(QBrush(QColor(100, 100, 150)))
        self.主体.setPen(QPen(QColor(100, 100, 100), 2))
        self.addToGroup(self.主体)
        
        self.创建左右按钮(宽度, 高度)
        
        self.名称标签 = QGraphicsTextItem(self.名称)
        self.名称标签.setPos(10, 5)
        self.addToGroup(self.名称标签)
        
        self.插件标签 = QGraphicsTextItem(f"[{self.插件名}]")
        self.插件标签.setPos(10, 25)
        字体 = QFont()
        字体.setPointSize(8)
        self.插件标签.setFont(字体)
        self.addToGroup(self.插件标签)
        
        self.状态标签 = QGraphicsTextItem("空闲")
        self.状态标签.setPos(10, 45)
        self.addToGroup(self.状态标签)
        
        self.添加输入端口("输入")
        self.添加输出端口("输出")
    
    def _更新名称(self):
        self.名称标签.setPlainText(self.名称)
    
    def 置状态(self, 状态值):
        super().置状态(状态值)
        状态文本 = {"空闲": "空闲", "就绪": "就绪", "运行中": "运行中", 
                   "等待中": "等待中", "错误": "错误", "禁用": "禁用"}
        self.状态标签.setPlainText(状态文本.get(状态值.name if hasattr(状态值, 'name') else str(状态值), "未知"))
    
    def _更新外观(self):
        颜色 = QColor(self.状态.value) if hasattr(self.状态, 'value') else QColor(100, 100, 150)
        self.主体.setBrush(QBrush(颜色))
# ========== 判断节点 ==========
class 判断节点(节点):
    """它不需要打包,也不需要信号槽,也不需要存储数据,
    它只需要处理输入方法去做条件判断并返回成功或者不成功,
    相当于简易条件判断的UI界面,并不是一个真正的可以解析数据包的节点"""
    def __init__(self, 节点ID: str, 名称: str = "判断"):
        self.判断条件 = "input == ''"  # 默认条件，使用 input 变量
        self.上次输入数据 = None       # 存储上次接收的数据
        super().__init__(节点ID, "判断", 名称)
    
    def _初始化(self):
        宽度, 高度 = 180, 80
        
        多边形 = QPolygonF([QPointF(90, 0), QPointF(180, 40), QPointF(90, 80), QPointF(0, 40)])
        self.主体 = QGraphicsPolygonItem(多边形)
        self.主体.setBrush(QBrush(QColor(150, 100, 100)))
        self.主体.setPen(QPen(QColor(100, 100, 100), 2))
        self.addToGroup(self.主体)
        
        self.创建左右按钮(宽度, 高度)
        
        self.名称标签 = QGraphicsTextItem(self.名称)
        self.名称标签.setPos(60, 15)
        self.addToGroup(self.名称标签)
        
        # 添加可点击的条件标签
        self.条件标签 = QGraphicsTextItem(self.判断条件 or "点击设置条件...")
        self.条件标签.setPos(40, 40)
        self.条件标签.setDefaultTextColor(QColor(50, 50, 50))
        self.条件标签.setTextWidth(100)
        字体 = QFont()
        字体.setPointSize(9)
        self.条件标签.setFont(字体)
        self.条件标签.setCursor(Qt.IBeamCursor)
        self.addToGroup(self.条件标签)
        
        self.添加输入端口("输入")
        self.添加输出端口("输出真")
    
    def mousePressEvent(self, 事件):
        # 检查点击位置是否在条件标签上
        条件标签本地坐标 = self.条件标签.mapFromParent(事件.pos())
        if self.条件标签.contains(条件标签本地坐标):
            self._弹出编辑对话框()
            事件.accept()
            return
        
        super().mousePressEvent(事件)
    
    def _弹出编辑对话框(self):
        """弹出输入对话框编辑判断条件"""
        # 创建自定义对话框，包含编辑和测试功能
        对话框 = QDialog(self.scene().views()[0] if self.scene() else None)
        对话框.setWindowTitle(f"设置 {self.名称} 的条件")
        对话框.resize(400, 250)
        
        布局 = QVBoxLayout(对话框)
        
        提示 = QLabel("输入判断条件，使用变量 input 引用左侧输入数据\n示例: input == 'ok', len(input) > 0, input.startswith('A')", 对话框)
        布局.addWidget(提示)
        
        文本编辑 = QTextEdit(self.判断条件, 对话框)
        文本编辑.setPlaceholderText("input == ''")
        布局.addWidget(文本编辑)
        
        按钮布局 = QHBoxLayout()
        
        测试按钮 = QPushButton("测试执行", 对话框)
        测试按钮.clicked.connect(lambda: self._测试条件(文本编辑.toPlainText()))
        按钮布局.addWidget(测试按钮)
        
        确定按钮 = QPushButton("确定", 对话框)
        确定按钮.clicked.connect(对话框.accept)
        按钮布局.addWidget(确定按钮)
        
        取消按钮 = QPushButton("取消", 对话框)
        取消按钮.clicked.connect(对话框.reject)
        按钮布局.addWidget(取消按钮)
        
        布局.addLayout(按钮布局)
        
        if 对话框.exec() == QDialog.Accepted:
            self.设置条件(文本编辑.toPlainText())
    
    def _测试条件(self, 条件文本: str):
        """测试条件语法是否正确"""
        try:
            test_env = {"input": "测试数据"}
            结果 = eval(条件文本, {"__builtins__": {}}, test_env)
            QMessageBox.information(None, "测试结果", f"条件语法正确！\n测试数据 '测试数据' 的执行结果: {结果}")
        except Exception as e:
            QMessageBox.warning(None, "测试失败", f"条件执行错误: {str(e)}")
    
    def 设置条件(self, 条件: str):
        """处理判断条件，验证语法"""
        if not isinstance(条件, str):
            return
        
        # 简单验证条件语法是否合法
        try:
            test_env = {"input": "test"}
            eval(条件, {"__builtins__": {}}, test_env)
        except SyntaxError as e:
            日志.警告(f"判断条件语法错误: {e}")
            return
        except:
            pass  # 运行时错误在验证时忽略
        
        self.判断条件 = 条件
        
        # 更新显示标签
        显示文本 = 条件 if 条件 else "点击设置条件..."
        self.条件标签.setPlainText(显示文本)
        
        # 触发状态变更信号
        信号.节点状态变更.emit(self.节点ID, 条件)
        日志.信息(f"判断节点 '{self.名称}' 设置条件: {条件[:50]}...")
    
    def 处理输入数据(self, 数据):
        """由外部调用，传入左侧端口的数据"""
        self.上次输入数据 = 数据
        
        # 创建执行环境，input 变量指向接收的数据
        执行环境 = {"input": 数据}
        
        try:
            # 执行条件表达式
            结果 = eval(self.判断条件, {"__builtins__": {}}, 执行环境)
            
            if 结果:
                日志.信息(f"判断节点 '{self.名称}' 条件成立: {self.判断条件}")
                return 数据  # 返回数据，继续向下游传递
            else:
                日志.信息(f"判断节点 '{self.名称}' 条件不成立: {self.判断条件}")
                return None  # 返回 None，停止传递
                
        except Exception as e:
            日志.错误(f"判断节点 '{self.名称}' 条件执行错误: {e}")
            self.置状态(节点状态.错误)
            return None

    def _更新名称(self):
        self.名称标签.setPlainText(self.名称)

    def _更新外观(self):
        颜色 = QColor(self.状态.value) if hasattr(self.状态, 'value') else QColor(150, 100, 100)
        self.主体.setBrush(QBrush(颜色))
# ========== 展示节点 ==========
class 展示节点(节点):
    """由于可以主动发送消息,他需要在发送前打包好自己的数据,并调用信号槽向下传递"""
    def __init__(self, 节点ID: str, 名称: str = "展示"):
        self.历史接收数据: list = []
        self.历史发送数据: list = []
        self.历史数据: list = []
        self.当前显示索引: int = -1
        self.选中模板索引: int = -1
        self.节点ID = 节点ID # 20260417
        # 网络开关状态
        self.网络开关状态 = False
        self.网络服务 = None
        self._网络服务就绪 = False
        super().__init__(节点ID, "展示", 名称)
    
    def _初始化(self):
        宽度, 高度 = 160, 80
        
        self.主体 = QGraphicsRectItem(0, 0, 宽度, 高度)
        self.主体.setBrush(QBrush(QColor(100, 100, 200)))
        self.主体.setPen(QPen(QColor(100, 100, 100), 2))
        self.addToGroup(self.主体)
        
        self.创建左右按钮(宽度, 高度)
        
        self.名称标签 = QGraphicsTextItem(self.名称)
        self.名称标签.setPos(10, 5)
        self.addToGroup(self.名称标签)
        
        # 计数标签
        self.计数标签 = QGraphicsTextItem("接收: 0")
        self.计数标签.setPos(100, 5)
        self.计数标签.setDefaultTextColor(QColor(255, 255, 255))
        字体 = QFont()
        字体.setPointSize(9)
        self.计数标签.setFont(字体)
        self.addToGroup(self.计数标签)
        
        # 触发器输入框：白底黑字，只读，点击触发弹窗
        self.触发框 = QLineEdit()
        self.触发框.setText("点击查看消息")
        self.触发框.setReadOnly(True)
        self.触发框.setFixedWidth(140)
        self.触发框.setFocusPolicy(Qt.NoFocus)
        
        self.触发框.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: black;
                border: 1px solid #888;
                border-radius: 4px;
                padding: 2px;
            }
        """)
        
        # 注意：不直接绑定mousePressEvent，在节点mousePressEvent中处理
        
        self.代理 = QGraphicsProxyWidget(self)
        self.代理.setWidget(self.触发框)
        self.代理.setPos(10, 30)
        self.addToGroup(self.代理)
        
        self.代理.setAcceptedMouseButtons(Qt.LeftButton)
        
        self.添加输入端口("输入")
        self.添加输出端口("输出")
        
        # 存储模板数据
        self.模板数据: list = []
        
        # ========== 网络开关 UI ==========
        self._创建网络开关(宽度)
    
    
    # ========== 网络开关方法 ==========
    def _创建网络开关(self, 节点宽度: float):
        """在节点右上角创建网络开关UI"""
        开关宽度, 开关高度 = 34, 16
        开关x = 节点宽度 - 开关宽度 - 5  # 右上角
        开关y = 3

        # 轨道（圆角矩形）
        self.网络开关轨道 = QGraphicsRectItem(开关x, 开关y, 开关宽度, 开关高度)
        self.网络开关轨道.setBrush(QBrush(QColor(150, 150, 150)))  # 灰色 = 关闭
        self.网络开关轨道.setPen(QPen(Qt.NoPen))
        self.addToGroup(self.网络开关轨道)

        # 滑块（圆形）
        滑块直径 = 14
        self.网络开关滑块 = QGraphicsEllipseItem(开关x + 1, 开关y + 1, 滑块直径, 滑块直径)
        self.网络开关滑块.setBrush(QBrush(Qt.white))
        self.网络开关滑块.setPen(QPen(QColor(120, 120, 120), 1))
        self.addToGroup(self.网络开关滑块)

        # 天线图标
        self.网络开关图标 = QGraphicsTextItem("📡")
        self.网络开关图标.setPos(开关x - 18, 开关y - 2)
        self.网络开关图标.setDefaultTextColor(QColor(180, 180, 180))
        字体 = QFont()
        字体.setPointSize(9)
        self.网络开关图标.setFont(字体)
        self.addToGroup(self.网络开关图标)

        # 开/关文字标签
        self.网络开关文字 = QGraphicsTextItem("关")
        self.网络开关文字.setPos(开关x + 14, 开关y + 1)
        self.网络开关文字.setDefaultTextColor(QColor(255, 255, 255))
        小字体 = QFont()
        小字体.setPointSize(7)
        self.网络开关文字.setFont(小字体)
        self.addToGroup(self.网络开关文字)

        # 存储开关区域用于点击检测
        self._开关区域 = QRectF(开关x - 20, 开关y - 2, 开关宽度 + 24, 开关高度 + 4)

    def _更新网络开关外观(self):
        """根据开关状态更新外观"""
        轨道宽度, 轨道高度 = 34, 16
        开关x = self._开关区域.x() + 20
        开关y = self._开关区域.y() + 2

        if self.网络开关状态:
            # 开启状态：绿色轨道，滑块右移
            self.网络开关轨道.setBrush(QBrush(QColor(76, 175, 80)))
            self.网络开关滑块.setPos(开关x + 轨道宽度 - 15, 开关y + 1)
            self.网络开关图标.setDefaultTextColor(QColor(76, 175, 80))
            self.网络开关文字.setPlainText("开")
            self.网络开关文字.setPos(开关x + 4, 开关y + 1)
        else:
            # 关闭状态：灰色轨道，滑块左移
            self.网络开关轨道.setBrush(QBrush(QColor(150, 150, 150)))
            self.网络开关滑块.setPos(开关x + 1, 开关y + 1)
            self.网络开关图标.setDefaultTextColor(QColor(180, 180, 180))
            self.网络开关文字.setPlainText("关")
            self.网络开关文字.setPos(开关x + 14, 开关y + 1)

    def _切换网络开关(self):
        """切换网络开关状态"""
        if self.网络开关状态:
            # 当前开启 -> 关闭
            self.网络开关状态 = False
            self._更新网络开关外观()
            if self.网络服务:
                self.网络服务.发送服务离线通知()
                self.网络服务.停止服务()
                self.网络服务 = None
            self._网络服务就绪 = False
            日志.信息(f"展示节点 '{self.名称}' 网络服务已关闭")
        else:
            # 当前关闭 -> 开启
            if 展示节点网络服务 is None:
                QMessageBox.warning(None, "警告", "展示节点网络服务模块未加载")
                return
            self.网络开关状态 = True
            self._更新网络开关外观()
            self._初始化网络服务()

        # 触发状态变更信号
        信号.节点状态变更.emit(self.节点ID, f"网络开关:{'开' if self.网络开关状态 else '关'}")

    def _初始化网络服务(self):
        """初始化并启动网络服务"""
        if 展示节点网络服务 is None:
            return
        try:
            self.网络服务 = 展示节点网络服务()
            self.网络服务.收到数据.connect(self._处理网络数据)
            self.网络服务.服务状态变更.connect(self._处理网络服务状态变更)
            self.网络服务.发送失败.connect(self._处理网络发送失败)

            if self.网络服务.启动服务():
                self._网络服务就绪 = True
                self.网络服务.发送服务上线通知()
                日志.信息(f"展示节点 '{self.名称}' 网络服务已启动")
            else:
                self.网络开关状态 = False
                self._更新网络开关外观()
                self._网络服务就绪 = False
        except Exception as e:
            日志.错误(f"展示节点 '{self.名称}' 启动网络服务失败: {e}")
            self.网络开关状态 = False
            self._更新网络开关外观()
            self._网络服务就绪 = False

    def _处理网络数据(self, 数据: dict):
        """处理从手机端收到的网络数据"""
        消息类型 = 数据.get("type", "")

        if 消息类型 == "message":
            内容 = 数据.get("content", "")
            if 内容:
                # 作为接收消息处理
                self.处理输入数据(内容)

        elif 消息类型 == "service_online":
            日志.信息("手机端服务已上线")

        elif 消息类型 == "service_offline":
            日志.信息("手机端服务已离线")

        elif 消息类型 == "heartbeat":
            # 心跳包，忽略或记录
            pass

        elif 消息类型 == "sync":
            # 同步数据
            同步数据 = 数据.get("data", {})
            self._处理同步数据(同步数据)

        elif 消息类型 == "kill_switch":
            # 杀死开关激活
            日志.警告(f"展示节点 '{self.名称}' 收到杀死开关指令！网络服务被永久禁用。")
            self.网络开关状态 = False
            self._更新网络开关外观()
            if self.网络服务:
                self.网络服务.停止服务()
                self.网络服务 = None
            self._网络服务就绪 = False
            # 阻止再次开启
            QMessageBox.critical(None, "安全警告", "收到杀死开关指令！\n网络服务已被永久禁用，无法重启。")

    def _处理同步数据(self, 数据: dict):
        """处理同步数据包"""
        操作 = 数据.get("操作")
        if 操作 == "history":
            # 同步历史记录
            self.历史数据 = 数据.get("内容", [])
        elif 操作 == "templates":
            # 同步模板
            self.模板数据 = 数据.get("内容", [])

    def _处理网络服务状态变更(self, 运行中: bool):
        """处理网络服务状态变更"""
        self._网络服务就绪 = 运行中
        if not 运行中 and self.网络开关状态:
            # 服务异常停止，更新开关状态
            self.网络开关状态 = False
            self._更新网络开关外观()

    def _处理网络发送失败(self, 错误信息: str):
        """处理网络发送失败"""
        日志.警告(f"展示节点 '{self.名称}' 网络发送失败: {错误信息}")

    def _同步发送消息到网络(self, 内容: str):
        """将发送的消息同步到网络"""
        if self.网络开关状态 and self._网络服务就绪 and self.网络服务:
            try:
                self.网络服务.发送消息(内容, self.节点ID)
            except Exception as e:
                日志.调试(f"同步消息到网络失败: {e}")
    def _弹出完整窗口(self):
        """弹出完整的三栏弹窗"""
        # 创建对话框（允许自由调整大小）
        对话框 = QDialog()
        对话框.setWindowTitle(f"{self.名称} - 历史数据 ({len(self.历史数据)} 条)")
        对话框.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | 
                             Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        对话框.resize(900, 600)
        主布局 = QHBoxLayout(对话框)
        主布局.setContentsMargins(5, 5, 5, 5)
        主布局.setSpacing(2)
        # ========== 左侧：历史管理 ==========
        左分割器 = QSplitter(Qt.Vertical)
        # 上部：历史列表
        历史列表 = QListWidget()
        历史列表.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        # 填充历史数据
        for 索引, 数据 in enumerate(self.历史数据):
            预览 = 数据["内容"][:30] + "..." if len(数据["内容"]) > 30 else 数据["内容"]
            项 = QListWidgetItem(f"[{数据['类型']}] {预览}")
            项.setData(Qt.UserRole, 索引)
            历史列表.addItem(项)
        
        # 中部：内容白框（只读）
        历史详情框 = QTextEdit()
        历史详情框.setReadOnly(True)
        历史详情框.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        历史详情框.setPlaceholderText("点击上方列表项查看详情...")
        
        # 列表选择变更事件
        def 历史列表选择变更(当前项, 前一项):
            if 当前项 is None:
                历史详情框.clear()
                return
            索引 = 当前项.data(Qt.UserRole)
            if 0 <= 索引 < len(self.历史数据):
                数据 = self.历史数据[索引]
                显示内容 = f"[{数据['类型']}] {数据['时间']}\n\n{数据['内容']}"
                历史详情框.setPlainText(显示内容)
        
        历史列表.currentItemChanged.connect(历史列表选择变更)
        
        # 下部：删除按钮区域
        左按钮容器 = QWidget()
        左按钮布局 = QHBoxLayout(左按钮容器)
        左按钮布局.setContentsMargins(0, 0, 0, 0)
        
        def 删除选中():
            当前项 = 历史列表.currentItem()
            if 当前项 is None:
                QMessageBox.warning(对话框, "警告", "请先选择一项")
                return
            
            索引 = 当前项.data(Qt.UserRole)
            if 索引 < 0 or 索引 >= len(self.历史数据):
                return
            
            数据 = self.历史数据[索引]
            回复 = QMessageBox.question(
                对话框, "确认删除",
                f"确定删除这条{数据['类型']}记录吗？\n\n{数据['内容'][:100]}...",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if 回复 == QMessageBox.Yes:
                删除项 = self.历史数据.pop(索引)
                if 删除项["类型"] == "接收" and 删除项["内容"] in self.历史接收数据:
                    self.历史接收数据.remove(删除项["内容"])
                elif 删除项["类型"] == "发送" and 删除项["内容"] in self.历史发送数据:
                    self.历史发送数据.remove(删除项["内容"])
                
                # 重建列表
                历史列表.clear()
                for i, d in enumerate(self.历史数据):
                    预览 = d["内容"][:30] + "..." if len(d["内容"]) > 30 else d["内容"]
                    项 = QListWidgetItem(f"[{d['类型']}] {预览}")
                    项.setData(Qt.UserRole, i)
                    历史列表.addItem(项)
                
                历史详情框.clear()
                self._更新计数显示()
                日志.信息(f"展示节点 '{self.名称}' 删除历史项")
        
        def 清空历史():
            if not self.历史数据:
                return
            
            回复 = QMessageBox.question(
                对话框, "确认清空",
                f"确定清空全部 {len(self.历史数据)} 条历史记录吗？\n此操作不可恢复！",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if 回复 == QMessageBox.Yes:
                self.历史数据.clear()
                self.历史接收数据.clear()
                self.历史发送数据.clear()
                历史列表.clear()
                历史详情框.clear()
                self._更新计数显示()
                日志.信息(f"展示节点 '{self.名称}' 清空全部历史")
        
        删除选中按钮 = QPushButton("删除选中项")
        删除选中按钮.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #ff5252; }
        """)
        删除选中按钮.clicked.connect(删除选中)
        
        清空历史按钮 = QPushButton("清空历史")
        清空历史按钮.setStyleSheet("""
            QPushButton {
                background-color: #ff9f43;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #ff8c00; }
        """)
        清空历史按钮.clicked.connect(清空历史)
        
        左按钮布局.addWidget(删除选中按钮)
        左按钮布局.addWidget(清空历史按钮)
        
        左分割器.addWidget(历史列表)
        左分割器.addWidget(历史详情框)
        左分割器.addWidget(左按钮容器)
        左分割器.setSizes([200, 150, 50])
        左分割器.setMinimumWidth(200)
        
        # ========== 中央：对话交互 ==========
        中分割器 = QSplitter(Qt.Vertical)
        
        # 上部：滚动对话框（气泡模式）
        对话框区域 = QScrollArea()
        对话框区域.setWidgetResizable(True)
        对话框区域.setStyleSheet("""
            QScrollArea {
                background-color: #e5e5e5;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        对话框区域.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        对话框容器 = QWidget()
        对话框布局 = QVBoxLayout(对话框容器)
        对话框布局.setAlignment(Qt.AlignTop)
        对话框布局.setSpacing(10)
        对话框布局.setContentsMargins(10, 10, 10, 10)
        对话框区域.setWidget(对话框容器)
        
        # 填充已有消息气泡
        for 数据 in self.历史数据:
            self._添加消息气泡到布局(对话框布局, 数据["内容"], 数据["类型"], 数据["时间"], 对话框区域)
        
        # 中部：多行输入框
        消息输入框 = QTextEdit()
        消息输入框.setPlaceholderText("输入消息... (Ctrl+Enter发送)")
        消息输入框.setMaximumHeight(100)
        消息输入框.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        
        # 下部：发送按钮
        发送按钮 = QPushButton("发送 (Ctrl+Enter)")
        发送按钮.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
        """)
        
        # 发送功能
        def 发送消息():
            基础内容 = 消息输入框.toPlainText().strip()
            if not 基础内容:
                QMessageBox.warning(对话框, "警告", "消息内容不能为空")
                return
            
            # 检查模板
            最终内容 = 基础内容
            模板前缀 = ""
            if self.选中模板索引 >= 0 and self.选中模板索引 < len(self.模板数据):
                模板前缀 = self.模板数据[self.选中模板索引]
                最终内容 = 模板前缀 + f"``人``:\n{基础内容}"
            
            当前时间 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 添加到历史
            数据项 = {
                "类型": "发送",
                "内容": 最终内容,
                "时间": 当前时间,
                "原始输入": 基础内容,
                "使用模板": 模板前缀 if 模板前缀 else None
            }
            self.历史数据.append(数据项)
            self.历史发送数据.append(最终内容)
            
            # 更新左侧列表
            预览 = 最终内容[:30] + "..." if len(最终内容) > 30 else 最终内容
            项 = QListWidgetItem(f"[发送] {预览}")
            项.setData(Qt.UserRole, len(self.历史数据) - 1)
            历史列表.addItem(项)
            历史列表.scrollToBottom()
            
            # 添加气泡
            self._添加消息气泡到布局(对话框布局, 最终内容, "发送", 当前时间, 对话框区域)
            
            # 清空输入
            消息输入框.clear()

            展示节点协议包 = 协议包装器.构建协议包(
                源节点=self.节点ID,
                插件名称="人",
                初始节点=self.节点ID,  # 设置初始节点为自己
                数据内容=最终内容,
                目标节点=None,  # 由路由决定
                消息类型="输出"
            )
            self._更新计数显示()
            # 先交给消息树管理器处理(更新消息树消息)
            处理后协议包列表 = 消息树管理.处理输出(展示节点协议包, self.节点ID)
            for 处理后协议包 in 处理后协议包列表:
                日志.调试(f"展示节点:输出->\n{json.dumps(处理后协议包, indent=2, ensure_ascii=False)}", self.节点ID)
                # 触发信号,传递消息
                信号.请求传递数据.emit(self.节点ID, 处理后协议包) # 展示节点发送数据 # 20260418
            
            # ========== 网络同步 ==========
            self._同步发送消息到网络(最终内容)
                
        
        发送按钮.clicked.connect(发送消息)
        
        # Ctrl+Enter 快捷键
        快捷键 = QShortcut(QKeySequence("Ctrl+Return"), 消息输入框)
        快捷键.activated.connect(发送消息)
        
        中分割器.addWidget(对话框区域)
        中分割器.addWidget(消息输入框)
        中分割器.addWidget(发送按钮)
        中分割器.setSizes([350, 80, 50])
        中分割器.setMinimumWidth(300)
        
        # ========== 右侧：模板管理 ==========
        右分割器 = QSplitter(Qt.Vertical)
        
        # 上部：模板列表
        模板列表 = QListWidget()
        模板列表.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        
        # 填充模板
        for i, 模板 in enumerate(self.模板数据):
            预览 = 模板[:30] + "..." if len(模板) > 30 else 模板
            项 = QListWidgetItem(预览)
            项.setData(Qt.UserRole, i)
            模板列表.addItem(项)
        
        # 模板选择变更 - 支持再次点击取消选中
        self._上次选中项 = None  # 用于追踪上次选中的项
        
        def 模板点击处理(项):
            if 项 is None:
                return
            
            # 检查是否是再次点击同一项
            if self._上次选中项 == 项:
                # 再次点击，取消选中
                模板列表.setCurrentItem(None)
                self.选中模板索引 = -1
                self._上次选中项 = None
                日志.调试(f"展示节点 '{self.名称}' 取消模板选中")
            else:
                # 新选中项
                self.选中模板索引 = 项.data(Qt.UserRole)
                self._上次选中项 = 项
        
        # 使用 itemClicked 信号来捕获每次点击，包括再次点击同一项
        模板列表.itemClicked.connect(模板点击处理)
        
        # 保留 currentItemChanged 用于处理键盘导航等情况
        def 模板选择变更(当前项, 前一项):
            if 当前项 is None:
                self.选中模板索引 = -1
                self._上次选中项 = None
        
        模板列表.currentItemChanged.connect(模板选择变更)
        
        # 中部：模板输入框
        模板输入框 = QTextEdit()
        模板输入框.setPlaceholderText("在此编辑模板内容...")
        模板输入框.setMaximumHeight(100)
        模板输入框.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        
        # 下部：三个按钮布局（删除模板 | 保存模板 | 清空模板）
        按钮容器 = QWidget()
        按钮布局 = QHBoxLayout(按钮容器)
        按钮布局.setContentsMargins(0, 0, 0, 0)
        按钮布局.setSpacing(5)
        
        # 左侧：删除模板按钮
        def 删除模板():
            if self.选中模板索引 < 0 or self.选中模板索引 >= len(self.模板数据):
                QMessageBox.warning(对话框, "警告", "请先选择要删除的模板")
                return
            
            模板内容 = self.模板数据[self.选中模板索引]
            预览 = 模板内容[:50] + "..." if len(模板内容) > 50 else 模板内容
            
            回复 = QMessageBox.question(
                对话框, "确认删除",
                f"确定要删除以下模板吗？\n\n{预览}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if 回复 == QMessageBox.Yes:
                删除内容 = self.模板数据.pop(self.选中模板索引)
                
                # 重建列表
                模板列表.clear()
                for i, 模板 in enumerate(self.模板数据):
                    预览 = 模板[:30] + "..." if len(模板) > 30 else 模板
                    项 = QListWidgetItem(预览)
                    项.setData(Qt.UserRole, i)
                    模板列表.addItem(项)
                
                # 重置选中状态
                self.选中模板索引 = -1
                self._上次选中项 = None
                模板列表.setCurrentItem(None)
                
                QMessageBox.information(对话框, "成功", "模板已删除")
                日志.信息(f"展示节点 '{self.名称}' 删除模板: {删除内容[:50]}...")
        
        删除模板按钮 = QPushButton("删除模板")
        删除模板按钮.setStyleSheet("""
            QPushButton {
                background-color: #ff6b6b;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #ff5252; }
            QPushButton:pressed { background-color: #e04545; }
        """)
        删除模板按钮.clicked.connect(删除模板)
        
        # 中间：保存模板按钮
        def 保存模板():
            模板内容 = 模板输入框.toPlainText().strip()
            if not 模板内容:
                QMessageBox.warning(对话框, "警告", "模板内容不能为空")
                return
            
            self.模板数据.append(模板内容)
            
            预览 = 模板内容[:30] + "..." if len(模板内容) > 30 else 模板内容
            项 = QListWidgetItem(预览)
            项.setData(Qt.UserRole, len(self.模板数据) - 1)
            模板列表.addItem(项)
            
            模板输入框.clear()
            QMessageBox.information(对话框, "成功", "模板已保存")
            日志.信息(f"展示节点 '{self.名称}' 保存模板: {模板内容[:50]}...")
        
        保存模板按钮 = QPushButton("保存模板")
        保存模板按钮.setStyleSheet("""
            QPushButton {
                background-color: #5f27cd;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #4a1fb8; }
            QPushButton:pressed { background-color: #3d1999; }
        """)
        保存模板按钮.clicked.connect(保存模板)
        
        # 右侧：清空模板按钮
        def 清空模板():
            if not self.模板数据:
                QMessageBox.information(对话框, "提示", "模板列表已经是空的")
                return
            
            回复 = QMessageBox.question(
                对话框, "确认清空",
                f"确定要清空所有 {len(self.模板数据)} 个模板吗？\n此操作不可恢复！",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if 回复 == QMessageBox.Yes:
                数量 = len(self.模板数据)
                self.模板数据.clear()
                模板列表.clear()
                
                # 重置选中状态
                self.选中模板索引 = -1
                self._上次选中项 = None
                
                QMessageBox.information(对话框, "成功", f"已清空 {数量} 个模板")
                日志.信息(f"展示节点 '{self.名称}' 清空全部模板 ({数量} 个)")
        
        清空模板按钮 = QPushButton("清空模板")
        清空模板按钮.setStyleSheet("""
            QPushButton {
                background-color: #ff9f43;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #ff8c00; }
            QPushButton:pressed { background-color: #e67e22; }
        """)
        清空模板按钮.clicked.connect(清空模板)
        
        # 添加三个按钮到布局
        按钮布局.addWidget(删除模板按钮)
        按钮布局.addWidget(保存模板按钮)
        按钮布局.addWidget(清空模板按钮)
        
        右分割器.addWidget(模板列表)
        右分割器.addWidget(模板输入框)
        右分割器.addWidget(按钮容器)
        右分割器.setSizes([200, 100, 50])
        右分割器.setMinimumWidth(200)
        
        # ========== 组装三栏 ==========
        主布局.addWidget(左分割器)
        主布局.addWidget(中分割器)
        主布局.addWidget(右分割器)
        
        # 显示对话框（非阻塞，允许自由操作）
        对话框.show()
        
        # ========== 新增：保存对话框关键部件引用，用于实时刷新 ==========
        self._对话框历史列表 = 历史列表
        self._对话框对话框布局 = 对话框布局
        self._对话框区域 = 对话框区域
        
        # 存储引用防止被垃圾回收
        self._当前对话框 = 对话框

    def _添加消息气泡到布局(self, 布局, 内容, 类型, 时间戳, 对话框区域):
        """辅助方法：添加消息气泡到指定布局"""
        
        # 计算最大宽度
        对话框宽度 = 对话框区域.viewport().width()
        最大气泡宽度 = int(对话框宽度 * 0.7)
        
        # 创建气泡标签
        气泡 = QLabel(内容)
        气泡.setWordWrap(True)
        气泡.setTextInteractionFlags(Qt.TextSelectableByMouse)
        气泡.setCursor(Qt.IBeamCursor)
        
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
                font-size: 13px;
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
        
        布局.addWidget(行容器)
        布局.addWidget(时间容器)
        
        # 滚动到底部
        QTimer.singleShot(10, lambda: 对话框区域.verticalScrollBar().setValue(
            对话框区域.verticalScrollBar().maximum()
        ))
    
    def _更新计数显示(self):
        self.计数标签.setPlainText(f"接收: {len(self.历史接收数据)}")
    
    def 处理输入数据(self, 数据):
        """处理接收到的数据"""
        数据字符串 = str(数据) if not isinstance(数据, str) else 数据
        当前时间 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        数据项 = {
            "类型": "接收",
            "内容": 数据字符串,
            "时间": 当前时间
        }
        self.历史数据.append(数据项)
        self.历史接收数据.append(数据字符串)
        self._更新计数显示()
        
        # ========== 新增：实时刷新已打开的对话框 ==========
        if hasattr(self, '_当前对话框') and self._当前对话框 and hasattr(self, '_对话框历史列表'):
            try:
                # 添加新项到左侧历史列表
                预览 = 数据字符串[:30] + "..." if len(数据字符串) > 30 else 数据字符串
                项 = QListWidgetItem(f"[接收] {预览}")
                项.setData(Qt.UserRole, len(self.历史数据) - 1)
                self._对话框历史列表.addItem(项)
                self._对话框历史列表.scrollToBottom()
                # 更新对话框标题
                self._当前对话框.setWindowTitle(f"{self.名称} - 历史数据 ({len(self.历史数据)} 条)")
                # 添加气泡到中央对话框区域
                if hasattr(self, '_对话框对话框布局') and self._对话框对话框布局:
                    self._添加消息气泡到布局(self._对话框对话框布局, 数据字符串, "接收", 当前时间, self._对话框区域)
            except Exception as e:
                日志.调试(f"实时刷新对话框失败: {e}")
        
        # ========== 网络同步：将接收到的数据同步到手机端 ==========
        if self.网络开关状态 and self._网络服务就绪 and self.网络服务:
            try:
                self.网络服务.发送数据({
                    "type": "message",
                    "content": 数据字符串,
                    "node_id": self.节点ID,
                    "timestamp": 当前时间
                })
            except Exception as e:
                日志.调试(f"同步接收数据到网络失败: {e}")
        日志.信息(f"展示节点 '{self.名称}' 接收 [{len(self.历史接收数据)}]: {数据字符串[:50]}...")
        return None

    
    def _更新名称(self):
        self.名称标签.setPlainText(self.名称)
    
    def _更新外观(self):
        颜色 = QColor(self.状态.value) if hasattr(self.状态, 'value') else QColor(100, 100, 200)
        self.主体.setBrush(QBrush(颜色))
    
    def mousePressEvent(self, 事件):
        """处理鼠标点击事件，检测是否点击了触发框区域或网络开关"""
        # 首先检测是否点击了网络开关区域
        if hasattr(self, '_开关区域') and self._开关区域.contains(事件.pos()):
            self._切换网络开关()
            事件.accept()
            return

        # 将事件位置映射到代理的本地坐标
        代理本地坐标 = self.代理.mapFromParent(事件.pos())
        # 检查点击位置是否在代理的边界矩形内
        if self.代理.boundingRect().contains(代理本地坐标):
            self._弹出完整窗口()
            事件.accept()
            return
        # 如果不是点击触发框，调用父类处理
        super().mousePressEvent(事件)

# ============ 画布 ============
class 画布(QGraphicsView):
    节点创建信号 = Signal(str, object)
    节点删除信号 = Signal(str)
    连线创建信号 = Signal(str, str, str, str, str)
    
    def __init__(self, 父=None):
        super().__init__(父)
        self.场景 = QGraphicsScene(self)
        self.setScene(self.场景)
        
        self._节点: Dict[str, 节点] = {}
        self._连线: List[连线] = []
        self._拖拽连线 = None
        self._拖拽起点端口 = None
        self._拖拽中 = False
        self._选中项目列表 = []

        self._单击计时器 = None
        self._单击候选位置 = None
        self._单击候选按钮 = None
        
        self._初始化()
        
        self.网格 = 网格()
        self.场景.addItem(self.网格)
        
        信号.节点删除.connect(self.删除节点)
        self.setFocusPolicy(Qt.StrongFocus)
        self.viewport().setFocusPolicy(Qt.StrongFocus)
    
    def _初始化(self):
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setBackgroundBrush(QBrush(画布背景色))
        self.场景.setSceneRect(-2500, -2500, 5000, 5000)
        self.setAcceptDrops(True)
        
        self._中键按下 = False
        self._中键起始位置 = QPoint()
        self._中键起始滚动条值 = (0, 0)
        self._单击计时器 = QTimer(self)
        self._单击计时器.setSingleShot(True)
        self._单击计时器.timeout.connect(self._处理单击)
        self._单击计时器.setInterval(200)
    
    def _查找端口(self, 场景位置: QPointF) -> Optional[端口]:
        目标项 = self.scene().itemAt(场景位置, self.transform())
        while 目标项 and not isinstance(目标项, 端口):
            目标项 = 目标项.parentItem()
        return 目标项 if isinstance(目标项, 端口) else None
    
    def _查找按钮(self, 场景位置: QPointF) -> Optional[添加端口按钮]:
        目标项 = self.scene().itemAt(场景位置, self.transform())
        while 目标项 and not isinstance(目标项, 添加端口按钮):
            目标项 = 目标项.parentItem()
        return 目标项 if isinstance(目标项, 添加端口按钮) else None
    
    def _查找节点(self, 场景位置: QPointF) -> Optional[节点]:
        目标项 = self.scene().itemAt(场景位置, self.transform())
        while 目标项 and not isinstance(目标项, 节点):
            目标项 = 目标项.parentItem()
        return 目标项 if isinstance(目标项, 节点) else None

    def wheelEvent(self, 事件):
        delta = 事件.angleDelta().y()
        因子 = 1.1 if delta > 0 else 0.9
        当前缩放 = self.transform().m11()
        新缩放 = 当前缩放 * 因子
        if 0.1 <= 新缩放 <= 5.0:
            self.scale(因子, 因子)
    
    def mousePressEvent(self, 事件):
        if 事件.button() == Qt.MiddleButton:
            self._中键按下 = True
            self._中键起始位置 = 事件.pos()
            self._中键起始滚动条值 = (self.horizontalScrollBar().value(), 
                                       self.verticalScrollBar().value())
            self.setCursor(Qt.ClosedHandCursor)
            事件.accept()
            return
        
        if 事件.button() == Qt.LeftButton:
            场景位置 = self.mapToScene(事件.pos())
            端口项 = self._查找端口(场景位置)
            if 端口项:
                self._启动连线拖拽(端口项)
                事件.accept()
                return
            按钮项 = self._查找按钮(场景位置)
            if 按钮项:
                self._单击候选按钮 = 按钮项
                self._单击候选位置 = 场景位置
                事件.accept()
                return
        
        super().mousePressEvent(事件)

    def mouseReleaseEvent(self, 事件):
        if 事件.button() == Qt.MiddleButton and self._中键按下:
            self._中键按下 = False
            self.unsetCursor()
            事件.accept()
            return
        
        if self._拖拽中 and 事件.button() == Qt.LeftButton:
            场景位置 = self.mapToScene(事件.pos())
            目标端口 = self._查找端口(场景位置)
            
            if (目标端口 and 目标端口 != self._拖拽起点端口 and self._拖拽起点端口.可连接(目标端口)):
                self._完成连线拖拽(目标端口)
            else:
                self._取消连线拖拽()
            self._拖拽中 = False
            事件.accept()
            return
    
        if 事件.button() == Qt.LeftButton and self.dragMode() == QGraphicsView.RubberBandDrag and not self._拖拽中:
            self._选中项目列表 = self.scene().selectedItems()
            for 项目 in self._选中项目列表:
                print(项目)

        if 事件.button() == Qt.LeftButton and self._单击候选按钮 and not self._拖拽中:
            场景位置 = self.mapToScene(事件.pos())
            当前按钮 = self._查找按钮(场景位置)
            
            if 当前按钮 == self._单击候选按钮:
                self._单击计时器.start()
                self._待处理按钮 = self._单击候选按钮
            else:
                self._单击候选按钮 = None
                self._单击候选位置 = None
            
            事件.accept()
            return
        
        super().mouseReleaseEvent(事件)

    def _处理单击(self):
        if not hasattr(self, '_待处理按钮') or not self._待处理按钮:
            return
        按钮 = self._待处理按钮
        父节点 = 按钮.父节点
        if 按钮.方向 == "左":
            self._处理左侧按钮单击(父节点)
        elif 按钮.方向 == "右":
            self._处理右侧按钮单击(父节点)
        self._单击候选按钮 = None
        self._单击候选位置 = None
        self._待处理按钮 = None
    
    def _处理左侧按钮单击(self, 节点项: 节点):
        节点项.添加输入端口()
    
    def _处理右侧按钮单击(self, 节点项: 节点):
        节点项.添加输出端口()

    def mouseMoveEvent(self, 事件):
        if self._拖拽中 and self._拖拽连线:
            场景位置 = self.mapToScene(事件.pos())
            self._拖拽连线.置临时终点(场景位置)
            事件.accept()
            return
        
        if self._中键按下:
            delta = 事件.pos() - self._中键起始位置
            h_val = self._中键起始滚动条值[0] - delta.x()
            v_val = self._中键起始滚动条值[1] - delta.y()
            self.horizontalScrollBar().setValue(h_val)
            self.verticalScrollBar().setValue(v_val)
            事件.accept()
            return
        
        super().mouseMoveEvent(事件)

    def _启动连线拖拽(self, 起点端口: 端口):
        self._拖拽中 = True
        self._拖拽起点端口 = 起点端口
        self._拖拽连线 = 连线(起点端口)
        self.场景.addItem(self._拖拽连线)
        日志.调试(f"开始拖拽连线 from {起点端口.名称}")

    def _完成连线拖拽(self, 终点端口: 端口):
        """完成连线拖拽，复用 _创建有效连线 方法实现自动方向纠正"""
        if not self._拖拽连线 or not self._拖拽起点端口:
            return
        起点端口 = self._拖拽起点端口
        # 使用公共方法创建连线（启用自动方向纠正，启用逻辑验证）
        新连线 = self._创建有效连线(
            原始起点端口=起点端口,
            原始终点端口=终点端口,
            连线ID=None,  # 自动生成新ID
            自动纠正方向=True,
            跳过逻辑验证=False
        )
        # 清理临时拖拽状态（无论成功失败）
        if 新连线:
            # 成功：删除临时连线对象（_创建有效连线已创建新的）
            self.场景.removeItem(self._拖拽连线)
        else:
            # 失败：取消拖拽
            self._取消连线拖拽()        
        self._清理拖拽状态()
    
    def _创建有效连线(self, 原始起点端口: 端口, 原始终点端口: 端口, 连线ID: str = None,
                    自动纠正方向: bool = True, 跳过逻辑验证: bool = False) -> 连线:
        """
        创建有效连线的公共方法，支持自动方向纠正和完整验证
        参数:
            原始起点端口: 用户拖拽或保存的起点端口
            原始终点端口: 用户拖拽或保存的终点端口  
            连线ID: 指定连线ID（导入时使用），None则自动生成
            自动纠正方向: 是否自动交换输入->输出为输出->输入
            跳过逻辑验证: 是否跳过节点类型间的逻辑验证（导入时建议True）
        返回:
            成功返回连线对象，失败返回None"""
        if not 原始起点端口 or not 原始终点端口:
            日志.调试("创建连线失败：端口为空")
            return None
        
        # ========== 方向检测与纠正 ==========
        实际起点端口 = 原始起点端口
        实际终点端口 = 原始终点端口
        方向已交换 = False
        
        # 情况1：方向正确（输出->输入），无需处理
        if 原始起点端口.类型 == "输出" and 原始终点端口.类型 == "输入":
            pass  # 方向正确
        
        # 情况2：方向反了（输入->输出），自动交换
        elif 原始起点端口.类型 == "输入" and 原始终点端口.类型 == "输出":
            if 自动纠正方向:
                日志.调试(f"自动纠正连线方向：{原始起点端口.名称}(输入) <- {原始终点端口.名称}(输出) 交换为 {原始终点端口.名称}(输出) -> {原始起点端口.名称}(输入)")
                实际起点端口 = 原始终点端口
                实际终点端口 = 原始起点端口
                方向已交换 = True
            else:
                日志.警告(f"连线方向错误：{原始起点端口.名称}({原始起点端口.类型}) -> {原始终点端口.名称}({原始终点端口.类型})，期望输出->输入")
                return None
        
        # 情况3/4：同类型端口，无法纠正
        elif 原始起点端口.类型 == 原始终点端口.类型:
            日志.警告(f"无法创建连线：两个端口都是{原始起点端口.类型}类型")
            return None
        
        # 最终验证：确保起点是输出，终点是输入
        if 实际起点端口.类型 != "输出" or 实际终点端口.类型 != "输入":
            日志.错误(f"端口类型异常：起点={实际起点端口.类型}, 终点={实际终点端口.类型}")
            return None
        
        # ========== 基础验证 ==========
        # 不能是同一节点
        实际起点节点 = 实际起点端口.parentItem()
        实际终点节点 = 实际终点端口.parentItem()
        
        if 实际起点节点 == 实际终点节点:
            日志.警告("不能连接同一节点的端口")
            return None
        
        # 输入端口只能有一个连接
        if len(实际终点端口.连线列表) > 0:
            日志.警告(f"输入端口 '{实际终点端口.名称}' 已存在连接")
            return None
        
        # ========== 逻辑验证（可选） ==========
        if not 跳过逻辑验证:
            # 防止特定类型节点的逻辑错误连接
            if 实际起点节点.类型 == "展示" and 实际终点节点.类型 == "开始":
                日志.警告("逻辑错误：不能从展示节点连向开始节点")
                return None
        
        # ========== 创建连线 ==========
        try:
            新连线 = 连线(实际起点端口, 实际终点端口, 连线ID)
            self.场景.addItem(新连线)
            
            # 添加到端口连线列表
            实际起点端口.添加连线(新连线)
            实际终点端口.添加连线(新连线)
            
            # 添加到内部列表
            self._连线.append(新连线)
            
            # 注册到状态管理器
            状态.添加连线(
                新连线.连线ID,
                实际起点节点.节点ID,
                实际起点端口.名称,
                实际终点节点.节点ID,
                实际终点端口.名称
            )
            
            # 发射信号
            self.连线创建信号.emit(
                新连线.连线ID,
                实际起点节点.节点ID,
                实际起点端口.名称,
                实际终点节点.节点ID,
                实际终点端口.名称
            )
            
            方向提示 = "（方向已自动纠正）" if 方向已交换 else ""
            日志.信息(f"创建连线: {实际起点节点.名称}.{实际起点端口.名称} -> {实际终点节点.名称}.{实际终点端口.名称}{方向提示}")
            
            return 新连线
            
        except Exception as e:
            日志.错误(f"创建连线失败: {e}")
            return None

    def _取消连线拖拽(self):
        if self._拖拽连线:
            self.场景.removeItem(self._拖拽连线)
            日志.调试("取消拖拽连线")
        self._清理拖拽状态()

    def _清理拖拽状态(self):
        self._拖拽连线 = None
        self._拖拽起点端口 = None

    def dragEnterEvent(self, 事件):
        if 事件.mimeData().hasText():
            事件.acceptProposedAction()
        else:
            事件.ignore()

    def dragMoveEvent(self, 事件):
        if 事件.mimeData().hasText():
            事件.acceptProposedAction()
        else:
            事件.ignore()

    def dropEvent(self, 事件):
        mime = 事件.mimeData()
        if mime.hasText():
            插件名 = mime.text()
            位置 = self.mapToScene(事件.pos())
            self.创建插件节点(位置, 插件名)
            事件.acceptProposedAction()
        else:
            事件.ignore()
    
    def contextMenuEvent(self, 事件):
        项 = self.itemAt(事件.pos())
        if 项 is None or isinstance(项, 网格):
            菜单 = QMenu(self)
            选中项 = self.scene().selectedItems()
            添加 = 菜单.addMenu("添加节点")
            添加.addAction("开始节点").triggered.connect(lambda: self.创建开始节点(事件.pos()))
            添加.addAction("插件节点").triggered.connect(lambda: self.创建插件节点(事件.pos()))
            添加.addAction("判断节点").triggered.connect(lambda: self.创建判断节点(事件.pos()))
            添加.addAction("展示节点").triggered.connect(lambda: self.创建展示节点(事件.pos()))  # 新增
            菜单.addSeparator()
            菜单.addAction("清空画布").triggered.connect(self.清空画布)
            if self._选中项目列表:
                菜单.addAction("删除").triggered.connect(self.删除选中项)
            菜单.exec(事件.globalPos())
        else:
            super().contextMenuEvent(事件)

    def 删除选中项(self):
        """删除所有选中的节点和连线"""
        if not self._选中项目列表:
            return
        
        总项数 = len(self._选中项目列表)
        _选中列表副本 = list(self._选中项目列表)
        
        # 使用类型名称字符串避免类引用问题
        def 取类型名(对象):
            return type(对象).__name__
        
        # 先收集所有需要删除的项
        待删连线集合 = set()
        待删节点列表 = []
        待删端口列表 = []
        
        for 项 in _选中列表副本:
            类型名字 = 取类型名(项)
            
            if 类型名字 == '连线':
                待删连线集合.add(项)
            elif 类型名字 == '节点':
                待删节点列表.append(项)
                # 收集该节点所有关联的连线
                for 端口对象 in list(项.输入端口.values()) + list(项.输出端口.values()):
                    for 连线对象 in list(端口对象.连线列表):
                        待删连线集合.add(连线对象)
            elif 类型名字 == '端口':
                待删端口列表.append(项)
                for 连线对象 in list(项.连线列表):
                    待删连线集合.add(连线对象)
        
        # 先删除所有连线
        for 单个连线 in list(待删连线集合):
            if 单个连线 in self._选中项目列表:
                self._选中项目列表.remove(单个连线)
            self._删除连线(单个连线)
        
        # 再删除节点
        for 单个节点 in 待删节点列表:
            if 单个节点 in self._选中项目列表:
                self._选中项目列表.remove(单个节点)
            self._删除节点对象(单个节点)
        
        # 最后处理单独的端口
        for 单个端口 in 待删端口列表:
            if 单个端口 in self._选中项目列表:
                self._选中项目列表.remove(单个端口)
            self._删除端口(单个端口)
        
        if len(self._选中项目列表) > 0:
            日志.信息(f"删除选中项 失败, 共 {总项数} 项, 余 {len(self._选中项目列表)} 项")
        else:
            日志.信息(f"删除选中项 完成，共 {总项数} 项")

    def _删除连线(self, 连线项: 连线):
        """删除单条连线，彻底清理所有引用"""
        连线ID = getattr(连线项, '连线ID', None)
        # 1. 从两端端口安全移除引用（即使端口已被删除）
        try:
            if hasattr(连线项, '移除连线自己'):
                连线项.移除连线自己()
        except Exception as e:
            日志.调试(f"移除连线引用时出错: {e}")
        # 2. 手动确保从所有端口的连线列表中移除（双重保险）
        try:
            if 连线项.起点端口 and hasattr(连线项.起点端口, '连线列表'):
                if 连线项 in 连线项.起点端口.连线列表:
                    连线项.起点端口.连线列表.remove(连线项)
        except Exception as e:
            日志.调试(f"从起点端口移除失败: {e}")
        try:
            if 连线项.终点端口 and hasattr(连线项.终点端口, '连线列表'):
                if 连线项 in 连线项.终点端口.连线列表:
                    连线项.终点端口.连线列表.remove(连线项)
        except Exception as e:
            日志.调试(f"从终点端口移除失败: {e}")
        # 3. 从状态管理器移除
        if 连线ID:
            状态.删除连线(连线ID)
            日志.调试(f"从状态管理器删除连线: {连线ID}")
        # 4. 从场景移除
        if 连线项.scene():
            self.场景.removeItem(连线项)
            日志.调试(f"从场景移除连线: {连线ID}")
        # 5. 从内部列表移除
        if 连线项 in self._连线:
            self._连线.remove(连线项)
            日志.调试(f"从内部列表移除连线: {连线ID}")
        # 6. 清空引用帮助垃圾回收
        连线项.起点端口 = None
        连线项.终点端口 = None
        日志.调试(f"删除连线完成: {连线ID}")

    def _删除节点对象(self, 节点项: 节点):
        """直接删除节点对象"""
        节点ID = 节点项.节点ID
        # 先清理所有端口的连线列表，防止残留
        try:
            for 端口名称, 端口对象 in list(节点项.输入端口.items()) + list(节点项.输出端口.items()):
                # 复制列表避免修改时迭代
                for 连线 in list(端口对象.连线列表):
                    if 连线 in self._连线:
                        self._删除连线(连线)
                # 清空端口自己的连线列表
                端口对象.连线列表.clear()
        except Exception as e:
            日志.调试(f"清理端口连线列表时出错: {e}")
        # 从内部字典移除
        if 节点ID in self._节点:
            del self._节点[节点ID]
        # 从状态管理器注销
        状态._节点对象.pop(节点ID, None)
        状态._节点数据.pop(节点ID, None)  # 清理缓存数据
        状态._节点状态.pop(节点ID, None)  # 清理状态
        # 从场景移除节点
        if 节点项.scene():
            self.场景.removeItem(节点项)
        日志.信息(f"删除节点: {节点ID}")

    def _删除端口(self, 端口项: 端口):
        """删除端口及其所有连线"""
        if not 端口项:
            return
        父节点项 = 端口项.parentItem()
        # 先删除所有关联连线
        if hasattr(端口项, '连线列表'):
            for 连线项 in list(端口项.连线列表):
                self._删除连线(连线项)
            端口项.连线列表.clear()
        # 从父节点的端口字典中移除
        if 父节点项:
            if 端口项.名称 in 父节点项.输入端口:
                del 父节点项.输入端口[端口项.名称]
            if 端口项.名称 in 父节点项.输出端口:
                del 父节点项.输出端口[端口项.名称]
        # 从场景移除
        if 端口项.scene():
            self.场景.removeItem(端口项)

    def 删除节点(self, 节点ID: str):
        """通过信号调用的节点删除方法"""
        if 节点ID not in self._节点:
            return
        节点项 = self._节点[节点ID]
        self._删除节点对象(节点项)

    def 清空画布(self):
        for 连线项 in self._连线[:]:
            self._删除连线(连线项)
        for 节点ID in list(self._节点.keys()):
            self.删除节点(节点ID)
        状态._节点对象.clear()  # 清空状态管理器
        状态._连线.clear()
        日志.信息("清空画布完成")

    def 创建开始节点(self, 位置) -> 开始节点:
        节点ID = f"开始_{uuid.uuid4().hex[:8]}"
        节点项 = 开始节点(节点ID)
        场景位置 = self.mapToScene(位置) if isinstance(位置, QPoint) else 位置
        节点项.setPos(场景位置 - QPointF(80, 30))
        self.场景.addItem(节点项)
        self._节点[节点ID] = 节点项
        # 注册到状态管理器（关键！）
        状态.注册节点(节点ID, 节点项)
        self.节点创建信号.emit(节点ID, 节点项)
        信号.节点创建.emit(节点ID, 节点项)
        日志.信息(f"创建开始节点: {节点ID}")
        return 节点项
    
    def 创建插件节点(self, 位置, 插件名: str = "测试") -> 插件节点:
        节点ID = f"插件_{uuid.uuid4().hex[:8]}"
        节点项 = 插件节点(节点ID, 插件名)
        场景位置 = self.mapToScene(位置) if isinstance(位置, QPoint) else 位置
        节点项.setPos(场景位置 - QPointF(90, 40))
        self.场景.addItem(节点项)
        self._节点[节点ID] = 节点项
        状态.注册节点(节点ID, 节点项)
        self.节点创建信号.emit(节点ID, 节点项)
        信号.节点创建.emit(节点ID, 节点项)
        日志.信息(f"创建插件节点: {节点ID}")
        return 节点项
    
    def 创建判断节点(self, 位置) -> 判断节点:
        节点ID = f"判断_{uuid.uuid4().hex[:8]}"
        节点项 = 判断节点(节点ID)
        场景位置 = self.mapToScene(位置) if isinstance(位置, QPoint) else 位置
        节点项.setPos(场景位置 - QPointF(90, 40))
        self.场景.addItem(节点项)
        self._节点[节点ID] = 节点项
        状态.注册节点(节点ID, 节点项)  # 注册到状态管理器
        self.节点创建信号.emit(节点ID, 节点项)
        信号.节点创建.emit(节点ID, 节点项)
        日志.信息(f"创建判断节点: {节点ID}")
        return 节点项

    def 创建展示节点(self, 位置) -> 展示节点:
        节点ID = f"展示_{uuid.uuid4().hex[:8]}"
        节点项 = 展示节点(节点ID)
        场景位置 = self.mapToScene(位置) if isinstance(位置, QPoint) else 位置
        节点项.setPos(场景位置 - QPointF(80, 30))
        self.场景.addItem(节点项)
        self._节点[节点ID] = 节点项
        状态.注册节点(节点ID, 节点项)
        self.节点创建信号.emit(节点ID, 节点项)
        信号.节点创建.emit(节点ID, 节点项)
        日志.信息(f"创建展示节点: {节点ID}")
        return 节点项

    def 导出字典(self) -> dict:
        """
        将所有节点和连线导出为字典，用于保存到JSON文件
        包含节点位置、端口配置、连线关系以及各类型节点的特定数据"""
        数据 = {
            "版本": "1.0.0",
            "节点": [],
            "连线": []
        }
        
        # 遍历所有节点
        for 节点ID, 节点项 in self._节点.items():
            节点数据 = {
                "id": 节点ID,
                "类型": 节点项.类型,
                "名称": 节点项.名称,
                "位置": {"x": 节点项.pos().x(), "y": 节点项.pos().y()},
                "输入端口": [{"名称": p.名称} for p in 节点项.输入端口.values()],
                "输出端口": [{"名称": p.名称} for p in 节点项.输出端口.values()]
            }
            
            # 根据节点类型添加特定数据
            if 节点项.类型 == "开始":
                节点数据["输出数据"] = 节点项.输出数据
                
            elif 节点项.类型 == "插件":
                节点数据["插件名"] = 节点项.插件名
                
            elif 节点项.类型 == "判断":
                节点数据["判断条件"] = 节点项.判断条件
                
            elif 节点项.类型 == "展示":
                # 保存历史数据（限制数量防止文件过大）
                历史数据列表 = []
                for 数据项 in 节点项.历史数据[-100:]:  # 只保存最近100条
                    历史数据列表.append({
                        "类型": 数据项.get("类型", "接收"),
                        "内容": 数据项.get("内容", ""),
                        "时间": 数据项.get("时间", ""),
                        "原始输入": 数据项.get("原始输入", ""),
                        "使用模板": 数据项.get("使用模板")
                    })
                节点数据["历史数据"] = 历史数据列表
                
                # 保存模板数据
                节点数据["模板数据"] = 节点项.模板数据.copy() if hasattr(节点项, '模板数据') else []
            
            数据["节点"].append(节点数据)
        
        # 遍历所有连线
        for 连线项 in self._连线:
            if 连线项.起点端口 and 连线项.终点端口:
                起点节点 = 连线项.起点端口.parentItem()
        