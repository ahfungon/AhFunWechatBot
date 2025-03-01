import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class Strategy:
    """策略数据模型"""
    def __init__(self, 
                 stock_name: str,
                 stock_code: str,
                 action: str,  # 支持"buy"、"sell"、"hold"三种操作类型
                 price_min: float = None,
                 price_max: float = None,
                 position_ratio: float = None,
                 take_profit_price: float = None,
                 stop_loss_price: float = None,
                 reason: str = None):
        self.id = None  # 会在保存时生成
        self.stock_name = stock_name
        self.stock_code = stock_code
        self.action = action
        self.price_min = price_min
        self.price_max = price_max
        self.position_ratio = position_ratio
        self.take_profit_price = take_profit_price
        self.stop_loss_price = stop_loss_price
        self.reason = reason
        self.created_at = datetime.now()
        self.is_active = True
        self.execution_status = "pending"  # pending, executed, expired

    def to_dict(self) -> dict:
        """转换为字典格式"""
        data = {
            "stock_name": self.stock_name,
            "stock_code": self.stock_code,
            "action": self.action,
            "price_min": self.price_min,
            "price_max": self.price_max,
            "position_ratio": self.position_ratio,
            "take_profit_price": self.take_profit_price,
            "stop_loss_price": self.stop_loss_price,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active
        }
        
        # 只有在已有ID的情况下才添加ID字段
        if self.id is not None:
            data["id"] = self.id
            
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Strategy':
        """从字典创建策略对象"""
        strategy = cls(
            stock_name=data["stock_name"],
            stock_code=data["stock_code"],
            action=data["action"],
            price_min=data.get("price_min"),
            price_max=data.get("price_max"),
            position_ratio=data.get("position_ratio"),
            take_profit_price=data.get("take_profit_price"),
            stop_loss_price=data.get("stop_loss_price"),
            reason=data.get("reason")
        )
        strategy.id = data.get("id")
        strategy.created_at = datetime.fromisoformat(data["created_at"])
        strategy.is_active = data.get("is_active", True)
        strategy.execution_status = data.get("execution_status", "pending")
        return strategy

