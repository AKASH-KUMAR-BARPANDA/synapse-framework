"""WebGL 3D Knowledge Graph HTML exporter using Solid Matte / Zinc styling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from synapse.config import DESIGN_TOKENS


class GraphExporter:
    """Exports knowledge graph state into a standalone 3D WebGL HTML visualizer."""

    @classmethod
    def to_webgl_json(cls, graph_source: Any) -> dict[str, Any]:
        """Converts graph into node and link lists for 3D force simulation."""
        default_palette = DESIGN_TOKENS["palettes"]["zinc"]

        # 1. Any BaseGraphStore or custom store providing get_3d_payload
        if hasattr(graph_source, "get_3d_payload"):
            payload = graph_source.get_3d_payload()
            if isinstance(payload, dict) and "nodes" in payload and "links" in payload:
                return payload

        # 2. Raw dict containing nodes and links
        if isinstance(graph_source, dict) and "nodes" in graph_source and "links" in graph_source:
            return graph_source

        # 3. NetworkX Graph or wrapper with .graph attribute
        underlying = getattr(graph_source, "graph", graph_source)
        if hasattr(underlying, "nodes") and hasattr(underlying, "edges"):
            nodes: list[dict[str, Any]] = []
            for node_id, data in underlying.nodes(data=True):
                node_type = data.get("type", "Default")
                color = data.get("color")
                if not color:
                    color = default_palette.get(node_type, default_palette.get("Default", "#71717a"))
                degree = underlying.degree(node_id) if hasattr(underlying, "degree") else 1
                nodes.append({
                    "id": str(node_id),
                    "name": str(node_id),
                    "type": node_type,
                    "color": color,
                    "val": max(3.5, min(12.0, degree * 2.0)),
                })

            links: list[dict[str, Any]] = []
            for u, v, data in underlying.edges(data=True):
                links.append({
                    "source": str(u),
                    "target": str(v),
                    "relation": data.get("relation", "CONNECTED_TO"),
                })

            return {"nodes": nodes, "links": links}

        return {"nodes": [], "links": []}

    @classmethod
    def render_html(cls, graph_source: Any) -> str:
        """Renders a self-contained 3D WebGL visualizer HTML string."""
        payload = cls.to_webgl_json(graph_source)
        payload_json = json.dumps(payload, indent=2)
        palettes_json = json.dumps(DESIGN_TOKENS["palettes"], indent=2)

        font_family_js = json.dumps(DESIGN_TOKENS["text"]["font_family"])
        canvas_bg_js = json.dumps(DESIGN_TOKENS["surface"]["canvas"])
        panel_bg_js = json.dumps(DESIGN_TOKENS["surface"]["panel"])
        border_subtle_js = json.dumps(DESIGN_TOKENS["border"]["subtle"])
        text_primary_js = json.dumps(DESIGN_TOKENS["text"]["primary"])
        text_secondary_js = json.dumps(DESIGN_TOKENS["text"]["secondary"])

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Synapse // Knowledge Graph Inspector</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    html, body {{
      width: 100%; height: 100%; overflow: hidden;
      background: {DESIGN_TOKENS["surface"]["canvas"]};
      font-family: {DESIGN_TOKENS["text"]["font_family"]};
      color: {DESIGN_TOKENS["text"]["primary"]};
    }}
    .matte-panel {{
      background: {DESIGN_TOKENS["surface"]["panel"]};
      border: 1px solid {DESIGN_TOKENS["border"]["subtle"]};
      border-radius: 6px;
      backdrop-filter: blur(8px);
    }}
    #header-hud {{
      position: absolute; top: 16px; left: 16px; z-index: 20;
      height: 36px; padding: 0 12px; display: flex; align-items: center; gap: 10px;
    }}
    .status-dot {{
      width: 7px; height: 7px; border-radius: 50%; background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }}
    .app-title {{ font-size: 0.82rem; font-weight: 500; letter-spacing: -0.01em; }}
    .node-counter {{ font-size: 0.72rem; color: {DESIGN_TOKENS["text"]["secondary"]}; margin-left: 4px; }}
    #control-hud {{
      position: absolute; top: 16px; right: 16px; z-index: 20;
      display: flex; align-items: center; gap: 8px;
    }}
    .control-item {{
      height: 36px; display: flex; align-items: center; padding: 0 10px; gap: 8px;
    }}
    .search-input {{
      background: transparent; border: none; outline: none;
      color: {DESIGN_TOKENS["text"]["primary"]}; font-size: 0.82rem; width: 170px;
      transition: width 0.2s ease;
    }}
    .search-input:focus {{ width: 230px; }}
    .search-badge {{
      display: none; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px;
      background: #27272a; color: #38bdf8; font-weight: 500; white-space: nowrap;
    }}
    .palette-select {{
      background: transparent; border: none; outline: none;
      color: {DESIGN_TOKENS["text"]["primary"]}; font-size: 0.8rem; cursor: pointer;
    }}
    .palette-select option {{
      background: {DESIGN_TOKENS["surface"]["panel"]}; color: {DESIGN_TOKENS["text"]["primary"]};
    }}
    .action-btn {{
      background: transparent; border: none; outline: none; cursor: pointer;
      color: {DESIGN_TOKENS["text"]["secondary"]}; font-size: 0.78rem; display: flex;
      align-items: center; gap: 4px; padding: 4px 8px; border-radius: 4px;
      transition: background 0.15s, color 0.15s;
    }}
    .action-btn:hover {{
      background: {DESIGN_TOKENS["border"]["subtle"]}; color: {DESIGN_TOKENS["text"]["primary"]};
    }}
    #legend-bar {{
      position: absolute; bottom: 16px; left: 16px; z-index: 20;
      display: flex; align-items: center; gap: 10px; padding: 6px 12px;
      font-size: 0.72rem; color: {DESIGN_TOKENS["text"]["secondary"]};
      max-width: calc(100vw - 32px); overflow-x: auto;
    }}
    .legend-chip {{
      display: flex; align-items: center; gap: 6px; cursor: pointer;
      padding: 3px 6px; border-radius: 4px; transition: background 0.15s;
      white-space: nowrap;
    }}
    .legend-chip:hover {{
      background: {DESIGN_TOKENS["border"]["subtle"]}; color: {DESIGN_TOKENS["text"]["primary"]};
    }}
    .legend-chip.active-filter {{
      background: #27272a; color: #38bdf8; font-weight: 500;
    }}
    .legend-indicator {{
      width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex-shrink: 0;
    }}
    #node-card {{
      position: absolute; bottom: 64px; right: 16px; z-index: 25;
      width: 280px; padding: 14px; display: none; flex-direction: column; gap: 8px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }}
    .card-header {{
      display: flex; align-items: center; justify-content: space-between;
    }}
    .card-title {{
      font-size: 0.88rem; font-weight: 600; color: {DESIGN_TOKENS["text"]["primary"]};
      word-break: break-word;
    }}
    .card-close {{
      cursor: pointer; color: {DESIGN_TOKENS["text"]["secondary"]}; font-size: 0.9rem;
      padding: 2px 6px; border-radius: 4px;
    }}
    .card-close:hover {{ background: {DESIGN_TOKENS["border"]["subtle"]}; color: #fff; }}
    .card-badge {{
      display: inline-flex; align-items: center; gap: 6px; font-size: 0.72rem;
      padding: 2px 8px; border-radius: 10px; background: #27272a; width: fit-content;
    }}
    .card-relations {{
      font-size: 0.74rem; color: {DESIGN_TOKENS["text"]["secondary"]};
      max-height: 120px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px;
      margin-top: 4px; border-top: 1px solid {DESIGN_TOKENS["border"]["subtle"]}; padding-top: 6px;
    }}
    .rel-item {{ word-break: break-word; line-height: 1.3; }}
    .rel-tag {{ color: #a1a1aa; font-weight: 500; }}
    #graph-viewport {{ position: absolute; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 1; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/3d-force-graph@1.76.2/dist/3d-force-graph.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three-spritetext@1.9.0/dist/three-spritetext.min.js"></script>
</head>
<body>
  <div id="header-hud" class="matte-panel">
    <div class="status-dot"></div>
    <span class="app-title">Synapse // Knowledge Graph</span>
    <span id="node-count-label" class="node-counter"></span>
  </div>

  <div id="control-hud">
    <div class="matte-panel control-item">
      <select id="palette-select" class="palette-select" title="Change color palette">
        <option value="zinc" selected>Zinc (Default)</option>
        <option value="stone">Warm Stone</option>
        <option value="basalt">Cool Basalt</option>
        <option value="neon">Cyberpunk Neon</option>
        <option value="custom">Developer Custom Colors (.color)</option>
      </select>
    </div>
    <div class="matte-panel control-item">
      <input type="text" id="search-input" class="search-input" placeholder="Find node... (⌘K)" autocomplete="off" />
      <span id="search-badge" class="search-badge"></span>
    </div>
    <div class="matte-panel control-item" style="padding: 0 4px;">
      <button id="btn-recenter" class="action-btn" title="Recenter Camera (Fit Graph)">
        <span>⊙</span> Fit
      </button>
    </div>
  </div>

  <div id="legend-bar" class="matte-panel"></div>

  <div id="node-card" class="matte-panel">
    <div class="card-header">
      <span id="card-name" class="card-title"></span>
      <span id="card-close-btn" class="card-close">✕</span>
    </div>
    <div class="card-badge">
      <span id="card-dot" class="legend-indicator"></span>
      <span id="card-type"></span>
    </div>
    <div id="card-degree" style="font-size: 0.72rem; color: #a1a1aa;"></div>
    <div id="card-relations" class="card-relations"></div>
  </div>

  <div id="graph-viewport"></div>

  <script>
    const gData = {payload_json};
    const PALETTES = {palettes_json};
    const fontName = {font_family_js};
    const canvasBg = {canvas_bg_js};
    const panelBg = {panel_bg_js};
    const borderSubtle = {border_subtle_js};
    const textPri = {text_primary_js};
    const textSec = {text_secondary_js};

    const viewport = document.getElementById('graph-viewport');
    const searchInput = document.getElementById('search-input');
    const searchBadge = document.getElementById('search-badge');
    const paletteSelect = document.getElementById('palette-select');
    const legendBar = document.getElementById('legend-bar');
    const nodeCard = document.getElementById('node-card');
    const nodeCountLabel = document.getElementById('node-count-label');
    const btnRecenter = document.getElementById('btn-recenter');

    let currentPaletteKey = 'zinc';
    let matchedNodeIds = new Set();
    let selectedNode = null;
    let activeFilterType = null;

    if (nodeCountLabel) {{
      nodeCountLabel.textContent = '(' + gData.nodes.length + ' nodes, ' + gData.links.length + ' relations)';
    }}

    // Deterministic hue generator for unknown dynamic types
    function getDeterministicColor(str) {{
      let hash = 0;
      for (let i = 0; i < str.length; i++) {{
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
      }}
      const hue = Math.abs(hash % 360);
      return `hsl(${{hue}}, 72%, 60%)`;
    }}

    // Robust color resolution supporting explicit node.color and active theme palettes
    function getNodeColor(node, paletteKey) {{
      const pal = PALETTES[paletteKey] || PALETTES['zinc'] || {{}};

      // 1. If user selected explicit "Developer Custom Colors (.color)"
      if (paletteKey === 'custom') {{
        if (node.color && node.color !== '#71717a' && node.color !== '#94a3b8') {{
          return node.color;
        }}
        return pal[node.type] || getDeterministicColor(node.type || 'Default');
      }}

      // 2. Default Zinc Theme: prioritize explicit custom .color if provided by user!
      if (paletteKey === 'zinc') {{
        if (node.color && node.color !== '#71717a' && node.color !== '#94a3b8') {{
          return node.color;
        }}
        if (pal[node.type]) return pal[node.type];
        return getDeterministicColor(node.type || 'Default');
      }}

      // 3. For chosen theme palettes (Stone, Basalt, Neon):
      // Apply theme palette for the entity type!
      if (pal && pal[node.type]) {{
        return pal[node.type];
      }}
      // If node has an explicit custom color, honor it
      if (node.color && node.color !== '#71717a' && node.color !== '#94a3b8') {{
        return node.color;
      }}
      return pal['Default'] || getDeterministicColor(node.type || 'Default');
    }}

    // Dynamic legend generation based on actual types present in the graph
    function syncLegend() {{
      if (!legendBar) return;
      legendBar.innerHTML = '';

      const typesInGraph = new Set();
      gData.nodes.forEach(n => {{
        typesInGraph.add(n.type || 'Default');
      }});

      Array.from(typesInGraph).sort().forEach(type => {{
        const chip = document.createElement('div');
        chip.className = 'legend-chip';
        if (activeFilterType === type) chip.classList.add('active-filter');
        chip.title = `Filter by ${{type}}`;

        const sampleNode = gData.nodes.find(n => n.type === type) || {{ type: type }};
        const color = getNodeColor(sampleNode, currentPaletteKey);

        const indicator = document.createElement('span');
        indicator.className = 'legend-indicator';
        indicator.style.backgroundColor = color;

        const label = document.createElement('span');
        label.textContent = type;

        chip.appendChild(indicator);
        chip.appendChild(label);

        chip.addEventListener('click', (e) => {{
          e.stopPropagation();
          if (activeFilterType === type) {{
            activeFilterType = null;
            searchInput.value = '';
            performSearch('');
          }} else {{
            activeFilterType = type;
            searchInput.value = type;
            performSearch(type);
          }}
          syncLegend();
        }});

        legendBar.appendChild(chip);
      }});
    }}

    // Apply palette to all nodes in the 3D scene
    function applyPalette(paletteKey) {{
      currentPaletteKey = paletteKey;
      syncLegend();

      gData.nodes.forEach(node => {{
        if (node.__mesh && node.__mesh.material) {{
          const isMatched = matchedNodeIds.size === 0 || matchedNodeIds.has(node.id);
          if (isMatched) {{
            const newColor = getNodeColor(node, currentPaletteKey);
            node.__mesh.material.color.set(newColor);
          }}
        }}
      }});
    }}

    // Search and highlight logic
    function performSearch(query) {{
      const q = query.trim().toLowerCase();
      matchedNodeIds.clear();

      if (!q) {{
        activeFilterType = null;
        if (searchBadge) {{
          searchBadge.style.display = 'none';
          searchBadge.textContent = '';
        }}

        gData.nodes.forEach(node => {{
          if (node.__mesh) {{
            node.__mesh.material.opacity = 1.0;
            node.__mesh.material.transparent = false;
            node.__mesh.scale.set(1, 1, 1);
            const col = getNodeColor(node, currentPaletteKey);
            node.__mesh.material.color.set(col);
          }}
          if (node.__sprite) {{
            node.__sprite.visible = true;
            node.__sprite.color = textSec;
          }}
        }});
        syncLegend();
        return;
      }}

      let firstMatch = null;
      gData.nodes.forEach(node => {{
        const nameMatch = (node.name || '').toLowerCase().includes(q);
        const idMatch = (node.id || '').toLowerCase().includes(q);
        const typeMatch = (node.type || '').toLowerCase().includes(q);

        if (nameMatch || idMatch || typeMatch) {{
          matchedNodeIds.add(node.id);
          if (!firstMatch) firstMatch = node;
        }}
      }});

      const count = matchedNodeIds.size;
      if (searchBadge) {{
        searchBadge.style.display = 'inline-block';
        searchBadge.textContent = count === 0 ? '0 found' : `${{count}} found (↵)`;
      }}

      gData.nodes.forEach(node => {{
        const isMatched = matchedNodeIds.has(node.id);
        if (node.__mesh) {{
          if (isMatched) {{
            node.__mesh.material.transparent = false;
            node.__mesh.material.opacity = 1.0;
            node.__mesh.scale.set(1.4, 1.4, 1.4);
            // Highlight color
            node.__mesh.material.color.set('#38bdf8');
          }} else {{
            node.__mesh.material.transparent = true;
            node.__mesh.material.opacity = 0.12;
            node.__mesh.scale.set(0.75, 0.75, 0.75);
            node.__mesh.material.color.set('#3f3f46');
          }}
        }}
        if (node.__sprite) {{
          if (isMatched) {{
            node.__sprite.visible = true;
            node.__sprite.color = '#ffffff';
          }} else {{
            node.__sprite.visible = false;
          }}
        }}
      }});
    }}

    // Fly camera smoothly to a target node
    function flyToNode(node) {{
      if (!node) return;
      const x = node.x || 0;
      const y = node.y || 0;
      const z = node.z || 0;
      const distance = 90;
      const currentHypot = Math.hypot(x, y, z) || 1;
      const distRatio = 1 + distance / currentHypot;

      Graph.cameraPosition(
        {{ x: x * distRatio, y: y * distRatio, z: z * distRatio }},
        {{ x: x, y: y, z: z }},
        1000
      );
    }}

    // Display interactive node details card
    function showNodeCard(node) {{
      if (!nodeCard || !node) return;
      selectedNode = node;

      document.getElementById('card-name').textContent = node.name || node.id;
      document.getElementById('card-type').textContent = node.type || 'Default';
      const col = getNodeColor(node, currentPaletteKey);
      document.getElementById('card-dot').style.backgroundColor = col;

      // Find relations
      const rels = [];
      gData.links.forEach(l => {{
        const srcId = typeof l.source === 'object' ? l.source.id : l.source;
        const tgtId = typeof l.target === 'object' ? l.target.id : l.target;
        if (srcId === node.id) {{
          rels.push(`→ ${{l.relation || 'CONNECTED_TO'}} → ${{tgtId}}`);
        }} else if (tgtId === node.id) {{
          rels.push(`← ${{l.relation || 'CONNECTED_TO'}} ← ${{srcId}}`);
        }}
      }});

      document.getElementById('card-degree').textContent = `${{rels.length}} connection${{rels.length === 1 ? '' : 's'}}`;
      const relsContainer = document.getElementById('card-relations');
      relsContainer.innerHTML = '';
      if (rels.length === 0) {{
        relsContainer.innerHTML = '<span style="color: #71717a;">No direct connections</span>';
      }} else {{
        rels.forEach(r => {{
          const div = document.createElement('div');
          div.className = 'rel-item';
          div.textContent = r;
          relsContainer.appendChild(div);
        }});
      }}

      nodeCard.style.display = 'flex';
    }}

    // Initialize ForceGraph3D
    const Graph = ForceGraph3D()(viewport)
      .graphData(gData)
      .backgroundColor(canvasBg)
      .nodeThreeObject(node => {{
        const group = new THREE.Group();
        const radius = Math.max(2.8, (node.val || 4) * 0.7);
        const sphereGeo = new THREE.SphereGeometry(radius, 18, 18);

        const initialColor = getNodeColor(node, currentPaletteKey);
        const sphereMat = new THREE.MeshLambertMaterial({{
          color: initialColor,
          transparent: true,
          opacity: 1.0,
        }});
        const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
        group.add(sphereMesh);

        const sprite = new SpriteText(node.name || node.id);
        sprite.material.depthWrite = false;
        sprite.color = textSec;
        sprite.textHeight = 3.0;
        sprite.fontFace = fontName;
        sprite.position.y = - (radius + 3.0);
        group.add(sprite);

        node.__mesh = sphereMesh;
        node.__sprite = sprite;
        node.__radius = radius;
        return group;
      }})
      .linkLabel(link => link.relation || '')
      .linkColor(() => borderSubtle)
      .linkWidth(0.8)
      .linkOpacity(0.5)
      .onNodeClick(node => {{
        flyToNode(node);
        showNodeCard(node);
      }})
      .onNodeHover(node => {{
        viewport.style.cursor = node ? 'pointer' : 'default';
      }})
      .onBackgroundClick(() => {{
        if (nodeCard) nodeCard.style.display = 'none';
      }});

    // Initialize legend
    syncLegend();

    // Event Listener 1: Palette / Theme Switcher
    if (paletteSelect) {{
      paletteSelect.addEventListener('change', (e) => {{
        applyPalette(e.target.value);
      }});
    }}

    // Event Listener 2: Real-time Search Input
    if (searchInput) {{
      searchInput.addEventListener('input', (e) => {{
        performSearch(e.target.value);
      }});

      searchInput.addEventListener('keydown', (e) => {{
        if (e.key === 'Enter') {{
          if (matchedNodeIds.size > 0) {{
            const firstId = Array.from(matchedNodeIds)[0];
            const target = gData.nodes.find(n => n.id === firstId);
            if (target) {{
              flyToNode(target);
              showNodeCard(target);
            }}
          }}
        }} else if (e.key === 'Escape') {{
          searchInput.value = '';
          performSearch('');
          searchInput.blur();
        }}
      }});
    }}

    // Global shortcut: ⌘K or Ctrl+K to focus search
    window.addEventListener('keydown', (e) => {{
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {{
        e.preventDefault();
        if (searchInput) {{
          searchInput.focus();
          searchInput.select();
        }}
      }}
    }});

    // Event Listener 3: Recenter Button
    if (btnRecenter) {{
      btnRecenter.addEventListener('click', () => {{
        Graph.zoomToFit(800, 35);
      }});
    }}

    // Event Listener 4: Close card
    const cardCloseBtn = document.getElementById('card-close-btn');
    if (cardCloseBtn) {{
      cardCloseBtn.addEventListener('click', () => {{
        if (nodeCard) nodeCard.style.display = 'none';
      }});
    }}

    // Initial Zoom to Fit
    setTimeout(() => Graph.zoomToFit(800, 35), 450);
  </script>
</body>
</html>"""

    @classmethod
    def export_to_html(
        cls,
        graph_source: Any,
        output_path: str | Path = "graph_preview.html",
    ) -> Path:
        """Writes a self-contained 3D WebGL visualizer HTML file to disk."""
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        html_template = cls.render_html(graph_source)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_template)
        return out_file
