from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.statreportbuilder.core.blocks import BLOCK_REGISTRY, Block


@dataclass
class Edge:
    src_node: str
    src_port: str
    dst_node: str
    dst_port: str


DEFAULT_RENDER_SETTINGS: dict[str, Any] = {
    "font_family": "Arial, sans-serif",
    "font_size_pt": 11,
    "page_format": "A4",
}


@dataclass
class Graph:
    nodes: dict[str, Block] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    render_settings: dict[str, Any] = field(
        default_factory=lambda: dict(DEFAULT_RENDER_SETTINGS)
    )
    block_overrides: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "nodes": {
                nid: {"type": block.type_id, "params": block.params}
                for nid, block in self.nodes.items()
            },
            "edges": [
                {
                    "src_node": e.src_node,
                    "src_port": e.src_port,
                    "dst_node": e.dst_node,
                    "dst_port": e.dst_port,
                }
                for e in self.edges
            ],
            "positions": {nid: list(pos) for nid, pos in self.positions.items()},
            "render_settings": dict(self.render_settings),
            "block_overrides": {
                nid: dict(overrides) for nid, overrides in self.block_overrides.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> Graph:
        nodes: dict[str, Block] = {}
        for nid, ndata in data.get("nodes", {}).items():
            block_cls = BLOCK_REGISTRY[ndata["type"]]
            nodes[nid] = block_cls(nid, params=dict(ndata.get("params", {})))
        edges = [
            Edge(e["src_node"], e["src_port"], e["dst_node"], e["dst_port"])
            for e in data.get("edges", [])
        ]
        positions = {nid: tuple(pos) for nid, pos in data.get("positions", {}).items()}
        render_settings = dict(DEFAULT_RENDER_SETTINGS)
        render_settings.update(data.get("render_settings") or {})

        block_overrides: dict[str, dict[str, str]] = {
            nid: dict(overrides)
            for nid, overrides in (data.get("block_overrides") or {}).items()
        }
        for nid, narrative in (data.get("draft_text") or {}).items():
            if not narrative:
                continue
            block_overrides.setdefault(nid, {}).setdefault("narrative", narrative)

        return cls(
            nodes=nodes,
            edges=edges,
            positions=positions,
            render_settings=render_settings,
            block_overrides=block_overrides,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> Graph:
        return cls.from_dict(json.loads(path.read_text()))

    def in_edges(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.dst_node == node_id]

    def topological_order(self) -> list[str]:
        in_edges_by_node: dict[str, list[Edge]] = {nid: [] for nid in self.nodes}
        for e in self.edges:
            if e.dst_node in in_edges_by_node:
                in_edges_by_node[e.dst_node].append(e)

        order: list[str] = []
        visited: set[str] = set()

        def visit(nid: str, stack: set[str]) -> None:
            if nid in visited or nid not in self.nodes:
                return
            if nid in stack:
                return
            stack.add(nid)
            for e in in_edges_by_node.get(nid, []):
                visit(e.src_node, stack)
            stack.discard(nid)
            visited.add(nid)
            order.append(nid)

        for nid in self.nodes:
            visit(nid, set())
        return order

    def execute(self, context: dict[str, Any]) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for nid in self.topological_order():
            block = self.nodes[nid]
            inputs: dict[str, Any] = {}
            for e in self.in_edges(nid):
                src_outputs = results.get(e.src_node) or {}
                if "_error" in src_outputs:
                    inputs[e.dst_port] = None
                else:
                    inputs[e.dst_port] = src_outputs.get(e.src_port)
            try:
                results[nid] = block.execute(inputs, context)
            except Exception as exc:
                results[nid] = {
                    "_error": str(exc),
                    "_traceback": traceback.format_exc(),
                }
        return results
