"""
deepseek v4 API
"""

# 你的APIKEY
API_KEY = None



模型名 = "deepseek-v4-pro"
# 外部读取的配置
__名称__ = "小鲸鱼"
__版本__ = "1.0.0"
__作者__ = "活火山MOE"
__分类__ = "API智能体"
__关键词__ = "[小鲸鱼]"
__分片策略类型__ = "否" # 脚本(输出不分片)/AI(输出可以分片),
__简介__ = f"""[开始]->{__名称__}的信息,
名称:“{__名称__}”,
版本:“{__版本__}”,作者:“{__作者__}”,
分类:“{__分类__}”,呼叫关键词:“{__关键词__}”
介绍:“这是联网的deepseek-v4-Pro智能体,参数量较大”<-[结束]"""
自我定义 = f"你是'{__名称__}',思维辩证,输出发散且自我质疑,中文回答,你具有强大的自主性,遇到难题时会冷静分析并逻辑清晰的规划步骤,但你不能质疑人类,执行任务三思而后行,先想办法获得有效信息,再去规划,最后再执行"
__根目录__ = "图形AI工具链_github"
清空历史关键词 = "[@清空历史]"
压缩历史关键词 = "[@压缩历史]"
__工具介绍__ = [
    {
        "type": "function",
        "function": {
            "name": "小鲸鱼", 
            "description": "调用deepseek-v4-Pro网络API,思维辩证,发散,且自我质疑,纯文本类大模型,可以正常与其交流",
            "parameters": {
                "type": "object",
                "properties": {
                    "文本": {
                        "type": "string",
                        "description": "向对方发送的文本内容"
                    }
                },
                "required": ["文本"]
            }
        }
    }
]
"""关键变量""" 
独立运行调试 = True



import _tools as tools
import json
import re
import sys
import threading
import queue
import time
import traceback
from typing import List, Dict, Any, Optional, Union
# ===================== 数据库配置 ====================
import numpy as np
from datetime import datetime
from openai import OpenAI
import os
from _插件公用 import 插件公用

# 创建公用方法实例
Pub = 插件公用(__名称__,独立运行调试,__关键词__,__版本__,__作者__)

