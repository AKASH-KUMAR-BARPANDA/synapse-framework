# app/storage/graph_exporter.py
import json
from pathlib import Path
from typing import Dict, Any, Union
import networkx as nx

from app.storage.graph_store import PersistentGraphStore
from app.config import DESIGN_TOKENS


class GraphExporter:
    """
    Exports Knowledge Graph representations into a solid matte,
    engineered WebGL canvas with crisp Linear/Anthropic UI aesthetics.
    """

    @staticmethod
    def to_webgl_json(graph_source: Union[PersistentGraphStore, nx.DiGraph]) -> Dict[str, Any]:
        default_palette = DESIGN_TOKENS["palettes"]["zinc"]

        if isinstance(graph_source, PersistentGraphStore):
            return graph_source.get_3d_payload()

        nodes = []
        for node_id, data in graph_source.nodes(data=True):
            node_type = data.get("type", "Default")
            color = data.get("color", default_palette.get(node_type, default_palette["Default"]))
            degree = graph_source.degree(node_id)
            node_size = max(3.5, min(12.0, degree * 2.0))

            nodes.append({
                "id": str(node_id),
                "name": str(node_id),
                "type": node_type,
                "color": color,
                "val": node_size,
            })

        links = []
        for u, v, data in graph_source.edges(data=True):
            links.append({
                "source": str(u),
                "target": str(v),
                "relation": data.get("relation", "CONNECTED_TO"),
            })

        return {"nodes": nodes, "links": links}

    @classmethod
    def export_to_html(
        cls,
        graph_source: Union[PersistentGraphStore, nx.DiGraph],
        output_path: Union[str, Path]
    ) -> Path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        payload = cls.to_webgl_json(graph_source)
        payload_json = json.dumps(payload, indent=2)
        palettes_json = json.dumps(DESIGN_TOKENS["palettes"], indent=2)

        # JSON-encode config values to prevent JS syntax breakage
        font_family_js = json.dumps(DESIGN_TOKENS["text"]["font_family"])
        canvas_bg_js = json.dumps(DESIGN_TOKENS["surface"]["canvas"])
        panel_bg_js = json.dumps(DESIGN_TOKENS["surface"]["panel"])
        border_subtle_js = json.dumps(DESIGN_TOKENS["border"]["subtle"])
        text_primary_js = json.dumps(DESIGN_TOKENS["text"]["primary"])
        text_secondary_js = json.dumps(DESIGN_TOKENS["text"]["secondary"])

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Synapse // Knowledge Graph</title>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }}
    html, body {{
      width: 100%;
      height: 100%;
      overflow: hidden;
      background-color: {DESIGN_TOKENS["surface"]["canvas"]};
      font-family: {DESIGN_TOKENS["text"]["font_family"]};
      color: {DESIGN_TOKENS["text"]["primary"]};
    }}

    .matte-panel {{
      background-color: {DESIGN_TOKENS["surface"]["panel"]};
      border: 1px solid {DESIGN_TOKENS["border"]["subtle"]};
      border-radius: 6px;
    }}

    #header-hud {{
      position: absolute;
      top: 16px;
      left: 16px;
      z-index: 20;
      height: 36px;
      padding: 0 12px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .status-dot {{
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background-color: {DESIGN_TOKENS["palettes"]["zinc"]["Project"]};
    }}
    .app-title {{
      font-size: 0.82rem;
      font-weight: 500;
      letter-spacing: -0.01em;
      color: {DESIGN_TOKENS["text"]["primary"]};
    }}
    .app-badge {{
      font-size: 0.72rem;
      color: {DESIGN_TOKENS["text"]["muted"]};
      margin-left: 2px;
    }}

    #control-hud {{
      position: absolute;
      top: 16px;
      right: 16px;
      z-index: 20;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .control-item {{
      height: 36px;
      display: flex;
      align-items: center;
      padding: 0 10px;
      gap: 8px;
    }}
    .search-input {{
      background: transparent;
      border: none;
      outline: none;
      color: {DESIGN_TOKENS["text"]["primary"]};
      font-size: 0.82rem;
      font-family: inherit;
      width: 160px;
      transition: width 0.2s ease;
    }}
    .search-input:focus {{
      width: 220px;
    }}
    .search-input::placeholder {{
      color: {DESIGN_TOKENS["text"]["muted"]};
    }}
    .key-badge {{
      font-size: 0.65rem;
      font-weight: 500;
      color: {DESIGN_TOKENS["text"]["muted"]};
      background-color: {DESIGN_TOKENS["surface"]["inset"]};
      border: 1px solid {DESIGN_TOKENS["border"]["subtle"]};
      padding: 2px 4px;
      border-radius: 3px;
    }}
    .palette-select {{
      background: transparent;
      border: none;
      outline: none;
      color: {DESIGN_TOKENS["text"]["secondary"]};
      font-size: 0.8rem;
      font-family: inherit;
      cursor: pointer;
    }}
    .palette-select option {{
      background-color: {DESIGN_TOKENS["surface"]["panel"]};
      color: {DESIGN_TOKENS["text"]["primary"]};
    }}

    #legend-bar {{
      position: absolute;
      bottom: 16px;
      left: 16px;
      z-index: 20;
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 6px 12px;
    }}
    .legend-chip {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.72rem;
      color: {DESIGN_TOKENS["text"]["secondary"]};
    }}
    .legend-indicator {{
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 2px;
    }}

    #graph-viewport {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: 1;
    }}
  </style>

  <script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/3d-force-graph@1.76.2/dist/3d-force-graph.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three-spritetext@1.9.0/dist/three-spritetext.min.js"></script>
