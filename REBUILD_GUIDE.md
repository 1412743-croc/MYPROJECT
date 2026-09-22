# MindBridge 重建实施手册

> 目标：在本 `NEW/` 目录内，从零重建一个可维护、可测试的校园心理支持 Web 应用。
>
> 工作方式：一次只做一个模块；每个模块通过验收并提交 Git 后，才进入下一个模块。本文是后续与 Codex 协作的唯一实施基线。

## 0. 项目边界与原则

### 目标功能

- 学生端：登录、聊天、流式回复、历史会话。
- 管理端：查看风险事件、报告和知识库状态。
- 后端：FastAPI、认证授权、持久化、AI Provider、风险评估、RAG。
- 运维扩展：Redis、异步任务、Excel/邮件、Docker、多 Agent、MCP。

### 不做的事

- 不复制旧项目的源代码、数据库、`.env` 或 API 密钥。
- 不在第一阶段接入真实模型、向量库、多 Agent 或邮件。
- 不将心理支持表述为医疗诊断、治疗或紧急服务的替代品。
- 不把密钥、密码、Token 或真实用户数据提交到 Git。

### 通用完成定义（每个模块都必须满足）

1. 只改动当前模块需要的文件，不顺带重构。
2. 新行为有自动化测试，已有测试仍通过。
3. README 或 `.env.example` 在需要时同步更新。
4. 完成验收后创建一次 Git commit。

### 每次交给 Codex 的通用前缀

```text
请先阅读当前代码和测试，说明将修改哪些文件及原因。
只实现本次需求，不重构无关代码，不删除已有功能。
先写或更新测试，再实现功能。
完成后运行测试，并报告：
1. 修改文件；2. 启动/测试命令；3. 已知限制；4. 下一步建议。
不要读取、打印或提交 .env 中的任何密钥。
```

---

## 模块 1：项目骨架

**目标**：可以启动 FastAPI，并在浏览器打开一个静态首页。

**建议技术栈**：Python 3.11、FastAPI、Uvicorn、SQLAlchemy、Pydantic Settings、pytest、原生 HTML/CSS/JavaScript。

**Codex 任务提示词**：

```text
在当前 NEW 空目录中创建名为 MindBridge 的 Python 项目。
实现最小可运行骨架：
- app/main.py，GET /actuator/health 返回 {"status":"UP"}
- app/static/index.html，显示“MindBridge”
- requirements.txt、.env.example、README.md、.gitignore
- 静态文件挂载在根路径
- 添加健康检查测试
暂不实现数据库、登录、AI、RAG。
```

