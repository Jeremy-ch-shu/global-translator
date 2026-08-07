# -*- coding: utf-8 -*-
"""
翻译引擎模块

提供四种翻译引擎：
1. GoogleTranslateEngine  - 使用 MyMemory 免费 API（需网络，支持多语言，但不支持 'auto' 源语言）
2. DeepSeekTranslateEngine - 使用 DeepSeek 大模型 API（需 API Key 和余额，质量最高）
3. DeepLEngine             - 使用 DeepL API（需 API Key，质量高）
4. OfflineTranslateEngine  - 使用 Argos Translate 离线翻译（无需网络，质量一般）

所有引擎均实现 translate 和 get_supported_languages 方法。
"""

import os
import time
from abc import ABC, abstractmethod
from typing import List

import requests
from loguru import logger

# 尝试导入 openai，若未安装则给出提示
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
    logger.warning("openai 未安装，DeepSeek 引擎不可用。请运行: pip install openai")


class TranslationEngine(ABC):
    """翻译引擎抽象基类"""

    @abstractmethod
    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'zh') -> str:
        """
        执行翻译
        :param text: 待翻译文本
        :param source_lang: 源语言代码（'auto' 表示自动检测）
        :param target_lang: 目标语言代码
        :return: 翻译后的文本，若失败则返回原文或错误提示
        """
        pass

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """返回该引擎支持的语言代码列表（不含 'auto'）"""
        pass


# ============================================================
# 1. MyMemory 免费 API 引擎（谷歌翻译的替代方案）
# ============================================================
class GoogleTranslateEngine(TranslationEngine):
    """
    使用 MyMemory 公共 API 进行翻译。
    - 免费，无需 API Key。
    - 不支持 'auto' 作为源语言，若传入 'auto' 将自动改用 'en'。
    - 请求频率有限，注意不要过于频繁。
    - 适合简单、非专业领域的翻译。
    """

    def __init__(self):
        self.api_url = "https://api.mymemory.translated.net/get"
        logger.info("MyMemory API 翻译引擎初始化成功")

    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'zh') -> str:
        if not text or not text.strip():
            return ""

        # MyMemory 不支持 'auto'，强制使用 'en' 作为默认源语言
        if source_lang.lower() == 'auto':
            source_lang = 'en'
            logger.debug("MyMemory 不支持 'auto'，已自动切换源语言为 'en'")

        target = 'zh-CN' if target_lang == 'zh' else target_lang
        params = {'q': text, 'langpair': f"{source_lang}|{target}"}

        # 重试机制（最多 3 次）
        for attempt in range(3):
            try:
                resp = requests.get(self.api_url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                if 'responseData' in data and 'translatedText' in data['responseData']:
                    translated = data['responseData']['translatedText']
                    # 检查是否返回错误信息（某些情况下 MyMemory 会返回错误提示而非译文）
                    if translated.startswith("PLEASE SELECT") or "DISTINCT LANGUAGES" in translated:
                        logger.warning(f"MyMemory 返回错误提示: {translated[:50]}...")
                        # 如果因为语言对不支持，可以尝试交换源和目标（极少情况）
                        # 但更可能的是源语言不支持，因此继续尝试
                        # 这里直接返回原文，避免递归
                        return text
                    logger.info(f"MyMemory 翻译成功: {text[:30]}... -> {translated[:30]}...")
                    return translated
                else:
                    logger.error(f"MyMemory 返回异常数据结构: {data}")
                    return text
            except requests.exceptions.RequestException as e:
                logger.warning(f"MyMemory 请求失败 (尝试 {attempt+1}/3): {e}")
                if attempt < 2:
                    time.sleep(2)  # 等待后重试
                else:
                    logger.error(f"MyMemory 彻底失败: {e}")
                    return text
            except Exception as e:
                logger.error(f"MyMemory 未预期的错误: {e}")
                return text
        return text

    def get_supported_languages(self) -> List[str]:
        # MyMemory 支持 100+ 语言，这里只列出常用
        return ['en', 'zh', 'ja', 'ko', 'fr', 'de', 'es', 'it', 'pt', 'ru']


# ============================================================
# 2. DeepSeek 大模型引擎（高质量）
# ============================================================
class DeepSeekTranslateEngine(TranslationEngine):
    """
    使用 DeepSeek 大模型 API 进行翻译。
    - 需要 API Key 和账户余额。
    - 支持所有语言，翻译质量高，适合长句和专业术语。
    - 需网络，按 token 计费。
    - API Key 通过环境变量 DEEPSEEK_API_KEY 或构造参数传入。
    """

    # 语言代码到中文名称的映射（用于构建 prompt）
    _LANG_NAME_MAP = {
        'zh': '中文',
        'en': '英文',
        'ja': '日文',
        'ko': '韩文',
        'fr': '法文',
        'de': '德文',
        'es': '西班牙文',
        'it': '意大利文',
        'pt': '葡萄牙文',
        'ru': '俄文',
    }

    def __init__(self, api_key: str = None):
        if OpenAI is None:
            raise ImportError("openai 库未安装，请运行: pip install openai")
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("未找到 DeepSeek API Key，请在 .env 中设置 DEEPSEEK_API_KEY")
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com/v1")
        self.model = "deepseek-chat"
        logger.info("DeepSeek 翻译引擎初始化成功")

    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'zh') -> str:
        if not text or not text.strip():
            return ""

        # 构造语言名称
        src_name = '自动检测' if source_lang.lower() == 'auto' else self._LANG_NAME_MAP.get(
            source_lang.split('-')[0], source_lang
        )
        tgt_name = self._LANG_NAME_MAP.get(target_lang.split('-')[0], target_lang)

        instruction = f"将以下{src_name}文本翻译成{tgt_name}，只输出翻译结果，不要任何额外解释。"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是专业翻译助手。"},
                    {"role": "user", "content": f"{instruction}\n\n{text}"}
                ],
                temperature=0.3,
                stream=False
            )
            translated = response.choices[0].message.content.strip()
            logger.info(f"DeepSeek 翻译成功: {text[:30]}... -> {translated[:30]}...")
            return translated
        except Exception as e:
            error_msg = str(e).lower()
            # 明确区分余额不足和认证错误
            if "402" in error_msg or "insufficient balance" in error_msg:
                user_friendly = "⚠️ DeepSeek 账户余额不足，请充值后重试。"
                logger.error(f"DeepSeek 余额不足: {e}")
                return user_friendly
            elif "401" in error_msg or "invalid api key" in error_msg:
                user_friendly = "⚠️ DeepSeek API Key 无效，请检查 .env 文件。"
                logger.error(f"DeepSeek 认证失败: {e}")
                return user_friendly
            else:
                logger.error(f"DeepSeek 翻译失败: {e}")
                return text  # 其他错误返回原文

    def get_supported_languages(self) -> List[str]:
        # DeepSeek 理论上支持所有语言，这里列常见语言
        return ['en', 'zh', 'ja', 'ko', 'fr', 'de', 'es', 'it', 'pt', 'ru']


