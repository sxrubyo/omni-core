#!/usr/bin/env python3
"""
melissa-omni.py  —  El Ojo que Todo lo Ve

La instancia personal de Santiago. No habla con pacientes.
Solo habla con Santiago y vigila todo lo demás.

QUÉ HACE:
  • Monitorea todas las instancias Melissa en tiempo real
  • Recibe eventos de cada instancia (nuevo chat, WhatsApp conectado, error)
  • Notifica a Santiago por Telegram cuando algo pasa
  • Santiago le pregunta en lenguaje natural: "cómo va clinica-bella?"
  • Puede enviar mensajes a cualquier instancia directamente
  • Detecta instancias caídas y alerta de inmediato
  • Genera resúmenes diarios automáticos
  • Gestiona solicitudes de nuevos números WhatsApp

MODOS:
  python3 melissa-omni.py server    →  servidor de eventos (puerto 9001)
  python3 melissa-omni.py chat      →  chat terminal con Omni
  python3 melissa-omni.py status    →  estado rápido de todo
  python3 melissa-omni.py watch     →  monitor live en terminal

VARIABLES .env:
  OMNI_PORT=9001
  OMNI_KEY=secreto
  OMNI_TELEGRAM_TOKEN=token_bot_personal_santiago
  SANTIAGO_CHAT_ID=tu_chat_id
  MELISSA_DIR=/home/ubuntu/melissa
  INSTANCES_DIR=/home/ubuntu/melissa-instances
"""

from __future__ import annotations

import asyncio, json, os, sys, re, time, threading, shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import urllib.request

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

try:
    from fastapi import FastAPI, Request, Response, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from contextlib import asynccontextmanager
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    import readline
    readline.set_history_length(200)
except ImportError:
    pass

# ══════════════════════════════════════════════════════════════════════════════
# COLORS — same purple system as melissa-cli
# ══════════════════════════════════════════════════════════════════════════════
def _tty(): return sys.stdout.isatty() or bool(os.getenv("FORCE_COLOR"))
def _e(c):  return f"\033[{c}m" if _tty() else ""

class C:
    R   = _e("0");  BOLD = _e("1"); DIM = _e("2")
    P1  = _e("38;5;183"); P2 = _e("38;5;141"); P3 = _e("38;5;135")
    P4  = _e("38;5;99");  P5 = _e("38;5;57")
    W   = _e("38;5;15");  G0 = _e("38;5;252"); G1 = _e("38;5;248")
    G2  = _e("38;5;244"); G3 = _e("38;5;240"); G4 = _e("38;5;236")
    GRN = _e("38;5;114"); RED = _e("38;5;203")
    YLW = _e("38;5;221"); CYN = _e("38;5;117"); AMB = _e("38;5;179")

def q(color, text, bold=False):
    return f"{C.BOLD if bold else ''}{color}{text}{C.R}"

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
OMNI_VERSION   = "1.0.0"
TEMPLATE_DIR   = os.getenv("MELISSA_DIR",    "/home/ubuntu/melissa")
INSTANCES_DIR  = os.getenv("INSTANCES_DIR",  "/home/ubuntu/melissa-instances")
OMNI_PORT      = int(os.getenv("OMNI_PORT",  "9001"))
OMNI_KEY       = os.getenv("OMNI_KEY",       "omni_secret_change_me")
SANTIAGO_CHAT  = os.getenv("SANTIAGO_CHAT_ID", "")
OMNI_TOKEN     = os.getenv("OMNI_TELEGRAM_TOKEN", "")
NOVA_PORT      = int(os.getenv("NOVA_PORT",  "9002"))

# Alertas: cuántos segundos entre pings de health
HEALTH_INTERVAL = int(os.getenv("OMNI_HEALTH_INTERVAL", "60"))

# ══════════════════════════════════════════════════════════════════════════════
# UI PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════════
def ok(m):   print(f"  {q(C.GRN,'✓')}  {q(C.W,m)}")
def fail(m): print(f"  {q(C.RED,'✗')}  {q(C.W,m)}")
def warn(m): print(f"  {q(C.YLW,'!')}  {q(C.G1,m)}")
def info(m): print(f"  {q(C.P2,'·')}  {q(C.G1,m)}")
def dim(m):  print(f"       {q(C.G3,m)}")
def nl():    print()
def hr():    print("  " + q(C.G3, "─" * 58))

def section(title, sub=""):
    print()
    print("  " + q(C.P1,"✦",bold=True) + "  " + q(C.W,title,bold=True))
    if sub: print("       " + q(C.G2, sub))
    print()

def kv(key, val, color=None):
    c = color or C.P2
    print(f"  {q(C.G2,f'{key:<22}')}  {q(c,str(val))}")

