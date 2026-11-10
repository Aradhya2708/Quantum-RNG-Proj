"""The four Hybrid-QRNG circuit models from Quantum_random_number_generator.ipynb.

All models share: classical seed bits -> X gates -> Hadamard on every qubit ->
[CNOT layer] -> measure. They differ in two switches:

    Model  CNOT layer                    Measurement order
    A      none                          qubit i -> clbit i
    B      shuffled fixed pairs          qubit i -> clbit i
    C      none                          random permutation ("dice")
    D      random pairs ("dice")         random permutation ("dice")

Randomness for the seed bits and the "dice" comes from a numpy Generator so a
run can be reproduced from its seed (the notebooks used unseeded
np.random / random).
"""
from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

MODELS = {
    "A": dict(cnot=False, dice_measure=False),
    "B": dict(cnot=True, dice_measure=False),
    "C": dict(cnot=False, dice_measure=True),
    "D": dict(cnot=True, dice_measure=True),
}


def build_circuit(model: str = "D", n_qubits: int = 32,
                  rng: np.random.Generator | None = None) -> QuantumCircuit:
    """Return the measured circuit for one run of `model`."""
    if model not in MODELS:
        raise ValueError(f"model must be one of {sorted(MODELS)}, got {model!r}")
    rng = rng if rng is not None else np.random.default_rng()
    cfg = MODELS[model]

    qc = QuantumCircuit(n_qubits, n_qubits)
    seed_bits = rng.integers(0, 2, n_qubits)          # "classical shot-noise seed"
    for q, b in enumerate(seed_bits):
        if b:
            qc.x(q)
    qc.h(range(n_qubits))
    if cfg["cnot"]:
        order = rng.permutation(n_qubits)              # random perfect matching
        for i in range(0, n_qubits - 1, 2):
            qc.cx(int(order[i]), int(order[i + 1]))
    if cfg["dice_measure"]:
        for clbit, q in enumerate(rng.permutation(n_qubits)):
            qc.measure(int(q), clbit)
    else:
        qc.measure(range(n_qubits), range(n_qubits))
    return qc
