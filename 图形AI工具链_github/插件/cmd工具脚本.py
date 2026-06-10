"""
一个cmd命令执行器
"""
# 外部读取的配置
__名称__ = "cmd"
__版本__ = "2.1.0"
__作者__ = "活火山(人)"
__分类__ = "工具脚本"
__关键词__ = "[cmd]"
__分片策略类型__ = "否"
__简介__ = f"""[开始]->{__名称__}的信息,
名称:“{__名称__}”,
版本:“{__版本__}”,作者:“{__作者__}”,
分类:“{__分类__}”,呼叫关键词:“{__关键词__}”(注意全小写,没有中括号)
介绍:“我是cmd命令终端,并不是角色扮演,你可以通过我来与真实的Win11计算机命令行交互,但是并没有管理员权限
每一次命令执行都是一个新的cmd窗口”<-[结束]"""
__工具介绍__ = [
    {
        "type": "function",
        "function": {
            "name": "cmd", 
            "description": "cmd命令终端,不是角色扮演,与真实的Win11计算机命令行交互,无管理员权限(注意函数名称小写)",
            "parameters": {
                "type": "object",
                "properties": {
                    "操作": {
                        "type": "string",
                        "description": "[新建cmd]:在新建的cmd窗口中执行,[清除cmd]:清除所有创建过的cmd,都是辅助选项(带中括号)",
                        "enum": ["[新建cmd]", "[清除cmd]"],
                        "defult": None
                    },
                    "命令": {
                        "type": "string",
                        "description": "具体命令"
                    }
                },
                "required": ["命令"]
            }
        }
    }
]
清除关键词 = "[清除cmd]"
新建关键词 = "[新建cmd]"
"""关键变量""" 
独立运行调试 = False


import _tools  as tools
import json
import re
import sys
import threading
import os
import traceback
import locale
from typing import List, Dict, Any, Optional, Union
# ===================== 数据库配置 ====================
from datetime import datetime
from _插件公用 import 插件公用, 危险指令校验器 # 指令校验器不需实例化可以直接调用

# 创建公用方法实例
Pub = 插件公用(__名称__,独立运行调试,__关键词__,__版本__,__作者__)
import subprocess
import threading
import time

