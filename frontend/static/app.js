/**
 * Varsh's Personal AI — Frontend JavaScript
 * =====================================
 * Handles all UI interactions, authentication, API communication, and state management.
 * Communicates with the FastAPI backend securely via REST API calls.
 */

// ─────────────────────────────────────────────
// Configuration
// ─────────────────────────────────────────────

const API_BASE = '';          // Empty = same origin as the page
const ENDPOINTS = {
  chat:    `${API_BASE}/api/chat`,
  newChat: `${API_BASE}/api/new-chat`,
  health:  `${API_BASE}/api/health`,
  models:  `${API_BASE}/api/models`,
  login:   `${API_BASE}/api/auth/login`,
  logout:  `${API_BASE}/api/auth/logout`,
  session: `${API_BASE}/api/auth/session`,
};

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────

const state = {
  sessionId:    generateSessionId(),
  isLoading:    false,
  messageCount: 0,
  currentModel: 'gemini-2.5-flash',
  authenticated: false,
};

// ─────────────────────────────────────────────
// DOM References
// ─────────────────────────────────────────────

const dom = {
  appContainer:      document.getElementById('app'),
  loginOverlay:      document.getElementById('login-overlay'),
  loginForm:         document.getElementById('login-form'),
  usernameInput:     document.getElementById('username'),
  passwordInput:     document.getElementById('password'),
  loginError:        document.getElementById('login-error'),
  messagesContainer: document.getElementById('messages-container'),
  welcomeScreen:     document.getElementById('welcome-screen'),
  typingIndicator:   document.getElementById('typing-indicator'),
  messageInput:      document.getElementById('message-input'),
  sendBtn:           document.getElementById('send-btn'),
  newChatBtn:        document.getElementById('new-chat-btn'),
  logoutBtn:         document.getElementById('logout-btn'),
  sessionIdDisplay:  document.getElementById('session-id-display'),
  msgCountDisplay:   document.getElementById('msg-count-display'),
  modelSelect:       document.getElementById('model-select'),
  statusDot:         document.getElementById('status-dot'),
  statusText:        document.getElementById('status-text'),
  toast:             document.getElementById('toast'),
  currentModelLabel: document.getElementById('current-model-label'),
};

// ─────────────────────────────────────────────
// Initialization & Authentication flow
// ─────────────────────────────────────────────

async function init() {
  setupLoginListener();
  await checkSession();
}

async function checkSession() {
  try {
    const res = await fetch(ENDPOINTS.session);
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated) {
        showApp();
      } else {
        showLogin();
      }
    } else {
      showLogin();
    }
  } catch {
    showLogin();
  }
}

function showLogin() {
  state.authenticated = false;
  dom.appContainer.style.display = 'none';
  dom.loginOverlay.classList.add('active');
  dom.usernameInput.focus();
}

async function showApp() {
  state.authenticated = true;
  dom.loginOverlay.classList.remove('active');
  dom.appContainer.style.display = 'flex';
  
  updateSessionDisplay();
  await checkHealth();
  await loadModels();
  setupEventListeners();
  dom.messageInput.focus();
}

// ─────────────────────────────────────────────
// Login & Logout Handlers
// ─────────────────────────────────────────────

function setupLoginListener() {
  if (dom.loginForm) {
    dom.loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      dom.loginError.style.display = 'none';
      const username = dom.usernameInput.value.trim();
      const password = dom.passwordInput.value;

      try {
        const res = await fetch(ENDPOINTS.login, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password }),
        });

        if (res.ok) {
          showToast('🔑 Authentication successful');
          dom.usernameInput.value = '';
          dom.passwordInput.value = '';
          await showApp();
        } else {
          const errData = await res.json().catch(() => ({}));
          dom.loginError.textContent = errData.detail || 'Invalid username or password.';
          dom.loginError.style.display = 'block';
        }
      } catch (err) {
        dom.loginError.textContent = 'Server connection failed.';
        dom.loginError.style.display = 'block';
      }
    });
  }
}

async function handleLogout() {
  try {
    await fetch(ENDPOINTS.logout, { method: 'POST' });
  } catch {}
  showToast('🚪 Logged out successfully');
  showLogin();
}

// ─────────────────────────────────────────────
// Health Check
// ─────────────────────────────────────────────

async function checkHealth() {
  try {
    const res = await fetch(ENDPOINTS.health);
    const data = await res.json();
    if (data.status === 'ok') {
      dom.statusText.textContent = 'Connected';
      dom.statusDot.style.background = 'var(--success)';
      dom.statusDot.style.boxShadow = '0 0 6px var(--success)';
    }
  } catch {
    dom.statusText.textContent = 'Offline';
    dom.statusDot.style.background = 'var(--error)';
    dom.statusDot.style.boxShadow = '0 0 6px var(--error)';
  }
}

// ─────────────────────────────────────────────
// Load Available Models
// ─────────────────────────────────────────────

