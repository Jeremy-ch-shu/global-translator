from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer

class TranslationOverlay(QWidget):
    """半透明置顶翻译悬浮窗 - 带关闭按钮和自动消失"""
    def __init__(self, auto_close_seconds=5):
        super().__init__()
        self.auto_close_seconds = auto_close_seconds
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)

        # 文本标签
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setStyleSheet(
            "color: white; background: rgba(30, 30, 30, 220); "
            "padding: 12px; border-radius: 8px; font-size: 14px;"
        )
        layout.addWidget(self.label)

        # 按钮行（关闭 + 置顶切换，可选）
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("✕ 关闭")
        close_btn.setFixedSize(80, 28)
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(200, 50, 50, 200); color: white; border: none; border-radius: 4px; }"
            "QPushButton:hover { background: rgba(255, 80, 80, 220); }"
        )
        close_btn.clicked.connect(self.hide)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # 默认隐藏
        self.hide()

    def show_translation(self, text):
        """显示翻译结果，并启动自动关闭计时器"""
        self.label.setText(text)
        self.adjustSize()
        self.move_to_bottom_right()
        self.show()
        self.raise_()
        self.timer.start(self.auto_close_seconds * 1000)

    def move_to_bottom_right(self, margin=30):
        """将窗口移动到屏幕右下角"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.right() - self.width() - margin
        y = geo.bottom() - self.height() - margin
        self.move(x, y)

    def closeEvent(self, event):
        """关闭窗口时停止计时器"""
        self.timer.stop()
        super().closeEvent(event)

    def mousePressEvent(self, event):
        # 单击可保持显示（不隐藏），但单击关闭按钮会触发隐藏
        pass