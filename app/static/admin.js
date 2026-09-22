const casesElement = document.querySelector("#cases");
const reportsElement = document.querySelector("#reports");
const caseCountElement = document.querySelector("#case-count");
const reportCountElement = document.querySelector("#report-count");
const statusElement = document.querySelector("#status");
const refreshButton = document.querySelector("#refresh");

async function request(path) {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `请求失败（${response.status}）`);
  }
  return response.json();
}

function addText(parent, tagName, text, className = "") {
  const element = document.createElement(tagName);
  element.textContent = text;
  if (className) element.className = className;
  parent.append(element);
  return element;
}

function formatTime(value) {
  return new Date(value).toLocaleString("zh-CN");
}

function renderCases(cases) {
  casesElement.replaceChildren();
  caseCountElement.textContent = String(cases.length);
  if (cases.length === 0) {
    addText(casesElement, "p", "当前没有高风险案例。", "empty");
    return;
  }
  cases.forEach((item) => {
    const card = document.createElement("article");
    card.className = "case-card";
    addText(card, "span", item.level.toUpperCase(), `badge ${item.level}`);
    addText(card, "h3", `${item.username} · 会话 ${item.session_id}`);
    addText(card, "p", item.content, "message");
    addText(card, "p", item.reason, "reason");
    addText(card, "time", formatTime(item.created_at));
    casesElement.append(card);
  });
}

function renderReports(reports) {
  reportsElement.replaceChildren();
  reportCountElement.textContent = String(reports.length);
  reports.forEach((item) => {
    const row = document.createElement("tr");
    addText(row, "td", formatTime(item.created_at));
    addText(row, "td", item.username);
    addText(row, "td", item.level.toUpperCase(), `level ${item.level}`);
    addText(row, "td", item.content);
    addText(row, "td", item.reason);
    reportsElement.append(row);
  });
}

async function loadDashboard() {
  refreshButton.disabled = true;
  statusElement.textContent = "正在加载……";
  try {
    const [cases, reports] = await Promise.all([
      request("/api/admin/cases"),
      request("/api/admin/reports"),
    ]);
    renderCases(cases);
    renderReports(reports);
    statusElement.textContent = "";
  } catch (error) {
    statusElement.textContent = error.message;
  } finally {
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", loadDashboard);
loadDashboard();
