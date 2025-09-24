# scripts/python/import_helper.py
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
paths_to_add = [
    str(PROJECT_ROOT / "src"),
    str(PROJECT_ROOT / "scripts" / "python")
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)