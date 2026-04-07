# Eco Nova - N8N Skills Bridge
import json
import subprocess

WORKFLOWS = {
    "sistema": "uiA2Je1w6ibk2iqI",
    "negocio": "AcnaP8ypOtGJVyVd",
    "vida": "andjL6JoJOKzui8c",
    "multimedia": "xAXieFARpTgqpURi"
}

def trigger_workflow(cluster, payload):
    """Triggers an n8n workflow via its ID."""
    wf_id = WORKFLOWS.get(cluster)
    if not wf_id:
        return {"error": f"Cluster {cluster} no encontrado."}
    
    # Using local n8n CLI to execute if possible, or curl
    # For now, we simulate the execution as a skill command
    return f"Triggered {cluster} with ID {wf_id}"

# This file serves as a registry for ruflo-based specialized agents.
