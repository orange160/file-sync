import sys

from PyQt6.QtWidgets import QApplication

from main_window import MainWindow

if __name__ == '__main__':
    # # Example usage
    # hostname = '192.168.1.87'
    # port = 22
    # username = 'li'
    # password = 'orange'
    # key_file_path = None
    #
    # local_folder = 'E:\\0_workspace\\python-workspace\\cocode-ai\\app'
    # remote_folder = '/home/li/.cocode-ai/app'
    #
    # comparator = FolderComparator(hostname, port, username, key_file_path, password, local_folder, remote_folder)
    # comparator.compare_folders()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
