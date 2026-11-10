"""Noise presets for the Aer simulation.

Why readout error is the only noise that matters here: every qubit ends in
|+> or |->, which give exactly 50/50 in the Z basis. Pauli (bit-flip, phase,
depolarizing) errors map |+>/|-> to |+>/|->, so they cannot bias the output;
neither can *symmetric* bit flips on the classical result (a fair bit XOR an
independent flip is still a fair bit). What real superconducting hardware does
have is *asymmetric* readout error -- |1> relaxes to |0> during measurement,
so P(read 0 | 1) is several times P(read 1 | 0) -- which biases the output
towards 0, differently on every qubit. That is what the extractor must fix.

Spec strings (used by the CLI and pipeline):
    none                 ideal simulator
    symmetric:P          P(flip) = P on every qubit, both directions
                         ("symmetric:0.02" reproduces noise_analysis.ipynb)
    readout:P10,P01      same asymmetric error on every qubit, where
                         P10 = P(read 0 | prepared 1), P01 = P(read 1 | prepared 0)
    ibm-like             per-qubit asymmetric error drawn once from a fixed
                         seed: P10 ~ U(1%, 6%), P01 ~ U(0.2%, 1.5%) -- the
                         range of published IBM Eagle/Heron calibration data
"""
from __future__ import annotations

import numpy as np
from qiskit_aer.noise import NoiseModel, ReadoutError

IBM_LIKE_SEED = 2026


def readout_table(spec: str, n_qubits: int) -> np.ndarray | None:
    """Return an (n_qubits, 2) array of [P01, P10] per qubit, or None."""
    spec = (spec or "none").strip().lower()
    if spec == "none":
        return None
    if spec.startswith("symmetric:"):
        p = float(spec.split(":", 1)[1])
        return np.tile([p, p], (n_qubits, 1))
    if spec.startswith("readout:"):
        p10, p01 = (float(x) for x in spec.split(":", 1)[1].split(","))
        return np.tile([p01, p10], (n_qubits, 1))
    if spec == "ibm-like":
        rng = np.random.default_rng(IBM_LIKE_SEED)
        p10 = rng.uniform(0.01, 0.06, n_qubits)
        p01 = rng.uniform(0.002, 0.015, n_qubits)
        return np.column_stack([p01, p10])
    raise ValueError(f"unknown noise spec {spec!r}")


def noise_model(spec: str, n_qubits: int) -> NoiseModel | None:
    table = readout_table(spec, n_qubits)
    if table is None:
        return None
    nm = NoiseModel()
    for q, (p01, p10) in enumerate(table):
        nm.add_readout_error(ReadoutError([[1 - p01, p01], [p10, 1 - p10]]), [q])
    return nm


def expected_p1(spec: str, n_qubits: int) -> np.ndarray:
    """P(output bit = 1) per qubit for an ideal 50/50 qubit under `spec`."""
    table = readout_table(spec, n_qubits)
    if table is None:
        return np.full(n_qubits, 0.5)
    p01, p10 = table[:, 0], table[:, 1]
    return 0.5 * (1 - p10) + 0.5 * p01
