import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from loguru import logger

from src.gui.main_window import MainWindow
from src.utils.config import Config

def main():
    """程序入口"""
    # 配置日志
    logger.add("logs/translator.log", rotation="10 MB", retention="7 days")
    
    # 加载配置
    config = Config.load()
    logger.info("全局翻译工具启动")
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行
    sys.exit(app.exec())

if __name__ == "__main__":
    main()