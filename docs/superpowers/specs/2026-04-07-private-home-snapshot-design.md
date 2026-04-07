# Private Home Snapshot Design

## Goal

Convert the current GitHub-safe `home_snapshot/` into a two-layer migration backup:

1. `home_snapshot/`
   Public-safe fallback with sanitized code/config structure.
2. `home_private_snapshot/`
   Private, encrypted overlay with hidden state, logs, runtime databases, and active project state needed to recover a host that should behave like the current one.

The private layer is for migration continuity, not for public mirroring.

## Constraints

- Do not commit plaintext `.env` files, raw SSH material, or plaintext credential files.
- Keep GitHub-compatible file sizes by splitting encrypted archives into sub-100MB parts.
- Preserve the current public-safe snapshot workflow.
- Prefer restoring the public layer first and then overlaying the encrypted private state.

## Proposed Structure

### Public Layer

Keep the existing structure unchanged:

- `home_snapshot/ubuntu/`
- `home_snapshot/inventory/`

### Private Layer

Add a sibling tree:

- `home_private_snapshot/inventory/`
- `home_private_snapshot/archives/`

`inventory/` will contain:

- included targets
- omitted targets
- archive manifest
- chunk manifest
- size summary
- restore notes

`archives/` will contain one encrypted, chunked archive per top-level target.

## Private Targets

Archive these top-level entries in encrypted form when present:

- `.claude`
- `.codex`
- `.gemini`
- `.melissa`
- `.n8n`
- `.nova`
- `.pm2`
- `Openclaw`
- `Workflows-n8n`
- `melissa`
- `melissa-instances`
- `nova-os`
- `openclaw-official`
- `tv-bridge`
- `whatsapp-bridge`
- `xus-core`
- `xus-https`
- `xus-tv-bridge`

Rationale:

- They contain the hidden runtime state the public snapshot misses.
- They cover the main codebases and runtime paths that must survive migration.
- They avoid historical backup piles and disposable caches that would explode repo size without helping the migration.

## Explicit Omissions

Do not include these in either plaintext or encrypted form:

- `.ssh`
- `.git-credentials`
- `.env*`
- `melissa-backups`
- `omni-core/backups`
- `node_modules`
- `.cache`
- `.npm`
- `.npm-global`
- tool caches and SDKs

Rationale:

- Secrets must not be committed in plaintext.
- Historical backup piles and caches are too large and not required for continuity.
- `omni-core` itself remains recoverable from Git.

## Encryption Model

- Use `openssl enc -aes-256-cbc -pbkdf2 -salt`.
- Accept passphrase from:
  - `HOME_PRIVATE_SNAPSHOT_PASSPHRASE_FILE`
  - else `HOME_PRIVATE_SNAPSHOT_PASSPHRASE`
  - else `OMNI_SECRET_PASSPHRASE`
  - else generate a local passphrase file under `backups/` and do not commit it.
- Split encrypted output into chunks under 95MB by default.

## Restore Flow

1. Clone `omni-core`.
2. Restore `home_snapshot/ubuntu/` into `/home/ubuntu/`.
3. Run `scripts/restore_home_private_snapshot.sh` with the passphrase file.
4. Re-run service bootstrap (`install.sh`, Compose, PM2, rewrite steps).

## Verification

The implementation should verify:

- public snapshot still excludes secrets
- private snapshot creates encrypted chunk files
- no plaintext private-state content is emitted into the repo outside `home_snapshot/`
- restore script can overlay a decrypted archive onto a temporary target in tests
