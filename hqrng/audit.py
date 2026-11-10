"""Reproduce the checks behind docs/FINDINGS.md (about a minute).

    python -m hqrng.audit
"""
from __future__ import annotations

from math import log2, pi, sqrt

import numpy as np
from qiskit.quantum_info import Statevector, entropy, partial_trace
from qiskit_aer import AerSimulator

from .circuits import build_circuit
from .lincomp import linear_complexity


def main():
    rng = np.random.default_rng(1)

    print("1. Do the CNOT layers entangle anything? (6-qubit statevectors, 20 random runs per model)")
    for model in "ABCD":
        ent = dev = 0.0
        for _ in range(20):
            sv = Statevector(build_circuit(model, 6, rng).remove_final_measurements(inplace=False))
            dev = max(dev, float(np.max(np.abs(sv.probabilities() - 1 / 64))))
            for k in range(6):
                ent = max(ent, entropy(partial_trace(sv, [j for j in range(6) if j != k]), base=2))
        print(f"   Model {model}: max entanglement entropy {ent:.1e} bits, max |P(x) - 1/64| {dev:.1e}")
    print("   -> every model prepares the same uniform product state: H|0>, H|1> are |+>, |->,")
    print("      and CNOT maps products of |+>/|-> to products of |+>/|->.")

    sim = AerSimulator()
    qc = build_circuit("D", 32, np.random.default_rng(7))
    print("\n2. What is AerSimulator doing?")
    r1 = sim.run(qc, shots=2000, memory=True, seed_simulator=42).result()
    r2 = sim.run(qc, shots=2000, memory=True, seed_simulator=42).result()
    print(f"   method = {r1.results[0].metadata.get('method')}; "
          f"same seed_simulator -> identical output: {r1.get_memory() == r2.get_memory()}")

    print("\n3. 'Shannon entropy' of the counts dictionary vs log2(shots)")
    for shots in (2000, 5000, 20000):
        c = sim.run(qc, shots=shots).result().get_counts()
        p = np.array(list(c.values())) / shots
        print(f"   shots={shots:6d}: H = {-np.sum(p * np.log2(p)):.4f}   log2(shots) = {log2(shots):.4f}   "
              f"distinct outcomes = {len(c)}")
    n = 5000
    print(f"   P(some 32-bit outcome repeats in 5000 shots) = {1 - np.exp(-n * (n - 1) / 2 / 2**32):.4f} "
          "(one repeat gives min-entropy log2(5000/2) = 11.29)")

    print("\n4. Average |off-diagonal correlation| expected from sampling noise alone, sqrt(2/(pi N))")
    for N in (2000, 5000):
        print(f"   N={N}: {sqrt(2 / (pi * N)):.4f}")

    print("\n5. Linear complexity (random: ~n/2; Mersenne Twister: 19937)")
    mem = sim.run(qc, shots=50_000, memory=True).result().get_memory()
    rows = np.frombuffer("".join(mem).encode(), np.uint8).reshape(-1, 32) - ord("0")
    for j in (0, 15, 31):
        print(f"   clbit {31 - j:2d} across 50000 shots of one circuit: L = {linear_complexity(rows[:, j])}")
    ref = np.random.default_rng(0).integers(0, 2, 50_000, dtype=np.uint8)
    print(f"   numpy PCG64 reference, 50000 bits:            L = {linear_complexity(ref)}")


if __name__ == "__main__":
    main()
