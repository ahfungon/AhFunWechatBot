# AhFun微信机器人

这是一个基于 wcferry 的微信机器人项目，集成了多种AI对话能力和实用功能。

## 功能特性

- 多模型AI对话支持
  - OpenAI
  - SparkDesk
  - Google PaLM
  - 智谱AI
- OCR图像识别
  - 支持百度OCR
  - 支持本地Tesseract
- 短信通知（阿里云）
- 日程提醒
- 农历/节假日查询

## 依赖要求

详细的依赖要求请查看项目根目录下的 `requirements.txt`。

主要依赖：
- wcferry v39.4.2.2
- openai >1.0.0
- sparkdesk-api v1.3.0

## 相关文档

- [API文档](./API_DOCUMENT.md)
- [前端工作流程](./FRONTEND_WORKFLOW.md)
- [OCR使用说明](./OCR使用说明.md)

## 部署说明

请参考 [部署文档](./DEPLOYMENT.md) 进行项目部署。 