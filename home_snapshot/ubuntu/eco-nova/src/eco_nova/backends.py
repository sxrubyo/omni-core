from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import tempfile
import uuid
import urllib.error
import urllib.request
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path

from .config import AgentConfig


class BackendError(RuntimeError):
    """Backend execution failure."""


@dataclass
class BackendResult:
    provider: str
    text: str


def _resolve_openai_api_key(config: AgentConfig) -> str:
    if config.backend.openai_api_key.strip():
        return config.backend.openai_api_key.strip()
    return os.environ.get(config.backend.openai_api_key_env, "").strip()


def _openai_request(config: AgentConfig, path: str, payload: bytes, content_type: str) -> dict:
    api_key = _resolve_openai_api_key(config)
    if not api_key:
        raise BackendError(
            f"Falta la credencial de OpenAI. Configura backend.openai_api_key o {config.backend.openai_api_key_env}."
        )
    request = urllib.request.Request(
        url=f"{config.backend.openai_base_url.rstrip('/')}/{path.lstrip('/')}",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.backend.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise BackendError(f"OpenAI devolvio HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise BackendError(f"No pude conectar con OpenAI: {error}") from error


def _parse_openai_output(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    outputs = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                outputs.append(text.strip())
    return "\n".join(outputs).strip()


def _openai_generate(config: AgentConfig, system_prompt: str, user_prompt: str) -> BackendResult:
    request_payload = {
        "model": config.backend.openai_model,
        "instructions": system_prompt,
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            }
        ],
    }
    payload = _openai_request(
        config,
        "/responses",
        json.dumps(request_payload).encode("utf-8"),
        "application/json",
    )
    text = _parse_openai_output(payload)
    if not text:
        raise BackendError("OpenAI respondio sin texto util.")
    return BackendResult(provider="openai", text=text)


def _run_codex_prompt(
    config: AgentConfig,
    system_prompt: str,
    user_prompt: str,
    image_paths: list[str] | None = None,
) -> BackendResult:
    prompt = (
        f"{system_prompt}\n\n"
        "Instruccion operativa adicional:\n"
        "- Si el mensaje es una consulta, responde sin modificar archivos.\n"
        "- Si el mensaje pide ejecutar o programar algo, puedes actuar dentro del workspace.\n"
        "- No menciones herramientas internas ni la arquitectura del runtime.\n\n"
        f"{user_prompt}"
    )
    with tempfile.NamedTemporaryFile("r+", encoding="utf-8", delete=False) as handle:
        output_path = handle.name

    command = ["codex"]
    if config.backend.codex_search:
        command.append("--search")
    command.extend(
        [
            "exec",
        ]
    )
    for image_path in image_paths or []:
        command.extend(["-i", image_path])
    command.extend(
        [
            "--skip-git-repo-check",
            "--full-auto",
            "--sandbox",
            config.backend.codex_sandbox,
            "--color",
            "never",
            "-C",
            config.backend.codex_workdir,
            "-o",
            output_path,
            "-",
        ]
    )
    if config.backend.codex_model.strip():
        command.extend(["--model", config.backend.codex_model.strip()])

    try:
        subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=config.backend.timeout_seconds,
            check=True,
        )
    except FileNotFoundError as error:
        raise BackendError("No encontre el binario `codex`.") from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        detail = stderr or stdout or "sin detalle"
        raise BackendError(f"Codex fallo: {detail}") from error
    except subprocess.TimeoutExpired as error:
        raise BackendError("Codex excedio el tiempo maximo configurado.") from error

    try:
        text = os.path.exists(output_path) and open(output_path, encoding="utf-8").read().strip()
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)
    if not text:
        raise BackendError("Codex termino sin devolver texto.")
    return BackendResult(provider="codex", text=text)


def _codex_generate(config: AgentConfig, system_prompt: str, user_prompt: str) -> BackendResult:
    return _run_codex_prompt(config, system_prompt, user_prompt)


def _file_to_data_url(path: str) -> str:
    source = Path(path)
    if not source.exists():
        raise BackendError(f"No existe la imagen: {path}")
    mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    encoded = b64encode(source.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def generate_vision_response(
    config: AgentConfig,
    system_prompt: str,
    user_prompt: str,
    image_paths: list[str],
) -> BackendResult:
    if not image_paths:
        raise BackendError("No se recibieron imagenes para analizar.")

    backend_type = config.backend.type.strip().lower()
    openai_key = _resolve_openai_api_key(config)
    use_openai = backend_type == "openai" or (backend_type == "auto" and bool(openai_key))

    if use_openai:
        content = [{"type": "input_text", "text": user_prompt}]
        for path in image_paths:
            content.append({"type": "input_image", "image_url": _file_to_data_url(path)})
        request_payload = {
            "model": config.backend.openai_model,
            "instructions": system_prompt,
            "input": [{"role": "user", "content": content}],
        }
        payload = _openai_request(
            config,
            "/responses",
            json.dumps(request_payload).encode("utf-8"),
            "application/json",
        )
        text = _parse_openai_output(payload)
        if not text:
            raise BackendError("OpenAI respondio sin texto util para la imagen.")
        return BackendResult(provider="openai", text=text)

    return _run_codex_prompt(config, system_prompt, user_prompt, image_paths=image_paths)


def transcribe_audio(config: AgentConfig, audio_path: str, prompt: str = "") -> BackendResult:
    api_key = _resolve_openai_api_key(config)
    if not api_key:
        raise BackendError(
            f"Escuchar audio requiere OpenAI. Configura {config.backend.openai_api_key_env} o backend.openai_api_key."
        )

    source = Path(audio_path)
    if not source.exists():
        raise BackendError(f"No existe el audio: {audio_path}")

    boundary = f"eco-nova-{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    body = bytearray()

    def add_field(name: str, value: str) -> None:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    def add_file(name: str, file_path: Path) -> None:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{name}"; filename="{file_path.name}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode("utf-8")
        )
        body.extend(file_path.read_bytes())
        body.extend(b"\r\n")

    add_field("model", config.backend.openai_transcription_model)
    if prompt.strip():
        add_field("prompt", prompt.strip())
    add_file("file", source)
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    payload = _openai_request(
        config,
        "/audio/transcriptions",
        bytes(body),
        f"multipart/form-data; boundary={boundary}",
    )
    text = str(payload.get("text", "")).strip()
    if not text:
        raise BackendError("OpenAI no devolvio transcripcion.")
    return BackendResult(provider="openai", text=text)


def generate_response(config: AgentConfig, system_prompt: str, user_prompt: str) -> BackendResult:
    backend_type = config.backend.type.strip().lower()
    if backend_type == "openai":
        return _openai_generate(config, system_prompt, user_prompt)
    if backend_type == "codex":
        return _codex_generate(config, system_prompt, user_prompt)
    if backend_type != "auto":
        raise BackendError(f"Backend no soportado: {config.backend.type}")

    openai_key = _resolve_openai_api_key(config)
    if openai_key:
        return _openai_generate(config, system_prompt, user_prompt)
    return _codex_generate(config, system_prompt, user_prompt)
