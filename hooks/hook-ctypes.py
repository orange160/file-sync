"""
@File  : hook_ctypes.py
@Author: lyj
@Create  : 2024/4/8 15:04
@Modify  : 
@Description  : 
"""
import os.path

from PyInstaller.utils.hooks import collect_dynamic_libs

from helper import base_path

# 如果DLL位于特定模块中，可以使用collect_dynamic_libs
binaries = collect_dynamic_libs('ctypes')

dll_dir = os.path.join(base_path, 'hooks/dll')
# 或者，如果DLL位于一个特定路径，你可以直接指定这个路径
binaries += [
    (os.path.join(dll_dir, 'ffi.dll'), '.'),
    (os.path.join(dll_dir, 'ffi-7.dll'), '.'),
    (os.path.join(dll_dir, 'ffi-8.dll'), '.')
]