def ghost_write(text, color=None, delay=0.015, prefix="  "):
    import random as _r
    c = color or C.P2
    sys.stdout.write(prefix + C.BOLD + c)
    for ch in text:
        sys.stdout.write(ch); sys.stdout.flush()
        if ch in ".!?":   time.sleep(delay*6)
        elif ch in ",:;": time.sleep(delay*2.5)
        elif ch == " ":   time.sleep(delay)
        else:             time.sleep(delay + _r.uniform(-0.003, 0.006))
    sys.stdout.write(C.R); print()

# Spinner
_SP = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
class Spinner:
    def __init__(self, msg):
        self.msg = msg; self._stop = threading.Event()
    def __enter__(self): self.start(); return self
    def __exit__(self, *a): self.finish()
    def start(self):
        def _r():
            i = 0
            while not self._stop.is_set():
                sys.stdout.write(f"\r  {q(C.P2,_SP[i%len(_SP)])}  {q(C.G1,self.msg)}")
                sys.stdout.flush(); time.sleep(0.08); i += 1
        threading.Thread(target=_r, daemon=True).start()
    def finish(self, msg=None, ok_=True):
        self._stop.set(); time.sleep(0.12)
        icon = q(C.GRN,"✓") if ok_ else q(C.RED,"✗")
        sys.stdout.write(f"\r  {icon}  {q(C.W, msg or self.msg)}\n")
        sys.stdout.flush()

def print_logo(compact=False):
    print()
    if compact:
        print(f"  {q(C.P1,'✦',bold=True)}  {q(C.W,'melissa omni',bold=True)}  "
              f"{q(C.G3,f'v{OMNI_VERSION}')}")
        print()
        return
    rows = [
        ("38;5;183", "  ███╗   ███╗███████╗██╗  ██╗███████╗███████╗ █████╗ "),
        ("38;5;183", "  ████╗ ████║██╔════╝██║  ██║██╔════╝██╔════╝██╔══██╗"),
        ("38;5;141", "  ██╔████╔██║█████╗  ██║  ██║███████╗███████╗███████║"),
        ("38;5;141", "  ██║╚██╔╝██║██╔══╝  ██║  ██║╚════██║╚════██║██╔══██║"),
        ("38;5;99",  "  ██║ ╚═╝ ██║███████╗███████║███████║███████║██║  ██║"),
        ("38;5;99",  "  ╚═╝     ╚═╝╚══════╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝"),
    ]
    for col, row in rows:
        print(f"{C.BOLD}{_e(col)}{row}{C.R}")
    print()
    print(f"  {q(C.AMB,'✦')} {q(C.G2,'OMNI')}  {q(C.G3,'·')}  "
          f"{q(C.G3,'El Ojo que Todo lo Ve')}  "
          f"{q(C.G3,f'v{OMNI_VERSION}')}")
    print(f"  {q(C.G4,'─'*58)}")
    print()

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def load_env(path: str) -> dict:
    env = {}
    try:
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception: pass
    return env

def get_all_instances() -> List[Dict]:
    instances = []
    be = load_env(f"{TEMPLATE_DIR}/.env")
    if be:
        instances.append({"name":"base","label":be.get("CLINIC_NAME","Instancia base"),
            "port":int(be.get("PORT",8001)),"dir":TEMPLATE_DIR,"env":be,"is_base":True})
    if os.path.isdir(INSTANCES_DIR):
        for name in sorted(os.listdir(INSTANCES_DIR)):
            d = f"{INSTANCES_DIR}/{name}"; ep = f"{d}/.env"
            if not os.path.isdir(d) or not os.path.exists(ep): continue
            ev = load_env(ep)
            instances.append({"name":name,"label":name.replace("-"," ").title(),
                "port":int(ev.get("PORT",8002)),"dir":d,"env":ev,"is_base":False})
    return instances

async def _get(url: str, timeout: float = 4.0) -> Optional[Dict]:
    try:
        if _HTTPX:
            r = await httpx.AsyncClient(timeout=timeout).__aenter__().__aexit__
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.get(url)
                return r.json() if r.status_code == 200 else None
        else:
            req = urllib.request.urlopen(url, timeout=int(timeout))
            return json.loads(req.read())
    except Exception: return None

async def _post(url: str, data: dict, headers: dict = None, timeout: float = 8.0) -> Optional[Dict]:
    try:
        if _HTTPX:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.post(url, json=data, headers=headers or {})
                return r.json() if r.status_code == 200 else None
    except Exception: return None

async def health(port: int) -> Dict:
    h = await _get(f"http://localhost:{port}/health")
    return h or {}

async def get_stats(port: int, master_key: str) -> Dict:
    if not _HTTPX: return {}
    try:
        async with httpx.AsyncClient(timeout=8.0) as c:
            r = await c.get(f"http://localhost:{port}/analytics/summary?days=7",
                           headers={"X-Master-Key": master_key})
            return r.json() if r.status_code == 200 else {}
    except Exception: return {}

