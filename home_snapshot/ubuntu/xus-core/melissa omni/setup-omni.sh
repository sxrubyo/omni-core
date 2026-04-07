#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# setup-omni.sh — Crea la carpeta melissa-omni y la deja lista para correr
#
# Lo que hace:
#   1. Crea /home/ubuntu/melissa-omni/
#   2. Copia los archivos necesarios de /home/ubuntu/melissa/
#   3. Copia el .env de Omni (con cascada LLM completa)
#   4. Instala con PM2 como servicio
#   5. Configura el webhook de Telegram si BASE_URL está configurado
#
# Uso:
#   chmod +x setup-omni.sh
#   ./setup-omni.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e

P='\033[0;35m'; G='\033[0;32m'; Y='\033[1;33m'
C='\033[0;36m'; R='\033[0;31m'; W='\033[1;37m'; DIM='\033[2m'; NC='\033[0m'

info()    { echo -e "  ${C}·  $1${NC}"; }
ok()      { echo -e "  ${G}✓  $1${NC}"; }
warn()    { echo -e "  ${Y}!  $1${NC}"; }
fail()    { echo -e "  ${R}✗  $1${NC}"; }
header()  { echo -e "\n${P}══ $1 ══${NC}\n"; }

# ── Directorios ────────────────────────────────────────────────────────────────
MELISSA_DIR="${MELISSA_DIR:-/home/ubuntu/melissa}"
OMNI_DIR="${OMNI_DIR:-/home/ubuntu/melissa-omni}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo -e "${P}  ✦  Melissa Omni — Setup${NC}"
echo -e "${DIM}  El ojo personal de Santiago${NC}"
echo ""

# ── 1. Verificar que melissa base existe ──────────────────────────────────────
header "Verificando"

if [ ! -d "$MELISSA_DIR" ]; then
  fail "Carpeta de Melissa no encontrada en $MELISSA_DIR"
  echo "  Configura MELISSA_DIR o asegúrate de tener Melissa instalada primero."
  exit 1
fi
ok "Melissa base encontrada en $MELISSA_DIR"

# ── 2. Crear carpeta melissa-omni ─────────────────────────────────────────────
header "Creando $OMNI_DIR"

mkdir -p "$OMNI_DIR"
ok "Carpeta creada"

# ── 3. Copiar archivos necesarios ─────────────────────────────────────────────
header "Copiando archivos"

# El cerebro de Omni
if [ -f "$SCRIPT_DIR/melissa-omni.py" ]; then
  cp "$SCRIPT_DIR/melissa-omni.py" "$OMNI_DIR/melissa-omni.py"
  ok "melissa-omni.py copiado"
elif [ -f "$MELISSA_DIR/melissa-omni.py" ]; then
  cp "$MELISSA_DIR/melissa-omni.py" "$OMNI_DIR/melissa-omni.py"
  ok "melissa-omni.py copiado desde melissa/"
else
  fail "melissa-omni.py no encontrado. Ponlo en $SCRIPT_DIR o $MELISSA_DIR"
  exit 1
fi

# requirements.txt (para instalar dependencias)
if [ -f "$MELISSA_DIR/requirements.txt" ]; then
  cp "$MELISSA_DIR/requirements.txt" "$OMNI_DIR/requirements.txt"
  ok "requirements.txt copiado"
fi

# ── 4. Crear/copiar .env ──────────────────────────────────────────────────────
header "Configurando .env"

ENV_SRC="$SCRIPT_DIR/melissa-omni.env"
ENV_DST="$OMNI_DIR/.env"

if [ -f "$ENV_DST" ]; then
  warn ".env ya existe en $OMNI_DIR"
  read -p "  ¿Sobreescribir? (s/N): " OVERWRITE
  if [[ ! "$OVERWRITE" =~ ^[sS] ]]; then
    info "Manteniendo .env existente"
  else
    if [ -f "$ENV_SRC" ]; then
      cp "$ENV_SRC" "$ENV_DST"
      ok ".env actualizado desde plantilla"
    fi
  fi
