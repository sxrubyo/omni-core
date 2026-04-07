"""Common utility functions"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

def check_command_exists(cmd: str) -> bool:
    """Check if command exists in PATH"""
    result = subprocess.run(['which', cmd], capture_output=True)
    return result.returncode == 0

def run_command(cmd: str, cwd: Optional[Path] = None) -> int:
    """Run shell command"""
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode

def run_command_output(cmd: str, cwd: Optional[Path] = None) -> tuple:
    """Run shell command and get output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr

def get_file_size(path: Path) -> str:
    """Get human-readable file size"""
    size = path.stat().st_size
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"