async def get_recent_chats(port: int, master_key: str, limit: int = 5) -> List[Dict]:
    if not _HTTPX: return []
    try:
        async with httpx.AsyncClient(timeout=6.0) as c:
            r = await c.get(f"http://localhost:{port}/conversations/patients?limit={limit}",
                           headers={"X-Master-Key": master_key})
            return r.json().get("conversations", []) if r.status_code == 200 else []
    except Exception: return []

async def send_to_instance(port: int, master_key: str, chat_id: str, msg: str) -> bool:
    if not _HTTPX: return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(f"http://localhost:{port}/send-message",
                json={"chat_id": chat_id, "message": msg},
                headers={"X-Master-Key": master_key})
            return r.status_code == 200
    except Exception: return False

async def send_telegram(text: str, chat_id: str = None, token: str = None):
    cid = chat_id or SANTIAGO_CHAT
    tok = token or OMNI_TOKEN
    if not cid or not tok: return
    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    try:
        if _HTTPX:
            async with httpx.AsyncClient(timeout=10.0) as c:
                await c.post(url, json={"chat_id": cid, "text": text, "parse_mode": "Markdown"})
        else:
            data = json.dumps({"chat_id": cid, "text": text}).encode()
            req = urllib.request.Request(url, data=data,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"  [omni] telegram error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# LLM  — Omni's brain (same cascade as Melissa)
# ══════════════════════════════════════════════════════════════════════════════
async def omni_brain(user_input: str, history: List[Dict],
                     all_status: List[Dict], base_env: dict) -> str:
    """LLM que sabe el estado de todos los clientes y puede tomar acciones."""

    # Build client summary for context
    lines = []
    for s in all_status:
        h  = s.get("health", {})
        st = s.get("stats",  {})
        ok_ = h.get("status") == "online"
        wa  = h.get("whatsapp", {})
        plat = f"WA {wa.get('phone','')}" if wa.get("connected") else "Telegram"
        convs = st.get("total_conversations", "?")
        apts  = st.get("total_appointments",  "?")
        nova  = "Nova ON" if s.get("env",{}).get("NOVA_ENABLED") == "true" else ""
        lines.append(
            f"  - {s['name']}: {'ONLINE' if ok_ else 'OFFLINE'} | {plat} | "
            f"{convs} convs | {apts} citas esta semana"
            + (f" | {nova}" if nova else "")
        )

    clients_ctx = "\n".join(lines) if lines else "  (sin instancias)"

    pending = _event_queue[-5:] if _event_queue else []
    events_ctx = ""
    if pending:
        events_ctx = "\nEVENTOS RECIENTES:\n" + "\n".join(
            f"  [{e.get('received_at','')[:16]}] {e.get('event','')} — "
            f"{e.get('clinic','')} — {e.get('details','')}"
            for e in pending
        )

    hist_text = "\n".join(
        f"{'Santiago' if h['role']=='user' else 'Omni'}: {h['content'][:150]}"
        for h in history[-8:]
    )

    system = f"""Eres Melissa Omni — el ojo personal de Santiago.
Santiago es el dueño de la plataforma Melissa. Tú eres su asistente ejecutiva.

ESTADO ACTUAL:
{clients_ctx}
{events_ctx}

CONVERSACIÓN:
{hist_text or "(inicio)"}

CÓMO ERES:
- Directa y ejecutiva. Máximo 3 oraciones.
- Cuando Santiago pregunta por un cliente, das el estado completo con números.
- Si hay algo offline o raro, lo mencionas primero.
- Puedes decir exactamente qué pasó basándote en los eventos.
- Hablas español, informal con Santiago.

ACCIONES (incluye al FINAL si necesitas ejecutar algo):
ACTION:{{"type":"detail","client":"nombre"}}
ACTION:{{"type":"send","client":"nombre","chat_id":"...","msg":"..."}}
ACTION:{{"type":"summary_all"}}
ACTION:{{"type":"restart","client":"nombre"}}"""

    messages = [{"role":"system","content":system},
                {"role":"user","content":user_input}]

    providers = []
    if base_env.get("GROQ_API_KEY"):
        providers.append(("groq","https://api.groq.com/openai/v1",
                          base_env["GROQ_API_KEY"],"llama-3.3-70b-versatile"))
    for k in ["GEMINI_API_KEY","GEMINI_API_KEY_2","GEMINI_API_KEY_3"]:
        if base_env.get(k):
            providers.append(("gemini","native",base_env[k],"gemini-2.0-flash"))
    if base_env.get("OPENROUTER_API_KEY"):
        providers.append(("openrouter","https://openrouter.ai/api/v1",
                          base_env["OPENROUTER_API_KEY"],"google/gemini-2.0-flash-001"))

    if not providers:
        return "No hay LLMs configurados en el .env de Melissa."

    for name, base_url, api_key, model in providers:
        try:
            if not _HTTPX: break
            if name == "gemini":
                contents = [{"role":"user" if m["role"]=="user" else "model",
                             "parts":[{"text":m["content"]}]}
                            for m in messages if m["role"] != "system"]
                sys_parts = [m for m in messages if m["role"]=="system"]
                payload = {"contents":contents,
                           "generationConfig":{"temperature":0.3,"maxOutputTokens":400}}
                if sys_parts:
                    payload["systemInstruction"] = {"parts":[{"text":sys_parts[0]["content"]}]}
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                async with httpx.AsyncClient(timeout=18.0) as c:
                    r = await c.post(url, json=payload)
                    r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                async with httpx.AsyncClient(timeout=18.0) as c:
                    r = await c.post(f"{base_url}/chat/completions",
                        headers={"Authorization":f"Bearer {api_key}",
                                 "Content-Type":"application/json"},
                        json={"model":model,"messages":messages,
                              "temperature":0.3,"max_tokens":400})
                    r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue

    return "Sin respuesta de LLM — verifica las API keys."

# ══════════════════════════════════════════════════════════════════════════════
# ACTION EXECUTOR
# ══════════════════════════════════════════════════════════════════════════════
def _extract_action(text: str) -> Optional[Dict]:
    m = re.search(r'ACTION:\s*(\{[^\n]+\})', text)
    if m:
        try: return json.loads(m.group(1))
        except Exception: pass
    return None

def _clean(text: str) -> str:
    return re.sub(r'\nACTION:\s*\{[^\n]+\}', '', text).strip()

async def execute_action(action: Dict, instances: List[Dict], base_env: dict) -> str:
    t = action.get("type","")

    if t == "detail":
        name = action.get("client","")
        inst = next((i for i in instances if name.lower() in i["name"].lower()), None)
        if not inst: return f"No encontré instancia '{name}'"
        h  = await health(inst["port"])
        mk = inst["env"].get("MASTER_API_KEY","")
        st = await get_stats(inst["port"], mk) if h else {}
        ch = await get_recent_chats(inst["port"], mk, 3) if h else []

        wa     = h.get("whatsapp",{})
        plat   = f"WA {wa.get('phone','')}" if wa.get("connected") else "Telegram"
        status = "online" if h.get("status")=="online" else "OFFLINE"
        lines  = [f"*{h.get('clinic',inst['name'])}* — {status} | {plat}"]
        if st:
            lines.append(f"Esta semana: {st.get('total_conversations',0)} convs, "
                        f"{st.get('total_appointments',0)} citas")
            cr = st.get("conversion_rate")
            if cr: lines.append(f"Conversión: {cr}%")
        if ch:
            lines.append("Últimas conversaciones:")
            for c in ch[:3]:
                n = c.get("name") or "Desconocido"
                last = (c.get("last_user_msg") or "")[:50]
                lines.append(f"  • {n}: \"{last}\"")
        return "\n".join(lines)

    if t == "summary_all":
        import concurrent.futures
        hs = await asyncio.gather(*[health(i["port"]) for i in instances])
        online = sum(1 for h in hs if h.get("status")=="online")
        lines = [f"*Resumen {datetime.now().strftime('%d/%m %H:%M')}*",
                 f"Online: {online}/{len(instances)}"]
        for inst, h in zip(instances, hs):
            icon = "🟢" if h.get("status")=="online" else "🔴"
            wa   = "WA" if h.get("whatsapp",{}).get("connected") else "TG"
            lines.append(f"{icon} {inst['name']} ({wa})")
        return "\n".join(lines)

    if t == "restart":
        name = action.get("client","")
        pm2_name = "melissa" if name == "base" else f"melissa-{name}"
        import subprocess
        r = subprocess.run(["pm2","restart",pm2_name], capture_output=True)
        return f"Restarted {pm2_name}" if r.returncode == 0 else f"No encontré {pm2_name}"

    if t == "send":
        name     = action.get("client","")
        chat_id  = action.get("chat_id","")
        msg      = action.get("msg","")
        inst = next((i for i in instances if name.lower() in i["name"].lower()), None)
        if not inst: return f"No encontré instancia '{name}'"
        mk = inst["env"].get("MASTER_API_KEY","")
        ok_ = await send_to_instance(inst["port"], mk, chat_id, msg)
        return f"Mensaje enviado a {name}" if ok_ else "Error enviando mensaje"

    return ""

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH MONITOR — background watcher
# ══════════════════════════════════════════════════════════════════════════════
_down_cache: Dict[str, bool] = {}   # name → was_down

async def health_watcher():
    """Vigila todas las instancias cada HEALTH_INTERVAL segundos.
    Notifica a Santiago cuando algo cae o se recupera."""
    while True:
        await asyncio.sleep(HEALTH_INTERVAL)
        instances = get_all_instances()
        for inst in instances:
            h = await health(inst["port"])
            is_down = h.get("status") != "online" or not h

            was_down = _down_cache.get(inst["name"], False)

            if is_down and not was_down:
                _down_cache[inst["name"]] = True
                msg = (f"⚠️ *{inst.get('label', inst['name'])}* está OFFLINE\n"
                       f"Puerto: {inst['port']}\n"
                       f"Hora: {datetime.now().strftime('%H:%M:%S')}")
                await send_telegram(msg)
                _event_queue.append({
                    "event": "instance_offline", "clinic": inst["name"],
                    "details": f"No responde en :{inst['port']}",
                    "received_at": datetime.now().isoformat()
                })

            elif not is_down and was_down:
                _down_cache[inst["name"]] = False
                msg = (f"✅ *{inst.get('label', inst['name'])}* volvió ONLINE\n"
                       f"Puerto: {inst['port']}")
                await send_telegram(msg)

# ══════════════════════════════════════════════════════════════════════════════
# DAILY SUMMARY — se envía a las 8am
# ══════════════════════════════════════════════════════════════════════════════
async def daily_summary_scheduler():
    """Envía resumen diario a Santiago a las 8:00am."""
    while True:
        now = datetime.now()
        # Calcular próximas 8am
        next_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if now >= next_8am:
            next_8am += timedelta(days=1)
        wait = (next_8am - now).total_seconds()
        await asyncio.sleep(wait)
        await send_daily_summary()

async def send_daily_summary():
    """Construye y envía el resumen diario."""
    instances = get_all_instances()
    base_env  = load_env(f"{TEMPLATE_DIR}/.env")

    hs = await asyncio.gather(*[health(i["port"]) for i in instances])
    online = sum(1 for h in hs if h.get("status")=="online")

    lines = [
        f"📊 *Resumen diario — {datetime.now().strftime('%d/%m/%Y')}*",
        f"",
        f"Instancias: {online}/{len(instances)} online",
    ]

    total_convs = 0
    total_apts  = 0

    for inst, h in zip(instances, hs):
        mk = inst["env"].get("MASTER_API_KEY","")
        if h.get("status") == "online":
            st = await get_stats(inst["port"], mk)
            c  = st.get("total_conversations", 0)
            a  = st.get("total_appointments", 0)
            total_convs += c
            total_apts  += a
            wa   = h.get("whatsapp",{})
            plat = "WA" if wa.get("connected") else "TG"
            lines.append(f"  {'🟢'} {inst['name']} ({plat}) — {c} convs, {a} citas")
        else:
            lines.append(f"  🔴 {inst['name']} — OFFLINE")

    lines += [
        f"",
        f"Total: {total_convs} conversaciones, {total_apts} citas",
    ]

    if _event_queue:
        recent = [e for e in _event_queue
                  if datetime.fromisoformat(e.get("received_at","2000-01-01"))
                  > datetime.now() - timedelta(hours=24)]
        if recent:
            lines.append(f"\nEventos (últimas 24h): {len(recent)}")
            for e in recent[-3:]:
                lines.append(f"  • {e.get('event','')} — {e.get('clinic','')}")

    await send_telegram("\n".join(lines))

# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI — servidor de eventos
# ══════════════════════════════════════════════════════════════════════════════
_event_queue: List[Dict] = []
_santiago_history: List[Dict] = []

if HAS_FASTAPI:
    @asynccontextmanager
    async def lifespan(app_: FastAPI):
        # Arrancar watchers en background
        asyncio.create_task(health_watcher())
        asyncio.create_task(daily_summary_scheduler())
        print_logo(compact=True)
        info(f"Omni server online — puerto {OMNI_PORT}")
        if OMNI_TOKEN:
            ok("Bot de Telegram configurado")
        else:
            warn("OMNI_TELEGRAM_TOKEN no configurado — sin notificaciones Telegram")
        nl()
        yield

    omni_app = FastAPI(title="Melissa Omni", version=OMNI_VERSION, lifespan=lifespan)
    omni_app.add_middleware(CORSMiddleware, allow_origins=["*"],
                            allow_methods=["*"], allow_headers=["*"])

    def _auth(request: Request) -> bool:
        return request.headers.get("X-Omni-Key","") == OMNI_KEY

    @omni_app.get("/health")
    async def omni_health():
        instances = get_all_instances()
        hs = await asyncio.gather(*[health(i["port"]) for i in instances])
        online = sum(1 for h in hs if h.get("status")=="online")
        return {"status":"online","version":OMNI_VERSION,
                "instances":len(instances),"online":online,
                "events":len(_event_queue)}

    @omni_app.post("/omni/event")
    async def receive_event(request: Request, bg: BackgroundTasks):
        """Recibe eventos de instancias de clientes."""
        if not _auth(request):
            return Response(status_code=403)
        data = await request.json()
        data["received_at"] = datetime.now().isoformat()
        _event_queue.append(data)
        # Guardar solo los últimos 500
        if len(_event_queue) > 500:
            _event_queue[:] = _event_queue[-500:]

        event = data.get("event","")
        clinic = data.get("clinic","")
        details = data.get("details","")

        # Alertas inmediatas para eventos críticos
        CRITICAL = {"new_whatsapp_number_requested","instance_error",
                    "client_complaint","reset_sesion","instancia_eliminada"}
        if event in CRITICAL:
            emoji_map = {
                "new_whatsapp_number_requested": "📱",
                "instance_error":                "🔥",
                "client_complaint":              "⚠️",
                "reset_sesion":                  "🔄",
                "instancia_eliminada":           "🗑️",
            }
            emoji = emoji_map.get(event, "📌")
            msg = f"{emoji} *{clinic}*\n{details}"
            bg.add_task(send_telegram, msg)

        return {"ok": True, "queued": len(_event_queue)}

    @omni_app.get("/omni/events")
    async def list_events(request: Request, limit: int = 20):
        if not _auth(request):
            return Response(status_code=403)
        return {"events": _event_queue[-limit:], "total": len(_event_queue)}

    @omni_app.get("/omni/status")
    async def omni_status_endpoint():
        instances = get_all_instances()
        hs = await asyncio.gather(*[health(i["port"]) for i in instances])
        return {
            "timestamp": datetime.now().isoformat(),
            "instances": [
                {"name": i["name"], "port": i["port"],
                 "status": h.get("status","offline"),
                 "clinic": h.get("clinic",""),
                 "whatsapp": h.get("whatsapp",{}),
                 "nova_enabled": i["env"].get("NOVA_ENABLED","false")}
                for i, h in zip(instances, hs)
            ]
        }

    @omni_app.post("/omni/message/{name}")
    async def send_message_to_client(name: str, request: Request):
        """Enviar mensaje directo a un paciente de una instancia."""
        if not _auth(request):
            return Response(status_code=403)
        data = await request.json()
        chat_id = data.get("chat_id","")
        msg = data.get("message","")
        instances = get_all_instances()
        inst = next((i for i in instances if name.lower() in i["name"].lower()), None)
        if not inst:
            return {"ok": False, "error": f"No encontré '{name}'"}
        ok_ = await send_to_instance(
            inst["port"], inst["env"].get("MASTER_API_KEY",""), chat_id, msg)
        return {"ok": ok_}

    @omni_app.post("/omni/webhook/{token_suffix}")
    async def telegram_webhook(token_suffix: str, request: Request, bg: BackgroundTasks):
        """Webhook de Telegram para el bot personal de Santiago."""
        if OMNI_TOKEN and not OMNI_TOKEN.endswith(token_suffix):
            return Response(status_code=403)
        body = await request.json()
        msg  = body.get("message",{})
        if not msg: return {"ok": True}
        chat_id = str(msg.get("chat",{}).get("id",""))
        text    = msg.get("text","").strip()
        if not text: return {"ok": True}
        # Solo Santiago puede hablar con Omni
        if SANTIAGO_CHAT and chat_id != str(SANTIAGO_CHAT):
            return {"ok": True}
        bg.add_task(_handle_telegram_message, chat_id, text)
        return {"ok": True}

async def _handle_telegram_message(chat_id: str, text: str):
    """Procesa un mensaje de Santiago y responde."""
    instances = get_all_instances()
    base_env  = load_env(f"{TEMPLATE_DIR}/.env")

    # Health de todas en paralelo
    hs = await asyncio.gather(*[health(i["port"]) for i in instances])
    all_status = [{"name":i["name"],"label":i.get("label",""),
                   "port":i["port"],"env":i["env"],
                   "health":h,"stats":{}}
                  for i,h in zip(instances,hs)]

    reply = await omni_brain(text, _santiago_history, all_status, base_env)
    action = _extract_action(reply)
    clean_reply = _clean(reply)

    await send_telegram(clean_reply, chat_id)

    if action:
        result = await execute_action(action, instances, base_env)
        if result:
            await send_telegram(result, chat_id)

    _santiago_history.append({"role":"user","content":text})
    _santiago_history.append({"role":"assistant","content":clean_reply})
    if len(_santiago_history) > 20:
        _santiago_history[:] = _santiago_history[-20:]

# ══════════════════════════════════════════════════════════════════════════════
# CLI COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_status():
    print_logo(compact=True)
    section("Estado de instancias")
    instances = get_all_instances()
    if not instances:
        warn("No hay instancias configuradas."); return
    hs = await asyncio.gather(*[health(i["port"]) for i in instances])
    online = sum(1 for h in hs if h.get("status")=="online")
    print(f"  {q(C.G2,'Online:')}  "
          f"{q(C.GRN if online==len(instances) else C.YLW, f'{online}/{len(instances)}')}")
    nl()
    for inst, h in zip(instances, hs):
        is_up  = h.get("status")=="online"
        icon   = q(C.GRN,"●") if is_up else q(C.RED,"●")
        clinic = h.get("clinic", inst["label"])
        wa     = h.get("whatsapp",{})
        plat   = f"WA {wa.get('phone','')[-8:]}" if wa.get("connected") else "Telegram"
        nova   = q(C.P3,"  ✦Nova") if inst["env"].get("NOVA_ENABLED")=="true" else ""
        mem    = h.get("memory_items","")
        print(f"  {icon}  {q(C.W,clinic,bold=True)}{nova}")
        print(f"       {q(C.G2,inst['name'])}  ·  :{inst['port']}  ·  "
              f"{q(C.G1,plat)}"
              + (f"  {q(C.G3,str(mem)+' mem')}" if mem else ""))
        nl()


async def cmd_watch():
    """Monitor live que refresca cada 5 segundos."""
    info("Watch mode — Ctrl+C para salir")
    try:
        while True:
            os.system("clear")
            instances = get_all_instances()
            hs = await asyncio.gather(*[health(i["port"]) for i in instances])
            online = sum(1 for h in hs if h.get("status")=="online")
            now = datetime.now().strftime("%H:%M:%S")

            print(f"\n  {q(C.P1,'✦',bold=True)}  {q(C.W,'Melissa Omni',bold=True)}  "
                  f"{q(C.G3,now)}  "
                  f"{q(C.GRN if online==len(instances) else C.YLW, f'{online}/{len(instances)} online')}")
            print("  " + q(C.G3,"─"*58))

            HDR = f"{'INSTANCIA':<24}{'ESTADO':<10}{'PLATAFORMA':<20}{'NOVA':<8}"
            print(f"  {q(C.G3,HDR)}")

            for inst, h in zip(instances, hs):
                is_up  = h.get("status")=="online"
                icon   = q(C.GRN,"●") if is_up else q(C.RED,"●")
                clinic = (h.get("clinic") or inst["label"])[:22]
                wa     = h.get("whatsapp",{})
                plat   = ("WA "+wa.get("phone","")[-8:]) if wa.get("connected") else "Telegram"
                nova   = q(C.P3,"✦") if inst["env"].get("NOVA_ENABLED")=="true" else q(C.G3,"—")
                status = "online" if is_up else "OFFLINE"
                print(f"  {icon}  {q(C.W,f'{clinic:<24}')}"
                      f"{q(C.GRN if is_up else C.RED,f'{status:<10}')}"
                      f"{q(C.G1,f'{plat:<20}')}{nova}")

            if _event_queue:
                print()
                print(f"  {q(C.G2,'Últimos eventos:')}")
                for e in _event_queue[-3:]:
                    ts  = e.get("received_at","")[:16]
                    ev  = e.get("event","")
                    cli = e.get("clinic","")
                    print(f"  {q(C.G3,ts)}  {q(C.G1,ev)}  {q(C.G3,cli)}")

            print()
            print(f"  {q(C.G3,'refresca cada 5s · Ctrl+C para salir')}")
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        pass


async def cmd_chat():
    """Chat interactivo con Omni desde terminal."""
    import readline as rl
    print_logo()
    instances = get_all_instances()
    hs = await asyncio.gather(*[health(i["port"]) for i in instances])
    online = sum(1 for h in hs if h.get("status")=="online")

    all_status = [{"name":i["name"],"label":i.get("label",""),
                   "port":i["port"],"env":i["env"],
                   "health":h,"stats":{}}
                  for i,h in zip(instances,hs)]

    base_env = load_env(f"{TEMPLATE_DIR}/.env")
    history: List[Dict] = []

    ghost_write(f"{online}/{len(instances)} instancias online. Pregúntame lo que necesites.", C.G1)
    ghost_write("Comandos: /status  /watch  /summary  /events  /exit", C.G3, delay=0.01)
    nl()

    while True:
        try:
            sys.stdout.write(f"  {q(C.AMB,'Santiago',bold=True)} {q(C.P3,'›')} ")
            sys.stdout.flush()
            text = input("").strip()
        except (EOFError, KeyboardInterrupt):
            nl(); info("Hasta luego."); break

        if not text: continue

        if text in ("/exit","exit","salir","q"): info("Hasta luego."); break
        if text == "/status":
            await cmd_status(); continue
        if text == "/watch":
            try: await cmd_watch()
            except KeyboardInterrupt: pass
            continue
        if text == "/summary":
            await send_daily_summary()
            info("Resumen enviado a Telegram"); continue
        if text == "/events":
            if not _event_queue:
                info("Sin eventos recientes")
            else:
                for e in _event_queue[-10:]:
                    ts = e.get("received_at","")[:16]
                    print(f"  {q(C.G3,ts)}  {q(C.G1,e.get('event',''))}  "
                          f"{q(C.P2,e.get('clinic',''))}  {q(C.G3,e.get('details','')[:50])}")
            continue

        # LLM
        print()
        # Quick spinner in main thread
        sys.stdout.write(f"  {q(C.P2,'·')}  {q(C.G3,'pensando...')}"); sys.stdout.flush()

        reply = await omni_brain(text, history, all_status, base_env)
        action = _extract_action(reply)
        clean  = _clean(reply)

        sys.stdout.write(f"\r  {q(C.AMB,'✦')}  {q(C.W,'Omni',bold=True)}\n")
        ghost_write(clean, C.G0, delay=0.012)

        if action:
            result = await execute_action(action, instances, base_env)
            if result:
                nl()
                for line in result.split("\n"):
                    print(f"       {q(C.G1,line)}")

        nl()
        history.append({"role":"user","content":text})
        history.append({"role":"assistant","content":clean})
        if len(history) > 16: history[:] = history[-16:]

        # Refresh status every 5 turns
        if len(history) % 10 == 0:
            hs = await asyncio.gather(*[health(i["port"]) for i in instances])
            all_status = [{"name":i["name"],"label":i.get("label",""),
                           "port":i["port"],"env":i["env"],
                           "health":h,"stats":{}}
                          for i,h in zip(instances,hs)]

# ══════════════════════════════════════════════════════════════════════════════
# WEBHOOK SETUP — registrar el webhook de Telegram
# ══════════════════════════════════════════════════════════════════════════════
async def setup_telegram_webhook(base_url: str):
    if not OMNI_TOKEN or not base_url:
        warn("OMNI_TELEGRAM_TOKEN o BASE_URL no configurados"); return
    token_suffix = OMNI_TOKEN.split(":")[-1][:10]
    webhook_url  = f"{base_url.rstrip('/')}/omni/webhook/{token_suffix}"
    url = f"https://api.telegram.org/bot{OMNI_TOKEN}/setWebhook"
    try:
        if _HTTPX:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(url, json={"url": webhook_url})
                if r.json().get("ok"):
                    ok(f"Webhook Telegram configurado: {webhook_url}")
                else:
                    warn(f"Webhook error: {r.text[:100]}")
    except Exception as e:
        warn(f"No pude configurar webhook: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "server"

    if cmd == "status":
        asyncio.run(cmd_status())

    elif cmd == "watch":
        asyncio.run(cmd_watch())

    elif cmd == "chat":
        asyncio.run(cmd_chat())

    elif cmd == "summary":
        asyncio.run(send_daily_summary())
        info("Resumen enviado")

    elif cmd == "server":
        if not HAS_FASTAPI:
            fail("Instala dependencias: pip install fastapi uvicorn httpx")
            sys.exit(1)

        base_env = load_env(f"{TEMPLATE_DIR}/.env")
        base_url = base_env.get("BASE_URL","")

        print_logo()
        info(f"Puerto:     {OMNI_PORT}")
        info(f"Instancias: {len(get_all_instances())}")
        info(f"Telegram:   {'configurado' if OMNI_TOKEN else 'NO configurado'}")
        info(f"Santiago:   {SANTIAGO_CHAT or 'NO configurado'}")
        nl()

        if OMNI_TOKEN and base_url:
            asyncio.run(setup_telegram_webhook(base_url))

        uvicorn.run(omni_app, host="0.0.0.0", port=OMNI_PORT, log_level="warning")

    elif cmd == "setup-webhook":
        base_env = load_env(f"{TEMPLATE_DIR}/.env")
        base_url = sys.argv[2] if len(sys.argv) > 2 else base_env.get("BASE_URL","")
        asyncio.run(setup_telegram_webhook(base_url))

    elif cmd in ("help","--help","-h"):
        print_logo()
        cmds = [
            ("server",         "Arrancar servidor de eventos (puerto 9001)"),
            ("chat",           "Chat interactivo desde terminal"),
            ("status",         "Estado rápido de todas las instancias"),
            ("watch",          "Monitor live que refresca cada 5s"),
            ("summary",        "Enviar resumen diario a Telegram ahora"),
            ("setup-webhook",  "Registrar webhook de Telegram"),
        ]
        print(f"  {q(C.W,'Uso:',bold=True)}\n")
        for c, d in cmds:
            print(f"    {q(C.P2,f'melissa-omni.py {c:<18}',bold=True)}{q(C.G2,d)}")
        nl()
        info("Variables requeridas en .env:")
        print(f"    {q(C.G3,'OMNI_PORT=9001')}")
        print(f"    {q(C.G3,'OMNI_KEY=secreto')}")
        print(f"    {q(C.G3,'OMNI_TELEGRAM_TOKEN=token_bot_personal')}")
        print(f"    {q(C.G3,'SANTIAGO_CHAT_ID=tu_chat_id')}")
        nl()
    else:
        fail(f"Comando desconocido: '{cmd}'")
        info("Usa 'melissa-omni.py help'")

if __name__ == "__main__":
    main()
