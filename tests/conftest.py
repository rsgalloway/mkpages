"""Pytest configuration for local source-tree imports."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
LIB_ROOT = PROJECT_ROOT / "lib"

src_path = str(SRC_ROOT)
lib_path = str(LIB_ROOT)

if lib_path in sys.path:
    sys.path.remove(lib_path)
if src_path not in sys.path:
    sys.path.insert(0, src_path)