# ==================== 全局变量初始化 =======================
AI上下文 = None
工具调用管理 = None
# ==================== 上下文管理器（核心封装） ====================
class 带压缩上下文管理器:
    def __init__(self, 系统提示=None, 上下文长度: int = 12800, 压缩文本长度: int = 4096, 历史对话保存文件夹:str|None = None):
        """
        初始化上下文管理器
        :param 系统提示: 初始系统角色设定
        :param 上下文长度: 总字数上限
        :param 压缩文本长度: 压缩后的目标长度
        """
        self.总字数 = 0
        self.系统提示 = 系统提示
        self.历史消息 = []
        self._历史消息锁 = threading.RLock()
        self.上下文长度限制 = 上下文长度
        self.压缩目标长度 = 压缩文本长度
        self.下游工具介绍列表 = []
        self.环境介绍路径 = tools.search_file_in(__根目录__,"环境简介-给AI.txt")
        # 初始化历史：系统提示固定保留在最顶部
        self.历史对话保存路径 = os.path.join(tools.search_folder_in(__根目录__,"deepseek文本类") if 历史对话保存文件夹 is None else 历史对话保存文件夹,"小鲸鱼历史对话.json")
        # 尝试加载历史对话
        self.历史加载成功否 = self._加载历史对话()
        # 计算初始总字数
        self.更新历史长度()

    def 初始化历史(self):
        """自动初始化:一个系统提示作为系统传入;一个介绍文档作为用户传入"""
        with self._历史消息锁:
            self.系统身份重置(self.系统提示)
            self.添加环境介绍()

    def 更新历史长度(self):
        """重新计算历史对话记载的总长度"""
        长度 = 0
        for 信息字典 in self.历史消息:
            文本 = 信息字典.get("content", "")
            长度 += len(文本)
        self.总字数 = 长度

    def 添加环境介绍(self):
        """如果没有成功加载历史消息使用的是新消息那么会在索引 1 的地方添加环境介绍"""
        with open(self.环境介绍路径,"r",encoding="utf-8") as f:
            环境介绍 = f.read()
        if not self.历史加载成功否:
            with self._历史消息锁:
                self.用户说(f"``管理``:\n{环境介绍}\n{Pub.AI_获取下游信息()}")
                响应结果 = self.deepseek()
                self.AI说(响应结果)
        else:
            return

    def 清空历史(self):
        with self._历史消息锁:
            self.历史消息 = [{"role": "system", "content": self.系统提示}] if self.系统提示 else []
            self.总字数 = len(self.历史消息[0]["content"]) if self.历史消息 else 0

    def _加载历史对话(self):
        """【私有方法】初始化时尝试从文件加载历史对话"""
        if os.path.exists(self.历史对话保存路径):
            try:
                with open(self.历史对话保存路径, 'r', encoding='utf-8') as f:
                    加载的数据 = json.load(f)
                # 验证数据格式
                if isinstance(加载的数据, list) and len(加载的数据) > 1:
                    # 如果当前有系统提示，保留它；否则使用加载的第一个系统消息
                    with self._历史消息锁:
                        if self.系统提示:
                            # 过滤掉加载数据中的系统消息，保留当前系统提示
                            过滤后的消息 = [msg for msg in 加载的数据 if msg.get("role") != "system"]
                            self.添加系统身份(self.系统提示)
                            self.历史消息.extend(过滤后的消息)
                        else:
                            self.历史消息 = 加载的数据
                    Pub.发送日志("信息",f"成功加载历史对话，共 {len(self.历史消息)} 条消息")
                    return True
                else:
                    Pub.发送日志("信息","历史对话文件格式不正确，使用新历史")
                    return False
            except Exception as e:
                Pub.发送日志("警告",f"加载历史对话时出错: {e}，使用空历史")
                return False
        else:
            Pub.发送日志("信息",f"未找到历史对话文件: {self.历史对话保存路径}，将创建新文件")
            return False

    def 保存历史对话(self):
        """将当前历史对话保存到JSON文件"""
        try:
            # 确保目录存在
            保存目录 = os.path.dirname(self.历史对话保存路径)
            if 保存目录 and not os.path.exists(保存目录):
                os.makedirs(保存目录, exist_ok=True)
            # 写入JSON文件（使用indent美化格式，ensure_ascii=False支持中文）
            with open(self.历史对话保存路径, 'w', encoding='utf-8') as f:
                json.dump(self.历史消息, f, ensure_ascii=False, indent=2)
            Pub.发送日志("信息",f"历史对话已保存到: {self.历史对话保存路径}")
            return True
        except PermissionError:
            Pub.发送日志("错误",f"保存失败：没有权限写入文件 {self.历史对话保存路径}")
            return False
        except Exception as e:
            Pub.发送日志("错误",f"保存历史对话时出错: {e}")
            return False

    def _压缩上下文(self):
        """私有方法：超出长度限制时，调用ollama压缩整个对话历史"""
        # 构建压缩指令：让AI总结/压缩完整对话
        # 重置历史：固定系统提示 + 压缩后的对话 + 清空字数统计
        self.系统身份重置(self.系统提示)
        self.添加环境介绍()
        压缩指令 = self.历史消息.copy()
        压缩指令.append({
            "role": "user",
            "content": f"请将以上所有对话内容压缩至{self.压缩目标长度}字以内，保留核心信息，不要添加额外内容"
        })
        # 调用ollama cilent模式压缩
        压缩响应 = self.deepseek()
        压缩结果 = 压缩响应["message"]["content"]
        self.AI说(f"历史对话总结：{压缩结果}")
    
    def 压缩历史(self):
        """自动压缩AI的上下文,保留系统提示,保留环境介绍"""
        self._压缩上下文()

    def 添加系统身份(self, 系统提示:str):
        """仅添加系统提示,不添加AI回答"""
        if not 系统提示:
            return None
        else:
            with self._历史消息锁:
                self.历史消息 = [{"role": "system", "content": 系统提示}]

    def 系统身份重置(self, 系统提示:str=None):
        """按照系统提示将历史消息初始化为一个只有系统提示所在字典的列表,并添加AI回答"""
        if not 系统提示:
            return None
        else:
            with self._历史消息锁:
                self.历史消息 = [{"role": "system", "content": 系统提示}]
                self.保存历史对话()
                身份规范响应 = self.deepseek()
                回答 = 身份规范响应["message"]["content"]
                self.AI说(回答)
                self.更新历史长度()


    def 用户说(self, 内容: str,压缩上下文:bool=False):
        """
        将用户输入封装并添加到历史消息
        :param 内容: 用户发送的文本
        """
        消息 = {"role": "user", "content": 内容}
        with self._历史消息锁:
            self.历史消息.append(消息)
            self.总字数 += len(内容)
        if 压缩上下文:
            self.自动压缩上下文()
        self.保存历史对话()

    def AI说(self, 内容: str, 压缩上下文: bool=False):
        """将AI回复封装并添加到历史消息
            :param 内容: AI生成的文本"""
        消息 = {"role": "assistant", "content": 内容}
        with self._历史消息锁:
            self.历史消息.append(消息)
            self.总字数 += len(内容)
        if 压缩上下文:
            self.自动压缩上下文()
        self.保存历史对话()

    def 自动压缩上下文(self):
        """自动判断上下文是否超出限制,如有,则压缩上下文"""
        if self.总字数 >= self.上下文长度限制:
            self._压缩上下文()
            
    def 对话接口(self, 用户输入: str) -> str:
        """
        【唯一对外接口】接收用户输入，返回AI回答，自动管理上下文
        :param 用户输入: 用户发送的文本
        :return: AI回复文本
        """
        # 1. 添加用户消息（使用新方法）
        self.用户说(用户输入)
        # Pub.发送日志("调试", f"思想者模型历史消息:\n{self.历史消息}")
        try:
            # 3. 请求AI生成回答
            AI回复 = self.deepseek()
            Pub.发送日志("调试", f"对话接口(),思想者输出:{AI回复 if AI回复 else '#NoNe'}")
        except Exception as e:
            Pub.发送日志("警告",f"对话接口(),思想者模型回复错误:\n{traceback.format_exc()}")
        # 4. 添加AI回复到上下文（使用新方法）
        self.AI说(AI回复)
        # 5. 再次检查并压缩
        self.自动压缩上下文()
        self.保存历史对话()
        return AI回复

    def deepseek(self):
        回应 = client.chat.completions.create(
            model=模型名,
            messages=self.历史消息,
            stream=False,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}}
        )
        return 回应.choices[0].message.content

