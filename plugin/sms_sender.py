#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional
import json
from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_models
from alibabacloud_tea_util import models as util_models
import logging
import re

class SmsSender:
    """阿里云短信发送插件，负责将策略结果通过短信发送"""
    
    def __init__(self, config: dict) -> None:
        """初始化短信发送插件
        
        Args:
            config: 配置字典，需要包含以下字段：
                - enabled: 是否启用短信功能
                - access_key_id: 阿里云访问密钥ID
                - access_key_secret: 阿里云访问密钥密码
                - sign_name: 短信签名名称
                - template_code: 短信模板CODE
                - phone_number: 接收短信的手机号
        """
        self.LOG = logging.getLogger("SmsSender")
        self.config = config
        
        # 检查是否启用短信功能
        if not self.config.get("enabled", False):
            self.LOG.info("短信功能已关闭")
            self.client = None
            return
            
        self.client = self._create_client()
        self.LOG.info("短信发送插件初始化完成")
        
    def _create_client(self) -> Dysmsapi20170525Client:
        """创建阿里云短信客户端"""
        config = open_api_models.Config(
            access_key_id=self.config.get("access_key_id"),
            access_key_secret=self.config.get("access_key_secret")
        )
        # 访问的域名
        config.endpoint = 'dysmsapi.aliyuncs.com'
        return Dysmsapi20170525Client(config)
        
    def format_strategy_content(self, ai_response: str) -> Optional[dict]:
        """从AI响应中提取并格式化内容
        
        Args:
            ai_response: AI的响应文本
            
        Returns:
            dict: 格式化后的模板参数
        """
        try:
            if not isinstance(ai_response, str):
                self.LOG.error(f"AI响应必须是字符串，而不是 {type(ai_response)}")
                return None

            # 使用正则表达式提取信息
            stock_name = re.search(r"###\s*股票名称\n(.*?)[（\(]", ai_response)
            stock_code = re.search(r"[（\(](\d{6})[）\)]", ai_response)
            action = re.search(r"\*\*操作要求\*\*：(\w+)", ai_response)
            position = re.search(r"\*\*建议数量\*\*：(\d+)%", ai_response)
            price_range = re.search(r"\*\*交易价格\*\*：(\d+)-(\d+)", ai_response)
            
            if not all([stock_name, stock_code, action, position, price_range]):
                missing = []
                if not stock_name: missing.append("服务名称")
                if not stock_code: missing.append("服务ID")
                if not action: missing.append("操作类型")
                if not position: missing.append("资源占用")
                if not price_range: missing.append("阈值范围")
                self.LOG.error(f"无法提取完整信息，缺少: {', '.join(missing)}")
                self.LOG.error(f"原始响应: {ai_response}")
                return None

            # 将操作类型转换为服务器操作
            action_map = {
                "买入": "启动",
                "卖出": "停止",
                "加仓": "扩容",
                "减仓": "缩容",
                "持有": "维持"
            }
            server_action = action_map.get(action.group(1), "未知")

            # 返回模板参数字典
            template_params = {
                "name": stock_name.group(1).strip(),
                "code": f"SRV{stock_code.group(1)}",
                "type": server_action,
                "low": price_range.group(1),
                "high": price_range.group(2),
                "ratio": position.group(1)
            }
            
            self.LOG.info(f"格式化后的模板参数: {template_params}")
            return template_params
            
        except Exception as e:
            self.LOG.error(f"格式化内容时发生错误: {str(e)}")
            self.LOG.error(f"原始响应: {ai_response}")
            return None

    def send_strategy_sms(self, ai_response: str) -> bool:
        """发送提醒短信
        
        Args:
            ai_response: AI的响应文本
            
        Returns:
            bool: 发送是否成功
        """
        # 如果短信功能未启用，直接返回
        if not self.config.get("enabled", False):
            self.LOG.info("短信功能未启用，跳过发送")
            return False
            
        try:
            self.LOG.info("开始处理短信发送请求")
            self.LOG.info(f"AI响应内容: {ai_response}")
            
            # 检查手机号码格式
            phone = self.config.get("phone_number")
            if not phone or not re.match(r'^1[3-9]\d{9}$', phone):
                self.LOG.error(f"手机号码格式错误: {phone}")
                return False
                
            # 格式化内容
            strategy = self.format_strategy_content(ai_response)
            if not strategy:
                self.LOG.error("格式化内容失败，无法发送短信")
                return False
                
            self.LOG.info(f"短信模板参数: {strategy}")
                
            # 构建请求对象
            runtime = util_models.RuntimeOptions()
            
            # 确保所有参数都是字符串类型，并且使用正确的键名
            template_params = {
                "name": str(strategy.get("name", "")),
                "code": str(strategy.get("code", "")),
                "type": str(strategy.get("type", "")),
                "low": str(strategy.get("low", "")),
                "high": str(strategy.get("high", "")),
                "ratio": str(strategy.get("ratio", ""))
            }
            
            # 打印完整的参数内容
            self.LOG.info(f"完整的模板参数: {template_params}")
            param_json = json.dumps(template_params, ensure_ascii=False)
            self.LOG.info(f"JSON格式的模板参数: {param_json}")
            
            send_req = dysmsapi_models.SendSmsRequest(
                phone_numbers=phone,
                sign_name=self.config.get("sign_name"),
                template_code=self.config.get("template_code"),
                template_param=param_json
            )
            
            self.LOG.info(f"发送短信请求: phone={phone}, "
                         f"sign={self.config.get('sign_name')}, "
                         f"template={self.config.get('template_code')}, "
                         f"params={param_json}")
            
            # 发送短信
            result = self.client.send_sms_with_options(send_req, runtime)
            success = result.body.code == "OK"
            
            if success:
                self.LOG.info(f"短信发送成功: {result.body.message}")
                self.LOG.info(f"短信发送状态: code={result.body.code}, message={result.body.message}, requestId={result.body.request_id}")
            else:
                self.LOG.error(f"短信发送失败: code={result.body.code}, message={result.body.message}")
                
            return success
            
        except Exception as e:
            self.LOG.error(f"发送短信时发生错误: {str(e)}")
            return False

    @staticmethod
    def value_check(conf: dict) -> bool:
        """检查配置是否有效
        
        Args:
            conf: 配置字典
            
        Returns:
            bool: 配置是否有效
        """
        if not conf:
            return False
            
        required_fields = [
            "access_key_id",
            "access_key_secret",
            "sign_name",
            "template_code",
            "phone_number"
        ]
        
        return all(conf.get(field) for field in required_fields) 