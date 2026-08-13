from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QTextEdit, QLabel,
    QSystemTrayIcon, QMenu, QApplication, QFileDialog,
    QMessageBox, QShortcut
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QIcon, QAction, QKeySequence, QImage

from loguru import logger
from ..translator.engine import TranslationEngineFactory
from ..ocr.screen_ocr import ScreenOCR
from ..capture.screenshot import ScreenCapture
from ..capture.region_selector import RegionSelector
from .overlay import TranslationOverlay
from .settings import SettingsDialog
from ..utils.config import Config

import time
import io
from PySide6.QtCore import QBuffer, QIODevice
from PIL import Image

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

    hotkey_pressed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("全局翻译工具")
        self.setGeometry(100, 100, 800, 600)

        # 配置
        self.config = Config.load()

        self.screen_capture = ScreenCapture()
        self.ocr = ScreenOCR(engine=self.config.get('ocr', {}).get('engine', 'tesseract'),
                             lang=self.config.get('ocr', {}).get('language', 'eng+chi_sim'))
        self.overlay = TranslationOverlay()

        self.current_engine = None
        self.worker = None
        self.selector = None
        self.tray = None

        self.setup_ui()
        self.setup_tray()
        self.setup_hotkeys()

        self.hotkey_pressed.connect(self._on_hotkey)

        # 剪贴板自动检测（仅在配置开启时连接）
        self._clipboard_last_ts = 0
        try:
            clipboard = QApplication.clipboard()
            if self.config.get('general', {}).get('clipboard_auto_detect', False):
                clipboard.dataChanged.connect(self._on_clipboard_data_changed)
        except Exception as e:
            logger.debug(f"无法连接剪贴板 dataChanged 信号: {e}")

    # ---------- UI ----------
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

        self.paste_image_btn = QPushButton("📋 粘贴截图")
        self.paste_image_btn.clicked.connect(self.paste_image_from_clipboard)
        btn_layout.addWidget(self.paste_image_btn)

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

    # ---------- 翻译流程 ----------
    def translate_text(self):
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
            if engine_type == 'Google翻译':
                engine = TranslationEngineFactory.create_engine('google')
            elif engine_type == 'DeepL':
                api_key = self.config.get('translation', {}).get('deepl_api_key', '')
                if not api_key:
                    self.target_text.setText("⚠️ DeepL 需要 API Key，请在设置中配置")
                    logger.error("DeepL API Key 未配置")
                    return
                engine = TranslationEngineFactory.create_engine('deepl', api_key=api_key)
            elif engine_type == '离线翻译':
                engine = TranslationEngineFactory.create_engine('offline')
            elif engine_type == 'DeepSeek':
                engine = TranslationEngineFactory.create_engine('deepseek')
            else:
                raise ValueError(f"未知引擎类型: {engine_type}")
            self.current_engine = engine
        except Exception as e:
            logger.error(f"创建翻译引擎失败: {e}")
            self.target_text.setText(f"引擎初始化失败: {str(e)}")
            return

        self.worker = TranslationWorker(engine, text, source_lang, target_lang)
        self.worker.finished.connect(self.on_translation_complete)
        self.worker.error.connect(self.on_translation_error)
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
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None

    def on_translation_complete(self, result):
        logger.info(f"翻译完成，结果长度: {len(result)}")
        self.target_text.setText(result)
        try:
            self.overlay.show_translation(result)
        except Exception:
            pass

    def on_translation_error(self, error_msg):
        logger.error(f"翻译失败: {error_msg}")
        self.target_text.setText(f"❌ 翻译失败: {error_msg}")

    # ---------- 帮助方法 ----------
    def get_lang_code(self, lang_name: str) -> str:
        return LANG_MAP.get(lang_name, 'auto')

    def get_lang_name(self, lang_code: str) -> str:
        return LANG_NAMES.get(lang_code, lang_code)

    # ---------- 屏幕翻译 ----------
    def start_screen_translate(self):
        logger.info("启动屏幕区域选择")
        if self.selector is not None:
            try:
                self.selector.close()
                self.selector.deleteLater()
            except Exception:
                pass
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)
        self.selector.showFullScreen()

    def on_region_selected(self, rect):
        logger.info(f"屏幕区域已选: {rect.x()},{rect.y()} {rect.width()}x{rect.height()}")
        x, y, w, h = int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height())
        if w <= 0 or h <= 0:
            logger.error("选区尺寸非法")
            return

        # 记录 monitor 信息与 region 参数
        try:
            monitors = getattr(self.screen_capture.sct, 'monitors', None)
            logger.debug(f"当前 monitors: {monitors}")
        except Exception as e:
            logger.debug(f"获取 monitors 信息失败: {e}")

        try:
            image = self.screen_capture.capture_region(x, y, w, h)
        except Exception as e:
            try:
                monitors = getattr(self.screen_capture.sct, 'monitors', None)
                logger.error(f"截图失败: {e}. region=({x},{y},{w},{h}), monitors={monitors}")
            except Exception:
                logger.error(f"截图失败: {e}. region=({x},{y},{w},{h})")
            self.target_text.setText(f"截图失败: {e}")
            return

        if image is None:
            logger.error("截图返回 None")
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

            engine = self.current_engine or TranslationEngineFactory.create_engine('google')

            if file_path.endswith('.docx'):
                translate_docx(file_path, engine)
            elif file_path.endswith('.pdf'):
                translate_pdf(file_path, engine)
            else:
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

    # ---------- 剪贴板 ----------
    def translate_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self.source_text.setText(text)
            logger.info("从剪贴板获取文本，自动翻译")
            self.translate_text()
        else:
            logger.warning("剪贴板为空")

    def paste_image_from_clipboard(self):
        clipboard = QApplication.clipboard()
        qimg = clipboard.image()
        if qimg is None or qimg.isNull():
            mime = clipboard.mimeData()
            if mime and mime.hasImage():
                try:
                    qimg = QImage(mime.imageData())
                except Exception:
                    qimg = None
        if qimg is None or qimg.isNull():
            self.target_text.setText("剪贴板中没有图像")
            logger.warning("剪贴板中没有图像可供粘贴")
            return

        try:
            buf = QBuffer()
            buf.open(QIODevice.ReadWrite)
            qimg.save(buf, "PNG")
            bytearr = buf.data()
            pil_img = Image.open(io.BytesIO(bytearr))
        except Exception as e:
            logger.error(f"将剪贴板图像转换为 PIL 失败: {e}")
            self.target_text.setText(f"处理剪贴板图像失败: {e}")
            return

        text = self.ocr.extract_text(pil_img)
        if text:
            self.source_text.setText(text)
            self.translate_text()
        else:
            self.target_text.setText("未识别到文本")

    def _on_clipboard_data_changed(self):
        now = time.time()
        if now - getattr(self, '_clipboard_last_ts', 0) < 2.0:
            return
        self._clipboard_last_ts = now
        QTimer.singleShot(250, self._process_clipboard_if_image)

    def _process_clipboard_if_image(self):
        clipboard = QApplication.clipboard()
        try:
            qimg = clipboard.image()
            has_image = not (qimg is None or qimg.isNull())
        except Exception:
            has_image = False
        if not has_image:
            mime = clipboard.mimeData()
            has_image = mime and mime.hasImage()
        if has_image:
            self.paste_image_from_clipboard()

    # ---------- 设置 ----------
    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == 1:
            # 重新加载配置并根据需要（重新注册热键/剪贴板）
            self.config = Config.load()
            self.setup_hotkeys()
            # 重新连接剪贴板信号
            try:
                clipboard = QApplication.clipboard()
                clipboard.dataChanged.disconnect()
            except Exception:
                pass
            try:
                if self.config.get('general', {}).get('clipboard_auto_detect', False):
                    QApplication.clipboard().dataChanged.connect(self._on_clipboard_data_changed)
            except Exception as e:
                logger.debug(f"重新连接剪贴板失败: {e}")

    # ---------- 托盘与热键 ----------
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
        cfg = self.config.get('general', {})
        register = bool(cfg.get('register_global_hotkeys', True))
        registered = False
        if register:
            try:
                import keyboard
                keyboard.add_hotkey(self.config.get('hotkeys', {}).get('screen_translate', 'ctrl+shift+x'),
                                    lambda: self.hotkey_pressed.emit('screen_translate'))
                keyboard.add_hotkey(self.config.get('hotkeys', {}).get('clipboard_translate', 'ctrl+shift+t'),
                                    lambda: self.hotkey_pressed.emit('clipboard_translate'))
                registered = True
                logger.info("全局热键注册成功")
            except Exception as e:
                logger.error(f"全局热键注册失败: {e}")

        if not registered:
            try:
                qs1 = QShortcut(QKeySequence("Ctrl+Shift+X"), self)
                qs1.activated.connect(self.start_screen_translate)
                qs2 = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
                qs2.activated.connect(self.translate_clipboard)
                logger.info("使用程序内快捷键作为全局热键的回退方案（窗口需有焦点）")
                if self.tray is not None:
                    self.tray.showMessage("热键回退", "全局热键注册失败，已启用程序内快捷键（窗口需有焦点）。\n"
                                              "可在设置中关闭全局热键或提高权限以恢复全局热键。")
            except Exception as e:
                logger.error(f"安装程序内快捷键回退失败: {e}")
                if self.tray is not None:
                    self.tray.showMessage("热键问题", "热键注册失败且程序内快捷键无法启用，请检查权限或在设置中禁用全局热键。")

    def _on_hotkey(self, name: str):
        if name == 'screen_translate':
            self.start_screen_translate()
        elif name == 'clipboard_translate':
            self.translate_clipboard()

    # ---------- 关闭事件 ----------
    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, '确认退出',
            '确定要退出程序吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            event.ignore()
            return

        try:
            import keyboard
            keyboard.unhook_all()
            logger.info("全局热键已卸载")
        except Exception as e:
            logger.debug(f"卸载热键时出现异常（可忽略）: {e}")

        self._abort_current_worker()

        if self.overlay is not None:
            self.overlay.close()
            self.overlay.deleteLater()

        if self.tray is not None:
            self.tray.hide()
            self.tray.deleteLater()

        if self.selector is not None:
            self.selector.close()
            self.selector.deleteLater()

        event.accept()
        QApplication.quit()
        logger.info("程序已退出")
