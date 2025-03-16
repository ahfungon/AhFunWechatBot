import os
import sys
import pytesseract
from PIL import Image

class ImageOCR:
    """图片OCR插件，负责识别图片中的文字"""
    
    def __init__(self) -> None:
        """初始化OCR插件"""
        try:
            # 设置Tesseract可执行文件路径
            if sys.platform == "win32":
                # Windows系统下的默认安装路径
                tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                if os.path.exists(tesseract_cmd):
                    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                    print(f"[图片OCR] 已设置Tesseract路径: {tesseract_cmd}")
                else:
                    print(f"[图片OCR] 警告: 未在默认路径找到Tesseract，将尝试使用环境变量中的设置")
            
            # 检查Tesseract版本和语言包
            version = pytesseract.get_tesseract_version()
            languages = pytesseract.get_languages()
            
            if 'chi_sim' not in languages:
                raise Exception("未安装中文语言包(chi_sim)，请重新安装Tesseract并选择安装中文语言包")
                
            self.available = True
            print(f"[图片OCR] 初始化完成")
            print(f"[图片OCR] Tesseract版本: {version}")
            print(f"[图片OCR] 可用语言包: {', '.join(languages)}")
            
        except Exception as e:
            self.available = False
            print("[图片OCR] 错误: 请确保正确安装Tesseract-OCR和pytesseract")
            print("Windows用户请：")
            print("1. 从 https://github.com/UB-Mannheim/tesseract/wiki 下载并安装Tesseract")
            print("2. 安装时选择安装中文语言包")
            print("3. 将安装路径(默认为C:\\Program Files\\Tesseract-OCR)添加到系统环境变量PATH中")
            print("4. 重启应用程序")
            print(f"[图片OCR] 错误详情: {str(e)}")
    
    def extract_text(self, image_path: str) -> str:
        """
        从图片中提取文字
        :param image_path: 图片路径
        :return: 提取的文字
        """
        if not self.available:
            print("[图片OCR] 错误: OCR未正确初始化，请查看上方的安装说明")
            if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                self.robot.log_to_gui("[图片OCR] 错误: OCR未正确初始化，请查看上方的安装说明", "ERROR")
            return ""
            
        if not os.path.exists(image_path):
            print(f"[图片OCR] 错误: 图片不存在: {image_path}")
            if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                self.robot.log_to_gui(f"[图片OCR] 错误: 图片不存在: {image_path}", "ERROR")
            return ""
            
        try:
            print(f"[图片OCR] 开始识别图片: {image_path}")
            if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                self.robot.log_to_gui(f"[图片OCR] 开始识别图片: {image_path}", "INFO")
            
            # 打开图片
            image = Image.open(image_path)
            
            # 使用Tesseract进行OCR识别
            # 设置识别语言为中文和英文
            text = pytesseract.image_to_string(
                image, 
                lang='chi_sim+eng',
                config='--psm 3'  # 自动检测页面分割和方向
            )
            
            if not text.strip():
                print("[图片OCR] 未识别到文字")
                if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                    self.robot.log_to_gui("[图片OCR] 未识别到文字", "WARNING")
                return ""
            
            # 处理识别结果
            lines = text.strip().split('\n')
            lines = [line.strip() for line in lines if line.strip()]
            
            print(f"[图片OCR] 识别完成，共 {len(lines)} 行文字")
            if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                self.robot.log_to_gui(f"[图片OCR] 识别完成，共 {len(lines)} 行文字", "INFO")
            
            return '\n'.join(lines)
            
        except Exception as e:
            print(f"[图片OCR] 识别出错: {str(e)}")
            if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                self.robot.log_to_gui(f"[图片OCR] 识别出错: {str(e)}", "ERROR")
            return ""

# 使用百度OCR替代本地OCR
try:
    from plugin.baidu_ocr import ImageOCR as BaiduImageOCR
    # 保存原始的OCR类，以便需要时可以回退
    LocalImageOCR = ImageOCR
    # 重写ImageOCR类
    ImageOCR = BaiduImageOCR
    print("[图片OCR] 已切换到百度OCR服务")
except ImportError:
    print("[图片OCR] 警告: 无法导入百度OCR，继续使用本地OCR") 