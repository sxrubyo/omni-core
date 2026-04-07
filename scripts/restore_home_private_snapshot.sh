#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLIC_TARGET_ROOT="$ROOT_DIR/home_snapshot/ubuntu"
PRIVATE_SNAPSHOT_ROOT="$ROOT_DIR/home_private_snapshot"
PRIVATE_ARCHIVE_DIR="$PRIVATE_SNAPSHOT_ROOT/archives"
PRIVATE_INVENTORY_DIR="$PRIVATE_SNAPSHOT_ROOT/inventory"
TARGET_ROOT="${1:-}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/restore_home_private_snapshot.sh TARGET_ROOT

Restores the public snapshot first, then overlays the encrypted private archives.
EOF
}

ensure_passphrase_file() {
  if [[ -n "${HOME_PRIVATE_SNAPSHOT_PASSPHRASE_FILE:-}" ]]; then
    printf '%s\n' "$HOME_PRIVATE_SNAPSHOT_PASSPHRASE_FILE"
    return 0
  fi

  local passphrase_value="${HOME_PRIVATE_SNAPSHOT_PASSPHRASE:-${OMNI_SECRET_PASSPHRASE:-}}"
  local passphrase_file="$ROOT_DIR/backups/home_private_snapshot.passphrase"

  if [[ -n "$passphrase_value" ]]; then
    mkdir -p "$(dirname "$passphrase_file")"
    umask 077
    printf '%s' "$passphrase_value" > "$passphrase_file"
    printf '%s\n' "$passphrase_file"
    return 0
  fi

  if [[ -f "$passphrase_file" ]]; then
    printf '%s\n' "$passphrase_file"
    return 0
  fi

  printf 'Missing passphrase. Set HOME_PRIVATE_SNAPSHOT_PASSPHRASE or HOME_PRIVATE_SNAPSHOT_PASSPHRASE_FILE.\n' >&2
  exit 1
}

restore_public_snapshot() {
  if [[ -d "$PUBLIC_TARGET_ROOT" ]]; then
    rsync -a "$PUBLIC_TARGET_ROOT/" "$TARGET_ROOT/"
  fi
}

restore_private_snapshot() {
  local passphrase_file="$1"
  local manifest="$PRIVATE_INVENTORY_DIR/archive_manifest.tsv"

  if [[ ! -f "$manifest" ]]; then
    return 0
  fi

  while IFS=$'\t' read -r _target slug _type _parts; do
    [[ -n "$slug" ]] || continue
    cat "$PRIVATE_ARCHIVE_DIR/$slug.tar.gz.enc.part-"* \
      | openssl enc -d -aes-256-cbc -pbkdf2 -salt -pass "file:$passphrase_file" \
      | tar -xzf - -C "$TARGET_ROOT"
  done < "$manifest"
}

main() {
  if [[ -z "$TARGET_ROOT" ]]; then
    usage >&2
    exit 1
  fi

  mkdir -p "$TARGET_ROOT"
  restore_public_snapshot
  restore_private_snapshot "$(ensure_passphrase_file)"
  printf 'Private snapshot restored into %s\n' "$TARGET_ROOT"
}

main "$@"
