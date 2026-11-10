"""End-to-end randomness evaluation: generate -> estimate entropy -> extract -> test.

    python -m hqrng.pipeline --profile full --out results/run1 --workers 8

Datasets (all Model D, 32 qubits, unless noted):

  urandom             control: the OS CSPRNG. Should pass everything.
  aer_D_5k            the notebooks' setup: 5000 shots per circuit, re-seeded
  aer_D_ideal         noiseless, 100k shots per circuit (a bulk generator)
  aer_D_sym2pct       + 2% symmetric readout flips (noise_analysis.ipynb)
  aer_D_ibmlike       + per-qubit asymmetric readout error (biased, hardware-like)
  aer_D_ibmlike_toeplitz   the previous one after Toeplitz extraction

Suites: NIST SP 800-22 (STS), TestU01 (Rabbit, Alphabit, LinearComp),
Dieharder (if installed), plus the 800-90B-style entropy estimates and a
Berlekamp-Massey linear-complexity check. Results go to <out>/summary.md and
<out>/summary.json; raw data to --data-dir (not committed).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import entropy, extractor, lincomp
from .bitio import read_bits, read_meta, write_meta
from .generate import generate
from .suites import dieharder, nist_sts, testu01

PROFILES = {
    # bits per dataset; NIST uses 10^6-bit sequences, LinearComp needs 2.6e7 bits
    "quick": dict(bits=32_000_000),
    "full": dict(bits=100_000_000),
}
DATASETS = {
    "urandom": dict(kind="urandom"),
    "aer_D_5k": dict(kind="aer", noise="none", shots=5_000),
    "aer_D_ideal": dict(kind="aer", noise="none", shots=100_000),
    "aer_D_sym2pct": dict(kind="aer", noise="symmetric:0.02", shots=100_000),
    "aer_D_ibmlike": dict(kind="aer", noise="ibm-like", shots=100_000, oversample=1.10),
    "aer_D_ibmlike_toeplitz": dict(kind="toeplitz", source="aer_D_ibmlike"),
}


def make_dataset(name, spec, n_bits, data_dir: Path, workers: int, seed: int) -> Path:
    path = data_dir / f"{name}.bin"
    if path.exists() and read_meta(path).get("n_bits", 0) >= n_bits:
        print(f"[{name}] reusing {path}")
        return path
    print(f"[{name}] generating {n_bits:,} bits")
    if spec["kind"] == "urandom":
        with open(path, "wb") as f:
            left = n_bits // 8
            while left:
                k = min(left, 1 << 24)
                f.write(os.urandom(k))
                left -= k
        write_meta(path, dict(source="os.urandom", n_bits=n_bits))
    elif spec["kind"] == "aer":
        generate(path, int(n_bits * spec.get("oversample", 1.0)), "D", 32, spec["shots"],
                 spec["noise"], seed, workers, quiet=True)
    elif spec["kind"] == "toeplitz":
        src = data_dir / f"{spec['source']}.bin"
        est = entropy.assess(read_bits(src), 32)
        meta = extractor.extract_file(src, path, est["h_min"])
        meta["entropy_estimate"] = est
        write_meta(path, meta)
    return path


def analyse(name, path, suites, n_seq) -> dict:
    bits = read_bits(path)
    res = dict(dataset=name, file=str(path), meta=read_meta(path), n_bits=int(len(bits)))
    res["entropy"] = entropy.assess(bits, 32)
    res["lincomp"] = lincomp.column_profile(bits, 32, 50_000, (0, 15, 31))
    del bits

    jobs = {}
    with ThreadPoolExecutor(3) as ex:
        if "nist" in suites:
            jobs["nist"] = ex.submit(nist_sts.run, path, 1_000_000, n_seq)
        if "testu01" in suites:
            jobs["testu01"] = ex.submit(testu01.run, path)
        if "dieharder" in suites:
            jobs["dieharder"] = ex.submit(dieharder.run, path)
        for k, fut in jobs.items():
            res[k] = fut.result()
    return res


def fmt_nist(r):
    if not r or r.get("status") != "ok":
        return (r or {}).get("status", "-")
    fails = [f["test"] for f in r["families"] if f["verdict"] == "fail"]
    marginal = [f["test"] for f in r["families"] if f["verdict"] == "marginal"]
    s = f"{r['subtests'] - r['failed_subtests']}/{r['subtests']} ({r['streams']} seq)"
    if fails:
        return s + f" ✗ {', '.join(fails)}"
    return s + (f" ✓ (within chance: {', '.join(marginal)})" if marginal else " ✓")


def fmt_tu(r, battery):
    if not r or r.get("status") != "ok":
        return (r or {}).get("status", "-")
    b = next((x for x in r["batteries"] if x["battery"] == battery), None)
    if not b:
        return "-"
    if b["status"] != "ok":
        return b["status"]
    n = len(b["tests"])
    tag = "✓" if not b["failed"] and not b["suspicious"] else ("✗" if b["failed"] else "?")
    extra = f", {b['suspicious']} susp." if b["suspicious"] else ""
    return f"{n - b['failed'] - b['suspicious']}/{n}{extra} {tag}"


def fmt_dh(r):
    if not r or r.get("status") != "ok":
        return (r or {}).get("status", "-")
    s = f"{r['passed']}P/{r['weak']}W/{r['failed']}F"
    return s + (f" (rewound {r['rewinds']}×)" if r["rewinds"] else "")


def _strip_paths(obj):
    """Replace absolute file paths by bare file names (keeps results shareable)."""
    if isinstance(obj, dict):
        return {k: _strip_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_paths(v) for v in obj]
    if isinstance(obj, str) and os.path.isabs(obj) and len(obj) < 1000:
        return os.path.basename(obj)
    return obj


def write_summary(out: Path, results: list[dict], profile: str):
    results = _strip_paths(results)
    (out / "summary.json").write_text(json.dumps(results, indent=1, default=str))
    L = [f"# Randomness test summary ({profile} profile)", "",
         f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC} by `python -m hqrng.pipeline`.", "",
         "| Dataset | Bits | Ones % | h_min/bit | Linear complexity per qubit (ideal ≈ n/2) "
         "| NIST SP 800-22 sub-tests passed | TestU01 Rabbit | TestU01 Alphabit | TestU01 LinearComp | Dieharder |",
         "|---|---:|---:|---:|---|---|---|---|---|---|"]
    for r in results:
        lc = r["lincomp"]
        lcs = ", ".join(str(v) for v in lc["columns"].values())
        lcs = f"{lcs} (n={lc['n']})" + (" **MT19937**" if lc["mt19937_signature"] else "")
        e = r["entropy"]
        L.append(f"| `{r['dataset']}` | {r['n_bits']:.2e} | {100 * e['ones_fraction']:.3f} | {e['h_min']:.4f} | {lcs} "
                 f"| {fmt_nist(r.get('nist'))} | {fmt_tu(r.get('testu01'), 'rabbit')} "
                 f"| {fmt_tu(r.get('testu01'), 'alphabit')} | {fmt_tu(r.get('testu01'), 'lincomp')} "
                 f"| {fmt_dh(r.get('dieharder'))} |")
    L += ["", "## Failing or suspicious results", ""]
    any_bad = False
    for r in results:
        rows = []
        n = r.get("nist") or {}
        for f in n.get("families", []):
            if f["verdict"] != "pass":
                rows.append(f"NIST {f['test']}: {f['failed']}/{f['subtests']} sub-tests failed "
                            f"(min proportion {f['min_proportion']:.2f}, min uniformity P {f['min_uniformity_p']})")
        for t in (r.get("testu01") or {}).get("tests", []):
            if t["verdict"] != "pass":
                rows.append(f"TestU01 {t['battery']} / {t['test']}: p = {t['p_value']:.3g} ({t['verdict']})")
        for t in (r.get("dieharder") or {}).get("tests", []):
            if t["verdict"] != "passed":
                rows.append(f"Dieharder {t['test']} (ntup {t['ntup']}): p = {t['p_value']:.3g} ({t['verdict']})")
        if rows:
            any_bad = True
            L += [f"**{r['dataset']}**", ""] + [f"- {x}" for x in rows] + [""]
    if not any_bad:
        L.append("None.")
    L += ["", "## Notes", "",
          "- NIST: 188 sub-tests, each judged on proportion (≥ 0.99 − 3σ) and P-value uniformity (≥ 1e-4; "
          "only applied with ≥ 55 sequences, per SP 800-22 §4.2.2). Random Excursions only uses sequences "
          "with ≥ 500 cycles (~60%), so its sample is smaller. With 148 NonOverlappingTemplate sub-tests "
          "an ideal source fails up to 3 by chance (99% level); the table calls that \"marginal\".",
          "- TestU01 Rabbit/Alphabit: nb (sequence length) is chosen so the file is never exhausted "
          "(they read ~23× and ~9× nb bits).",
          "- TestU01: suspicious = p outside [0.001, 0.999]; fail = outside [1e-10, 1 − 1e-10]. "
          "LinearComp uses BigCrush's parameters (n = 400020, bits 0 and 29 of each word).",
          "- h_min: most conservative of the SP 800-90B MCV, Markov and per-qubit MCV estimates.",
          "- Linear complexity: Berlekamp–Massey on single bit positions followed across shots; "
          "19937 is the Mersenne Twister state size."]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=PROFILES, default="quick")
    ap.add_argument("--out", default="results/latest")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--datasets", default=",".join(DATASETS))
    ap.add_argument("--suites", default="nist,testu01,dieharder")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--parallel", type=int, default=3, help="datasets analysed at once")
    ap.add_argument("--seed", type=int, default=20261107)
    ap.add_argument("--resummarize", action="store_true",
                    help="only rebuild <out>/summary.md from <out>/summary.json")
    a = ap.parse_args(argv)
    if a.resummarize:
        out = Path(a.out)
        results = json.loads((out / "summary.json").read_text())
        for r in results:
            if "nist" in r:
                r["nist"] = nist_sts.rejudge(r["nist"])
        write_summary(out, results, a.profile)
        print(f"rewrote {out / 'summary.md'}")
        return

    n_bits = PROFILES[a.profile]["bits"]
    n_seq = n_bits // 1_000_000
    out, data_dir = Path(a.out), Path(a.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    names = a.datasets.split(",")
    suites = set(a.suites.split(","))

    t0 = time.time()
    paths = {}
    for i, name in enumerate(names):
        spec = DATASETS[name]
        if spec["kind"] == "toeplitz" and spec["source"] not in paths:
            paths[spec["source"]] = make_dataset(spec["source"], DATASETS[spec["source"]], n_bits,
                                                 data_dir, a.workers, a.seed + 100)
        paths[name] = make_dataset(name, spec, n_bits, data_dir, a.workers, a.seed + i)

    print(f"data ready in {time.time() - t0:.0f}s; running suites {sorted(suites)}")
    with ThreadPoolExecutor(a.parallel) as ex:
        futs = [ex.submit(analyse, n, paths[n], suites, n_seq) for n in names]
        results = []
        for n, f in zip(names, futs):
            results.append(f.result())
            print(f"[{n}] done ({time.time() - t0:.0f}s)", flush=True)
    write_summary(out, results, a.profile)
    print(f"wrote {out / 'summary.md'} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
