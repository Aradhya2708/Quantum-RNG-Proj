"""Generate large bitstreams from the Hybrid-QRNG models.

    python -m hqrng.generate --model D --bits 100000000 --noise ibm-like \\
        --out data/aer_D_ibm.bin --workers 8 --seed 1

Differences from the notebooks, all needed for valid statistical testing:

* Shot order is preserved (``memory=True``). The notebooks rebuilt the bit
  matrix from ``get_counts()``, which groups identical outcomes together and
  so destroys the time order that runs/serial/autocorrelation tests look at.
* Output size is set in bits, not shots: NIST SP 800-22 wants 100 sequences of
  10^6 bits (10^8 bits). The notebooks produced 1.6x10^5.
* Every run is reproducible from ``--seed``: it fixes the classical seed bits,
  the "dice", and Aer's ``seed_simulator``. (That the whole output is fixed by
  one integer is itself the point: AerSimulator is a classical PRNG.)
* A JSON sidecar (``<out>.json``) records how the file was made.
"""
from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import numpy as np

from .bitio import write_meta
from .circuits import build_circuit
from .noise import expected_p1, readout_table


def _run_one(job):
    """Simulate one circuit; return its shots as packed bytes (MSB first)."""
    from qiskit_aer import AerSimulator
    from .noise import noise_model

    model, n_qubits, shots, noise, entropy, index = job
    rng = np.random.default_rng(np.random.SeedSequence(entropy, spawn_key=(index,)))
    qc = build_circuit(model, n_qubits, rng)
    sim = AerSimulator(noise_model=noise_model(noise, n_qubits), max_parallel_threads=1)
    seed_sim = int(rng.integers(0, 2**31 - 1))
    mem = sim.run(qc, shots=shots, memory=True, seed_simulator=seed_sim).result().get_memory()
    # Each memory entry is the clbit string, clbit n-1 first -- the same row
    # order the notebooks used for their bit matrix.
    bits = np.frombuffer("".join(mem).encode("ascii"), dtype=np.uint8) - ord("0")
    return np.packbits(bits).tobytes()


def generate(out, n_bits: int, model: str = "D", n_qubits: int = 32,
             shots_per_circuit: int = 100_000, noise: str = "none",
             seed: int | None = None, workers: int = 1, quiet: bool = False) -> dict:
    """Write `n_bits` bits (rounded up to whole shots, then truncated) to `out`."""
    if (shots_per_circuit * n_qubits) % 8:
        raise ValueError("shots_per_circuit * n_qubits must be a multiple of 8")
    entropy = seed if seed is not None else np.random.SeedSequence().entropy
    bits_per_circuit = shots_per_circuit * n_qubits
    n_circuits = -(-n_bits // bits_per_circuit)
    jobs = [(model, n_qubits, shots_per_circuit, noise, entropy, i) for i in range(n_circuits)]

    need = n_bits // 8
    t0 = time.time()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        if workers > 1:
            with ProcessPoolExecutor(workers) as ex:
                chunks = ex.map(_run_one, jobs)
                written = _drain(chunks, f, need, n_circuits, quiet, t0)
        else:
            written = _drain(map(_run_one, jobs), f, need, n_circuits, quiet, t0)

    import qiskit, qiskit_aer
    meta = dict(
        source="qiskit-aer", model=model, n_qubits=n_qubits,
        shots_per_circuit=shots_per_circuit, n_circuits=n_circuits,
        noise=noise, readout_table_p01_p10=_tolist(readout_table(noise, n_qubits)),
        expected_p1_per_qubit=expected_p1(noise, n_qubits).tolist(),
        seed_entropy=str(entropy), n_bits=written * 8, bit_order="MSB-first packed, shot-major",
        qiskit=qiskit.__version__, qiskit_aer=qiskit_aer.__version__,
        seconds=round(time.time() - t0, 1), created=datetime.now(timezone.utc).isoformat(),
    )
    write_meta(out, meta)
    return meta


def _drain(chunks, f, need, n_circuits, quiet, t0):
    written = 0
    for i, chunk in enumerate(chunks, 1):
        take = min(len(chunk), need - written)
        f.write(chunk[:take])
        written += take
        if not quiet and (i == n_circuits or i % max(1, n_circuits // 10) == 0):
            rate = written * 8 / max(time.time() - t0, 1e-9) / 1e6
            print(f"  circuit {i}/{n_circuits}  {written * 8 / 1e6:.1f} Mbit  ({rate:.2f} Mbit/s)", flush=True)
    return written


def _tolist(a):
    return None if a is None else np.round(a, 6).tolist()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="D", choices=list("ABCD"))
    ap.add_argument("--bits", type=float, required=True, help="number of output bits, e.g. 1e8")
    ap.add_argument("--qubits", type=int, default=32)
    ap.add_argument("--shots-per-circuit", type=int, default=100_000)
    ap.add_argument("--noise", default="none", help="none | symmetric:P | readout:P10,P01 | ibm-like")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    meta = generate(a.out, int(a.bits), a.model, a.qubits, a.shots_per_circuit, a.noise, a.seed, a.workers)
    print(f"wrote {meta['n_bits']:,} bits to {a.out} in {meta['seconds']} s")


if __name__ == "__main__":
    main()
