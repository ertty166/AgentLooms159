"""

"""
# 外部读取的配置
__名称__ = "..."
__版本__ = "2.1.0"
__作者__ = "作者"
__分类__ = "xxxx"
__关键词__ = "[...]"
__分片策略类型__ = "否" # 脚本(输出不分片)/AI(输出可以分片),
__简介__ = f"""[开始]->{__名称__}的信息,
名称:“{__名称__}”,
版本:“{__版本__}”,作者:“{__作者__}”,
分类:“{__分类__}”,呼叫关键词:“{__关键词__}”
介绍:“.....”<-[结束]"""
__工具介绍__ = [
    {
        "type": "function",
        "function": {
            "name": "memory_operator",  # 工具名称，模型调用时会用到
            "description": "",  # 告诉模型这个工具是干嘛的
            "parameters": {  # 参数定义主体
                "type": "object",  # 固定格式，表示参数是一个对象
                "properties": {  # 具体的参数列表
                    "操作": {  # 对应你要求的“操作”字段
                        "type": "string",  # 类型是字符串
                        "description": "",  # 明确告诉模型只能选这三个
                        "enum": ["1", "2", "3"]  # 【关键】枚举限制，强制模型只能输出这三个值之一
                    },
                    "文本": {  # 对应你要求的“文本”字段
                        "type": "string",  # 类型是字符串
                        "description": ""  # 解释文本在不同操作下的用途
                    }
                },
                "required": ["操作", "文本"]  # 指定这两个字段是必填的，防止模型漏传
            }
        }
    }
]
"""关键变量""" 
独立运行调试 = False
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
from _插件公用 import 插件公用

# 创建公用方法实例
Pub = 插件公用(__名称__,独立运行调试,__关键词__,__版本__,__作者__)

# ===================== 核心方法：处理（原监听并输出） =====================
def 处理(数据, 数据类型: str = "str", 协议头: dict = {}) -> str:
    """
    处理函数 - 专注于业务逻辑
    传入: 已提取的纯数据（字符串/列表/字典等）
    返回: 处理结果字符串（或None表示不处理）
    """
    Pub.发送状态("运行中")  # 通知主进程开始工作
    # ========== 获取呼叫关键词 =========
    回调关键词 = 协议头.get("插件信息",{}).get("呼叫关键词",None)
    Pub.发送日志("调试",f"回调关键词:{str(回调关键词)}")
    # ========== 关键词检查 ==========
    if __关键词__ not in str(数据):
        return None  # 不包含关键词，不处理
    # 变量初始化
    数据 = 数据.replace(__关键词__)  # 清理文本
    数据 = Pub.移除标记间内容("``","``:",数据) # 清理文本

    # ============这里是你的业务逻辑返回结果向外发送的地方,你不需要管理协议包只需要保证业务结果返回的是字符串 =======
    结果 = 111
    return 结果


# ===================== 初始化方法 =====================
def 初始化(模型路径=None, 数据库文件路径=None):
    """初始化"""
    return True,"yes"


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
                Pub.发送日志("错误", f"思想者插件:读取写入并缓存时出现错误:\n{traceback.format_exc()}")
    t2 = threading.Thread(target=缓存线程, daemon=True)
    t2.start()

初始化否,text = 初始化()
if __name__ == "__main__":
    if 独立运行调试:
        Pub.发送日志("信息",f"{__名称__}插件运行")
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
            Pub.发送日志("信息", f"{__名称__}:插件已加载")
            Pub.发送状态("就绪")
            
            开始缓存()
            开始处理()
                    
            Pub.发送状态("空闲")
        else: 
            Pub.发送日志("错误", f"{__名称__}:初始化方法未完成,已停运")