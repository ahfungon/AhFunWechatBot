import requests
import json
import logging
import time
from configuration import Config

class StrategyAnalyzer:
    """策略分析插件，负责调用API分析股票策略"""
    
    def __init__(self, base_url: str = "http://localhost:5000") -> None:
        """初始化策略分析插件
        :param base_url: API基础URL
        """
        self.base_url = base_url
        self.logger = logging.getLogger("StrategyAnalyzer")
        self.config = Config()
        self.prompt = self.config.STOCK_PROMPT
        self.max_retries = 3  # 最大重试次数
        self.timeout = 30     # 超时时间（秒）
        print("[策略分析] 初始化完成")
        if self.prompt:
            print("[策略分析] 成功加载提示词模板")
        else:
            print("[策略分析] 警告：未找到提示词模板，将使用默认模板")
    
    def analyze_strategy(self, text: str) -> str:
        """
        分析策略文本并返回格式化的结果
        :param text: 策略文本
        :return: 格式化的分析结果
        """
        for retry in range(self.max_retries):
            try:
                self.logger.info(f"[策略分析] 开始分析文本: {text}")
                if retry > 0:
                    self.logger.info(f"[策略分析] 第{retry + 1}次尝试")
                
                # 调用API分析策略
                url = f"{self.base_url}/api/v1/analyze_strategy"
                self.logger.info(f"[策略分析] 发送请求到: {url}")
                self.logger.info(f"[策略分析] 请求数据: {{'strategy_text': {text}}}")
                
                response = requests.post(
                    url, 
                    json={"strategy_text": text}, 
                    timeout=self.timeout
                )
                self.logger.info(f"[策略分析] 收到响应状态码: {response.status_code}")
                
                # 检查HTTP响应状态
                response.raise_for_status()
                
                # 解析JSON响应
                try:
                    result = response.json()
                    self.logger.info(f"[策略分析] 响应数据: {json.dumps(result, ensure_ascii=False)}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"[策略分析] JSON解析失败: {str(e)}")
                    continue
                
                # 检查响应状态
                if not isinstance(result, dict):
                    self.logger.error(f"[策略分析] 无效的响应格式: {result}")
                    continue
                
                if result.get("code") != 200:
                    self.logger.error(f"[策略分析] API返回错误，状态码: {result.get('code')}, 消息: {result.get('message', '未知错误')}")
                    continue
                
                # 获取分析结果
                data = result.get("data", {})
                self.logger.info(f"[策略分析] 解析后的数据: {json.dumps(data, ensure_ascii=False)}")
                
                # 检查是否与股票无关
                if "error" in data:
                    self.logger.info(f"[策略分析] 非股票内容: {data['error']}")
                    return "这段内容不存在明确的某支股票交易指令，或与股票无关哦~"
                
                if not data:
                    self.logger.warning("[策略分析] 数据为空")
                    continue
                
                # 保存策略
                self.logger.info("[策略分析] 开始保存策略...")
                save_result = self.save_strategy(data)
                self.logger.info(f"[策略分析] 策略保存结果: {'成功' if save_result else '失败'}")
                
                # 格式化输出结果
                output = ["【策略分析结果】", "="*30]
                
                # 基本信息
                output.append(f"股票名称：{data.get('stock_name', '未知')}")
                output.append(f"股票代码：{data.get('stock_code', '未知')}")
                
                # 操作类型
                action = data.get('action')
                if action == 'buy':
                    action_text = '买入'
                elif action == 'sell':
                    action_text = '卖出'
                elif action == 'hold':
                    action_text = '持有'
                else:
                    action_text = '未知'
                output.append(f"操作类型：{action_text}")
                
                output.append(f"仓位比例：{int(data.get('position_ratio', 0) * 100)}%")
                
                # 价格信息（如果有）
                if data.get('price_min') or data.get('price_max'):
                    price_range = []
                    if data.get('price_min'):
                        price_range.append(f"最低{data['price_min']}元")
                    if data.get('price_max'):
                        price_range.append(f"最高{data['price_max']}元")
                    output.append(f"价格区间：{' - '.join(price_range)}")
                
                # 止盈止损（如果有）
                if data.get('take_profit_price'):
                    output.append(f"止盈价位：{data['take_profit_price']}元")
                if data.get('stop_loss_price'):
                    output.append(f"止损价位：{data['stop_loss_price']}元")
                
                # 其他条件和理由（如果有）
                if data.get('other_conditions'):
                    output.append(f"其他条件：{data['other_conditions']}")
                if data.get('reason'):
                    output.append(f"操作理由：{data['reason']}")
                
                output.append("="*30)
                
                # 添加保存状态
                if save_result:
                    output.append("策略已成功保存到系统喵~")
                else:
                    output.append("策略保存失败了喵...")
                
                formatted_result = "\n".join(output)
                self.logger.info(f"[策略分析] 最终输出结果:\n{formatted_result}")
                return formatted_result
                
            except requests.exceptions.Timeout:
                self.logger.error("[策略分析] API请求超时")
                if retry < self.max_retries - 1:
                    time.sleep(2 * (retry + 1))  # 指数退避
                    continue
                return "喵呜...策略分析服务响应超时了..."
            except requests.exceptions.ConnectionError:
                self.logger.error("[策略分析] 无法连接到API服务")
                if retry < self.max_retries - 1:
                    time.sleep(2 * (retry + 1))
                    continue
                return "喵呜...无法连接到策略分析服务..."
            except requests.exceptions.RequestException as e:
                self.logger.error(f"[策略分析] API请求失败: {str(e)}")
                if retry < self.max_retries - 1:
                    time.sleep(2 * (retry + 1))
                    continue
                return "喵呜...策略分析服务暂时无法访问..."
            except Exception as e:
                self.logger.error(f"[策略分析] 策略分析出错: {str(e)}")
                if retry < self.max_retries - 1:
                    time.sleep(2 * (retry + 1))
                    continue
                return "喵呜...策略分析过程中出现错误..."
        
        return "喵呜...多次尝试分析策略都失败了..."

    def save_strategy(self, strategy_data: dict) -> bool:
        """
        保存策略到系统
        :param strategy_data: 策略数据
        :return: 是否保存成功
        """
        for retry in range(self.max_retries):
            try:
                self.logger.info(f"[策略分析] 开始保存策略，数据: {json.dumps(strategy_data, ensure_ascii=False)}")
                
                url = f"{self.base_url}/api/v1/strategies"
                self.logger.info(f"[策略分析] 发送保存请求到: {url}")
                
                response = requests.post(url, json=strategy_data, timeout=self.timeout)
                self.logger.info(f"[策略分析] 保存请求响应状态码: {response.status_code}")
                
                # 检查HTTP响应状态
                response.raise_for_status()
                
                # 解析JSON响应
                try:
                    result = response.json()
                    self.logger.info(f"[策略分析] 保存响应数据: {json.dumps(result, ensure_ascii=False)}")
                except json.JSONDecodeError as e:
                    self.logger.error(f"[策略分析] 保存策略时JSON解析失败: {str(e)}")
                    continue
                
                # 检查响应状态和数据内容
                if not isinstance(result, dict):
                    self.logger.error(f"[策略分析] 保存策略时收到无效的响应格式: {result}")
                    continue
                
                if result.get("code") == 200 and "error" not in result.get("data", {}):
                    self.logger.info(f"[策略分析] 策略保存成功: {strategy_data.get('stock_name')}")
                    return True
                
                error_msg = result.get("data", {}).get("error") or result.get("message")
                self.logger.error(f"[策略分析] 策略保存失败: {error_msg}")
                
            except requests.exceptions.Timeout:
                self.logger.error("[策略分析] 保存策略时请求超时")
                if retry < self.max_retries - 1:
                    time.sleep(2 * (retry + 1))
                    continue
            except requests.exceptions.ConnectionError:
                self.logger.error("[策略分析] 保存策略时无法连接到服务")
                if retry < self.max_retries - 1:
                    time.sleep(2 * (retry + 1))
                    continue
            except requests.exceptions.RequestException as e:
                self.logger.error(f"[策略分析] 保存策略时请求失败: {str(e)}")
                if retry < self.max_retries - 1:
                    time.sleep(2 * (retry + 1))
                    continue
            except Exception as e:
                self.logger.error(f"[策略分析] 保存策略时出错: {str(e)}")
                if retry < self.max_retries - 1:
                    time.sleep(2 * (retry + 1))
                    continue
        
        return False

if __name__ == "__main__":
    # 测试代码
    analyzer = StrategyAnalyzer()
    test_text = "以30元买入平安银行，仓位30%"
    result = analyzer.analyze_strategy(test_text)
    print(result) 