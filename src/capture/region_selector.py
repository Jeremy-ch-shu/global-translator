from PySide6.QtWidgets import QWidget, QApplication
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