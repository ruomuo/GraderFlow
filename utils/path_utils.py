#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路径工具模块
处理PyInstaller打包后的路径问题
"""

import os
import sys
from pathlib import Path


def get_app_root_dir():
    """
    获取应用程序根目录
    
    在开发环境中，返回脚本所在目录
    在PyInstaller打包环境中，返回可执行文件所在目录
    
    Returns:
        str: 应用程序根目录路径
    """
    if getattr(sys, 'frozen', False):
        # 打包后的环境
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller打包，返回可执行文件所在目录
            return os.path.dirname(sys.executable)
        else:
            # 其他打包工具
            return os.path.dirname(sys.executable)
    else:
        # 开发环境，返回主脚本所在目录
        # 尝试从调用栈中找到main.py的路径
        import inspect
        frame = inspect.currentframe()
        try:
            while frame:
                filename = frame.f_code.co_filename
                if filename.endswith('main.py') or filename.endswith('config_manager.py'):
                     # If it's main.py, dirname is root.
                     # If config_manager.py is in utils/, dirname is utils, parent is root.
                    if filename.endswith('main.py'):
                        return os.path.dirname(os.path.abspath(filename))
                    elif 'utils' in os.path.dirname(os.path.abspath(filename)):
                        return os.path.dirname(os.path.dirname(os.path.abspath(filename)))
                    return os.path.dirname(os.path.abspath(filename))
                frame = frame.f_back
            
            # 如果找不到，假设utils/path_utils.py在utils下，向上找一级
            current_file = os.path.abspath(__file__)
            if 'utils' in os.path.dirname(current_file):
                 return os.path.dirname(os.path.dirname(current_file))
            return os.getcwd()
        finally:
            del frame

def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径
    优先查找应用程序根目录（支持用户自定义配置）
    如果找不到，且处于打包环境，则查找临时目录（内置默认配置）
    """
    app_root = get_app_root_dir()
    path = os.path.join(app_root, relative_path)
    
    if os.path.exists(path):
        return path
        
    # 如果在打包环境中，尝试从临时目录查找
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        temp_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(temp_path):
            return temp_path
            
    return path

def get_project_root():
    """Alias for get_app_root_dir for semantic clarity"""
    return get_app_root_dir()

def get_config_dir():
    """
    获取配置文件目录 (config/)
    
    Returns:
        str: 配置文件目录的绝对路径
    """
    app_root = get_app_root_dir()
    config_dir = os.path.join(app_root, 'config')
    # 确保目录存在
    os.makedirs(config_dir, exist_ok=True)
    
    return config_dir


def get_answer_config_dir():
    """
    获取答案配置文件目录 (config/answer_config/)
    
    Returns:
        str: 答案配置文件目录的绝对路径
    """
    config_dir = get_config_dir()
    answer_config_dir = os.path.join(config_dir, 'answer_config')
    # 确保目录存在
    os.makedirs(answer_config_dir, exist_ok=True)
    
    return answer_config_dir


def get_config_file_path(filename):
    """
    获取配置文件的完整路径
    
    Args:
        filename (str): 配置文件名或相对路径
        
    Returns:
        str: 配置文件的完整路径
    """
    app_root = get_app_root_dir()
    
    # 如果是绝对路径，直接返回
    if os.path.isabs(filename):
        return filename
        
    # 如果路径以 config 开头，认为是相对于项目根目录的路径
    if filename.startswith('config'):
        return os.path.join(app_root, filename)
        
    # 否则默认在 config/answer_config 目录下
    return os.path.join(get_answer_config_dir(), filename)


def get_app_file_path(filename):
    """
    获取应用程序文件的完整路径
    
    Args:
        filename (str): 文件名
        
    Returns:
        str: 文件的完整路径
    """
    app_root = get_app_root_dir()
    return os.path.join(app_root, filename)


def ensure_dir_exists(path):
    """
    确保目录存在
    
    Args:
        path (str): 目录路径
    """
    if os.path.isfile(path):
        path = os.path.dirname(path)
    
    os.makedirs(path, exist_ok=True)


if __name__ == "__main__":
    # 测试函数
    print("应用程序根目录:", get_app_root_dir())
    print("配置文件目录:", get_config_dir())
    print("客观题答案文件路径:", get_config_file_path('answer_multiple.txt'))
    print("主观题答案文件路径:", get_config_file_path('test_subjective_answer.txt'))
    print("问题类型文件路径:", get_config_file_path('question_types.txt'))
    print("是否为打包环境:", getattr(sys, 'frozen', False))
    if hasattr(sys, '_MEIPASS'):
        print("PyInstaller临时目录:", sys._MEIPASS)