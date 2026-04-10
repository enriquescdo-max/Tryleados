/**
 * LeadOS Support Chat Widget
 * Drop <script src="leadOS-chat-widget.js"></script> before </body> on any page.
 * Connects to POST /chat/message on the Railway backend.
 */
(function () {
  'use strict';

  const API = (window.LeadOSConfig && window.LeadOSConfig.API_BASE_URL)
    || 'https://tryleados-production.up.railway.app';

  // ── Inject CSS ────────────────────────────────────────────────────────
  const css = `
  #los-chat-fab {
    position:fixed;bottom:24px;right:24px;z-index:9999;
    width:52px;height:52px;border-radius:50%;background:#00ff88;
    border:none;cursor:pointer;box-shadow:0 4px 20px rgba(0,255,136,.35);
    display:flex;align-items:center;justify-content:center;
    font-size:22px;transition:transform .2s,box-shadow .2s;
  }
  #los-chat-fab:hover{transform:scale(1.08);box-shadow:0 6px 28px rgba(0,255,136,.45)}
  #los-chat-fab .los-badge{
    position:absolute;top:-2px;right:-2px;width:16px;height:16px;
    border-radius:50%;background:#ff4d4d;border:2px solid #050810;
    font-size:8px;color:#fff;font-family:monospace;font-weight:700;
    display:flex;align-items:center;justify-content:center;display:none;
  }
  #los-chat-box {
    position:fixed;bottom:88px;right:24px;z-index:9998;
    width:340px;max-width:calc(100vw - 32px);
    background:#0c1120;border:1px solid rgba(255,255,255,.1);
    border-radius:16px;overflow:hidden;
    box-shadow:0 24px 64px rgba(0,0,0,.6);
    display:none;flex-direction:column;
    font-family:'DM Mono',monospace,sans-serif;
  }
  #los-chat-box.open{display:flex}
  .los-chat-header {
    padding:14px 16px;background:#111827;border-bottom:1px solid rgba(255,255,255,.07);
    display:flex;align-items:center;gap:10px;
  }
  .los-chat-avatar{
    width:32px;height:32px;background:#00ff88;border-radius:8px;
    display:flex;align-items:center;justify-content:center;
    font-family:'Syne',sans-serif;font-size:13px;font-weight:900;color:#000;flex-shrink:0;
  }
  .los-chat-name{font-size:11px;font-weight:700;color:#f0f4ff}
  .los-chat-status{font-size:9px;color:#00ff88;display:flex;align-items:center;gap:4px}
  .los-chat-status::before{content:'';width:6px;height:6px;border-radius:50%;background:#00ff88;display:inline-block}
  .los-chat-close{margin-left:auto;background:none;border:none;color:#5a7099;cursor:pointer;font-size:16px;padding:0 4px;line-height:1}
  .los-chat-close:hover{color:#f0f4ff}
  .los-messages{
    flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;
    min-height:240px;max-height:320px;
  }
  .los-msg{max-width:85%;line-height:1.5}
  .los-msg .los-bubble{
    padding:9px 12px;border-radius:12px;font-size:11px;word-break:break-word;
  }
  .los-msg.bot .los-bubble{background:#111827;color:#f0f4ff;border-radius:12px 12px 12px 2px}
  .los-msg.user .los-bubble{background:rgba(0,255,136,.12);color:#f0f4ff;border-radius:12px 12px 2px 12px;margin-left:auto}
  .los-msg.bot{align-self:flex-start}
  .los-msg.user{align-self:flex-end}
  .los-msg .los-ts{font-size:8px;color:#5a7099;margin-top:3px;text-align:right}
  .los-msg.bot .los-ts{text-align:left}
  .los-typing .los-bubble{display:flex;gap:4px;align-items:center;padding:11px 14px}
  .los-dot{width:5px;height:5px;border-radius:50%;background:#5a7099;animation:losDot 1.2s infinite}
  .los-dot:nth-child(2){animation-delay:.2s}
  .los-dot:nth-child(3){animation-delay:.4s}
  @keyframes losDot{0%,80%,100%{transform:scale(.8);opacity:.4}40%{transform:scale(1);opacity:1}}
  .los-chat-input-row{
    padding:12px 14px;border-top:1px solid rgba(255,255,255,.07);
    display:flex;gap:8px;align-items:flex-end;
  }
  .los-input{
    flex:1;background:#111827;border:1px solid rgba(255,255,255,.1);border-radius:8px;
    padding:9px 12px;font-family:'DM Mono',monospace;font-size:11px;color:#f0f4ff;
    outline:none;resize:none;line-height:1.5;max-height:80px;
    transition:border-color .2s;
  }
  .los-input:focus{border-color:rgba(0,255,136,.4)}
  .los-input::placeholder{color:#5a7099}
  .los-send{
    width:34px;height:34px;border-radius:8px;background:#00ff88;border:none;
    cursor:pointer;display:flex;align-items:center;justify-content:center;
    flex-shrink:0;transition:background .2s;font-size:14px;
  }
  .los-send:hover{background:#00e87a}
  .los-send:disabled{opacity:.4;pointer-events:none}
  .los-suggested{
    padding:0 14px 10px;display:flex;flex-wrap:wrap;gap:6px;
  }
  .los-chip{
    background:rgba(0,255,136,.07);border:1px solid rgba(0,255,136,.2);
    border-radius:20px;padding:5px 10px;font-size:9px;color:#00ff88;
    cursor:pointer;transition:background .15s;white-space:nowrap;
    font-family:'DM Mono',monospace;
  }
  .los-chip:hover{background:rgba(0,255,136,.14)}
  `;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  // ── Build DOM ─────────────────────────────────────────────────────────
  const fab = document.createElement('button');
  fab.id = 'los-chat-fab';
  fab.title = 'Chat with LeadOS';
  fab.innerHTML = '💬<div class="los-badge" id="los-badge">1</div>';

  const box = document.createElement('div');
  box.id = 'los-chat-box';
  box.innerHTML = `
    <div class="los-chat-header">
      <div class="los-chat-avatar">L</div>
      <div>
        <div class="los-chat-name">LeadOS Support</div>
        <div class="los-chat-status">Online · Powered by Claude AI</div>
      </div>
      <button class="los-chat-close" id="los-close" title="Close">✕</button>
    </div>
    <div class="los-messages" id="los-messages"></div>
    <div class="los-suggested" id="los-suggested">
      <div class="los-chip" onclick="losSend('How do I set up voice transfers?')">Voice transfers?</div>
      <div class="los-chip" onclick="losSend('How are leads scored?')">Lead scoring?</div>
      <div class="los-chip" onclick="losSend('What does $49/month include?')">Pricing?</div>
    </div>
    <div class="los-chat-input-row">
      <textarea class="los-input" id="los-input" placeholder="Ask anything about LeadOS..." rows="1"></textarea>
      <button class="los-send" id="los-send" title="Send">➤</button>
    </div>
  `;

  document.body.appendChild(fab);
  document.body.appendChild(box);

  // ── State ─────────────────────────────────────────────────────────────
  let sessionId = 'sess_' + Math.random().toString(36).slice(2);
  let history = [];
  let isOpen = false;
  let isTyping = false;

  // ── Helpers ───────────────────────────────────────────────────────────
  function ts() {
    return new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  }

  function scrollBottom() {
    const el = document.getElementById('los-messages');
    if (el) el.scrollTop = el.scrollHeight;
  }

  function addMsg(role, text) {
    const el = document.getElementById('los-messages');
    if (!el) return;
    const div = document.createElement('div');
    div.className = `los-msg ${role === 'user' ? 'user' : 'bot'}`;
    div.innerHTML = `<div class="los-bubble">${text.replace(/\n/g,'<br>')}</div><div class="los-ts">${ts()}</div>`;
    el.appendChild(div);
    scrollBottom();
  }

  function showTyping() {
    const el = document.getElementById('los-messages');
    if (!el || isTyping) return;
    isTyping = true;
    const div = document.createElement('div');
    div.className = 'los-msg bot los-typing';
    div.id = 'los-typing-indicator';
    div.innerHTML = '<div class="los-bubble"><div class="los-dot"></div><div class="los-dot"></div><div class="los-dot"></div></div>';
    el.appendChild(div);
    scrollBottom();
  }

  function hideTyping() {
    const el = document.getElementById('los-typing-indicator');
    if (el) el.remove();
    isTyping = false;
  }

  // ── Send message ──────────────────────────────────────────────────────
  window.losSend = async function(text) {
    text = (text || '').trim();
    if (!text) return;

    const input = document.getElementById('los-input');
    const send  = document.getElementById('los-send');
    const sug   = document.getElementById('los-suggested');
    if (input) input.value = '';
    if (send)  send.disabled = true;
    if (sug)   sug.style.display = 'none';

    addMsg('user', text);
    history.push({role:'user', content: text});
    showTyping();

    try {
      const res = await fetch(`${API}/chat/message`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({message: text, session_id: sessionId, history: history.slice(-10)})
      });
      const data = await res.json();
      hideTyping();
      const reply = data.reply || data.message || 'Something went wrong. Try again in a moment.';
      addMsg('bot', reply);
      history.push({role:'assistant', content: reply});
    } catch(e) {
      hideTyping();
      addMsg('bot', "I'm having trouble connecting right now. Please try again in a moment, or email support@tryleados.com.");
    }

    if (send) send.disabled = false;
    if (input) input.focus();
  };

  // ── Event listeners ───────────────────────────────────────────────────
  fab.addEventListener('click', function() {
    isOpen = !isOpen;
    box.classList.toggle('open', isOpen);
    fab.innerHTML = isOpen
      ? '✕<div class="los-badge" id="los-badge"></div>'
      : '💬<div class="los-badge" id="los-badge"></div>';
    if (isOpen && history.length === 0) {
      // Greeting on first open
      setTimeout(() => addMsg('bot', "👋 Hey! I'm your LeadOS support agent.\n\nI can help with pricing, lead scoring, voice transfers, CRM setup, and anything else about the platform.\n\nWhat can I help you with?"), 300);
    }
    if (isOpen) scrollBottom();
  });

  document.getElementById('los-close').addEventListener('click', function() {
    isOpen = false;
    box.classList.remove('open');
    fab.innerHTML = '💬<div class="los-badge" id="los-badge"></div>';
  });

  const input = document.getElementById('los-input');
  const send  = document.getElementById('los-send');

  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      losSend(input.value);
    }
  });
  input.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 80) + 'px';
  });
  send.addEventListener('click', function() {
    losSend(input.value);
  });
})();
