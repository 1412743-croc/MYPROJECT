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

## 学生聊天

启动应用后访问 <http://127.0.0.1:8000/student.html>。浏览器弹出认证框时使用学生账号：

```text
student / student123
```

学生端当前支持：

- 新建和切换会话。
- 发送消息并获得离线 Mock AI 的支持性回复。
- 将用户和助手消息完整保存到 SQLite。
- 页面刷新后重新加载历史会话与消息。
- 对明显高风险词语返回谨慎的紧急求助提示。

管理员账号不能访问学生页面或调用聊天接口。当前回复由确定性的 Mock AI 生成，不会访问外网，也不代表真实 AI 或医疗诊断。

聊天接口包括：

- `POST /api/chat/sessions`
- `GET /api/chat/sessions`
- `GET /api/chat/sessions/{session_id}/messages`
- `POST /api/chat`

## 当前范围

模块 1–3 已完成。当前聊天使用 Mock AI；真实 AI、正式风险评估和 RAG 将在后续模块中实现。
