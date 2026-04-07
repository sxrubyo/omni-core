from __future__ import annotations

from dataclasses import dataclass, field

from .architecture import MAIN_CLUSTER_KEYWORDS, SUBAGENT_KEYWORDS, WorkflowArchitecture


@dataclass
class RouteResult:
    cluster_id: str
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    selected_subagents: list[str] = field(default_factory=list)


def _score_keywords(text: str, keywords: set[str]) -> list[str]:
    matches = []
    lowered = text.lower()
    for keyword in sorted(keywords):
        if keyword in lowered:
            matches.append(keyword)
    return matches


def route_message(text: str, architecture: WorkflowArchitecture) -> RouteResult:
    cluster_matches = {
        cluster_id: _score_keywords(text, keywords)
        for cluster_id, keywords in MAIN_CLUSTER_KEYWORDS.items()
    }
    best_cluster = max(cluster_matches, key=lambda cluster_id: len(cluster_matches[cluster_id]))
    matched_keywords = cluster_matches[best_cluster]

    if not matched_keywords:
        best_cluster = "sistema"
        confidence = 0.25
    else:
        confidence = min(0.95, 0.35 + (0.12 * len(matched_keywords)))

    available_subagents = architecture.clusters.get(best_cluster)
    selected_subagents = []
    if available_subagents:
        keyword_map = SUBAGENT_KEYWORDS.get(best_cluster, {})
        for name in available_subagents.subagents:
            for configured_name, keywords in keyword_map.items():
                if configured_name not in name:
                    continue
                if _score_keywords(text, keywords):
                    selected_subagents.append(name)
                    break

        if not selected_subagents:
            selected_subagents = available_subagents.subagents[:2]

    return RouteResult(
        cluster_id=best_cluster,
        confidence=confidence,
        matched_keywords=matched_keywords,
        selected_subagents=selected_subagents,
    )
