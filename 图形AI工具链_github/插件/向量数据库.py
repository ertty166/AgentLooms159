"""
千问记忆者插件 - 基于Qwen模型的结构化记忆存储与检索系统
支持标准Function Calling与原有格式双模式
history数据结构:[(用户说,AI回),(用户说,AI回)]
"""
# 工具关键词配置
存入关键词 = "[存入]"
取出关键词 = "[取出]"
聚类关键词 = "[聚类]"
数据标首 = "[数据]"
数据标尾 = "[数据结尾]"
删除关键词 = "[删除]"
# 外部读取的配置
__名称__ = "记忆者"
__版本__ = "2.1.0"
__作者__ = "作者"
__分类__ = "AI/记忆"
__分片策略类型__ = "否"
__关键词__ = "[记忆者]"
__简介__ = f"""[开始]->{__名称__}的信息,
名称:“{__名称__}”,
版本:“{__版本__}”,作者:“{__作者__}”,
分类:“{__分类__}”,呼叫关键词:“{__关键词__}”
介绍:[开始]->“你好,我是一个记忆库,名字叫{__名称__},在你说的话中带上'{__关键词__}'才能调用我的功能,
1.存入记忆:{__关键词__}[存入]“这里是存入内容”;直接拼成一串,不需要多余润色或结构,但注意{__关键词__}[存入]是紧挨着的,且顺序不能变
2.提取记忆:{__关键词__}[取出]“关键短句|长句”;基于向量进行匹配查询,例如查(道德的定义)->返还(道德的定义:xxx,xxx)
3.聚类记忆:{__关键词__}[聚类],我会整理全部的记忆,之后你可以尝试再次查询
4.删除记忆:"{__关键词__}[删除]“这里是你描述的删除内容”",
5.一个反引号块只能封装一个你要存入的内容,如果你想一次存入多个不同内容,你需要多次用反引号块包裹命令”
6.执行任务时:开始规划时调用我查询曾经的相关保存,任务结束后调用我保存这一轮任务的总结(起因->大概经过->结论)
7.只有在你确保要存入一条常规文本结论时才能使用我保存,并且我保存的内容是经过辩证验证的<-[结束]"""
# 这是一个标准的 Python 字典，可以直接赋值给变量
# 注意：Ollama 的 tools 参数通常需要一个列表，所以我们将这个字典放在列表中
__工具介绍__ = [
    {
        "type": "function",
        "function": {
            "name": "[记忆者]",  # 工具名称，模型调用时会用到
            "description": "长期记忆数据库的操作接口，支持存入、取出和删除记忆数据",  # 告诉模型这个工具是干嘛的
            "parameters": {  # 参数定义主体
                "type": "object",  # 固定格式，表示参数是一个对象
                "properties": {  # 具体的参数列表
                    "操作": {  # 对应你要求的“操作”字段
                        "type": "string",  # 类型是字符串
                        "description": "必须从以下三个选项中选择一个：[存入]、[取出]、[删除]",  # 明确告诉模型只能选这三个
                        "enum": ["[存入]", "[取出]", "[删除]"]  # 【关键】枚举限制，强制模型只能输出这三个值之一
                    },
                    "文本": {  # 对应你要求的“文本”字段
                        "type": "string",  # 类型是字符串
                        "description": "具体的数据内容。如果是[存入]则填入完整文本;如果是[取出]或[删除]则填入用于检索的关键句(长短不限)"  # 解释文本在不同操作下的用途
                    }
                },
                "required": ["操作", "文本"]  # 指定这两个字段是必填的，防止模型漏传
            }
        }
    }
]
词嵌入 = None

独立运行调试 = False
直接文本模式 = True
"""新版本:
    [取出]故障处理方法
    [删除]故障处理流程
[记忆者][存入][数据]{"内容":["我是数据A","我是数据B","我是数据C"]}[数据结尾]
    [记忆者][存入][数据]{"内容":["我是数据A"]}[数据结尾]
    [记忆者][删除]数据A
    [记忆者][取出][数据]{"关键":["内容A"]}[数据结尾]
    [记忆者][存入][数据]{"内容":[" transformer著名的是多头注意力系统,他将权重切分,并且训练每一个切分的块来达到更好的精度"]}[数据结尾]
    [记忆者][删除]transformer创始人开的那场发布会,他说他认为自己的东西阻碍了AI的发展,他说这些东西起源于一次下午茶,一些黑板上的乱涂乱画,他希望我们探索
    [记忆者][聚类]
    [记忆者][取出][数据]{"关键":["transformer创始人发布会"]}[数据结尾]
    [记忆者]帮我记录下这些:“transformer创始人说他认为transformer阻碍了AI的发展,他认为我们应该探索更多的,抛除掉强化学习”
   [记忆者]我想存入一个定义:“感情是联系文明个体的纽带，道德是维系感情防止有照顾思想的个体因性格问题受到严重损害而消失的关键因素,二者共同构成持续文明生命力以及关爱文明内个体的关键逻辑”
   [记忆者]我想提取一些数据:和计算机有关
   [记忆者]我想提取数据:计算机,内容A
   [记忆者]我想提取数据:transformer创始人
   [记忆者][存入]最近才发现,除了transformer架构之外还有另一种神经元的架构,叫类脑神经脉冲模型,每一个神经元达到激活阈值之后才会激活,并且生成时并不会看到全部的上文,而是将全部的上文综合为一个内容,然后根据这一个内容向下生成,所以它的生成算力需求程度是线性增长
   [记忆者][存入]地球是个椭球体
   [记忆者][存入]胶棒用来粘接物体,不同种类的胶棒他们粘接的基本原理也有所不同,502是一种强力胶他在粘接效应上就非常的强大,它凝固之后是坚硬的
   [记忆者][存入]今天去菜市场买菜看起来普遍的蔬菜价格都在十块钱一斤以下,甚至有一些两三块钱就能买到一斤
   [记忆者][存入]人类的定义:人类是动物,动物中的高级动物,首先是因为人类有大脑,其次是因为人类有提出->验证->总结->保存的闭环逻辑
   [记忆者][存入]道德的定义:道德是文明前进的必须因素,如同如同科技评估一个文明当前发展的高度一样,道德用来评估他未来的发展潜力,没有未来的文明毫无意义,它的本质是一定程度上自我约束,不将情绪化和一些自身足以解决的内部问题带给他人,理论上来讲你所掌握的资源和权力越多你的道德要求就要越严格,因为这意味着一旦你失去了道德你就可能会变成一个罪人,因为你足以有能力去做一个罪人,并且强大从来都是靠弱小衬托,在这宇宙里,没有谁是绝对的强者,所以当你成为强者的那一刻,你就欠这世界上所有弱者一份东西,你可以不还你可以不屑,但你必须明白
   [记忆者][取出]道德的定义
   """
from modelscope import AutoTokenizer, AutoModelForCausalLM, AutoModel
import torch
import random
import _tools as tools
import json
import re
import sys
import threading
import os
import time
import jieba
import base64
import traceback
from typing import List, Dict, Any, Optional, Union
# ===================== 数据库配置 ====================
import sqlite3
import pickle
import math
import numpy as np
from datetime import datetime
from _插件公用 import 插件公用, 上下文管理器
Pub = 插件公用(__名称__,独立运行调试,__关键词__,__版本__,__作者__)

# ===================== 记忆者配置中心（全部中文命名） =====================
class 记忆者配置中心:
    # ---------- 基础参数 ----------
    每级数据量 = 1000              # 聚类分层基数，每级多少条数据
    向量维度 = 4096                # 向量截断维度
    张量精度 = "float16"           # 计算精度：float16 / float32
    张量存储设备 = "cpu"           # 张量强制存储设备
    判断短长词数量阈值 = 8             # 用于判断查询键是短句还是长句(按照jieba分词最长匹配句子中的词数量),继而决定是否添加前缀

    # ---------- 有效值系统 ----------
    初始有效值 = 1.0               # 新数据默认有效值
    冻结阈值 = 0.0                 # 【核心】<=此值冻结，>此值有效
    冻结衰减值 = 0.01              # 后台衰减每次扣除量
    衰减间隔秒 = 10              # 后台衰减周期（30分钟）
    衰减提交批次 = 100             # 衰减处理每N条提交一次
    删除阈值 = -28

    # ---------- 相似度与惩罚奖励 ----------
    除零保护值 = 1e-8              # 余弦相似度防除零极小值
    相似度惩罚阈值 = 0.6            # 惩罚/奖励分界相似度
    相似度奖励阈值 = 0.6            # 高奖励门槛（可与惩罚阈值相同或不同）
    低相似保底奖励 = 0.01           # 低匹配时的保底奖励基数
    硬惩罚系数 = 5.0               # K_HARD：错误匹配惩罚强度
    软惩罚系数 = 3.0               # K_SOFT：正确匹配奖励/软惩罚强度
    Sigmoid缩放因子 = 0.1           # SIGMOID_SCALE：边界软化程度
    
    # ---------- 束搜索参数 ----------
    初始束宽 = 5                   # 第一层保留候选数
    束宽最小值 = 1                  # 相似度差距大时保留数
    束宽最大值 = 10                 # 相似度差距小时保留数（不超过此值）
    束宽默认值 = 3                  # 中等差距时保留数
    束宽差距上限 = 0.3              # 差距>此值用最小束宽
    束宽差距下限 = 0.1              # 差距<此值用最大束宽
    束搜索方差惩罚系数 = 0.5         # BEAM_ALPHA：路径均衡得分方差权重
    
    # ---------- 聚类参数 ----------
    聚类随机种子 = 42               # K-means随机种子
    聚类最大迭代 = 300              # K-means最大迭代次数
    异常相似度阈值 = 0.3            # 数据与所有簇中心最高相似度<此值视为异常
    聚类前清理阈值 = 0.0            # 聚类前删除有效值<=此值的数据（应与冻结阈值一致）
    异常标记值 = "__OUTLIER__"      # 异常数据的UP_LEVEL标记值
    
    # ---------- 复苏参数 ----------
    复苏相似度比例 = 0.8            # 复苏门槛 = 相似度奖励阈值 * 此比例
    复苏查询束宽 = 1                # 复苏查询只取Top1簇，减少计算
    
    # ---------- KEY生成参数 ----------
    KEY窗口大小 = 1000              # 插空生成KEY的窗口大小
    KEY随机范围 = 99999999999999999999  # 随机KEY最大值
    
    # ---------- 其他 ----------
    默认标签 = "_无_"               # 无标签时的默认值
    最大尝试轮次 = 10

    # ---------- 激励函数（删除+增加共用）----------
    激励峰值 = 2              # 相似度=1时的激励强度（删除扣多少/增加加多少）
    激励陡度 = 6           # 【核心】控制"悬崖"陡峭程度，越大越陡
    激励中心 = 0.65              # 悬崖中心位置，>此值重激励，<此值轻激励
    激励保底 = 0.001             # 最低激励值（避免完全为0）
    最大查询数量 = 9

    匹配成功总值 = 10 # 
    匹配成功阈值 = 0.3 # 控制返回数据与查询数据的相似度,超过此相似度的才会被返回
    
