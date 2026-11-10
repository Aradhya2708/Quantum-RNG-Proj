"""Bitstream file formats.

Canonical format for every suite here: a *raw* file of packed bits, MSB first
(numpy.packbits order), no header. NIST STS (binary mode), TestU01
(tools/testu01_file.c) and Dieharder (-g 201) all read this directly.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np


def write_bits(path, bits: np.ndarray) -> Path:
    """Write an array of 0/1 values as packed raw bytes (length rounded down to 8)."""
    bits = np.asarray(bits, dtype=np.uint8)
    n = len(bits) - len(bits) % 8
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.packbits(bits[:n]).tofile(path)
    return path


def read_bits(path, n_bits: int | None = None) -> np.ndarray:
    """Read a raw packed file back into a 0/1 uint8 array."""
    count = -1 if n_bits is None else (n_bits + 7) // 8
    data = np.fromfile(path, dtype=np.uint8, count=count)
    bits = np.unpackbits(data)
    return bits if n_bits is None else bits[:n_bits]


def n_bits_in(path) -> int:
    return Path(path).stat().st_size * 8


def write_meta(path, meta: dict) -> Path:
    p = Path(str(path) + ".json")
    p.write_text(json.dumps(meta, indent=2, default=str))
    return p


def read_meta(path) -> dict:
    p = Path(str(path) + ".json")
    return json.loads(p.read_text()) if p.exists() else {}


def read_qrng_header_bin(path) -> np.ndarray:
    """Read the 'QRNG'-header format written by noise_analysis.ipynb.

    Layout: b'QRNG', uint32 LE num_shots, uint32 LE num_bits, then one uint32 LE
    per shot whose binary expansion (MSB first) is the shot's bitstring.
    Returns the (num_shots, num_bits) bit matrix.
    """
    raw = Path(path).read_bytes()
    if raw[:4] != b"QRNG":
        raise ValueError(f"{path} is not a QRNG-header file")
    shots, width = struct.unpack("<II", raw[4:12])
    words = np.frombuffer(raw[12:12 + 4 * shots], dtype="<u4")
    shifts = np.arange(width - 1, -1, -1, dtype=np.uint32)
    return ((words[:, None] >> shifts) & 1).astype(np.uint8)
