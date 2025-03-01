# 百度OCR使用指南

## 概述

本项目已从本地Tesseract OCR切换到百度OCR云服务，提供更高的识别准确率和更好的中文识别能力。

## 优势对比

| 特性 | 百度OCR | 本地Tesseract OCR |
|------|---------|-------------------|
| 识别准确率 | ★★★★★ | ★★★☆☆ |
| 中文识别能力 | ★★★★★ | ★★★☆☆ |
| 特殊格式识别 | ★★★★☆ | ★★☆☆☆ |
| 速度 | 取决于网络 | 取决于本地计算能力 |
| 依赖安装 | 简单(仅需pip) | 复杂(需安装Tesseract) |
| 离线使用 | ❌ | ✅ |

## 当前配置

目前使用的是百度OCR的通用文字识别（高精度版），配置如下：

- AppID: 6516508
- API Key: gZndmnu0pn0RqlFVQN8eLctP
- Secret Key: sG3owM5ITEbjW2Md66a9abBjYXCDg6RX

## 使用方法

系统已自动配置为使用百度OCR，无需额外操作。相关功能包括：

1. 聊天中的图片自动OCR识别
2. 股票策略图片分析
3. 其他需要文字识别的功能

## 如何切换回本地OCR

如果需要切换回本地Tesseract OCR，请编辑`plugin/image_ocr.py`文件，注释或删除文件末尾的以下代码：

```python
# 使用百度OCR替代本地OCR
try:
    from plugin.baidu_ocr import ImageOCR as BaiduImageOCR
    # 保存原始的OCR类，以便需要时可以回退
    LocalImageOCR = ImageOCR
    # 重写ImageOCR类
    ImageOCR = BaiduImageOCR
    print("[图片OCR] 已切换到百度OCR服务")
except ImportError:
    print("[图片OCR] 警告: 无法导入百度OCR，继续使用本地OCR")
```

## 测试

可以使用项目根目录下的`test_baidu_ocr.py`脚本测试百度OCR功能：

```bash
python test_baidu_ocr.py <图片路径>
```

如果未指定图片路径，脚本将尝试使用`test_images`目录中的第一个图片文件。

## 注意事项

1. 百度OCR为云服务，使用时需要联网
2. 百度OCR有调用次数限制，具体限制可查看百度AI开放平台
3. 保持稳定的网络连接可以提高OCR的响应速度
4. 高质量、清晰的图片可以提高识别准确率 