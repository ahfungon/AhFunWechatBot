#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from configuration import Config
from robot import Robot
import logging
from wcferry import WxMsg
from constants import ChatType  # 导入ChatType

# 模拟的WCF类
class MockWcf:
    def __init__(self):
        self._wxid = "wxid_test123"  # 模拟的微信ID
        self.msg_queue = []  # 用于存储消息的队列
        self.receiving_msg = True  # 消息接收状态

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

    def send_text(self, msg, receiver, at_list=""):
        print(f"发送消息到 {receiver}: {msg}")
        if at_list:
            print(f"@列表: {at_list}")
        return True

    def get_alias_in_chatroom(self, wxid, room_id):
        return f"用户{wxid}"

    def query_sql(self, db, sql):
        # 返回一个模拟的联系人列表
        return [{"UserName": "test_user", "NickName": "测试用户"}]

# 模拟的消息类，用于模拟 WxMsg
class MockWxMsg(WxMsg):
    def __init__(self, content, sender, roomid, msg_type=0x01):
        self.id = "mock_msg_id"  # 消息id
        self.type = msg_type     # 消息类型
        self.sender = sender     # 发送者
        self.roomid = roomid     # 群id
        self.content = content   # 消息内容
        self.sign = ""          # 消息签名
        self.thumb = ""         # 图片缩略图
        self.extra = ""         # 附加信息
        self.timestamp = 0      # 时间戳

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
        return f"@{wxid}" in self.content

class ChatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("微信机器人模拟器")
        self.root.geometry("800x600")
        
        # 初始化日志
        self.chat_log = []
        
        # 初始化机器人，使用智谱AI
        self.config = Config()
        self.mock_wcf = MockWcf()
        self.robot = Robot(self.config, self.mock_wcf, ChatType.ZhiPu.value)  # 使用智谱AI
        
        # 创建界面元素
        self.create_widgets()
        
        # 绑定快捷键
        self.root.bind_all("<Return>", self.handle_return)
        self.root.bind_all("<Shift-Return>", self.handle_shift_return)
        
        # 显示启动信息
        self.show_startup_info()
        
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
            "=========================="
        ]
        for line in info:
            self.chat_text.insert(tk.END, line + "\n")
        self.chat_text.see(tk.END)

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
        left_frame = ttk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        right_frame = ttk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧：聊天记录
        chat_label = ttk.Label(left_frame, text="聊天记录")
        chat_label.pack(anchor=tk.W)
        
        self.chat_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, width=40, height=30)
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        
        # 右侧：发送消息区域
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
        
        # 发送图片按钮
        send_image_button = ttk.Button(button_frame, text="发送图片", command=self.send_image)
        send_image_button.pack(side=tk.LEFT, padx=5)
        
        # 发送消息按钮
        send_button = ttk.Button(button_frame, text="发送消息", command=self.send_message)
        send_button.pack(side=tk.LEFT, padx=5)
        
        # 清空按钮
        clear_button = ttk.Button(button_frame, text="清空记录", command=self.clear_chat)
        clear_button.pack(side=tk.LEFT, padx=5)

    def send_image(self):
        """发送图片消息"""
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
                
            # 创建图片消息对象（type=3 表示图片消息）
            if self.chat_type.get() == "private":
                msg = MockWxMsg(content=file_path, sender=sender, roomid="", msg_type=0x03)
            else:
                msg = MockWxMsg(content=file_path, sender=sender, roomid="group1", msg_type=0x03)
            
            # 记录消息
            self.log_message(f"[{sender}]: [图片消息] {file_path}")
            
            # 处理消息
            self.robot.onMsg(msg)

    def send_message(self):
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
        
        # 记录消息
        self.log_message(f"[{sender}]: {content}")
        
        # 处理消息
        self.robot.onMsg(msg)
        
        # 清空消息输入框
        self.message_text.delete("1.0", tk.END)
        
    def clear_chat(self):
        self.chat_log.clear()
        self.chat_text.delete("1.0", tk.END)
        self.show_startup_info()
        
    def log_message(self, message: str):
        """记录消息到聊天记录"""
        self.chat_log.append(message)
        self.chat_text.insert(tk.END, message + "\n")
        self.chat_text.see(tk.END)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ChatGUI()
    app.run() 