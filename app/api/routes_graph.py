
from fastapi import APIRouter
from app.storage.graph_store import PersistentGraphStore
from app.config import DESIGN_TOKENS

router = APIRouter(prefix="/graph", tags=["Graph"])
graph_store = PersistentGraphStore()


@router.get("/data")
def get_graph_visualization_data():

    g = graph_store.graph
    palette = DESIGN_TOKENS["palettes"]["zinc"]
    default_color = palette.get("Default", "#71717a")

    nodes = []
    for node_id, attrs in g.nodes(data=True):
        node_type = attrs.get("type", "Default")
        nodes.append({
            "id": node_id,
            "label": str(node_id),
            "type": node_type,
            "color": palette.get(node_type, default_color),
            "degree": g.degree(node_id),
            "metadata": attrs
        })

    links = []
    for source, target, attrs in g.edges(data=True):
        links.append({
            "source": source,
            "target": target,
            "relation": attrs.get("relation", "RELATION"),
            "metadata": attrs
        })

    return {
        "nodes": nodes,
        "links": links,
        "stats": graph_store.get_stats(),
        "tokens": {
            "canvas": DESIGN_TOKENS["surface"]["canvas"],
            "palette": palette
        }
    }