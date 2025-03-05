#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from configuration import Config
from robot import Robot
import logging
from wcferry import WxMsg
from constants import ChatType
import os
import time
import shutil
import threading

# 模拟的WCF类
class MockWcf:
    def __init__(self):
        self._wxid = "wxid_test123"  # 模拟的微信ID
        self.msg_queue = []  # 用于存储消息的队列
        self.receiving_msg = True  # 消息接收状态
        self.last_image_path = None  # 用于存储图片路径
        self.gui = None  # 添加对GUI的引用
        
        # 创建图片保存目录
        self.img_dir = os.path.abspath("img")
        if not os.path.exists(self.img_dir):
            os.makedirs(self.img_dir)
            print(f"[模拟WCF] 创建图片目录: {self.img_dir}")

    def get_self_wxid(self):
        return self._wxid

    def get_msg(self):
        return None if not self.msg_queue else self.msg_queue.pop(0)

    def is_receiving_msg(self):
        return self.receiving_msg

    def enable_receiving_msg(self):
        self.receiving_msg = True

    def disable_receiving_msg(self):
        self.receiving_msg = False

    def enable_recv_msg(self, callback):
        self.receiving_msg = True
        return True

    def send_text(self, msg: str, receiver: str, at_list=None):
        """发送文本消息的模拟方法"""
        print(f"[模拟WCF] 发送文本消息: {msg} 到 {receiver}, at列表={at_list}")
        
        # 如果有GUI引用，在GUI中显示机器人回复
        if hasattr(self, "gui") and self.gui:
            self.gui.root.after(0, lambda: self.gui.add_robot_message(msg))
            
        return True

    def get_alias_in_chatroom(self, wxid, room_id):
        return f"用户{wxid}"

    def query_sql(self, db, sql):
        # 返回一个模拟的联系人列表
        return [{"UserName": "test_user", "NickName": "测试用户"}]
        
    def get_user_img(self, msg_id):
        """模拟获取图片，直接返回图片路径"""
        # 直接返回最后一次选择的图片路径
        if hasattr(self, "last_image_path") and self.last_image_path:
            print(f"[模拟WCF] 获取图片: msg_id={msg_id}, 返回路径={self.last_image_path}")
            return self.last_image_path
        print(f"[模拟WCF] 获取图片失败: msg_id={msg_id}")
        return None
        
    def download_attach(self, id, thumb, extra):
        """模拟下载附件"""
        print(f"[模拟WCF] 模拟下载附件: id={id}, thumb={thumb}, extra={extra}")
        
        # 确保extra路径存在
        if extra and os.path.exists(os.path.dirname(extra)):
            # 创建一个空文件作为占位符
            try:
                with open(extra, 'w') as f:
                    f.write(f"Mock attachment for message {id}")
                print(f"[模拟WCF] 创建附件占位文件: {extra}")
                return 0  # 返回成功
            except Exception as e:
                print(f"[模拟WCF] 创建附件占位文件失败: {str(e)}")
                return -1
        else:
            print(f"[模拟WCF] 附件路径不存在: {extra}")
            return -1
        
    def download_image(self, id, extra, dir):
        """模拟下载图片"""
        print(f"[模拟WCF] 模拟下载图片: id={id}, extra={extra}, dir={dir}")
        
        if not hasattr(self, "last_image_path") or not self.last_image_path or not os.path.exists(self.last_image_path):
            print(f"[模拟WCF] 错误: 图片路径不存在或无效")
            return None
        
        # 创建年月子目录
        now = time.localtime()
        year_month = f"{now.tm_year}-{now.tm_mon:02d}"
        year_month_dir = os.path.join(dir, year_month)
        if not os.path.exists(year_month_dir):
            os.makedirs(year_month_dir)
        
        # 复制图片到目标目录
        filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{os.path.basename(self.last_image_path)}"
        target_path = os.path.join(year_month_dir, filename)
        try:
            shutil.copy2(self.last_image_path, target_path)
            print(f"[模拟WCF] 图片已保存到: {target_path}")
            return target_path
        except Exception as e:
            print(f"[模拟WCF] 保存图片出错: {str(e)}")
            return None

