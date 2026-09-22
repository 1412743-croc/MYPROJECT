const sessionsElement = document.querySelector("#sessions");
const messagesElement = document.querySelector("#messages");
const statusElement = document.querySelector("#status");
const formElement = document.querySelector("#chat-form");
const inputElement = document.querySelector("#message");
const newSessionButton = document.querySelector("#new-session");

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
    const exchange = await request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: activeSessionId, message }),
    });
    renderMessage(exchange.user_message);
    renderMessage(exchange.assistant_message);
    inputElement.value = "";
    messagesElement.scrollTop = messagesElement.scrollHeight;
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
loadSessions().catch((error) => showStatus(error.message));