# ===================== 词嵌入向量映射类 =====================
class 词嵌入向量映射:
    def __init__(self, 模型路径:str=None):
        self.model_path = 模型路径 if 模型路径 else tools.search_folder_in("图形AI工具链_github","bge-large-zh-v1___5",build=False)
        self.分词器 = AutoTokenizer.from_pretrained(self.model_path,use_fast=False)
        self.向量模型 = AutoModel.from_pretrained(self.model_path).eval()
    
    def 获取比对向量(self,查询否:bool, 文本:str):
        """查询True,拼接“为这个句子生成表示向量：”查询前缀"""
        if 查询否:
            词数量 = len(jieba.lcut(文本, cut_all=False))
            if 词数量 <= 记忆者配置中心.判断短长词数量阈值:
                文本 = f"为这个句子生成表示向量：{文本}"
        编码后输入 = self.分词器(
            [文本],
            padding=True,
            truncation=True,
            return_tensors='pt',
            max_length = 1024
        )
        with torch.no_grad():
            模型输出 = self.向量模型(**编码后输入)
            句子向量 = 模型输出[0][:, 0]
        句子向量 = torch.nn.functional.normalize(句子向量, p=2, dim=1)
        # ===================== 使用【你的超强余弦函数】计算最终分数 =====================
        #向量 = 句子向量[0].numpy()  # 索引零的向量
        向量 = 句子向量[0]
        return 向量

