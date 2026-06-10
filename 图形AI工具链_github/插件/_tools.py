import os
import json
from typing import Optional
import socket
import threading
import time
import subprocess
import re
import random
import base64
import math


根目录名称 = ""
#此文件包含以下功能:
"""获取当前文件或当前上一级目录绝对路径
   支持遍历查找文件或文件夹
   还有基于socket开发的扫描工具
   还有JSONL过滤工具"""
def 随机起名(名首='W',查重集:set=None):
    """实现了一个自动查重起名器"""
    name = 名首+str(random.randint(0,9999999999999999999999999999))
    if 查重集:
        查重集 = set(查重集)
        while name in 查重集:
            name = 名首+str(random.randint(0,9999999999999999999999999999))
    return name
def get_now_path(type: str = "folder") -> Optional[str]:
    """获取当前文件或所在文件夹的路径"""
    try:
        if type == "folder":
            return os.path.dirname(os.path.abspath(__file__))
        elif type == "00file":
            return os.path.abspath(__file__)
        else:
            print("方法'get_now_path()'错误：需传入'folder'或'file'")
            return None
    except Exception as e:
        print(f"路径获取失败：{str(e)}")
        return None

def creat_increament_file(target_folder_path,file_start_end_list={None},file_frount_name=None):
    for i in range(file_start_end_list["start"],file_start_end_list["end"]):
        if file_frount_name:
            filename = f"{file_frount_name}-{i}"
        else:
            filename = f"{i}"
        filepath = os.path.join(target_folder_path,filename)
        with open(filepath,"w",encoding="utf-8") as f:
            pass

def search_folder_in(upto: int|str, foldername: Optional[str] = None, prompt: int = 0, build=False) -> Optional[str]:
    """向上查找指定文件夹"""
    if foldername is None:
        if prompt == 1:
            print("错误：必须提供foldername参数")
        return None

    s_root_path = get_now_path("00file")
    if not s_root_path:
        print("获取当前文件目录失败,已返回")
        return None

    if prompt == 1:
        print(f"""提示：
- upto=1 表示当前文件的上一级文件夹
- 每增加1，向上多跳转一次目录
- 关闭提示可将prompt设为0
- 当前路径：{s_root_path}""")

    try:
        # 如果 upto 是字符串，先计算需要跳转的次数
        if isinstance(upto, str):
            目标文件夹 = upto
            当前路径_norm = s_root_path.replace("\\", "/").replace("//", "/").rstrip("/")
            名称列表 = [part for part in 当前路径_norm.split("/") if part]
            
            # 查找目标文件夹并计算跳转次数
            跳转次数 = None
            for i, 名称 in enumerate(reversed(名称列表)):
                if 名称 == 目标文件夹:
                    跳转次数 = i
                    break
            
            if 跳转次数 is None:
                if prompt == 1:
                    print(f"错误：未找到文件夹 '{目标文件夹}'")
                return None
            
            # 使用计算出的跳转次数
            upto = 跳转次数
        
        # 向上跳转指定层级
        for _ in range(upto):
            s_root_path = os.path.dirname(s_root_path)
        
        if prompt == 1:
            print(f"跳转后的根目录：{s_root_path}")
        
        # 递归查找文件夹
        for dirpath, dirnames, _ in os.walk(s_root_path):
            if foldername in dirnames:
                folder_path = os.path.join(dirpath, foldername)
                if prompt == 1:
                    print(f"找到文件夹：{folder_path}")
                return folder_path
        
        if build:
            # 在目标位置创建文件夹
            depend_dir = os.path.join(s_root_path, foldername)
            os.makedirs(depend_dir, exist_ok=True)
            folder_path = depend_dir
            if prompt == 1:
                print(f"创建文件夹：{folder_path}")
            return folder_path
        else:
            if prompt == 1:
                print(f"未找到文件夹{foldername},且build参数是False,将不会创建目标文件夹")
            return None
    except Exception as e:
        print(f"文件夹查找失败：{str(e)}")
        return None