class StrategyManager:
    """策略管理器"""
    def __init__(self):
        from configuration import Config
        config = Config()
        self.base_url = config.API["base_url"].rstrip('/')

    def _call_api(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        """调用API接口
        :param method: 请求方法（GET, POST, PUT, DELETE）
        :param endpoint: 接口路径
        :param data: 请求数据
        :return: 响应数据
        """
        try:
            import requests
            
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            print(f"\n===========调用接口==========")
            print(f"请求方法：{method}")
            print(f"接口地址：{url}")
            if data:
                print(f"请求数据：{json.dumps(data, ensure_ascii=False, indent=2)}")
            
            response = requests.request(method, url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"返回结果：{json.dumps(result, ensure_ascii=False, indent=2)}")
                if result.get("code") == 200:
                    return result.get("data")
                else:
                    print(f"[策略管理] 接口调用失败: {result.get('message')}")
            else:
                print(f"[策略管理] 接口调用失败: HTTP {response.status_code}")
                
            return None
        except Exception as e:
            print(f"[策略管理] 接口调用出错: {str(e)}")
            return None

    def add_strategy(self, strategy: Strategy) -> Tuple[bool, str, Optional[Strategy]]:
        """添加新策略
        :return: (是否成功, 消息, 更新后的策略对象)
        """
        print("\n" + "="*50)
        print("检查重复策略")
        print("="*50)
        print(f"检查股票：{strategy.stock_name}({strategy.stock_code})")
        print(f"操作类型：{'买入' if strategy.action == 'buy' else '卖出'}")
        
        # 检查是否存在重复策略
        existing_strategy = self.find_duplicate_strategy(strategy)
        if existing_strategy:
            print(f"发现重复策略：ID={existing_strategy.id}")
            print("="*50)
            
            # 准备更新数据
            updates = {
                "price_min": strategy.price_min,
                "price_max": strategy.price_max,
                "position_ratio": strategy.position_ratio,
                "take_profit_price": strategy.take_profit_price,
                "stop_loss_price": strategy.stop_loss_price,
                "reason": strategy.reason
            }
            
            # 检查仓位变化和执行状态
            if strategy.position_ratio > existing_strategy.position_ratio:
                print(f"仓位增加：{existing_strategy.position_ratio * 100}% -> {strategy.position_ratio * 100}%")
                if existing_strategy.execution_status == "executed":
                    print("原策略已全部执行，更新状态为部分执行")
                    updates["execution_status"] = "partial"
            
            # 调用更新接口
            result = self._call_api("PUT", f"/strategies/{existing_strategy.id}", updates)
            if result:
                # 更新本地Strategy对象的状态
                existing_strategy = Strategy.from_dict(result)
                print(f"更新策略成功：ID={existing_strategy.id}")
                print("="*50)
                return True, f"已更新{strategy.stock_name}的{strategy.action}策略喵~", existing_strategy
            else:
                return False, "更新策略失败喵~", None

        # 调用创建策略接口
        result = self._call_api("POST", "/strategies", strategy.to_dict())
        if result:
            # 创建新的Strategy对象
            new_strategy = Strategy.from_dict(result)
            print(f"新增策略成功：ID={new_strategy.id}")
            print("="*50)
            return True, f"已添加{strategy.stock_name}的{strategy.action}策略喵~", new_strategy
        else:
            return False, "创建策略失败喵~", None

    def find_duplicate_strategy(self, strategy: Strategy) -> Optional[Strategy]:
        """查找重复策略
        调用查重接口检查是否存在重复策略
        """
        print("\n" + "="*50)
        print("调用查重接口")
        print("="*50)
        
        # 准备请求参数
        params = {
            "stock_name": strategy.stock_name,
            "stock_code": strategy.stock_code,
            "action": strategy.action
        }
        
        result = self._call_api("POST", "/strategies/check", params)
        if result:
            return Strategy.from_dict(result)
        return None

    def update_strategy(self, strategy_id: int, **updates) -> Tuple[bool, str]:
        """更新策略
        :return: (是否成功, 消息)
        """
        result = self._call_api("PUT", f"/strategies/{strategy_id}", updates)
        if result:
            return True, f"已更新策略喵~"
        return False, "更新策略失败喵~"

    def get_strategy(self, strategy_id: int) -> Optional[Strategy]:
        """获取指定策略"""
        result = self._call_api("GET", f"/strategies/{strategy_id}")
        if result:
            return Strategy.from_dict(result)
        return None

    def list_active_strategies(self) -> List[Strategy]:
        """获取所有有效策略"""
        result = self._call_api("GET", "/strategies", {"is_active": True})
        if result:
            return [Strategy.from_dict(data) for data in result]
        return []

    def cleanup_expired_strategies(self) -> None:
        """清理过期策略（7天）
        通过调用搜索接口，获取所有策略，然后根据时间判断是否需要清理
        """
        try:
            # 获取所有有效策略
            result = self._call_api("GET", "/strategies", {"is_active": True})
            if not result:
                print("[策略管理] 获取策略列表失败")
                return

            # 计算7天前的时间
            expire_time = datetime.now() - timedelta(days=7)
            
            # 遍历策略，检查是否过期
            for strategy_data in result:
                strategy = Strategy.from_dict(strategy_data)
                if strategy.created_at < expire_time:
                    # 调用停用策略接口
                    self._call_api("POST", f"/strategies/{strategy.id}/deactivate")
                    print(f"[策略管理] 清理过期策略：{strategy.stock_name}({strategy.stock_code})")
                    
        except Exception as e:
            print(f"[策略管理] 清理过期策略出错: {str(e)}")

    def extract_stock_info(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """从文本中提取股票信息
        :return: (股票名称, 股票代码, 操作类型)
        """
        print(f"[策略管理] 开始提取股票信息: {text}")
        
        # 提取股票名称和代码
        stock_patterns = [
            r"(?:【|###)\s*股票名称\s*(?:】|\n)\s*(.*?)\s*[（(](\d{6})[)）]",
            r"###\s*股票名称\s*(.*?)\s*[（(](\d{6})[)）]",
            r"【(.*?)】\s*[（(](\d{6})[)）]"
        ]
        
        stock_name = None
        stock_code = None
        
        for pattern in stock_patterns:
            stock_match = re.search(pattern, text, re.DOTALL)
            if stock_match:
                stock_name = stock_match.group(1).strip()
                stock_code = stock_match.group(2)
                break

        if not stock_name or not stock_code:
            print(f"[策略管理] 无法匹配股票信息")
            return None, None, None

        # 提取操作类型
        action = None
        if any(keyword in text for keyword in ["买入策略", "建仓策略", "入场策略", "买入时机"]):
            action = "buy"
        elif any(keyword in text for keyword in ["卖出策略", "清仓策略", "离场策略", "卖出时机"]):
            action = "sell"
        elif any(keyword in text for keyword in ["持有建议", "继续持有", "持股待涨"]):
            action = "hold"

        print(f"[策略管理] 提取结果: 股票={stock_name}, 代码={stock_code}, 操作={action}")
        return stock_name, stock_code, action

    def extract_price_info(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """从文本中提取价格信息
        :return: (最小价格, 最大价格)
        """
        print(f"[策略管理] 开始提取价格信息")
        
        # 提取价格范围的模式
        price_patterns = [
            r"交易价格[：:]\s*(\d+\.?\d*)-(\d+\.?\d*)元",
            r"价格区间[：:]\s*最低\s*(\d+\.?\d*)\s*元\s*-\s*最高\s*(\d+\.?\d*)\s*元",
            r"目标价格[：:]\s*(\d+\.?\d*)-(\d+\.?\d*)元",
            r"(?:买入|卖出)价格[：:]\s*(\d+\.?\d*)-(\d+\.?\d*)元"
        ]
        
        for pattern in price_patterns:
            price_match = re.search(pattern, text)
            if price_match:
                min_price = float(price_match.group(1))
                max_price = float(price_match.group(2))
                print(f"[策略管理] 提取到价格区间: {min_price}-{max_price}元")
                return min_price, max_price
        
        # 尝试提取单个价格
        single_price_patterns = [
            r"交易价格[：:]\s*(\d+\.?\d*)元",
            r"目标价格[：:]\s*(\d+\.?\d*)元",
            r"(?:买入|卖出)价格[：:]\s*(\d+\.?\d*)元"
        ]
        
        for pattern in single_price_patterns:
            single_price_match = re.search(pattern, text)
            if single_price_match:
                price = float(single_price_match.group(1))
                print(f"[策略管理] 提取到单一价格: {price}元")
                return price, price
            
        print(f"[策略管理] 无法提取价格信息")
        return None, None

    def extract_position_ratio(self, text: str) -> Optional[float]:
        """从文本中提取仓位比例"""
        ratio_pattern = r"(\d+)%仓位"
        ratio_match = re.search(ratio_pattern, text)
        if ratio_match:
            return float(ratio_match.group(1)) / 100
        return None

    def extract_stop_prices(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """从文本中提取止盈止损价格
        :return: (止损价格, 止盈价格)
        """
        print(f"[策略管理] 开始提取止盈止损价格")
        stop_loss = None
        take_profit = None

        # 提取止损价格
        stop_loss_patterns = [
            r"止损价格[：:]\s*(\d+\.?\d*)元",
            r"止损价位[：:]\s*(\d+\.?\d*)元",
            r"止损位[：:]\s*(\d+\.?\d*)元",
            r"止损设置[：:]\s*(\d+\.?\d*)元"
        ]
        
        for pattern in stop_loss_patterns:
            stop_loss_match = re.search(pattern, text)
            if stop_loss_match:
                stop_loss = float(stop_loss_match.group(1))
                print(f"[策略管理] 提取到止损价格: {stop_loss}元")
                break

        # 提取止盈价格
        take_profit_patterns = [
            r"止盈价格[：:]\s*(\d+\.?\d*)元",
            r"止盈价位[：:]\s*(\d+\.?\d*)元",
            r"止盈位[：:]\s*(\d+\.?\d*)元",
            r"止盈目标[：:]\s*(\d+\.?\d*)元"
        ]
        
        for pattern in take_profit_patterns:
            take_profit_match = re.search(pattern, text)
            if take_profit_match:
                take_profit = float(take_profit_match.group(1))
                print(f"[策略管理] 提取到止盈价格: {take_profit}元")
                break

        if not stop_loss and not take_profit:
            print(f"[策略管理] 无法提取止盈止损信息")
        return stop_loss, take_profit

    def extract_reason(self, text: str) -> Optional[str]:
        """从文本中提取操作理由"""
        reason_pattern = r"持股理由[：:](.*?)(?=###|$)"
        reason_match = re.search(reason_pattern, text, re.DOTALL)
        if reason_match:
            reason = reason_match.group(1).strip()
            # 将理由分点提取并合并
            points = re.findall(r"[-•]\s*(.*?)(?=[-•]|$)", reason, re.DOTALL)
            if points:
                return "；".join(point.strip() for point in points if point.strip())
            return reason
        return None

    def _markdown_to_json(self, text: str) -> dict:
        """将Markdown格式的策略文本转换为JSON格式
        :param text: Markdown格式的策略文本
        :return: 转换后的JSON数据
        """
        try:
            print("[策略管理] 开始解析Markdown文本")
            
            # 提取股票信息
            stock_match = re.search(r"###\s*股票名称\s*(.*?)\s*[（(](\d{6})[)）]", text, re.DOTALL)
            if not stock_match:
                print("[策略管理] 无法提取股票信息")
                return {}
                
            stock_name = stock_match.group(1).strip()
            stock_code = stock_match.group(2)
            
            # 提取价格信息
            price_match = re.search(r"交易价格[：:]\s*(\d+\.?\d*)-(\d+\.?\d*)元", text)
            price_min = float(price_match.group(1)) if price_match else None
            price_max = float(price_match.group(2)) if price_match else None
            
            # 提取仓位信息
            position_match = re.search(r"建议数量[：:]\s*(\d+)%", text)
            position_ratio = float(position_match.group(1))/100 if position_match else None
            
            # 提取止损价格
            stop_loss_match = re.search(r"止损[：:][^。]*?(\d+\.?\d*)元", text)
            stop_loss = float(stop_loss_match.group(1)) if stop_loss_match else None
            
            # 提取止盈价格
            take_profit_match = re.search(r"止盈[：:][^。]*?(\d+\.?\d*)元", text)
            take_profit = float(take_profit_match.group(1)) if take_profit_match else None
            
            # 提取操作理由
            reason_match = re.search(r"持股理由[：:](.*?)(?=###|$)", text, re.DOTALL)
            if reason_match:
                reason = reason_match.group(1).strip()
                # 提取分点信息
                points = re.findall(r"[-•]\s*(.*?)(?=[-•]|$)", reason, re.DOTALL)
                reason = "；".join(point.strip() for point in points if point.strip())
            else:
                reason = None
                
            # 判断操作类型
            action = "buy" if "买入" in text or "建仓" in text or "入场" in text else "sell"
            
            return {
                "stock_name": stock_name,
                "stock_code": stock_code,
                "action": action,
                "price_min": price_min,
                "price_max": price_max,
                "position_ratio": position_ratio,
                "take_profit_price": take_profit,
                "stop_loss_price": stop_loss,
                "reason": reason
            }
            
        except Exception as e:
            print(f"[策略管理] Markdown解析错误: {str(e)}")
            return {}

    def analyze_strategy(self, text: str) -> Optional[dict]:
        """调用策略分析接口
        :param text: 策略文本
        :return: 分析结果
        """
        try:
            import requests
            from configuration import Config
            
            print("\n===========获取到用户发送信息========")
            print(f"信息内容：\n{text}")
            
            # 从配置中获取API URL
            config = Config()
            base_url = config.API["base_url"]
            url = f"{base_url.rstrip('/')}/analyze_strategy"
            
            print("\n===========调用策略分析接口==========")
            print(f"接口地址：{url}")
            print(f"传入参数：{{'strategy_text': {text}}}")
            
            response = requests.post(url, json={"strategy_text": text})
            
            if response.status_code == 200:
                result = response.json()
                print(f"返回结果：{result}")
                
                if result.get("code") == 200:
                    return result.get("data")
                else:
                    print(f"[策略管理] 策略分析失败: {result.get('message')}")
            else:
                print(f"[策略管理] 接口调用失败: {response.status_code}")
                
            return None
        except Exception as e:
            print(f"[策略管理] 策略分析出错: {str(e)}")
            return None

    def create_strategy(self, text: str) -> Optional[Strategy]:
        """从AI分析结果创建新策略
        :param text: AI分析返回的文本
        :return: Strategy对象或None
        """
        try:
            # 调用策略分析接口
            data = self.analyze_strategy(text)
            if not data:
                print("[策略管理] 策略分析失败")
                return None
            
            print("\n" + "="*50)
            print("结构化分析返回策略")
            print("="*50)
            
            # 格式化显示策略信息
            strategy_info = {
                "股票名称": data.get("stock_name"),
                "股票代码": data.get("stock_code"),
                "操作类型": "买入" if data.get("action") == "buy" else "卖出",
                "价格区间": f"{data.get('price_min')}-{data.get('price_max')}元",
                "仓位比例": f"{data.get('position_ratio', 0) * 100}%",  # 0.1 代表 10%
                "止损价格": f"{data.get('stop_loss_price')}元" if data.get('stop_loss_price') else "未设置",
                "止盈价格": f"{data.get('take_profit_price')}元" if data.get('take_profit_price') else "未设置",
                "操作理由": data.get("reason", data.get("other_conditions", "未提供"))
            }
            
            # 打印格式化的策略信息
            for key, value in strategy_info.items():
                print(f"{key}：{value}")
            
            print("="*50)
                
            # 创建策略对象
            strategy = Strategy(
                stock_name=data.get("stock_name"),
                stock_code=data.get("stock_code"),
                action=data.get("action"),
                price_min=data.get("price_min"),
                price_max=data.get("price_max"),
                position_ratio=data.get("position_ratio"),
                take_profit_price=data.get("take_profit_price"),
                stop_loss_price=data.get("stop_loss_price"),
                reason=data.get("reason", data.get("other_conditions"))
            )
            
            print(f"\n[策略管理] 创建策略对象: {strategy.stock_name}({strategy.stock_code})")
            return strategy
            
        except Exception as e:
            print(f"[策略管理] 创建策略出错: {str(e)}")
            return None

    def format_strategy_message(self, strategy: Strategy) -> str:
        """格式化策略消息"""
        if strategy.action == "buy":
            action_text = "买入"
        elif strategy.action == "sell":
            action_text = "卖出"
        else:
            action_text = "持有"
            
        msg_parts = [
            f"【{strategy.stock_name}（{strategy.stock_code}）{action_text}策略】"
        ]

        if strategy.price_min is not None:
            if strategy.price_min == strategy.price_max:
                msg_parts.append(f"目标价格：{strategy.price_min}元")
            else:
                msg_parts.append(f"目标价格区间：{strategy.price_min}-{strategy.price_max}元")

        if strategy.position_ratio is not None:
            msg_parts.append(f"建议仓位：{strategy.position_ratio * 100}%")  # 0.1 代表 10%

        if strategy.stop_loss_price is not None:
            msg_parts.append(f"止损价格：{strategy.stop_loss_price}元")

        if strategy.take_profit_price is not None:
            msg_parts.append(f"止盈价格：{strategy.take_profit_price}元")

        if strategy.reason:
            msg_parts.append(f"操作理由：{strategy.reason}")

        msg_parts.append(f"执行状态：{strategy.execution_status}")
        
        return "\n".join(msg_parts) 