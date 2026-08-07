from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("设置面板"))
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)