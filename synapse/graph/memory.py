"""Pure in-memory knowledge graph implementation for Synapse."""

from __future__ import annotations

from synapse.graph.networkx_store import NetworkXGraph


class InMemoryGraph(NetworkXGraph):
    """Ephemeral knowledge graph residing purely in RAM with zero disk footprints."""

    def __init__(self, palette: dict[str, str] | None = None) -> None:
        super().__init__(filepath=None, palette=palette)


def in_memory_graph(palette: dict[str, str] | None = None) -> InMemoryGraph:
    """Factory helper creating an in-memory knowledge graph."""
    return InMemoryGraph(palette=palette)


__all__ = ["InMemoryGraph", "in_memory_graph"]
