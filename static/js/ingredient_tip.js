const api  = (window.TIP_CONFIG && window.TIP_CONFIG.api)  || "";
const name = (window.TIP_CONFIG && window.TIP_CONFIG.name) || "";

const chat = document.getElementById("chat");
const q = document.getElementById("q");
const send = document.getElementById("send");

function scrollChatToBottom() {
  chat.parentElement.scrollTop = chat.parentElement.scrollHeight;
}

function append(role, text) {
  const el = document.createElement("div");
  el.className = "msg " + role;
  el.textContent = (role === "user" ? "나: " : "도우미: ") + text;
  chat.appendChild(el);
  scrollChatToBottom();
  return el;
}

function setSending(on) {
  send.disabled = !!on;
}

function loadTip() {
  setSending(true);
  const slot = append("assistant", "불러오는 중...");
  fetch(api + "?name=" + encodeURIComponent(name), {
    headers: { "X-Requested-With": "XMLHttpRequest" },
  })
    .then((r) => (r.ok ? r.text() : Promise.reject(r)))
    .then((txt) => {
      slot.textContent = "도우미: " + (txt || "정보를 불러오지 못했어요.");
    })
    .catch(() => {
      slot.textContent = "도우미: 오류가 발생했어요.";
    })
    .finally(() => setSending(false));
}

function ask() {
  const text = q.value.trim();
  if (!text) return;
  append("user", text);
  const slot = append("assistant", "생각 중...");
  q.value = "";
  q.focus();
  setSending(true);

  const url =
    api +
    "?name=" +
    encodeURIComponent(name) +
    "&q=" +
    encodeURIComponent(text);
  fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
    .then((r) => (r.ok ? r.text() : Promise.reject(r)))
    .then((txt) => {
      slot.textContent = "도우미: " + (txt || "답변을 받지 못했어요.");
    })
    .catch(() => {
      slot.textContent = "도우미: 오류가 발생했어요.";
    })
    .finally(() => setSending(false));
}

send.addEventListener("click", ask);
q.addEventListener("keydown", (e) => {
  if (e.key === "Enter") ask();
});

// 첫 메시지 로드
loadTip();
