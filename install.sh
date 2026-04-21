#!/usr/bin/env bash
set -euo pipefail

REPO_SLUG="${OMNI_INSTALL_REPO:-sxrubyo/omni-core}"
ARCHIVE_URL="${OMNI_INSTALL_SOURCE_ARCHIVE:-https://codeload.github.com/${REPO_SLUG}/tar.gz/refs/heads/main}"
LOCAL_REPO="${OMNI_INSTALL_LOCAL_REPO:-}"
OMNI_HOME="${OMNI_INSTALL_HOME:-$HOME/.omni}"
RUNTIME_DIR="${OMNI_RUNTIME_DIR:-$OMNI_HOME/runtime}"
BIN_DIR="${OMNI_BIN_DIR:-$HOME/.local/bin}"
WRAPPER_PATH="${OMNI_WRAPPER_PATH:-$BIN_DIR/omni}"
SKIP_DEP_BOOTSTRAP="${OMNI_INSTALL_SKIP_DEPENDENCY_BOOTSTRAP:-0}"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

say() {
  printf '==> %s\n' "$1"
}

ok() {
  printf '  OK  %s\n' "$1"
}

fail() {
  printf '  ERR %s\n' "$1" >&2
  exit 1
}

ensure_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

stage_repo_from_local() {
  local source_repo="$1"
  [ -d "$source_repo" ] || fail "Local repo override not found: $source_repo"
  mkdir -p "$OMNI_HOME"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
      --exclude '.git' \
      --exclude '.pytest_cache' \
      --exclude '__pycache__' \
      --exclude '.env' \
      --exclude 'home_snapshot' \
      --exclude 'home_private_snapshot' \
      --exclude 'logs' \
      --exclude 'data' \
      --exclude 'backups' \
      --exclude 'config/repos.json' \
      --exclude 'config/servers.json' \
      --exclude 'config/system_manifest.json' \
      --exclude 'config/omni_agent.json' \
      --exclude 'config/omni_agent_activation.txt' \
      "$source_repo"/ "$OMNI_HOME"/
  else
    cp -a "$source_repo"/. "$OMNI_HOME"/
    rm -rf \
      "$OMNI_HOME/.git" \
      "$OMNI_HOME/.pytest_cache" \
      "$OMNI_HOME/.env" \
      "$OMNI_HOME/logs" \
      "$OMNI_HOME/data" \
      "$OMNI_HOME/backups" \
      "$OMNI_HOME/home_snapshot" \
      "$OMNI_HOME/home_private_snapshot" \
      "$OMNI_HOME/config/repos.json" \
      "$OMNI_HOME/config/servers.json" \
      "$OMNI_HOME/config/system_manifest.json" \
      "$OMNI_HOME/config/omni_agent.json" \
      "$OMNI_HOME/config/omni_agent_activation.txt"
  fi
}

stage_repo_from_archive() {
  local archive="$TMP_DIR/omni-core.tgz"
  local extract_dir="$TMP_DIR/extract"
  mkdir -p "$extract_dir" "$OMNI_HOME"
  curl -fsSL "$ARCHIVE_URL" -o "$archive"
  ok "Archive downloaded"
  tar -xzf "$archive" -C "$extract_dir"
  local staged_root
  staged_root="$(find "$extract_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  [ -n "$staged_root" ] || fail "Could not locate extracted repository root"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$staged_root"/ "$OMNI_HOME"/
  else
    cp -a "$staged_root"/. "$OMNI_HOME"/
  fi
}

bootstrap_runtime() {
  local python_bin
  python_bin="$(command -v python3 || true)"
  [ -n "$python_bin" ] || fail "python3 is required"
  "$python_bin" -m venv "$RUNTIME_DIR"
  if [ "$SKIP_DEP_BOOTSTRAP" = "1" ]; then
    return
  fi
  "$RUNTIME_DIR/bin/pip" install --disable-pip-version-check --upgrade pip >/dev/null
  "$RUNTIME_DIR/bin/pip" install --disable-pip-version-check rich tqdm prompt_toolkit >/dev/null
}

write_wrapper() {
  mkdir -p "$BIN_DIR"
  cat >"$WRAPPER_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
unset OMNI_CONFIG_DIR OMNI_STATE_DIR OMNI_BACKUP_DIR OMNI_BUNDLE_DIR OMNI_AUTO_BUNDLE_DIR
unset OMNI_LOG_DIR OMNI_WATCH_STATE_FILE OMNI_ENV_FILE OMNI_AGENT_CONFIG_FILE OMNI_TASKS_FILE
unset OMNI_REPOS_FILE OMNI_SERVERS_FILE OMNI_MANIFEST_FILE
export OMNI_HOME="${OMNI_HOME}"
exec "${RUNTIME_DIR}/bin/python" "${OMNI_HOME}/src/omni_core.py" "\$@"
EOF
  chmod +x "$WRAPPER_PATH"
}

persist_path() {
  local line='export PATH="$HOME/.local/bin:$PATH"'
  for profile in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    if [ -f "$profile" ] && ! grep -Fq "$line" "$profile"; then
      printf '\n%s\n' "$line" >> "$profile"
    fi
  done
}

validate_install() {
  "$WRAPPER_PATH" init >/dev/null 2>&1 || true
  "$WRAPPER_PATH" help >/dev/null 2>&1 || fail "Wrapper validation failed"
}

say "Preparing Omni installation"
ensure_cmd curl
ensure_cmd tar
ensure_cmd bash

if [ -n "$LOCAL_REPO" ]; then
  say "Staging Omni from local repository"
  stage_repo_from_local "$LOCAL_REPO"
  ok "Repository staged in $OMNI_HOME"
else
  say "Downloading Omni Core"
  stage_repo_from_archive
  ok "Repository staged in $OMNI_HOME"
fi

say "Bootstrapping isolated runtime"
bootstrap_runtime
ok "Runtime ready at $RUNTIME_DIR"

say "Creating CLI wrapper"
write_wrapper
persist_path
ok "CLI wrapper created at $WRAPPER_PATH"

say "Validating Omni CLI"
validate_install
ok "Omni CLI is ready"

cat <<EOF

Omni Core installed.
Open a new terminal if PATH changes are not visible yet.
Commands:
  omni
  omni guide
  omni connect --host <ip|fqdn> --user <user>

One-line install:
  curl -fsSL https://raw.githubusercontent.com/${REPO_SLUG}/main/install.sh | bash
EOF
