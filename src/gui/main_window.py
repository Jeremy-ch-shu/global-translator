from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QTextEdit, QLabel,
    QSystemTrayIcon, QMenu, QApplication, QFileDialog,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QIcon, QAction

from loguru import logger
from ..translator.engine import TranslationEngineFactory
from ..ocr.screen_ocr import ScreenOCR
from ..capture.screenshot import ScreenCapture
from ..capture.region_selector import RegionSelector
from .overlay import TranslationOverlay
from .settings import SettingsDialog

# 语言名称到代码的完整映射
LANG_MAP = {
    '自动检测': 'auto',
    '中文': 'zh',
    '英文': 'en',
    '日文': 'ja',
    '韩文': 'ko',
    '法语': 'fr',
    '德语': 'de',
    '西班牙语': 'es',
    '意大利语': 'it',
    '葡萄牙语': 'pt',
    '俄语': 'ru',
}
LANG_NAMES = {v: k for k, v in LANG_MAP.items()}


class TranslationWorker(QThread):
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
            logger.error(f"翻译线程异常: {e}")
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("全局翻译工具")
        self.setGeometry(100, 100, 800, 600)

        self.screen_capture = ScreenCapture()
        self.ocr = ScreenOCR(engine='tesseract', lang='eng+chi_sim')
        self.overlay = TranslationOverlay()

        self.current_engine = None
        self.worker = None
        self.selector = None
        self.tray = None

        self.setup_ui()
        self.setup_tray()
        self.setup_hotkeys()

        # 如需自动翻译，取消下面注释
        # self.source_text.textChanged.connect(self.on_source_text_changed)

    # ---------- UI 布局 ----------
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(15)

        control_layout.addWidget(QLabel("源语言:"))
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(LANG_MAP.keys())
        self.source_lang_combo.setCurrentText('自动检测')
        control_layout.addWidget(self.source_lang_combo)

        control_layout.addWidget(QLabel("目标语言:"))
        self.target_lang_combo = QComboBox()
        target_items = [k for k in LANG_MAP.keys() if k != '自动检测']
        self.target_lang_combo.addItems(target_items)
        self.target_lang_combo.setCurrentText('中文')
        control_layout.addWidget(self.target_lang_combo)

        control_layout.addWidget(QLabel("翻译引擎:"))
        self.engine_combo = QComboBox()
        # 新增 DeepSeek 选项
        self.engine_combo.addItems(['Google翻译', 'DeepL', '离线翻译', 'DeepSeek'])
        control_layout.addWidget(self.engine_combo)

        layout.addLayout(control_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.screen_translate_btn = QPushButton("📷 屏幕翻译")
        self.screen_translate_btn.clicked.connect(self.start_screen_translate)
        btn_layout.addWidget(self.screen_translate_btn)

        self.doc_translate_btn = QPushButton("📄 文档翻译")
        self.doc_translate_btn.clicked.connect(self.start_document_translate)
        btn_layout.addWidget(self.doc_translate_btn)

        self.settings_btn = QPushButton("⚙️ 设置")
        self.settings_btn.clicked.connect(self.open_settings)
        btn_layout.addWidget(self.settings_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addWidget(QLabel("原文:"))
        self.source_text = QTextEdit()
        self.source_text.setPlaceholderText("在此输入或粘贴待翻译文本...")
        layout.addWidget(self.source_text)

        layout.addWidget(QLabel("译文:"))
        self.target_text = QTextEdit()
        self.target_text.setReadOnly(True)
        self.target_text.setPlaceholderText("翻译结果将显示在这里")
        layout.addWidget(self.target_text)

        translate_btn = QPushButton("翻译")
        translate_btn.clicked.connect(self.translate_text)
        translate_btn.setFixedHeight(36)
        layout.addWidget(translate_btn)

    # ---------- 核心功能 ----------
    def translate_text(self):
        """执行翻译（手动触发）"""
        # 1. 取消正在运行的翻译任务
        self._abort_current_worker()

        text = self.source_text.toPlainText().strip()
        if not text:
            logger.warning("翻译请求：原文为空，已忽略")
            return

        source_lang = self.get_lang_code(self.source_lang_combo.currentText())
        target_lang = self.get_lang_code(self.target_lang_combo.currentText())
        engine_type = self.engine_combo.currentText()

        logger.info(f"手动翻译触发: 引擎={engine_type}, 源语言={source_lang}, 目标语言={target_lang}, 文本长度={len(text)}")

        try:
            # 根据选中的引擎创建对应实例
            if engine_type == 'Google翻译':
                engine = TranslationEngineFactory.create_engine('google')
            elif engine_type == 'DeepL':
                # 从配置读取 API Key（示例：从环境变量或 config.json）
                api_key = ""  # 应替换为实际读取逻辑
                if not api_key:
                    self.target_text.setText("⚠️ DeepL 需要 API Key，请在设置中配置")
                    logger.error("DeepL API Key 未配置")
                    return
                engine = TranslationEngineFactory.create_engine('deepl', api_key=api_key)
            elif engine_type == '离线翻译':
                engine = TranslationEngineFactory.create_engine('offline')
            elif engine_type == 'DeepSeek':
                # DeepSeek 引擎在 engine.py 中实现，会自动从环境变量读取密钥
                engine = TranslationEngineFactory.create_engine('deepseek')
            else:
                raise ValueError(f"未知引擎类型: {engine_type}")
            self.current_engine = engine
        except Exception as e:
            logger.error(f"创建翻译引擎失败: {e}")
            self.target_text.setText(f"引擎初始化失败: {str(e)}")
            return

        # 创建并启动新的工作线程
        self.worker = TranslationWorker(engine, text, source_lang, target_lang)
        self.worker.finished.connect(self.on_translation_complete)
        self.worker.error.connect(self.on_translation_error)
        # 线程结束后自动清理（信号连接）
        self.worker.finished.connect(self._cleanup_worker)
        self.worker.error.connect(self._cleanup_worker)
        self.worker.start()

    def _abort_current_worker(self):
        if self.worker is not None:
            if self.worker.isRunning():
                self.worker.quit()
                if not self.worker.wait(1500):
                    logger.warning("Worker 未及时响应，强制终止")
                    self.worker.terminate()
            self.worker.deleteLater()
            self.worker = None

    def _cleanup_worker(self):
        """清理 Worker 引用（信号触发）"""
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None

    def on_translation_complete(self, result):
        logger.info(f"翻译完成，结果长度: {len(result)}")
        self.target_text.setText(result)
        self.overlay.show_translation(result)

    def on_translation_error(self, error_msg):
        logger.error(f"翻译失败: {error_msg}")
        self.target_text.setText(f"❌ 翻译失败: {error_msg}")

    # ---------- 辅助方法 ----------
    def get_lang_code(self, lang_name: str) -> str:
        return LANG_MAP.get(lang_name, 'auto')

    def get_lang_name(self, lang_code: str) -> str:
        return LANG_NAMES.get(lang_code, lang_code)

    # ---------- 屏幕翻译 ----------
    def start_screen_translate(self):
        logger.info("启动屏幕区域选择")
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)
        self.selector.showFullScreen()

    def on_region_selected(self, rect):
        logger.info(f"屏幕区域已选: {rect.x()},{rect.y()} {rect.width()}x{rect.height()}")
        image = self.screen_capture.capture_region(
            rect.x(), rect.y(), rect.width(), rect.height()
        )
        if image is None:
            logger.error("截图失败")
            return
        text = self.ocr.extract_text(image)
        if text:
            self.source_text.setText(text)
            logger.info(f"OCR识别文本: {text[:50]}...")
            self.translate_text()
        else:
            self.source_text.setText("未识别到文本")
            logger.warning("OCR未识别到任何文本")

    # ---------- 文档翻译 ----------
    def start_document_translate(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文档", "",
            "文档文件 (*.docx *.pdf *.txt);;所有文件 (*.*)"
        )
        if file_path:
            self.translate_document(file_path)

    def translate_document(self, file_path: str):
        try:
            from ..document.docx_translator import translate_docx
            from ..document.pdf_translator import translate_pdf

            # 使用当前引擎，若未初始化则使用 Google 作为默认
            engine = self.current_engine or TranslationEngineFactory.create_engine('google')

            if file_path.endswith('.docx'):
                translate_docx(file_path, engine)
            elif file_path.endswith('.pdf'):
                translate_pdf(file_path, engine)
            else:
                # 简单文本文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                target_lang = self.get_lang_code(self.target_lang_combo.currentText())
                translated = engine.translate(content, 'auto', target_lang)
                out_path = file_path.replace('.txt', '_translated.txt')
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(translated)
                logger.info(f"文本文件翻译完成: {out_path}")
                self.target_text.setText(f"翻译完成，文件已保存为: {out_path}")
        except Exception as e:
            logger.error(f"文档翻译失败: {e}")
            self.target_text.setText(f"文档翻译失败: {e}")

    # ---------- 剪贴板翻译 ----------
    def translate_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.source_text.setText(text)
            logger.info("从剪贴板获取文本，自动翻译")
            self.translate_text()
        else:
            logger.warning("剪贴板为空")

    # ---------- 设置 ----------
    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    # ---------- 托盘和热键 ----------
    def setup_tray(self):
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
        try:
            import keyboard
            keyboard.add_hotkey('ctrl+shift+x', self.start_screen_translate)
            keyboard.add_hotkey('ctrl+shift+t', self.translate_clipboard)
            logger.info("全局热键注册成功: Ctrl+Shift+X (屏幕翻译), Ctrl+Shift+T (剪贴板翻译)")
        except Exception as e:
            logger.error(f"全局热键注册失败: {e}")

    # ---------- 可选：自动翻译（延时触发） ----------
    def on_source_text_changed(self):
        if not hasattr(self, '_auto_translate_timer'):
            self._auto_translate_timer = QTimer()
            self._auto_translate_timer.setSingleShot(True)
            self._auto_translate_timer.timeout.connect(self.translate_text)
        self._auto_translate_timer.stop()
        self._auto_translate_timer.start(500)

    # ---------- 关闭事件 ----------
    def closeEvent(self, event):
        """重写关闭事件：询问用户是否退出，确认后清理资源并退出进程。"""
        reply = QMessageBox.question(
            self, '确认退出',
            '确定要退出程序吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            event.ignore()
            return

        # 1. 卸载全局热键（释放键盘钩子）
        try:
            import keyboard
            keyboard.unhook_all()
            logger.info("全局热键已卸载")
        except Exception as e:
            logger.debug(f"卸载热键时出现异常（可忽略）: {e}")

        # 2. 强制终止 Worker（安全退出）
        self._abort_current_worker()

        # 3. 关闭悬浮窗
        if self.overlay is not None:
            self.overlay.close()
            self.overlay.deleteLater()

        # 4. 隐藏并删除系统托盘图标
        if self.tray is not None:
            self.tray.hide()
            self.tray.deleteLater()

        # 5. 关闭区域选择器
        if self.selector is not None:
            self.selector.close()
            self.selector.deleteLater()

        event.accept()
        QApplication.quit()
        logger.info("程序已退出")