**验收**：

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload
# 浏览器： http://127.0.0.1:8000
# 接口：   http://127.0.0.1:8000/actuator/health
```

**提交**：`feat: bootstrap FastAPI application`

---

## 模块 2：数据库、认证与角色

**目标**：开发环境使用 SQLite，学生与管理员角色可安全地区分。

**数据模型最小集**：`users(id, username, password_hash, display_name, role, created_at)`。

**Codex 任务提示词**：

```text
在现有项目实现最小认证系统。
- SQLite 数据库路径为 data/mindbridge.db
- users 表字段：id、username、password_hash、display_name、role、created_at
- 提供登录接口和 GET /api/profile
- 使用安全的密码哈希；采用 HTTP Basic Auth 或 Bearer Token，并说明选择原因
- 仅在数据库没有用户时创建演示账号 student/student123 和 admin/admin123
- 增加未认证返回 401、学生/管理员登录成功的 pytest 测试
不要实现聊天、AI 或后台页面。
```

**验收**：未登录访问 profile 为 401；两个演示账号分别返回 student/admin 角色。

**提交**：`feat: add authentication and roles`

---

## 模块 3：学生聊天闭环（Mock AI）

**目标**：学生能收发消息，刷新后仍可看到历史；此阶段不依赖真实模型。

**新增模型最小集**：

- `chat_sessions(id, user_id, title, created_at)`
- `chat_messages(id, session_id, role, content, created_at)`

**Codex 任务提示词**：

```text
实现学生端聊天最小闭环，使用 Mock AI。
- 学生才可访问 student.html，管理员不得发起学生聊天
- 页面包含消息列表、输入框、发送按钮
- 提供创建/读取会话和发送消息的 API
- 用户消息与 Mock AI 回复均保存 SQLite
- Mock 回复使用自然、共情、非诊断的中文；不调用外网
- 刷新页面后可重新加载会话历史
- 为权限、发消息、历史持久化写接口测试
```

**验收**：用 student 登录，发送消息后刷新页面，消息仍存在。

**提交**：`feat: add persistent student chat with mock AI`

---

## 模块 4：可解释风险评估与管理后台

**目标**：以可测试的规则优先保护高风险用户，并只向管理员显示风险信息。

**新增模型最小集**：`risk_cases(id, user_id, message_id, level, reason, status, created_at)`。

**Codex 任务提示词**：

```text
为聊天增加可解释的风险评估和最小管理员后台。
- RiskLevel：LOW、MEDIUM、HIGH
- 实现纯规则 assess_risk(message)，返回等级、命中的规则和原因
- HIGH 仅针对明确自伤/自杀计划、即时危险等强信号；普通压力和低落不能一律误报 HIGH
- 每条用户消息保存风险等级和原因；HIGH 创建 risk_case
- GET /api/admin/cases 与 GET /api/admin/reports 仅 admin 可访问
- 新建极简 admin.html 展示风险案例
- 高风险的聊天回复必须提供立即寻求当地紧急服务、可信赖的人和校园支持的建议，不虚构电话号码
- 为 LOW/MEDIUM/HIGH 和权限边界写测试
- 不发送邮件、不联系任何人
```

**验收**：普通考试压力不误报 HIGH；明确即时危险文本生成 HIGH 案例；学生无法访问管理接口。

**提交**：`feat: add rule-based risk assessment and admin cases`

---

## 模块 5：AI Provider 抽象与真实模型

**目标**：保留可离线开发的 Mock Provider，同时可配置 OpenAI-compatible API 或 Ollama。

**配置项**：`AI_PROVIDER`、`OPENAI_BASE_URL`、`OPENAI_API_KEY`、`OPENAI_MODEL`、`OLLAMA_BASE_URL`、`OLLAMA_MODEL`。

**Codex 任务提示词**：

```text
将 Mock AI 抽象为 AIProvider 接口，保留 MockProvider。
新增 OpenAICompatibleProvider，并可选实现 OllamaProvider。
- 所有配置从 .env 读取，补全 .env.example，但绝不写入真实密钥
- 真实调用失败或 API Key 缺失时回退 MockProvider，并在服务端日志说明原因
- 系统提示词独立管理，要求共情、非诊断、不承诺疗效；高风险优先安全建议
- 网络调用必须设置超时；测试中使用 mock，不能真的访问网络
- 为 provider 选择、回退和请求映射写测试
```

**验收**：未配密钥时仍可聊天；配置合法模型后可收到真实回复；密钥未出现在页面、日志或 Git。

**提交**：`feat: add configurable AI providers`

---

## 模块 6：SSE 流式聊天

**目标**：将完整回复改为前端逐段显示，且消息保存不重复、不丢失。

**Codex 任务提示词**：

```text
实现 POST /api/chat/stream 的 Server-Sent Events 聊天接口。
- 使用 token、done、error 三种事件
- 前端逐段追加 assistant 回复
- 流完整结束后只保存一条完整 assistant 消息
- provider 出错时发送 error，并在页面显示友好提示
- MockProvider 同样模拟分段输出，便于离线测试
- 为事件格式、异常处理、最终消息持久化写测试
```

**验收**：回复逐字/逐段出现；刷新后仅有一条完整助手消息。

**提交**：`feat: add streaming chat via SSE`

---

## 模块 7：知识库与 RAG（先 BM25）

**目标**：让咨询类问题参考本地资料；闲聊不触发检索。

**顺序**：Markdown 文档 → 切块入库 → BM25 → 路由 → 提示词上下文。向量库是后续增强，不是前置条件。

**Codex 任务提示词**：

```text
实现最小 RAG 知识库，第一版只使用本地 BM25/关键词检索，不使用向量库。
- app/knowledge 放置中文 Markdown 心理支持资料
- 管理员能新增 Markdown 知识文本
- 文本按固定长度和重叠切块，保存 source、content、chunk_index
- 仅 CONSULT/RISK 类问题检索；CHAT 闲聊不检索
- 取前 N 个片段拼入 AI 上下文；响应可返回 sources 供前端展示
- 为切块、排序、路由决策、权限写测试
```

**验收**：相关咨询能显示来源；普通闲聊不查询资料；管理员可管理资料。

**提交**：`feat: add BM25 knowledge retrieval`

---

## 模块 8：向量检索增强（可选）

**目标**：加入语义检索，但任何故障均可以降级回 BM25。

**Codex 任务提示词**：

```text
在已有 BM25 RAG 基础上增加可选 Chroma 向量检索和 embedding provider。
- 向量库持久化到 data/chroma
- 使用环境变量控制启用与模型名称
- 向量结果与 BM25 结果加权融合，并保留来源和分数
- embedding 或 Chroma 不可用时自动降级 BM25；只有配置 VECTOR_REQUIRED=true 才返回明确错误
- 写索引、融合、降级行为的测试，外部 embedding 调用必须 mock
```

**验收**：没配 embedding Key 时聊天仍可用；向量可用时检索质量提升且可观察状态。

**提交**：`feat: add optional vector retrieval with BM25 fallback`

---

## 模块 9：生产支撑能力

按以下顺序拆成独立小模块，每项一个 commit：

1. **Redis 短期记忆**：只放最近上下文；SQLite 仍是完整历史的事实来源。
2. **文件导入**：先 `.txt`/`.md`，再 PDF；必须限制大小、校验类型并记录来源。
3. **异步工具队列**：先仅记录任务状态，再写入 Excel；开发环境默认不实际发送邮件。
4. **预警通知**：必须配置显式开关和限流；不在未经确认的环境发送真实通知。
5. **Docker Compose**：应用、MySQL、Redis；所有密钥通过环境变量注入。
6. **可观测性**：结构化日志、健康检查、管理员受控状态接口。

---

## 模块 10：多 Agent 与 MCP（最后实施）

只有模块 1–9 稳定后再开始。先让单一服务中的意图识别、风险评估、检索、生成各自可测试，再拆 Agent。

建议角色：

- `Coordinator`：任务与最终采纳。
- `Understanding`：判定 CHAT / CONSULT / RISK。
- `Safety`：独立风险审查，可覆盖不安全回复。
- `Context`：记忆和 RAG 上下文。
- `Response`：生成候选回复。

MCP 首批只暴露低风险、可审计工具，例如写入本地风险台账。任何邮件、外部通知、数据删除工具都需要单独的权限、审计与人工确认设计。

**提交建议**：`feat: add event-driven agent runtime` 与 `feat: add audited MCP tools` 分开。

---

## 开发节奏与故障处理

### 每个模块的固定流程

```text
阅读本手册对应模块
→ 向 Codex 提交该模块提示词
→ 阅读改动和测试结果
→ 本地手动验收
→ git status 确认无敏感文件
→ git add / git commit
→ 进入下一模块
```

### 出错时给 Codex 的提示词

```text
不要直接重写。请先复现该错误，定位根因，说明最小修复方案；
然后只做该修复，补充一个防回归测试，最后运行相关测试。
```

### 推荐的提交检查

```powershell
git status
git diff --check
.\.venv\Scripts\python -m pytest
git add .
git commit -m "<本模块的提交信息>"
```

## 当前进度

- [x] 模块 1：项目骨架
- [x] 模块 2：数据库、认证与角色
- [x] 模块 3：学生聊天闭环（Mock AI）
- [ ] 模块 4：风险评估与管理后台
- [ ] 模块 5：AI Provider
- [ ] 模块 6：SSE 流式聊天
- [ ] 模块 7：BM25 RAG
- [ ] 模块 8：向量检索（可选）
- [ ] 模块 9：生产支撑能力
- [ ] 模块 10：多 Agent 与 MCP