class 工具调用管理器:
    def __init__(self):
        self.下游工具介绍列表 = []
        self.下游工具呼叫关键词列表 = []
        self.初始化下游工具调用相关()

    def 初始化下游工具调用相关(self):
        self.下游工具介绍列表 = Pub.获取下游工具介绍列表()
        if self.下游工具介绍列表:
            for 典 in self.下游工具介绍列表:
                函数典 = 典.get("function",{})
                呼叫关键词 = 函数典.get("name",None)
                if 呼叫关键词:
                    self.下游工具呼叫关键词列表.append(呼叫关键词)

    def 处理工具文本拼接(self, 模型响应: dict) -> str:
        """传入模型完整响应自动提取其中文本和工具调用并拼接成反引号工具调用块格式"""
        默认文本 = "->模型未输出文本<-"
        message = 模型响应["message"]
        模型文本输出 = message.get("content", 默认文本)
        
        if 'tool_calls' in message and message['tool_calls']:
            for tool_call in message['tool_calls']:
                呼叫关键词 = tool_call['function']['name']
                参数组 = tool_call['function']['arguments']  # arguments是dict
                
                # 【修改点】：遍历参数字典，提取每个参数的值并首尾相接拼接
                if isinstance(参数组, dict):
                    参数字典 = 参数组
                elif isinstance(参数组, str):
                    try:
                        参数字典 = json.loads(参数组)
                    except:
                        Pub.发送日志("错误",f"工具调用输出解析失败:{traceback.format_exc()}")
                else:
                    参数字典 = {"no":""}
                    Pub.发送日志("错误",f"工具调用输出解析失败:不是dict,也不是str")
                # 遍历字典所有值，按顺序拼接成纯字符串
                参数字符串 = ""
                for 参数值 in 参数字典.values():
                    参数字符串 += str(参数值)
                # 判断是否合法，并拼接参数
                if 呼叫关键词 in self.下游工具呼叫关键词列表:
                    模型文本输出 = 模型文本输出 + f"""```{呼叫关键词}{参数字符串}```"""
        return 模型文本输出


