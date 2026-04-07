# Handoff: Nova Discovery Hardening, Gmail Dedupe, Branding Normalization

## Session Metadata
- Created: 2026-03-26 18:19:22
- Project: /home/ubuntu/nova-os
- Branch: main
- Session duration: ~1 hour

### Recent Commits (for context)
  - 642ac52 Update guide
  - 3ed6d52 Integrate backend runtime
  - c1efd51 chore: remove demo and internal-only assets
  - bd3a454 feat: ship frontend refresh and github auth groundwork
  - 9532740 chore: start public installs with empty state

## Handoff Chain

- **Continues from**: [2026-03-26-010939-nova-runtime-integration.md](./2026-03-26-010939-nova-runtime-integration.md)
  - Previous title: Nova Runtime Integration
- **Supersedes**: None

> Review the previous handoff for full context before filling this one.

## Current State Summary

This session focused on fixing the discovery engine so Nova only reports agents backed by enough host evidence, adding a real Gmail duplicate-check endpoint against the ledger, normalizing the missing official Nova icon asset, and replacing the stale n8n custom node with one that targets the current `/api/*` backend. Backend tests covering the new scanner confirmation rules and Gmail duplicate route are passing, the frontend production build is passing, and a real host scan now returns only `codex_cli`, `n8n`, and `openclaw` instead of false positives like `langchain_agent` and `open_interpreter`.

## Codebase Understanding

### Architecture Overview

- `frontend/` is the active React + Vite app. The existing enterprise visual language is already established and should be preserved.
- `nova/` is the active FastAPI + runtime kernel. Discovery lives under `nova/discovery/`, API routes under `nova/api/routes/`, ledger persistence under `nova/ledger/` and `nova/storage/`.
- `n8n-nodes-nova/` exists but was stale. It previously pointed at legacy endpoints like `/validate` and `/rules` that do not exist in the current backend.
- The worktree is already dirty with many unrelated and pre-existing modifications. Do not assume every change shown by `git status` belongs to this session.

### Critical Files

| File | Purpose | Relevance |
|------|---------|-----------|
| `nova/discovery/fingerprints.py` | Discovery fingerprint definitions | Added confidence thresholds, logo paths, health paths, and disabled generic discovery outputs |
| `nova/discovery/scanner.py` | Host scanner implementation | Now filters out weak matches, removes generic docker/process reporting, and only counts verified port probes |
| `nova/api/routes/gmail.py` | New Gmail helper route | Adds `/api/gmail/check-duplicate` backed by ledger records |
| `nova/ledger/hash_chain.py` | Ledger persistence | Stores `dedupe_keys` metadata for `send_email` records |
| `frontend/src/pages/dashboard/Discovery.jsx` | Discovery UI | Rewritten to reflect real evidence, filters, runtime events, and logo fallbacks |
| `frontend/src/components/brand/NovaLogo.jsx` | Brand component | Switched from hand-drawn placeholder to official asset-based mark |
| `n8n-nodes-nova/Nova.node.js` | n8n custom node | Replaced stale legacy-node behavior with operations that target current backend routes |
| `n8n-nodes-nova/NovaApi.credentials.js` | n8n credentials | Defaults now align with the live Nova API on `127.0.0.1:8000` |

### Key Patterns Discovered

- Discovery data is serialized through `to_payload()`; adding metadata under `agent.metadata` is low-friction and frontend-safe.
- The frontend already consumes `agent.metadata?.connected`; additional discovery metadata should keep using the same payload shape.
- The scanner had been too permissive because it treated environment variables, dotenv files, broad ports, and generic docker/process matches as valid evidence on their own.
- SQLite-backed tests can surface naïve datetimes even though production code generally uses timezone-aware values. Route code needs to normalize defensively.

## Work Completed

### Tasks Finished

- [x] Reproduced discovery false positives on the real host and confirmed the root cause
- [x] Hardened scanner confirmation rules so weak single-signal matches are filtered out
- [x] Removed generic docker/process discovery output from the active scan path
- [x] Added Gmail duplicate-check API route backed by ledger dedupe metadata
- [x] Added tests for scanner confirmation behavior and Gmail duplicate detection
- [x] Normalized the missing `frontend/nova-branding/nova_i.svg` asset from the official transparent PNGs
- [x] Refreshed favicon and Apple touch icon assets from the official Nova isotipo
- [x] Reworked the discovery UI to show evidence, filters, live toasts, and real runtime summaries
- [x] Replaced the stale n8n custom node with one aligned to the active Nova API