class 命令执行器:
    def __init__(自身):
        自身.进程列表 = []
        自身.新建窗口锁 = threading.Lock()
        # 获取系统编码
        自身.系统编码 = locale.getpreferredencoding()  # Windows中文系统通常是 'cp936' 或 'gbk'
    
    def 执行命令(self, 命令字符串: str="", 新建窗口: bool = False, 删除窗口: bool = False) -> str:
        """
        执行cmd命令并返回UTF-8字符串结果
        Args:命令字符串: 要执行的命令
            新建窗口: 是否在新cmd窗口执行
            删除窗口: 是否清空所有已创建的cmd窗口  
        Returns:命令执行结果字符串
        """
        if 命令字符串:
            # 如果要求删除窗口
            if 删除窗口:
                self.清空所有窗口()
                return "已清空所有cmd窗口"
            
            # 如果要在新窗口执行
            if 新建窗口 and False:
                with self.新建窗口锁:
                    进程 = self.新建独立窗口执行(命令字符串)
                    self.进程列表.append(进程)
                    return f"已在新窗口启动命令，窗口ID: {len(self.进程列表)}"
            
            # 正常执行（不新建窗口）
            return self.同步执行命令(命令字符串)
        else:
            return None
    
    def 同步执行命令(self, 命令字符串: str) -> str:
        """在当前进程同步执行命令，正确处理中文编码"""
        try:
            # 获取原始字节数据
            结果 = subprocess.run(
                命令字符串,
                shell=True,
                capture_output=True,
                text=False,  # 重要！设置为False获取字节数据
            )
            
            # 解码输出，优先使用系统编码
            def 解码输出(字节数据) -> str:
                if not 字节数据:
                    return ""
                # 如果已经是字符串，直接返回
                if isinstance(字节数据, str):
                    return 字节数据
                # 尝试多种编码
                编码列表 = [self.系统编码, 'gbk', 'cp936', 'utf-8', 'gb2312', 'latin-1']
                for 编码 in 编码列表:
                    try:
                        return 字节数据.decode(编码)
                    except (UnicodeDecodeError, LookupError):
                        continue
                # 如果都失败，用latin-1解码并用替换错误字符
                return 字节数据.decode('latin-1', errors='replace')
            try:
                输出 = 解码输出(结果.stdout)
            except:
                输出 = "有响应"
            错误 = 解码输出(结果.stderr)
            return f"你的命令是:\n{命令字符串}\nCMD结果是:\n{输出.strip()}\n{错误}"
            
        except Exception as 异常:
            return f"你的命令是:\n{命令字符串}\n执行错误:{str(异常)}"

    
    def 新建独立窗口执行(自身, 命令字符串: str) -> subprocess.Popen:
        """在新的cmd窗口中异步执行命令"""
        # Windows下启动新cmd窗口的命令
        if 命令字符串.strip().startswith("python"):
            # 如果是python命令，使用start来保持窗口
            完整命令 = f'start cmd /k "{命令字符串}"'
        else:
            完整命令 = f'start cmd /k "{命令字符串} && echo 命令执行完成 && exit"'
        
        进程 = subprocess.Popen(
            完整命令,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        return 进程
    
    def 清空所有窗口(self) -> int:
        """关闭所有已创建的cmd窗口，返回关闭的窗口数"""
        关闭数量 = 0
        for 进程 in self.进程列表:
            try:
                进程.terminate()
                进程.wait(timeout=2)
                关闭数量 += 1
            except:
                pass
        self.进程列表.clear()
        return 关闭数量
    
    def 获取窗口状态(self) -> str:
        """获取所有窗口状态信息"""
        if not self.进程列表:
            return "没有运行中的cmd窗口"
        
        状态列表 = []
        for 索引, 进程 in enumerate(self.进程列表, 1):
            状态 = "运行中" if 进程.poll() is None else "已结束"
            状态列表.append(f"窗口{索引}: {状态}")
        
        return f"共有 {len(self.进程列表)} 个cmd窗口:\n" + "\n".join(状态列表)

CMD执行器 = 命令执行器()

# ===================== 核心方法：处理（原监听并输出） =====================
def 处理(数据, 数据类型: str = "str", 协议包: dict = {}) -> str:
    Pub.发送状态("运行中")  # 通知主进程开始工作
    """
    处理函数 - 专注于业务逻辑
    传入: 已提取的纯数据（字符串/列表/字典等）
    返回: 处理结果字符串（或None表示不处理）
    """
    global __简介__
    if isinstance(数据, str):
        # ========== 获取呼叫关键词 =========
        回调关键词 = Pub.提取回调关键词(协议包,False)
        Pub.发送日志("调试",f"回调关键词:{str(回调关键词)}")
        # 变量初始化
        清除否 = (清除关键词 in 数据)
        新建否 = (新建关键词 in 数据)
        数据 = 数据.replace(__关键词__, "").replace(清除关键词,"").replace(新建关键词,"")  # 清理文本
        数据 = Pub.移除标记间内容("``","``:\n",数据) # 去除无关前缀
        数据 = 数据.strip()
        合法否, 当前错误命令 = 危险指令校验器.校验(数据)
        忌讳列表 = 危险指令校验器.获取所有危险指令()
        if 合法否:
            结果 = CMD执行器.执行命令(数据, True, 清除否)
        else:
            结果 = f"错误:你的命令中包含:{当前错误命令},\n这些是非法的危险指令:\n{忌讳列表},\n请通知人类你的需求"
        return 结果


# ===================== 初始化方法 =====================
def 初始化(模型路径=None, 数据库文件路径=None):
    """初始化"""
    return True,"yes"

初始化否,text = 初始化()
if __name__ == "__main__":
    if 独立运行调试:
        Pub.发送日志("信息", "CMD插件运行")
        Pub.发送状态("就绪")
        
        while True:
            try:
                user_input = input()
                if not user_input:
                    continue
                
                # 独立调试模式直接传字符串
                结果 = 处理(f"{__关键词__}``人``:\n{user_input}", 数据类型="str")
                
                if 结果 is not None:
                    Pub.发送输出(结果)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                Pub.发送日志("错误", f"运行错误：{traceback.format_exc()}")
                
    else:
        # 插件引擎模式
        if 初始化否:
            Pub.发送日志("信息", "CMD:插件已加载")
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
                        Pub.发送日志("调试","没有协议包")
                        continue
                    # 检查停止命令
                    if Pub.base64解码(行.strip()) == "[命令]停止":
                        Pub.发送日志("信息", "收到停止命令")
                        break
                    
                    协议头信息 = 协议包.get("协议头", {})
                    协议尾信息 = 协议包.get("协议尾", {})
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
                    结果 = 处理(数据, 数据类型, 协议包)
                    # ========== 发送结果 ==========
                    回调关键词 = Pub.提取回调关键词(协议包, False)
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
            Pub.发送日志("错误", "CMD:初始化方法未完成,已停运")
