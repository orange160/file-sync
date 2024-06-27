"""
@File  : file_compare.py
@Author: lyj
@Create  : 2024/6/26 15:23
@Modify  : 
@Description  : 文件比较线程
"""
import hashlib
import os
import posixpath
import stat

import paramiko
from PyQt6.QtCore import QThread, pyqtSignal


class FolderComparatorThread(QThread):
    log_signal = pyqtSignal(str)
    stop_signal = pyqtSignal()
    data_signal = pyqtSignal(dict)

    def __init__(self, server_name, flag, ignore_folders, ignore_file_types, changed_files,
                 hostname, port, username,
                 key_file_path=None, password=None, local_folder=None,
                 remote_folder=None):
        """
        初始化 FolderComparator 对象。

        :param server_name: 服务器名称
        :param flag: 操作标志
        :param hostname: 远程服务器的主机名或IP地址。
        :param port: 远程服务器的端口号。
        :param username: 用于连接远程服务器的用户名。
        :param key_file_path: SSH私钥文件的路径（可选）。
        :param password: 用户密码（可选）。
        :param local_folder: 本地文件夹的路径。
        :param remote_folder: 远程文件夹的路径。
        """
        super(FolderComparatorThread, self).__init__()

        self.server_name = server_name
        self.flag = flag
        self.changed_files = changed_files
        self.ignore_folders = ignore_folders
        self.ignore_file_types = ignore_file_types

        self.hostname = hostname
        self.port = port
        self.username = username
        self.key_file_path = key_file_path
        self.password = password
        self.sftp = None
        self.ssh = None
        self.transport = None
        self.local_folder = local_folder
        self.remote_folder = remote_folder

    def connect(self):
        """
        连接到远程服务器。
        """
        try:
            self.transport = paramiko.Transport((self.hostname, self.port))
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.key_file_path:
                key = paramiko.RSAKey.from_private_key_file(self.key_file_path)
                self.transport.connect(username=self.username, pkey=key)
                self.ssh.connect(self.hostname, port=self.port, username=self.username, pkey=key)
            elif self.password:
                self.transport.connect(username=self.username, password=self.password)
                self.ssh.connect(self.hostname, port=self.port, username=self.username, password=self.password)
            else:
                self.stop_signal.emit()
                raise ValueError("请配置密码/密钥")
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
            self.log_emit(f"连接服务器成功")
        except Exception as e:
            self.log_emit(f"连接服务器失败: {e}")
            self.stop_signal.emit()
            raise

    def disconnect(self):
        """
        断开与远程服务器的连接。
        """
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        if self.transport:
            self.transport.close()

    def log_emit(self, msg):
        clean_msg = msg.replace(self.remote_folder, '').replace(self.local_folder, '').replace('\\', '/')
        self.log_signal.emit(f'{self.server_name}, {clean_msg}')

    def execute_command(self, command):
        """
        通过SSH执行命令
        :param command: 要执行的命令
        :return: 命令的输出结果
        """
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()

            if error:
                self.log_emit(f"命令执行错误: {error}")

            return output
        except Exception as e:
            self.log_emit(f"命令执行失败: {e}")
            return None

    def get_md5(self, file_path):
        """
        计算本地文件的MD5哈希值。

        :param file_path: 本地文件的路径。
        :return: 文件的MD5哈希值。
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.log_emit(f"Failed to calculate MD5 for {file_path}: {e}")
            self.stop_signal.emit()
            raise

    def get_remote_md5(self, file_path, use_command=True):
        """
       计算远程文件的MD5哈希值。

       :param file_path: 远程文件的路径。
       :param use_command: True通过SSH使用命令获取md5,False 读取远程文件计算md5
       :return: 文件的MD5哈希值。
       """
        if use_command:
            command = f"md5sum {file_path}"
            result = self.execute_command(command)
            if result:
                md5_hash = result.split()[0]  # 直接取结果的第一个部分
                return md5_hash
            else:
                self.log_emit(f"Failed to calculate remote MD5 by command for {file_path}")
                self.stop_signal.emit()
                raise
        else:
            hash_md5 = hashlib.md5()
            try:
                with self.sftp.open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
                return hash_md5.hexdigest()
            except Exception as e:
                self.log_emit(f"Failed to calculate remote MD5 by read file for {file_path}: {e}")
                self.stop_signal.emit()
                raise

    def should_ignore_folder(self, folder_path):
        """
        检查文件夹是否需要忽略
        :param folder_path: 文件夹路径
        :return: True 需要忽略 False 不需要忽略
        """
        if not self.ignore_folders:
            return False

        # 清理路径
        clean_path = folder_path.replace(self.local_folder, '').replace(self.remote_folder, '').replace('\\', '/').lstrip('/')
        if clean_path == '':
            return False

        # 检查是否忽略文件夹
        for f in self.ignore_folders:
            if f.startswith('**/'):
                single_folder = f[3:]
                if single_folder in clean_path:
                    return True
            elif clean_path.startswith(f):
                return True

        return False

    def should_ignore_file(self, file_path):
        """
        是否应该忽略文件
        :param file_path: 文件路径
        :return: True 需要忽略 False 不需要忽略
        """
        if not self.ignore_file_types:
            return False

        for file_type in self.ignore_file_types:
            if file_path.endswith(f'.{file_type}'):
                return True
        return False

    def get_all_files(self, local_folder):
        """
        获取本地文件夹中所有文件的列表。

        :param local_folder: 本地文件夹的路径。
        :return: 文件的全路径和相对路径的元组列表。
        """
        files_list = []
        try:
            for root, _, files in os.walk(local_folder):
                if self.should_ignore_folder(root):
                    continue
                for file in files:
                    if self.should_ignore_file(file):
                        continue
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, local_folder)
                    md5 = self.get_md5(full_path)
                    files_list.append((full_path, relative_path, md5))
                    self.log_emit(f"获取本地文件 {relative_path}")
            return files_list
        except Exception as e:
            self.log_emit(f"Failed to list all files in {local_folder}: {e}")
            self.stop_signal.emit()
            raise

    def get_all_remote_files(self, remote_folder):
        """
        获取远程文件夹中所有文件的列表。

        :param remote_folder: 远程文件夹的路径。
        :return: 文件的全路径和相对路径的元组列表。
        """
        files_list = []

        def recursive_list(path):
            try:
                for entry in self.sftp.listdir_attr(path):
                    full_path = posixpath.join(path, entry.filename)
                    if self.should_ignore_folder(entry.filename):
                        continue
                    if stat.S_ISDIR(entry.st_mode):
                        recursive_list(full_path)
                    else:
                        if self.should_ignore_file(entry.filename):
                            continue
                        relative_path = os.path.relpath(full_path, remote_folder)
                        md5 = self.get_remote_md5(full_path, use_command=True)
                        files_list.append((full_path, relative_path, md5))
                        self.log_emit(f"获取远程文件 {relative_path}")
            except Exception as e:
                self.log_emit(f"Failed to list all remote files in {path}: {e}")
                raise

        recursive_list(remote_folder)
        return files_list

    def create_remote_dir(self, remote_directory):
        """
        创建远程目录（包括所有必要的父目录）。

        :param remote_directory: 要创建的远程目录的路径。
        """
        dirs_to_create = []
        while remote_directory and remote_directory != self.remote_folder:
            try:
                self.sftp.stat(remote_directory)
                break
            except FileNotFoundError:
                dirs_to_create.append(remote_directory)
                remote_directory, _ = posixpath.split(remote_directory)

        while dirs_to_create:
            dir = dirs_to_create.pop()
            try:
                self.sftp.mkdir(dir)
            except Exception as e:
                self.log_emit(f"Failed to create remote directory {dir}: {e}")
                raise

    def remove_remote_file_and_empty_dirs(self, remote_path):
        """
         删除远程文件并递归删除空目录。

         :param remote_path: 要删除的远程文件的路径。
         """
        try:
            self.sftp.remove(remote_path)
            self.log_emit(f"删除远程文件 {remote_path}")
        except Exception as e:
            self.log_emit(f"Failed to remove remote file {remote_path}: {e}")
            return False

        dir_path = posixpath.dirname(remote_path)
        while dir_path and dir_path != "/" and dir_path != ".":
            try:
                if not self.sftp.listdir(dir_path):
                    self.sftp.rmdir(dir_path)
                    self.log_emit(f"删除远程文件夹 {dir_path}")
                    dir_path = posixpath.dirname(dir_path)
                else:
                    break
            except Exception as e:
                self.log_emit(f"Failed to remove remote directory {dir_path}: {e}")
                return False
        return True

    def upload_file(self, local_file, remote_file):
        """
        上传本地文件到远程服务器。

        :param local_file: 本地文件的路径。
        :param remote_file: 远程文件的路径。
        """
        remote_dir = posixpath.dirname(remote_file)
        self.create_remote_dir(remote_dir)
        try:
            self.sftp.put(local_file, remote_file)
            self.log_emit(
                f'上传文件: {local_file} --> {remote_file}')
            return True
        except Exception as e:
            self.log_emit(f"Failed to upload file {local_file} --> {remote_file}: {e}")
            return False

    def sync_files(self):
        """
       比较本地和远程文件夹，并同步不同的文件。
       """
        self.connect()

        fail_count = 0
        try:
            if self.changed_files:
                for file in self.changed_files:
                    change = file['change']
                    local_file = file['local_file']
                    remote_file = file['remote_file']
                    relative_path = file['path']

                    flag = None
                    if change == 'not_same' or change == 'local':
                        flag = self.upload_file(local_file, remote_file)
                    elif change == 'remote':
                        flag = self.remove_remote_file_and_empty_dirs(remote_file)

                    if flag is not None:
                        data = {'type': 'sync', 'path': relative_path, 'status': flag}
                        self.data_signal.emit(data)
                        if not flag:
                            fail_count += 1
        finally:
            self.disconnect()
            all_count = len(self.changed_files)
            self.log_emit(f'同步完毕，共 {all_count} 个文件，成功 {all_count - fail_count} 个，失败 {fail_count} 个')

    def refresh_files(self):
        """
       比较本地和远程文件夹，并同步不同的文件。
       """
        self.connect()
        change_count = 0
        try:
            local_files = self.get_all_files(self.local_folder)
            remote_files = self.get_all_remote_files(self.remote_folder)

            all_files = set([file[1] for file in local_files] + [file[1] for file in remote_files])
            for relative_path in all_files:
                local_file = next((file for file in local_files if file[1] == relative_path), None)
                remote_file = next((file for file in remote_files if file[1] == relative_path), None)

                local_file_path = local_file[0] if local_file else None
                remote_file_path = remote_file[0] if remote_file else None

                data = {
                    'type': 'refresh',
                    'path': relative_path.replace('\\', '/'),
                    'local_file': local_file_path,
                }
                if local_file_path and remote_file_path:
                    # 本地和远程都有同名文件，然后比较两个文件的MD5值
                    local_md5 = local_file[2]
                    remote_md5 = remote_file[2]
                    if local_md5 != remote_md5:
                        data['change'] = 'not_same'
                        data['remote_file'] = remote_file_path
                        change_count += 1
                        self.data_signal.emit(data)
                elif local_file_path:
                    # 只有本地有此文件
                    data['change'] = 'local'
                    data['remote_file'] = posixpath.join(self.remote_folder, relative_path.replace('\\', '/'))
                    change_count += 1
                    self.data_signal.emit(data)
                else:
                    # 只有远程有此文件
                    data['change'] = 'remote'
                    data['remote_file'] = remote_file_path
                    change_count += 1
                    self.data_signal.emit(data)
        finally:
            self.disconnect()
            self.log_emit(f'刷新完毕，共有 {change_count} 个文件需要上传')

    def run(self):
        if self.flag == 'refresh':
            self.refresh_files()
        elif self.flag == 'sync':
            self.sync_files()

        self.stop_signal.emit()
