"""Min-entropy estimates in the style of NIST SP 800-90B (non-IID track).

This implements two of the ten 800-90B estimators -- Most Common Value
(Sec. 6.3.1) and Markov (Sec. 6.3.3) -- plus a per-qubit MCV, which matters
because every qubit has its own readout bias. They are enough to size the
Toeplitz extractor; for a formal 800-90B claim run NIST's full tool
(github.com/usnistgov/SP800-90B_EntropyAssessment, `ea_non_iid -i 1 <file> 1`).

    python -m hqrng.entropy data/aer_D_ibm.bin --width 32
"""
from __future__ import annotations

import argparse
import json
import math

import numpy as np

from .bitio import read_bits

Z_99 = 2.576  # 800-90B uses the upper 99% confidence bound


def mcv(samples: np.ndarray) -> float:
    """Most Common Value estimate, bits per sample (800-90B Sec. 6.3.1)."""
    samples = np.asarray(samples)
    L = len(samples)
    p_hat = np.bincount(samples.astype(np.int64)).max() / L
    p_u = min(1.0, p_hat + Z_99 * math.sqrt(p_hat * (1 - p_hat) / (L - 1)))
    return -math.log2(p_u)


def markov(bits: np.ndarray) -> float:
    """Markov estimate for binary data, bits per bit (800-90B Sec. 6.3.3)."""
    b = np.asarray(bits, dtype=np.uint8)
    L = len(b)
    p1 = b.mean()
    p0 = 1 - p1
    pairs = b[:-1] * 2 + b[1:]
    c = np.bincount(pairs, minlength=4).astype(float)    # 00, 01, 10, 11
    p00 = c[0] / max(c[0] + c[1], 1); p01 = 1 - p00
    p10 = c[2] / max(c[2] + c[3], 1); p11 = 1 - p10
    with np.errstate(divide="ignore"):
        cands = [
            p0 * p00 ** 127,
            p0 * p01 ** 64 * p10 ** 63,
            p0 * p01 * p11 ** 126,
            p1 * p10 * p00 ** 126,
            p1 * p10 ** 64 * p01 ** 63,
            p1 * p11 ** 127,
        ]
    p_max = max(cands)
    return min(-math.log2(p_max) / 128, 1.0)


def per_column_mcv(bits: np.ndarray, width: int) -> np.ndarray:
    """MCV estimate for each bit position of `width`-bit words.

    A position is one qubit only if the qubit -> clbit map is fixed. Models C
    and D re-draw that map every circuit, so a column then mixes several
    qubits; since -log2 is convex this can only *lower* the estimate (safe).
    """
    n = len(bits) - len(bits) % width
    cols = np.asarray(bits[:n], dtype=np.uint8).reshape(-1, width)
    return np.array([mcv(cols[:, j]) for j in range(width)])


def assess(bits: np.ndarray, width: int = 32) -> dict:
    """All estimates; `h_min` is the most conservative, per bit."""
    cols = per_column_mcv(bits, width)
    res = dict(
        n_bits=int(len(bits)),
        ones_fraction=float(np.mean(bits)),
        mcv=mcv(bits),
        markov=markov(bits),
        per_qubit_mcv_mean=float(cols.mean()),
        per_qubit_mcv_min=float(cols.min()),
        per_qubit_ones_fraction=np.asarray(bits[: len(bits) - len(bits) % width]).reshape(-1, width).mean(0).round(5).tolist(),
    )
    # A block of `width` consecutive bits spans every qubit once, so the
    # per-qubit *mean* is the right per-bit figure for block extraction.
    res["h_min"] = min(res["mcv"], res["markov"], res["per_qubit_mcv_mean"])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--width", type=int, default=32, help="bits per shot (qubits)")
    ap.add_argument("--max-bits", type=float, default=None)
    a = ap.parse_args(argv)
    bits = read_bits(a.file, None if a.max_bits is None else int(a.max_bits))
    r = assess(bits, a.width)
    r.pop("per_qubit_ones_fraction")
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
