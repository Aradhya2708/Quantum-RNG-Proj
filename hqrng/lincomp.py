"""Linear-complexity diagnostic (Berlekamp-Massey over GF(2)).

A truly random n-bit sequence has linear complexity L ~ n/2. A sequence that
is a linear function of a Mersenne Twister (MT19937) state has L <= 19937, the
size of that state, no matter how long it is. Qiskit Aer draws its
measurement outcomes from MT19937, and each classical bit followed across the
shots of one circuit shows L = 19937 exactly -- see docs/FINDINGS.md.

    python -m hqrng.lincomp data/aer_D_ideal.bin --width 32 --n 50000
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from .bitio import read_bits

MT19937_DEGREE = 19937


def linear_complexity(bits: np.ndarray) -> int:
    s = np.asarray(bits, dtype=np.uint8)
    n = len(s)
    c = np.zeros(n + 1, np.uint8)
    b = np.zeros(n + 1, np.uint8)
    c[0] = b[0] = 1
    L, m = 0, -1
    for i in range(n):
        d = s[i] ^ (int(np.bitwise_and(c[1:L + 1], s[i - L:i][::-1]).sum()) & 1)
        if d:
            t = c.copy()
            shift = i - m
            c[shift:] ^= b[: n + 1 - shift]
            if 2 * L <= i:
                L, m, b = i + 1 - L, i, t
    return L


def column_profile(bits: np.ndarray, width: int = 32, n: int = 50_000,
                   columns=(0, -1)) -> dict:
    """Linear complexity of selected bit positions followed across n words."""
    rows = np.asarray(bits[: (len(bits) // width) * width], dtype=np.uint8).reshape(-1, width)
    n = min(n, len(rows))
    out = {}
    for j in columns:
        j = j % width
        out[f"bit{j}"] = linear_complexity(rows[:n, j])
    stream = linear_complexity(np.asarray(bits[:n], dtype=np.uint8))
    return dict(n=n, expected=n // 2, stream=stream, columns=out,
                mt19937_signature=any(v == MT19937_DEGREE for v in out.values()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--width", type=int, default=32)
    ap.add_argument("--n", type=int, default=50_000)
    ap.add_argument("--columns", default="0,15,31")
    a = ap.parse_args(argv)
    cols = tuple(int(c) for c in a.columns.split(","))
    bits = read_bits(a.file, a.width * a.n)
    print(json.dumps(column_profile(bits, a.width, a.n, cols), indent=2))


if __name__ == "__main__":
    main()
