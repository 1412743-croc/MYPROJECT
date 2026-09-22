# MindBridge

一个从零构建中的校园心理支持 Web 应用。当前已包含 FastAPI 服务、静态首页、SQLite 数据库与基础身份认证。

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

## 数据库与登录

应用首次启动时会创建 `data/mindbridge.db`。只有当 `users` 表为空时，才会创建两个本地演示账号：

| 角色 | 用户名 | 密码 |
| --- | --- | --- |
| 学生 | `student` | `student123` |
| 管理员 | `admin` | `admin123` |

认证暂时使用 HTTP Basic：

- `POST /api/auth/login`：验证用户名和密码并返回个人资料。
- `GET /api/profile`：返回当前认证用户的个人资料。

可以在 <http://127.0.0.1:8000/docs> 点击接口的 **Authorize** 按钮输入账号密码，也可以在 PowerShell 中执行：

```powershell
$credential = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("student:student123"))
Invoke-RestMethod `
  -Method Get `
  -Uri http://127.0.0.1:8000/api/profile `
  -Headers @{ Authorization = "Basic $credential" }
```

HTTP Basic 只编码凭据，并不加密传输；当前适合本机开发，正式部署时必须使用 HTTPS。

## 当前范围

模块 1 和模块 2 已完成。聊天、AI 和 RAG 将在后续模块中实现。
