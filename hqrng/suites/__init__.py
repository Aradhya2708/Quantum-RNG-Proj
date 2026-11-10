"""Drivers for external randomness test suites.

Each driver exposes ``run(bitfile, ...) -> dict`` with at least
``{"suite", "status", "tests": [...], "log"}``; status is one of
``ok`` (ran), ``unavailable`` (tool not installed) or ``insufficient-data``.

Tools are looked up under $HQRNG_TOOLS (default: <repo>/third_party), as laid
out by tools/setup_tools.sh:
    $HQRNG_TOOLS/sts/assess[.exe]            NIST SP 800-22 STS 2.1.2
    $HQRNG_TOOLS/bin/testu01_file[.exe]      TestU01 file harness
    dieharder on PATH or $HQRNG_TOOLS/bin/   Dieharder
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXE = ".exe" if sys.platform == "win32" else ""


def tools_dir() -> Path:
    return Path(os.environ.get("HQRNG_TOOLS", REPO / "third_party"))


def find_tool(*candidates: str) -> str | None:
    for c in candidates:
        p = tools_dir() / c
        for q in (p, p.with_name(p.name + EXE)):
            if q.is_file():
                return str(q)
    for c in candidates:
        w = shutil.which(Path(c).name)
        if w:
            return w
    return None