### Files Modified

| File | Changes | Rationale |
|------|---------|-----------|
| `nova/discovery/fingerprints.py` | Added `required_matches`, `health_paths`, `logo_path`, and disabled generic discovery outputs | Stop discovery from inventing agents off weak signals |
| `nova/discovery/scanner.py` | Removed env/dotenv/generic discovery from active path, required verified port probes, added confirmation filtering metadata | Match only real host evidence |
| `tests/test_discovery_scanner.py` | Added scanner confirmation test | Lock the false-positive fix in place |
| `nova/ledger/hash_chain.py` | Added `dedupe_keys` metadata for `send_email` ledger writes | Make duplicate-email checks queryable without storing full payloads |
| `nova/api/routes/gmail.py` | Added `/api/gmail/check-duplicate` | Support the real n8n + Gmail anti-duplicate use case |
| `nova/api/server.py` | Registered the new Gmail router | Expose the new API route |
| `tests/test_api/test_gmail.py` | Added duplicate-route coverage | Verify the new route against real evaluation writes |
| `frontend/src/components/brand/NovaLogo.jsx` | Replaced placeholder-drawn logo with official asset-based branding | Align the product surface with the real Nova mark |
| `frontend/src/components/ui/NovaLogo.jsx` | Added a stable UI re-export | Future imports can use the expected UI namespace |
| `frontend/src/components/ui/index.js` | Re-exported `NovaLogo` | Keep UI exports coherent |
| `frontend/src/App.jsx` | Mounted `ToastRegion` globally | Discovery live-event toasts now render |
| `frontend/src/pages/dashboard/Discovery.jsx` | Rewrote discovery UX around evidence, filters, runtime events, and logo fallbacks | Make the page faithful to the scanner and more operator-useful |
| `frontend/nova-branding/nova_i.svg` | Generated normalized official SVG wrapper from the master PNG asset | The repo was missing the promised canonical icon asset |
| `frontend/public/agent-logos/*` | Added codex/n8n/openclaw/generic discovery marks and fallbacks | Support branded discovery cards without broken images |
| `frontend/public/favicon*`, `frontend/public/apple-touch-icon.png` | Regenerated from official Nova icon | Bring favicons in line with official branding |
| `n8n-nodes-nova/Nova.node.js` | Replaced stale legacy node behavior with operations for evaluate, gmail duplicate check, agent registration, and ledger verification | The previous node targeted backend routes that no longer exist |
| `n8n-nodes-nova/NovaApi.credentials.js` | Updated credentials metadata and default API URL | Align n8n defaults with the running Nova API |
| `n8n-nodes-nova/package.json` | Added description/files/metadata | Make the node package self-describing and shippable |
| `n8n-nodes-nova/README.md` | Added usage and workflow guidance | Clarify how to use the node for anti-duplicate email flows |

### Decisions Made

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Harden discovery by thresholding existing fingerprints instead of introducing a parallel scanner subsystem | New `fingerprints_real.py` + new scanner vs hardening current scanner | Lower churn, less integration risk, and immediate compatibility with current connectors and API payloads |
| Drop environment and dotenv signals from the active confirmation path | Keep them as standalone evidence vs stop counting them | They were a major source of false positives and do not prove a runtime actually exists |
| Disable generic docker/process agents in scan results | Keep generic discovery vs explicit fingerprints only | Generic hits were surfacing unrelated services like Evolution API |
| Store only email dedupe keys in ledger metadata | Store full payload snapshots vs store a minimal recipient/subject fingerprint | Minimal storage improves privacy and still supports duplicate detection |
| Normalize the missing `nova_i.svg` from the official transparent PNGs | Invent a fresh vector path vs wrap the real asset | The repo did not contain the promised source SVG, so the safest move was to normalize the official master asset already present |
| Replace the n8n node around real backend routes | Preserve the stale legacy routes vs match the live `/api/*` surface | The existing node was effectively broken against the current backend |

## Pending Work

## Immediate Next Steps

1. Decide whether to restart the live n8n containers after syncing the updated node package, because the code is ready but the running instance may still have the old node loaded until restart.
2. Add a dedicated help/onboarding surface for discovery if the product still wants `/dashboard/help/discovery` instead of the inline discovery guidance now present.
3. Audit the broader frontend branding and provider-logo inventory; there are other assets in the repo that look stale or externally scraped, but they were out of scope for this pass.