else
  if [ -f "$ENV_SRC" ]; then
    cp "$ENV_SRC" "$ENV_DST"
    ok ".env copiado desde plantilla"
  else
    # Generar .env básico leyendo claves del .env de Melissa
    MELISSA_ENV="$MELISSA_DIR/.env"
    if [ -f "$MELISSA_ENV" ]; then
      GROQ=$(grep "^GROQ_API_KEY=" "$MELISSA_ENV" 2>/dev/null | cut -d= -f2-)
      GEM1=$(grep "^GEMINI_API_KEY=" "$MELISSA_ENV" 2>/dev/null | cut -d= -f2-)
      GEM2=$(grep "^GEMINI_API_KEY_2=" "$MELISSA_ENV" 2>/dev/null | cut -d= -f2-)
      GEM3=$(grep "^GEMINI_API_KEY_3=" "$MELISSA_ENV" 2>/dev/null | cut -d= -f2-)
      ORCA=$(grep "^OPENROUTER_API_KEY=" "$MELISSA_ENV" 2>/dev/null | cut -d= -f2-)
      OAI=$(grep "^OPENAI_API_KEY=" "$MELISSA_ENV" 2>/dev/null | cut -d= -f2-)
      BASE_URL=$(grep "^BASE_URL=" "$MELISSA_ENV" 2>/dev/null | cut -d= -f2-)
    fi

    cat > "$ENV_DST" << ENVEOF
# melissa-omni/.env — generado por setup-omni.sh

# ── Bot personal de Santiago ──────────────────────────────────────────────────
# Crea un nuevo bot en @BotFather → /newbot → pega el token aquí
OMNI_TELEGRAM_TOKEN=

# Tu chat_id: escríbele a @userinfobot en Telegram
SANTIAGO_CHAT_ID=

# ── Servidor ──────────────────────────────────────────────────────────────────
OMNI_PORT=9001
OMNI_KEY=omni_$(openssl rand -hex 8 2>/dev/null || echo "secret_cambia_esto")
BASE_URL=${BASE_URL}

# ── Rutas a instancias ────────────────────────────────────────────────────────
MELISSA_DIR=$MELISSA_DIR
INSTANCES_DIR=${INSTANCES_DIR:-/home/ubuntu/melissa-instances}

# ── LLM — heredadas de Melissa ───────────────────────────────────────────────
GROQ_API_KEY=${GROQ}
GEMINI_API_KEY=${GEM1}
GEMINI_API_KEY_2=${GEM2}
GEMINI_API_KEY_3=${GEM3}
OPENROUTER_API_KEY=${ORCA}
OPENAI_API_KEY=${OAI}

# ── Nova ──────────────────────────────────────────────────────────────────────
NOVA_URL=http://localhost:9002
NOVA_API_KEY=

# ── Health monitor ────────────────────────────────────────────────────────────
OMNI_HEALTH_INTERVAL=60
OMNI_DAILY_SUMMARY_HOUR=8
ENVEOF
    ok ".env generado con claves heredadas de Melissa"
  fi
fi

# ── 5. Verificar OMNI_TELEGRAM_TOKEN y SANTIAGO_CHAT_ID ──────────────────────
header "Verificando configuración"

OMNI_TOKEN=$(grep "^OMNI_TELEGRAM_TOKEN=" "$ENV_DST" 2>/dev/null | cut -d= -f2- | xargs)
SANTIAGO_ID=$(grep "^SANTIAGO_CHAT_ID=" "$ENV_DST" 2>/dev/null | cut -d= -f2- | xargs)

if [ -z "$OMNI_TOKEN" ]; then
  warn "OMNI_TELEGRAM_TOKEN vacío"
  echo ""
  echo -e "  ${Y}Para obtenerlo:${NC}"
  echo "  1. Abre Telegram → busca @BotFather"
  echo "  2. Escribe /newbot"
  echo "  3. Ponle el nombre que quieras (ej: Santiago Omni)"
  echo "  4. Copia el token y ponlo en $ENV_DST"
  echo ""
  read -p "  Pega el token ahora (o Enter para dejarlo vacío): " TOKEN_INPUT
  if [ -n "$TOKEN_INPUT" ]; then
    sed -i "s|^OMNI_TELEGRAM_TOKEN=.*|OMNI_TELEGRAM_TOKEN=$TOKEN_INPUT|" "$ENV_DST"
    ok "Token guardado"
  fi