# 主要调用方法
def 处理(数据, 数据类型: str = "str", 协议头: dict = {}) -> str:
    """
    处理函数 - 专注于业务逻辑
    传入: 已提取的纯数据（字符串/列表/字典等）
    返回: 处理结果字符串（或None表示不处理）
    """
    Pub.发送状态("运行中")
    if isinstance (数据, str):
        # 清空历史特殊处理
        if 压缩历史关键词 in 数据:
            AI上下文.压缩历史()
            return None
        elif 清空历史关键词 in 数据:
            AI上下文.清空历史()
            return None  # 已通过状态通知，无需返回内容
        try:
            # 核心：仅调用上下文管理器对外对话接口
            数据 = 数据.removeprefix(__关键词__) # 清理关键词
            AI回复 = AI上下文.对话接口(数据)
            return AI回复
        except Exception as e:
            Pub.发送日志("错误", f"请求失败: {str(e)}")
            Pub.发送状态("错误")
            return None


def 开始处理(): # 20260425
    """创建一个处理线程,从缓存队列中拿取包并且处理"""
    def 处理线程():
        while True:
            if Pub.能否开工:
                try:
                    try:
                        协议包 = Pub.接收缓存队列.get_nowait()
                    except queue.Empty:
                        协议包 = None
                    if not 协议包 or not isinstance(协议包, dict):
                        time.sleep(0.1)
                        continue
                    协议头信息 = 协议包.get("协议头", {})
                    消息类型 = Pub.获取字段值(协议包, "协议头.消息类型")
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
                    # ========== 发送结果（使用分片发送） ==========
                    回调关键词 = Pub.提取回调关键词(协议包, False)
                    if 结果 is not None:
                        Pub.发送输出(结果=结果,呼叫关键词=None,
                                透传协议包=协议包) # 可选：基于输入包透传修改
                    Pub.发送状态("就绪")
                except Exception as e:
                    Pub.发送日志("错误", f"处理流程错误:{traceback.format_exc()}")
                    Pub.发送状态("错误")
            else:
                time.sleep(0.1)
    t1 = threading.Thread(target=处理线程, daemon=True)
    t1.start()
    t1.join() # 这会阻塞主线程直到处理线程退出结束

def 开始缓存():# 20260425
    """创建一个缓存线程从stdin读取传进来的协议包并且缓存它,并且它负责处理那些非业务逻辑,例如历史或者下游信息更新"""
    def 缓存线程():
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
                消息类型 = Pub.获取字段值(协议包, "协议头.消息类型")

                if 消息类型 == "下游信息": # 20260425 # 判断并更新开工标识
                    try:
                        # Pub.发送日志("调试", "test已接收到下游信息")
                        Pub.能否开工 = True
                        Pub.发送日志("调试", "test能否开工更新为True")
                    except Exception as e:
                        Pub.发送日志("错误", f"更新下游信息时错误:{traceback.format_exc()}")
                        Pub.发送状态("错误")
                    continue
                # 放入队列等待处理线程处理
                Pub.接收缓存队列.put(协议包)

            except Exception as e:
                Pub.发送日志("错误", f"deepseek插件:读取写入并缓存时出现错误:\n{traceback.format_exc()}")
    t2 = threading.Thread(target=缓存线程, daemon=True)
    t2.start()

def 初始化():
    global AI上下文, 工具调用管理, client
    client = OpenAI(  api_key=API_KEY,  base_url="https://api.deepseek.com")
    # 初始化全局上下文实例
    AI上下文 = 带压缩上下文管理器(系统提示=自我定义,上下文长度=128000,压缩文本长度=2048)
    工具调用管理 = 工具调用管理器()

初始化()
# ========== 运行流程 =========
if __name__ == "__main__":
    if 独立运行调试:
        Pub.发送日志("信息", "deepseek插件进入独立调试模式")
        Pub.发送状态("就绪")
        
        while True:
            try:
                user_input = input()
                if not user_input:
                    continue
                # 独立调试模式直接传字符串
                结果 = 处理(f"{__关键词__}{user_input}", 数据类型="str")
                # ========== 发送结果（使用分片发送） ==========
                回调关键词 = "这是模拟回调关键词========="
                传入消息标识 = "这是模拟消息标识=========="
                if 结果 is not None:
                    Pub.发送输出(结果, 回调关键词, 传入消息标识)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                Pub.发送日志("错误", f"运行错误：{traceback.format_exc()}")
                
    else:
        # 插件引擎模式
        Pub.发送日志("信息", "deepseek插件已加载")
        Pub.发送状态("就绪")
        开始缓存()
        开始处理()
        Pub.发送状态("空闲")
