from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QComboBox, QTextEdit, QLabel, 
    QSystemTrayIcon, QMenu, QApplication)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QIcon, QAction

from ..translator.engine import TranslationEngineFactory
from ..ocr.screen_ocr import ScreenOCR
from ..capture.screenshot import ScreenCapture
from ..capture.region_selector import RegionSelector
from .overlay import TranslationOverlay
from .settings import SettingsDialog

class TranslationWorker(QThread):
    """翻译工作线程 - 避免阻塞UI"""
    
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, engine, text, source_lang, target_lang):
        super().__init__()
        self.engine = engine
        self.text = text
        self.source_lang = source_lang
        self.target_lang = target_lang
    
    def run(self):
        try:
            result = self.engine.translate(self.text, self.source_lang, self.target_lang)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("全局翻译工具")
        self.setGeometry(100, 100, 800, 600)
        
        # 初始化组件
        self.screen_capture = ScreenCapture()
        self.ocr = ScreenOCR(engine='tesseract', lang='eng+chi_sim')
        self.translation_engine = TranslationEngineFactory.create_engine('google')
        self.overlay = TranslationOverlay()
        
        self.setup_ui()
        self.setup_tray()
        self.setup_hotkeys()
    
    def setup_ui(self):
        """设置UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 顶部控制栏
        control_layout = QHBoxLayout()
        
        # 源语言选择
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(['自动检测', '英文', '中文', '日文', '韩文'])
        control_layout.addWidget(QLabel("源语言:"))
        control_layout.addWidget(self.source_lang_combo)
        
        # 目标语言选择
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(['中文', '英文', '日文', '韩文'])
        control_layout.addWidget(QLabel("目标语言:"))
        control_layout.addWidget(self.target_lang_combo)
        
        # 翻译引擎选择
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(['Google翻译', 'DeepL', '离线翻译'])
        control_layout.addWidget(QLabel("翻译引擎:"))
        control_layout.addWidget(self.engine_combo)
        
        layout.addLayout(control_layout)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.screen_translate_btn = QPushButton("📷 屏幕翻译")
        self.screen_translate_btn.clicked.connect(self.start_screen_translate)
        btn_layout.addWidget(self.screen_translate_btn)
        
        self.doc_translate_btn = QPushButton("📄 文档翻译")
        self.doc_translate_btn.clicked.connect(self.start_document_translate)
        btn_layout.addWidget(self.doc_translate_btn)
        
        self.settings_btn = QPushButton("⚙️ 设置")
        self.settings_btn.clicked.connect(self.open_settings)
        btn_layout.addWidget(self.settings_btn)
        
        layout.addLayout(btn_layout)
        
        # 原文和译文
        layout.addWidget(QLabel("原文:"))
        self.source_text = QTextEdit()
        layout.addWidget(self.source_text)
        
        layout.addWidget(QLabel("译文:"))
        self.target_text = QTextEdit()
        self.target_text.setReadOnly(True)
        layout.addWidget(self.target_text)
        
        # 翻译按钮
        translate_btn = QPushButton("翻译")
        translate_btn.clicked.connect(self.translate_text)
        layout.addWidget(translate_btn)
    
    def start_screen_translate(self):
        """启动屏幕翻译"""
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)
        self.selector.showFullScreen()
    
    def on_region_selected(self, rect):
        """区域选择完成后的回调"""
        # 截图
        image = self.screen_capture.capture_region(
            rect.x(), rect.y(), rect.width(), rect.height()
        )
        # OCR识别
        text = self.ocr.extract_text(image)
        self.source_text.setText(text)
        # 自动翻译
        if text:
            self.translate_text()
    
    def translate_text(self):
        """执行翻译"""
        text = self.source_text.toPlainText()
        if not text:
            return
        
        source_lang = self.get_lang_code(self.source_lang_combo.currentText())
        target_lang = self.get_lang_code(self.target_lang_combo.currentText())
        
        self.worker = TranslationWorker(
            self.translation_engine, text, source_lang, target_lang
        )
        self.worker.finished.connect(self.on_translation_complete)
        self.worker.error.connect(self.on_translation_error)
        self.worker.start()
    
    def on_translation_complete(self, result):
        self.target_text.setText(result)
        # 显示悬浮窗
        self.overlay.show_translation(result)
    
    def on_translation_error(self, error):
        self.target_text.setText(f"翻译错误: {error}")
    
    def get_lang_code(self, lang_name: str) -> str:
        lang_map = {
            '自动检测': 'auto',
            '中文': 'zh-CN',
            '英文': 'en',
            '日文': 'ja',
            '韩文': 'ko'
        }
        return lang_map.get(lang_name, 'auto')
    
    def setup_tray(self):
        """系统托盘"""
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon())
        
        tray_menu = QMenu()
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self.tray.setContextMenu(tray_menu)
        self.tray.show()
    
    def setup_hotkeys(self):
        """全局热键 - 使用keyboard库"""
        import keyboard
        keyboard.add_hotkey('ctrl+shift+x', self.start_screen_translate)
        keyboard.add_hotkey('ctrl+shift+t', self.translate_clipboard)
    
    def translate_clipboard(self):
        """翻译剪贴板内容"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.source_text.setText(text)
            self.translate_text()
    
    def start_document_translate(self):
        """文档翻译"""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文档", "", "文档文件 (*.docx *.pdf *.txt)"
        )
        if file_path:
            self.translate_document(file_path)
    
    def translate_document(self, file_path: str):
        """翻译文档"""
        # 根据扩展名选择不同的处理器
        from ..document.docx_translator import translate_docx
        from ..document.pdf_translator import translate_pdf
        
        if file_path.endswith('.docx'):
            translate_docx(file_path, self.translation_engine)
        elif file_path.endswith('.pdf'):
            translate_pdf(file_path, self.translation_engine)
    
    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec()