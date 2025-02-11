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

__version__ = "39.2.4.0"


class Robot(Job):
    """个性化自己的机器人
    """

    def __init__(self, config: Config, wcf: Wcf, chat_type: int) -> None:
        self.wcf = wcf
        self.config = config
        self.LOG = logging.getLogger("Robot")
        self.wxid = self.wcf.get_self_wxid()
        self.allContacts = self.getAllContacts()
        
        # 初始化插件
        from plugin.image_saver import ImageSaver
        from plugin.image_ocr import ImageOCR
        from plugin.strategy_analyzer import StrategyAnalyzer
        self.image_saver = ImageSaver(self.wcf)
        self.image_ocr = ImageOCR()
        self.strategy_analyzer = StrategyAnalyzer()

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
                self.LOG.warning("未配置模型")
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
                self.LOG.warning("未配置模型")
                self.chat = None

        self.LOG.info(f"已选择: {self.chat}")

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

    def toChitchat(self, msg: WxMsg) -> bool:
        """闲聊，接入 ChatGPT
        """
        if not self.chat:  # 没接 ChatGPT，固定回复
            # self.sendTextMsg("你@我干嘛？", msg.roomid)
            return True
        else:  # 接了 ChatGPT，智能回复
            q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
            # 先获取AI的回复
            ai_response = self.chat.get_answer(q, (msg.roomid if msg.from_group() else msg.sender))
            if ai_response:
                # 发送AI的回复
                # if msg.from_group():
                #     self.sendTextMsg(f"我的理解是：\n{ai_response}", msg.roomid, msg.sender)
                # else:
                #     self.sendTextMsg(f"我的理解是：\n{ai_response}", msg.sender)
                
                # 将AI的回复提交给策略分析器
                strategy_result = self.strategy_analyzer.analyze_strategy(ai_response)
                # if strategy_result:
                #     if msg.from_group():
                #         self.sendTextMsg(strategy_result, msg.roomid, msg.sender)
                #     else:
                #         self.sendTextMsg(strategy_result, msg.sender)
                return True
            else:
                # rsp = "喵呜...AI处理文字时出现了问题..."
                return False

        # if rsp:
        #     if msg.from_group():
        #         self.sendTextMsg(rsp, msg.roomid, msg.sender)
        #     else:
        #         self.sendTextMsg(rsp, msg.sender)
        #     return True
        # else:
        #     self.LOG.error(f"无法从 ChatGPT 获得答案")
        #     return False

    def process_image_message(self, msg: WxMsg, is_group: bool = False) -> None:
        """处理图片消息
        :param msg: 微信消息
        :param is_group: 是否是群消息
        """
        receiver = msg.roomid if is_group else msg.sender
        
        # 发送处理提示
        # if is_group:
        #     self.sendTextMsg("感谢分享，马上分析处理~", receiver, msg.sender)
        # else:
        #     self.sendTextMsg("我收到了图片，马上下载处理哦~", receiver)
        
        # 自动保存图片
        saved_path = self.image_saver.save_image(msg)
        if saved_path:
            self.LOG.info(f"{'群聊' if is_group else '私聊'}图片已保存到: {saved_path}")
            
            # 发送保存成功提示
            filename = os.path.basename(saved_path)
            # if is_group:
            #     self.sendTextMsg(f"图片已成功保存为：{filename}", receiver, msg.sender)
            # else:
            #     self.sendTextMsg(f"图片已成功保存为：{filename}", receiver)
            
            # OCR识别图片文字
            text = self.image_ocr.extract_text(saved_path)
            if text:
                # 整理识别结果
                formatted_text = "【图片文字识别结果】\n" + "="*30 + "\n"
                
                # 按行分割，去除空行和多余空格
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                formatted_text += "\n".join(lines)
                formatted_text += "\n" + "="*30
                
                # 如果文字太长，分段发送
                # if len(formatted_text) > 500:
                #     if is_group:
                #         self.sendTextMsg("文字内容较多，将分段发送：", receiver, msg.sender)
                #     else:
                #         self.sendTextMsg("文字内容较多，将分段发送：", receiver)
                        
                #     # 每500字符分段，但不打断完整行
                #     segments = []
                #     current_segment = ""
                    
                #     for line in formatted_text.split('\n'):
                #         if len(current_segment) + len(line) + 1 > 500:
                #             segments.append(current_segment)
                #             current_segment = line
                #         else:
                #             current_segment += ('\n' if current_segment else '') + line
                    
                #     if current_segment:
                #         segments.append(current_segment)
                        
                #     # 发送每个分段
                #     for i, segment in enumerate(segments, 1):
                #         if len(segments) > 1:
                #             segment = f"[第{i}/{len(segments)}段]\n{segment}"
                #         if is_group:
                #             self.sendTextMsg(segment, receiver, msg.sender)
                #         else:
                #             self.sendTextMsg(segment, receiver)
                # else:
                #     if is_group:
                #         self.sendTextMsg(formatted_text, receiver, msg.sender)
                #     else:
                #         self.sendTextMsg(formatted_text, receiver)
                
                # 将OCR识别的文字提交给AI处理
                if self.chat:
                    # if is_group:
                    #     self.sendTextMsg("我需要思考一下~", receiver, msg.sender)
                    # else:
                    #     self.sendTextMsg("我需要思考一下~", receiver)
                        
                    # 去掉格式化的标记，只保留纯文本
                    pure_text = "\n".join(lines)
                    ai_response = self.chat.get_answer(pure_text, receiver)
                    if ai_response:
                        # 发送AI的回复
                        # if is_group:
                        #     self.sendTextMsg(f"我的理解是：\n{ai_response}", receiver, msg.sender)
                        # else:
                        #     self.sendTextMsg(f"我的理解是：\n{ai_response}", receiver)
                            
                        # 将AI的回复提交给策略分析器
                        strategy_result = self.strategy_analyzer.analyze_strategy(ai_response)
                        # if strategy_result:
                        #     if is_group:
                        #         self.sendTextMsg(strategy_result, receiver, msg.sender)
                        #     else:
                        #         self.sendTextMsg(strategy_result, receiver)
                    # else:
                    #     if is_group:
                    #         self.sendTextMsg("喵呜...AI处理文字时出现了问题...", receiver, msg.sender)
                    #     else:
                    #         self.sendTextMsg("喵呜...AI处理文字时出现了问题...", receiver)
            # else:
            #     if is_group:
            #         self.sendTextMsg("图片中未识别到文字内容喵~", receiver, msg.sender)
            #     else:
            #         self.sendTextMsg("图片中未识别到文字内容喵~", receiver)
        # else:
        #     # 发送失败提示
        #     if is_group:
        #         self.sendTextMsg("喵呜...图片保存失败了...", receiver, msg.sender)
        #     else:
        #         self.sendTextMsg("喵呜...图片保存失败了...", receiver)

    def processMsg(self, msg: WxMsg) -> None:
        """当接收到消息的时候，会调用本方法。如果不实现本方法，则打印原始消息。
        此处可进行自定义发送的内容,如通过 msg.content 关键字自动获取当前天气信息，并发送到对应的群组@发送者
        群号：msg.roomid  微信ID：msg.sender  消息内容：msg.content
        """
        # 群聊消息
        if msg.from_group():
            # 如果在群里被 @
            if msg.roomid not in self.config.GROUPS:  # 不在配置的响应的群列表里，忽略
                return

            if msg.is_at(self.wxid):  # 被@
                self.toAt(msg)
            elif msg.type == 0x03:  # 图片消息
                self.process_image_message(msg, is_group=True)
            else:  # 其他消息
                self.toChengyu(msg)

            return  # 处理完群聊信息，后面就不需要处理了

        # 非群聊信息，按消息类型进行处理
        if msg.type == 37:  # 好友请求
            self.autoAcceptFriendRequest(msg)

        elif msg.type == 10000:  # 系统信息
            self.sayHiToNewFriend(msg)

        elif msg.type == 0x01:  # 文本消息
            # 让配置加载更灵活，自己可以更新配置。也可以利用定时任务更新。
            if msg.from_self():
                if msg.content == "^更新$":
                    self.config.reload()
                    self.LOG.info("已更新")
            else:
                self.toChitchat(msg)  # 闲聊

        elif msg.type == 0x03:  # 图片消息
            self.process_image_message(msg, is_group=False)

    def onMsg(self, msg: WxMsg) -> int:
        try:
            self.LOG.info(msg)  # 打印信息
            self.processMsg(msg)
        except Exception as e:
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
            # self.wcf.send_text(msg, receiver, at_list)
        else:
            self.LOG.info(f"To {receiver}: {msg}{ats}")
            # 确保@放在消息前面
            # self.wcf.send_text(f"{ats}\n\n{msg}", receiver, at_list)

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