# 模拟的消息类，用于模拟 WxMsg
class MockWxMsg(WxMsg):
    def __init__(self, content, sender, roomid, msg_type=0x01):
        # 确保ID是整数
        timestamp_id = int(time.time())
        self.id = timestamp_id
        self.type = msg_type     # 消息类型
        self.sender = sender     # 发送者
        self.roomid = roomid     # 群id
        self.content = content   # 消息内容
        self.sign = ""          # 消息签名
        self.thumb = ""         # 图片缩略图
        self.extra = ""         # 附加信息
        self.timestamp = timestamp_id  # 时间戳
        print(f"[MockWxMsg] 创建消息: id={self.id}, type={self.type}, sender={self.sender}")

    def __str__(self):
        return f"[{self.type}]{'[Group]' if self.from_group() else ''} {self.sender}: {self.content}"

    def from_group(self):
        """是否是群消息"""
        return bool(self.roomid)

    def from_self(self):
        """是否是自己发送的消息"""
        return self.sender == "my_wechat_id"

    def is_at(self, wxid):
        """是否@了某人"""
        # 更加健壮的@检测
        return f"@{wxid}" in self.content or f"@{wxid} " in self.content or f" @{wxid}" in self.content

class ChatGUI:
    def __init__(self):
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("微信机器人模拟器")
        self.root.geometry("1200x800")  # 增加窗口宽度，以便显示更多信息
        
        # 设置样式
        self.setup_styles()
        
        # 设置颜色
        self.bg_color = "#f5f5f5"
        self.text_bg = "#ffffff"
        self.button_bg = "#1aad19"  # 微信绿
        self.button_fg = "#ffffff"
        self.status_bg = "#e6f3ff"
        
        # 设置字体
        self.default_font = ("微软雅黑", 9)
        self.bold_font = ("微软雅黑", 9, "bold")
        self.header_font = ("微软雅黑", 10, "bold")
        
        # 设置进度条相关变量
        self.processing = False
        self.progress_value = 0
        self.progress_step = 2
        self.progress_max = 100
        self.animation_chars = ["🌕", "🌖", "🌗", "🌘", "🌑", "🌒", "🌓", "🌔"]
        self.animation_index = 0
        self.animation_timer = None
        
        # 设置进度描述列表
        self.progress_descriptions = [
            "正在初始化...",
            "正在分析消息内容...",
            "正在调用AI模型...",
            "AI正在思考中...",
            "正在处理AI回复...",
            "正在提取策略信息...",
            "正在保存策略数据...",
            "处理完成"
        ]
        
        # 创建模拟的WCF对象
        self.mock_wcf = MockWcf()
        
        # 创建配置对象
        self.config = Config()
        
        # 把模拟的群ID添加到响应群列表
        if not hasattr(self.config, 'GROUPS'):
            self.config.GROUPS = []
        self.config.GROUPS.append("group1")
        
        # 创建机器人对象 - 使用智谱AI
        chat_type = ChatType.ZhiPu.value
        self.robot = Robot(self.config, self.mock_wcf, chat_type)
        
        # 设置机器人的GUI引用
        self.robot.gui = self
        
        # 创建聊天记录列表
        self.chat_log = []
        
        # 创建UI组件
        self.create_widgets()
        
        # 显示启动信息
        self.show_startup_info()
    
    def setup_styles(self):
        """设置样式"""
        self.style = ttk.Style()
        
        # 进度条样式
        self.style.configure(
            "Processing.Horizontal.TProgressbar", 
            background='#49b66e',  # 微信绿色
            troughcolor='#e6e6e6', 
            bordercolor='#e6e6e6',
            lightcolor='#49b66e', 
            darkcolor='#49b66e'
        )
        
        # 聊天框架样式
        self.style.configure(
            "ChatFrame.TFrame",
            background="#f5f5f5"  # 微信背景色
        )
        
        # 按钮样式
        self.style.configure(
            "WeChatButton.TButton",
            background="#49b66e",  # 绿色背景
            foreground="#ffffff",  # 白色文字
            font=("微软雅黑", 9)
        )
        
        # 由于ttk按钮在Windows上样式有限制，使用普通tk按钮替代
        self.button_bg = "#49b66e"  # 微信绿色
        self.button_fg = "#ffffff"  # 白色文字

    def show_startup_info(self):
        """显示启动信息"""
        info = [
            "=== 微信机器人模拟器启动 ===",
            "功能说明：",
            "1. 默认使用智谱AI模型",
            "2. 支持文本消息和图片消息",
            "3. 支持私聊和群聊模式",
            "",
            "快捷键：",
            "- Enter: 发送消息",
            "- Shift+Enter: 换行",
            "",
            "注意事项：",
            "- 群聊模式下会自动添加@机器人",
            "- 发送 ^更新$ 可以重新加载配置",
            "- 图片会保存在img目录下",
            "=========================="
        ]
        
        # 将消息以系统消息的形式添加到聊天记录
        for line in info:
            if line.strip():
                self.add_system_message(line)
            else:
                # 空行，添加间隔
                self.chat_text.update_idletasks()

    def handle_return(self, event):
        """处理回车键"""
        if event.widget == self.message_text:
            self.send_message()
            return "break"

    def handle_shift_return(self, event):
        """处理Shift+回车键"""
        if event.widget == self.message_text:
            self.message_text.insert(tk.INSERT, "\n")
            return "break"

    def create_widgets(self):
        # 创建左右分栏
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧日志面板 - 增加宽度比例
        self.left_frame = ttk.Frame(self.paned_window, width=600)
        
        # 右侧聊天面板
        self.right_frame = ttk.Frame(self.paned_window, width=400)
        
        # 添加到分栏
        self.paned_window.add(self.left_frame, weight=6)  # 增加左侧权重
        self.paned_window.add(self.right_frame, weight=4)
        
        # 左侧日志面板标题
        self.log_title_frame = ttk.Frame(self.left_frame)
        self.log_title_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.log_title = ttk.Label(
            self.log_title_frame, 
            text="处理日志与分析结果", 
            font=self.header_font,
            foreground="#0066CC"
        )
        self.log_title.pack(side=tk.LEFT, padx=5)
        
        # 左侧日志文本框
        self.chat_text_frame = ttk.Frame(self.left_frame)
        self.chat_text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建带滚动条的文本框
        self.chat_text = scrolledtext.ScrolledText(
            self.chat_text_frame,
            wrap=tk.WORD,
            bg=self.text_bg,
            font=self.default_font,
            padx=10,
            pady=10
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        
        # 右侧聊天面板标题
        self.chat_title_frame = ttk.Frame(self.right_frame)
        self.chat_title_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.chat_title = ttk.Label(
            self.chat_title_frame, 
            text="微信聊天模拟", 
            font=self.header_font,
            foreground="#1aad19"
        )
        self.chat_title.pack(side=tk.LEFT, padx=5)
        
        # 右侧聊天类型选择
        self.chat_type_frame = ttk.Frame(self.right_frame)
        self.chat_type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.chat_type_label = ttk.Label(
            self.chat_type_frame, 
            text="聊天类型:", 
            font=self.default_font
        )
        self.chat_type_label.pack(side=tk.LEFT, padx=5)
        
        self.chat_type = tk.StringVar(value="private")
        
        self.private_radio = ttk.Radiobutton(
            self.chat_type_frame, 
            text="私聊", 
            variable=self.chat_type, 
            value="private"
        )
        self.private_radio.pack(side=tk.LEFT, padx=5)
        
        self.group_radio = ttk.Radiobutton(
            self.chat_type_frame, 
            text="群聊", 
            variable=self.chat_type, 
            value="group"
        )
        self.group_radio.pack(side=tk.LEFT, padx=5)
        
        # 发送者输入框
        self.sender_frame = ttk.Frame(self.right_frame)
        self.sender_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.sender_label = ttk.Label(
            self.sender_frame, 
            text="发送者:", 
            font=self.default_font
        )
        self.sender_label.pack(side=tk.LEFT, padx=5)
        
        self.sender_entry = ttk.Entry(self.sender_frame)
        self.sender_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.sender_entry.insert(0, "test_user")
        
        # 消息输入框
        self.message_frame = ttk.Frame(self.right_frame)
        self.message_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.message_label = ttk.Label(
            self.message_frame, 
            text="消息内容:", 
            font=self.default_font
        )
        self.message_label.pack(anchor=tk.W, padx=5, pady=2)
        
        self.message_text = scrolledtext.ScrolledText(
            self.message_frame,
            height=10,
            wrap=tk.WORD,
            bg=self.text_bg,
            font=self.default_font
        )
        self.message_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 绑定快捷键
        self.message_text.bind("<Return>", self.handle_return)
        self.message_text.bind("<Shift-Return>", self.handle_shift_return)
        
        # 状态框架（包含进度条和状态文本）
        self.status_frame = ttk.Frame(self.root, style="Status.TFrame")
        
        # 创建进度条容器
        self.progress_container = ttk.Frame(self.status_frame)
        self.progress_container.pack(fill=tk.X, padx=10, pady=5)
        
        # 创建进度标签
        self.progress_label = ttk.Label(
            self.progress_container, 
            text="0%", 
            font=self.bold_font
        )
        self.progress_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 创建进度条
        self.progress_style = ttk.Style()
        self.progress_style.configure(
            "Custom.Horizontal.TProgressbar", 
            thickness=25,
            troughcolor="#E0E0E0",
            background="#1aad19"
        )
        
        self.progress_bar = ttk.Progressbar(
            self.progress_container,
            orient=tk.HORIZONTAL,
            length=100,
            mode='determinate',
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 创建状态标签
        self.status_label = ttk.Label(
            self.status_frame, 
            text="就绪", 
            font=self.default_font,
            padding=(10, 5)
        )
        self.status_label.pack(fill=tk.X)
        
        # 按钮框架
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 图片按钮
        image_button = tk.Button(
            self.button_frame, 
            text="发送图片", 
            command=self.send_image,
            bg=self.button_bg,
            fg=self.button_fg,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            font=self.default_font
        )
        image_button.pack(side=tk.LEFT, padx=5)
        
        # 发送消息按钮
        send_button = tk.Button(
            self.button_frame, 
            text="发送消息", 
            command=self.send_message,
            bg=self.button_bg,
            fg=self.button_fg,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            font=self.default_font
        )
        send_button.pack(side=tk.LEFT, padx=5)
        
        # 清空按钮
        clear_button = tk.Button(
            self.button_frame, 
            text="清空记录", 
            command=self.clear_chat,
            bg=self.button_bg,
            fg=self.button_fg,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            font=self.default_font
        )
        clear_button.pack(side=tk.LEFT, padx=5)

    def start_progress(self, status_text="正在处理消息..."):
        """开始进度条并显示状态文本"""
        self.processing = True
        
        # 设置状态文本
        self.status_label.config(text=status_text)
        
        # 显示状态框架
        self.status_frame.pack(fill=tk.X, pady=(0, 5), padx=5)
        
        # 启动进度条
        self.progress_bar.start(10)  # 动画速度
        
    def stop_progress(self):
        """停止进度条"""
        self.processing = False
        self.progress_bar.stop()
        self.status_frame.pack_forget()
    
    def add_log_message(self, text, level="INFO"):
        """添加日志消息到界面"""
        # 获取当前时间
        time_str = time.strftime("%H:%M:%S")
        
        # 确定日志级别对应的标签
        level_tag = "info"
        if level == "ERROR":
            level_tag = "error"
        elif level == "WARNING":
            level_tag = "warning"
        elif level == "DEBUG":
            level_tag = "debug"
        elif level == "AI":
            level_tag = "ai_response"
        elif level == "STRATEGY":
            level_tag = "strategy"
        
        # 在文本末尾插入新行
        self.chat_text.insert(tk.END, f"[{time_str}] ", "time")
        self.chat_text.insert(tk.END, f"[{level}] ", level_tag)
        self.chat_text.insert(tk.END, f"{text}\n", "content")
        
        # 滚动到底部
        self.chat_text.see(tk.END)

    def add_section_header(self, title):
        """添加带有分隔线的章节标题"""
        self.chat_text.insert(tk.END, "\n" + "="*50 + "\n", "content")
        self.chat_text.insert(tk.END, f" {title} \n", "section_header")
        self.chat_text.insert(tk.END, "="*50 + "\n", "content")
        self.chat_text.see(tk.END)

    def process_message_thread(self, msg):
        """在线程中处理消息"""
        try:
            # 根据消息类型显示不同的状态文本
            status_text = "正在处理图片..." if msg.type == 0x03 else "正在分析消息..."
            
            # 在主线程中更新状态
            self.root.after(0, lambda: self.update_status(status_text, True))
            
            # 记录处理开始的更详细日志
            msg_type_str = "图片" if msg.type == 0x03 else "文本"
            room_str = f"群聊({msg.roomid})" if msg.roomid else "私聊"
            self.root.after(0, lambda: self.add_log_message(
                f"开始处理{msg_type_str}消息: ID={msg.id}, 类型={msg_type_str}, 发送者={msg.sender}, 类型={room_str}",
                "INFO"
            ))
            
            # 记录消息内容
            content_preview = msg.content
            if msg.type == 0x03:
                content_preview = f"[图片消息] 路径={self.mock_wcf.last_image_path}" if hasattr(self.mock_wcf, "last_image_path") else "[图片消息]"
                # 添加图片路径详细信息
                self.root.after(0, lambda: self.add_log_message(f"图片完整路径: {self.mock_wcf.last_image_path}", "INFO"))
            else:
                content_preview = f"{msg.content[:50]}{'...' if len(msg.content) > 50 else ''}"
            
            self.root.after(0, lambda: self.add_log_message(f"消息内容: {content_preview}", "INFO"))
            
            # 处理开始前记录
            self.root.after(0, lambda: self.add_log_message("交给机器人处理中...", "INFO"))
            
            # 更新状态为处理中
            self.root.after(0, lambda: self.update_status("机器人处理中...", True))
            
            # 处理消息前记录原始消息内容
            if msg.type == 0x03:
                # 图片消息处理前，添加OCR处理章节
                self.root.after(0, lambda: self.add_section_header("图片OCR处理"))
                
                # 保存图片路径到wcf对象，以便get_user_img方法使用
                if hasattr(self.mock_wcf, "last_image_path") and self.mock_wcf.last_image_path:
                    # 记录图片保存路径
                    self.root.after(0, lambda: self.add_log_message(f"图片路径: {self.mock_wcf.last_image_path}", "INFO"))
            else:
                # 文本消息处理前，添加AI分析章节
                self.root.after(0, lambda: self.add_section_header("AI分析处理"))
                
                # 记录完整的消息内容
                self.root.after(0, lambda: self.add_log_message(f"完整消息内容:\n{msg.content}", "INFO"))
            
            # 处理消息
            self.robot.onMsg(msg)
            
            # 在主线程中更新状态为完成
            self.root.after(0, lambda: self.update_status("处理完成", False))
            
            # 添加处理完成日志
            self.root.after(0, lambda: self.add_log_message(f"消息处理完成: ID={msg.id}", "INFO"))
        except Exception as e:
            print(f"处理消息出错: {e}")
            # 记录详细错误日志
            error_msg = f"处理消息出错: {str(e)}"
            import traceback
            trace_info = traceback.format_exc()
            self.root.after(0, lambda: self.add_log_message(error_msg, "ERROR"))
            self.root.after(0, lambda: self.add_log_message(f"错误详情: {trace_info}", "ERROR"))
            
            # 更新状态为错误
            self.root.after(0, lambda: self.update_status("处理出错", False))

    def add_system_message(self, text):
        """添加系统消息"""
        time_str = time.strftime("%H:%M:%S")
        
        # 在文本末尾插入新行
        self.chat_text.insert(tk.END, f"[{time_str}] ", "time")
        self.chat_text.insert(tk.END, f"{text}\n", "system")
        
        # 滚动到底部
        self.chat_text.see(tk.END)

    def add_user_message(self, sender, text, is_self=False):
        """添加用户消息"""
        time_str = time.strftime("%H:%M:%S")
        
        # 添加发送时间和发送者
        self.chat_text.insert(tk.END, f"[{time_str}] ", "time")
        
        if is_self:
            self.chat_text.insert(tk.END, f"我: ", "user")
        else:
            self.chat_text.insert(tk.END, f"{sender}: ", "user")
            
        # 添加消息内容
        self.chat_text.insert(tk.END, f"{text}\n", "content")
        
        # 滚动到底部
        self.chat_text.see(tk.END)

    def add_robot_message(self, text):
        """添加机器人消息"""
        time_str = time.strftime("%H:%M:%S")
        
        # 添加发送时间和发送者
        self.chat_text.insert(tk.END, f"[{time_str}] ", "time")
        self.chat_text.insert(tk.END, f"机器人: ", "robot")
        
        # 添加消息内容
        self.chat_text.insert(tk.END, f"{text}\n", "content")
        
        # 滚动到底部
        self.chat_text.see(tk.END)

    def send_image(self):
        """发送图片消息"""
        if self.processing:
            # 如果正在处理消息，不允许发送
            self.add_system_message("正在处理消息，请稍候...")
            return
            
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            sender = self.sender_entry.get().strip()
            if not sender:
                return
            
            # 保存图片路径到wcf对象，以便get_user_img方法使用
            self.mock_wcf.last_image_path = file_path
            
            # 创建一个临时的extra路径，模拟微信的图片路径
            now = time.localtime()
            year = now.tm_year
            month = f"{now.tm_mon:02d}"
            image_hash = f"mock_{int(time.time())}"
            extra_path = os.path.join(self.mock_wcf.img_dir, f"{year}-{month}", f"{image_hash}.dat")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(extra_path), exist_ok=True)
            
            # 创建空文件作为占位符
            with open(extra_path, 'w') as f:
                f.write('')
            
            # 创建图片消息对象（type=3 表示图片消息）
            if self.chat_type.get() == "private":
                msg = MockWxMsg(content="[图片]", sender=sender, roomid="", msg_type=0x03)
            else:
                msg = MockWxMsg(content="[图片]", sender=sender, roomid="group1", msg_type=0x03)
            
            # 设置额外信息
            msg.extra = extra_path
            
            # 记录消息 - 以微信风格添加
            self.add_user_message(sender, f"[图片] {os.path.basename(file_path)}", True)
            print(f"[GUI] 发送图片消息: id={msg.id}, extra={msg.extra}, 原始路径={file_path}")
            
            # 启动线程处理消息，使用特定状态文本
            thread = threading.Thread(target=self.process_message_thread, args=(msg,))
            thread.daemon = True
            thread.start()

    def update_status(self, status_text, progress=True):
        """更新状态文本，可选择是否显示进度条"""
        self.status_label.config(text=status_text)
        
        # 如果需要进度条但当前没有显示
        if progress and not self.processing:
            self.start_progress(status_text)
        elif not progress and self.processing:
            self.stop_progress()
        elif progress and self.processing:
            # 仅更新文本
            self.status_label.config(text=status_text)
        elif not progress and not self.processing:
            # 显示状态但不显示进度条
            self.status_frame.pack(fill=tk.X, pady=(0, 5), padx=5)
            self.progress_bar.pack_forget()
        
        # 更新UI
        self.status_frame.update_idletasks()

    def send_message(self):
        if self.processing:
            # 如果正在处理消息，不允许发送
            self.add_system_message("正在处理消息，请稍候...")
            return
            
        sender = self.sender_entry.get().strip()
        content = self.message_text.get("1.0", tk.END).strip()
        
        if not sender or not content:
            return
            
        # 创建消息对象
        if self.chat_type.get() == "private":
            msg = MockWxMsg(content=content, sender=sender, roomid="")
        else:
            # 如果是群聊，自动添加@机器人
            if not content.startswith(f"@{self.robot.wxid}"):
                content = f"@{self.robot.wxid} {content}"
            msg = MockWxMsg(content=content, sender=sender, roomid="group1")
        
        # 记录消息 - 以微信风格添加
        self.add_user_message(sender, content, True)
        
        # 添加日志记录
        msg_type = "私聊" if self.chat_type.get() == "private" else "群聊"
        self.add_log_message(f"用户发送{msg_type}消息: {content[:30]}{'...' if len(content) > 30 else ''}")
        
        # 显示处理状态
        self.update_status(f"正在分析{msg_type}消息...", True)
        
        # 启动线程处理消息
        thread = threading.Thread(target=self.process_message_thread, args=(msg,))
        thread.daemon = True
        thread.start()
        
        # 清空消息输入框
        self.message_text.delete("1.0", tk.END)
        
    def clear_chat(self):
        """清空聊天记录"""
        # 清空聊天文本
        self.chat_text.delete(1.0, tk.END)
        
        # 显示清空成功消息
        self.add_system_message("聊天记录已清空")

    def log_message(self, message: str):
        """记录消息到聊天记录"""
        self.chat_log.append(message)
        
        # 解析消息，判断是用户消息还是系统消息
        if message.startswith("[") and "]:" in message:
            # 用户消息
            parts = message.split("]: ", 1)
            sender = parts[0][1:]
            content = parts[1] if len(parts) > 1 else ""
            
            # 添加到界面
            self.add_user_message(sender, content)
        else:
            # 系统消息
            self.add_system_message(message)

    # 覆盖原来的Robot.onMsg方法，以便在处理消息后更新界面
    def handle_robot_response(self, msg, response):
        """处理机器人的回复"""
        if msg.from_group():
            target = msg.roomid
        else:
            target = msg.sender
            
        # 添加机器人回复到界面
        self.add_robot_message(response)

    def run(self):
        self.root.mainloop()


# 修改Robot类的sendTextMsg方法，使其在发送消息后通知GUI
original_send_text_msg = Robot.sendTextMsg

def patched_send_text_msg(self, msg, receiver, at_list=""):
    """添加GUI回调的sendTextMsg方法"""
    # 调用原始的发送方法
    original_send_text_msg(self, msg, receiver, at_list)
    
    # 如果有GUI实例，记录日志并显示机器人消息
    if hasattr(self, "gui") and self.gui:
        # 添加发送日志
        self.gui.root.after(0, lambda: self.gui.add_log_message(f"发送消息到 {receiver}: {msg[:30]}{'...' if len(msg) > 30 else ''}", "INFO"))
        # 添加机器人消息
        self.gui.root.after(0, lambda: self.gui.add_robot_message(msg))

# 替换原方法
Robot.sendTextMsg = patched_send_text_msg

if __name__ == "__main__":
    app = ChatGUI()
    
    # 将GUI实例添加到Robot中，以便在发送消息时更新界面
    app.robot.gui = app
    
    # 确保在模拟WCF中也有GUI引用
    app.mock_wcf.gui = app
    
    # 添加启动信息日志
    app.add_log_message("微信机器人模拟器已启动", "INFO")
    app.add_log_message(f"机器人wxid: {app.robot.wxid}", "INFO")
    app.add_log_message(f"使用AI模型: {app.robot.chat.__class__.__name__ if app.robot.chat else '未配置'}", "INFO") 
    app.add_log_message("添加\"group1\"到响应群列表", "INFO")
    app.add_log_message("现在可以发送消息测试机器人了", "INFO")
    
    # 设置自定义标题
    app.root.title(f"微信机器人模拟器 - AI: {app.robot.chat.__class__.__name__ if app.robot.chat else '未配置'}")
    
    app.run() 