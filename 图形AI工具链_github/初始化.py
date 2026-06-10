import modelscope
import _tools as tools
import os
#模型下载 modeldownload
from modelscope import snapshot_download
import _tools as tools
当前根目录 = tools.get_now_path()
数据根目录 = tools.search_folder_in(1,"数据",build=True,BuildPath=当前根目录)
模型权重根目录 = tools.search_folder_in(1,"模型权重",build=True,BuildPath=数据根目录)
model_dir = snapshot_download('BAAI/bge-large-zh-v1.5',cache_dir=模型权重根目录)
# model_dir = snapshot_download('Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4',cache_dir=模型权重根目录)