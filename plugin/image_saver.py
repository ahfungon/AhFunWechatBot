import os
import time
import re
from datetime import datetime
from wcferry import Wcf, WxMsg

class ImageSaver:
    """图片保存插件，负责将接收到的图片保存到指定文件夹"""
    
    def __init__(self, wcf: Wcf = None) -> None:
        self.wcf = wcf
        # 使用绝对路径
        self.save_dir = os.path.abspath("img")
        self.max_retries = 3
        
        # 确保保存目录存在
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            print(f"[图片保存] 创建目录: {self.save_dir}")
        
        print(f"[图片保存] 使用保存目录: {self.save_dir}")
    
    def parse_image_path(self, file_path: str, msg: WxMsg) -> dict:
        """
        解析图片文件路径，提取有用信息
        :param file_path: 文件路径
        :param msg: 消息对象，用于获取来源信息
        :return: 包含解析信息的字典
        """
        info = {}
        try:
            # 使用正则表达式提取信息
            pattern = r".*\\(\d{4})-(\d{2})\\([a-f0-9]+)\.dat$"
            match = re.search(pattern, file_path.replace("/", "\\"))
            
            # 获取当前时间
            now = datetime.now()
            # 确定消息来源（群聊/单聊）
            source_type = "group" if msg.from_group() else "private"
            # 获取发送者ID（群ID或个人ID）
            sender_id = msg.roomid if msg.from_group() else msg.sender
            
            if match:
                year, month, image_hash = match.groups()
                info["year"] = year
                info["month"] = month
                info["hash"] = image_hash
                info["time"] = f"{year}-{month}"
                
                # 构造新的文件名：YYYYMMDD_HHMMSS_来源_ID_hash.jpg
                info["new_filename"] = (
                    f"{now.strftime('%Y%m%d_%H%M%S')}"
                    f"_{source_type}"
                    f"_{sender_id[-8:]}"  # 使用ID的最后8位
                    f"_{image_hash}.jpg"
                )
            else:
                # 如果无法解析，使用时间戳作为文件名
                info["time"] = now.strftime("%Y-%m")
                info["new_filename"] = (
                    f"{now.strftime('%Y%m%d_%H%M%S')}"
                    f"_{source_type}"
                    f"_{sender_id[-8:]}"
                    f"_unknown.jpg"
                )
                
            print(f"[图片保存] 文件信息解析: {info}")
            return info
        except Exception as e:
            print(f"[图片保存] 解析文件路径出错: {str(e)}")
            # 发生错误时使用时间戳
            info["time"] = now.strftime("%Y-%m")
            info["new_filename"] = (
                f"{now.strftime('%Y%m%d_%H%M%S')}"
                f"_{source_type}"
                f"_{sender_id[-8:]}"
                f"_error.jpg"
            )
            return info
    
    def wait_for_file(self, file_path: str, timeout: int = 10, stable_threshold: int = 3) -> bool:
        """
        等待文件下载完成并且大小稳定
        :param file_path: 文件路径
        :param timeout: 超时时间（秒）
        :param stable_threshold: 文件大小保持稳定的次数阈值
        :return: 是否成功
        """
        start_time = time.time()
        last_size = -1
        stable_count = 0
        check_interval = 0.5  # 检查间隔（秒）
        
        while time.time() - start_time < timeout:
            if os.path.exists(file_path):
                try:
                    current_size = os.path.getsize(file_path)
                    print(f"[图片保存] 文件大小: {current_size} 字节")
                    
                    if current_size == last_size:
                        stable_count += 1
                        print(f"[图片保存] 文件大小稳定次数: {stable_count}/{stable_threshold}")
                        if stable_count >= stable_threshold:
                            print(f"[图片保存] 文件已稳定: {file_path}")
                            return True
                    else:
                        stable_count = 0
                        print(f"[图片保存] 文件大小变化: {last_size} -> {current_size}")
                    last_size = current_size
                except Exception as e:
                    print(f"[图片保存] 检查文件大小出错: {str(e)}")
                    stable_count = 0
            else:
                print(f"[图片保存] 等待文件出现: {file_path}")
            time.sleep(check_interval)
            
        print(f"[图片保存] 等待超时: {timeout}秒")
        return False
    
    def save_image(self, msg: WxMsg) -> str:
        if not self.wcf:
            print("[图片保存] 错误: wcf未初始化")
            return ""
            
        if msg.type != 0x03:  # 不是图片消息
            return ""
            
        print(f"[图片保存] 开始处理图片消息:")
        print(f"- 消息ID: {msg.id}")
        print(f"- 消息类型: {type(msg.id)}")
        print(f"- Thumb: {msg.thumb}")
        print(f"- Extra: {msg.extra}")
        print(f"- 来源: {'群聊' if msg.from_group() else '单聊'}")
        print(f"- 发送者: {msg.roomid if msg.from_group() else msg.sender}")
        print(f"- WxMsg类型: {type(msg).__name__}")
        print(f"- WxMsg类的所有属性: {dir(msg)}")
        
        # 处理消息ID
        try:
            msg_id = int(msg.id)
            print(f"[图片保存] 消息ID (int): {msg_id}")
        except (ValueError, TypeError):
            # 如果消息ID无效，使用当前时间戳作为ID
            msg_id = int(time.time())
            print(f"[图片保存] 消息ID无效，使用时间戳替代: {msg_id}")
        
        # 检查extra属性
        if not msg.extra:
            print(f"[图片保存] 错误: 消息缺少extra属性")
            # 尝试从get_user_img获取图片
            try:
                img_path = self.wcf.get_user_img(msg_id)
                if img_path and os.path.exists(img_path):
                    # 获取文件名和扩展名
                    _, filename = os.path.split(img_path)
                    # 创建年月子目录
                    now = time.localtime()
                    year_month = f"{now.tm_year}-{now.tm_mon:02d}"
                    year_month_dir = os.path.join(self.save_dir, year_month)
                    if not os.path.exists(year_month_dir):
                        os.makedirs(year_month_dir)
                    # 构造新的文件名
                    new_filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{filename}"
                    target_path = os.path.join(year_month_dir, new_filename)
                    # 复制文件
                    import shutil
                    shutil.copy2(img_path, target_path)
                    print(f"[图片保存] 直接复制图片: {img_path} -> {target_path}")
                    return target_path
                else:
                    print(f"[图片保存] 获取图片失败: {img_path}")
            except Exception as e:
                print(f"[图片保存] 尝试获取图片时出错: {str(e)}")
            return ""
        
        # 解析图片信息
        image_info = self.parse_image_path(msg.extra, msg)  # 传入msg参数
        
        # 创建年月子目录
        year_month_dir = os.path.join(self.save_dir, image_info["time"])
        if not os.path.exists(year_month_dir):
            os.makedirs(year_month_dir)
            print(f"[图片保存] 创建年月目录: {year_month_dir}")
        
        for retry in range(self.max_retries):
            try:
                print(f"[图片保存] 第{retry + 1}次尝试处理图片...")
                
                # 第一步：使用download_attach下载.dat文件
                print(f"[图片保存] 步骤1: 下载.dat文件...")
                print(f"调用参数: id={msg_id}, thumb={msg.thumb}, extra={msg.extra}")
                result = self.wcf.download_attach(
                    id=msg_id,
                    thumb=msg.thumb,
                    extra=msg.extra
                )
                
                if result != 0:
                    print(f"[图片保存] .dat文件下载失败，错误码: {result}")
                    continue
                
                # 等待.dat文件下载完成并稳定
                print(f"[图片保存] 等待.dat文件下载完成并稳定...")
                if not self.wait_for_file(msg.extra, timeout=60, stable_threshold=5):
                    print(f"[图片保存] .dat文件下载或稳定超时")
                    continue
                
                print(f"[图片保存] .dat文件下载成功并稳定: {msg.extra}")
                
                # 额外等待一段时间，确保文件完全写入
                time.sleep(2)
                
                # 第二步：使用download_image保存图片
                print(f"[图片保存] 步骤2: 转换并保存图片...")
                saved_path = self.wcf.download_image(
                    id=msg_id,
                    extra=msg.extra,
                    dir=year_month_dir  # 使用年月子目录
                )
                
                print(f"下载后路径: {saved_path}")
                
                if saved_path and os.path.exists(saved_path):
                    # 等待图片文件保存完成并稳定
                    if self.wait_for_file(saved_path, timeout=30, stable_threshold=3):
                        # 重命名文件
                        new_path = os.path.join(year_month_dir, image_info["new_filename"])
                        try:
                            os.rename(saved_path, new_path)
                            saved_path = new_path
                            print(f"[图片保存] 文件已重命名: {saved_path}")
                        except Exception as e:
                            print(f"[图片保存] 重命名失败: {str(e)}")
                        
                        print(f"[图片保存] 成功: {saved_path}")
                        print(f"[图片保存] 文件大小: {os.path.getsize(saved_path)} 字节")
                        return saved_path
                    else:
                        print("[图片保存] 等待图片保存完成超时")
                else:
                    print("[图片保存] 图片保存失败")
                
                if retry < self.max_retries - 1:
                    print("[图片保存] 等待3秒后重试...")
                    time.sleep(3)
                    
            except Exception as e:
                print(f"[图片保存] 第{retry + 1}次尝试出错: {str(e)}")
                if retry < self.max_retries - 1:
                    print("[图片保存] 等待3秒后重试...")
                    time.sleep(3)
        
        print("[图片保存] 失败: 已达到最大重试次数")
        return ""