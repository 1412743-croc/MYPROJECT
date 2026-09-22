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

## 风险评估与管理后台

每条新的学生消息都会经过本地、可解释的规则评估，并保存等级、命中的规则和原因：

| 等级 | 当前含义 |
| --- | --- |
| `LOW` | 未发现明确的中高风险规则信号 |
| `MEDIUM` | 出现明显压力、焦虑、失眠或含义不明确的消极表达 |
| `HIGH` | 出现明确自伤/自杀意图、计划或即时危险信号 |

普通考试压力不会被标记为 `HIGH`。只有 `HIGH` 消息会创建待处理的风险案例，同时学生会收到立即联系当地紧急服务、可信赖的人和校园支持的提示。系统不会虚构电话号码，也不会自动发邮件或联系任何人。

管理员可在独立浏览器窗口或无痕窗口访问 <http://127.0.0.1:8000/admin.html>，使用：

```text
admin / admin123
```

管理端接口：

- `GET /api/admin/cases`：查看高风险案例。
- `GET /api/admin/reports`：查看全部规则评估记录。

学生不能访问管理页面或管理接口。当前规则评估只是保守的第一层筛查，不能代替专业人员判断。

## AI Provider

默认使用 `MockProvider`，不访问网络、不消耗 Token，也不会产生模型费用。学生页面顶部和 `GET /api/ai/status` 会显示当前有效 Provider，但不会返回 API Key。

如需启用 OpenAI-compatible Chat Completions，请在本地新建 `.env`（该文件已被 Git 忽略）：

```env
AI_PROVIDER=openai
AI_TIMEOUT_SECONDS=30
AI_TEMPERATURE=0.4
AI_HISTORY_LIMIT=10
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=你的_API_Key
OPENAI_MODEL=你要使用的模型名称
```

也可以连接本机 Ollama：

```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=你已经安装的本地模型名称
```

修改 `.env` 后需要重启应用。以下情况会自动回退到 Mock Provider：

- Provider 名称未知。
- OpenAI API Key 或模型名称缺失。
- Ollama 模型名称缺失。
- 网络超时、连接失败、HTTP 错误或返回结构异常。

模型系统提示词单独保存在 `app/services/prompts.py`，要求共情、非诊断、不承诺疗效；HIGH 风险时优先当地紧急服务、可信赖的人和校园支持建议。服务端不会记录 API Key。

## SSE 流式聊天

学生页面通过 `POST /api/chat/stream` 接收 Server-Sent Events，不再等待完整回复后一次性显示。事件类型：

| 事件 | 内容 |
| --- | --- |
| `token` | 一段新增回复文本 |
| `done` | 完整回复结束，并返回已保存消息的 ID |
| `error` | 不包含内部异常的友好错误提示 |

用户消息和风险评估会先保存。只有 Provider 完整结束后，系统才会把拼接后的文本保存为一条助手消息；流式失败时不会保存半截助手回复。Mock Provider 会按小段输出，OpenAI-compatible Provider 解析 SSE，Ollama Provider 解析流式 NDJSON。

原来的 `POST /api/chat` 非流式接口暂时保留，便于兼容和测试。

## 当前范围

模块 1–6 已完成。聊天支持 Mock、OpenAI-compatible API、Ollama 和 SSE 流式输出；RAG 将在后续模块中实现。
