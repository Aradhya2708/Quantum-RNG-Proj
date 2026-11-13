"""Dieharder (R. G. Brown) on a raw bit file.

Dieharder is a Linux tool: install it with `apt install dieharder` (Linux/WSL),
use the GitHub Actions workflow, or build it natively (we have built 3.31.1
with MinGW + GSL; put dieharder.exe in $HQRNG_TOOLS/bin).

The trap with file input: `dieharder -a` consumes many gigabytes, and when a
file runs out Dieharder silently REWINDS it and re-reads the same bits. Tests on
re-used data fail for the wrong reason. Two modes:

    python -m hqrng.suites.dieharder data/file.bin            # sized: no rewinds
    python -m hqrng.suites.dieharder data/file.bin --args -a  # classic -a run

Sized mode runs each "Good" test on its own, with the largest number of
p-samples (1, 30 or 100; with 2-10 the final KS test is degenerate) that the file supports without rewinding.
The plan is calibrated on a reference file of the same size (normally the
control) and then applied to every dataset, so all datasets get identical tests.
Tests that rewind even with one p-sample are reported as needing more data.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

from . import find_tool

ROW = re.compile(r"^\s*(?P<name>[\w.-]+)\|\s*(?P<ntup>\d+)\|\s*(?P<tsamples>\d+)\|"
                 r"\s*(?P<psamples>\d+)\|\s*(?P<p>[\d.eE+-]+)\|\s*(?P<verdict>PASSED|WEAK|FAILED)")
REWOUND = re.compile(r"rewound (\d+) times")
LISTED = re.compile(r"^\s*-d\s+(\d+)\s+(.+?)\s+(Good|Suspect|Do Not Use)\s*$")
P_STEPS = (1, 30, 100)   # 2-10 p-samples make the final KS test degenerate (p = 1.0)


def parse(text: str) -> tuple[list[dict], int]:
    tests = [dict(test=m["name"], ntup=int(m["ntup"]), tsamples=int(m["tsamples"]), psamples=int(m["psamples"]),
                  p_value=float(m["p"]), verdict=m["verdict"].lower())
             for m in map(ROW.match, text.splitlines()) if m]
    rewinds = max((int(x) for x in REWOUND.findall(text)), default=0)
    return tests, rewinds


def _exe():
    return find_tool("bin/dieharder")


def _call(exe, bitfile, args, timeout=None) -> tuple[list[dict], int, str]:
    # Dieharder truncates long file names, so run it next to the file.
    f = Path(bitfile).resolve()
    proc = subprocess.run([exe, *args, "-g", "201", "-f", f.name], capture_output=True, text=True,
                          timeout=timeout, cwd=f.parent)
    out = proc.stdout + proc.stderr
    tests, rewinds = parse(out)
    return tests, rewinds, out


def list_tests(exe=None, reliability=("Good",)) -> list[dict]:
    exe = exe or _exe()
    out = subprocess.run([exe, "-l"], capture_output=True, text=True).stdout
    return [dict(id=int(m[1]), name=m[2].strip(), reliability=m[3])
            for m in map(LISTED.match, out.splitlines()) if m and m[3] in reliability]


def calibrate(reference_file, exe=None, tests=None) -> list[dict]:
    """Largest p-sample count per test that does not rewind `reference_file`.

    The reference should be a good source (the control). A test whose result on
    it is exactly 0 or 1 at the chosen setting is degenerate there (this happens
    with some tests at one p-sample) and is left out of the plan.
    """
    exe = exe or _exe()
    plan = []
    for t in tests or list_tests(exe):
        best, rows_best = None, []
        for p in P_STEPS:
            rows, rewinds, _ = _call(exe, reference_file, ["-d", str(t["id"]), "-p", str(p)])
            if rewinds:
                break
            best, rows_best = p, rows
        note = None
        if best is None:
            note = "needs more data"
        elif any(r["p_value"] in (0.0, 1.0) for r in rows_best):
            best, note = None, "degenerate at this size (p = 0 or 1 on the control)"
        plan.append({**t, "psamples": best, "note": note})
    return plan


def summarize(tests: list[dict]) -> dict:
    return dict(passed=sum(t["verdict"] == "passed" for t in tests),
                weak=sum(t["verdict"] == "weak" for t in tests),
                failed=sum(t["verdict"] == "failed" for t in tests))


def run_sized(bitfile, plan) -> dict:
    exe = _exe()
    if not exe:
        return dict(suite="Dieharder", status="unavailable", tests=[], reason="dieharder not installed")
    t0 = time.time()
    tests, skipped, rewound = [], [], []
    for t in plan:
        if not t["psamples"]:
            skipped.append(t["name"])
            continue
        rows, rewinds, _ = _call(exe, bitfile, ["-d", str(t["id"]), "-p", str(t["psamples"])])
        if rewinds:
            rewound.append(t["name"])
        for r in rows:
            r.update(test_id=t["id"], test_name=t["name"], rewinds=rewinds)
        tests += rows
    return dict(suite="Dieharder", status="ok" if tests else "error", mode="sized", seconds=round(time.time() - t0, 1),
                tests=tests, skipped_need_more_data=skipped, rewound=rewound, **summarize(tests))


def run(bitfile, args=("-a",), timeout=None) -> dict:
    exe = _exe()
    if not exe:
        return dict(suite="Dieharder", status="unavailable", tests=[],
                    reason="dieharder not installed (Linux/WSL: apt install dieharder; or use CI)")
    t0 = time.time()
    tests, rewinds, out = _call(exe, bitfile, list(args), timeout)
    return dict(suite="Dieharder", status="ok" if tests else "error", mode="classic", rewinds=rewinds,
                seconds=round(time.time() - t0, 1), tests=tests, **summarize(tests),
                log=None if tests else out[-4000:])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--args", default=None, help="classic mode: dieharder arguments, e.g. '-a' or '-d 0'")
    ap.add_argument("--reference", default=None, help="sized mode: file to calibrate on (default: the file itself)")
    a = ap.parse_args(argv)
    if a.args:
        r = run(a.file, tuple(a.args.split()))
    else:
        plan = calibrate(a.reference or a.file)
        r = run_sized(a.file, plan)
        r["plan"] = plan
    print(json.dumps({k: v for k, v in r.items() if k != "tests"}, indent=2))


if __name__ == "__main__":
    main()
