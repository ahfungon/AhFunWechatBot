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
        pwd = os.path.dirname(os.path.abspath(__file__))
        try:
            with open(f"{pwd}/config.yaml", "rb") as fp:
                yconfig = yaml.safe_load(fp)
        except FileNotFoundError:
            shutil.copyfile(f"{pwd}/config.yaml.template", f"{pwd}/config.yaml")
            with open(f"{pwd}/config.yaml", "rb") as fp:
                yconfig = yaml.safe_load(fp)

        return yconfig

    def _get_value(self, key: str, default=None):
        """获取配置值，支持变量替换"""
        yconfig = self._load_config()
        value = yconfig.get(key, default)
        
        # 如果是字符串，检查是否需要变量替换
        if isinstance(value, str) and "${" in value:
            # 替换 ${xxx} 格式的变量
            for var_key in yconfig:
                if isinstance(yconfig[var_key], str):
                    placeholder = "${" + var_key + "}"
                    if placeholder in value:
                        value = value.replace(placeholder, yconfig[var_key])
        return value

    def reload(self) -> None:
        yconfig = self._load_config()
        logging.config.dictConfig(yconfig["logging"])
        self.GROUPS = yconfig["groups"]["enable"]
        self.NEWS = yconfig["news"]["receivers"]
        self.REPORT_REMINDERS = yconfig["report_reminder"]["receivers"]

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
        if zhipu_config and "prompt" in zhipu_config:
            zhipu_config["prompt"] = self._get_value("zhipu")["prompt"]
        self.ZhiPu = zhipu_config

    @property
    def STOCK_PROMPT(self) -> str:
        """获取股票策略分析提示词"""
        return self._get_value("stock_prompt", "")
