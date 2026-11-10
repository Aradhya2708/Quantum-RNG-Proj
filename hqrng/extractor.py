"""Toeplitz-hashing randomness extractor (the standard QRNG post-processing).

Raw device bits are biased and possibly correlated: they carry h < 1 bits of
min-entropy per bit. A Toeplitz matrix T (m x n, over GF(2)) built from a
uniform seed is a two-universal hash, so by the Leftover Hash Lemma

        y = T . x  (mod 2),   m = floor(n * h  -  2 * log2(1 / eps))

is eps-close to uniform for any n-bit input block x with min-entropy >= n*h.
T is constant along diagonals, T[i, j] = s[i - j + n - 1], so it is fixed by
n + m - 1 seed bits and T.x is a convolution -- computed here with FFTs, block
by block, reusing one seed (allowed because the extractor is *strong*: the
output stays uniform even given the seed).

    python -m hqrng.extractor raw.bin out.bin --h-min 0.93 --block 16384

Use hqrng.entropy to get --h-min. The extractor only works if the input really
has that much *physical* min-entropy; it cannot create randomness from a
deterministic source (e.g. a PRNG -- see docs/FINDINGS.md).
"""
from __future__ import annotations

import argparse
import math
import os

import numpy as np

from .bitio import read_bits, read_meta, write_bits, write_meta


def output_length(n: int, h_min: float, eps: float = 2.0**-100, multiple: int = 8) -> int:
    """Leftover-hash-lemma output length for an n-bit block, rounded down."""
    m = math.floor(n * h_min - 2 * math.log2(1 / eps))
    m -= m % multiple
    if m <= 0:
        raise ValueError(f"block of {n} bits with h_min={h_min} is too small for eps={eps}")
    return m


def random_seed(n: int, m: int) -> np.ndarray:
    """n + m - 1 uniform seed bits from the OS CSPRNG."""
    k = n + m - 1
    return np.unpackbits(np.frombuffer(os.urandom((k + 7) // 8), dtype=np.uint8))[:k]


def toeplitz_matrix(seed: np.ndarray, n: int, m: int) -> np.ndarray:
    """Explicit m x n Toeplitz matrix (for testing; use toeplitz_extract for data)."""
    i = np.arange(m)[:, None]
    j = np.arange(n)[None, :]
    return np.asarray(seed, dtype=np.uint8)[i - j + n - 1]


def toeplitz_extract(bits: np.ndarray, n: int, m: int, seed: np.ndarray,
                     blocks_per_batch: int = 256) -> np.ndarray:
    """Hash every complete n-bit block of `bits` to m bits. Leftover bits are dropped."""
    seed = np.asarray(seed, dtype=np.float64)
    if len(seed) != n + m - 1:
        raise ValueError(f"seed must have n + m - 1 = {n + m - 1} bits, got {len(seed)}")
    n_blocks = len(bits) // n
    x = np.asarray(bits[: n_blocks * n], dtype=np.uint8).reshape(n_blocks, n)
    L = 1 << (2 * n + m - 2).bit_length()          # FFT size >= full convolution length
    S = np.fft.rfft(seed, L)
    out = np.empty((n_blocks, m), dtype=np.uint8)
    for a in range(0, n_blocks, blocks_per_batch):
        X = np.fft.rfft(x[a:a + blocks_per_batch].astype(np.float64), L, axis=1)
        conv = np.fft.irfft(X * S, L, axis=1)[:, n - 1:n - 1 + m]
        r = np.rint(conv)
        if np.max(np.abs(conv - r)) > 0.25:        # float64 FFT is exact far beyond our sizes
            raise RuntimeError("FFT rounding error too large; use a smaller block")
        out[a:a + blocks_per_batch] = r.astype(np.int64) & 1
    return out.reshape(-1)


def extract_file(src, dst, h_min: float, block: int = 16384, eps: float = 2.0**-100,
                 seed: np.ndarray | None = None) -> dict:
    bits = read_bits(src)
    m = output_length(block, h_min, eps)
    seed = random_seed(block, m) if seed is None else seed
    y = toeplitz_extract(bits, block, m, seed)
    write_bits(dst, y)
    np.packbits(seed).tofile(str(dst) + ".seed")
    meta = dict(source=str(src), source_meta=read_meta(src), extractor="toeplitz",
                block_n=block, out_m=m, ratio=m / block, h_min=h_min, eps=eps,
                n_bits_in=len(bits), n_bits=len(y) - len(y) % 8,
                seed_file=os.path.basename(str(dst)) + ".seed", seed_bits=len(seed))
    write_meta(dst, meta)
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--h-min", type=float, required=True, help="min-entropy per raw bit (0..1]")
    ap.add_argument("--block", type=int, default=16384, help="input block size n")
    ap.add_argument("--eps", type=float, default=2.0**-100)
    a = ap.parse_args(argv)
    meta = extract_file(a.src, a.dst, a.h_min, a.block, a.eps)
    print(f"n={meta['block_n']} -> m={meta['out_m']} (ratio {meta['ratio']:.4f}); "
          f"{meta['n_bits_in']:,} -> {meta['n_bits']:,} bits")


if __name__ == "__main__":
    main()
