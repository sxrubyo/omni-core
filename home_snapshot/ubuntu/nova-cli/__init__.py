#!/usr/bin/env python3
"""Nova CLI Package Configuration"""

from pathlib import Path

# Package metadata
__version__ = "1.0.0"
__author__ = "Your Organization"
__license__ = "MIT"

# Directories
NOVA_HOME = Path(__file__).parent
LIB_DIR = NOVA_HOME / 'lib'
COMMANDS_DIR = NOVA_HOME / 'commands'
TESTS_DIR = NOVA_HOME / 'tests'
DOCS_DIR = NOVA_HOME / 'docs'

# Defaults
DEFAULT_BACKUP_DIR = Path.home() / 'nova-backups'
DEFAULT_LOG_FILE = Path.home() / '.nova' / 'nova-cli.log'

# Ensure directories exist
DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
