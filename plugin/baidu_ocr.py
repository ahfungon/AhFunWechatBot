import os
import requests
import base64
import json
from PIL import Image

class BaiduOCR:
    """百度OCR插件，负责识别图片中的文字"""
    
    def __init__(self) -> None:
        """初始化百度OCR插件"""
        # 百度OCR API凭证
        self.app_id = '6516508'
        self.api_key = 'gZndmnu0pn0RqlFVQN8eLctP'
        self.secret_key = 'sG3owM5ITEbjW2Md66a9abBjYXCDg6RX'
        self.access_token = None
        self.token_expire_time = 0
        
        # 设置robot引用，将在Robot类中设置
        self.robot = None
        
        try:
            # 初始获取access token
            self._get_access_token()
            
            if self.access_token:
                self.available = True
                print(f"[百度OCR] 初始化完成，已连接百度OCR服务")
            else:
                self.available = False
                print("[百度OCR] 错误: 无法获取百度OCR授权令牌")
                
        except Exception as e:
            self.available = False
            print("[百度OCR] 错误: 百度OCR初始化失败")
            print(f"[百度OCR] 错误详情: {str(e)}")
    
    def _get_access_token(self):
        """获取百度OCR API的access token"""
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key
        }
        
        try:
            response = requests.post(url, params=params)
            result = response.json()
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                print(f"[百度OCR] 成功获取百度OCR授权令牌")
                return True
            else:
                print(f"[百度OCR] 获取授权令牌失败: {result}")
                return False
                
        except Exception as e:
            print(f"[百度OCR] 获取授权令牌出错: {str(e)}")
            return False
    
    def extract_text(self, image_path: str) -> str:
        """
        使用百度OCR API从图片中提取文字
        :param image_path: 图片路径
        :return: 提取的文字
        """
        if not self.available:
            print("[图片OCR] 错误: 百度OCR服务未正确初始化")
            if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                self.robot.log_to_gui("[图片OCR] 错误: 百度OCR服务未正确初始化", "ERROR")
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
            
            # 读取图片并转为base64编码
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # 调用百度OCR API的通用文字识别（高精度版）
            request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
            
            params = {
                "access_token": self.access_token
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                "image": image_data,
                # 可选参数
                "language_type": "CHN_ENG", # 中英文混合
                "detect_direction": "true", # 检测图像方向
                "probability": "true",      # 返回识别结果的置信度
            }
            
            response = requests.post(request_url, data=data, params=params, headers=headers)
            result = response.json()
            
            # 检查是否需要重新获取token
            if "error_code" in result and result["error_code"] == 110:
                print("[图片OCR] 授权令牌已过期，正在重新获取")
                if self._get_access_token():
                    # 重试请求
                    params["access_token"] = self.access_token
                    response = requests.post(request_url, data=data, params=params, headers=headers)
                    result = response.json()
            
            # 处理识别结果
            if "words_result" in result:
                words_result = result["words_result"]
                if not words_result:
                    print("[图片OCR] 未识别到文字")
                    if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                        self.robot.log_to_gui("[图片OCR] 未识别到文字", "WARNING")
                    return ""
                
                # 提取识别文本
                lines = [item["words"] for item in words_result]
                
                print(f"[图片OCR] 识别完成，共 {len(lines)} 行文字")
                if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                    self.robot.log_to_gui(f"[图片OCR] 识别完成，共 {len(lines)} 行文字", "INFO")
                
                return '\n'.join(lines)
            else:
                error_msg = f"识别失败: {result.get('error_msg', '未知错误')}"
                print(f"[图片OCR] {error_msg}")
                if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                    self.robot.log_to_gui(f"[图片OCR] {error_msg}", "ERROR")
                return ""
            
        except Exception as e:
            print(f"[图片OCR] 识别出错: {str(e)}")
            if hasattr(self, "robot") and self.robot and hasattr(self.robot, "log_to_gui"):
                self.robot.log_to_gui(f"[图片OCR] 识别出错: {str(e)}", "ERROR")
            return ""

# 为了保持与原有代码兼容，创建一个继承类
class ImageOCR(BaiduOCR):
    """兼容原有代码的ImageOCR类，使用百度OCR实现"""
    pass
