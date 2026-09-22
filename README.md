# MindBridge

一个从零构建中的校园心理支持 Web 应用。本阶段仅包含 FastAPI 服务、健康检查和静态首页。

## 环境要求

- Python 3.11 或更高版本
- PowerShell（Windows）

## 安装与启动

在 `NEW` 目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

打开以下地址：

- 首页：<http://127.0.0.1:8000>
- 健康检查：<http://127.0.0.1:8000/actuator/health>
- OpenAPI 文档：<http://127.0.0.1:8000/docs>

## 测试

先激活虚拟环境，然后运行：

```powershell
python -m pytest
```

## 当前范围

模块 1 仅提供项目骨架。数据库、认证、聊天、AI 和 RAG 将在后续模块中实现。
