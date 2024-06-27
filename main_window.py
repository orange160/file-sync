"""
@File  : main_window.py
@Author: lyj
@Create  : 2024/6/26 17:02
@Modify  : 
@Description  : 主界面
"""
from datetime import datetime

import yaml
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QTextEdit, \
    QHeaderView, QTableWidget, QTableWidgetItem, QMessageBox, QSplitter

from file_compare_thread import FolderComparatorThread
from helper import get_resource


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Sync")
        self.setWindowIcon(QIcon(get_resource("images/logo.png")))
        self.setGeometry(100, 100, 800, 600)
        self.worker = None
        self.changed_files = []

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 第一层：按钮和选择框
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setFixedSize(100, 40)
        self.sync_button = QPushButton("同步")
        self.sync_button.setFixedSize(100, 40)
        self.server_combo = QComboBox()
        self.server_combo.setFixedSize(300, 40)

        # 设置QComboBox字体大小
        font = QFont()
        font.setPointSize(11)
        self.server_combo.setFont(font)

        button_layout.addWidget(self.server_combo)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.sync_button)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        # 使用QSplitter将table和log_output分隔开
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 第二层：表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["文件名", "不一致类型", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self.table)

        # 第三层：多行输入框
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        splitter.addWidget(self.log_output)

        # 设置初始大小比例
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # 连接信号和槽
        self.refresh_button.clicked.connect(self.on_refresh)
        self.sync_button.clicked.connect(self.on_sync)

        self.load_servers()

    def set_buttons_enabled(self, flag):
        self.sync_button.setEnabled(flag)
        self.refresh_button.setEnabled(flag)
        self.server_combo.setEnabled(flag)
        if flag:
            self.refresh_button.setStyleSheet("")
            self.sync_button.setStyleSheet("")
            self.server_combo.setStyleSheet("")
        else:
            self.refresh_button.setStyleSheet("background-color: lightgray")
            self.sync_button.setStyleSheet("background-color: lightgray")
            self.server_combo.setStyleSheet("background-color: lightgray")

    def load_servers(self):
        try:
            with open("config.yaml", "r") as file:
                self.config = yaml.safe_load(file)
                for server in self.config["servers"]:
                    self.server_combo.addItem(server["name"])
        except FileNotFoundError:
            self.config = {"servers": []}

    def create_worker(self, server_name, flag, changed_files=None):
        try:
            current_server = next(server for server in self.config["servers"] if server["name"] == server_name)
            hostname = current_server.get("hostname")
            port = current_server.get("port")
            username = current_server.get("username")
            key_file_path = current_server.get("key_file_path")
            password = current_server.get("password")
            local_folder = current_server.get("local_folder")
            remote_folder = current_server.get("remote_folder")

            self.worker = FolderComparatorThread(
                server_name=server_name,
                flag=flag,
                changed_files=changed_files,
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                key_file_path=key_file_path,
                local_folder=local_folder,
                remote_folder=remote_folder
            )
            self.worker.log_signal.connect(self.worker_log_slot)
            self.worker.stop_signal.connect(self.worker_stop_slot)
            self.worker.data_signal.connect(self.worker_data_slot)

            self.worker.start()
        except StopIteration:
            self.log_output.append("选择的服务器未找到，请先设置连接信息。")
        except FileNotFoundError:
            self.log_output.append("配置文件未找到，请先设置连接信息。")

    def add_log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] {message}"

        with open('result.log', 'a', encoding='utf-8') as f:
            f.write(f'{msg}\n')

        self.log_output.append(msg)

    def on_refresh(self):
        reply = QMessageBox.question(self, '确认', '你确定要刷新吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        self.add_log_message("刷新按钮被点击")
        self.changed_files = []
        self.set_buttons_enabled(False)
        self.clear_table()
        self.create_worker(self.server_combo.currentText(), 'refresh', None)

    def on_sync(self):
        row_count = self.table.rowCount()
        if not row_count:
            QMessageBox.information(self, '提示', '请先刷新/没有需要同步的文件')
            return

        all_sync = True
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 2)
            if item is None:
                all_sync = False
                break
            else:
                if item.text() == '失败':
                    all_sync = False
                    break
        if all_sync:
            QMessageBox.information(self, '提示', '已经全部同步成功，请勿重复')
            return

        reply = QMessageBox.question(self, '确认', '你确定要同步吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        self.add_log_message("同步按钮被点击")
        self.set_buttons_enabled(False)
        self.create_worker(self.server_combo.currentText(), 'sync', self.changed_files)

    def clear_table(self):
        self.table.clearContents()
        self.table.setRowCount(0)
        self.table.setColumnCount(3)

    def worker_data_slot(self, data):
        server_name = self.server_combo.currentText()
        msg = None
        if data['type'] == 'refresh':
            if data['change'] == 'not_same':
                change_item = QTableWidgetItem('不一致')
                change_item.setBackground(QColor('#FFC7A6'))  # 设置背景颜色
            elif data['change'] == 'local':
                change_item = QTableWidgetItem('本地有')
                change_item.setBackground(QColor('#A3C8FF'))  # 设置背景颜色
            elif data['change'] == 'remote':
                change_item = QTableWidgetItem('远程有')
                change_item.setBackground(QColor('#ACFFA3'))  # 设置背景颜色
            else:
                change_item = QTableWidgetItem('Unknown')

            row_number = self.table.rowCount()
            self.table.insertRow(row_number)
            self.table.setItem(row_number, 0, QTableWidgetItem(data['path']))
            self.table.setItem(row_number, 1, change_item)

            self.changed_files.append(data)
            msg = '{} 刷新，文件: {}, 不一致类型: {}'.format(server_name, data['path'], change_item.text())
        elif data['type'] == 'sync':
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)  # 获取第一列的单元格
                if item is not None:
                    cell_text = item.text()
                    if cell_text and cell_text == data['path']:
                        if data['status']:
                            status_item = QTableWidgetItem('成功')
                            status_item.setBackground(QColor('#50FF37'))
                        else:
                            status_item = QTableWidgetItem('失败')
                            status_item.setBackground(QColor('#FF5757'))
                        self.table.setItem(row, 2, QTableWidgetItem(status_item))
                        msg = '{} 同步，文件: {}, 状态: {}'.format(server_name, data['path'], status_item.text())
                        break

        if msg:
            self.add_log_message(msg)

    def worker_log_slot(self, msg):
        self.add_log_message(msg)

    def worker_stop_slot(self):
        self.set_buttons_enabled(True)