### Blockers/Open Questions

- [ ] The worktree contains many unrelated tracked and untracked changes from earlier work. Any follow-up should inspect files carefully before assuming authorship or reverting anything.
- [ ] The live n8n runtime was not restarted in this session to avoid interrupting active workflows without explicit downtime approval.

### Deferred Items

- A dedicated `/dashboard/help/discovery` route was deferred because the discovery page itself now explains the evidence model and the bigger product already has a heavy route surface.
- Full cleanup of unrelated docs/version drift (for example stale README claims versus the current runtime) was deferred to keep this pass focused on discovery, branding, and the n8n/Gmail flow.

## Context for Resuming Agent

## Important Context

The most important outcome is that discovery is now evidence-thresholded and verified against the real host. Before the fix, the scanner incorrectly reported `langchain_agent` and `open_interpreter` just because port `8000` responded, even though that port was actually Nova OS itself. After the fix, a real scan on this machine returns only `codex_cli`, `n8n`, and `openclaw`. The Gmail duplicate route depends on new `dedupe_keys` stored in ledger metadata for future `send_email` evaluations; older ledger records without those keys will not be matched as duplicates. The n8n node code has been updated in the repo, but the live n8n containers were not restarted, so runtime validation in the UI may still reflect the old node until that operational step happens.

### Assumptions Made

- The official Nova isotipo assets in `frontend/nova-branding/Nova I/` are authoritative because the promised `frontend/nova-branding/nova_i.svg` did not exist.
- Restarting the live n8n service without checking for active workflows could be disruptive, so that step was intentionally not executed automatically.
- The active frontend route is `frontend/src/pages/dashboard/Discovery.jsx`, and preserving the existing enterprise visual language matters more than introducing a new design system.

### Potential Gotchas

- `git status` is noisy. Many modified/untracked files predate this work. Do not mass-revert.
- The scanner still contains `_scan_environment` and `_scan_dotenv_files`, but they are no longer called by `full_scan()`.
- SQLite tests may surface naïve datetimes from ORM objects; normalize before comparing against timezone-aware timestamps.
- `frontend/src/components/brand/NovaLogo.jsx` defaults to the white isotipo because all current usages are on dark surfaces. If the logo is moved onto light backgrounds, pass a dark-tone variant or extend the component.

## Environment State

### Tools/Services Used

- Project venv: `/home/ubuntu/nova-os/.venv`
- Added Python package: `Pillow` inside the project venv for asset validation/generation
- Frontend build: `npm run build` in `frontend/`
- Backend tests: `pytest` from project root
- n8n node syntax check: `node -e "require('./Nova.node.js'); require('./NovaApi.credentials.js')"`

### Active Processes

- `nova_api` container is running on `127.0.0.1:8000`
- `nexus-n8n-main` container is running on `127.0.0.1:5678`
- `nexus-n8n-worker-1` container is running
- `nexus-evolution-api` container is running on `127.0.0.1:8080`
- OpenClaw ports observed during scan: `18789` and `18791`

### Environment Variables

- `OPENAI_API_KEY`
- `N8N_BASIC_AUTH_USER`
- `N8N_BASIC_AUTH_PASSWORD`
- `VITE_API_PROXY_TARGET`

## Related Resources

- [Discovery scanner](/home/ubuntu/nova-os/nova/discovery/scanner.py)
- [Discovery fingerprints](/home/ubuntu/nova-os/nova/discovery/fingerprints.py)
- [Gmail duplicate route](/home/ubuntu/nova-os/nova/api/routes/gmail.py)
- [Ledger hash chain](/home/ubuntu/nova-os/nova/ledger/hash_chain.py)
- [Discovery page](/home/ubuntu/nova-os/frontend/src/pages/dashboard/Discovery.jsx)
- [Nova logo component](/home/ubuntu/nova-os/frontend/src/components/brand/NovaLogo.jsx)
- [n8n custom node](/home/ubuntu/nova-os/n8n-nodes-nova/Nova.node.js)
- [Previous handoff](/home/ubuntu/nova-os/.claude/handoffs/2026-03-26-010939-nova-runtime-integration.md)

---

**Security Reminder**: Before finalizing, run `validate_handoff.py` to check for accidental secret exposure.
