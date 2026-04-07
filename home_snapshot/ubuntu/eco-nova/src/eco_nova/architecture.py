from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


MAIN_CLUSTER_KEYWORDS = {
    "vida": {
        "habito",
        "habitos",
        "agenda",
        "recordatorio",
        "recordatorios",
        "calendario",
        "rutina",
        "planeacion",
        "plan",
        "auditoria",
        "tribunal",
        "deuda",
        "despertar",
        "push up",
        "cold shower",
        "ingles",
        "deep work",
        "lectura",
    },
    "negocio": {
        "lead",
        "leads",
        "outreach",
        "cold email",
        "campana",
        "prospect",
        "prospecto",
        "instagram",
        "crm",
        "pipeline",
        "revenue",
        "facturacion",
        "venta",
        "ventas",
        "contrato",
        "onboarding",
        "cliente",
        "coach",
        "mentor",
        "realtor",
        "correo",
    },
    "multimedia": {
        "musica",
        "playlist",
        "spotify",
        "youtube",
        "tv",
        "volumen",
        "mute",
        "pausa",
        "skip",
        "dj",
        "android",
        "bateria",
        "alarma",
        "notificacion",
        "netflix",
        "hdmi",
        "cine",
    },
    "sistema": {
        "workflow",
        "workflows",
        "n8n",
        "drive",
        "docs",
        "documento",
        "sheet",
        "sheets",
        "reporte",
        "reportes",
        "menu",
        "ayuda",
        "help",
        "buscar",
        "investiga",
        "noticia",
        "archivo",
        "google",
    },
}


SUBAGENT_KEYWORDS = {
    "sistema": {
        "XUS Flow v1.0 | N8N": {"workflow", "workflows", "n8n", "prompt", "nodo", "activar"},
        "XUS Drive v1.0 - Docs & Files": {
            "drive",
            "docs",
            "documento",
            "archivo",
            "carpeta",
            "sheet",
        },
        "XUS Reports v1.0": {"reporte", "reportes", "dashboard", "resumen", "semanal", "mensual"},
        "XUS Menu v6.0 - Quick Access": {"menu", "help", "ayuda", "/start", "/menu"},
    },
    "negocio": {
        "XUS Hunter v1.0 - Lead Intelligence": {"lead", "leads", "prospecto", "instagram", "buscar"},
        "Xus Outreach Engine - V1.0": {"outreach", "cold email", "campana", "contacta", "prospectar"},
        "XUS Closer v1.0 - Sales & Onboarding": {"cierre", "venta", "contrato", "onboarding", "pago"},
        "XUS Data Core & Intelligence v2.0": {"crm", "revenue", "kpi", "pipeline", "estadistica"},
        "XUS Email Manager v2.0 - Full Gmail": {"correo", "email", "gmail", "bandeja", "responder"},
        "Xus Instagram v1.0 -Sub Agent": {"instagram", "dm", "story", "like", "seguir"},
    },
    "vida": {
        "XUS Habits v2.0 - Dual Agent": {"habito", "habitos", "listo", "hice", "falle", "rutina"},
        "XUS Calendar v3.0 - Full Dynamic": {"agenda", "calendario", "evento", "reunion", "cita"},
        "XUS Remind v1.0 - Smart Alerts": {"recordatorio", "recuerdame", "alarma", "alerta", "follow up"},
    },
    "multimedia": {
        "XUS DJ v10 - Optimized Single Agent": {"musica", "playlist", "spotify", "youtube", "pon"},
        "XUS TV AutoHealing - SSH & LG Controller": {
            "tv",
            "volumen",
            "mute",
            "netflix",
            "youtube tv",
            "hdmi",
            "android",
        },
    },
}


@dataclass
class ClusterArchitecture:
    cluster_id: str
    workflow_name: str
    file_path: str
    prompt_excerpt: str
    subagents: list[str] = field(default_factory=list)


@dataclass
class WorkflowArchitecture:
    workflows_dir: str
    entry_workflows: list[str]
    main_orchestrator: str
    output_engine: str
    ext_workflows: list[str]
    clusters: dict[str, ClusterArchitecture]


def _normalize(value: str) -> str:
    value = value.lower()
    value = value.replace("business", "negocio").replace("bussines", "negocio")
    value = value.replace("life", "vida").replace("system", "sistema")
    return value


def _detect_cluster_id(value: str) -> str:
    normalized = _normalize(value)
    if "vida" in normalized:
        return "vida"
    if "negocio" in normalized:
        return "negocio"
    if "multimedia" in normalized:
        return "multimedia"
    return "sistema"


def _extract_prompt_excerpt(nodes: list[dict]) -> str:
    for node in nodes:
        options = node.get("parameters", {}).get("options", {})
        system_message = options.get("systemMessage")
        if isinstance(system_message, str) and system_message.strip():
            compact = re.sub(r"\s+", " ", system_message.strip())
            return compact[:1800]
    return ""


def discover_architecture(workflows_dir: str | Path) -> WorkflowArchitecture:
    root = Path(workflows_dir)
    input_dir = root / "Input & Output"
    main_agents_dir = root / "Main Agents"
    subagents_dir = root / "Sub X Agents"
    ext_dir = root / "E.X.T"

    entry_workflows = []
    main_orchestrator = ""
    output_engine = ""
    for path in sorted(input_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        name = payload.get("name", path.stem)
        if "Begin" in name:
            entry_workflows.append(name)
        elif "Output Engine" in name:
            output_engine = name
        elif "Orchestrator" in name:
            main_orchestrator = name

    clusters: dict[str, ClusterArchitecture] = {}
    for path in sorted(main_agents_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        name = payload.get("name", path.stem)
        cluster_id = _detect_cluster_id(name)
        clusters[cluster_id] = ClusterArchitecture(
            cluster_id=cluster_id,
            workflow_name=name,
            file_path=str(path),
            prompt_excerpt=_extract_prompt_excerpt(payload.get("nodes", [])),
            subagents=[],
        )

    for path in sorted(subagents_dir.rglob("*.json")):
        cluster_id = _detect_cluster_id(str(path.parent))
        payload = json.loads(path.read_text(encoding="utf-8"))
        name = payload.get("name", path.stem)
        clusters.setdefault(
            cluster_id,
            ClusterArchitecture(
                cluster_id=cluster_id,
                workflow_name=cluster_id.title(),
                file_path="",
                prompt_excerpt="",
            ),
        ).subagents.append(name)

    ext_workflows = []
    for path in sorted(ext_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        ext_workflows.append(payload.get("name", path.stem))

    return WorkflowArchitecture(
        workflows_dir=str(root),
        entry_workflows=entry_workflows,
        main_orchestrator=main_orchestrator,
        output_engine=output_engine,
        ext_workflows=ext_workflows,
        clusters=clusters,
    )
