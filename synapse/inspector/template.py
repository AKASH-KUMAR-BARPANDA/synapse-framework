"""Interactive Web Inspector HTML/CSS/JS template for Synapse."""

from __future__ import annotations

INSPECTOR_HTML: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Synapse // Interactive Inspector</title>
  <style>
    :root {
      --canvas: #09090b;
      --panel: #18181b;
      --panel-hover: #27272a;
      --inset: #121215;
      --border-subtle: #27272a;
      --border-strong: #3f3f46;
      --text-pri: #f4f4f5;
      --text-sec: #a1a1aa;
      --text-muted: #71717a;
      --accent: #8b8cf8;
      --emerald: #43a077;
      --amber: #c98a3e;
      --font: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--canvas);
      color: var(--text-pri);
      font-family: var(--font);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }
    header {
      height: 52px;
      background: var(--panel);
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      flex-shrink: 0;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 600;
      font-size: 0.95rem;
      letter-spacing: -0.01em;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--emerald);
      box-shadow: 0 0 8px rgba(67, 160, 119, 0.4);
    }
    .tabs {
      display: flex;
      gap: 6px;
    }
    .tab-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-sec);
      font-family: inherit;
      font-size: 0.82rem;
      font-weight: 500;
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .tab-btn:hover {
      color: var(--text-pri);
      background: var(--panel-hover);
    }
    .tab-btn.active {
      color: var(--text-pri);
      background: var(--inset);
      border-color: var(--border-subtle);
    }
    main {
      flex: 1;
      display: flex;
      overflow: hidden;
      position: relative;
    }
    .tab-content {
      display: none;
      width: 100%;
      height: 100%;
      overflow: hidden;
    }
    .tab-content.active {
      display: flex;
    }
    /* Chat View */
    .chat-layout {
      width: 100%;
      display: flex;
      height: 100%;
    }
    .chat-main {
      flex: 1;
      display: flex;
      flex-direction: column;
      height: 100%;
      border-right: 1px solid var(--border-subtle);
    }
    .messages-pane {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .msg {
      max-width: 80%;
      padding: 12px 16px;
      border-radius: 8px;
      font-size: 0.88rem;
      line-height: 1.5;
      word-break: break-word;
    }
    .msg.user {
      align-self: flex-end;
      background: var(--panel-hover);
      border: 1px solid var(--border-strong);
      color: var(--text-pri);
    }
    .msg.assistant {
      align-self: flex-start;
      background: var(--panel);
      border: 1px solid var(--border-subtle);
      color: var(--text-pri);
    }
    .msg pre {
      background: var(--inset);
      padding: 8px 12px;
      border-radius: 4px;
      overflow-x: auto;
      margin: 8px 0;
      font-family: monospace;
      font-size: 0.82rem;
    }
    .input-pane {
      padding: 16px 20px;
      background: var(--panel);
      border-top: 1px solid var(--border-subtle);
      display: flex;
      gap: 10px;
    }
    .chat-input {
      flex: 1;
      background: var(--inset);
      border: 1px solid var(--border-subtle);
      color: var(--text-pri);
      font-family: inherit;
      font-size: 0.88rem;
      padding: 10px 14px;
      border-radius: 6px;
      outline: none;
    }
    .chat-input:focus {
      border-color: var(--accent);
    }
    .send-btn {
      background: var(--accent);
      color: #09090b;
      font-weight: 600;
      border: none;
      padding: 0 18px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.85rem;
    }
    /* Side Inspector Pane */
    .inspector-side {
      width: 380px;
      background: var(--panel);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 20px;
      gap: 18px;
    }
    .card {
      background: var(--inset);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 14px;
    }
    .card-title {
      font-size: 0.78rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-sec);
      margin-bottom: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .badge {
      display: inline-block;
      padding: 2px 7px;
      font-size: 0.72rem;
      border-radius: 4px;
      font-weight: 500;
    }
    .badge.green { background: rgba(67,160,119,0.15); color: var(--emerald); }
    .badge.amber { background: rgba(201,138,62,0.15); color: var(--amber); }
    .pill-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .pill {
      background: var(--panel);
      border: 1px solid var(--border-subtle);
      font-size: 0.75rem;
      padding: 4px 8px;
      border-radius: 4px;
      color: var(--text-sec);
    }
    /* Connectors & Graph View */
    .full-pane {
      width: 100%;
      height: 100%;
      overflow-y: auto;
      padding: 28px;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }
    .action-btn {
      background: var(--panel-hover);
      border: 1px solid var(--border-subtle);
      color: var(--text-pri);
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 0.8rem;
      cursor: pointer;
      font-family: inherit;
    }
    .action-btn:hover { background: var(--border-strong); }
    iframe.graph-frame {
      width: 100%;
      height: 100%;
      border: none;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="status-dot"></div>
      <span>Synapse // Inspector</span>
    </div>
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('chat')">Chat Playground</button>
      <button class="tab-btn" onclick="switchTab('connectors')">Connectors</button>
      <button class="tab-btn" onclick="switchTab('graph')">3D Knowledge Graph</button>
    </div>
  </header>

  <main>
    <!-- TAB 1: Chat Playground -->
    <div id="tab-chat" class="tab-content active">
      <div class="chat-layout">
        <div class="chat-main">
          <div id="messages-pane" class="messages-pane">
            <div class="msg assistant">
              Hello! Synapse is online with Multi-MCP tool routing and Hybrid RAG active. Try asking:
              <br><br>
              • <em>"Check my email to find any unread messages"</em><br>
              • <em>"Search my Notion notes"</em><br>
              • <em>"Explain how Hybrid RAG combines ChromaDB with NetworkX"</em>
            </div>
          </div>
          <div class="input-pane">
            <input type="text" id="chat-input" class="chat-input" placeholder="Type a message or tool request..." onkeydown="if(event.key==='Enter') sendMessage()" />
            <button class="send-btn" onclick="sendMessage()">Send</button>
          </div>
        </div>

        <div class="inspector-side">
          <div class="card">
            <div class="card-title">Active Model Provider</div>
            <div id="model-badge" style="font-size:0.85rem; font-weight:500; color:var(--text-pri);">{{MODEL_DISPLAY}}</div>
          </div>

          <div class="card">
            <div class="card-title">
              <span>Executed Tools</span>
              <span id="tool-count" class="badge green">0 calls</span>
            </div>
            <div id="live-tool-display" style="font-size:0.8rem; color:var(--text-sec);">No tools invoked yet.</div>
          </div>

          <div class="card">
            <div class="card-title">Retrieved Chunks</div>
            <div id="chunks-pill-list" class="pill-list">
              <span style="font-size:0.75rem; color:var(--text-muted);">None</span>
            </div>
          </div>

          <div class="card">
            <div class="card-title">Graph Triples</div>
            <div id="triples-pill-list" class="pill-list">
              <span style="font-size:0.75rem; color:var(--text-muted);">None</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: Connectors -->
    <div id="tab-connectors" class="tab-content">
      <div class="full-pane">
        <h2 style="font-size: 1.15rem; font-weight:600; margin-bottom: 6px;">Registered Connectors</h2>
        <p style="font-size: 0.85rem; color: var(--text-sec);">Multi-MCP connectors registered in this Synapse instance.</p>
        <div id="connectors-grid" class="grid-2">
          <!-- Dynamically filled -->
        </div>
      </div>
    </div>

    <!-- TAB 3: 3D Knowledge Graph -->
    <div id="tab-graph" class="tab-content">
      <iframe src="/graph/export" class="graph-frame"></iframe>
    </div>
  </main>

  <script>
    function switchTab(name) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById('tab-' + name).classList.add('active');
      if (name === 'connectors') loadConnectors();
    }

    async function loadConnectors() {
      try {
        const res = await fetch('/sync/servers');
        const data = await res.json();
        const grid = document.getElementById('connectors-grid');
        grid.innerHTML = '';
        (data.servers || []).forEach(s => {
          const card = document.createElement('div');
          card.className = 'card';
          card.innerHTML = `
            <div class="card-title">
              <span>${s.name.toUpperCase()}</span>
              <span class="badge ${s.is_ready ? 'green' : 'amber'}">${s.is_ready ? 'Connected' : 'Needs Config'}</span>
            </div>
            <p style="font-size:0.8rem; color:var(--text-sec); margin-bottom:12px;">${s.description || 'MCP Connector'}</p>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:12px;">Default tool: <code>${s.default_tool || 'N/A'}</code></div>
            <button class="action-btn" onclick="syncConnector('${s.name}')">Trigger Background Sync</button>
          `;
          grid.appendChild(card);
        });
      } catch (e) {
        console.error(e);
      }
    }

    async function syncConnector(name) {
      try {
        const res = await fetch('/sync/' + name, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({extract_graph: true})
        });
        const data = await res.json();
        alert(data.message || 'Sync initiated.');
      } catch (e) {
        alert('Sync error: ' + e);
      }
    }

    async function sendMessage() {
      const input = document.getElementById('chat-input');
      const text = input.value.trim();
      if (!text) return;
      input.value = '';

      const pane = document.getElementById('messages-pane');
      const userMsg = document.createElement('div');
      userMsg.className = 'msg user';
      userMsg.textContent = text;
      pane.appendChild(userMsg);

      const assistantMsg = document.createElement('div');
      assistantMsg.className = 'msg assistant';
      assistantMsg.textContent = '...';
      pane.appendChild(assistantMsg);
      pane.scrollTop = pane.scrollHeight;

      try {
        const res = await fetch('/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({message: text, history: []})
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        assistantMsg.textContent = '';
        const tokenContainer = document.createElement('div');
        tokenContainer.className = 'msg-body';
        assistantMsg.appendChild(tokenContainer);

        while (true) {
          const {done, value} = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, {stream: true});
          const lines = buffer.split('\\n');
          buffer = lines.pop();

          for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.startsWith('event: context')) {
              const nextLine = lines[i+1];
              if (nextLine && nextLine.startsWith('data: ')) {
                const ctx = JSON.parse(nextLine.slice(6));
                renderContext(ctx);
                if (ctx.tool_calls && ctx.tool_calls.length > 0) {
                  ctx.tool_calls.forEach(call => {
                    const badge = document.createElement('div');
                    badge.style.cssText = 'display:flex; align-items:center; gap:6px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); color:#10b981; border-radius:6px; padding:6px 10px; font-size:0.75rem; font-family:monospace; margin-bottom:8px;';
                    const argsFormatted = JSON.stringify(call.arguments || {});
                    badge.innerHTML = `<span>⚡</span> <span>Invoked Tool: <strong>${call.server}.${call.tool}</strong>(${argsFormatted})</span>`;
                    assistantMsg.insertBefore(badge, tokenContainer);
                  });
                }
                i++;
              }
            } else if (line.startsWith('data: ')) {
              try {
                const payload = JSON.parse(line.slice(6));
                if (payload.token) {
                  tokenContainer.textContent += payload.token;
                  pane.scrollTop = pane.scrollHeight;
                }
              } catch(e) {}
            }
          }
        }
      } catch (err) {
        assistantMsg.textContent = 'Error: ' + err;
      }

    }

    function renderContext(ctx) {
      if (ctx.tool_calls && ctx.tool_calls.length > 0) {
        document.getElementById('tool-count').textContent = ctx.tool_calls.length + ' call(s)';
        document.getElementById('live-tool-display').innerHTML = ctx.tool_calls.map(c => `<code>${c.server}.${c.tool}</code> (${c.items_fetched || 0} items)`).join('<br>');
      } else {
        document.getElementById('tool-count').textContent = '0 calls';
        document.getElementById('live-tool-display').textContent = 'No live tool called.';
      }

      const chunkList = document.getElementById('chunks-pill-list');
      chunkList.innerHTML = '';
      if (ctx.chunks && ctx.chunks.length > 0) {
        ctx.chunks.forEach(c => {
          const pill = document.createElement('span');
          pill.className = 'pill';
          pill.textContent = (c.subject || c.source || 'Chunk').slice(0, 32);
          chunkList.appendChild(pill);
        });
      } else {
        chunkList.innerHTML = '<span style="font-size:0.75rem; color:var(--text-muted);">None</span>';
      }

      const tripleList = document.getElementById('triples-pill-list');
      tripleList.innerHTML = '';
      if (ctx.graph_triples && ctx.graph_triples.length > 0) {
        ctx.graph_triples.forEach(t => {
          const pill = document.createElement('span');
          pill.className = 'pill';
          pill.textContent = String(t).slice(0, 36);
          tripleList.appendChild(pill);
        });
      } else {
        tripleList.innerHTML = '<span style="font-size:0.75rem; color:var(--text-muted);">None</span>';
      }
    }

    async function loadAppInfo() {
      try {
        const res = await fetch('/info');
        if (!res.ok) return;
        const data = await res.json();
        if (data.model_display) {
          const badge = document.getElementById('model-badge');
          if (badge) badge.textContent = data.model_display;
        }
      } catch (e) {
        console.warn('Could not load app info:', e);
      }
    }

    window.addEventListener('DOMContentLoaded', () => {
      loadAppInfo();
    });
  </script>
</body>
</html>
"""


def render_inspector_html(model_display: str = "Ollama (qwen2.5:0.5b)") -> str:
    """Renders the Inspector HTML template with dynamic metadata."""
    return INSPECTOR_HTML.replace("{{MODEL_DISPLAY}}", model_display)

