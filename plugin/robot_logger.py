import os
import json
import time
from datetime import datetime
import logging
from typing import Dict, Optional, Any, List

class RobotLogger:
    """机器人日志管理器，用于记录机器人处理的消息和结果"""
    
    def __init__(self) -> None:
        """初始化日志管理器"""
        # 基本日志目录
        self.log_dir = os.path.abspath("logs")
        
        # 创建日志目录
        self._create_log_dirs()
        
        # 配置标准Python日志
        self.logger = logging.getLogger("RobotLogger")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        
        # 创建日志处理器
        file_handler = logging.FileHandler(os.path.join(self.log_dir, "robot.log"))
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        self.logger.info("日志管理器初始化完成")
    
    def _create_log_dirs(self) -> None:
        """创建日志目录结构"""
        # 创建主日志目录
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        # 创建子目录
        subdirs = ["private_chat", "group_chat", "private_images", "group_images", "strategies"]
        for subdir in subdirs:
            path = os.path.join(self.log_dir, subdir)
            if not os.path.exists(path):
                os.makedirs(path)
    
    def _get_date_filename(self, prefix: str, extension: str = "txt") -> str:
        """获取基于日期的文件名
        :param prefix: 文件名前缀
        :param extension: 文件扩展名
        :return: 完整的文件名
        """
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{prefix}_{today}.{extension}"
    
    def log_private_chat(self, sender: str, content: str, ai_response: str) -> None:
        """记录私聊消息及回复
        :param sender: 发送者ID
        :param content: 消息内容
        :param ai_response: AI回复内容
        """
        filename = self._get_date_filename("private_chat")
        log_file = os.path.join(self.log_dir, "private_chat", filename)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"=== {timestamp} ===\n")
            f.write(f"发送者: {sender}\n")
            f.write(f"消息内容:\n{content}\n")
            f.write(f"AI回复:\n{ai_response}\n")
            f.write("="*50 + "\n\n")
        
        self.logger.info(f"已记录私聊消息 - 发送者: {sender}")
    
    def log_group_chat(self, group_id: str, sender: str, content: str, ai_response: str) -> None:
        """记录群聊消息及回复
        :param group_id: 群ID
        :param sender: 发送者ID
        :param content: 消息内容
        :param ai_response: AI回复内容
        """
        filename = self._get_date_filename("group_chat")
        log_file = os.path.join(self.log_dir, "group_chat", filename)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"=== {timestamp} ===\n")
            f.write(f"群ID: {group_id}\n")
            f.write(f"发送者: {sender}\n")
            f.write(f"消息内容:\n{content}\n")
            f.write(f"AI回复:\n{ai_response}\n")
            f.write("="*50 + "\n\n")
        
        self.logger.info(f"已记录群聊消息 - 群ID: {group_id}, 发送者: {sender}")
    
    def log_private_image(self, sender: str, image_path: str, ocr_text: str, ai_response: str) -> None:
        """记录私聊图片消息及处理结果
        :param sender: 发送者ID
        :param image_path: 图片保存路径
        :param ocr_text: OCR识别文本
        :param ai_response: AI回复内容
        """
        filename = self._get_date_filename("private_images")
        log_file = os.path.join(self.log_dir, "private_images", filename)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"=== {timestamp} ===\n")
            f.write(f"发送者: {sender}\n")
            f.write(f"图片路径: {image_path}\n")
            f.write(f"OCR文本:\n{ocr_text}\n")
            f.write(f"AI回复:\n{ai_response}\n")
            f.write("="*50 + "\n\n")
        
        self.logger.info(f"已记录私聊图片消息 - 发送者: {sender}")
    
    def log_group_image(self, group_id: str, sender: str, image_path: str, ocr_text: str, ai_response: str) -> None:
        """记录群聊图片消息及处理结果
        :param group_id: 群ID
        :param sender: 发送者ID
        :param image_path: 图片保存路径
        :param ocr_text: OCR识别文本
        :param ai_response: AI回复内容
        """
        filename = self._get_date_filename("group_images")
        log_file = os.path.join(self.log_dir, "group_images", filename)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"=== {timestamp} ===\n")
            f.write(f"群ID: {group_id}\n")
            f.write(f"发送者: {sender}\n")
            f.write(f"图片路径: {image_path}\n")
            f.write(f"OCR文本:\n{ocr_text}\n")
            f.write(f"AI回复:\n{ai_response}\n")
            f.write("="*50 + "\n\n")
        
        self.logger.info(f"已记录群聊图片消息 - 群ID: {group_id}, 发送者: {sender}")
    
    def log_strategy(self, source_type: str, source_id: str, sender: str, content: str, 
                    ai_response: str, strategy: Dict[str, Any], success: bool, message: str) -> None:
        """记录策略分析结果
        :param source_type: 来源类型（私聊/群聊）
        :param source_id: 来源ID（发送者ID或群ID）
        :param sender: 发送者ID
        :param content: 原始消息内容
        :param ai_response: AI回复内容
        :param strategy: 策略数据
        :param success: 策略处理是否成功
        :param message: 处理结果消息
        """
        filename = self._get_date_filename("strategy", "json")
        log_file = os.path.join(self.log_dir, "strategies", filename)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 准备日志数据
        log_data = {
            "timestamp": timestamp,
            "source_type": source_type,
            "source_id": source_id,
            "sender": sender,
            "content": content,
            "ai_response": ai_response,
            "strategy": strategy,
            "success": success,
            "message": message
        }
        
        # 读取现有数据
        try:
            if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = []
        except Exception as e:
            self.logger.error(f"读取策略日志出错: {str(e)}")
            data = []
        
        # 添加新数据
        data.append(log_data)
        
        # 写入文件
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"已记录策略分析 - 类型: {source_type}, ID: {source_id}")
        except Exception as e:
            self.logger.error(f"写入策略日志出错: {str(e)}") 