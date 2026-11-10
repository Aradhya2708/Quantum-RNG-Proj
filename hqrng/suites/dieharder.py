"""Dieharder (R. G. Brown) on a raw bit file.

Dieharder has no native Windows build. Run it on Linux, inside WSL
(`sudo apt install dieharder`), or let the GitHub Actions workflow in
.github/workflows/randomness.yml run it.

Caveat that matters for QRNG data: `dieharder -a` consumes far more data than
a simulator run produces, and with file input it silently REWINDS the file
when it runs out. Re-used data makes tests fail for the wrong reason, so the
number of rewinds is recorded and any test run on rewound data should be read
with that in mind.

    python -m hqrng.suites.dieharder data/file.bin
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time

from . import find_tool

ROW = re.compile(r"^\s*(?P<name>[\w.-]+)\|\s*(?P<ntup>\d+)\|\s*(?P<tsamples>\d+)\|"
                 r"\s*(?P<psamples>\d+)\|\s*(?P<p>[\d.eE+-]+)\|\s*(?P<verdict>PASSED|WEAK|FAILED)")
REWOUND = re.compile(r"rewound (\d+) times")


def parse(text: str) -> tuple[list[dict], int]:
    tests = [dict(test=m["name"], ntup=int(m["ntup"]), p_value=float(m["p"]),
                  verdict=m["verdict"].lower())
             for m in map(ROW.match, text.splitlines()) if m]
    rewinds = max((int(x) for x in REWOUND.findall(text)), default=0)
    return tests, rewinds


def run(bitfile, args=("-a",), timeout=None) -> dict:
    exe = find_tool("bin/dieharder")
    if not exe:
        return dict(suite="Dieharder", status="unavailable", tests=[],
                    reason="dieharder not installed (Linux/WSL: apt install dieharder; or use CI)")
    t0 = time.time()
    proc = subprocess.run([exe, *args, "-g", "201", "-f", str(bitfile)],
                          capture_output=True, text=True, timeout=timeout)
    tests, rewinds = parse(proc.stdout + proc.stderr)
    return dict(suite="Dieharder", status="ok" if tests else "error", rewinds=rewinds,
                seconds=round(time.time() - t0, 1), tests=tests,
                passed=sum(t["verdict"] == "passed" for t in tests),
                weak=sum(t["verdict"] == "weak" for t in tests),
                failed=sum(t["verdict"] == "failed" for t in tests),
                log=None if tests else (proc.stdout + proc.stderr)[-4000:])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--args", default="-a", help="dieharder test selection, e.g. '-d 0' or '-a'")
    a = ap.parse_args(argv)
    r = run(a.file, tuple(a.args.split()))
    print(json.dumps({k: v for k, v in r.items() if k != "tests"}, indent=2))


if __name__ == "__main__":
    main()
