from abc import ABC, abstractmethod
from loguru import logger

class TranslationEngine(ABC):
    """翻译引擎抽象基类"""
    
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """翻译文本"""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        pass

class GoogleTranslateEngine(TranslationEngine):
    """Google翻译引擎"""
    
    def __init__(self):
        from deep_translator import GoogleTranslator
        self.translator = GoogleTranslator()
    
    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'zh-CN') -> str:
        try:
            result = self.translator.translate(text, source=source_lang, target=target_lang)
            logger.info(f"翻译成功: {text[:50]}... -> {result[:50]}...")
            return result
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return text

class DeepLEngine(TranslationEngine):
    """DeepL翻译引擎"""
    
    def __init__(self, api_key: str):
        import requests
        self.api_key = api_key
        self.api_url = "https://api-free.deepl.com/v2/translate"
    
    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'ZH') -> str:
        # DeepL实现
        pass
    
    def get_supported_languages(self) -> list:
        return ['EN', 'ZH', 'JA', 'DE', 'FR', 'ES', 'IT', 'NL', 'PL', 'PT', 'RU']

class TranslationEngineFactory:
    """翻译引擎工厂"""
    
    @staticmethod
    def create_engine(engine_type: str, **kwargs) -> TranslationEngine:
        if engine_type == 'google':
            return GoogleTranslateEngine()
        elif engine_type == 'deepl':
            return DeepLEngine(kwargs.get('api_key', ''))
        elif engine_type == 'offline':
            # 使用Argos Translate实现离线翻译
            from argostranslate import translate
            return OfflineTranslateEngine()
        else:
            raise ValueError(f"不支持的翻译引擎: {engine_type}")