</head>
<body>
  <div id="header-hud" class="matte-panel">
    <div class="status-dot"></div>
    <span class="app-title">Synapse <span class="app-badge">Graph</span></span>
  </div>

  <div id="control-hud">
    <div class="matte-panel control-item">
      <select id="palette-select" class="palette-select">
        <option value="zinc" selected>Zinc (Linear)</option>
        <option value="stone">Stone (Anthropic)</option>
        <option value="basalt">Basalt (Slate)</option>
      </select>
    </div>
    <div class="matte-panel control-item">
      <input type="text" id="search-input" class="search-input" placeholder="Find node..." autocomplete="off" />
      <span class="key-badge">⌘K</span>
    </div>
  </div>

  <div id="legend-bar" class="matte-panel">
    <div class="legend-chip"><span id="dot-Person" class="legend-indicator"></span>Person</div>
    <div class="legend-chip"><span id="dot-Email" class="legend-indicator"></span>Email</div>
    <div class="legend-chip"><span id="dot-Project" class="legend-indicator"></span>Project</div>
    <div class="legend-chip"><span id="dot-Tool" class="legend-indicator"></span>Tool</div>
    <div class="legend-chip"><span id="dot-Topic" class="legend-indicator"></span>Topic</div>
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
    const paletteSelect = document.getElementById('palette-select');

    let currentPaletteKey = 'zinc';
    let matchedNodeIds = new Set();
    let currentQuery = '';

    function syncLegend() {{
      const pal = PALETTES[currentPaletteKey];
      for (const [type, color] of Object.entries(pal)) {{
        const dot = document.getElementById(`dot-${{type}}`);
        if (dot) dot.style.backgroundColor = color;
      }}
    }}
    syncLegend();

    const Graph = ForceGraph3D()(viewport)
      .graphData(gData)
      .backgroundColor(canvasBg)
      .nodeThreeObject(node => {{
        const group = new THREE.Group();
        const radius = Math.max(2.6, (node.val || 4) * 0.7);
        const sphereGeo = new THREE.SphereGeometry(radius, 20, 20);
        
        const pal = PALETTES[currentPaletteKey];
        const baseColor = pal[node.type] || pal['Default'];

        // Pure matte diffuse material (no specular plastic reflections)
        const sphereMat = new THREE.MeshLambertMaterial({{
          color: baseColor,
          transparent: false
        }});
        const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
        group.add(sphereMesh);

        // Labels
        const sprite = new SpriteText(node.name);
        sprite.material.depthWrite = false;
        sprite.color = textSec;
        sprite.textHeight = 3.0;
        sprite.fontFace = fontName;
        sprite.fontWeight = '400';
        sprite.position.y = - (radius + 3.0);
        group.add(sprite);

        node.__mesh = sphereMesh;
        node.__sprite = sprite;
        return group;
      }})
      .linkDirectionalParticles(0)
      .linkLabel(link => link.relation)
      .linkColor(() => borderSubtle)
      .linkWidth(0.7)
      .onNodeClick(node => focusOnNode(node));

    function focusOnNode(node) {{
      const distance = 42;
      const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
      Graph.cameraPosition(
        {{ x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }},
        node,
        1200
      );
    }}

    function applyState() {{
      const pal = PALETTES[currentPaletteKey];
      
      gData.nodes.forEach(node => {{
        if (node.__mesh && node.__sprite) {{
          const baseColor = pal[node.type] || pal['Default'];
          
          if (!currentQuery) {{
            node.__mesh.material.color.set(baseColor);
            node.__mesh.scale.set(1, 1, 1);
            node.__sprite.color = textSec;
            node.__sprite.visible = true;
          }} else if (matchedNodeIds.has(node.id)) {{
            node.__mesh.material.color.set(baseColor);
            node.__mesh.scale.set(1.3, 1.3, 1.3);
            node.__sprite.color = textPri;
            node.__sprite.visible = true;
          }} else {{
            node.__mesh.material.color.set(panelBg);
            node.__mesh.scale.set(0.75, 0.75, 0.75);
            node.__sprite.visible = false;
          }}
        }}
      }});

      Graph.linkColor(link => {{
        if (!currentQuery) return borderSubtle;
        const isConnected = matchedNodeIds.has(link.source.id || link.source) || 
                            matchedNodeIds.has(link.target.id || link.target);
        return isConnected ? textSec : panelBg;
      }});
    }}

    paletteSelect.addEventListener('change', e => {{
      currentPaletteKey = e.target.value;
      syncLegend();
      applyState();
    }});

    searchInput.addEventListener('input', e => {{
      const query = e.target.value.trim().toLowerCase();
      currentQuery = query;
      matchedNodeIds.clear();

      if (query) {{
        gData.nodes.forEach(node => {{
          if (node.name.toLowerCase().includes(query) || (node.type && node.type.toLowerCase().includes(query))) {{
            matchedNodeIds.add(node.id);
          }}
        }});
      }}
      applyState();
    }});

    window.addEventListener('keydown', e => {{
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {{
        e.preventDefault();
        searchInput.focus();
      }}
    }});

    searchInput.addEventListener('keydown', e => {{
      if (e.key === 'Enter' && matchedNodeIds.size > 0) {{
        const firstId = Array.from(matchedNodeIds)[0];
        const targetNode = gData.nodes.find(n => n.id === firstId);
        if (targetNode) focusOnNode(targetNode);
      }}
    }});

    setTimeout(() => {{
      Graph.zoomToFit(800, 35);
    }}, 400);
  </script>
</body>
</html>
"""
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_template)

        return out_file


      