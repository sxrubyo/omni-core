#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence


@dataclass(frozen=True)
class SSHDestination:
    host: str
    user: str
    port: int = 22
    key_path: str = ""

    def target(self) -> str:
        return f"{self.user}@{self.host}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _ssh_base_command(destination: SSHDestination) -> List[str]:
    args = ["ssh", "-p", str(destination.port)]
    if destination.key_path:
        args.extend(["-i", destination.key_path])
    args.extend(
        [
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            destination.target(),
        ]
    )
    return args


def parse_remote_probe_output(raw: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "system": "unknown",
        "package_manager": "unknown",
        "home_entries": 0,
        "git_repos": 0,
        "package_count": 0,
        "fresh_server": False,
        "home": "",
    }
    for line in str(raw or "").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in {"home_entries", "git_repos", "package_count"}:
            try:
                payload[key] = int(value)
            except ValueError:
                payload[key] = 0
        elif key == "fresh_server":
            payload[key] = value.lower() in {"1", "true", "yes"}
        else:
            payload[key] = value
    return payload


def probe_remote_host(
    destination: SSHDestination,
    *,
    timeout: int = 30,
    runner: Any = subprocess.run,
) -> Dict[str, Any]:
    script = r"""
set -eu
printf 'system=%s\n' "$(uname -s 2>/dev/null || echo unknown)"
pkg=unknown
for candidate in apt-get apt dnf yum pacman apk zypper brew; do
  if command -v "$candidate" >/dev/null 2>&1; then
    pkg="$candidate"
    break
  fi
done
printf 'package_manager=%s\n' "$pkg"
printf 'home=%s\n' "${HOME:-}"
home_entries="$(find "${HOME:-.}" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l | tr -d ' ')"
git_repos="$(find "${HOME:-.}" -maxdepth 3 -name .git -type d 2>/dev/null | wc -l | tr -d ' ')"
package_count=0
if command -v dpkg-query >/dev/null 2>&1; then
  package_count="$(dpkg-query -W -f='${Package}\n' 2>/dev/null | wc -l | tr -d ' ')"
elif command -v rpm >/dev/null 2>&1; then
  package_count="$(rpm -qa 2>/dev/null | wc -l | tr -d ' ')"
elif command -v brew >/dev/null 2>&1; then
  package_count="$(brew list 2>/dev/null | wc -l | tr -d ' ')"
fi
fresh=false
if [ "${home_entries:-0}" -le 6 ] && [ "${git_repos:-0}" -eq 0 ] && [ "${package_count:-0}" -le 500 ]; then
  fresh=true
fi
printf 'home_entries=%s\n' "${home_entries:-0}"
printf 'git_repos=%s\n' "${git_repos:-0}"
printf 'package_count=%s\n' "${package_count:-0}"
printf 'fresh_server=%s\n' "$fresh"
"""
    command = _ssh_base_command(destination) + [script]
    result = runner(command, capture_output=True, text=True, check=False, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "SSH probe failed")
    return parse_remote_probe_output(result.stdout)


def build_rsync_command(
    source_paths: Sequence[str],
    destination: SSHDestination,
    *,
    remote_path: str,
) -> List[str]:
    ssh_transport = f"ssh -p {destination.port}"
    if destination.key_path:
        ssh_transport += f" -i {destination.key_path}"
    command = ["rsync", "-az", "--info=progress2", "-e", ssh_transport]
    command.extend(list(source_paths))
    command.append(f"{destination.target()}:{remote_path.rstrip('/')}/")
    return command


def build_sftp_command(
    source_paths: Sequence[str],
    destination: SSHDestination,
    *,
    remote_path: str,
) -> tuple[List[str], str]:
    lines = [f"mkdir {remote_path}", f"cd {remote_path}"]
    for source in source_paths:
        resolved = Path(source)
        if resolved.is_dir():
            lines.append(f"put -r {resolved}")
        else:
            lines.append(f"put {resolved}")
    batch = "\n".join(lines) + "\n"
    command = ["sftp", "-P", str(destination.port)]
    if destination.key_path:
        command.extend(["-i", destination.key_path])
    command.extend(["-b", "-", destination.target()])
    return command, batch


def transfer_payload(
    source_paths: Sequence[str],
    destination: SSHDestination,
    *,
    remote_path: str,
    transport: str = "rsync",
    timeout: int = 1200,
    runner: Any = subprocess.run,
) -> Dict[str, Any]:
    if not source_paths:
        raise ValueError("At least one source path is required")

    resolved_transport = transport.lower().strip()
    if resolved_transport == "rsync" and not shutil.which("rsync"):
        resolved_transport = "sftp"

    if resolved_transport == "rsync":
        command = build_rsync_command(source_paths, destination, remote_path=remote_path)
        result = runner(command, capture_output=True, text=True, check=False, timeout=timeout)
    elif resolved_transport == "sftp":
        command, batch = build_sftp_command(source_paths, destination, remote_path=remote_path)
        result = runner(command, input=batch, capture_output=True, text=True, check=False, timeout=timeout)
    else:
        raise ValueError(f"Unsupported transport: {transport}")

    return {
        "success": result.returncode == 0,
        "transport": resolved_transport,
        "command": command,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }

