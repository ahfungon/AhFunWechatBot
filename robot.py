# -*- coding: utf-8 -*-

import logging
import re
import time
import xml.etree.ElementTree as ET
from queue import Empty
from threading import Thread
from base.func_zhipu import ZhiPu

from wcferry import Wcf, WxMsg

from base.func_bard import BardAssistant
from base.func_chatglm import ChatGLM
from base.func_chatgpt import ChatGPT
from base.func_chengyu import cy
from base.func_news import News
from base.func_tigerbot import TigerBot
from base.func_xinghuo_web import XinghuoWeb
from configuration import Config
from constants import ChatType
from job_mgmt import Job
import os
from plugin.strategy_manager import StrategyManager
from plugin.robot_logger import RobotLogger

__version__ = "39.2.4.0"


class Robot(Job):
    """股票策略分析机器人"""

    def __init__(self, config: Config, wcf: Wcf, chat_type: int) -> None:
        # 初始化父类 Job
        super().__init__()
        
        self.wcf = wcf
        self.config = config
        self.LOG = logging.getLogger("Robot")
        self.wxid = self.wcf.get_self_wxid()
        self.allContacts = self.getAllContacts()
        
        # 初始化日志管理器
        self.robot_logger = RobotLogger()
        self.LOG.info("日志管理器已初始化")
        
        # GUI引用，用于显示日志
        self.gui = None
        
        # 初始化插件
        from plugin.image_saver import ImageSaver
        from plugin.image_ocr import ImageOCR
        self.image_saver = ImageSaver(self.wcf)
        self.image_ocr = ImageOCR()
        # 设置OCR插件的robot引用，以便记录日志
        self.image_ocr.robot = self
        
        self.strategy_manager = StrategyManager()

        # 初始化AI模型
        if ChatType.is_in_chat_types(chat_type):
            if chat_type == ChatType.TIGER_BOT.value and TigerBot.value_check(self.config.TIGERBOT):
                self.chat = TigerBot(self.config.TIGERBOT)
            elif chat_type == ChatType.CHATGPT.value and ChatGPT.value_check(self.config.CHATGPT):
                self.chat = ChatGPT(self.config.CHATGPT)
            elif chat_type == ChatType.XINGHUO_WEB.value and XinghuoWeb.value_check(self.config.XINGHUO_WEB):
                self.chat = XinghuoWeb(self.config.XINGHUO_WEB)
            elif chat_type == ChatType.CHATGLM.value and ChatGLM.value_check(self.config.CHATGLM):
                self.chat = ChatGLM(self.config.CHATGLM)
            elif chat_type == ChatType.BardAssistant.value and BardAssistant.value_check(self.config.BardAssistant):
                self.chat = BardAssistant(self.config.BardAssistant)
            elif chat_type == ChatType.ZhiPu.value and ZhiPu.value_check(self.config.ZhiPu):
                self.chat = ZhiPu(self.config.ZhiPu)
            else:
                self.LOG.warning("未配置AI模型")
                self.chat = None
        else:
            if TigerBot.value_check(self.config.TIGERBOT):
                self.chat = TigerBot(self.config.TIGERBOT)
            elif ChatGPT.value_check(self.config.CHATGPT):
                self.chat = ChatGPT(self.config.CHATGPT)
            elif XinghuoWeb.value_check(self.config.XINGHUO_WEB):
                self.chat = XinghuoWeb(self.config.XINGHUO_WEB)
            elif ChatGLM.value_check(self.config.CHATGLM):
                self.chat = ChatGLM(self.config.CHATGLM)
            elif BardAssistant.value_check(self.config.BardAssistant):
                self.chat = BardAssistant(self.config.BardAssistant)
            elif ZhiPu.value_check(self.config.ZhiPu):
                self.chat = ZhiPu(self.config.ZhiPu)
            else:
                self.LOG.warning("未配置AI模型")
                self.chat = None

        self.LOG.info(f"已选择AI模型: {self.chat}")

        # 添加定时任务：每小时清理过期策略
        self.onEveryHours(1, self.strategy_manager.cleanup_expired_strategies)

    @staticmethod
    def value_check(args: dict) -> bool:
        if args:
            return all(value is not None for key, value in args.items() if key != 'proxy')
        return False

    def toAt(self, msg: WxMsg) -> bool:
        """处理被 @ 消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        return self.toChitchat(msg)

    def toChengyu(self, msg: WxMsg) -> bool:
        """
        处理成语查询/接龙消息
        :param msg: 微信消息结构
        :return: 处理状态，`True` 成功，`False` 失败
        """
        status = False
        texts = re.findall(r"^([#|?|？])(.*)$", msg.content)
        # [('#', '天天向上')]
        if texts:
            flag = texts[0][0]
            text = texts[0][1]
            if flag == "#":  # 接龙
                if cy.isChengyu(text):
                    rsp = cy.getNext(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True
            elif flag in ["?", "？"]:  # 查词
                if cy.isChengyu(text):
                    rsp = cy.getMeaning(text)
                    if rsp:
                        self.sendTextMsg(rsp, msg.roomid)
                        status = True

        return status

    def is_valid_strategy_text(self, text: str) -> bool:
        """检查文本是否包含股票相关的关键词
        :param text: 待检查的文本
        :return: 是否是有效的策略文本
        """
        keywords = ['股票', '买入', '卖出', '仓位', '价格', '止盈', '止损']
        return any(keyword in text for keyword in keywords)

    # 添加日志记录到GUI的方法
    def log_to_gui(self, message, level="INFO"):
        """将日志记录到GUI界面"""
        if hasattr(self, "gui") and self.gui:
            self.gui.root.after(0, lambda: self.gui.add_log_message(message, level))
        else:
            # 如果没有GUI，就使用标准日志
            if level == "ERROR":
                self.LOG.error(message)
            elif level == "WARNING":
                self.LOG.warning(message)
            else:
                self.LOG.info(message)

    def toChitchat(self, msg: WxMsg) -> bool:
        """闲聊，接入 ChatGPT
        """
        if not self.chat:  # 没接 ChatGPT，固定回复
            self.log_to_gui("未配置AI模型，无法进行对话", "WARNING")
            # self.sendTextMsg("你@我干嘛？", msg.roomid)
            return True
        else:  # 接了 ChatGPT，智能回复
            q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
            self.log_to_gui(f"处理聊天消息: {q[:30]}{'...' if len(q) > 30 else ''}")
            
            # 先获取AI的回复
            self.log_to_gui(f"向AI ({self.chat.__class__.__name__}) 发送请求...")
            ai_response = self.chat.get_answer(q, (msg.roomid if msg.from_group() else msg.sender))
            
            if ai_response:
                self.log_to_gui(f"收到AI回复: {ai_response[:30]}{'...' if len(ai_response) > 30 else ''}")
                
                # 记录AI回复
                if msg.from_group():
                    self.robot_logger.log_group_chat(msg.roomid, msg.sender, q, ai_response)
                    self.log_to_gui(f"记录群聊日志: roomid={msg.roomid}, sender={msg.sender}")
                    # 在群聊中发送回复，并@发送者
                    self.sendTextMsg(ai_response, msg.roomid, msg.sender)
                else:
                    self.robot_logger.log_private_chat(msg.sender, q, ai_response)
                    self.log_to_gui(f"记录私聊日志: sender={msg.sender}")
                    # 在私聊中发送回复
                    self.sendTextMsg(ai_response, msg.sender)
                
                # 只有当文本包含股票相关内容时才进行策略分析
                if self.is_valid_strategy_text(ai_response):
                    self.log_to_gui("检测到股票相关内容，开始策略分析")
                    strategy_result = self.strategy_manager.analyze_strategy(ai_response)
                    self.log_to_gui(f"策略分析结果: {strategy_result[:30] if isinstance(strategy_result, str) else '分析完成'}")
                return True
            else:
                self.log_to_gui("AI处理失败，未能获取回复", "ERROR")
                # rsp = "喵呜...AI处理文字时出现了问题..."
                return False

    def process_strategy_text(self, text: str, receiver: str, at_list: str = "") -> None:
        """处理策略文本
        :param text: 策略文本
        :param receiver: 接收者
        :param at_list: @列表
        """
        if not self.chat:
            self.log_to_gui("未配置AI模型，无法分析策略", "WARNING")
            self.sendTextMsg("未配置AI模型，无法分析策略喵~", receiver, at_list)
            return

        # 获取AI分析结果
        self.log_to_gui(f"开始分析策略文本: {text[:30]}{'...' if len(text) > 30 else ''}")
        ai_response = self.chat.get_answer(text, receiver)
        
        if not ai_response:
            self.log_to_gui("AI分析失败，未能获取回复", "ERROR")
            self.sendTextMsg("AI分析策略时出错了喵~", receiver, at_list)
            return
            
        self.log_to_gui(f"收到AI策略分析: {ai_response[:30]}{'...' if len(ai_response) > 30 else ''}")
            
        # 检查是否是群聊
        is_group = '@' in at_list
        source_type = "group" if is_group else "private"
        sender = at_list if is_group else receiver
        
        # 检查AI是否返回"无相关信息"
        if ai_response.strip() == "无相关信息":
            self.log_to_gui("AI判断内容与股票无关，不进行策略分析")
            self.sendTextMsg(ai_response, receiver, at_list)
            
            # 记录聊天日志
            if is_group:
                self.robot_logger.log_group_chat(receiver, sender, text, ai_response)
            else:
                self.robot_logger.log_private_chat(sender, text, ai_response)
            return

        # 创建策略
        self.log_to_gui("开始从AI回复中提取策略信息")
        strategy = self.strategy_manager.create_strategy(ai_response)
        
        if not strategy:
            self.log_to_gui("未能提取有效策略信息", "WARNING")
            self.sendTextMsg("无法从AI回复中提取有效的策略信息喵~", receiver, at_list)
            
            # 记录聊天日志
            if is_group:
                self.robot_logger.log_group_chat(receiver, sender, text, ai_response)
            else:
                self.robot_logger.log_private_chat(sender, text, ai_response)
            return

        # 添加策略
        try:
            # 处理价格显示
            price_display = "未设置"
            if hasattr(strategy, 'price_min') and strategy.price_min is not None:
                if hasattr(strategy, 'price_max') and strategy.price_max is not None and strategy.price_max != strategy.price_min:
                    price_display = f"{strategy.price_min}-{strategy.price_max}"
                else:
                    price_display = f"{strategy.price_min}"
                    
            # 处理操作类型显示
            action_display = "未知"
            if hasattr(strategy, 'action') and strategy.action:
                action_display = "买入" if strategy.action == "buy" else "卖出"
                
            self.log_to_gui(f"开始添加策略: 股票={strategy.stock_name}, 价格={price_display}, 类型={action_display}")
        except Exception as e:
            self.log_to_gui(f"记录策略信息时出错: {e}", "WARNING")
            
        success, message, updated_strategy = self.strategy_manager.add_strategy(strategy)
        self.log_to_gui(f"添加策略结果: {message}")
        
        # 记录策略分析日志
        self.robot_logger.log_strategy(
            source_type=source_type,
            source_id=receiver,
            sender=sender,
            content=text,
            ai_response=ai_response,
            strategy=strategy.to_dict() if strategy else {},
            success=success,
            message=message
        )
        
        if success:
            # 发送策略详情
            strategy_message = self.strategy_manager.format_strategy_message(updated_strategy)
            self.sendTextMsg(strategy_message, receiver, at_list)
        else:
            # 如果是重复策略，查找并发送现有策略的详情
            existing = self.strategy_manager.find_duplicate_strategy(strategy)
            if existing:
                strategy_message = self.strategy_manager.format_strategy_message(existing)
                self.sendTextMsg(f"{message}\n\n当前有效策略：\n{strategy_message}", receiver, at_list)
            else:
                self.sendTextMsg(message, receiver, at_list)

    def process_image_message(self, msg: WxMsg, is_group: bool = False) -> None:
        """处理图片消息
        :param msg: 微信消息
        :param is_group: 是否是群消息
        """
        receiver = msg.roomid if is_group else msg.sender
        
        # 自动保存图片
        saved_path = self.image_saver.save_image(msg)
        if saved_path:
            self.LOG.info(f"{'群聊' if is_group else '私聊'}图片已保存到: {saved_path}")
            self.log_to_gui(f"图片已保存到: {saved_path}", "INFO")
            
            # OCR识别图片文字
            text = self.image_ocr.extract_text(saved_path)
            
            # 记录图片日志
            sender = msg.sender
            
            if text:
                # 以更明显的方式显示OCR识别结果
                self.log_to_gui("============ OCR识别结果开始 ============", "INFO")
                self.log_to_gui(text, "INFO")
                self.log_to_gui("============ OCR识别结果结束 ============", "INFO")
                
                # 获取AI回复
                ai_response = self.chat.get_answer(text, receiver) if self.chat else "未配置AI模型"
                
                # 记录图片处理日志
                if is_group:
                    self.robot_logger.log_group_image(msg.roomid, sender, saved_path, text, ai_response)
                else:
                    self.robot_logger.log_private_image(sender, saved_path, text, ai_response)
                
                # 检查AI是否返回"无相关信息"
                if ai_response.strip() == "无相关信息":
                    self.LOG.info("AI判断图片内容与股票无关，不进行策略分析")
                    self.log_to_gui("AI判断图片内容与股票无关，不进行策略分析", "INFO")
                    self.sendTextMsg(ai_response, receiver, msg.sender if is_group else "")
                    return
                
                # 处理识别出的文字
                self.process_strategy_text(text, receiver, msg.sender if is_group else "")
            else:
                # 记录空OCR结果
                self.log_to_gui("OCR识别结果: 未识别到文字", "WARNING")
                
                if is_group:
                    self.robot_logger.log_group_image(msg.roomid, sender, saved_path, "未识别到文字", "")
                else:
                    self.robot_logger.log_private_image(sender, saved_path, "未识别到文字", "")
                
                self.sendTextMsg("图片中未识别到文字内容喵~", receiver, msg.sender if is_group else "")
        else:
            # 记录图片保存失败
            self.log_to_gui("图片保存失败", "ERROR")
            
            if is_group:
                self.robot_logger.log_group_image(msg.roomid, msg.sender, "图片保存失败", "", "")
            else:
                self.robot_logger.log_private_image(msg.sender, "图片保存失败", "", "")
            
            self.sendTextMsg("喵呜...图片保存失败了...", receiver, msg.sender if is_group else "")

    def processMsg(self, msg: WxMsg) -> None:
        """处理接收到的消息"""
        # 记录消息
        self.log_to_gui(f"收到{'群' if msg.from_group() else '私聊'}消息: {msg}")
        
        # 群聊消息
        if msg.from_group():
            if msg.roomid not in self.config.GROUPS:  # 不在配置的响应的群列表里，忽略
                self.log_to_gui(f"忽略非响应群消息: roomid={msg.roomid}", "DEBUG")
                return

            if msg.is_at(self.wxid):  # 被@
                self.log_to_gui(f"收到@消息: roomid={msg.roomid}, sender={msg.sender}")
                # 记录群聊消息
                self.robot_logger.log_group_chat(msg.roomid, msg.sender, msg.content, "处理中...")
                # 对于模拟环境，使用toChitchat方法处理消息可能更合适
                if hasattr(self.wcf, 'gui') and self.wcf.gui:
                    # 在模拟环境中，使用toChitchat直接处理
                    self.log_to_gui("在模拟环境中使用toChitchat处理消息")
                    self.toChitchat(msg)
                else:
                    # 在真实环境中，使用process_strategy_text处理
                    self.log_to_gui("在真实环境中使用process_strategy_text处理消息")
                    self.process_strategy_text(msg.content, msg.roomid, msg.sender)
            elif msg.type == 0x03:  # 图片消息
                self.log_to_gui(f"收到群图片消息: roomid={msg.roomid}, sender={msg.sender}")
                self.process_image_message(msg, is_group=True)
            else:  # 其他消息
                if self.toChengyu(msg):
                    # 如果是成语消息，记录处理结果
                    self.log_to_gui(f"处理成语消息: roomid={msg.roomid}, sender={msg.sender}")
                    self.robot_logger.log_group_chat(msg.roomid, msg.sender, msg.content, "成语处理")
            return

        # 非群聊信息
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)
        elif msg.type == 10000:  # 系统信息
            self.sayHiToNewFriend(msg)
        elif msg.type == 0x01:  # 文本消息
            if msg.from_self():
                if msg.content == "^更新$":
                    self.config.reload()
                    self.LOG.info("已更新配置")
            else:
                # 记录私聊消息
                self.robot_logger.log_private_chat(msg.sender, msg.content, "处理中...")
                self.process_strategy_text(msg.content, msg.sender)
        elif msg.type == 0x03:  # 图片消息
            self.process_image_message(msg, is_group=False)

    def onMsg(self, msg: WxMsg) -> int:
        try:
            self.LOG.info(msg)  # 打印信息
            self.log_to_gui(f"开始处理消息: {msg}")
            self.processMsg(msg)
            # 使用明显区别的格式，避免与系统日志混淆
            self.log_to_gui(f"🤖 机器人处理完成: id={msg.id}")
        except Exception as e:
            self.log_to_gui(f"处理消息出错: {str(e)}", "ERROR")
            self.LOG.error(e)

        return 0

    def enableRecvMsg(self) -> None:
        self.wcf.enable_recv_msg(self.onMsg)

    def enableReceivingMsg(self) -> None:
        def innerProcessMsg(wcf: Wcf):
            while wcf.is_receiving_msg():
                try:
                    msg = wcf.get_msg()
                    self.LOG.info(msg)
                    self.processMsg(msg)
                except Empty:
                    continue  # Empty message
                except Exception as e:
                    self.LOG.error(f"Receiving message error: {e}")

        self.wcf.enable_receiving_msg()
        Thread(target=innerProcessMsg, name="GetMessage", args=(self.wcf,), daemon=True).start()

    def sendTextMsg(self, msg: str, receiver: str, at_list: str = "") -> None:
        """ 发送消息
        :param msg: 消息字符串
        :param receiver: 接收人wxid或者群id
        :param at_list: 要@的wxid, @所有人的wxid为：notify@all
        """
        # msg 中需要有 @ 名单中一样数量的 @
        ats = ""
        if at_list:
            if at_list == "notify@all":  # @所有人
                ats = " @所有人"
            else:
                # 如果at_list是单个wxid而不是逗号分隔的列表，直接处理
                if "," not in at_list:
                    nickname = self.wcf.get_alias_in_chatroom(at_list, receiver)
                    if nickname:
                        ats = f" @{nickname}"
                    else:
                        ats = f" @{at_list}"  # 如果获取不到昵称，直接用wxid
                else:
                    # 处理多个@
                    wxids = at_list.split(",")
                    for wxid in wxids:
                        nickname = self.wcf.get_alias_in_chatroom(wxid, receiver)
                        if nickname:
                            ats += f" @{nickname}"
                        else:
                            ats += f" @{wxid}"

        # 发送消息
        if not ats:
            self.LOG.info(f"To {receiver}: {msg}")
            self.wcf.send_text(msg, receiver, at_list)
            
            # 更新私聊日志中的AI回复部分
            if not '@' in at_list and at_list != "notify@all":
                try:
                    self.robot_logger.log_private_chat(receiver, "更新AI回复", msg)
                except Exception as e:
                    self.LOG.error(f"更新私聊日志出错: {e}")
        else:
            self.LOG.info(f"To {receiver}: {msg}{ats}")
            # 确保@放在消息前面
            self.wcf.send_text(f"{ats}\n\n{msg}", receiver, at_list)
            
            # 更新群聊日志中的AI回复部分
            try:
                self.robot_logger.log_group_chat(receiver, at_list, "更新AI回复", msg)
            except Exception as e:
                self.LOG.error(f"更新群聊日志出错: {e}")

    def getAllContacts(self) -> dict:
        """
        获取联系人（包括好友、公众号、服务号、群成员……）
        格式: {"wxid": "NickName"}
        """
        contacts = self.wcf.query_sql("MicroMsg.db", "SELECT UserName, NickName FROM Contact;")
        return {contact["UserName"]: contact["NickName"] for contact in contacts}

    def keepRunningAndBlockProcess(self) -> None:
        """
        保持机器人运行，不让进程退出
        """
        while True:
            self.runPendingJobs()
            time.sleep(1)
    def autoAcceptFriendRequest(self, msg: WxMsg) -> None:
        try:
            xml = ET.fromstring(msg.content)
            v3 = xml.attrib["encryptusername"]
            v4 = xml.attrib["ticket"]
            scene = int(xml.attrib["scene"])
            self.wcf.accept_new_friend(v3, v4, scene)

        except Exception as e:
            self.LOG.error(f"同意好友出错：{e}")

    def sayHiToNewFriend(self, msg: WxMsg) -> None:
        nickName = re.findall(r"你已添加了(.*)，现在可以开始聊天了。", msg.content)
        if nickName:
            # 添加了好友，更新好友列表
            self.allContacts[msg.sender] = nickName[0]
            # self.sendTextMsg(f"Hi {nickName[0]}，我自动通过了你的好友请求。", msg.sender)

    def newsReport(self) -> None:
        receivers = self.config.NEWS
        if not receivers:
            return

        news = News().get_important_news()
        # for r in receivers:
        #     self.sendTextMsg(news, r)

