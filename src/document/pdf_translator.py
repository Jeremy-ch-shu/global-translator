import fitz  # PyMuPDF
from loguru import logger

def translate_pdf(file_path: str, engine, target_lang: str = 'zh-CN'):
    """翻译PDF文档并保留布局"""
    
    doc = fitz.open(file_path)
    output_doc = fitz.open()
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 提取文本块及其位置[reference:22]
        text_blocks = page.get_text("dict")["blocks"]
        
        # 创建新页面
        new_page = output_doc.new_page(width=page.rect.width, height=page.rect.height)
        
        for block in text_blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        if text.strip():
                            # 翻译文本
                            translated = engine.translate(text, 'auto', target_lang)
                            
                            # 在相同位置插入翻译文本
                            bbox = span["bbox"]
                            font_size = span["size"]
                            color = span["color"]
                            
                            new_page.insert_text(
                                (bbox[0], bbox[3]),  # 左下角坐标
                                translated,
                                fontsize=font_size,
                                color=color
                            )
    
    # 保存
    output_path = file_path.replace('.pdf', '_translated.pdf')
    output_doc.save(output_path)
    output_doc.close()
    logger.info(f"PDF翻译完成: {output_path}")
    return output_path