def search_file_in(upto: int|str = 1, filename: Optional[str] = None, prompt: int = 0, build=False) -> Optional[str]:
    """向上查找指定文件，未找到则在跳转后的根目录创建"""
    if filename is None:
        if prompt == 1:
            print("错误：必须提供filename参数")
        return None

    s_root_path = get_now_path("00file")
    if not s_root_path:
        return None

    if prompt == 1:
        print(f"""提示：
- upto=1 表示当前文件的上一级文件夹
- 每增加1，向上多跳转一次目录
- 关闭提示可将prompt设为0
- 当前tools.py路径：{s_root_path}""")

    try:
        # 如果 upto 是字符串，先计算需要跳转的次数
        if isinstance(upto, str):
            目标文件夹 = upto
            当前路径_norm = s_root_path.replace("\\", "/").replace("//", "/").rstrip("/")
            名称列表 = [part for part in 当前路径_norm.split("/") if part]
            
            跳转次数 = None
            for i, 名称 in enumerate(reversed(名称列表)):
                if 名称 == 目标文件夹:
                    跳转次数 = i
                    break
            
            if 跳转次数 is None:
                if prompt == 1:
                    print(f"错误：未找到文件夹 '{目标文件夹}'")
                return None
            
            upto = 跳转次数
        
        # 向上跳转指定层级 ✅ 关键步骤
        for _ in range(upto):
            s_root_path = os.path.dirname(s_root_path)
        
        if prompt == 1:
            print(f"跳转后的根目录：{s_root_path}")
        
        # 递归查找文件
        for dirpath, _, filenames in os.walk(s_root_path):
            if filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if prompt == 1:
                    print(f"找到文件：{file_path}")
                return file_path
        
        if build:
            # ✅ 修复：在跳转后的根目录直接创建文件（不再强制 Depend 子目录）
            file_path = os.path.join(s_root_path, filename)
            # 确保目录存在（虽然 s_root_path 应该已存在）
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(filename) else s_root_path, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                pass  # 创建空文件
            
            if prompt == 1:
                print(f"创建文件：{file_path}")
            return file_path
        else:
            if prompt == 1:
                print(f"未找到文件{filename},且build参数是False,将不会创建目标文件")
            return None   
    except Exception as e:
        print(f"文件查找/创建失败：{str(e)}")
        return None



