"""
Fraud ring / shared-entity network using NetworkX.

Claims are nodes; edges connect claims sharing high-specificity entities
(phone, bank account, address, VIN). Repair shop alone is too common to
link every pair — it only reinforces an existing edge or links small buckets.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

import networkx as nx

# High-specificity entities: always link pairs that share these
PRIMARY_ENTITY_FIELDS = (
    ("claimant_phone", "phone"),
    ("bank_account", "bank_account"),
    ("claimant_address", "address"),
    ("vehicle_vin", "vin"),
)

# Low-specificity: only form edges when the shared bucket is small
SECONDARY_ENTITY_FIELDS = (("repair_shop", "repair_shop"),)
SECONDARY_MAX_BUCKET = 25


def _entity_value(claim: Any, field: str) -> str | None:
    value = getattr(claim, field, None) if not isinstance(claim, dict) else claim.get(field)
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"unknown", "none", "n/a"}:
        return None
    return text


def _claim_id(claim: Any) -> int:
    return int(claim.id if not isinstance(claim, dict) else claim["id"])


def _add_bucket_edges(
    graph: nx.Graph,
    buckets: dict[str, list[int]],
    entity_type: str,
    max_bucket: int | None = None,
) -> None:
    for value, ids in buckets.items():
        if len(ids) < 2:
            continue
        if max_bucket is not None and len(ids) > max_bucket:
            # Popular values (e.g. busy repair shops) are not discriminative alone
            continue
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if graph.has_edge(a, b):
                    shared = graph[a][b].setdefault("shared_entities", [])
                    shared.append({"type": entity_type, "value": value})
                else:
                    graph.add_edge(
                        a,
                        b,
                        shared_entities=[{"type": entity_type, "value": value}],
                    )


def build_claim_graph(claims: Sequence[Any]) -> nx.Graph:
    graph = nx.Graph()
    for claim in claims:
        cid = _claim_id(claim)
        score = (
            getattr(claim, "fraud_score", None)
            if not isinstance(claim, dict)
            else claim.get("fraud_score")
        )
        name = (
            getattr(claim, "claimant_name", "")
            if not isinstance(claim, dict)
            else claim.get("claimant_name", "")
        )
        policy = (
            getattr(claim, "policy_number", None)
            if not isinstance(claim, dict)
            else claim.get("policy_number")
        )
        graph.add_node(
            cid,
            claim_id=cid,
            claimant_name=name,
            fraud_score=score,
            policy_number=policy,
        )

    for field, entity_type in PRIMARY_ENTITY_FIELDS:
        buckets: dict[str, list[int]] = defaultdict(list)
        for claim in claims:
            value = _entity_value(claim, field)
            if value is None:
                continue
            buckets[value].append(_claim_id(claim))
        _add_bucket_edges(graph, buckets, entity_type)

    for field, entity_type in SECONDARY_ENTITY_FIELDS:
        buckets = defaultdict(list)
        for claim in claims:
            value = _entity_value(claim, field)
            if value is None:
                continue
            buckets[value].append(_claim_id(claim))
        _add_bucket_edges(graph, buckets, entity_type, max_bucket=SECONDARY_MAX_BUCKET)

    return graph


def find_fraud_rings(graph: nx.Graph, min_size: int = 3) -> list[list[int]]:
    rings: list[list[int]] = []
    for component in nx.connected_components(graph):
        if len(component) >= min_size:
            rings.append(sorted(component))
    return rings


def graph_to_payload(
    graph: nx.Graph,
    focus_claim_id: int | None = None,
    neighborhood_only: bool = False,
) -> dict[str, Any]:
    """Serialize graph (or ego neighborhood) for frontend force-graph rendering."""
    if focus_claim_id is not None and focus_claim_id not in graph:
        return {"nodes": [], "edges": [], "rings": [], "focus_claim_id": focus_claim_id}

    if neighborhood_only and focus_claim_id is not None:
        component = nx.node_connected_component(graph, focus_claim_id)
        sub = graph.subgraph(component).copy()
    else:
        sub = graph

    nodes = []
    for node_id, data in sub.nodes(data=True):
        nodes.append(
            {
                "id": node_id,
                "claim_id": node_id,
                "label": data.get("claimant_name") or f"Claim {node_id}",
                "fraud_score": data.get("fraud_score"),
                "policy_number": data.get("policy_number"),
                "is_focus": focus_claim_id is not None and node_id == focus_claim_id,
            }
        )

    edges = []
    for source, target, data in sub.edges(data=True):
        edges.append(
            {
                "source": source,
                "target": target,
                "shared_entities": data.get("shared_entities", []),
            }
        )

    rings = find_fraud_rings(sub, min_size=3)
    return {
        "nodes": nodes,
        "edges": edges,
        "rings": [{"claim_ids": r, "size": len(r)} for r in rings],
        "focus_claim_id": focus_claim_id,
    }


def build_network_payload(
    claims: Sequence[Any],
    focus_claim_id: int | None = None,
) -> dict[str, Any]:
    graph = build_claim_graph(claims)
    return graph_to_payload(
        graph,
        focus_claim_id=focus_claim_id,
        neighborhood_only=focus_claim_id is not None,
    )
