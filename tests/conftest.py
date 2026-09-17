"""
Pytest configuration for ACO System.

Adds the project root to sys.path so `import core.database`, `import agents.*`,
etc. work the same way the running scripts do. Tests use a temporary SQLite
file per-test via the `db_session` fixture; they never touch the project data
directory.
"""
import sys
from pathlib import Path

# Make `import core.database` resolve when tests are run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))