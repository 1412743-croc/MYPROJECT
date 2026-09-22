const sessionsElement = document.querySelector("#sessions");
const messagesElement = document.querySelector("#messages");
const statusElement = document.querySelector("#status");
const formElement = document.querySelector("#chat-form");
const inputElement = document.querySelector("#message");
const newSessionButton = document.querySelector("#new-session");
const providerElement = document.querySelector("#ai-provider");

let activeSessionId = null;

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `请求失败（${response.status}）`);
  }
  return response.json();
}

function showStatus(message = "") {
  statusElement.textContent = message;
}

function renderMessage(message) {
  const item = document.createElement("article");
  item.className = `message ${message.role}`;

  const label = document.createElement("strong");
  label.textContent = message.role === "user" ? "我" : "MindBridge";
  const content = document.createElement("p");
  content.textContent = message.content;

  item.append(label, content);
  messagesElement.append(item);
  return { item, content };
}

function parseSseBlock(block) {
  let eventName = "message";
  const dataLines = [];
  block.replaceAll("\r", "").split("\n").forEach((line) => {
    if (line.startsWith("event:")) eventName = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
  });
  if (dataLines.length === 0) return null;
  return { event: eventName, data: JSON.parse(dataLines.join("\n")) };
}

async function streamChat(sessionId, message) {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `请求失败（${response.status}）`);
  }
  if (!response.body) throw new Error("浏览器不支持流式响应");

  renderMessage({ role: "user", content: message });
  const assistant = renderMessage({ role: "assistant", content: "" });
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed = false;

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const parsed = parseSseBlock(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        if (parsed?.event === "token") {
          assistant.content.textContent += parsed.data.content;
          messagesElement.scrollTop = messagesElement.scrollHeight;
          await new Promise((resolve) => requestAnimationFrame(resolve));
        } else if (parsed?.event === "done") {
          completed = true;
        } else if (parsed?.event === "error") {
          throw new Error(parsed.data.message || "回复生成失败，请稍后重试。");
        }
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
    if (!completed) throw new Error("回复流意外中断，请稍后重试。");
  } catch (error) {
    assistant.item.remove();
    throw error;
  }
}

async function loadMessages(sessionId) {
  activeSessionId = sessionId;
  messagesElement.replaceChildren();
  const messages = await request(`/api/chat/sessions/${sessionId}/messages`);
  messages.forEach(renderMessage);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function renderSessions(sessions) {
  sessionsElement.replaceChildren();
  sessions.forEach((session) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = session.title;
    button.className = session.id === activeSessionId ? "active" : "";
    button.addEventListener("click", async () => {
      await loadMessages(session.id);
      await loadSessions();
    });
    sessionsElement.append(button);
  });
}

async function createSession() {
  const session = await request("/api/chat/sessions", {
    method: "POST",
    body: JSON.stringify({ title: "新对话" }),
  });
  activeSessionId = session.id;
  messagesElement.replaceChildren();
  await loadSessions();
}

async function loadSessions() {
  const sessions = await request("/api/chat/sessions");
  if (sessions.length === 0) {
    await createSession();
    return;
  }
  if (!activeSessionId) {
    activeSessionId = sessions[0].id;
    await loadMessages(activeSessionId);
  }
  renderSessions(sessions);
}

formElement.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = inputElement.value.trim();
  if (!message || !activeSessionId) return;

  inputElement.disabled = true;
  showStatus("正在回复……");
  try {
    inputElement.value = "";
    await streamChat(activeSessionId, message);
    await loadSessions();
    showStatus();
  } catch (error) {
    showStatus(error.message);
  } finally {
    inputElement.disabled = false;
    inputElement.focus();
  }
});

newSessionButton.addEventListener("click", () => createSession().catch((error) => showStatus(error.message)));
request("/api/ai/status")
  .then((status) => {
    const model = status.effective_provider === "mock" ? "Mock AI" : status.model;
    providerElement.textContent = `当前回复：${status.effective_provider} · ${model}`;
  })
  .catch(() => {
    providerElement.textContent = "当前回复：状态不可用";
  });
loadSessions().catch((error) => showStatus(error.message));
