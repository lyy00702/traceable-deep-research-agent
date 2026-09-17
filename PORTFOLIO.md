# 可溯源 Deep Research Agent 二次开发

基于开源 GPT Researcher 的二次开发与评测版本，重点补充中文搜索适配、来源去重、来源质量评分、RAG 离线回退、阶段 Trace 和固定评测流程。

## 我的主要改动

- 接入 DeepSeek 等 OpenAI 兼容模型，用于研究规划、检索决策和报告生成
- 新增 360 与必应中国检索器，降低 DuckDuckGo、Google 和公共 SearX 超时导致的零来源问题
- 实现 URL 规范化去重，移除追踪参数并保留稳定来源
- 实现可解释来源评分：域名可信度、内容完整度和时效性
- 增加 SDK 运行器、JSONL 阶段 Trace、固定评测集和 p50/p95 统计
- 在受限网络中提供 `local-hash-768` Embedding 回退，恢复 RAG 上下文压缩链路
- 补充实验模块单元测试

## 上游项目

本项目基于并保留以下开源项目：

- https://github.com/assafelovic/gpt-researcher

上游原有的规划、检索、抓取、报告生成和 WebSocket 能力应归功于原项目及其贡献者；本仓库中的新增代码用于本地实验、工程化评测和中文搜索适配。

## 快速开始

1. 创建独立虚拟环境
2. 安装 `requirements.txt`
3. 复制 `.env.example` 为 `.env` 并填写自己的模型与搜索配置
4. 运行 `scripts/run_research_sdk.py` 执行单次任务
5. 运行 `scripts/run_evaluation.py` 执行固定评测

公开仓库不包含 API Key、运行输出、Trace 原文和本地实验日志。
