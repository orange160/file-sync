"""
@File  : helper.py
@Author: lyj
@Create  : 2024/5/30 15:39
@Modify  : 
@Description  : 工具函数
"""
import os
import sys

base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))


def get_resource(path: str) -> str:
    """
    获取资源，通过这个函数获取资源，无论是在打包，还是开发运行，都能获取资源
    """
    return os.path.join(base_path, 'resources', path)