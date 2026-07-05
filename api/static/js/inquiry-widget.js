(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────────────────────
  var state = {
    sessionId: null,
    open: false,
    loading: false,
    readyToSubmit: false,
    extracted: null,
    submitted: false,
  };

  // ── Security ───────────────────────────────────────────────────────────────
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function safeText(str) {
    return escapeHtml(str).replace(/\n/g, '<br>');
  }

  // ── DOM helpers ────────────────────────────────────────────────────────────
  function el(id) { return document.getElementById(id); }

  function scrollToBottom() {
    var msgs = el('iq-messages');
    if (msgs) msgs.scrollTop = msgs.scrollHeight;
  }

  function setInputDisabled(disabled) {
    var input = el('iq-input');
    var send  = el('iq-send-btn');
    if (input) input.disabled = disabled;
    if (send)  send.disabled  = disabled;
  }

  // ── Widget HTML ────────────────────────────────────────────────────────────
  function buildWidget() {
    var wrapper = document.createElement('div');
    wrapper.innerHTML = [
      // Floating trigger button
      '<button class="iq-trigger" id="iq-trigger" aria-label="Open inquiry chat" aria-expanded="false" aria-controls="iq-panel">',
      '  <span class="iq-trigger-dot" aria-hidden="true"></span>',
      '  <span>get in touch</span>',
      '</button>',

      // Chat panel
      '<div class="iq-panel" id="iq-panel" role="dialog" aria-modal="true" aria-label="Inquiry chat" hidden>',

      '  <div class="iq-header">',
      '    <span class="iq-header-title">reach out</span>',
      '    <button class="iq-close-btn" id="iq-close-btn" aria-label="Close chat">',
      '      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">',
      '        <line x1="3" y1="3" x2="13" y2="13"/><line x1="13" y1="3" x2="3" y2="13"/>',
      '      </svg>',
      '    </button>',
      '  </div>',

      '  <div class="iq-disclosure" id="iq-disclosure">',
      '    You\'re chatting with an AI assistant. Adrian will review your inquiry personally.',
      '    <br>Your responses will be stored and sent to Adrian with your consent.',
      '  </div>',

      '  <div class="iq-messages" id="iq-messages" aria-live="polite" aria-label="Chat messages"></div>',

      '  <div class="iq-submit-section" id="iq-submit-section" hidden>',
      '    <label class="iq-consent-label">',
      '      <input type="checkbox" id="iq-consent">',
      '      I agree to my responses being stored and shared with Adrian Hensler for the purpose of this inquiry.',
      '    </label>',
      '    <button class="iq-submit-btn" id="iq-submit-btn" disabled>send to adrian</button>',
      '  </div>',

      '  <div class="iq-input-row" id="iq-input-row">',
      '    <textarea class="iq-input" id="iq-input" placeholder="Type a message…" rows="1" aria-label="Your message" maxlength="2000"></textarea>',
      '    <button class="iq-send-btn" id="iq-send-btn" aria-label="Send message">',
      '      <svg class="iq-send-icon" viewBox="0 0 24 24">',
      '        <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
      '      </svg>',
      '    </button>',
      '  </div>',

      '</div>',
    ].join('');

    document.body.appendChild(wrapper.firstChild);
    document.body.appendChild(wrapper.firstChild);
  }

  // ── Open / close ───────────────────────────────────────────────────────────
  function openPanel() {
    if (state.open) return;
    state.open = true;

    var panel   = el('iq-panel');
    var trigger = el('iq-trigger');

    panel.removeAttribute('hidden');
    panel.classList.add('iq-entering');
    panel.addEventListener('animationend', function handler() {
      panel.classList.remove('iq-entering');
      panel.removeEventListener('animationend', handler);
    });

    trigger.setAttribute('aria-expanded', 'true');

    // Show welcome message on first open
    if (!el('iq-messages').hasChildNodes()) {
      appendMessage('ai', 'Hi! I\'m here to help connect you with Adrian. Tell me a bit about what you have in mind — what kind of photography project are you thinking?');
    }

    el('iq-input').focus();
  }

  function closePanel() {
    if (!state.open) return;
    state.open = false;

    var panel   = el('iq-panel');
    var trigger = el('iq-trigger');

    panel.classList.add('iq-leaving');
    panel.addEventListener('animationend', function handler() {
      panel.classList.remove('iq-leaving');
      panel.setAttribute('hidden', '');
      panel.removeEventListener('animationend', handler);
    });

    trigger.setAttribute('aria-expanded', 'false');
    trigger.focus();
  }

  // ── Messages ───────────────────────────────────────────────────────────────
  function appendMessage(role, text) {
    var msgs = el('iq-messages');
    var div  = document.createElement('div');
    div.className = role === 'user' ? 'iq-msg iq-msg-user' : 'iq-msg iq-msg-ai';
    div.innerHTML = safeText(text);
    msgs.appendChild(div);
    scrollToBottom();
    return div;
  }

  function showTyping() {
    var msgs = el('iq-messages');
    var div  = document.createElement('div');
    div.className = 'iq-typing';
    div.id = 'iq-typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    msgs.appendChild(div);
    scrollToBottom();
  }

  function removeTyping() {
    var t = el('iq-typing');
    if (t) t.remove();
  }

  // ── Session ────────────────────────────────────────────────────────────────
  async function ensureSession() {
    if (state.sessionId) return;
    var res = await fetch('/api/inquiries/session', { method: 'POST' });
    if (!res.ok) throw new Error('Could not start session');
    var data = await res.json();
    state.sessionId = data.session_id;
  }

  // ── Send message ───────────────────────────────────────────────────────────
  async function sendMessage() {
    var input = el('iq-input');
    var text  = input.value.trim();
    if (!text || state.loading || state.submitted) return;

    state.loading = true;
    setInputDisabled(true);
    input.value = '';
    input.style.height = 'auto';

    appendMessage('user', text);
    showTyping();

    try {
      await ensureSession();

      var res = await fetch('/api/inquiries/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: state.sessionId, message: text }),
      });

      removeTyping();

      if (!res.ok) {
        var err = await res.json().catch(function () { return {}; });
        var msg = (err.detail) || 'Something went wrong. Please try again.';
        appendMessage('ai', msg);
        return;
      }

      var data = await res.json();
      appendMessage('ai', data.reply);

      if (data.ready_to_submit && !state.readyToSubmit) {
        state.readyToSubmit = true;
        state.extracted     = data.extracted;
        showSubmitSection();
      }

    } catch (e) {
      removeTyping();
      appendMessage('ai', 'There was a connection issue. Please try again.');
    } finally {
      state.loading = false;
      if (!state.readyToSubmit) {
        setInputDisabled(false);
        input.focus();
      } else {
        // Lock the input once ready — submit section takes over
        el('iq-input-row').setAttribute('hidden', '');
      }
    }
  }

  // ── Submit section ─────────────────────────────────────────────────────────
  function showSubmitSection() {
    var section = el('iq-submit-section');
    section.removeAttribute('hidden');
    scrollToBottom();
  }

  async function submitInquiry() {
    if (state.submitted || state.loading) return;

    var consent = el('iq-consent').checked;
    if (!consent) return;

    state.loading = true;
    var btn = el('iq-submit-btn');
    btn.disabled = true;
    btn.textContent = 'sending…';

    try {
      var res = await fetch('/api/inquiries/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: state.sessionId, consent: true }),
      });

      if (!res.ok) {
        var err = await res.json().catch(function () { return {}; });
        btn.disabled = false;
        btn.textContent = 'send to adrian';
        appendMessage('ai', (err.detail) || 'Could not submit — please try again.');
        return;
      }

      state.submitted = true;
      showSuccess();

    } catch (e) {
      btn.disabled = false;
      btn.textContent = 'send to adrian';
      appendMessage('ai', 'There was a connection issue. Please try again.');
    } finally {
      state.loading = false;
    }
  }

  function showSuccess() {
    var panel = el('iq-panel');

    // Replace panel contents with success state
    var header = panel.querySelector('.iq-header');
    var disclosure = el('iq-disclosure');
    var messages = el('iq-messages');
    var submitSection = el('iq-submit-section');
    var inputRow = el('iq-input-row');

    if (header) header.style.display = 'none';
    if (disclosure) disclosure.style.display = 'none';
    if (messages) messages.style.display = 'none';
    if (submitSection) submitSection.style.display = 'none';
    if (inputRow) inputRow.style.display = 'none';

    var success = document.createElement('div');
    success.className = 'iq-success';
    success.innerHTML = [
      '<div class="iq-success-icon" aria-hidden="true">✦</div>',
      '<div class="iq-success-title">inquiry sent</div>',
      '<p class="iq-success-body">',
      'Adrian will review your project details and be in touch soon.',
      '<br><br>Thank you for reaching out.',
      '</p>',
    ].join('');
    panel.appendChild(success);
  }

  // ── Event wiring ───────────────────────────────────────────────────────────
  function wire() {
    el('iq-trigger').addEventListener('click', openPanel);
    el('iq-close-btn').addEventListener('click', closePanel);

    // Send on button click
    el('iq-send-btn').addEventListener('click', sendMessage);

    // Send on Enter (Shift+Enter = newline)
    el('iq-input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // Auto-grow textarea
    el('iq-input').addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 80) + 'px';
    });

    // Consent checkbox enables submit
    el('iq-consent').addEventListener('change', function () {
      el('iq-submit-btn').disabled = !this.checked;
    });

    el('iq-submit-btn').addEventListener('click', submitInquiry);

    // Close on Escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && state.open) closePanel();
    });
  }

  // ── Init ───────────────────────────────────────────────────────────────────
  function init() {
    buildWidget();
    wire();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
