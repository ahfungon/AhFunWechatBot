#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging.config
import os
import shutil

import yaml


class Config(object):
    def __init__(self) -> None:
        self.reload()

    def _load_config(self) -> dict:
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _get_value(self, key: str, default_value: str = None) -> str:
        """获取配置值，支持变量替换"""
        config = self._load_config()
        value = config.get(key, default_value)
        
        # 如果是字符串且包含变量引用
        if isinstance(value, str) and "${" in value:
            # 提取变量名
            var_name = value[2:-1]  # 去掉 ${ 和 }
            # 递归获取变量值
            var_value = self._get_value(var_name, "")
            return var_value
        return value

    def reload(self) -> None:
        yconfig = self._load_config()
        logging.config.dictConfig(yconfig["logging"])
        self.GROUPS = yconfig["groups"]["enable"]
        self.NEWS = yconfig["news"]["receivers"]
        self.REPORT_REMINDERS = yconfig["report_reminder"]["receivers"]

        # 获取API配置
        self.API = yconfig.get("api", {})
        if not self.API.get("base_url"):
            self.API["base_url"] = "http://localhost:5000/api/v1"  # 默认值

        # 获取AI模型配置
        self.CHATGPT = yconfig.get("chatgpt", {})
        self.TIGERBOT = yconfig.get("tigerbot", {})
        
        # 处理讯飞星火配置
        xinghuo_config = yconfig.get("xinghuo_web", {})
        if xinghuo_config and "prompt" in xinghuo_config:
            xinghuo_config["prompt"] = self._get_value("xinghuo_web")["prompt"]
        self.XINGHUO_WEB = xinghuo_config
        
        self.CHATGLM = yconfig.get("chatglm", {})
        self.BardAssistant = yconfig.get("bard", {})
        
        # 处理智谱配置
        zhipu_config = yconfig.get("zhipu", {})
        # 不再从config.yaml中读取prompt
        self.ZhiPu = zhipu_config

    @property
    def STOCK_PROMPT(self) -> str:
        """获取股票策略分析提示词"""
        return self._get_value("stock_prompt", "")
