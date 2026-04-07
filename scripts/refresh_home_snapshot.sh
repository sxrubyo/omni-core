#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_ROOT="${1:-/home/ubuntu}"
SNAPSHOT_ROOT="$ROOT_DIR/home_snapshot"
TARGET_ROOT="$SNAPSHOT_ROOT/ubuntu"
INVENTORY_DIR="$SNAPSHOT_ROOT/inventory"

mkdir -p "$TARGET_ROOT" "$INVENTORY_DIR"
rm -rf "$TARGET_ROOT"
mkdir -p "$TARGET_ROOT"

ALLOWLIST_DIRS=(
  ".agents"
  ".codex"
  ".nova"
  "Openclaw"
  "Workflows-n8n"
  "eco-nova"
  "melissa"
  "melissa-instances"
  "nova-cli"
  "nova-os"
  "nova-test"
  "openclaw-official"
  "tv-bridge"
  "whatsapp-bridge"
  "xus-core"
  "xus-https"
  "xus-tv-bridge"
)

ALLOWLIST_FILES=(
  ".bashrc"
  ".gitconfig"
  ".gitignore"
  "AGENTS.md"
  "QUICK_FIX_GUIDE.md"
  "QUICK_REFERENCE.md"
  "RESTART_SUMMARY.md"
  "SECURITY_FIXES_APPLIED.md"
  "check_token.py"
  "install.sh"
  "package-lock.json"
  "package.json"
  "pair_tv.js"
  "verify_fixes.sh"
)

TOP_LEVEL_OMIT_REASONS=(
  ".android:tool-cache"
  ".appium:tool-cache"
  ".cache:cache"
  ".claude:session-data"
  ".claude-flow:runtime"
  ".config:user-config-may-contain-secrets"
  ".copilot:session-data"
  ".docker:cache"
  ".env.nova:secret"
  ".gemini:session-data"
  ".git-credentials:secret"
  ".local:cache"
  ".melissa:runtime-state"
  ".n8n:runtime-state-and-secrets"
  ".npm:cache"
  ".npm-global:global-packages"
  ".ollama:model-cache"
  ".openclaw:runtime-state"
  ".pki:certificates"
  ".playwright-cli:cache"
  ".pm2:runtime-state"
  ".pytest_cache:cache"
  ".ssh:secret"
  ".swarm:runtime-state"
  "android-sdk:tool-cache"
  "backups-test:backup"
  "data:runtime-state"
  "data-test:test-runtime-state"
  "go:tool-cache"
  "logs-test:test-runtime-state"
  "main.py.tmp:temp-file"
  "melissa-backups:backup"
  "node_modules:dependency-cache"
  "omni-core:git-root"
  "opencode_env:venv"
  "output:build-output"
  "tmp:temp-file"
  "vectors.db:database"
  "nova.db:database"
  "data.db:database"
)

RSYNC_EXCLUDES=(
  "--exclude=.git/"
  "--exclude=node_modules/"
  "--exclude=.venv/"
  "--exclude=venv/"
  "--exclude=__pycache__/"
  "--exclude=.pytest_cache/"
  "--exclude=.cache/"
  "--exclude=.coverage"
  "--exclude=.env"
  "--exclude=.env.*"
  "--exclude=*.env"
  "--exclude=*.pem"
  "--exclude=*.key"
  "--exclude=gcp-sa.json"
  "--exclude=authorized_keys"
  "--exclude=.git-credentials"
  "--exclude=*.db"
  "--exclude=*.db-*"
  "--exclude=*.sqlite"
  "--exclude=*.sqlite-*"
  "--exclude=*.sql.gz"
  "--exclude=logs/"
  "--exclude=*.log"
  "--exclude=backups/"
  "--exclude=backup*/"
  "--exclude=sessions/"
  "--exclude=vendor/"
  "--exclude=.tmp/"
  "--exclude=tmp/"
)

top_level_inventory() {
  find "$HOME_ROOT" -mindepth 1 -maxdepth 1 -printf '%y\t%f\n' | sort > "$INVENTORY_DIR/top_level_entries.tsv"
  du -sh "$HOME_ROOT"/* "$HOME_ROOT"/.[!.]* 2>/dev/null | sort -h > "$INVENTORY_DIR/top_level_sizes.txt" || true
}

write_omissions() {
  : > "$INVENTORY_DIR/omitted_top_level.tsv"
  for item in "${TOP_LEVEL_OMIT_REASONS[@]}"; do
    printf '%s\t%s\n' "${item%%:*}" "${item#*:}" >> "$INVENTORY_DIR/omitted_top_level.tsv"
  done
}

copy_dir() {
  local name="$1"
  local src="$HOME_ROOT/$name"
  local dest="$TARGET_ROOT/$name"

  if [[ ! -e "$src" ]]; then
    return 0
  fi

  mkdir -p "$dest"

  if [[ "$name" == ".codex" ]]; then
    mkdir -p "$dest"
    for entry in AGENTS.override.md config.toml instructions.md version.json rules skills superpowers; do
      if [[ -e "$src/$entry" ]]; then
        rsync -a "$src/$entry" "$dest/"
      fi
    done
    return 0
  fi

  if [[ "$name" == ".nova" ]]; then
    mkdir -p "$dest"
    for entry in .gitignore nova nova.py profiles.json protected.json shell_setup.sh; do
      if [[ -e "$src/$entry" ]]; then
        rsync -a "$src/$entry" "$dest/"
      fi
    done
    if [[ -d "$src/agents" ]]; then
      while IFS= read -r rules_dir; do
        rel_dir="${rules_dir#"$src/"}"
        mkdir -p "$dest/$rel_dir"
        rsync -a "$rules_dir/" "$dest/$rel_dir/"
      done < <(find "$src/agents" -type d -name rules | sort)
    fi
    return 0
  fi

  rsync -a "${RSYNC_EXCLUDES[@]}" "$src/" "$dest/"
}

copy_file() {
  local name="$1"
  local src="$HOME_ROOT/$name"
  local dest="$TARGET_ROOT/$name"

  if [[ -f "$src" ]]; then
    install -D -m 0644 "$src" "$dest"
  fi
}

write_manifest() {
  cat > "$INVENTORY_DIR/snapshot_scope.txt" <<EOF
GitHub-safe fallback snapshot generated from: $HOME_ROOT

Included top-level directories:
$(printf '%s\n' "${ALLOWLIST_DIRS[@]}")

Included top-level files:
$(printf '%s\n' "${ALLOWLIST_FILES[@]}")

Global exclusions inside copied directories:
$(printf '%s\n' "${RSYNC_EXCLUDES[@]}")
EOF
}

top_level_inventory
write_omissions

for dir_name in "${ALLOWLIST_DIRS[@]}"; do
  copy_dir "$dir_name"
done

for file_name in "${ALLOWLIST_FILES[@]}"; do
  copy_file "$file_name"
done

write_manifest

du -sh "$TARGET_ROOT" > "$INVENTORY_DIR/snapshot_size.txt" || true
find "$TARGET_ROOT" -type f | sed "s#^$TARGET_ROOT/##" | sort > "$INVENTORY_DIR/snapshot_files.txt"

printf 'Snapshot refreshed at %s\n' "$TARGET_ROOT"