async function loadModels() {
  try {
    const res = await fetch(ENDPOINTS.models);
    if (res.status === 401) {
      showLogin();
      return;
    }
    const data = await res.json();
    state.currentModel = data.current_model;

    // Populate model dropdown
    dom.modelSelect.innerHTML = '';
    data.available_models.forEach(model => {
      const opt = document.createElement('option');
      opt.value = model.name;
      opt.textContent = model.name;
      opt.selected = model.name === data.current_model;
      opt.title = model.description;
      dom.modelSelect.appendChild(opt);
    });

    if (dom.currentModelLabel) {
      dom.currentModelLabel.textContent = data.current_model;
    }
  } catch {
    // Keep default model if API is unavailable
  }
}

// ─────────────────────────────────────────────
// Event Listeners
// ─────────────────────────────────────────────

function setupEventListeners() {
  // Clear any previous duplicate listeners
  const newMsgInput = dom.messageInput.cloneNode(true);
  dom.messageInput.parentNode.replaceChild(newMsgInput, dom.messageInput);
  dom.messageInput = newMsgInput;

  const newSendBtn = dom.sendBtn.cloneNode(true);
  dom.sendBtn.parentNode.replaceChild(newSendBtn, dom.sendBtn);
  dom.sendBtn = newSendBtn;

  // Send on Enter, newline on Shift+Enter
  dom.messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Auto-resize textarea as user types
  dom.messageInput.addEventListener('input', () => {
    autoResize(dom.messageInput);
  });

  dom.sendBtn.addEventListener('click', sendMessage);
  
  if (dom.newChatBtn) {
    const newChatBtnClone = dom.newChatBtn.cloneNode(true);
    dom.newChatBtn.parentNode.replaceChild(newChatBtnClone, dom.newChatBtn);
    dom.newChatBtn = newChatBtnClone;
    dom.newChatBtn.addEventListener('click', startNewChat);
  }

  if (dom.logoutBtn) {
    const logoutBtnClone = dom.logoutBtn.cloneNode(true);
    dom.logoutBtn.parentNode.replaceChild(logoutBtnClone, dom.logoutBtn);
    dom.logoutBtn = logoutBtnClone;
    dom.logoutBtn.addEventListener('click', handleLogout);
  }

  // Suggestion cards
  document.querySelectorAll('.suggestion-card').forEach(card => {
    const cardClone = card.cloneNode(true);
    card.parentNode.replaceChild(cardClone, card);
    cardClone.addEventListener('click', () => {
      const text = cardClone.querySelector('.suggestion-text').textContent;
      dom.messageInput.value = text;
      autoResize(dom.messageInput);
      dom.messageInput.focus();
      sendMessage();
    });
  });
}

// ─────────────────────────────────────────────
// Send Message
// ─────────────────────────────────────────────

async function sendMessage() {
  const message = dom.messageInput.value.trim();
  if (!message || state.isLoading) return;

  // Hide welcome screen on first message
  if (dom.welcomeScreen) {
    dom.welcomeScreen.style.animation = 'fadeInUp 0.3s ease reverse forwards';
    setTimeout(() => {
      if (dom.welcomeScreen) dom.welcomeScreen.remove();
    }, 300);
  }

  // Clear input and reset height
  dom.messageInput.value = '';
  autoResize(dom.messageInput);

  // Show user bubble
  appendUserMessage(message);

  // Show loading state
  setLoading(true);

  try {
    const requestBody = {
      message,
      session_id: state.sessionId,
    };

    const res = await fetch(ENDPOINTS.chat, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });

    if (res.status === 401) {
      showLogin();
      return;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();

    // Update state
    state.messageCount = data.message_count;
    updateSessionDisplay();

    // Show AI reply
    appendAIMessage(data.reply, formatTime(new Date(data.timestamp)));

  } catch (err) {
    appendErrorMessage(`Error: ${err.message}`);
    console.error('Chat error:', err);
  } finally {
    setLoading(false);
    scrollToBottom();
    dom.messageInput.focus();
  }
}

// ─────────────────────────────────────────────
// Start New Chat
// ─────────────────────────────────────────────

async function startNewChat() {
  try {
    const res = await fetch(ENDPOINTS.newChat, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: state.sessionId }),
    });
    if (res.status === 401) {
      showLogin();
      return;
    }
  } catch { /* Ignore network errors on reset */ }

  // Generate a new session
  state.sessionId = generateSessionId();
  state.messageCount = 0;

  // Clear messages UI
  dom.messagesContainer.innerHTML = '';
  dom.messagesContainer.appendChild(createWelcomeScreen());

  updateSessionDisplay();
  showToast('✨ New conversation started');
  dom.messageInput.focus();
}

// ─────────────────────────────────────────────
// UI Builders
// ─────────────────────────────────────────────

function appendUserMessage(text) {
  const group = document.createElement('div');
  group.className = 'message-group user-group';

  group.innerHTML = `
    <div class="message-row">
      <div class="avatar user-avatar">👤</div>
      <div class="message-bubble user-bubble">
        <div class="message-text">${escapeHtml(text)}</div>
      </div>
    </div>
    <div class="message-meta">${formatTime(new Date())}</div>
  `;

  dom.messagesContainer.appendChild(group);
  scrollToBottom();
}

