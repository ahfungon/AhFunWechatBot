"""
百度OCR测试脚本
用于测试百度OCR功能是否正常工作
"""

import os
import sys
from plugin.baidu_ocr import ImageOCR

def test_ocr(image_path):
    """测试OCR功能"""
    # 初始化OCR
    ocr = ImageOCR()
    
    # 确认图片存在
    if not os.path.exists(image_path):
        print(f"错误: 图片不存在: {image_path}")
        return
    
    print(f"开始识别图片: {image_path}")
    
    # 执行OCR识别
    text = ocr.extract_text(image_path)
    
    if not text:
        print("识别结果为空")
        return
    
    # 输出识别结果
    print("\n" + "="*50)
    print("OCR识别结果:")
    print("="*50)
    print(text)
    print("="*50)
    print(f"共识别 {text.count('\n') + 1} 行文字")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # 使用默认测试图片，如果存在
        test_dir = "test_images"
        if os.path.exists(test_dir):
            image_files = [f for f in os.listdir(test_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if image_files:
                image_path = os.path.join(test_dir, image_files[0])
                print(f"使用默认测试图片: {image_path}")
            else:
                print("未找到测试图片，请指定图片路径作为命令行参数")
                print("使用方法: python test_baidu_ocr.py <图片路径>")
                sys.exit(1)
        else:
            print("未找到测试图片目录，请指定图片路径作为命令行参数")
            print("使用方法: python test_baidu_ocr.py <图片路径>")
            sys.exit(1)
    
    # 执行测试
    test_ocr(image_path) 