# ===================== 知识库类（全部使用配置中心参数） =====================
class 知识库():
    def __init__(self, 数据库路径=None):
        self.连接 = sqlite3.connect(数据库路径)
        self.游标 = self.连接.cursor()
        self.数据库路径 = 数据库路径

        # 【修改】所有参数从配置中心读取
        self.每级数据量 = 记忆者配置中心.每级数据量
        self.合法表名正则 = re.compile(r"^(memory|index_level\d+|meta_info)$")
        
        # 性能优化
        self.连接.execute("PRAGMA cache_size = -102400")
        self.连接.execute("PRAGMA journal_mode = WAL")
        
        # 初始化表
        self.创建基础表()
        self.创建元信息表()
        self.层级数 = self.计算当前层级数()
        self.索引缓存 = {}
        self.加载索引缓存()
        self._数据库锁 = threading.RLock()
        # 【修改】从配置中心读取
        self.向量维度 = 记忆者配置中心.向量维度
        self.张量精度 = getattr(torch, 记忆者配置中心.张量精度)
        self.相似度方法 = self.余弦相似度向量化
        
        # 【修改】后台衰减参数从配置中心
        self.冻结衰减值 = 记忆者配置中心.冻结衰减值
        self.衰减间隔秒 = 记忆者配置中心.衰减间隔秒
        self.衰减线程 = None
        self.衰减运行中 = False
        self.启动衰减线程()

    # ------------------------------ 强制刷盘 ------------------------------
    def 强制刷盘(self):
        try:
            self.连接.commit()
            self.连接.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.连接.execute("PRAGMA sync")
            return True
        except Exception as e:
            self.连接.rollback()
            return False

    def _激励函数(self, 相似度: float) -> float:
        """
        【核心】共用激励函数：输入相似度，输出激励强度
        
        曲线特征：
        - 相似度→1.0，输出→激励峰值（剧烈）
        - 相似度略降（如0.9→0.7），输出悬崖式暴跌
        - 相似度<0.5，输出≈激励保底（几乎为0）
        
        删除和增加共用此函数，只是：
        - 删除：扣除 = 激励强度
        - 增加：增量 = 激励强度
        """
        
        峰值 = 记忆者配置中心.激励峰值
        陡度 = 记忆者配置中心.激励陡度
        中心 = 记忆者配置中心.激励中心
        保底 = 记忆者配置中心.激励保底
        
        # 边界裁剪
        相似度 = max(0.0, min(1.0, 相似度))
        
        # 翻转Sigmoid：相似度>中心时快速上升，<中心时快速饱和
        sigmoid输入 = 陡度 * (相似度 - 中心)
        悬崖因子 = 1 / (1 + math.exp(-sigmoid输入))
        
        # 指数压制低相似度区域
        if 相似度 < 中心:
            压制指数 = 陡度 * 0.2  # 压制强度与陡度联动
            压制因子 = math.exp(压制指数 * (相似度 - 中心))
            激励 = 峰值 * 悬崖因子 * 压制因子
        else:
            激励 = 峰值 * 悬崖因子
        
        # 保底
        return max(保底, 激励)

    def 计算扣除有效值(self, 相似度: float) -> float:
        """删除激励：越像扣越多（删对了，轻罚），越不像扣越少（删错了，不罚）"""
        激励 = self._激励函数(相似度)
        return self.量化有效值(激励)

    def 计算查询奖励(self, 相似度: float) -> float:
        """增加激励：越像加越多（查对了，重奖），越不像加越少（查错了，不奖）"""
        激励 = self._激励函数(相似度)
        return self.量化有效值(激励)

    # ------------------------------ 后台衰减线程 ------------------------------
    def 启动衰减线程(self):
        if self.衰减线程 is not None and self.衰减线程.is_alive():
            return
        self.衰减运行中 = True
        self.衰减线程 = threading.Thread(target=self._衰减循环, daemon=True)
        self.衰减线程.start()

    def _衰减循环(self):
        while self.衰减运行中:
            self._执行冻结衰减()
            for _ in range(self.衰减间隔秒):
                if not self.衰减运行中:
                    break
                time.sleep(1)

    def 停止衰减线程(self):
        self.衰减运行中 = False
        if self.衰减线程:
            self.衰减线程.join(timeout=5)

    def _执行冻结衰减(self): # 20260429
        衰减计数 = 0
        删除计数 = 0
        提交批次 = 记忆者配置中心.衰减提交批次
        
        # 【关键】在线程内创建独立连接，而不是用 self.连接
        线程连接 = sqlite3.connect(self.数据库路径)
        线程连接.execute("PRAGMA cache_size = -102400")
        线程连接.execute("PRAGMA journal_mode = WAL")
        线程游标 = 线程连接.cursor()
        
        try:
            with self._数据库锁:
                for 行 in self._冻结数据生成器(线程游标):
                    KEY, 当前有效值 = 行
                    新值 = self.量化有效值(当前有效值 - self.冻结衰减值)
                    
                    if 新值 <= 记忆者配置中心.删除阈值:
                        线程游标.execute("DELETE FROM memory WHERE KEY = ?", (KEY,))
                        删除计数 += 1
                    else:
                        线程游标.execute("""
                        UPDATE memory SET VALIDITY = ? WHERE KEY = ?
                        """, (新值, KEY))
                        衰减计数 += 1
                    
                    if (衰减计数 + 删除计数) % 提交批次 == 0:
                        线程连接.commit()
                
                线程连接.commit()
                
                # 【关键】强制刷盘也用线程自己的连接
                线程连接.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                线程连接.execute("PRAGMA sync")
                
        finally:
            线程连接.close()

    def _冻结数据生成器(self, 外部游标=None):
        页大小 = 记忆者配置中心.KEY窗口大小  # 【修改】复用窗口大小作为分页大小
        偏移量 = 0
        if not 外部游标:
            return None
        线程游标 = 外部游标
        while True:
            线程游标.execute("""
            SELECT KEY, VALIDITY FROM memory 
            WHERE FROZEN = 1 
            ORDER BY KEY 
            LIMIT ? OFFSET ?
            """, (页大小, 偏移量))
            
            行列表 = 线程游标.fetchall()
            if not 行列表:
                break
            
            for 行 in 行列表:
                yield 行
            
            偏移量 += 页大小
            if len(行列表) < 页大小:
                break

    # ------------------------------ 基础表操作 ------------------------------
    def 校验表名(self, 表名):
        if self.合法表名正则.match(表名):
            return 表名
        raise ValueError(f"非法表名：{表名}")

    def 创建基础表(self):
        初始有效值 = 记忆者配置中心.初始有效值  # 【修改】
        
        self.游标.execute(f"""
        CREATE TABLE IF NOT EXISTS memory (
            KEY TEXT PRIMARY KEY,
            UP_LEVEL TEXT,
            DATA_CH TEXT NOT NULL,
            TIME DATE,
            MY_TENSOR BLOB,
            LABEL TEXT,
            VALIDITY REAL DEFAULT {初始有效值},
            FROZEN INTEGER DEFAULT 0
        )
        """)
        self.游标.execute("CREATE INDEX IF NOT EXISTS idx_memory_uplevel ON memory(UP_LEVEL)")
        self.游标.execute("CREATE INDEX IF NOT EXISTS idx_memory_frozen ON memory(FROZEN)")
        self.游标.execute("CREATE INDEX IF NOT EXISTS idx_memory_frozen_key ON memory(FROZEN, KEY)")
        self.连接.commit()
        
        # 兼容旧表
        try:
            self.游标.execute("SELECT VALIDITY FROM memory LIMIT 1")
        except sqlite3.OperationalError:
            self.游标.execute(f"ALTER TABLE memory ADD COLUMN VALIDITY REAL DEFAULT {初始有效值}")
            self.连接.commit()
        
        try:
            self.游标.execute("SELECT FROZEN FROM memory LIMIT 1")
        except sqlite3.OperationalError:
            self.游标.execute("ALTER TABLE memory ADD COLUMN FROZEN INTEGER DEFAULT 0")
            self.连接.commit()

    def 创建元信息表(self):
        self.游标.execute("""
        CREATE TABLE IF NOT EXISTS meta_info (
            CLUSTER_STATE TEXT DEFAULT 'unclustered',
            MAX_LEVEL INTEGER DEFAULT 0,
            LAST_CLUSTER_TIME DATE
        )
        """)
        self.游标.execute("SELECT COUNT(*) FROM meta_info")
        if self.游标.fetchone()[0] == 0:
            self.游标.execute("INSERT INTO meta_info VALUES ('unclustered', 0, NULL)")
            self.连接.commit()
        
    def 创建索引表(self, 层级):
        原始表名 = f"index_level{层级}"
        合法表名 = self.校验表名(原始表名)
        self.游标.execute(f"""
        CREATE TABLE IF NOT EXISTS {合法表名} (
            INDEX_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            UP_LEVEL TEXT,
            MY_NAME TEXT UNIQUE NOT NULL,
            MY_TENSOR BLOB,
            TIME DATE
        )
        """)
        self.游标.execute(f"CREATE INDEX IF NOT EXISTS idx_{合法表名}_uplevel ON {合法表名}(UP_LEVEL)")
        self.连接.commit()

    # ------------------------------ 层级计算 ------------------------------
    def 计算总数据量(self):
        self.游标.execute("SELECT COUNT(*) FROM memory")
        return self.游标.fetchone()[0]

    def 计算当前层级数(self):
        总数据量 = self.计算总数据量()
        if 总数据量 < self.每级数据量:
            return 0
        return math.floor(math.log(总数据量, self.每级数据量))

    def 张量序列化(self, 张量):
        return pickle.dumps(张量)

    def 张量反序列化(self, 二进制数据):
        try:
            return pickle.loads(二进制数据)
        except:
            return None

    # ------------------------------ 相似度计算 ------------------------------
    def 余弦相似度(self, 向量1, 向量2):
        点积 = sum(a*b for a, b in zip(向量1, 向量2))
        模长1 = sum(a*a for a in 向量1)**0.5
        模长2 = sum(b*b for b in 向量2)**0.5
        return 点积/(模长1*模长2) if (模长1*模长2) != 0 else 0

    '''
    def 余弦相似度向量化(self, 向量1, 向量2):
        保护值 = 记忆者配置中心.除零保护值  # 【修改】
        
        向量1 = np.array(向量1, dtype=np.float32)
        向量2 = np.array(向量2, dtype=np.float32)
        
        if len(向量1.shape) > 1:
            向量1 = 向量1.flatten()[:self.向量维度]
        if len(向量2.shape) > 1:
            向量2 = 向量2.flatten()[:self.向量维度]
        
        向量1 = np.pad(向量1, (0, self.向量维度 - len(向量1)), 'constant')[:self.向量维度]
        向量2 = np.pad(向量2, (0, self.向量维度 - len(向量2)), 'constant')[:self.向量维度]
        
        点积 = np.dot(向量1, 向量2)
        模长1 = np.linalg.norm(向量1)
        模长2 = np.linalg.norm(向量2)
        return 点积/(模长1*模长2 + 保护值)  # 【修改】'''

    def 余弦相似度向量化(self, 向量1, 向量2):
        """
        【修复版】统一使用 4096 维，与模型输出维度一致。
        去掉不必要的 pad，只在长度不足时补零，且上限为 4096。
        """
        保护值 = 记忆者配置中心.除零保护值
        
        向量1 = np.array(向量1, dtype=np.float32)
        向量2 = np.array(向量2, dtype=np.float32)
        
        # 处理多维输入（如聚类中心可能是 [n_clusters, hidden_dim]）
        if len(向量1.shape) > 1:
            向量1 = 向量1.flatten()[:self.向量维度]
        if len(向量2.shape) > 1:
            向量2 = 向量2.flatten()[:self.向量维度]
        
        # 【修复】只在实际长度不足时补零，不再强制扩展到 8192
        # 如果向量已经是 4096 维（正常情况），这里不做任何操作
        if len(向量1) < self.向量维度:
            向量1 = np.pad(向量1, (0, self.向量维度 - len(向量1)), 'constant')[:self.向量维度]
        else:
            向量1 = 向量1[:self.向量维度]
            
        if len(向量2) < self.向量维度:
            向量2 = np.pad(向量2, (0, self.向量维度 - len(向量2)), 'constant')[:self.向量维度]
        else:
            向量2 = 向量2[:self.向量维度]
        
        点积 = np.dot(向量1, 向量2)
        模长1 = np.linalg.norm(向量1)
        模长2 = np.linalg.norm(向量2)
        
        return 点积 / (模长1 * 模长2 + 保护值)


    def 量化有效值(self, v: float) -> float:
        整数部分 = int(v)
        小数部分 = (v - 整数部分)
        量化小数 = round(小数部分 * 256) / 256.0
        return 整数部分 + 量化小数

    # ------------------------------ 细粒度相似度匹配 ------------------------------
    def _细粒度相似度匹配(self, 查询文本, 查询张量, 目标数据列表, 返回条数) -> list: 
        """返回:[(内容, 标签, 时间), ...]"""
        if not 目标数据列表:
            return []
        
        目标向量列表 = [self.张量反序列化(行[3]).cpu().detach().numpy() for 行 in 目标数据列表]
        
        if isinstance(查询张量, torch.Tensor):
            查询原始向量 = 查询张量.cpu().detach().numpy()
        else:
            查询原始向量 = np.array(查询张量)
        
        if len(查询原始向量.shape) == 2:
            查询向量 = np.mean(查询原始向量, axis=0)
        else:
            查询向量 = 查询原始向量.flatten()[:self.向量维度]
        
        保护值 = 记忆者配置中心.除零保护值  # 【修改】
        查询向量 = 查询向量 / (np.linalg.norm(查询向量) + 保护值)
        
        相似度数据列表 = []
        当前相似度 = 0
        for 行数据, 目标向量 in zip(目标数据列表, 目标向量列表):
            if len(目标向量.shape) == 2:
                目标聚类向量 = np.mean(目标向量, axis=0)
            else:
                目标聚类向量 = 目标向量.flatten()[:self.向量维度]
            目标聚类向量 = 目标聚类向量 / (np.linalg.norm(目标聚类向量) + 保护值)
            
            相似度 = self.余弦相似度向量化(查询向量, 目标聚类向量)
            if 当前相似度 <= 记忆者配置中心.匹配成功总值 and len(相似度数据列表) <= 记忆者配置中心.最大查询数量:
                相似度数据列表.append((-相似度, 行数据))
                当前相似度 += 相似度
        if 相似度数据列表:
            相似度数据列表.sort(key=lambda x: x[0])
            排序后数据 = [行数据 for (_, 行数据) in 相似度数据列表]
            最终结果 = [(行[1], 行[2], 行[4]) for 行 in 排序后数据[:返回条数]]
        else:
            最终结果 = []
        return 最终结果

    def _细粒度相似度匹配带分数(self, 查询文本, 查询张量, 目标数据列表) -> list:
        """返回[(内容, 标签, 时间, **相似度**, **KEY**), ...]"""
        if not 目标数据列表:
            return []
        
        目标向量列表 = []
        for 行 in 目标数据列表:
            张量 = self.张量反序列化(行[3])
            if 张量 is None:
                continue
            if isinstance(张量, torch.Tensor):
                张量 = 张量.cpu().detach().numpy()
            目标向量列表.append(张量)
        
        if isinstance(查询张量, torch.Tensor):
            查询原始向量 = 查询张量.cpu().detach().numpy()
        else:
            查询原始向量 = np.array(查询张量)
        
        if len(查询原始向量.shape) == 2:
            查询向量 = np.mean(查询原始向量, axis=0)
        else:
            查询向量 = 查询原始向量.flatten()[:self.向量维度]
        
        保护值 = 记忆者配置中心.除零保护值  # 【修改】
        查询向量 = 查询向量 / (np.linalg.norm(查询向量) + 保护值)
        
        结果列表 = []
        for 行数据, 目标向量 in zip(目标数据列表, 目标向量列表):
            if len(目标向量.shape) == 2:
                目标聚类向量 = np.mean(目标向量, axis=0)
            else:
                目标聚类向量 = 目标向量.flatten()[:self.向量维度]
            目标聚类向量 = 目标聚类向量 / (np.linalg.norm(目标聚类向量) + 保护值)
            
            相似度 = self.余弦相似度向量化(查询向量, 目标聚类向量)
            结果列表.append((行数据[1], 行数据[2], 行数据[4], 相似度, 行数据[0]))
        
        结果列表.sort(key=lambda x: x[3], reverse=True)
        return 结果列表

    # ------------------------------ 数据存入 ------------------------------
    def 数据存入(self, 文本, 标签=None, 数据张量=None):
        if 数据张量 is None:
            return False, "请传入张量"
        if isinstance(文本, list):
            文本列表 = 文本
            标签列表 = 标签 if isinstance(标签, list) else [None] * len(文本)
            张量列表 = 数据张量 if isinstance(数据张量, list) else [数据张量]
            return self.批量数据存入(文本列表, 标签列表, 张量列表)
        
        if not isinstance(数据张量, torch.Tensor):
            return False, "张量类型不是torch"
        
        原总数据量 = self.计算总数据量()
        KEY = self.生成KEY()
        时间 = datetime.now().strftime("%Y/%m/%d")
        
        存储设备 = 记忆者配置中心.张量存储设备  # 【修改】
        数据张量 = 数据张量.to(device=存储设备)
        序列化张量 = self.张量序列化(数据张量)
        
        初始有效值 = 记忆者配置中心.初始有效值  # 【修改】
        
        UP_LEVEL值 = None
        if self.层级数 > 0:
            try:
                with torch.no_grad():
                    if isinstance(数据张量, torch.Tensor):
                        查询向量_np = 数据张量.cpu().numpy()
                    else:
                        查询向量_np = np.array(数据张量)
                    
                    if len(查询向量_np.shape) == 2:
                        查询向量_np = np.mean(查询向量_np, axis=0)
                    
                    查询向量_np = 查询向量_np.flatten()[:self.向量维度]
                    保护值 = 记忆者配置中心.除零保护值  # 【修改】
                    查询向量_np = 查询向量_np / (np.linalg.norm(查询向量_np) + 保护值)
                    
                    目标簇列表 = self.逐级检索索引(查询向量_np, [1])
                    if 目标簇列表:
                        UP_LEVEL值 = 目标簇列表[0]
            except Exception as e:
                UP_LEVEL值 = None
        
        self.游标.execute("""
        INSERT INTO memory (KEY, UP_LEVEL, DATA_CH, TIME, MY_TENSOR, LABEL, VALIDITY, FROZEN)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (KEY, UP_LEVEL值, 文本, 时间, 序列化张量, 标签, 初始有效值, 0))
        
        新总数据量 = self.计算总数据量()
        层级新增, 原层级, 新层级 = self.判断层级新增(原总数据量, 新总数据量)
        if 层级新增:
            self.逐级更新索引(新层级, 数据张量, KEY)
        self.层级数 = self.计算当前层级数()
        self.强制刷盘()
        return True, f"数据库数据存入方法成功，归入簇: {UP_LEVEL值 if UP_LEVEL值 else '无'}\n"

    def 批量数据存入(self, 文本列表, 标签列表=None, 张量列表=None):
        try:
            标签列表 = 标签列表 or [None] * len(文本列表)
            原总数据量 = self.计算总数据量()
            批量数据 = []
            KEY列表 = []
            时间 = datetime.now().strftime("%Y/%m/%d")
            初始有效值 = 记忆者配置中心.初始有效值  # 【修改】
            默认标签 = 记忆者配置中心.默认标签  # 【修改】
            
            for i, (文本, 标签, 张量) in enumerate(zip(文本列表, 标签列表, 张量列表)):
                KEY = f"{(原总数据量 + i + 1):020d}"
                KEY列表.append(KEY)
                序列化张量 = self.张量序列化(张量)
                
                UP_LEVEL值 = None
                if self.层级数 > 0:
                    try:
                        with torch.no_grad():
                            if isinstance(张量, torch.Tensor):
                                查询向量_np = 张量.cpu().numpy()
                            else:
                                查询向量_np = np.array(张量)
                            if len(查询向量_np.shape) == 2:
                                查询向量_np = np.mean(查询向量_np, axis=0)
                            查询向量_np = 查询向量_np.flatten()[:self.向量维度]
                            保护值 = 记忆者配置中心.除零保护值  # 【修改】
                            查询向量_np = 查询向量_np / (np.linalg.norm(查询向量_np) + 保护值)
                            目标簇列表 = self.逐级检索索引(查询向量_np, [1])
                            if 目标簇列表:
                                UP_LEVEL值 = 目标簇列表[0]
                    except Exception as e:
                        UP_LEVEL值 = None
                
                使用标签 = 标签 if 标签 is not None else 默认标签  # 【修改】
                批量数据.append((KEY, UP_LEVEL值, 文本, 时间, 序列化张量, 使用标签, 初始有效值, 0))
            
            self.游标.execute("BEGIN TRANSACTION")
            self.游标.executemany("""
            INSERT INTO memory (KEY, UP_LEVEL, DATA_CH, TIME, MY_TENSOR, LABEL, VALIDITY, FROZEN)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, 批量数据)
            
            新总数据量 = self.计算总数据量()
            层级新增, 原层级, 新层级 = self.判断层级新增(原总数据量, 新总数据量)
            if 层级新增:
                代表张量 = 张量列表[-1]
                for KEY in KEY列表:
                    self.逐级更新索引(新层级, 代表张量, KEY)
            
            self.层级数 = self.计算当前层级数()
            self.强制刷盘()
            
            归类数量 = sum(1 for d in 批量数据 if d[1] is not None)
            return True, f"数据库批量数据存入方法执行成功，{归类数量}/{len(批量数据)}条归入现有簇\n"
        except Exception as e:
            return False, f"数据库批量数据存入方法执行失败,报错:{e}\n"

    def _检索候选数据(self, 查询文本, 查询张量, 包含冻结数据=False, 目标簇数=1):
        """
        【共用】通过聚类索引检索候选数据，避免全表扫描
        """
        # 1. 预处理查询向量
        if isinstance(查询张量, torch.Tensor):
            查询原始向量 = 查询张量.cpu().numpy()
        else:
            查询原始向量 = np.array(查询张量)
        
        if len(查询原始向量.shape) == 2:
            查询索引向量 = np.mean(查询原始向量, axis=0)
        else:
            查询索引向量 = 查询原始向量.flatten()[:self.向量维度]
        
        保护值 = 记忆者配置中心.除零保护值
        查询索引向量 = 查询索引向量 / (np.linalg.norm(查询索引向量) + 保护值)
        
        候选数据 = []
        
        # 2. 有聚类时用索引检索多个候选簇
        if self.层级数 > 0:
            目标簇名称列表 = self.逐级检索索引(查询索引向量, 目标簇数)
            
            if 目标簇名称列表:
                占位符 = ",".join(["?"] * len(目标簇名称列表))
                
                if 包含冻结数据 is True:
                    SQL = f"""
                    SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY, FROZEN, UP_LEVEL 
                    FROM memory 
                    WHERE UP_LEVEL IN ({占位符})
                    """
                    self.游标.execute(SQL, 目标簇名称列表)
                elif 包含冻结数据 == '仅冻结':
                    SQL = f"""
                    SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY, FROZEN, UP_LEVEL 
                    FROM memory 
                    WHERE UP_LEVEL IN ({占位符}) AND FROZEN = 1
                    """
                    self.游标.execute(SQL, 目标簇名称列表)
                else:
                    SQL = f"""
                    SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY, FROZEN, UP_LEVEL 
                    FROM memory 
                    WHERE UP_LEVEL IN ({占位符}) AND FROZEN = 0
                    """
                    self.游标.execute(SQL, 目标簇名称列表)
                
                候选数据 = self.游标.fetchall()
        else:
            # 无聚类，被迫全表
            if 包含冻结数据 is True:
                self.游标.execute("""
                SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY, FROZEN, UP_LEVEL 
                FROM memory
                """)
            elif 包含冻结数据 == '仅冻结':
                self.游标.execute("""
                SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY, FROZEN, UP_LEVEL 
                FROM memory WHERE FROZEN = 1
                """)
            else:
                self.游标.execute("""
                SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY, FROZEN, UP_LEVEL 
                FROM memory WHERE FROZEN = 0
                """)
            
            候选数据 = self.游标.fetchall()
        
        # 3. 兜底异常数据
        异常标记 = 记忆者配置中心.异常标记值
        
        if 包含冻结数据 is True:
            self.游标.execute("""
            SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY, FROZEN, UP_LEVEL 
            FROM memory WHERE UP_LEVEL = ?
            """, (异常标记,))
        elif 包含冻结数据 == '仅冻结':
            self.游标.execute("""
            SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY, FROZEN, UP_LEVEL 
            FROM memory WHERE UP_LEVEL = ? AND FROZEN = 1
            """, (异常标记,))
        else:
            self.游标.execute("""
            SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY, FROZEN, UP_LEVEL 
            FROM memory WHERE UP_LEVEL = ? AND FROZEN = 0
            """, (异常标记,))
        
        异常数据 = self.游标.fetchall()
        所有候选 = list(候选数据) + list(异常数据)
        
        return 所有候选

    def 数据删除(self, 目标文本: str, 压缩向量: torch.Tensor):
        """
        【优化版】使用聚类索引检索，避免全表扫描
        删除操作匹配全表（正常+冻结），越像扣越多
        """
        # 1. 索引检索候选（全表）
        所有候选 = self._检索候选数据(目标文本, 压缩向量, 包含冻结数据=True, 目标簇数=1)
        
        if not 所有候选:
            return False, "数据库为空"
        
        # 2. 细粒度匹配
        目标数据列表 = [(行[0], 行[1], 行[2], 行[3], 行[4]) for 行 in 所有候选]
        匹配结果 = self._细粒度相似度匹配(目标文本, 压缩向量, 目标数据列表, 1)
        
        if not 匹配结果:
            return False, "未找到匹配数据"
        
        最像内容, 最像标签, 最像时间 = 匹配结果[0]
        
        # 3. 定位完整数据
        self.游标.execute("""
        SELECT KEY, VALIDITY, FROZEN FROM memory WHERE DATA_CH = ? LIMIT 1
        """, (最像内容,))
        键值结果 = self.游标.fetchone()
        if not 键值结果:
            return False, "数据定位失败"
        
        目标KEY, 当前有效值, FROZEN状态 = 键值结果
        
        # 4. 计算相似度
        self.游标.execute("SELECT MY_TENSOR FROM memory WHERE KEY = ?", (目标KEY,))
        张量结果 = self.游标.fetchone()
        
        if 张量结果:
            目标张量 = self.张量反序列化(张量结果[0])
            if isinstance(目标张量, torch.Tensor):
                目标张量_np = 目标张量.cpu().detach().numpy()
            else:
                目标张量_np = np.array(目标张量)
            
            if isinstance(压缩向量, torch.Tensor):
                查询向量_np = 压缩向量.cpu().detach().numpy()
            else:
                查询向量_np = np.array(压缩向量)
            
            目标张量_np = 目标张量_np.flatten()[:self.向量维度]
            查询向量_np = 查询向量_np.flatten()[:self.向量维度]
            max_len = max(len(目标张量_np), len(查询向量_np))
            目标张量_np = np.pad(目标张量_np, (0, max_len - len(目标张量_np)), 'constant')
            查询向量_np = np.pad(查询向量_np, (0, max_len - len(查询向量_np)), 'constant')
            
            实际相似度 = self.余弦相似度向量化(查询向量_np, 目标张量_np)
        else:
            实际相似度 = 0.0
        
        # 5. 扣除有效值
        扣除量 = self.计算扣除有效值(实际相似度)
        新有效值, 是否冻结 = self.更新有效值(目标KEY, 扣除量=扣除量)
        
        删除阈值 = 记忆者配置中心.删除阈值
        
        if 新有效值 <= 删除阈值:
            self.游标.execute("DELETE FROM memory WHERE KEY = ?", (目标KEY,))
            self.连接.commit()
            self.强制刷盘()
            return True, f"已删除(有效值耗尽): 内容“{最像内容}”\n标签“{最像标签}”\n原存入时间“{最像时间}”\n扣除{扣除量}, 剩余有效值{新有效值}"
        else:
            return True, f"惩罚扣除{扣除量}, 剩余有效值{新有效值}: 内容“{最像内容}”\n标签“{最像标签}”\n存入时间“{最像时间}”\n状态：{'已冻结' if 是否冻结 else '正常'}"

    def 数据奖励(self, 目标文本: str, 压缩向量: torch.Tensor):
        """
        【优化版】使用聚类索引检索，避免全表扫描
        奖励操作匹配全表（正常+冻结），越像加越多
        """
        # 1. 索引检索候选（全表）
        所有候选 = self._检索候选数据(目标文本, 压缩向量, 包含冻结数据=True, 目标簇数=1)
        
        if not 所有候选:
            return False, "数据库为空"
        
        # 2. 细粒度匹配
        目标数据列表 = [(行[0], 行[1], 行[2], 行[3], 行[4]) for 行 in 所有候选]
        匹配结果 = self._细粒度相似度匹配(目标文本, 压缩向量, 目标数据列表, 1)
        
        if not 匹配结果:
            return False, "未找到匹配数据"
        
        最像内容, 最像标签, 最像时间 = 匹配结果[0]
        
        # 3. 定位完整数据
        self.游标.execute("""
        SELECT KEY, VALIDITY, FROZEN FROM memory WHERE DATA_CH = ? LIMIT 1
        """, (最像内容,))
        键值结果 = self.游标.fetchone()
        if not 键值结果:
            return False, "数据定位失败"
        
        目标KEY, 当前有效值, FROZEN状态 = 键值结果
        
        # 4. 计算相似度
        self.游标.execute("SELECT MY_TENSOR FROM memory WHERE KEY = ?", (目标KEY,))
        张量结果 = self.游标.fetchone()
        
        if 张量结果:
            目标张量 = self.张量反序列化(张量结果[0])
            if isinstance(目标张量, torch.Tensor):
                目标张量_np = 目标张量.cpu().detach().numpy()
            else:
                目标张量_np = np.array(目标张量)
            
            if isinstance(压缩向量, torch.Tensor):
                查询向量_np = 压缩向量.cpu().detach().numpy()
            else:
                查询向量_np = np.array(压缩向量)
            
            目标张量_np = 目标张量_np.flatten()[:self.向量维度]
            查询向量_np = 查询向量_np.flatten()[:self.向量维度]
            max_len = max(len(目标张量_np), len(查询向量_np))
            目标张量_np = np.pad(目标张量_np, (0, max_len - len(目标张量_np)), 'constant')
            查询向量_np = np.pad(查询向量_np, (0, max_len - len(查询向量_np)), 'constant')
            
            实际相似度 = self.余弦相似度向量化(查询向量_np, 目标张量_np)
        else:
            实际相似度 = 0.0
        
        # 5. 增加有效值
        奖励量 = self.计算查询奖励(实际相似度)
        新有效值, 是否冻结 = self.更新有效值(目标KEY, 增量=奖励量)
        
        return True, f"奖励有效值:{奖励量}, 剩余有效值{新有效值}: 内容“{最像内容}”\n标签“{最像标签}”\n存入时间“{最像时间}”\n状态：{'已冻结' if 是否冻结 else '正常'}"

    # ------------------------------ KEY生成 ------------------------------
    def 插空生成Key(self) -> str:
        窗口大小 = 记忆者配置中心.KEY窗口大小  # 【修改】
        
        self.游标.execute("SELECT MAX(CAST(KEY AS INTEGER)) FROM memory")
        结果 = self.游标.fetchone()[0]
        最大序号 = int(结果) if 结果 else 0
        
        窗口数 = (最大序号 // 窗口大小) + 2
        
        for 窗口索引 in range(窗口数):
            窗口起始 = 窗口索引 * 窗口大小 + 1
            窗口结束 = 窗口起始 + 窗口大小 - 1
            
            self.游标.execute("""
                SELECT CAST(KEY AS INTEGER) FROM memory 
                WHERE CAST(KEY AS INTEGER) >= ? AND CAST(KEY AS INTEGER) <= ?
                ORDER BY CAST(KEY AS INTEGER)
            """, (窗口起始, 窗口结束))
            
            序号列表 = [int(row[0]) for row in self.游标.fetchall()]
            
            if not 序号列表:
                return f"{窗口起始:020d}"
            
            if 序号列表[0] > 窗口起始:
                return f"{窗口起始:020d}"
            
            for i in range(len(序号列表) - 1):
                当前序号 = 序号列表[i]
                下一个序号 = 序号列表[i + 1]
                if 下一个序号 > 当前序号 + 1:
                    断点 = 当前序号 + 1
                    return f"{断点:020d}"
        
        return f"{最大序号 + 1:020d}"

    def 随机生成Key(self):
        随机范围 = 记忆者配置中心.KEY随机范围  # 【修改】
        return f"{random.randint(0, 随机范围):020d}"

    def 生成KEY(self):
        Key = self.计算总数据量() + 1
        while self.检查KEY是否重复(Key):
            Key = self.随机生成Key()
        return Key

    def 检查KEY是否重复(self, key: str) -> bool:
        self.游标.execute("SELECT 1 FROM memory WHERE KEY = ? LIMIT 1", (key,))
        return self.游标.fetchone() is not None

    def 判断层级新增(self, 原总数据量, 新总数据量):
        原层级 = math.floor(math.log(原总数据量, self.每级数据量)) if 原总数据量 >= self.每级数据量 else 0
        新层级 = math.floor(math.log(新总数据量, self.每级数据量)) if 新总数据量 >= self.每级数据量 else 0
        return 新层级 > 原层级, 原层级, 新层级
    # ------------------------------ 索引更新 ------------------------------
    def 逐级更新索引(self, 新增层级, 数据张量, 数据KEY):
        当前层级 = 新增层级
        while 当前层级 >= 1:
            原始索引表名 = f"index_level{当前层级}"
            合法索引表名 = self.校验表名(原始索引表名)
            self.创建索引表(当前层级)
            
            索引名称 = f"level{当前层级}_{self.计算总数据量() // self.每级数据量:06d}"
            上级索引名称 = None if 当前层级 == 1 else f"level{当前层级-1}_{self.计算总数据量() // (self.每级数据量**2):06d}"
            时间 = datetime.now().strftime("%Y/%m/%d")
            序列化张量 = self.张量序列化(数据张量)
            
            self.游标.execute(f"""
            INSERT OR IGNORE INTO {合法索引表名} (UP_LEVEL, MY_NAME, MY_TENSOR, TIME)
            VALUES (?, ?, ?, ?)
            """, (上级索引名称, 索引名称, 序列化张量, 时间))
            
            self.游标.execute("""
            UPDATE memory SET UP_LEVEL = ? WHERE KEY = ?
            """, (索引名称, 数据KEY))
            
            self.强制刷盘()
            当前层级 -= 1

    # ------------------------------ 聚类 ------------------------------
    def 执行聚类(self, 强制刷新=False):
        清理阈值 = 记忆者配置中心.聚类前清理阈值  # 【修改】
        
        self.游标.execute("SELECT COUNT(*) FROM memory WHERE VALIDITY <= ?", (清理阈值,))  # 【修改】<=
        待清理数量 = self.游标.fetchone()[0]
        
        if 待清理数量 > 0:
            self.游标.execute("DELETE FROM memory WHERE VALIDITY <= ?", (清理阈值,))  # 【修改】<=
            self.连接.commit()
        
        self.游标.execute("SELECT CLUSTER_STATE, MAX_LEVEL FROM meta_info")
        聚类状态, 已聚类最高层级 = self.游标.fetchone()
        
        if 聚类状态 == 'clustered' and not 强制刷新:
            return "[#promot]聚类状态正常无需刷新[#promot]"
        
        总数据量 = self.计算总数据量()
        目标层级 = self.计算当前层级数()
        
        for 层级 in range(1, 目标层级+1):
            self.聚类单层级(层级)
        
        self.游标.execute("""
        UPDATE meta_info SET 
            CLUSTER_STATE = 'clustered',
            MAX_LEVEL = ?,
            LAST_CLUSTER_TIME = ?
        """, (目标层级, datetime.now().strftime("%Y/%m/%d")))
        self.强制刷盘()
        self.加载索引缓存()
        return "[#promot]聚类完成[#promot]"

    def 聚类单层级(self, 层级):
        if 层级 == 1:
            self.游标.execute("SELECT KEY, DATA_CH, LABEL, MY_TENSOR, FROZEN FROM memory")
            所有数据 = self.游标.fetchall()
            
            if not 所有数据:
                return
            
            原始张量列表 = []
            KEY列表 = []
            文本列表 = []
            标签列表 = []
            冻结标记列表 = []
            
            for row in 所有数据:
                KEY, 文本, 标签, 张量二进制, FROZEN = row
                原始张量 = self.张量反序列化(张量二进制)
                if 原始张量 is not None:
                    原始张量列表.append(原始张量)
                    KEY列表.append(KEY)
                    文本列表.append(文本)
                    标签列表.append(标签)
                    冻结标记列表.append(FROZEN)
            
            if not 原始张量列表:
                return
            
            聚类向量列表 = []
            for 原始张量 in 原始张量列表:
                if isinstance(原始张量, torch.Tensor):
                    原始张量 = 原始张量.cpu().detach().numpy()
                
                if len(原始张量.shape) == 2:
                    聚类向量 = np.mean(原始张量, axis=0)
                else:
                    聚类向量 = 原始张量.flatten()[:self.向量维度]
                聚类向量列表.append(聚类向量)
            
            聚类向量数组 = np.array(聚类向量列表, dtype=np.float32)
            簇数量 = max(1, len(聚类向量数组) // self.每级数据量)
            
            if 簇数量 < 2:
                中心张量 = np.mean(聚类向量数组, axis=0, dtype=np.float32)
                索引名称 = f"level{层级}_000001"
                self.创建索引表(层级)
                合法表名 = self.校验表名(f"index_level{层级}")
                self.游标.execute(f"""
                INSERT OR IGNORE INTO {合法表名} (UP_LEVEL, MY_NAME, MY_TENSOR, TIME)
                VALUES (?, ?, ?, ?)
                """, (None, 索引名称, self.张量序列化(中心张量), datetime.now().strftime("%Y/%m/%d")))
                
                for KEY in KEY列表:
                    self.游标.execute("UPDATE memory SET UP_LEVEL = ? WHERE KEY = ?", (索引名称, KEY))
                self.强制刷盘()
                return
            
            随机种子 = 记忆者配置中心.聚类随机种子  # 【修改】
            最大迭代 = 记忆者配置中心.聚类最大迭代  # 【修改】
            
            try:
                from sklearn.cluster import KMeans
                kmeans = KMeans(n_clusters=簇数量, random_state=随机种子, max_iter=最大迭代)  # 【修改】
                簇标签 = kmeans.fit_predict(聚类向量数组)
                簇中心列表 = kmeans.cluster_centers_
            except ImportError:
                簇大小 = len(聚类向量数组) // 簇数量
                簇分割索引 = [i * 簇大小 for i in range(1, 簇数量)]
                簇向量列表 = np.split(聚类向量数组, 簇分割索引)
                KEY簇列表 = np.split(np.array(KEY列表), 簇分割索引)
                簇中心列表 = [np.mean(vec, axis=0) for vec in 簇向量列表]
                簇标签 = []
                for idx, vec in enumerate(簇向量列表):
                    簇标签.extend([idx] * len(vec))
            
            self.创建索引表(层级)
            合法表名 = self.校验表名(f"index_level{层级}")
            
            for 簇_idx in range(簇数量):
                索引名称 = f"level{层级}_{簇_idx+1:06d}"
                中心张量 = 簇中心列表[簇_idx]
                self.游标.execute(f"""
                INSERT OR IGNORE INTO {合法表名} (UP_LEVEL, MY_NAME, MY_TENSOR, TIME)
                VALUES (?, ?, ?, ?)
                """, (None, 索引名称, self.张量序列化(中心张量), datetime.now().strftime("%Y/%m/%d")))
            
            异常数据计数 = 0
            
            for 成员索引 in range(len(聚类向量列表)):
                成员向量 = 聚类向量列表[成员索引]
                成员KEY = KEY列表[成员索引]
                
                是否异常, 最佳相似度, 最佳簇索引 = self.判断数据是否异常(
                    成员向量, 
                    所有簇中心列表=簇中心列表
                )
                
                if 是否异常:
                    self.将数据标记为异常(成员KEY)
                    异常数据计数 += 1
                else:
                    最佳索引名称 = f"level{层级}_{最佳簇索引+1:06d}"
                    self.游标.execute("""
                    UPDATE memory SET UP_LEVEL = ? WHERE KEY = ?
                    """, (最佳索引名称, 成员KEY))
            
            self.强制刷盘()
            
        else:
            下级表名 = self.校验表名(f"index_level{层级-1}")
            self.游标.execute(f"SELECT MY_NAME, MY_TENSOR FROM {下级表名}")
            下级索引数据 = self.游标.fetchall()
            
            if not 下级索引数据:
                return
            
            下级名称列表 = [t[0] for t in 下级索引数据]
            下级张量列表 = [self.张量反序列化(t[1]) for t in 下级索引数据]
            
            聚类向量列表 = []
            for 张量 in 下级张量列表:
                if isinstance(张量, torch.Tensor):
                    张量 = 张量.cpu().detach().numpy()
                聚类向量列表.append(张量)
            
            聚类向量数组 = np.array(聚类向量列表, dtype=np.float32)
            簇数量 = max(1, len(聚类向量数组) // self.每级数据量)
            簇大小 = len(聚类向量数组) // 簇数量
            簇分割索引 = [i * 簇大小 for i in range(1, 簇数量)]
            簇向量列表 = np.split(聚类向量数组, 簇分割索引)
            下级名称簇列表 = np.split(np.array(下级名称列表), 簇分割索引)
            
            self.创建索引表(层级)
            合法表名 = self.校验表名(f"index_level{层级}")
            
            for 簇_idx, (簇向量, 簇内下级名称) in enumerate(zip(簇向量列表, 下级名称簇列表)):
                中心张量 = np.mean(簇向量, axis=0, dtype=np.float32)
                索引名称 = f"level{层级}_{簇_idx+1:06d}"
                上级索引名称 = 簇内下级名称[0] if len(簇内下级名称) > 0 else None
                self.游标.execute(f"""
                INSERT OR IGNORE INTO {合法表名} (UP_LEVEL, MY_NAME, MY_TENSOR, TIME)
                VALUES (?, ?, ?, ?)
                """, (上级索引名称, 索引名称, self.张量序列化(中心张量), datetime.now().strftime("%Y/%m/%d")))
            
            self.强制刷盘()

    def 判断数据是否异常(self, 数据向量, 所有簇中心列表):
        阈值 = 记忆者配置中心.异常相似度阈值  # 【修改】
        
        最佳相似度 = -1.0
        最佳簇索引 = -1
        
        for idx, 簇中心 in enumerate(所有簇中心列表):
            if isinstance(数据向量, torch.Tensor):
                数据向量_np = 数据向量.cpu().detach().numpy()
            else:
                数据向量_np = np.array(数据向量)
                
            if isinstance(簇中心, torch.Tensor):
                簇中心_np = 簇中心.cpu().detach().numpy()
            else:
                簇中心_np = np.array(簇中心)
            
            数据向量_np = 数据向量_np.flatten()[:self.向量维度]
            簇中心_np = 簇中心_np.flatten()[:self.向量维度]
            max_len = max(len(数据向量_np), len(簇中心_np))
            数据向量_np = np.pad(数据向量_np, (0, max_len - len(数据向量_np)), 'constant')
            簇中心_np = np.pad(簇中心_np, (0, max_len - len(簇中心_np)), 'constant')
            
            相似度 = self.余弦相似度向量化(数据向量_np, 簇中心_np)
            
            if 相似度 > 最佳相似度:
                最佳相似度 = 相似度
                最佳簇索引 = idx
        
        return 最佳相似度 < 阈值, 最佳相似度, 最佳簇索引  # 【修改】<

    def 将数据标记为异常(self, KEY):
        try:
            异常标记 = 记忆者配置中心.异常标记值  # 【修改】
            self.游标.execute("""
            UPDATE memory SET UP_LEVEL = ? WHERE KEY = ?
            """, (异常标记, KEY))
            return True
        except Exception as e:
            return False

    # ------------------------------ 有效值计算 ------------------------------
    def 计算扣除有效值(self, 相似度: float) -> float:
        T = 记忆者配置中心.相似度惩罚阈值  # 【修改】
        K_hard = 记忆者配置中心.硬惩罚系数  # 【修改】
        K_soft = 记忆者配置中心.软惩罚系数  # 【修改】
        epsilon = 记忆者配置中心.Sigmoid缩放因子  # 【修改】
        
        import math
        
        if 相似度 < T:
            差值 = T - 相似度
            sigmoid因子 = 1 / (1 + math.exp(-差值 / epsilon))
            扣除 = 差值 * sigmoid因子 * K_hard
        else:
            差值 = 相似度 - T
            扣除 = 差值 * K_soft
        
        return self.量化有效值(扣除)

    '''
    def 计算查询奖励(self, 相似度: float) -> float:
        T = 记忆者配置中心.相似度奖励阈值  # 【修改】
        K_soft = 记忆者配置中心.软惩罚系数  # 【修改】
        epsilon = 记忆者配置中心.Sigmoid缩放因子  # 【修改】
        保底奖励 = 记忆者配置中心.低相似保底奖励  # 【修改】
        
        if 相似度 >= T:
            差值 = 相似度 - T
            奖励 = 差值 * K_soft
        else:
            差值 = T - 相似度
            sigmoid因子 = 1 / (1 + math.exp(-差值 / epsilon))
            奖励 = 保底奖励 * (1 - sigmoid因子)  # 【修改】
        return self.量化有效值(奖励)'''

    def 更新有效值(self, KEY: str, 扣除量: float = None, 增量: float = None) -> tuple:
        self.游标.execute("SELECT VALIDITY, FROZEN FROM memory WHERE KEY = ?", (KEY,))
        结果 = self.游标.fetchone()
        if not 结果:
            return None, True
        
        当前值, 当前冻结状态 = 结果
        
        if 扣除量 is not None:
            新值 = self.量化有效值(当前值 - 扣除量)
        elif 增量 is not None:
            新值 = self.量化有效值(当前值 + 增量)
        else:
            return 当前值, 当前冻结状态 == 1
        
        冻结阈值 = 记忆者配置中心.冻结阈值  # 【修改】核心！
        是否冻结 = 新值 <= 冻结阈值  # 【修改】使用配置中心参数
        
        self.游标.execute("""
        UPDATE memory SET VALIDITY = ?, FROZEN = ? WHERE KEY = ?
        """, (新值, 1 if 是否冻结 else 0, KEY))
        self.连接.commit()
        
        return 新值, 是否冻结

    # ------------------------------ 索引检索 ------------------------------
    def 加载索引缓存(self):
        self.索引缓存.clear()
        for 层级 in range(1, self.层级数+1):
            原始表名 = f"index_level{层级}"
            合法表名 = self.校验表名(原始表名)
            self.游标.execute(f"SELECT MY_NAME, MY_TENSOR FROM {合法表名}")
            索引数据 = self.游标.fetchall()
            self.索引缓存[层级] = {名: self.张量反序列化(张量) for 名, 张量 in 索引数据}

    def 逐级检索索引(self, 查询向量, 返回簇数=1):
        """
        【修复】均衡路径束搜索，支持返回TopN个候选簇
        
        :param 返回簇数: 最终返回多少个叶子节点（默认1，删除/奖励用1，查询可用更多）
        """
        if self.层级数 == 0:
            return []
        
        if 1 not in self.索引缓存:
            return []
        
        一级索引缓存 = self.索引缓存[1]
        
        一级相似度列表 = []
        for 名, 张量 in 一级索引缓存.items():
            相似度 = self.相似度方法(查询向量, 张量)
            一级相似度列表.append((名, 相似度))
        
        K1 = self.计算自适应束宽([s for _, s in 一级相似度列表])
        一级相似度列表.sort(key=lambda x: x[1], reverse=True)
        初始路径 = [[(名, 相似度)] for 名, 相似度 in 一级相似度列表[:K1]]
        
        当前路径 = 初始路径
        
        for 当前层级 in range(2, self.层级数 + 1):
            新路径列表 = []
            
            for 路径 in 当前路径:
                末端节点名 = 路径[-1][0]
                
                合法下级表名 = self.校验表名(f"index_level{当前层级}")
                self.游标.execute(f"""
                SELECT MY_NAME, MY_TENSOR FROM {合法下级表名} WHERE UP_LEVEL = ?
                """, (末端节点名,))
                下级索引数据 = self.游标.fetchall()
                
                if not 下级索引数据:
                    新路径列表.append(路径)
                    continue
                
                子节点相似度 = []
                for 子名, 子张量二进制 in 下级索引数据:
                    子张量 = self.张量反序列化(子张量二进制)
                    相似度 = self.相似度方法(查询向量, 子张量)
                    子节点相似度.append((子名, 相似度))
                
                K = self.计算自适应束宽([s for _, s in 子节点相似度])
                子节点相似度.sort(key=lambda x: x[1], reverse=True)
                
                for 子名, 相似度 in 子节点相似度[:K]:
                    新路径 = 路径 + [(子名, 相似度)]
                    新路径列表.append(新路径)
            
            束宽最大值 = 记忆者配置中心.束宽最大值
            
            if len(新路径列表) > 束宽最大值:
                路径得分列表 = []
                for 路径 in 新路径列表:
                    相似度序列 = [s for _, s in 路径]
                    得分 = self.路径均衡得分(相似度序列)
                    路径得分列表.append((路径, 得分))
                
                路径得分列表.sort(key=lambda x: x[1], reverse=True)
                当前路径 = [路径 for 路径, _ in 路径得分列表[:束宽最大值]]
            else:
                当前路径 = 新路径列表
        
        if not 当前路径:
            return []
        
        # 【修复】返回TopN个最优叶子节点，而不是只返回1个
        最终评分 = []
        for 路径 in 当前路径:
            相似度序列 = [s for _, s in 路径]
            得分 = self.路径均衡得分(相似度序列)
            末端节点 = 路径[-1][0]
            最终评分.append((末端节点, 得分, 相似度序列))
        
        最终评分.sort(key=lambda x: x[1], reverse=True)
        
        # 去重并返回指定数量
        已返回 = set()
        结果 = []
        for 叶子节点, 得分, _ in 最终评分:
            if 叶子节点 not in 已返回:
                结果.append(叶子节点)
                已返回.add(叶子节点)
                if len(结果) >= 返回簇数:
                    break
        
        return 结果

    '''
    def 逐级检索索引(self, 查询向量, 检索数列表):
        if self.层级数 == 0:
            return []
        
        if 1 not in self.索引缓存:
            return []
        
        一级索引缓存 = self.索引缓存[1]
        
        一级相似度列表 = []
        for 名, 张量 in 一级索引缓存.items():
            相似度 = self.相似度方法(查询向量, 张量)
            一级相似度列表.append((名, 相似度))
        
        K1 = self.计算自适应束宽([s for _, s in 一级相似度列表])
        一级相似度列表.sort(key=lambda x: x[1], reverse=True)
        初始路径 = [[(名, 相似度)] for 名, 相似度 in 一级相似度列表[:K1]]
        
        当前路径 = 初始路径
        
        for 当前层级 in range(2, self.层级数 + 1):
            新路径列表 = []
            
            for 路径 in 当前路径:
                末端节点名 = 路径[-1][0]
                
                合法下级表名 = self.校验表名(f"index_level{当前层级}")
                self.游标.execute(f"""
                SELECT MY_NAME, MY_TENSOR FROM {合法下级表名} WHERE UP_LEVEL = ?
                """, (末端节点名,))
                下级索引数据 = self.游标.fetchall()
                
                if not 下级索引数据:
                    新路径列表.append(路径)
                    continue
                
                子节点相似度 = []
                for 子名, 子张量二进制 in 下级索引数据:
                    子张量 = self.张量反序列化(子张量二进制)
                    相似度 = self.相似度方法(查询向量, 子张量)
                    子节点相似度.append((子名, 相似度))
                
                K = self.计算自适应束宽([s for _, s in 子节点相似度])
                子节点相似度.sort(key=lambda x: x[1], reverse=True)
                
                for 子名, 相似度 in 子节点相似度[:K]:
                    新路径 = 路径 + [(子名, 相似度)]
                    新路径列表.append(新路径)
            
            束宽最大值 = 记忆者配置中心.束宽最大值  # 【修改】
            
            if len(新路径列表) > 束宽最大值:
                路径得分列表 = []
                for 路径 in 新路径列表:
                    相似度序列 = [s for _, s in 路径]
                    得分 = self.路径均衡得分(相似度序列)
                    路径得分列表.append((路径, 得分))
                
                路径得分列表.sort(key=lambda x: x[1], reverse=True)
                当前路径 = [路径 for 路径, _ in 路径得分列表[:束宽最大值]]
            else:
                当前路径 = 新路径列表
        
        if not 当前路径:
            return []
        
        最终评分 = []
        for 路径 in 当前路径:
            相似度序列 = [s for _, s in 路径]
            得分 = self.路径均衡得分(相似度序列)
            末端节点 = 路径[-1][0]
            最终评分.append((末端节点, 得分, 相似度序列))
        
        最终评分.sort(key=lambda x: x[1], reverse=True)
        最优叶子节点 = 最终评分[0][0]
        return [最优叶子节点]'''

    def 路径均衡得分(self, 路径相似度列表: list, alpha: float = None) -> float:
        if alpha is None:
            alpha = 记忆者配置中心.束搜索方差惩罚系数  # 【修改】
        
        if not 路径相似度列表:
            return 0.0
        
        均值 = sum(路径相似度列表) / len(路径相似度列表)
        方差 = sum((s - 均值) ** 2 for s in 路径相似度列表) / len(路径相似度列表)
        
        return 均值 - alpha * 方差

    def 计算自适应束宽(self, 相似度列表: list) -> int:
        if not 相似度列表:
            return 记忆者配置中心.束宽默认值  # 【修改】
        
        差距上限 = 记忆者配置中心.束宽差距上限  # 【修改】
        差距下限 = 记忆者配置中心.束宽差距下限  # 【修改】
        束宽最小值 = 记忆者配置中心.束宽最小值  # 【修改】
        束宽最大值 = 记忆者配置中心.束宽最大值  # 【修改】
        束宽默认值 = 记忆者配置中心.束宽默认值  # 【修改】
        
        gap = max(相似度列表) - min(相似度列表)
        
        if gap > 差距上限:
            return 束宽最小值
        elif gap < 差距下限:
            return min(束宽最大值, len(相似度列表))
        else:
            return 束宽默认值

    # ------------------------------ 双轨查询 ------------------------------
    def 数据提取(self, 查询文本, 查询张量, 检索数列表=None, mode="cuda") -> list[tuple[str, str, str]]:
        检索数列表 = 检索数列表 or [10]
        返回条数 = 检索数列表[0]
        
        if isinstance(查询张量, torch.Tensor):
            查询原始向量 = 查询张量.cpu().numpy()
        else:
            查询原始向量 = np.array(查询张量)
        
        if len(查询原始向量.shape) == 2:
            查询索引向量 = np.mean(查询原始向量, axis=0)
        else:
            查询索引向量 = 查询原始向量.flatten()[:self.向量维度]
        
        保护值 = 记忆者配置中心.除零保护值  # 【修改】
        查询索引向量 = 查询索引向量 / (np.linalg.norm(查询索引向量) + 保护值)
        
        正常匹配结果 = self._正常查询轨道(查询文本, 查询张量, 查询索引向量, 返回条数)
        
        复苏线程 = threading.Thread(
            target=self._复苏查询轨道,
            args=(查询文本, 查询张量, 查询索引向量),
            daemon=True
        )
        复苏线程.start()
        
        return 正常匹配结果

    def _正常查询轨道(self, 查询文本, 查询张量, 查询索引向量, 返回条数):
        if self.层级数 == 0:
            self.游标.execute("""
            SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY 
            FROM memory 
            WHERE FROZEN = 0
            """)
            正常数据 = self.游标.fetchall()
        else:
            目标簇名称列表 = self.逐级检索索引(查询索引向量, [返回条数])
            
            正常数据 = []
            if 目标簇名称列表:
                占位符 = ",".join(["?"] * len(目标簇名称列表))
                self.游标.execute(f"""
                SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY 
                FROM memory 
                WHERE UP_LEVEL IN ({占位符}) AND FROZEN = 0
                """, 目标簇名称列表)
                正常数据 = self.游标.fetchall()
        
        异常标记 = 记忆者配置中心.异常标记值  # 【修改】
        self.游标.execute("""
        SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY 
        FROM memory 
        WHERE UP_LEVEL = ? AND FROZEN = 0
        """, (异常标记,))
        正常异常数据 = self.游标.fetchall()
        
        所有正常数据 = list(正常数据) + list(正常异常数据)
        正常目标数据列表 = [(行[0], 行[1], 行[2], 行[3], 行[4]) for 行 in 所有正常数据]
        匹配结果 = self._细粒度相似度匹配(查询文本, 查询张量, 正常目标数据列表, 返回条数)
        if 匹配结果:
            for 内容, 标签, 时间 in 匹配结果:
                self._给予查询奖励(查询文本, 查询张量, 内容, 是冻结数据=False)
        else:
            匹配结果 = [(f"抱歉,未找到与你所查找的数据:“{查询文本}”相似度高于“{记忆者配置中心.匹配成功阈值}”的数据,\n目前你只能描述得更详细,或者不查(未来可能会加命令给你调整这些参数)","_空_","-13800000000/0/0")]
        return 匹配结果

    def _复苏查询轨道(self, 查询文本, 查询张量, 查询索引向量):
        """【修复】复苏线程使用独立连接，支持层级数=0时的全表扫描，修复参数类型错误"""
        # 在线程内创建独立连接
        线程连接 = sqlite3.connect(self.数据库路径)
        线程连接.execute("PRAGMA cache_size = -102400")
        线程连接.execute("PRAGMA journal_mode = WAL")
        线程游标 = 线程连接.cursor()
        
        try:
            #Pub.发送日志("调试","复苏查询轨道被调用")
            冻结数据 = []
            复苏束宽 = 记忆者配置中心.复苏查询束宽
            
            if self.层级数 > 0:
                # 【修复】传入整数而非列表
                目标簇名称列表 = self.逐级检索索引(查询索引向量, 复苏束宽)
                
                if 目标簇名称列表:
                    占位符 = ",".join(["?"] * len(目标簇名称列表))
                    线程游标.execute(f"""
                    SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY 
                    FROM memory 
                    WHERE UP_LEVEL IN ({占位符}) AND FROZEN = 1
                    """, 目标簇名称列表)
                    冻结数据 = 线程游标.fetchall()
            else:
                # 【修复】层级数=0时，全表扫描找冻结数据
                线程游标.execute("""
                SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY 
                FROM memory 
                WHERE FROZEN = 1
                """)
                冻结数据 = 线程游标.fetchall()
            
            异常标记 = 记忆者配置中心.异常标记值
            线程游标.execute("""
            SELECT KEY, DATA_CH, LABEL, MY_TENSOR, TIME, VALIDITY 
            FROM memory 
            WHERE UP_LEVEL = ? AND FROZEN = 1
            """, (异常标记,))
            冻结异常数据 = 线程游标.fetchall()
            
            所有冻结数据 = list(冻结数据) + list(冻结异常数据)
            
            if not 所有冻结数据:
                Pub.发送日志("警告","复苏查询轨道:没有冻结数据")
                return
            
            冻结目标数据列表 = [(行[0], 行[1], 行[2], 行[3], 行[4]) for 行 in 所有冻结数据]
            带分数结果 = self._细粒度相似度匹配带分数(查询文本, 查询张量, 冻结目标数据列表)
            
            复苏比例 = 记忆者配置中心.复苏相似度比例
            奖励阈值 = 记忆者配置中心.相似度奖励阈值
            复苏阈值 = 奖励阈值 * 复苏比例
            
            for 内容, 标签, 时间, 相似度, KEY in 带分数结果:
                if 相似度 < 复苏阈值:
                    continue
                
                # 使用线程游标查询当前状态（可能被其他线程修改）
                线程游标.execute("SELECT VALIDITY, FROZEN FROM memory WHERE KEY = ?", (KEY,))
                结果 = 线程游标.fetchone()
                if not 结果:
                    continue
                
                当前有效值, 当前冻结状态 = 结果
                
                # 【修复】如果已经不是冻结状态，跳过（可能被其他查询复苏了）
                if 当前冻结状态 != 1:
                    continue
                
                奖励量 = self.计算查询奖励(相似度)
                
                # 直接计算新值，不调用 self.更新有效值（避免跨线程游标问题）
                新值 = self.量化有效值(当前有效值 + 奖励量)
                冻结阈值 = 记忆者配置中心.冻结阈值
                是否冻结 = 新值 <= 冻结阈值
                
                # 使用线程游标执行更新，并加锁保护
                with self._数据库锁:
                    线程游标.execute("""
                    UPDATE memory SET VALIDITY = ?, FROZEN = ? WHERE KEY = ?
                    """, (新值, 1 if 是否冻结 else 0, KEY))
                    线程连接.commit()
                
                # 如果已经解冻，确保状态正确
                if not 是否冻结:
                    with self._数据库锁:
                        线程游标.execute("""
                        UPDATE memory SET FROZEN = 0 WHERE KEY = ? AND FROZEN = 1
                        """, (KEY,))
                        线程连接.commit()
                    
                    if 独立运行调试:
                        print(f"[复苏] KEY={KEY}, 当前有效值={当前有效值}, 奖励量={奖励量}, 新值={新值}, 已解冻")
        
        finally:
            线程连接.close()

    def _给予查询奖励(self, 查询文本, 查询张量, 数据内容: str, 是冻结数据: bool = False):
        self.游标.execute("SELECT KEY, VALIDITY, MY_TENSOR, FROZEN FROM memory WHERE DATA_CH = ? LIMIT 1", (数据内容,))
        键值结果 = self.游标.fetchone()
        if not 键值结果:
            return
            
        KEY, 当前值, 张量二进制, FROZEN状态 = 键值结果
        
        if FROZEN状态 == 1:
            return
        
        数据张量 = self.张量反序列化(张量二进制)
        if 数据张量 is None:
            return
            
        if isinstance(数据张量, torch.Tensor):
            数据向量_np = 数据张量.cpu().detach().numpy()
        else:
            数据向量_np = np.array(数据张量)
        
        if isinstance(查询张量, torch.Tensor):
            查询向量_np = 查询张量.cpu().detach().numpy()
        else:
            查询向量_np = np.array(查询张量)
        
        数据向量_np = 数据向量_np.flatten()[:self.向量维度]
        查询向量_np = 查询向量_np.flatten()[:self.向量维度]
        max_len = max(len(数据向量_np), len(查询向量_np))
        数据向量_np = np.pad(数据向量_np, (0, max_len - len(数据向量_np)), 'constant')
        查询向量_np = np.pad(查询向量_np, (0, max_len - len(查询向量_np)), 'constant')
        
        实际相似度 = self.余弦相似度向量化(查询向量_np, 数据向量_np)
        奖励量 = self.计算查询奖励(实际相似度)
        
        if 当前值 is not None:
            self.更新有效值(KEY, 增量=奖励量)

    # ------------------------------ 析构 ------------------------------
    def __del__(self):
        self.停止衰减线程()
        
        if hasattr(self, '连接'):
            self.强制刷盘()
            self.连接.close()
        try:
            torch.cuda.empty_cache()
        except:
            pass


"""                    全    局    设    定                         """
# ===================== 全局变量（仅初始化一次） =====================
tokenizer = None
model = None
模型初始化完成 = False
初始化错误信息 = ""
torch.set_default_dtype(torch.float16)
model_dir = None  # 需要外部传入或使用默认搜索
全局通讯锁 = threading.RLock()
# ===================== 提取输入的JSON并解析 ===================
def 提取JSON字典(输入字符串, 提示词1, 提示词2):
    def _convert_yes_no_to_bool(data):
        if isinstance(data, dict):
            for key, value in data.items():
                data[key] = _convert_yes_no_to_bool(value)
            return data
        elif isinstance(data, list):
            return [_convert_yes_no_to_bool(item) for item in data]
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
            
            JSON字符串 = 输入字符串[JSON起始索引:目标提示词2索引].strip()
            if JSON字符串:
                工具字典 = json.loads(JSON字符串)
                工具字典 = _convert_yes_no_to_bool(工具字典)
                工具调用字典列表.append(工具字典)
            
            当前起始位置 = 目标提示词2索引 + 提示词2长度
            字典序号 += 1
        return True,工具调用字典列表
    except Exception as e:
        return False,[f"JSON解析异常,解析{字典序号}号索引的工具字典时出现问题(索引从0开始)：{e}"]
# ===================== 调用千问解析出浓缩语义向量 =====================
def 获取统一浓缩向量(text) -> torch.Tensor:
    global tokenizer, model
    inputs = tokenizer(
        text,
        return_tensors="pt",
        padding=False,
        truncation=True,
        max_length=8192
    ).to(model.device)
    token_ids = inputs["input_ids"]
    attention_mask = inputs["attention_mask"]
    word_embedding_matrix = model.transformer.wte(token_ids)
    mask_expanded = attention_mask.unsqueeze(-1).expand(word_embedding_matrix.size()).float()
    sum_embeddings = torch.sum(word_embedding_matrix * mask_expanded, dim=1)
    sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
    pooled_embedding = sum_embeddings / sum_mask
    pooled_embedding = torch.nn.functional.normalize(pooled_embedding, p=2, dim=1)
    return pooled_embedding
"""                    记    忆    者                    """
数据库路径 = None  # 需要外部初始化时传入


def 记忆工具(text:str):
    global 存入关键词, 取出关键词, 聚类关键词, 数据标首, 数据标尾, 删除关键词
    
    if (存入关键词 in text) and (取出关键词 in text):
        return False, f"""用中文原封不动的复读引号中内容:“错误:关键词冲突，{存入关键词}和{取出关键词}只能选一个”"""
    结果 = ""
    # 预处理文本
    Pub.发送日志("调试", f"记忆工接受处理内容:{text}") # 20260429
    text = text.strip().removeprefix(__关键词__).strip()
    Pub.发送日志("调试", f"记忆工具正处理内容:{text}") # 20260429
    # 聚类
    if text.startswith(聚类关键词):
        结果 = kb.执行聚类(强制刷新=True)
        return (True, 结果) if 结果 else (False, "聚类执行失败")
    # 删除
    elif text.startswith(删除关键词):
        text = text.removeprefix(删除关键词)
        with torch.no_grad():
            #张量 = 获取统一浓缩向量(text=text)
            张量 = 词嵌入.获取比对向量(True,text)
        成功否,工具结果 = kb.数据删除(目标文本=text,压缩向量=张量)
        del 张量
        torch.cuda.empty_cache()
        return (True,f"成功:{工具结果}") if 成功否 else (False,f"错误:{工具结果}")
    # 新增使用方法直接传入文本没有复杂JSON结构
    
    elif 直接文本模式: # 20260429
        # 存入 ======
        if text.startswith(存入关键词):
            存入文本 = text.removeprefix(存入关键词)
            try:
                标签字符串 = "_无_"
                with torch.no_grad():
                    #张量 = 获取统一浓缩向量(存入文本)
                    张量 = 词嵌入.获取比对向量(False,存入文本)
                成功否,返回结果 = kb.数据存入(存入文本, 标签字符串, 张量)
                del 张量
            except Exception as e:
                return None, f"“错误:{traceback.format_exc()}”"
            return (True, f"“{返回结果}”") if 成功否 else (False, f"错误,数据存入失败,结果:{返回结果}")
        # 取出 ======
        elif text.startswith(取出关键词):
            目标查询 = text.removeprefix(取出关键词)
            with torch.no_grad():
                #张量 = 获取统一浓缩向量(目标查询)
                张量 = 词嵌入.获取比对向量(True,目标查询)
            工具结果 = kb.数据提取(查询文本=目标查询, 查询张量=张量)
            if isinstance(工具结果,list):
                返回文本串 = f"查询目标文本:“{目标查询}”,返回结果内容:\n"
                for n,项目元组 in enumerate(工具结果):
                    try:
                        内容 = 项目元组[0]
                        标签 = 项目元组[1]
                        时间 = 项目元组[2]
                    except Exception as e:
                        返回子文本串 += f"\t第{n}条,错误:{e}"
                        continue
                    返回最小文本串单位 = f"""\t第{n}条:存入时间:{时间},数据标签:({标签}),具体数据内容-start->{内容}<-stop-\n"""
                    返回文本串 += 返回最小文本串单位
            else:
                返回文本串 = "错误:是数据库的问题,查询返回结果不是list,故障原因未知"
            del 张量
            torch.cuda.empty_cache()
            return (True, 返回文本串) if 返回文本串 else (False, "数据提取无结果")
        else:
            return False, "错误:关键词格式必须是“[记忆者][存入]|[记忆者][取出]|[记忆者][删除]....”这样,关键词要紧挨着"
    elif not 直接文本模式:
        # 解析(存入/取出)
        成功否,传入字典列表 = 提取JSON字典(text, 数据标首, 数据标尾)
        if not isinstance(传入字典列表, list) or len(传入字典列表) == 0:
            return False, f"用中文原封不动的复读引号中内容:“JSON解析失败：{传入字典列表}”"
        传入字典 = 传入字典列表[0] # 只取首个
        if not isinstance(传入字典, dict):
            return False, f"[#promot]记忆者传入解包后内容类型:{type(传入字典)},具体内容:{传入字典}[#promot]"
        # 存入信息
        if 存入关键词 in text:
            try:
                内容列表 = 传入字典["内容"]
                if not 内容列表:
                    return False, "用中文原封不动的复读引号中内容:“错误,不能传入空的内容列表”"
            except KeyError:
                return False, "用中文原封不动的复读引号中内容:“存入格式错误,缺少 内容:内容列表 键值对”"
            成功否 = False
            # 遍历并存入
            for i in range(len(内容列表)):
                try:
                    标签字符串 = "_无_"
                    with torch.no_grad():
                        #张量 = 获取统一浓缩向量(内容列表[i])
                        张量 = 词嵌入.获取比对向量(False,内容列表[i])
                    成功否,返回结果 = kb.数据存入(内容列表[i], 标签字符串, 张量)
                    del 张量
                except Exception as e:
                    return None, f"“错误:{traceback.format_exc()}”"
            
            return (True, f"“{返回结果}”") if 成功否 else (False, f"错误,数据存入失败,结果:{返回结果}")
        # 取出信息
        elif 取出关键词 in text:
            try:
                提取参照列表 = 传入字典["关键"]
            except KeyError:
                return False, "错误,取出格式,缺少Key“关键”对应内容"
            结果 = []
            返回文本串 = ""
            for i,关键词 in enumerate(提取参照列表):
                with torch.no_grad():
                    张量 = 词嵌入.获取比对向量(True,关键词)
                工具结果 = kb.数据提取(查询文本=关键词, 查询张量=张量)
                if isinstance(工具结果,list):
                    返回子文本串 = f"查询关键索引:“{关键词}”,内容:\n"
                    for n,项目元组 in enumerate(工具结果):
                        try:
                            内容 = 项目元组[0]
                            标签 = 项目元组[1]
                            时间 = 项目元组[2]
                        except Exception as e:
                            返回子文本串 += f"\t第{n}条,错误:{e}"
                            break
                        返回最小文本串单位 = f"""\t第{n}条:存入时间:{时间},数据标签:({标签}),具体数据内容-start->{内容}<-stop-\n"""
                        返回子文本串 += 返回最小文本串单位
                    返回文本串+=返回子文本串
                del 张量
                torch.cuda.empty_cache()
            return (True, 返回文本串) if 返回文本串 else (False, "数据提取无结果")
        # 未知情况
        else:
            return False, "无效的工具调用"

# ===================== 核心方法：处理（原监听并输出） =====================
记忆者上下文管理器 = 上下文管理器(上下文限制=65535,历史=[])
def 处理(数据, 数据类型: str = "str", 协议头: dict = {}) -> str:
    # 通知主进程开始工作
    Pub.发送状态("运行中")
    """
    处理函数 - 专注于业务逻辑
    传入: 已提取的纯数据（字符串/列表/字典等）
    返回: 处理结果字符串（或None表示不处理）
    """
    global __简介__
    if isinstance (数据, str):
        # ========== 获取呼叫关键词 =========
        回调关键词 = 协议头.get("插件信息",{}).get("呼叫关键词",None)
        Pub.发送日志("调试",f"回调关键词:{str(回调关键词)}")
        # 变量初始化
        数据 = Pub.移除标记间内容("``","``:",数据).strip() # 清理文本
        数据 = 数据.removeprefix(__关键词__)  # 清理文本
        提示 = ""
        # 直接操作工具（新协议格式） 
        if 直接文本模式:
            成功否, 提示 = 记忆工具(数据)
            if 成功否:
                return 提示
            else: # 统一返回给主循环进行发送,减少发送输出方法的调用次数
                return f"“你的需求未成功:{提示}”"
    # 没调用记忆者（理论上不会走到这里）
    return None


# ===================== 初始化方法 =====================
def 初始化(模型路径=None, 数据库文件路径=None):
    """初始化记忆者模块
        参数:
            模型路径: Qwen模型文件夹路径，None则自动搜索
            数据库文件路径: Memorytest.db路径，None则自动搜索"""
    global tokenizer, model, 模型初始化完成, 初始化错误信息, kb, 数据库路径, model_dir, 词嵌入
    try:
        # 发送日志("正在加载记忆者模型...")
        if 模型路径 is None:
            model_dir = tools.search_folder_in("图形AI工具链_github","bge-large-zh-v1___5")  # 自动搜索模型目录
        else:
            model_dir = 模型路径
        if 数据库文件路径 is None:
            数据库路径 = tools.search_file_in("图形AI工具链_github","记忆数据库.db")
        else:
            数据库路径 = 数据库文件路径
        词嵌入 = 词嵌入向量映射(model_dir)
        模型初始化完成 = True
        # 初始化知识库
        kb = 知识库(数据库路径=数据库路径)
        Pub.发送日志("信息","模型加载完成！")
        return True, "初始化成功"
        
    except Exception as e:
        初始化错误信息 = str(e)
        Pub.发送日志("错误",f"初始化错误:{traceback.format_exc()}")
        Pub.发送状态("错误")
        return False, str(e)
# ========== 运行流程 =========
初始化否,信息 = 初始化()
if __name__ == "__main__":
    if 独立运行调试:
        Pub.发送日志("信息", "BGE-记忆者:插件进入独立调试模式")
        Pub.发送状态("就绪")
        
        while True:
            try:
                user_input = input()
                if not user_input:
                    continue
                
                # 独立调试模式直接传字符串
                结果 = 处理(f"{__关键词__}{user_input}", 数据类型="str")
                
                if 结果 is not None:
                    Pub.发送输出(结果)
                Pub.发送状态("就绪 ")
            except KeyboardInterrupt:
                break
            except Exception as e:
                Pub.发送日志("错误", f"运行错误：{traceback.format_exc()}")
                
    else:
        # 插件引擎模式
        if 初始化否:
            Pub.发送日志("信息", "BGE-记忆者:插件已加载")
            Pub.发送状态("就绪")
            
            while True:
                try:
                    行 = sys.stdin.readline()
                    if not 行:
                        break
                    if not 行.strip():
                        continue
                    
                    # ========== 解析输入协议包（统一使用插件公用方法） ==========
                    协议包 = Pub.解析输入协议包(行.strip())
                    if not 协议包:
                        continue
                    # 检查停止命令
                    if Pub.base64解码(行.strip()) == "[命令]停止":
                        Pub.发送日志("信息", "收到停止命令")
                        break
                    
                    协议头信息 = 协议包.get("协议头", {})
                    消息类型 = 协议头信息.get("消息类型", "数据")
                    
                    # ========== 处理历史数据消息 ==========
                    if 消息类型 == "历史":
                        上下文数据 = 协议包.get("协议体", {}).get("上下文数据", {})
                        历史数据 = 上下文数据.get("历史数据", [])
                        Pub.处理历史数据(历史数据)
                        continue
                    
                    # ========== 提取纯数据 ==========
                    数据类型, 数据 = Pub.提取输入数据(协议包)
                    
                    # ========== 调用处理函数 ==========
                    结果 = 处理(数据, 数据类型, 协议头信息)
                    
                    # ========== 发送结果 ==========
                    回调关键词 = Pub.提取回调关键词(协议包,False)
                    if 结果 is not None:
                        Pub.发送输出(结果=结果,呼叫关键词=回调关键词,
                            透传协议包=协议包) # 可选：基于输入包透传修改
                    Pub.发送状态("就绪")
                        
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    Pub.发送日志("错误", traceback.format_exc())
                    
            Pub.发送状态("空闲")
        else: 
            Pub.发送日志("错误", "BGE-记忆者:初始化方法未完成,已停运")
