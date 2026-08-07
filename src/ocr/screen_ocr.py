import pytesseract
import easyocr
from PIL import Image
import numpy as np
from loguru import logger

class ScreenOCR:
    """屏幕OCR识别"""
    
    def __init__(self, engine: str = 'tesseract', lang: str = 'eng+chi_sim'):
        self.engine_type = engine
        self.lang = lang
        
        if engine == 'easyocr':
            # EasyOCR支持更多语言，无需额外安装
            self.reader = easyocr.Reader([lang.replace('+', ',').split(',')])
            logger.info("EasyOCR初始化完成")
        else:
            # Tesseract需要提前安装[reference:13]
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            logger.info("Tesseract初始化完成")
    
    def extract_text(self, image: Image.Image) -> str:
        """从图片中提取文字"""
        try:
            if self.engine_type == 'easyocr':
                # EasyOCR需要numpy数组
                img_array = np.array(image)
                results = self.reader.readtext(img_array)
                text = ' '.join([result[1] for result in results])
            else:
                # Tesseract OCR[reference:15]
                text = pytesseract.image_to_string(image, lang=self.lang)
            
            logger.info(f"OCR识别结果: {text[:100]}...")
            return text.strip()
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            return ""
    
    def extract_text_with_boxes(self, image: Image.Image) -> list:
        """提取文字及其位置信息"""
        if self.engine_type == 'easyocr':
            results = self.reader.readtext(np.array(image))
            return [{'text': r[1], 'bbox': r[0], 'confidence': r[2]} for r in results]
        else:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            boxes = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 30:  # 置信度过滤
                    boxes.append({
                        'text': data['text'][i],
                        'bbox': (data['left'][i], data['top'][i], 
                                data['width'][i], data['height'][i]),
                        'confidence': int(data['conf'][i])
                    })
            return boxes