# ============================================================
# 3. DeepL 引擎（需 API Key）
# ============================================================
class DeepLEngine(TranslationEngine):
    """
    DeepL 翻译引擎（需 API Key）
    - 高质量翻译，支持多种语言。
    - 免费版有每月字符数限制，需注册获取 API Key。
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("DeepL API Key 不能为空")
        self.api_key = api_key
        self.api_url = "https://api-free.deepl.com/v2/translate"
        logger.info("DeepL 翻译引擎初始化成功")

    def translate(self, text: str, source_lang: str = 'auto', target_lang: str = 'ZH') -> str:
        if not text or not text.strip():
            return ""

        try:
            payload = {
                'auth_key': self.api_key,
                'text': text,
                'target_lang': target_lang.upper()
            }
            if source_lang.lower() != 'auto':
                payload['source_lang'] = source_lang.upper()

            resp = requests.post(self.api_url, data=payload, timeout=10)
            resp.raise_for_status()
            translated = resp.json()['translations'][0]['text']
            logger.info(f"DeepL 翻译成功: {text[:30]}... -> {translated[:30]}...")
            return translated
        except Exception as e:
            logger.error(f"DeepL 翻译失败: {e}")
            return text

    def get_supported_languages(self) -> List[str]:
        # DeepL 支持的语言（目标语言代码）
        return ['EN', 'ZH', 'JA', 'DE', 'FR', 'ES', 'IT', 'NL', 'PL', 'PT', 'RU']


# ============================================================
# 4. 离线翻译引擎（Argos Translate）
# ============================================================
class OfflineTranslateEngine(TranslationEngine):
    """
    离线翻译引擎，使用 Argos Translate。
    - 无需网络，完全离线。
    - 需要安装 argostranslate 并下载语言包。
    - 翻译质量一般，适合紧急情况或隐私敏感场景。
    """

    def __init__(self):
        try:
            import argostranslate.package
            import argostranslate.translate
            logger.info("离线翻译引擎初始化成功")
        except ImportError:
            logger.error("argostranslate 未安装，请运行: pip install argostranslate")
            raise

    def translate(self, text: str, source_lang: str = 'en', target_lang: str = 'zh') -> str:
        if not text or not text.strip():
            return ""

        try:
            import argostranslate.translate
            # 取语言代码的基础部分（如 zh-CN -> zh）
            source = source_lang.split('-')[0]
            target = target_lang.split('-')[0]
            translated = argostranslate.translate.translate(text, source, target)
            logger.info(f"离线翻译成功: {text[:30]}... -> {translated[:30]}...")
            return translated
        except Exception as e:
            logger.error(f"离线翻译失败: {e}")
            return text

    def get_supported_languages(self) -> List[str]:
        # 离线支持的语言取决于已安装的语言包，这里列常见
        return ['en', 'zh', 'ja', 'ko', 'fr', 'de', 'es', 'it', 'pt', 'ru']


# ============================================================
# 5. 工厂
# ============================================================
class TranslationEngineFactory:
    """翻译引擎工厂，根据类型创建对应的引擎实例"""

    @staticmethod
    def create_engine(engine_type: str, **kwargs) -> TranslationEngine:
        """
        创建翻译引擎实例
        :param engine_type: 引擎类型，支持 'google', 'deepseek', 'deepl', 'offline'
        :param kwargs: 额外参数（如 api_key）
        :return: TranslationEngine 实例
        """
        engine_type = engine_type.lower()
        logger.info(f"正在创建翻译引擎: {engine_type}")

        if engine_type == 'google':
            return GoogleTranslateEngine()
        elif engine_type == 'deepseek':
            return DeepSeekTranslateEngine(kwargs.get('api_key'))
        elif engine_type == 'deepl':
            return DeepLEngine(kwargs.get('api_key', ''))
        elif engine_type == 'offline':
            return OfflineTranslateEngine()
        else:
            raise ValueError(f"不支持的引擎类型: {engine_type}")