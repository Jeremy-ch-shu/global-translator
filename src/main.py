# -*- coding: utf-8 -*-
"""
程序入口
- 显示自定义启动画面（带进度条和旋转动画）
- 延迟导入大型模块，确保启动画面快速显示
- 逐步加载配置、资源，最后显示主窗口
"""

import sys
import os
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

load_dotenv()   

# 添加项目根目录到 Python 路径（必须尽早执行）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from src.utils.config import Config


# ===== 全局样式表 =====
GLOBAL_STYLE = """
    QMainWindow {
        background-color: #f5f7fa;
    }
    QLabel {
        font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        color: #2c3e50;
    }
    QPushButton {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: bold;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #2980b9;
    }
    QPushButton:pressed {
        background-color: #1f6c8c;
    }
    QComboBox {
        background-color: white;
        border: 1px solid #bdc3c7;
        border-radius: 6px;
        padding: 5px 10px;
        min-height: 25px;
    }
    QComboBox:hover {
        border-color: #3498db;
    }
    QComboBox::drop-down {
        border: none;
    }
    QTextEdit {
        background-color: white;
        border: 1px solid #dcdde1;
        border-radius: 8px;
        padding: 8px;
        font-size: 14px;
        font-family: "Segoe UI", sans-serif;
    }
    QTextEdit:focus {
        border-color: #3498db;
    }
    QProgressBar {
        border: none;
        background: #ecf0f1;
        border-radius: 10px;
        height: 20px;
        text-align: center;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #3498db, stop:1 #2ecc71);
        border-radius: 10px;
    }
    QMenu {
        background-color: white;
        border: 1px solid #bdc3c7;
        border-radius: 6px;
    }
    QMenu::item {
        padding: 6px 20px;
    }
    QMenu::item:selected {
        background-color: #3498db;
        color: white;
    }
"""


class SplashScreen(QWidget):
    """自定义启动画面（带进度条和旋转动画）"""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 260)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title = QLabel("🌍 全局翻译工具")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        # 副标题
        sub = QLabel("正在加载，请稍候...")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        layout.addWidget(sub)

        # 旋转动画指示器
        self.spinner_label = QLabel("⏳")
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_label.setStyleSheet("font-size: 32px; color: #3498db;")
        layout.addWidget(self.spinner_label)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #ecf0f1;
                border-radius: 10px;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.progress)

        # 状态标签
        self.status_label = QLabel("初始化...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; color: #95a5a6;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        # 窗口背景（半透明磨砂）
        self.setStyleSheet("""
            SplashScreen {
                background: rgba(255, 255, 255, 220);
                border-radius: 20px;
                border: 1px solid #bdc3c7;
            }
        """)

        # 旋转动画定时器
        self.spinner_frames = ["⏳", "⌛", "⏳", "⌛"]
        self.spinner_index = 0
        self.spinner_timer = QTimer()
        self.spinner_timer.timeout.connect(self._update_spinner)
        self.spinner_timer.start(300)

        # 启动时间记录，用于提示加载过久
        self.start_time = QTimer()
        self.start_time.setSingleShot(True)
        self.start_time.timeout.connect(self._show_slow_hint)
        self.start_time.start(5000)  # 5秒后触发

    def _update_spinner(self):
        """更新旋转动画字符"""
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
        self.spinner_label.setText(self.spinner_frames[self.spinner_index])

    def _show_slow_hint(self):
        """加载超过5秒时显示提示"""
        self.status_label.setText("⏱️ 加载时间较长，请耐心等待...")
        self.status_label.setStyleSheet("font-size: 12px; color: #e67e22;")

    def set_progress(self, value: int, status: str = ""):
        """更新进度和状态文字"""
        self.progress.setValue(value)
        if status:
            self.status_label.setText(status)
            # 如果状态变化，重置慢速提示（如果已经显示，可以保留）
            # 但保留提示，用户知道还在加载

    def closeEvent(self, event):
        """关闭时停止所有定时器"""
        self.spinner_timer.stop()
        self.start_time.stop()
        super().closeEvent(event)


def main():
    """程序主入口"""
    # 配置日志
    logger.add("logs/translator.log", rotation="10 MB", retention="7 days")
    logger.info("正在启动全局翻译工具...")

    # 创建 Qt 应用（必须尽早，以便显示启动画面）
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app.setStyleSheet(GLOBAL_STYLE)

    # 显示启动画面（此时尚未导入 MainWindow，所以响应迅速）
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # 主窗口实例（暂为 None）
    window = None

    # ---------- 加载步骤（逐步执行，最后才导入 MainWindow） ----------
    def load_config():
        splash.set_progress(10, "加载配置...")
        config = Config.load()  # 可在此预处理配置
        QTimer.singleShot(200, init_ocr)

    def init_ocr():
        splash.set_progress(30, "初始化OCR引擎...")
        # 可提前导入 OCR 模块（但为保持快速，仅模拟）
        QTimer.singleShot(300, load_translator)

    def load_translator():
        splash.set_progress(50, "加载翻译引擎...")
        # 可提前导入翻译引擎（但也可在主窗口首次使用时加载）
        QTimer.singleShot(300, prepare_ui)

    def prepare_ui():
        splash.set_progress(70, "准备界面...")
        # 其他准备工作
        QTimer.singleShot(200, create_window)

    def create_window():
        """延迟导入 MainWindow（耗时操作）"""
        nonlocal window
        splash.set_progress(85, "正在加载主窗口模块...")
        # 导入 MainWindow（此时会加载 PySide6 等大模块，但启动画面已经显示）
        from src.gui.main_window import MainWindow
        splash.set_progress(90, "创建主窗口...")
        window = MainWindow()
        QTimer.singleShot(200, finish_loading)

    def finish_loading():
        splash.set_progress(100, "加载完成！")
        splash.close()
        window.show()
        logger.info("程序启动完成")

    # 启动加载流程
    QTimer.singleShot(100, load_config)

    # 运行事件循环
    try:
        sys.exit(app.exec())
    except Exception as e:
        logger.exception(f"程序运行时发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()