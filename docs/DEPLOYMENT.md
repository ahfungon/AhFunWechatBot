# 部署指南

## 环境要求

- Python 3.8+
- Windows 10/11 操作系统
- 微信 3.9.2.23

## 安装步骤

1. 克隆项目到本地

2. 安装依赖
```bash
pip install -r requirements.txt
```

如果遇到阿里云短信SDK相关错误，请尝试单独安装：
```bash
pip install alibabacloud-tea>=0.4.2 alibabacloud-tea-openapi>=0.3.8 alibabacloud-tea-util>=0.3.13 alibabacloud-dysmsapi20170525>=3.0.0
```

3. 配置文件
- 复制 `config.yaml.template` 为 `config.yaml`
- 填写相关API密钥和配置信息：
  - OpenAI API Key
  - 百度OCR相关密钥
  - 阿里云短信配置（如需使用）
  - 其他AI平台密钥

4. 短信功能配置（可选）
如果需要使用短信通知功能，请在 `config.yaml` 中配置以下内容：
```yaml
sms:
  enabled: true  # 设置为true启用短信功能
  access_key_id: "你的阿里云AccessKey ID"
  access_key_secret: "你的阿里云AccessKey Secret"
  sign_name: "你的短信签名"
  template_code: "你的短信模板CODE"
  phone_number: "接收短信的手机号"
```

5. 启动微信
- 使用符合版本要求的微信客户端
- 确保已经登录目标微信账号

6. 运行机器人
```bash
python main.py
```

## 常见问题

1. wcferry 安装失败
- 确保使用的是最新版本 39.4.2.2
- 检查 Python 版本兼容性

2. OCR 相关问题
- 确保已正确安装 Tesseract（本地OCR）
- 检查百度OCR密钥配置

3. 短信发送失败
- 验证阿里云账号余额
- 检查短信模板配置
- 确保在 `config.yaml` 中正确配置了 `sms` 部分
- 如果出现 "No module named 'Tea.core'" 或其他导入错误，请运行：
  ```bash
  pip uninstall alibabacloud-tea Tea -y
  pip install alibabacloud-tea>=0.4.2 alibabacloud-tea-openapi>=0.3.8 alibabacloud-tea-util>=0.3.13 alibabacloud-dysmsapi20170525>=3.0.0
  ```
- 如果安装过程中遇到网络超时，可以尝试使用国内镜像源：
  ```bash
  pip install alibabacloud-tea>=0.4.2 alibabacloud-tea-openapi>=0.3.8 alibabacloud-tea-util>=0.3.13 alibabacloud-dysmsapi20170525>=3.0.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```

## 更新维护

- 定期检查依赖更新
- 关注 wcferry 版本变化
- 备份配置文件和数据

## 安全建议

- 不要将配置文件提交到代码仓库
- 定期更换API密钥
- 监控API使用情况
- 注意微信登录状态 