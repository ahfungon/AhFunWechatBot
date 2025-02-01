import os

class ImageOCR:
    """图片OCR插件，负责识别图片中的文字"""
    
    def __init__(self) -> None:
        """初始化OCR插件"""
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=True,  # 使用角度分类器
                lang="ch",  # 中英文识别
                show_log=False  # 不显示日志
            )
            self.available = True
            print("[图片OCR] 初始化完成")
        except ImportError:
            self.available = False
            print("[图片OCR] 错误: 请先安装paddleocr，命令：pip install paddleocr")
    
    def extract_text(self, image_path: str) -> str:
        """
        从图片中提取文字
        :param image_path: 图片路径
        :return: 提取的文字
        """
        if not self.available:
            print("[图片OCR] 错误: OCR未正确初始化")
            return ""
            
        if not os.path.exists(image_path):
            print(f"[图片OCR] 错误: 图片不存在: {image_path}")
            return ""
            
        try:
            print(f"[图片OCR] 开始识别图片: {image_path}")
            result = self.ocr.ocr(image_path, cls=True)
            
            if not result or not result[0]:
                print("[图片OCR] 未识别到文字")
                return ""
            
            texts = []
            for line in result[0]:
                text = line[1][0]  # 获取识别的文字
                confidence = line[1][1]  # 获取置信度
                texts.append(text)
                print(f"[图片OCR] 识别文字: {text} (置信度: {confidence:.2f})")
            
            full_text = "\n".join(texts)
            print(f"[图片OCR] 识别完成，共 {len(texts)} 行文字")
            return full_text
            
        except Exception as e:
            print(f"[图片OCR] 识别出错: {str(e)}")
            return "" 