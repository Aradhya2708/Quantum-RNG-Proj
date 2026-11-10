"""NIST SP 800-22 rev1a via the official Statistical Test Suite (STS 2.1.2).

Runs the protocol the standard prescribes -- m sequences of n bits each
(default 100 x 10^6) -- and evaluates every sub-test on the two second-level
criteria from SP 800-22 Sec. 4.2:

  * proportion of sequences passing at alpha = 0.01 must be at least
    p - 3*sqrt(p(1-p)/m), p = 0.99   (96/100 for m = 100)
  * uniformity of the m p-values: chi-square P-value >= 0.0001, applied only
    when m >= 55 (Sec. 4.2.2: fewer sequences make that chi-square meaningless;
    this mostly affects Random Excursions, which only uses sequences with
    >= 500 cycles, and the quick profile)

The single-sequence GUI run in the original README (one p-value per test on
1.6x10^5 bits) is not this protocol and cannot support a "passes NIST" claim.

    python -m hqrng.suites.nist_sts data/file.bin --streams 100 --n 1000000
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from . import find_tool, tools_dir

ROW = re.compile(
    r"^\s*((?:\d+\s+){10})(?P<pval>[\d.]+|----)\s*(?P<pstar>\*?)\s+"
    r"(?P<pass>\d+)/(?P<total>\d+)\s*(?P<rstar>\*?)\s+(?P<name>\S+)\s*$")


MIN_SEQ_UNIFORMITY = 55


def min_pass_rate(m: int, alpha: float = 0.01) -> float:
    p = 1 - alpha
    return p - 3 * math.sqrt(p * (1 - p) / m)


def min_pass_count(m: int, alpha: float = 0.01) -> int:
    """Smallest passing count, truncated to int exactly as STS 2.1.2 does (96 for m = 100)."""
    return int(min_pass_rate(m, alpha) * m)


def judge(row: dict) -> dict:
    total, passed, pval = row["total"], row["passed"], row["uniformity_p"]
    rate_ok = total > 0 and passed >= min_pass_count(total)
    unif_ok = pval is None or total < MIN_SEQ_UNIFORMITY or pval >= 1e-4
    return dict(row, proportion_ok=rate_ok, uniformity_ok=unif_ok, ok=rate_ok and unif_ok)


def parse_report(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        mo = ROW.match(line)
        if mo:
            rows.append(judge(dict(test=mo["name"], passed=int(mo["pass"]), total=int(mo["total"]),
                                   uniformity_p=None if mo["pval"] == "----" else float(mo["pval"]))))
    return rows


def allowed_failures(n_subtests: int, m: int, level: float = 0.01) -> int:
    """How many sub-tests of a family an ideal generator fails with probability >= 1 - level.

    One sub-test fails with probability P(Bin(m, 0.99) < min_pass_count) plus 1e-4
    for uniformity. NonOverlappingTemplate (148 sub-tests, m = 100) allows 3;
    a single-sub-test family allows 0.
    """
    from scipy.stats import binom
    p_sub = binom.cdf(min_pass_count(m) - 1, m, 0.99) + (1e-4 if m >= MIN_SEQ_UNIFORMITY else 0)
    k = 0
    while binom.sf(k, n_subtests, p_sub) >= level:
        k += 1
    return k


def summarize(rows: list[dict]) -> list[dict]:
    fam = defaultdict(list)
    for r in rows:
        fam[r["test"]].append(r)
    out = []
    for name, rs in fam.items():
        bad = [r for r in rs if not r["ok"]]
        pvals = [r["uniformity_p"] for r in rs if r["uniformity_p"] is not None]
        m = max(r["total"] for r in rs)
        allowed = allowed_failures(len(rs), m)
        verdict = "pass" if not bad else ("marginal" if len(bad) <= allowed else "fail")
        out.append(dict(test=name, subtests=len(rs), failed=len(bad), allowed_by_chance=allowed,
                        min_proportion=min(r["passed"] / r["total"] for r in rs if r["total"]),
                        min_uniformity_p=min(pvals) if pvals else None,
                        sequences=m, verdict=verdict))
    return out


def rejudge(result: dict) -> dict:
    """Re-apply the pass rules to a saved result (e.g. after changing them)."""
    if result.get("status") != "ok":
        return result
    rows = [judge(r) for r in result["tests"]]
    return dict(result, tests=rows, families=summarize(rows),
                failed_subtests=sum(not r["ok"] for r in rows),
                min_pass_count=min_pass_count(result["streams"]))


def run(bitfile, n: int = 1_000_000, streams: int = 100, sts_dir=None, keep: Path | None = None,
        timeout: float | None = None) -> dict:
    sts_dir = Path(sts_dir) if sts_dir else tools_dir() / "sts"
    exe = find_tool("sts/assess")
    if not exe or not (sts_dir / "templates").is_dir():
        return dict(suite="NIST SP 800-22", status="unavailable",
                    reason=f"STS not found under {sts_dir} (run tools/setup_tools.sh)", tests=[])
    available = Path(bitfile).stat().st_size * 8
    if available < n * streams:
        streams = available // n
        if streams < 1:
            return dict(suite="NIST SP 800-22", status="insufficient-data", tests=[],
                        reason=f"{available} bits < one sequence of {n}")

    # STS writes into ./experiments relative to its cwd and reads ./templates,
    # so each run gets a private copy of that layout (also allows parallel runs).
    work = Path(tempfile.mkdtemp(prefix="sts_", dir=tools_dir()))
    try:
        shutil.copytree(sts_dir / "templates", work / "templates")
        for d in (sts_dir / "experiments" / "AlgorithmTesting").iterdir():
            if d.is_dir():
                (work / "experiments" / "AlgorithmTesting" / d.name).mkdir(parents=True)
        shutil.copyfile(bitfile, work / "data.bin")   # STS limits the path to 200 chars
        answers = f"0\ndata.bin\n1\n0\n{streams}\n1\n"
        t0 = time.time()
        proc = subprocess.run([exe, str(n)], input=answers, text=True, cwd=work,
                              capture_output=True, timeout=timeout)
        report_path = work / "experiments" / "AlgorithmTesting" / "finalAnalysisReport.txt"
        report = report_path.read_text(errors="replace") if report_path.exists() else ""
        rows = parse_report(report)
        if keep:
            keep = Path(keep)
            keep.mkdir(parents=True, exist_ok=True)
            (keep / "finalAnalysisReport.txt").write_text(report)
            (keep / "stdout.txt").write_text(proc.stdout[-20000:])
        status = "ok" if rows else "error"
        return dict(suite="NIST SP 800-22", status=status, n=n, streams=streams,
                    min_pass_count=min_pass_count(streams), seconds=round(time.time() - t0, 1),
                    families=summarize(rows), subtests=len(rows),
                    failed_subtests=sum(not r["ok"] for r in rows), tests=rows,
                    reason=None if rows else proc.stdout[-2000:])
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--n", type=int, default=1_000_000)
    ap.add_argument("--streams", type=int, default=100)
    ap.add_argument("--keep", default=None, help="directory to save the raw STS report")
    a = ap.parse_args(argv)
    r = run(a.file, a.n, a.streams, keep=a.keep)
    r.pop("tests")
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
