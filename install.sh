#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_TARGET="/usr/local/bin/omni"
USE_COMPOSE=false
AUTO_SYNC=false
USE_PM2=false
INSTALL_TIMER=false
RECOVER_APPS_IPS=false
TIMER_ON_CALENDAR="${OMNI_TIMER_ON_CALENDAR:-daily}"
PROFILE="${OMNI_PROFILE:-full-home}"

for arg in "$@"; do
  case "$arg" in
    --compose) USE_COMPOSE=true ;;
    --sync) AUTO_SYNC=true ;;
    --pm2) USE_PM2=true ;;
    --timer) INSTALL_TIMER=true ;;
    --recover-apps-ips) RECOVER_APPS_IPS=true ;;
    --on-calendar=*) TIMER_ON_CALENDAR="${arg#*=}" ;;
  esac
done

should_run_sync() {
  local servers_file="$ROOT_DIR/config/servers.json"
  if [ ! -f "$servers_file" ]; then
    return 1
  fi
  if grep -q '"1.2.3.4"' "$servers_file"; then
    return 1
  fi
  if [ -n "${SSH_AUTH_SOCK:-}" ]; then
    return 0
  fi
  if [ -d "$HOME/.ssh" ] && find "$HOME/.ssh" -maxdepth 1 -type f ! -name "*.pub" ! -name "authorized_keys" ! -name "known_hosts*" ! -name "config" | grep -q .; then
    return 0
  fi
  return 1
}

mkdir -p "$ROOT_DIR/config" "$ROOT_DIR/config/systemd" "$ROOT_DIR/data/servers" "$ROOT_DIR/backups/host-bundles" "$ROOT_DIR/logs"

if [ ! -f "$ROOT_DIR/.env" ] && [ -f "$ROOT_DIR/.env.example" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

if [ ! -f "$ROOT_DIR/config/repos.json" ]; then
  cp "$ROOT_DIR/config/repos.example.json" "$ROOT_DIR/config/repos.json"
fi

if [ ! -f "$ROOT_DIR/config/servers.json" ]; then
  cp "$ROOT_DIR/config/servers.example.json" "$ROOT_DIR/config/servers.json"
fi

if [ ! -f "$ROOT_DIR/config/system_manifest.json" ] && [ -f "$ROOT_DIR/config/system_manifest.example.json" ]; then
  cp "$ROOT_DIR/config/system_manifest.example.json" "$ROOT_DIR/config/system_manifest.json"
fi

chmod +x "$ROOT_DIR/bin/omni"

if command -v sudo >/dev/null 2>&1; then
  sudo ln -sf "$ROOT_DIR/bin/omni" "$BIN_TARGET"
else
  ln -sf "$ROOT_DIR/bin/omni" "$BIN_TARGET"
fi

"$ROOT_DIR/bin/omni" init --profile "$PROFILE" >/dev/null || true

if $AUTO_SYNC; then
  if should_run_sync; then
    "$ROOT_DIR/bin/omni" sync || true
  else
    echo "Skipping initial sync: no remote SSH identity configured yet or servers.json still uses placeholders."
  fi
fi

if $USE_PM2; then
  pm2 start "$ROOT_DIR/ecosystem.config.js"
fi

if $USE_COMPOSE; then
  MIGRATE_ARGS=(migrate --accept-all --profile "$PROFILE")
  if $RECOVER_APPS_IPS; then
    MIGRATE_ARGS+=(--recover-apps-ips)
  fi
  "$ROOT_DIR/bin/omni" "${MIGRATE_ARGS[@]}"
fi

if $INSTALL_TIMER; then
  "$ROOT_DIR/bin/omni" timer-install --service-name omni-update --on-calendar "$TIMER_ON_CALENDAR"
fi

cat <<EOF
Omni Core instalado en: $ROOT_DIR

Modo automático:
  ./install.sh --compose --sync --timer

Archivos clave:
  .env
  config/repos.json
  config/servers.json
  config/system_manifest.json
  tasks.json

Comandos:
  omni
  omni start
  omni doctor
  omni capture
  omni restore
  omni migrate
  omni install
  omni inventory
  omni bundle-create
  omni secrets-export
  omni reconcile
  omni timer-install
  omni sync
  omni migrate --accept-all
  omni migrate --accept-all --recover-apps-ips
EOF
