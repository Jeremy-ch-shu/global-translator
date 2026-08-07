import mss
import mss.tools
from PIL import Image
import numpy as np

class ScreenCapture:
    """屏幕截图类"""
    
    def __init__(self):
        self.sct = mss.mss()
    
    def capture_full_screen(self) -> Image.Image:
        """截取全屏"""
        monitor = self.sct.monitors[1]  # 主显示器
        screenshot = self.sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    
    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """截取指定区域"""
        region = {"top": y, "left": x, "width": width, "height": height}
        screenshot = self.sct.grab(region)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

# src/capture/region_selector.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QPen, QColor

class RegionSelector(QWidget):
    """屏幕区域选择器 - 半透明覆盖层"""
    
    region_selected = Signal(QRect)
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        self.start_point = None
        self.end_point = None
        self.is_dragging = False
        
        # 全屏显示
        screen = QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
    
    def mousePressEvent(self, event):
        self.start_point = event.pos()
        self.is_dragging = True
    
    def mouseMoveEvent(self, event):
        self.end_point = event.pos()
        self.update()
    
    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        if self.start_point and self.end_point:
            rect = QRect(self.start_point, self.end_point).normalized()
            self.region_selected.emit(rect)
            self.close()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))  # 半透明黑色背景
        
        if self.start_point and self.end_point:
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.setPen(QPen(QColor(0, 255, 0), 2))
            painter.drawRect(rect)
            # 清除选区内的暗色
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)