def Jsonl_filter(towhat_dict: dict, tpath: Optional[str] = None) -> str:
    """过滤JSONL文件，按目标字典补全键值对（修复键值匹配逻辑）"""
    if tpath is None:
        raise ValueError("请提供目标JSONL文件的绝对路径")
    if not os.path.exists(tpath):
        raise FileNotFoundError(f"文件不存在：{tpath}")
    dir_path, file = os.path.split(tpath)
    filename, ext = os.path.splitext(file)
    output_path = os.path.join(dir_path, f"{filename}-F{ext}")
    with open(tpath, "r", encoding="utf-8") as infile, \
         open(output_path, "w", encoding="utf-8") as outfile:
        line_num = 0
        for line in infile:
            line_num += 1
            try:
                datadic = json.loads(line.strip())
                if not isinstance(datadic, dict):
                    raise ValueError("行内容不是字典格式")
                new_dict = {}
                # 修复：通过键名匹配而非索引匹配
                for target_key, default_value in towhat_dict.items():
                    # 优先使用输入数据中的对应键值，否则用默认值
                    new_dict[target_key] = datadic.get(target_key, default_value)
                outfile.write(json.dumps(new_dict, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"处理第{line_num}行出错：{str(e)}")
                continue
    print(f"处理完成，输出文件：{output_path}")
    return output_path


def base64编码(文本字符串: str) -> str:
    """传入任意文本字符串（含中文/换行/特殊字符），返回Base64编码后的字符串"""
    字节数据 = 文本字符串.encode("utf-8")
    base64字节 = base64.b64encode(字节数据)
    return base64字节.decode("utf-8")
def base64解码(base64字符串: str) -> str:
    """传入Base64编码的字符串形式，返回解码后的原始文本字符串"""
    try:
        base64字节 = base64字符串.encode("utf-8")
        原始字节 = base64.b64decode(base64字节)
        return 原始字节.decode("utf-8")
    except Exception as e:
        return f"解码失败：{str(e)}"

def 线性傅里叶拟合(点列表):
    """
    对 [0, 2π) 上等间距分布的偶数个点，构造三角多项式精确插值。
    参数:
        点列表: [(x0, y0), (x1, y1), ...]  元组列表
    返回:
        插值函数 f(x)，输入任意 x 返回插值结果,注意它返回的是函数实例

    异常:
        参数非法时抛出 ValueError
    """
    # ========== 防御性校验 ==========
    # 1. 检查列表非空
    if not 点列表:
        raise ValueError("点列表不能为空，至少需要提供 2 个点")
    # 2. 检查每个元素都是二元元组
    for 索引, 点 in enumerate(点列表):
        if not isinstance(点, (tuple, list)) or len(点) != 2:
            raise ValueError(f"第 {索引} 个元素必须是长度为 2 的元组或列表，当前为: {点}")
        if not all(isinstance(值, (int, float)) for 值 in 点):
            raise ValueError(f"第 {索引} 个元素的坐标必须是数值类型，当前为: {点}")
    # 3. 检查点的数量为偶数
    点数 = len(点列表)
    if 点数 % 2 != 0:
        raise ValueError(f"点的数量必须为偶数，当前为 {点数} 个（奇数）")
    # 4. 按 x 坐标排序
    排序后的点 = sorted(点列表, key=lambda 点: 点[0])
    
    # 5. 提取 x 和 y 坐标
    x坐标列表 = [点[0] for 点 in 排序后的点]
    y坐标列表 = [点[1] for 点 in 排序后的点]
    
    # 6. 检查 x 坐标在 [0, 2π) 范围内
    for 索引, x值 in enumerate(x坐标列表):
        if not (0 <= x值 < 2 * math.pi):
            raise ValueError(
                f"第 {索引} 个点的 x 坐标 {x值} 超出 [0, 2π) 范围，"
                f"有效范围是 [0, {2*math.pi:.6f})"
            )
    
    # 7. 检查 x 坐标是否等间距
    间隔列表 = []
    for 索引 in range(点数 - 1):
        间隔 = x坐标列表[索引 + 1] - x坐标列表[索引]
        间隔列表.append(间隔)
    
    # 最后一个间隔：从最后一个点到 2π 应该等于第一个间隔（周期性）
    末尾间隔 = 2 * math.pi - x坐标列表[-1]
    间隔列表.append(末尾间隔)
    
    平均间隔 = sum(间隔列表) / len(间隔列表)
    最大偏差 = max(abs(间隔 - 平均间隔) for 间隔 in 间隔列表)
    允许误差 = 平均间隔 * 1e-6
    
    if 最大偏差 > 允许误差:
        raise ValueError(
            f"x 坐标不是等间距分布。相邻间隔为: {[f'{间隔:.6f}' for 间隔 in 间隔列表]}, "
            f"平均间隔为 {平均间隔:.6f}，最大偏差 {最大偏差:.2e} 超过允许误差 {允许误差:.2e}"
        )
    
    # 8. 检查第一个点是否接近 0
    if x坐标列表[0] > 允许误差:
        raise ValueError(
            f"第一个点的 x 坐标 {x坐标列表[0]} 应该接近 0，"
            f"等间距分布应从 0 开始"
        )
    
    # ========== 计算傅里叶系数 ==========
    
    半点数 = 点数 // 2
    
    余弦系数列表 = []
    正弦系数列表 = []
    
    for 频率 in range(半点数 + 1):
        余弦累加 = 0.0
        正弦累加 = 0.0
        for 序号, y值 in enumerate(y坐标列表):
            角度 = 2 * math.pi * 频率 * 序号 / 点数
            余弦累加 += y值 * math.cos(角度)
            正弦累加 += y值 * math.sin(角度)
        
        余弦累加 *= (2.0 / 点数)
        正弦累加 *= (2.0 / 点数)
        
        余弦系数列表.append(余弦累加)
        正弦系数列表.append(正弦累加)
    
    # 修正边界系数
    余弦系数列表[0] /= 2.0
    余弦系数列表[半点数] /= 2.0
    # ========== 构造插值函数 ==========
    def 插值函数(输入x):
        结果 = 余弦系数列表[0]
        
        for 频率 in range(1, 半点数 + 1):
            结果 += 余弦系数列表[频率] * math.cos(频率 * 输入x)
            if not (点数 % 2 == 0 and 频率 == 半点数):
                结果 += 正弦系数列表[频率] * math.sin(频率 * 输入x)
        return 结果
    return 插值函数
