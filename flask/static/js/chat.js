const messagesEl = document.getElementById("chat-messages");
const typingEl = document.getElementById("typing-indicator");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const sendBtn = formEl.querySelector("button[type='submit']");

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setTyping(isTyping) {
  typingEl.classList.toggle("hidden", !isTyping);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.reply || "Ошибка запроса");
  }
  return data;
}

async function initChat() {
  try {
    const data = await postJson("/api/chat/start");
    addMessage(data.reply, "bot");
  } catch (error) {
    addMessage("Не удалось запустить чат. Попробуйте обновить страницу.", "bot");
  }
}

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;

  addMessage(text, "user");
  inputEl.value = "";
  inputEl.focus();
  sendBtn.disabled = true;
  setTyping(true);

  try {
    await new Promise((resolve) => setTimeout(resolve, 420));
    const data = await postJson("/api/chat/message", { message: text });
    addMessage(data.reply, "bot");
  } catch (error) {
    addMessage(error.message || "Ошибка. Попробуйте еще раз.", "bot");
  } finally {
    setTyping(false);
    sendBtn.disabled = false;
  }
});

initChat();
