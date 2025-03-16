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
from plugin.sms_sender import SmsSender

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
                # 使用自定义prompt初始化智谱AI
                zhipu_config = self.config.ZhiPu.copy()
                zhipu_config["prompt"] = self.get_ai_prompt()
                self.chat = ZhiPu(zhipu_config)
            elif chat_type == ChatType.WenXin.value and WenXin.value_check(self.config.WenXin):
                # 使用自定义prompt初始化文心一言
                wenxin_config = self.config.WenXin.copy()
                wenxin_config["prompt"] = self.get_ai_prompt()
                self.chat = WenXin(wenxin_config)
            elif chat_type == ChatType.QianWen.value and QianWen.value_check(self.config.QianWen):
                # 使用自定义prompt初始化通义千问
                qianwen_config = self.config.QianWen.copy()
                qianwen_config["prompt"] = self.get_ai_prompt()
                self.chat = QianWen(qianwen_config)
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
                # 使用自定义prompt初始化智谱AI
                zhipu_config = self.config.ZhiPu.copy()
                zhipu_config["prompt"] = self.get_ai_prompt()
                self.chat = ZhiPu(zhipu_config)
            else:
                self.LOG.warning("未配置AI模型")
                self.chat = None

        self.LOG.info(f"已选择AI模型: {self.chat}")

        # 初始化短信发送插件
        if hasattr(self.config, 'SMS') and SmsSender.value_check(self.config.SMS):
            self.sms_sender = SmsSender(self.config.SMS)
            self.LOG.info("短信发送插件初始化成功")
        else:
            self.sms_sender = None
            self.LOG.warning("短信发送插件未配置或配置无效")

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

    def log_to_gui(self, message, level="INFO"):
        """向GUI发送日志消息"""
        if hasattr(self, "gui") and self.gui:
            self.gui.root.after(0, lambda: self.gui.add_log_message(message, level))
        self.LOG.info(message)

    def get_ai_prompt(self) -> str:
        """获取AI提示词
        :return: 统一的AI提示词
        """
        return """
        你是一个股票策略研究专家，请根据我提供的信息，给出股票的交易策略。
        用户给你的内容有可能是通过图片OCR识别的，请自行拼接整理，并忽略文字识别错误。
        如果我提供的信息跟股票无关，则直接返回"无相关信息"。
        如果我提供的信息跟股票有关，但是只有基础的指标或价格数据、交易数据等信息，没有任何明确的操作要求或建议，请直接返回"无相关信息"。
        如果我提供的信息中，没有明确说明是针对某个股票，只是基础行情分析或趋势判断，请直接返回"无相关信息"。
        只有在我给你的信息中，如果包含"#大师实战演练""操作建议""选股理由""建议数量"这些字眼，且有指向具体股票，一般是明确的买入股票的策略要求。如果有提到几成仓位，则代表相应成数的仓位，比如1成仓位，就是10%仓位。
        只有在我给你的信息中，如果包含"#加仓减仓""建议加仓""建议减仓"这些字眼，且有指向具体股票，一般是加仓或者减仓的策略要求。如果有提到几成仓位，则代表相应成数的仓位，比如1成仓位，就是10%仓位。
        只有在我给你的信息中，如果包含"#止盈止损""高抛兑现""获利了结""卖出"这些字眼，且有指向具体股票，一般是卖出股票的策略要求，如果未明确说明仓位，则默认仓位100%。
        只有在我给你的信息中，如果包含"#持有""耐心持股""持股待涨"这些字眼，且有指向具体股票，一般是持有股票的策略要求，如果有提到几成仓位，则代表相应成数的仓位，比如1成仓位，就是10%仓位。
        如果跟具体的股票操作策略有关，请严格生成格式文字内容，不需要做任何的铺垫和阐述，也不要总结用户的话，注意事项：
        1. 严格按照用户输入的内容进行整理
        2. 不要添加任何用户未提供的信息或操作建议
        3. 如果用户没有提供某些信息（如止损价格），对应部分可以省略
        4. 保持格式的一致性和专业性，文字要精简，不要啰嗦
        5. 如果用户提供的信息是建议持有而不是买入或卖出，请在操作建议总结中使用**持有建议**而不是买入时机
        6. 如果用户提供的操作价格描述是"xx元下方"或"xx下方"或类似话术，则代表最低价是0，最高价是xx。
        7. 如果用户提供的操作价格描述是"xx元上方"或"xx上方"或类似话术，则代表最低价是xx，最高价是9999。
        8. 如果用户提供的操作价格描述是"xx元附近"或"xx附近"或类似话术，则代表最低价是xx乘以0.97，最高价是xx乘以1.03。

        买入股票策略，请遵循以下格式规范生成：
        ### 股票名称
        股票名称（股票代码）

        ### 操作建议
        1. **执行策略**
            - **操作要求**：买入
            - **交易价格**：xx-xx元
            - **建议数量**：xx%仓位

        2. **止损策略**
            - **止损价格**：xx元下方
            - **理由**：设置合理的止损位以控制风险，避免损失过大。

        3. **止盈策略**
            - **止盈价格**：xx元上方
            - **理由**：在股价达到预期收益时获利了结，确保利润的实现。

        4. **操作理由**
            - 根据用户输入的信息整理相关理由
            - 不要添加任何用户未提供的信息

        卖出股票策略，请遵循以下格式规范生成：
        ### 股票名称
        股票名称（股票代码）

        ### 操作建议
        1. **执行策略**
            - **操作要求**：卖出
            - **交易价格**：xx-xx元
            - **建议数量**：xx%仓位

        2. **操作理由**
            - 根据用户输入的信息整理相关理由
            - 不要添加任何用户未提供的信息

        股票加仓策略，请遵循以下格式规范生成：
        ### 股票名称
        股票名称（股票代码）

        ### 操作建议
        1. **执行策略**
            - **操作要求**：加仓
            - **交易价格**：xx-xx元
            - **建议数量**：xx%仓位

        2. **操作理由**
            - 根据用户输入的信息整理相关理由
            - 不要添加任何用户未提供的信息

        股票减仓策略，请遵循以下格式规范生成：
        ### 股票名称
        股票名称（股票代码）

        ### 操作建议
        1. **执行策略**
            - **操作要求**：减仓
            - **交易价格**：xx-xx元
            - **建议数量**：xx%仓位

        2. **操作理由**
            - 根据用户输入的信息整理相关理由
            - 不要添加任何用户未提供的信息

        股票持有策略，请遵循以下格式规范生成：
        ### 股票名称
        股票名称（股票代码）

        ### 操作建议
        1. **执行策略**
            - **操作要求**：持有

        2. **止损策略**
            - **止损价格**：xx元下方
            - **理由**：设置合理的止损位以控制风险，避免损失过大。

        3. **止盈策略**
            - **止盈价格**：xx元上方
            - **理由**：在股价达到预期收益时获利了结，确保利润的实现。

        4. **操作理由**
            - 根据用户输入的信息整理相关理由
            - 不要添加任何用户未提供的信息
        """

    def toChitchat(self, msg: WxMsg) -> bool:
        """闲聊，接入 ChatGPT
        """
        if not self.chat:  # 没接 ChatGPT，固定回复
            self.log_to_gui("未配置AI模型，无法进行对话", "WARNING")
            # 不发送消息给用户
            return True
        else:  # 接了 ChatGPT，智能回复
            q = re.sub(r"@.*?[\u2005|\s]", "", msg.content).replace(" ", "")
            self.log_to_gui(f"处理聊天消息: {q[:30]}{'...' if len(q) > 30 else ''}")
            
            # 获取提示词
            prompt = self.get_ai_prompt()
            self.log_to_gui(f"使用的AI提示词:\n{prompt[:100]}...", "INFO")
            
            # 先获取AI的回复
            self.log_to_gui(f"向AI ({self.chat.__class__.__name__}) 发送请求...")
            ai_response = self.chat.get_answer(prompt + q, (msg.roomid if msg.from_group() else msg.sender))
            
            if ai_response:
                # 添加分隔线和AI回复章节标题
                if hasattr(self, "gui") and self.gui:
                    self.gui.root.after(0, lambda: self.gui.add_section_header("AI分析结果"))
                
                self.log_to_gui(f"收到AI回复: {ai_response[:30]}{'...' if len(ai_response) > 30 else ''}")
                # 记录完整的AI回复
                self.log_to_gui(f"完整AI回复内容:\n{ai_response}", "AI")
                
                # 记录AI回复
                if msg.from_group():
                    self.robot_logger.log_group_chat(msg.roomid, msg.sender, q, ai_response)
                    self.log_to_gui(f"记录群聊日志: roomid={msg.roomid}, sender={msg.sender}")
                    # 不发送消息给用户
                else:
                    self.robot_logger.log_private_chat(msg.sender, q, ai_response)
                    self.log_to_gui(f"记录私聊日志: sender={msg.sender}")
                    # 不发送消息给用户
                
                # 只有当文本包含股票相关内容时才进行策略分析
                if self.is_valid_strategy_text(ai_response):
                    # 添加策略分析章节标题
                    if hasattr(self, "gui") and self.gui:
                        self.gui.root.after(0, lambda: self.gui.add_section_header("策略分析处理"))
                    
                    self.log_to_gui("检测到股票相关内容，开始策略分析")
                    strategy_result = self.strategy_manager.analyze_strategy(ai_response)
                    
                    if strategy_result:
                        # 记录策略分析结果
                        self.log_to_gui("策略分析结果:", "STRATEGY")
                        for key, value in strategy_result.items():
                            if isinstance(value, dict):
                                self.log_to_gui(f"  {key}:", "STRATEGY")
                                for sub_key, sub_value in value.items():
                                    self.log_to_gui(f"    {sub_key}: {sub_value}", "STRATEGY")
                            else:
                                self.log_to_gui(f"  {key}: {value}", "STRATEGY")
                    else:
                        self.log_to_gui("未能提取有效的策略信息", "STRATEGY")
                return True
            else:
                self.log_to_gui("AI处理失败，未能获取回复", "ERROR")
                return False

    def process_strategy_text(self, text: str, receiver: str, at_list: list) -> None:
        """处理策略文本
        
        Args:
            text: 策略文本
            receiver: 接收者
            at_list: @列表
        """
        self.LOG.info(f"收到策略文本: {text}")
        self.LOG.info(f"接收者: {receiver}")
        self.LOG.info(f"@列表: {at_list}")
        
        # 调用AI处理策略文本
        ai_response = self.chat.get_answer(text, receiver)
        self.LOG.info(f"AI响应: {ai_response}")
        
        # 发送短信
        if self.sms_sender.config.get("enabled", False):
            self.LOG.info("短信功能已启用，准备发送短信...")
            if self.sms_sender.send_strategy_sms(ai_response):
                self.LOG.info("短信发送成功")
                if self.gui:
                    self.gui.add_sms_log("短信发送成功", "INFO")
            else:
                self.LOG.error("短信发送失败")
                if self.gui:
                    self.gui.add_sms_log("短信发送失败", "ERROR")
        else:
            self.LOG.info("短信功能未启用，跳过发送")
            if self.gui:
                self.gui.add_sms_log("短信功能未启用，跳过发送", "INFO")

    def process_image_message(self, msg: WxMsg, is_group: bool = False) -> None:
        """处理图片消息
        :param msg: 微信消息
        :param is_group: 是否是群消息
        """
        receiver = msg.roomid if is_group else msg.sender
        
        # 检查是否是模拟消息
        is_mock = self.is_mock_message(msg)
        if is_mock and hasattr(msg, 'content') and os.path.isfile(msg.content):
            # 模拟消息，直接使用content作为图片路径
            self.log_to_gui(f"检测到模拟图片消息，使用路径: {msg.content}")
            saved_path = msg.content
            
            # 添加OCR识别章节标题
            if hasattr(self, "gui") and self.gui:
                self.gui.root.after(0, lambda: self.gui.add_section_header("OCR文字识别"))
                
            # OCR识别图片文字
            text = self.image_ocr.extract_text(saved_path)
            
            # 记录图片日志
            sender = msg.sender
            
            if text:
                # 以更明显的方式显示OCR识别结果
                self.log_to_gui("============ OCR识别结果开始 ============", "INFO")
                self.log_to_gui(text, "INFO")
                self.log_to_gui("============ OCR识别结果结束 ============", "INFO")
                
                # 处理识别出的文字
                self.process_strategy_text(text, receiver, [])
            else:
                # 记录空OCR结果
                self.log_to_gui("OCR识别结果: 未识别到文字", "WARNING")
                
                if is_group:
                    self.robot_logger.log_group_image(msg.roomid, sender, saved_path, "未识别到文字", "")
                else:
                    self.robot_logger.log_private_image(sender, saved_path, "未识别到文字", "")
                
                # 不发送消息给用户
            return
            
        # 自动保存图片
        saved_path = self.image_saver.save_image(msg)
        if saved_path:
            self.LOG.info(f"{'群聊' if is_group else '私聊'}图片已保存到: {saved_path}")
            self.log_to_gui(f"图片已保存到: {saved_path}", "INFO")
            
            # 添加OCR识别章节标题
            if hasattr(self, "gui") and self.gui:
                self.gui.root.after(0, lambda: self.gui.add_section_header("OCR文字识别"))
                
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
                    # 不发送消息给用户
                    return
                
                # 处理识别出的文字
                self.process_strategy_text(text, receiver, [])
            else:
                # 记录空OCR结果
                self.log_to_gui("OCR识别结果: 未识别到文字", "WARNING")
                
                if is_group:
                    self.robot_logger.log_group_image(msg.roomid, sender, saved_path, "未识别到文字", "")
                else:
                    self.robot_logger.log_private_image(sender, saved_path, "未识别到文字", "")
                
                # 不发送消息给用户
        else:
            # 记录图片保存失败
            self.log_to_gui("图片保存失败", "ERROR")
            
            if is_group:
                self.robot_logger.log_group_image(msg.roomid, msg.sender, "图片保存失败", "", "")
            else:
                self.robot_logger.log_private_image(msg.sender, "图片保存失败", "", "")
            
            # 不发送消息给用户

    def is_mock_message(self, msg: WxMsg) -> bool:
        """判断是否是模拟消息
        :param msg: 微信消息
        :return: 是否是模拟消息
        """
        # 检查消息ID是否包含mock标记
        if hasattr(msg, 'id') and 'mock' in str(msg.id).lower():
            return True
        # 检查发送者是否是测试用户
        if hasattr(msg, 'sender') and 'test' in str(msg.sender).lower():
            return True
        return False

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
                    self.process_strategy_text(msg.content, msg.roomid, [])
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
                self.process_strategy_text(msg.content, msg.sender, [])
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
        """发送文本消息（重写为不执行任何操作）
        :param msg: 消息内容
        :param receiver: 接收人
        :param at_list: 要@的用户列表
        """
        # 只记录日志，不实际发送消息
        self.log_to_gui(f"[静默模式] 不发送消息到 {receiver}: {msg[:50]}{'...' if len(msg) > 50 else ''}", "INFO")
        
        # 如果在GUI模式下，仍然显示机器人消息（但不实际发送）
        if hasattr(self, "gui") and self.gui:
            self.gui.root.after(0, lambda: self.gui.add_robot_message(f"[静默模式] {msg}"))

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

