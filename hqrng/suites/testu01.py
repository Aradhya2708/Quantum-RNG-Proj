"""TestU01 (L'Ecuyer & Simard) on a finite bit file, via tools/testu01_file.c.

Batteries:
  rabbit     Rabbit   -- built for finite hardware-RNG bit files; nb chosen so
             the file is never exhausted (Rabbit reads ~23 bits per bit of nb)
  alphabit   Alphabit -- likewise (~9 bits per bit of nb)
  lincomp    BigCrush's two LinearComp tests (bits 0 and 29 of each word).
             This is the test that exposes Aer's Mersenne Twister.
  smallcrush SmallCrush -- needs ~2.3e8 words (7.3 Gbit / 0.9 GB) of data

Verdict per p-value follows the TestU01 guide: outside [0.001, 0.999] is
"suspicious"; outside [1e-10, 1 - 1e-10] is a clear failure.

    python -m hqrng.suites.testu01 data/file.bin --batteries rabbit,alphabit,lincomp
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time

from . import find_tool

SMALLCRUSH_WORDS = 226_594_193  # measured with tools/testu01_file on /dev/urandom data
LINCOMP_WORDS = 800_040
# Rabbit/Alphabit take a sequence length nb (bits) but each of their tests draws
# its own fresh data: measured consumption is ~0.714 and ~0.282 words per bit of nb.
WORDS_PER_NB = {"rabbit": 0.7143, "alphabit": 0.2813}


def choose_nb(battery: str, available_words: int) -> int | None:
    """Largest power-of-two nb whose data need fits in the file (5% margin)."""
    k = WORDS_PER_NB[battery]
    nb = 1 << 30
    while nb >= 1 << 16:
        if nb * k * 1.05 <= available_words:
            return nb
        nb >>= 1
    return None


def classify(p: float) -> str:
    if p < 1e-10 or p > 1 - 1e-10:
        return "fail"
    if p < 1e-3 or p > 1 - 1e-3:
        return "suspicious"
    return "pass"


def run_battery(bitfile, battery: str, exe: str, timeout=None) -> dict:
    t0 = time.time()
    words = os.path.getsize(bitfile) // 4
    cmd = [exe, battery, str(bitfile)]
    nb = None
    if battery in WORDS_PER_NB:
        nb = choose_nb(battery, words)
        if nb is None:
            return dict(battery=battery, status="insufficient-data", words_available=words, tests=[],
                        failed=0, suspicious=0, seconds=0.0, words_used=None, nb=None, log=None)
        cmd.append(str(nb))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    tests, used, exhausted = [], None, None
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if parts[0] == "RESULT" and len(parts) == 3:
            p = float(parts[2])
            tests.append(dict(test=parts[1], p_value=p, verdict=classify(p)))
        elif parts[0] == "WORDS_USED":
            used = int(parts[1])
        elif parts[0] == "EXHAUSTED":
            exhausted = int(parts[1])
    if exhausted is not None:
        status = "insufficient-data"
    elif proc.returncode != 0 or not tests:
        status = "error"
    else:
        status = "ok"
    return dict(battery=battery, status=status, nb=nb, words_used=used, words_available=exhausted,
                seconds=round(time.time() - t0, 1), tests=tests,
                failed=sum(t["verdict"] == "fail" for t in tests),
                suspicious=sum(t["verdict"] == "suspicious" for t in tests),
                log=proc.stdout[-6000:] if status != "ok" else None)


def run(bitfile, batteries=("rabbit", "alphabit", "lincomp"), timeout=None) -> dict:
    exe = find_tool("bin/testu01_file")
    if not exe:
        return dict(suite="TestU01", status="unavailable", tests=[],
                    reason="testu01_file not built (run tools/setup_tools.sh)")
    results = [run_battery(bitfile, b, exe, timeout) for b in batteries]
    return dict(suite="TestU01", status="ok", batteries=results,
                tests=[dict(t, battery=r["battery"]) for r in results for t in r["tests"]])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--batteries", default="rabbit,alphabit,lincomp")
    a = ap.parse_args(argv)
    r = run(a.file, tuple(a.batteries.split(",")))
    r.pop("tests")
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
