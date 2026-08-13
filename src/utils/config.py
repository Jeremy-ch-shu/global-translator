import json
import os
from pathlib import Path
from loguru import logger

class Config:
    """配置管理"""

    # 支持跨平台：优先 APPDATA（Windows），否则使用用户主目录
    CONFIG_DIR = Path(os.environ.get('APPDATA') or Path.home()) / 'GlobalTranslator'
    CONFIG_FILE = CONFIG_DIR / 'config.json'

    DEFAULT_CONFIG = {
        'general': {
            'clipboard_auto_detect': False,
            'register_global_hotkeys': True
        },
        'translation': {
            'engine': 'google',  # google, deepl, offline
            'source_lang': 'auto',
            'target_lang': 'zh-CN',
            'deepl_api_key': ''
        },
        'ocr': {
            'engine': 'tesseract',  # tesseract, easyocr
            'language': 'eng+chi_sim'
        },
        'hotkeys': {
            'screen_translate': 'ctrl+shift+x',
            'clipboard_translate': 'ctrl+shift+t'
        },
        'appearance': {
            'overlay_opacity': 0.9,
            'font_size': 14,
            'theme': 'dark'
        }
    }

    @classmethod
    def load(cls):
        """加载配置"""
        if not cls.CONFIG_FILE.exists():
            cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            cls.save(cls.DEFAULT_CONFIG)
            return cls.DEFAULT_CONFIG

        try:
            with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return cls.DEFAULT_CONFIG

    @classmethod
    def save(cls, config):
        """保存配置"""
        try:
            cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            logger.info(f"配置已保存: {cls.CONFIG_FILE}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