function appendAIMessage(text, timestamp) {
  const group = document.createElement('div');
  group.className = 'message-group ai-group';

  const formattedText = formatMarkdown(text);

  group.innerHTML = `
    <div class="message-row">
      <div class="avatar ai-avatar">✨</div>
      <div class="message-bubble ai-bubble">
        <button class="copy-btn" title="Copy response" onclick="copyText(this, ${JSON.stringify(text)})">⧉</button>
        <div class="message-text">${formattedText}</div>
      </div>
    </div>
    <div class="message-meta">${timestamp || formatTime(new Date())} · Assistant</div>
  `;

  dom.messagesContainer.appendChild(group);
}

function appendErrorMessage(text) {
  const div = document.createElement('div');
  div.className = 'error-message';
  div.innerHTML = `<span>⚠️</span> <span>${escapeHtml(text)}</span>`;
  dom.messagesContainer.appendChild(div);
}

function createWelcomeScreen() {
  const div = document.createElement('div');
  div.id = 'welcome-screen';
  div.innerHTML = `
    <div class="welcome-orb">✨</div>
    <div class="welcome-text">
      <h2>Hello! I'm Varsh's Personal AI</h2>
      <p>Your private, secure assistant. Ask me anything — I'm here to help you think, create, and explore.</p>
    </div>
    <div class="welcome-suggestions">
      <button class="suggestion-card">
        <span class="suggestion-icon">💡</span>
        <span class="suggestion-text">Explain quantum computing in simple terms</span>
      </button>
      <button class="suggestion-card">
        <span class="suggestion-icon">🐍</span>
        <span class="suggestion-text">Write a Python function to sort a list of dicts</span>
      </button>
      <button class="suggestion-card">
        <span class="suggestion-icon">✍️</span>
        <span class="suggestion-text">Help me write a professional email</span>
      </button>
      <button class="suggestion-card">
        <span class="suggestion-icon">🎨</span>
        <span class="suggestion-text">Give me creative ideas for a mobile app</span>
      </button>
    </div>
  `;

  // Attach suggestion listeners
  div.querySelectorAll('.suggestion-card').forEach(card => {
    card.addEventListener('click', () => {
      const text = card.querySelector('.suggestion-text').textContent;
      dom.messageInput.value = text;
      autoResize(dom.messageInput);
      dom.messageInput.focus();
      sendMessage();
    });
  });

  return div;
}

// ─────────────────────────────────────────────
// Loading State
// ─────────────────────────────────────────────

function setLoading(isLoading) {
  state.isLoading = isLoading;
  dom.sendBtn.disabled = isLoading;
  dom.messageInput.disabled = isLoading;

  if (isLoading) {
    dom.typingIndicator.classList.add('visible');
    scrollToBottom();
  } else {
    dom.typingIndicator.classList.remove('visible');
  }
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function autoResize(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

function scrollToBottom() {
  setTimeout(() => {
    dom.messagesContainer.scrollTo({
      top: dom.messagesContainer.scrollHeight,
      behavior: 'smooth',
    });
  }, 50);
}

function updateSessionDisplay() {
  if (dom.sessionIdDisplay) {
    dom.sessionIdDisplay.textContent = state.sessionId.substring(0, 14) + '...';
    dom.sessionIdDisplay.title = state.sessionId;
  }
  if (dom.msgCountDisplay) {
    dom.msgCountDisplay.textContent = state.messageCount;
  }
}

function generateSessionId() {
  return 'sess-' + Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 8);
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}

/**
 * Basic markdown formatter for AI responses.
 * Handles: code blocks, inline code, bold, italic, lists, headers.
 */
function formatMarkdown(text) {
  // Escape HTML first
  let result = escapeHtml(text);

  // Code blocks (``` ```)
  result = result.replace(/```(\w+)?\n?([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code
  result = result.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold (**text**)
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // Italic (*text*)
  result = result.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

  // Headings (### ## #)
  result = result.replace(/^### (.+)$/gm, '<strong>$1</strong>');
  result = result.replace(/^## (.+)$/gm, '<strong style="font-size:1.05em">$1</strong>');
  result = result.replace(/^# (.+)$/gm, '<strong style="font-size:1.1em">$1</strong>');

  // Unordered lists
  result = result.replace(/^[•\-\*] (.+)$/gm, '&nbsp;• $1');

  // Numbered lists
  result = result.replace(/^\d+\. (.+)$/gm, (match) => match);

  // Newlines to <br> (but not inside pre blocks)
  // Split by pre blocks, only add <br> outside them
  const parts = result.split(/(<pre>[\s\S]*?<\/pre>)/g);
  result = parts.map((part, i) => {
    if (i % 2 === 1) return part; // Inside <pre>, don't change
    return part.replace(/\n/g, '<br>');
  }).join('');

  return result;
}

function copyText(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '✓';
    btn.style.color = 'var(--success)';
    setTimeout(() => {
      btn.textContent = '⧉';
      btn.style.color = '';
    }, 1500);
  });
}

function showToast(message) {
  dom.toast.textContent = message;
  dom.toast.classList.add('show');
  setTimeout(() => {
    dom.toast.classList.remove('show');
  }, 2500);
}

// ─────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