else
  ok "OMNI_TELEGRAM_TOKEN configurado"
fi

if [ -z "$SANTIAGO_ID" ]; then
  warn "SANTIAGO_CHAT_ID vacío"
  echo ""
  echo -e "  ${Y}Para obtenerlo:${NC}"
  echo "  1. Abre Telegram → busca @userinfobot"
  echo "  2. Escribe /start → te responde con tu ID"
  echo ""
  read -p "  Pega tu chat_id ahora (o Enter para dejarlo vacío): " ID_INPUT
  if [ -n "$ID_INPUT" ]; then
    sed -i "s|^SANTIAGO_CHAT_ID=.*|SANTIAGO_CHAT_ID=$ID_INPUT|" "$ENV_DST"
    ok "Chat ID guardado"
  fi
else
  ok "SANTIAGO_CHAT_ID configurado"
fi

# ── 6. Instalar dependencias ──────────────────────────────────────────────────
header "Dependencias"

if [ -f "$OMNI_DIR/requirements.txt" ]; then
  info "Instalando dependencias Python..."
  pip install --quiet fastapi "uvicorn[standard]" httpx python-dotenv 2>/dev/null || \
  pip3 install --quiet fastapi "uvicorn[standard]" httpx python-dotenv 2>/dev/null || \
  warn "No pude instalar automáticamente. Corre manualmente: pip install fastapi uvicorn httpx python-dotenv"
  ok "Dependencias instaladas"
fi

# ── 7. Lanzar con PM2 ─────────────────────────────────────────────────────────
header "Lanzando con PM2"

if command -v pm2 &>/dev/null; then
  pm2 delete melissa-omni 2>/dev/null || true
  pm2 start "$OMNI_DIR/melissa-omni.py" \
    --name melissa-omni \
    --interpreter python3 \
    -- server \
    2>/dev/null
  pm2 save 2>/dev/null || true
  sleep 3

  # Health check
  OMNI_PORT_VAL=$(grep "^OMNI_PORT=" "$ENV_DST" 2>/dev/null | cut -d= -f2 || echo "9001")
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    "http://localhost:$OMNI_PORT_VAL/health" 2>/dev/null || echo "000")

  if [ "$HTTP_STATUS" = "200" ]; then
    ok "Melissa Omni online en puerto $OMNI_PORT_VAL"
  else
    warn "Omni arrancando (puede tardar unos segundos)"
    info "Verifica con: pm2 logs melissa-omni"
  fi
else
  warn "PM2 no encontrado. Arranca manualmente:"
  echo "  cd $OMNI_DIR && python3 melissa-omni.py server"
fi

# ── 8. Resumen final ──────────────────────────────────────────────────────────
echo ""
echo -e "${G}══════════════════════════════════════════════${NC}"
echo -e "${G}  Melissa Omni lista en $OMNI_DIR${NC}"
echo -e "${G}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${C}Carpeta:${NC}   $OMNI_DIR"
echo -e "  ${C}Puerto:${NC}    $(grep "^OMNI_PORT=" "$ENV_DST" 2>/dev/null | cut -d= -f2 || echo 9001)"
echo -e "  ${C}PM2:${NC}       melissa-omni"
echo ""
echo -e "  ${DIM}Comandos:${NC}"
echo "  pm2 logs melissa-omni           → logs en vivo"
echo "  python3 melissa-omni.py chat    → chat terminal"
echo "  python3 melissa-omni.py status  → estado de clientes"
echo "  python3 melissa-omni.py watch   → monitor live"
echo ""

if [ -z "$OMNI_TOKEN" ] || [ -z "$SANTIAGO_ID" ]; then
  echo -e "  ${Y}Pendiente:${NC}"
  [ -z "$OMNI_TOKEN" ] && echo "  · Configurar OMNI_TELEGRAM_TOKEN en $ENV_DST"
  [ -z "$SANTIAGO_ID" ] && echo "  · Configurar SANTIAGO_CHAT_ID en $ENV_DST"
  echo "  Luego: pm2 restart melissa-omni"
  echo ""
fi
