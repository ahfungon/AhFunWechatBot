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
        self.root = tk.Tk()
        self.root.title("微信机器人模拟器")
        self.root.geometry("800x600")
        
        # 设置样式
        self.setup_styles()
        
        # 初始化日志
        self.chat_log = []
        
        # 初始化机器人，使用智谱AI
        self.config = Config()
        
        # 把模拟的群ID添加到响应群列表
        if not hasattr(self.config, 'GROUPS'):
            self.config.GROUPS = []
        self.config.GROUPS.append("group1")
        
        self.mock_wcf = MockWcf()
        self.mock_wcf.gui = self  # 设置GUI引用
        
        # 确保图片保存目录存在
        img_dir = os.path.abspath("img")
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
            print(f"[GUI] 创建图片目录: {img_dir}")
        
        # 使用标准的Robot类
        self.robot = Robot(self.config, self.mock_wcf, ChatType.ZhiPu.value)
        print(f"[GUI] 机器人初始化完成: wxid={self.robot.wxid}, 使用AI模型={ChatType.ZhiPu.name}")
        
        # 处理状态
        self.processing = False
        
        # 创建界面元素
        self.create_widgets()
        
        # 绑定快捷键
        self.root.bind_all("<Return>", self.handle_return)
        self.root.bind_all("<Shift-Return>", self.handle_shift_return)
        
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
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：聊天记录
        left_frame = ttk.Frame(main_paned, style="ChatFrame.TFrame")
        main_paned.add(left_frame, weight=1)
        
        # 标题栏
        title_frame = ttk.Frame(left_frame, style="ChatFrame.TFrame")
        title_frame.pack(fill=tk.X, padx=5, pady=5)
        
        chat_label = ttk.Label(
            title_frame, 
            text="微信聊天模拟器", 
            font=("微软雅黑", 10, "bold"),
            background="#f5f5f5"
        )
        chat_label.pack(anchor=tk.CENTER)
        
        # 使用Text组件替代Canvas，使内容可复制
        self.chat_text = tk.Text(
            left_frame,
            background="#f5f5f5",
            wrap=tk.WORD,
            padx=10,
            pady=5,
            font=("微软雅黑", 9),
            highlightthickness=0,
            borderwidth=0
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 添加滚动条
        chat_scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.chat_text.yview)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_text.configure(yscrollcommand=chat_scrollbar.set)
        
        # 设置标签样式
        self.chat_text.tag_configure("time", foreground="#999999", font=("微软雅黑", 8))
        self.chat_text.tag_configure("info", foreground="#666666", font=("微软雅黑", 8, "bold"))
        self.chat_text.tag_configure("error", foreground="#E74C3C", font=("微软雅黑", 8, "bold"))
        self.chat_text.tag_configure("warning", foreground="#F39C12", font=("微软雅黑", 8, "bold"))
        self.chat_text.tag_configure("debug", foreground="#3498DB", font=("微软雅黑", 8, "bold"))
        self.chat_text.tag_configure("content", foreground="#333333", font=("微软雅黑", 9))
        self.chat_text.tag_configure("system", foreground="#1E90FF", font=("微软雅黑", 9, "italic"))
        self.chat_text.tag_configure("user", foreground="#333333", font=("微软雅黑", 9, "bold"))
        self.chat_text.tag_configure("robot", foreground="#49b66e", font=("微软雅黑", 9))
        
        # 状态框架（包含进度条和状态文本）
        self.status_frame = ttk.Frame(left_frame, style="ChatFrame.TFrame")
        self.status_frame.pack(fill=tk.X, pady=(0, 5), padx=5)
        
        # 状态文本
        self.status_label = ttk.Label(
            self.status_frame,
            text="就绪",
            background="#f5f5f5",
            foreground="#666666",
            font=("微软雅黑", 9)
        )
        self.status_label.pack(fill=tk.X, pady=(0, 3))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.status_frame, 
            orient=tk.HORIZONTAL, 
            length=100, 
            mode='indeterminate', 
            variable=self.progress_var,
            style="Processing.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X)
        
        # 默认隐藏状态框架
        self.status_frame.pack_forget()
        
        # 右侧：发送消息区域
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        # 发送者输入
        sender_frame = ttk.Frame(right_frame)
        sender_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(sender_frame, text="发送者:").pack(side=tk.LEFT)
        self.sender_entry = ttk.Entry(sender_frame)
        self.sender_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.sender_entry.insert(0, "test_user")
        
        # 聊天类型选择
        type_frame = ttk.Frame(right_frame)
        type_frame.pack(fill=tk.X, pady=5)
        
        self.chat_type = tk.StringVar(value="private")
        ttk.Radiobutton(type_frame, text="私聊", variable=self.chat_type, value="private").pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="群聊", variable=self.chat_type, value="group").pack(side=tk.LEFT)
        
        # 消息输入区域
        message_frame = ttk.Frame(right_frame)
        message_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(message_frame, text="消息内容:").pack(anchor=tk.W)
        self.message_text = scrolledtext.ScrolledText(message_frame, wrap=tk.WORD, width=40, height=10)
        self.message_text.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区域
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # 使用tk.Button替代ttk.Button，以便更好地控制外观
        # 发送图片按钮
        send_image_button = tk.Button(
            button_frame, 
            text="发送图片", 
            command=self.send_image,
            bg=self.button_bg,
            fg=self.button_fg,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            font=("微软雅黑", 9)
        )
        send_image_button.pack(side=tk.LEFT, padx=5)
        
        # 发送消息按钮
        send_button = tk.Button(
            button_frame, 
            text="发送消息", 
            command=self.send_message,
            bg=self.button_bg,
            fg=self.button_fg,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            font=("微软雅黑", 9)
        )
        send_button.pack(side=tk.LEFT, padx=5)
        
        # 清空按钮
        clear_button = tk.Button(
            button_frame, 
            text="清空记录", 
            command=self.clear_chat,
            bg=self.button_bg,
            fg=self.button_fg,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            font=("微软雅黑", 9)
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
        
        # 在文本末尾插入新行
        self.chat_text.insert(tk.END, f"[{time_str}] ", "time")
        self.chat_text.insert(tk.END, f"[{level}] ", level_tag)
        self.chat_text.insert(tk.END, f"{text}\n", "content")
        
        # 滚动到底部
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
            else:
                content_preview = f"{msg.content[:50]}{'...' if len(msg.content) > 50 else ''}"
            
            self.root.after(0, lambda: self.add_log_message(f"消息内容: {content_preview}", "INFO"))
            
            # 处理开始前记录
            self.root.after(0, lambda: self.add_log_message("交给机器人处理中...", "INFO"))
            
            # 更新状态为处理中
            self.root.after(0, lambda: self.update_status("机器人处理中...", True))
            
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