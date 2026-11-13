"""Figures for the presentation, computed from the generated data and results.

    python -m hqrng.figures --data-dir data --results results/full/summary.json --out figures

Every figure is a PNG in --out; numbers that are better shown as native
PowerPoint charts or tables go to <out>/data.json. Use --only fig07,fig11 to
regenerate a subset.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from scipy.special import erfc

from .bitio import read_bits
from .extractor import output_length, toeplitz_matrix

# ---- style ------------------------------------------------------------------
INK = "#111111"
MUTED = "#6B7280"
GRID = "#ECE9F5"
C_REF = "#6B7280"      # urandom control (grey)
C_SIM = "#6D28D9"      # simulator (purple, the deck's primary colour)
C_NOISY = "#C2410C"    # noisy raw bits (burnt orange = problem)
C_CLEAN = "#0F766E"    # Toeplitz output (teal = cleaned)
C_FAIL = "#B91C1C"
C_PASS = "#15803D"

DATASETS = ["urandom", "aer_D_5k", "aer_D_ideal", "aer_D_sym2pct", "aer_D_ibmlike", "aer_D_ibmlike_toeplitz"]
LABELS = {
    "urandom": "OS random\n(control)",
    "aer_D_5k": "Simulator\n5k shots/run",
    "aer_D_ideal": "Simulator\n100k shots/run",
    "aer_D_sym2pct": "Simulator\n2% symmetric noise",
    "aer_D_ibmlike": "Simulator\nuneven read-out noise",
    "aer_D_ibmlike_toeplitz": "Same noisy bits\nafter Toeplitz",
}
SHORT = {
    "urandom": "Control\n(OS random)", "aer_D_5k": "Sim\n5k/run", "aer_D_ideal": "Sim\n100k/run",
    "aer_D_sym2pct": "Sim\n2% sym.", "aer_D_ibmlike": "Sim\nread-out noise", "aer_D_ibmlike_toeplitz": "After\nToeplitz",
}
COLORS = {"urandom": C_REF, "aer_D_5k": "#A78BFA", "aer_D_ideal": C_SIM, "aer_D_sym2pct": "#4C1D95",
          "aer_D_ibmlike": C_NOISY, "aer_D_ibmlike_toeplitz": C_CLEAN}


def _use_poppins():
    """Use Poppins (the deck font) when installed; other glyphs fall back to DejaVu Sans."""
    from matplotlib import font_manager
    dirs = [Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts", Path("C:/Windows/Fonts"),
            Path.home() / ".fonts", Path("/usr/share/fonts")]
    found = False
    for d in dirs:
        if d.is_dir():
            for f in d.rglob("Poppins-*.ttf"):
                font_manager.fontManager.addfont(str(f))
                found = True
    if found:
        plt.rcParams["font.family"] = ["Poppins", "DejaVu Sans"]


_use_poppins()

plt.rcParams.update({
    "font.size": 12, "axes.titlesize": 14, "axes.titleweight": "bold", "axes.labelsize": 12,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "legend.frameon": False, "figure.dpi": 100, "savefig.dpi": 200,
    "savefig.bbox": "tight", "savefig.facecolor": "white", "text.color": INK,
})

DATA: dict = {}


def _save(fig, out: Path, name: str):
    fig.savefig(out / f"{name}.png")
    plt.close(fig)
    print(f"  wrote {name}.png")


class Bits:
    """Lazy loader for the datasets (bits as uint8 0/1)."""

    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir)
        self.cache: dict[str, np.ndarray] = {}

    def __call__(self, name: str, n: int | None = None) -> np.ndarray:
        if name not in self.cache:
            self.cache[name] = read_bits(self.dir / f"{name}.bin")
        b = self.cache[name]
        return b if n is None else b[:n]

    def bytes(self, name: str) -> np.ndarray:
        return np.fromfile(self.dir / f"{name}.bin", dtype=np.uint8)


# ---- source and circuits ------------------------------------------------------
def fig01_circuits(out, bits, results):
    """The four circuit variants, 6 qubits each."""
    from .circuits import build_circuit
    fig, axes = plt.subplots(2, 2, figsize=(14, 7.5))
    titles = {"A": "A: H only", "B": "B: H + CNOT layer",
              "C": "C: H + shuffled read-out", "D": "D: H + CNOT + shuffled read-out"}
    for ax, m in zip(axes.flat, "ABCD"):
        qc = build_circuit(m, 6, np.random.default_rng(1))
        qc.draw("mpl", ax=ax, style={"name": "bw", "fontsize": 11})
        ax.set_title(titles[m], fontsize=15, fontweight="bold", color=INK)
    fig.tight_layout()
    _save(fig, out, "fig01_circuits")


def fig02_variants_uniform(out, bits, results):
    """Statevector check: every variant is an unentangled, exactly uniform state."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector, entropy, partial_trace
    from .circuits import build_circuit
    n = 6
    rows = []
    for m in "ABCD":
        worst_ent, worst_dev = 0.0, 0.0
        for s in range(20):
            qc = build_circuit(m, n, np.random.default_rng(s)).remove_final_measurements(inplace=False)
            sv = Statevector(qc)
            worst_dev = max(worst_dev, float(np.max(np.abs(sv.probabilities() - 1 / 2 ** n))))
            for q in range(n):
                rho = partial_trace(sv, [k for k in range(n) if k != q])
                worst_ent = max(worst_ent, float(entropy(rho, base=2)))
        rows.append((m, max(worst_ent, 1e-16), max(worst_dev, 1e-18)))
    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    bell_ent = float(entropy(partial_trace(Statevector(bell), [1]), base=2))
    DATA["variants_statevector"] = dict(n_qubits=n, circuits_per_variant=20,
                                        rows=[dict(variant=m, max_entanglement_bits=e, max_prob_deviation=d)
                                              for m, e, d in rows], bell_entanglement_bits=bell_ent)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.4))
    names = [f"Variant {m}" for m, _, _ in rows] + ["Bell pair\n(H then CNOT on |00⟩)"]
    ents = [e for _, e, _ in rows] + [bell_ent]
    cols = [C_SIM] * 4 + [C_NOISY]
    a1.bar(names, ents, color=cols)
    a1.set_yscale("log")
    a1.set_ylim(1e-17, 10)
    a1.set_ylabel("entanglement of one qubit (bits)")
    a1.set_title("Entanglement: none in any variant")
    for i, v in enumerate(ents):
        a1.text(i, v * 2.5, "1.0" if v > 0.5 else f"{v:.0e}", ha="center", fontsize=11)
    a2.bar([f"Variant {m}" for m, _, _ in rows], [d for _, _, d in rows], color=C_SIM)
    a2.set_yscale("log")
    a2.set_ylim(1e-19, 1e-12)
    a2.set_ylabel("max |P(x) − 1/64|")
    a2.set_title("Outcome distribution: exactly uniform")
    for ax in (a1, a2):
        ax.tick_params(axis="x", labelsize=11)
    fig.tight_layout()
    _save(fig, out, "fig02_variants_uniform")


def fig03_noise_bias(out, bits, results):
    """P(1) vs error rate: symmetric flips vs uneven read-out error (theory + Aer)."""
    from .generate import generate
    rates = [0.0, 0.05, 0.1, 0.2, 0.3, 0.4]
    sim = {"symmetric": [], "readout": []}
    with tempfile.TemporaryDirectory() as td:
        for r in rates:
            for kind, spec in (("symmetric", f"symmetric:{r}"), ("readout", f"readout:{r},{r / 5}")):
                f = os.path.join(td, "x.bin")
                generate(f, 32 * 40_000, model="A", shots_per_circuit=40_000, noise=spec, seed=11,
                         workers=1, quiet=True)
                sim[kind].append(float(read_bits(f).mean()))
    x = np.linspace(0, 0.45, 100)
    DATA["noise_bias"] = dict(rates=rates, simulated_p1=sim, bits_per_point=32 * 40_000,
                              readout_rule="P(0|1)=r, P(1|0)=r/5")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(x, np.full_like(x, 0.5), color=C_SIM, lw=2.5, label="Symmetric flip, any rate: P(1) = 0.5")
    ax.plot(x, 0.5 * (1 - x) + 0.5 * x / 5, color=C_NOISY, lw=2.5,
            label="Uneven read-out (P(0|1)=r, P(1|0)=r/5): P(1) = ½(1−r) + ½·r/5")
    ax.scatter(rates, sim["symmetric"], color=C_SIM, s=60, zorder=3, edgecolor="white")
    ax.scatter(rates, sim["readout"], color=C_NOISY, s=60, zorder=3, edgecolor="white")
    ax.set_xlabel("error rate r")
    ax.set_ylabel("fraction of 1s in output")
    ax.set_ylim(0.3, 0.55)
    ax.set_title("Only uneven read-out error can bias a fair qubit")
    ax.legend(loc="lower left", fontsize=11)
    ax.text(0.45, 0.535, "dots: Aer simulation, 1.28 M bits each", ha="right", color=MUTED, fontsize=10)
    _save(fig, out, "fig03_noise_bias")


def fig04_readout_table(out, bits, results):
    """Per-qubit read-out error of the IBM-like preset and the resulting P(1)."""
    from .noise import expected_p1, readout_table
    t = readout_table("ibm-like", 32)
    p01, p10 = t[:, 0], t[:, 1]
    p1 = expected_p1("ibm-like", 32)
    order = np.argsort(p10)[::-1]
    DATA["readout_ibm_like"] = dict(p01=p01.round(5).tolist(), p10=p10.round(5).tolist(),
                                    expected_p1=p1.round(5).tolist(), mean_p1=float(p1.mean()))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True, gridspec_kw=dict(height_ratios=[1.2, 1]))
    q = np.arange(32)
    a1.bar(q - 0.2, p10[order] * 100, 0.4, color=C_NOISY, label="P(read 0 | was 1): decay during read-out")
    a1.bar(q + 0.2, p01[order] * 100, 0.4, color=C_REF, label="P(read 1 | was 0): excitation")
    a1.set_ylabel("error (%)")
    a1.legend(fontsize=11, loc="upper right")
    a1.set_title("Uneven read-out errors, 32 qubits (IBM-like preset: P(0|1) 1–6%, P(1|0) 0.2–1.5%)")
    a2.bar(q, (p1[order] - 0.5) * 100, color=C_NOISY)
    a2.axhline(0, color=INK, lw=1)
    a2.set_ylabel("P(1) − 50% (pts)")
    a2.set_xlabel("qubit (sorted by decay error)")
    a2.set_xticks(q)
    a2.set_xticklabels([str(i) for i in order], fontsize=9)
    a2.set_title(f"Every qubit leans towards 0: mean P(1) = {p1.mean() * 100:.2f}%", fontsize=13)
    fig.tight_layout()
    _save(fig, out, "fig04_readout_table")


def fig05_entropy_saturation(out, bits, results):
    """Plug-in entropy of 32-bit outcomes is log2(N) until N approaches 2^16."""
    words = {}
    for name in ("urandom", "aer_D_ideal"):
        b = bits(name, 32 * 3_000_000).reshape(-1, 32)
        words[name] = np.packbits(b, axis=1).view(">u4").ravel()
    Ns = np.unique(np.logspace(2, math.log10(3_000_000), 22).astype(int))
    res = {}
    for name, w in words.items():
        sh, mn = [], []
        for n in Ns:
            _, c = np.unique(w[:n], return_counts=True)
            p = c / n
            sh.append(float(-(p * np.log2(p)).sum()))
            mn.append(float(-np.log2(p.max())))
        res[name] = dict(shannon=sh, min=mn)
    DATA["entropy_saturation"] = dict(N=Ns.tolist(), **res)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(Ns, np.log2(Ns), color=INK, lw=1.5, ls="--", label="log₂(N)")
    ax.axhline(32, color=MUTED, lw=1.2, ls=":", label="true entropy of 32 fair bits = 32")
    ax.plot(Ns, res["aer_D_ideal"]["shannon"], "o-", color=C_SIM, ms=5, label="Shannon entropy of counts (simulator)")
    ax.plot(Ns, res["urandom"]["min"], "s", color=C_REF, ms=4, mfc="none", label="Min-entropy of counts (OS random)")
    ax.set_xscale("log")
    ax.set_xlabel("number of shots N")
    ax.set_ylabel("entropy (bits)")
    ax.set_ylim(0, 34)
    ax.set_title("Entropy of outcome counts measures the sample size, not the source")
    ax.legend(fontsize=10.5, loc="lower right")
    ax.annotate("N = 5000 → 12.29 bits\nfor any good source", (5000, math.log2(5000)), (130, 20),
                arrowprops=dict(arrowstyle="->", color=MUTED), fontsize=11, color=INK)
    _save(fig, out, "fig05_entropy_saturation")


def fig06_correlation_floor(out, bits, results):
    """Mean |off-diagonal Pearson r| of 32 bit positions vs N, with sqrt(2/(pi N))."""
    b = bits("urandom", 32 * 1_000_000).reshape(-1, 32).astype(np.float32)
    Ns = np.unique(np.logspace(2.5, 6, 15).astype(int))
    iu = np.triu_indices(32, 1)
    vals = [float(np.abs(np.corrcoef(b[:n].T)[iu]).mean()) for n in Ns]
    DATA["correlation_floor"] = dict(N=Ns.tolist(), mean_abs_r=vals)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw=dict(width_ratios=[1.45, 1]))
    xs = np.logspace(2.5, 6, 100)
    a1.plot(xs, np.sqrt(2 / (np.pi * xs)), color=INK, lw=2, label="theory for independent bits: √(2/πN)")
    a1.plot(Ns, vals, "o", color=C_SIM, ms=7, label="measured, OS random bits")
    a1.set_xscale("log")
    a1.set_yscale("log")
    a1.set_xlabel("number of shots N")
    a1.set_ylabel("mean |r| between bit positions")
    a1.set_title("Sampling noise sets a floor on measured correlation")
    a1.legend(fontsize=11)
    for n in (2000, 5000):
        a1.annotate(f"N={n}: {math.sqrt(2 / (math.pi * n)):.4f}", (n, math.sqrt(2 / (math.pi * n))),
                    (n * 3, math.sqrt(2 / (math.pi * n)) * 1.6), fontsize=10.5,
                    arrowprops=dict(arrowstyle="->", color=MUTED))
    r = np.corrcoef(b[:5000].T)
    np.fill_diagonal(r, np.nan)
    im = a2.imshow(r, cmap="RdBu_r", vmin=-0.06, vmax=0.06)
    a2.set_title("32×32 correlation matrix, N = 5000")
    a2.grid(False)
    a2.set_xlabel("bit position")
    a2.set_ylabel("bit position")
    fig.colorbar(im, ax=a2, fraction=0.046, pad=0.04, label="Pearson r")
    fig.tight_layout()
    _save(fig, out, "fig06_correlation_floor")


# ---- the simulator's PRNG -------------------------------------------------------
def _lc_profile(s: np.ndarray) -> np.ndarray:
    """Berlekamp-Massey, returning the linear complexity after each bit."""
    s = np.asarray(s, dtype=np.uint8)
    n = len(s)
    c = np.zeros(n + 1, np.uint8)
    b = np.zeros(n + 1, np.uint8)
    c[0] = b[0] = 1
    L, m = 0, -1
    prof = np.empty(n, np.int32)
    for i in range(n):
        d = s[i] ^ (int(np.bitwise_and(c[1:L + 1], s[i - L:i][::-1]).sum()) & 1)
        if d:
            t = c.copy()
            shift = i - m
            c[shift:] ^= b[: n + 1 - shift]
            if 2 * L <= i:
                L, m, b = i + 1 - L, i, t
        prof[i] = L
    return prof


def fig07_linear_complexity(out, bits, results):
    """Linear complexity grows as n/2 for random bits, but stops at 19937 for Aer."""
    n = 50_000
    prof = {}
    for name in ("urandom", "aer_D_ideal"):
        col = bits(name, 32 * n).reshape(-1, 32)[:, 0]
        t = time.time()
        prof[name] = _lc_profile(col)
        print(f"    LC profile {name}: {time.time() - t:.0f}s, final {prof[name][-1]}")
    step = 250
    DATA["lc_profile"] = dict(n=list(range(step, n + 1, step)),
                              **{k: v[step - 1::step].tolist() for k, v in prof.items()})
    fig, ax = plt.subplots(figsize=(10.5, 5))
    x = np.arange(1, n + 1)
    ax.plot(x, x / 2, color=INK, ls="--", lw=1.2, label="expected for random bits: n/2")
    ax.plot(x, prof["urandom"], color=C_REF, lw=2.2, label="OS random (one bit position)")
    ax.plot(x, prof["aer_D_ideal"], color=C_SIM, lw=2.8, label="Aer simulator (bit 0 across 50,000 shots)")
    ax.axhline(19937, color=C_NOISY, lw=1.2, ls=":")
    ax.text(1000, 20600, "19,937 = size of the Mersenne Twister state", color=C_NOISY, fontsize=11)
    ax.annotate("stops growing at n ≈ 39,874:\na 19,937-bit linear recurrence\nreproduces every later bit",
                (41_000, 19937), (30_000, 7_000), arrowprops=dict(arrowstyle="->", color=MUTED), fontsize=11)
    ax.set_xlabel("number of bits n")
    ax.set_ylabel("linear complexity L(n)")
    ax.set_title("Berlekamp–Massey exposes the simulator's hidden formula")
    ax.legend(loc="lower right", fontsize=11)
    _save(fig, out, "fig07_linear_complexity")


def fig08_lfsr_example(out, bits, results):
    """A 4-bit LFSR (x^4 + x + 1): 15-bit period, linear complexity 4."""
    reg = [1, 0, 0, 0]
    seq = []
    for _ in range(30):
        seq.append(reg[-1])
        fb = reg[-1] ^ reg[-2]  # s[t+4] = s[t+1] XOR s[t]  <=>  x^4 + x + 1
        reg = [fb] + reg[:-1]
    prof = _lc_profile(np.array(seq))
    rnd = np.random.default_rng(3).integers(0, 2, 30)
    DATA["lfsr_example"] = dict(polynomial="x^4 + x + 1", seed=[1, 0, 0, 0], bits=seq,
                                lc_profile=prof.tolist(), random_bits=rnd.tolist(),
                                random_lc_profile=_lc_profile(rnd).tolist())
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 4.4), gridspec_kw=dict(height_ratios=[1, 2]))
    a1.imshow(np.array(seq)[None, :], cmap=LinearSegmentedColormap.from_list("b", ["white", C_SIM]), aspect="auto")
    for i, v in enumerate(seq):
        a1.text(i, 0, str(v), ha="center", va="center", color="white" if v else INK, fontsize=11)
    a1.set_yticks([])
    a1.set_xticks([])
    a1.grid(False)
    a1.set_title("LFSR x⁴ + x + 1: output repeats every 15 bits")
    a2.step(np.arange(1, 31), prof, where="post", color=C_SIM, lw=2.5, label="LFSR: L stays at 4")
    a2.step(np.arange(1, 31), _lc_profile(rnd), where="post", color=C_REF, lw=2, label="random bits: L ≈ n/2")
    a2.plot(np.arange(1, 31), np.arange(1, 31) / 2, ls="--", color=INK, lw=1)
    a2.set_xlabel("bits seen n")
    a2.set_ylabel("L(n)")
    a2.legend(fontsize=11, loc="upper left")
    fig.tight_layout()
    _save(fig, out, "fig08_lfsr_example")


# ---- entropy and extraction -----------------------------------------------------
def fig09_entropy_curves(out, bits, results):
    p = np.linspace(0.3, 0.7, 401)
    sh = -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
    mn = -np.log2(np.maximum(p, 1 - p))
    p0 = results_lookup(results, "aer_D_ibmlike")["entropy"]["ones_fraction"]
    sh0 = -(p0 * math.log2(p0) + (1 - p0) * math.log2(1 - p0))
    mn0 = -math.log2(max(p0, 1 - p0))
    DATA["entropy_example"] = dict(p1=p0, shannon=sh0, min_entropy=mn0)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(p, sh, color=C_SIM, lw=2.5, label="Shannon H = −Σ p log₂ p (average surprise)")
    ax.plot(p, mn, color=C_NOISY, lw=2.5, label="Min-entropy H∞ = −log₂ max p (best single guess)")
    ax.axvline(p0, color=MUTED, ls=":", lw=1.2)
    ax.scatter([p0, p0], [sh0, mn0], color=[C_SIM, C_NOISY], zorder=3, s=60)
    ax.annotate(f"P(1) = {p0:.4f}\nShannon {sh0:.4f}\nmin-entropy {mn0:.4f}", (p0, mn0), (0.33, 0.83),
                arrowprops=dict(arrowstyle="->", color=MUTED), fontsize=11)
    ax.set_xlabel("P(bit = 1)")
    ax.set_ylabel("bits of entropy per bit")
    ax.set_ylim(0.75, 1.02)
    ax.set_title("Min-entropy is the cautious measure: it drops much faster with bias")
    ax.legend(fontsize=11, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=1)
    _save(fig, out, "fig09_entropy_curves")


def results_lookup(results, name):
    return next(r for r in results if r["dataset"] == name)


def fig10_hmin_datasets(out, bits, results):
    rows = []
    for name in DATASETS:
        e = results_lookup(results, name)["entropy"]
        rows.append(dict(dataset=name, mcv=e["mcv"], markov=e["markov"],
                         per_qubit_mcv=e["per_qubit_mcv_mean"], h_min=e["h_min"], ones=e["ones_fraction"]))
    DATA["hmin_datasets"] = rows
    fig, ax = plt.subplots(figsize=(13, 4.8))
    x = np.arange(len(rows))
    w = 0.26
    ax.bar(x - w, [r["mcv"] for r in rows], w, color=C_REF, label="Most common value (whole stream)")
    ax.bar(x, [r["markov"] for r in rows], w, color=C_SIM, label="Markov (bit-to-bit dependence)")
    ax.bar(x + w, [r["per_qubit_mcv"] for r in rows], w, color=C_NOISY, label="Most common value, per bit position")
    for i, r in enumerate(rows):
        ax.text(i, 1.0025, f"h_min {r['h_min']:.3f}", ha="center", fontsize=10.5, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT[r["dataset"]] for r in rows], fontsize=11)
    ax.set_ylim(0.94, 1.016)
    ax.set_ylabel("min-entropy per bit")
    ax.set_title("SP 800-90B-style estimates: the lowest one (h_min) sizes the extractor", pad=34)
    ax.legend(fontsize=10.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    _save(fig, out, "fig10_hmin_datasets")


def fig11_piling_up(out, bits, results):
    b = bits("aer_D_ibmlike", 64_000_000).astype(np.uint8)
    eps0 = 0.5 - b.mean()
    ks = [1, 2, 3, 4, 5, 6]
    emp = []
    for k in ks:
        y = b[: (len(b) // k) * k].reshape(-1, k)
        x = np.bitwise_xor.reduce(y, axis=1)
        emp.append(abs(0.5 - x.mean()))
    theory = [2 ** (k - 1) * eps0 ** k for k in ks]
    se = [0.5 / math.sqrt(len(b) // k) for k in ks]
    DATA["piling_up"] = dict(eps0=float(eps0), k=ks, empirical_bias=[float(e) for e in emp],
                             theory_bias=theory, standard_error=se)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.semilogy(ks, theory, "o-", color=C_CLEAN, lw=2.5, ms=8, label="theory: bias of XOR of k bits = 2ᵏ⁻¹·εᵏ")
    ax.semilogy(ks[:3], emp[:3], "s", color=C_NOISY, ms=10, mfc="none", mew=2,
                label="measured on the noisy simulator bits")
    ax.semilogy(ks, se, ":", color=MUTED, label="measurement noise floor (64 M bits)")
    ax.set_xlabel("number of bits XORed together (k)")
    ax.set_ylabel("bias |P(1) − ½|")
    ax.set_title(f"XOR shrinks bias geometrically (starting bias ε = {eps0:.4f})")
    ax.legend(fontsize=11)
    _save(fig, out, "fig11_piling_up")


def fig12_toeplitz_structure(out, bits, results):
    rng = np.random.default_rng(5)
    n, m = 24, 14
    seed = rng.integers(0, 2, n + m - 1)
    T = toeplitz_matrix(seed, n, m)
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.imshow(T, cmap=LinearSegmentedColormap.from_list("t", ["#F3F0FA", C_SIM]), aspect="equal")
    for d in (0, 5, -6):
        ii = np.arange(m)
        jj = ii + d
        ok = (jj >= 0) & (jj < n)
        ax.plot(jj[ok], ii[ok], color=C_NOISY, lw=2.2, alpha=0.9)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    ax.set_xlabel(f"n = {n} input bits")
    ax.set_ylabel(f"m = {m} output bits")
    ax.set_title(f"A {m}×{n} Toeplitz matrix: every diagonal is constant,\n"
                 f"so {n + m - 1} seed bits define all {n * m} entries")
    _save(fig, out, "fig12_toeplitz_structure")


def fig13_toeplitz_example(out, bits, results):
    """4x6 worked example: y = T x mod 2."""
    seed = np.array([1, 0, 1, 1, 0, 0, 1, 0, 1])     # n + m - 1 = 9
    n, m = 6, 4
    T = toeplitz_matrix(seed, n, m)
    x = np.array([0, 1, 1, 1, 0, 1])
    y = (T @ x) % 2
    DATA["toeplitz_example"] = dict(seed=seed.tolist(), T=T.tolist(), x=x.tolist(), y=y.tolist(),
                                    rule="T[i][j] = seed[i - j + n - 1]",
                                    row_sums=(T @ x).tolist())
    fig = plt.figure(figsize=(12, 3.8))
    cm = LinearSegmentedColormap.from_list("t", ["#F3F0FA", C_SIM])

    def grid(ax, M, title, hl=None):
        M = np.atleast_2d(M)
        ax.imshow(M % 2, cmap=cm, vmin=0, vmax=1)
        for (i, j), v in np.ndenumerate(M):
            ax.text(j, i, str(v), ha="center", va="center", fontsize=15,
                    color="white" if v % 2 else INK, fontweight="bold")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        ax.set_title(title, fontsize=13)
        for s in ax.spines.values():
            s.set_visible(False)

    a1 = fig.add_axes([0.02, 0.1, 0.4, 0.75])
    grid(a1, T, "T (4×6), built from seed 1 0 1 1 0 0 1 0 1")
    a2 = fig.add_axes([0.47, 0.1, 0.07, 0.75])
    grid(a2, x[:, None], "x")
    a3 = fig.add_axes([0.62, 0.1, 0.07, 0.75])
    grid(a3, ((T @ x))[:, None], "T·x")
    a4 = fig.add_axes([0.77, 0.1, 0.07, 0.75])
    grid(a4, y[:, None], "y = T·x mod 2")
    fig.text(0.44, 0.47, "×", fontsize=26, ha="center", color=INK)
    fig.text(0.585, 0.47, "=", fontsize=26, ha="center", color=INK)
    fig.text(0.735, 0.47, "→", fontsize=26, ha="center", color=INK)
    fig.text(0.86, 0.47, "each output bit =\nXOR of the input bits\nwhere its row has a 1",
             fontsize=12, color=INK, va="center")
    _save(fig, out, "fig13_toeplitz_example")


def fig14_lhl_length(out, bits, results):
    h = np.linspace(0.5, 1.0, 200)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for n, ls in ((1024, ":"), (4096, "--"), (16384, "-")):
        m = [output_length(n, hh) / n for hh in h]
        ax.plot(h, m, ls=ls, lw=2.3, color=C_CLEAN, label=f"n = {n:,}")
    h0 = results_lookup(results, "aer_D_ibmlike")["entropy"]["h_min"]
    m0 = output_length(16384, h0)
    DATA["lhl"] = dict(n=16384, h_min=h0, eps_log2=-100, m=m0, kept_fraction=m0 / 16384,
                       entropy_in=16384 * h0, security_cost_bits=200)
    ax.scatter([h0], [m0 / 16384], color=C_NOISY, s=80, zorder=3)
    ax.annotate(f"our run: h = {h0:.4f} → m = {m0:,} of 16,384\n(keep {m0 / 16384 * 100:.1f}%)",
                (h0, m0 / 16384), (0.62, 0.9), arrowprops=dict(arrowstyle="->", color=MUTED), fontsize=11)
    ax.plot(h, h, color=MUTED, lw=1, label="entropy available (m/n = h)")
    ax.set_xlabel("min-entropy per input bit h")
    ax.set_ylabel("output bits kept per input bit m/n")
    ax.set_title("Leftover Hash Lemma: m = n·h − 2·log₂(1/ε), here ε = 2⁻¹⁰⁰")
    ax.legend(fontsize=11, loc="upper left")
    _save(fig, out, "fig14_lhl_length")


def fig15_column_bias(out, bits, results):
    nshots = 3_000_000
    raw = bits("aer_D_ibmlike", 32 * nshots).reshape(-1, 32)
    clean = bits("aer_D_ibmlike_toeplitz", 32 * nshots).reshape(-1, 32)
    # Variant D reshuffles the read-out order per circuit, so follow one circuit (100k shots)
    r1 = raw[:100_000].mean(0)
    c1 = clean[:100_000].mean(0)
    DATA["column_bias"] = dict(raw=r1.tolist(), toeplitz=c1.tolist(), shots=100_000)
    fig, ax = plt.subplots(figsize=(12, 4.6))
    x = np.arange(32)
    se = 3 * 0.5 / math.sqrt(100_000)
    ax.axhspan(50 - se * 100, 50 + se * 100, color=GRID, label="±3σ for a fair bit")
    ax.bar(x - 0.2, r1 * 100, 0.4, color=C_NOISY, label="raw noisy bits")
    ax.bar(x + 0.2, c1 * 100, 0.4, color=C_CLEAN, label="after Toeplitz")
    ax.set_ylim(46.5, 50.8)
    ax.axhline(50, color=INK, lw=1)
    ax.set_xticks(x)
    ax.set_xlabel("bit position within the 32-bit shot")
    ax.set_ylabel("% ones (100,000 shots)")
    ax.set_title("Per-position bias before and after extraction", pad=30)
    ax.legend(fontsize=11, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    _save(fig, out, "fig15_column_bias")


def fig16_column_heatmap(out, bits, results):
    nshots = 2_000_000      # 20 circuits
    block = 10_000
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
    cm = LinearSegmentedColormap.from_list("d", [C_NOISY, "#FFFFFF", C_SIM])
    for ax, name, title in ((axes[0], "aer_D_ibmlike", "Raw noisy bits"),
                            (axes[1], "aer_D_ibmlike_toeplitz", "After Toeplitz")):
        b = bits(name, 32 * nshots).reshape(-1, block, 32).mean(1)
        im = ax.imshow((b - 0.5) * 100, cmap=cm, vmin=-3, vmax=3, aspect="auto", interpolation="nearest")
        ax.set_title(title)
        ax.set_xlabel("bit position")
        ax.grid(False)
    axes[0].set_ylabel("block of 10,000 shots (time →)")
    for k in range(0, 200, 10):
        axes[0].axhline(k - 0.5, color=INK, lw=0.4, alpha=0.4)
    fig.colorbar(im, ax=axes, fraction=0.03, pad=0.02, label="% ones − 50")
    _save(fig, out, "fig16_column_heatmap")


def fig17_bytepair(out, bits, results):
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.4), gridspec_kw=dict(wspace=0.22))
    cm = LinearSegmentedColormap.from_list("d", [C_NOISY, "#FFFFFF", C_SIM])
    stats = {}
    for ax, name, title in ((axes[0], "urandom", "OS random"), (axes[1], "aer_D_ibmlike", "Raw noisy bits"),
                            (axes[2], "aer_D_ibmlike_toeplitz", "After Toeplitz")):
        by = bits.bytes(name)[: 12_000_000]
        a, b = by[0::2].astype(np.int64), by[1::2].astype(np.int64)
        h = np.bincount(a * 256 + b, minlength=65536).reshape(256, 256)
        rel = h / h.mean()
        # sort bytes by number of 1 bits so bias shows as a gradient
        order = np.argsort([bin(i).count("1") for i in range(256)], kind="stable")
        im = ax.imshow(rel[np.ix_(order, order)], cmap=cm.reversed(), vmin=0.4, vmax=1.6, interpolation="nearest")
        ax.set_title(title)
        ax.set_xticks([0, 255])
        ax.set_xticklabels(["0", "8"])
        ax.set_yticks([0, 255])
        ax.set_yticklabels(["0", "8"])
        ax.grid(False)
        stats[name] = dict(cv=float(rel.std()), min=float(rel.min()), max=float(rel.max()))
    axes[0].set_ylabel("first byte: number of 1s →")
    axes[1].set_xlabel("second byte: number of 1s → (256 values each, sorted)")
    fig.colorbar(im, ax=axes, fraction=0.02, pad=0.02, label="count ÷ expected")
    DATA["bytepair"] = stats
    _save(fig, out, "fig17_bytepair")


def fig18_autocorr(out, bits, results):
    lags = np.arange(1, 71)
    fig, ax = plt.subplots(figsize=(12, 4.4))
    n = 50_000_000
    res = {}
    for name, col, mk in (("aer_D_ibmlike", C_NOISY, "o"), ("aer_D_ibmlike_toeplitz", C_CLEAN, "s")):
        x = bits(name, n).astype(np.float32)
        x -= x.mean()
        v = float((x * x).mean())
        r = np.array([float((x[:-k] * x[k:]).mean()) / v for k in lags])
        res[name] = r.tolist()
        ax.plot(lags, r, mk, color=col, ms=5, label=LABELS[name].replace("\n", " "))
    s3 = 3 / math.sqrt(n)
    ax.axhspan(-s3, s3, color=GRID, label="±3σ band")
    ax.set_ylim(-s3 * 2, s3 * 2)
    ax.set_xlabel("lag (bits)")
    ax.set_ylabel("autocorrelation")
    ax.set_title("Autocorrelation (50 M bits) is blind to bias: raw and cleaned bits look the same", pad=30)
    ax.legend(fontsize=10.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    DATA["autocorr"] = dict(lags=lags.tolist(), n=n, three_sigma=s3, **res)
    _save(fig, out, "fig18_autocorr")


# ---- statistical tests -----------------------------------------------------------
def _monobit_p(seq_bits: np.ndarray) -> np.ndarray:
    n = seq_bits.shape[1]
    s = np.abs(2 * seq_bits.sum(1, dtype=np.int64) - n) / math.sqrt(n)
    return erfc(s / math.sqrt(2))


def _runs_p(seq_bits: np.ndarray) -> np.ndarray:
    n = seq_bits.shape[1]
    pi = seq_bits.mean(1)
    v = 1 + (seq_bits[:, 1:] != seq_bits[:, :-1]).sum(1)
    p = erfc(np.abs(v - 2 * n * pi * (1 - pi)) / (2 * math.sqrt(2 * n) * pi * (1 - pi)))
    p[np.abs(pi - 0.5) >= 2 / math.sqrt(n)] = 0.0     # NIST pre-test: frequency must pass first
    return p


def fig19_pvalue_hist(out, bits, results):
    names = ("urandom", "aer_D_ibmlike", "aer_D_ibmlike_toeplitz")
    fig, axes = plt.subplots(2, 3, figsize=(11.5, 6.0), sharex=True)
    res = {}
    for j, name in enumerate(names):
        b = bits(name, 100_000_000).reshape(100, 1_000_000)
        for i, (tname, f) in enumerate((("Frequency (monobit)", _monobit_p), ("Runs", _runs_p))):
            p = f(b)
            ok = int((p >= 0.01).sum())
            res.setdefault(name, {})[tname] = dict(p=np.round(p, 6).tolist(), passed=ok)
            ax = axes[i, j]
            ax.hist(p, bins=10, range=(0, 1), color=COLORS[name], edgecolor="white")
            ax.axhline(10, color=INK, ls="--", lw=1)
            ax.set_ylim(0, 100)
            ax.set_title(f"{SHORT[name].replace(chr(10), ' ')}\n{tname}: {ok}/100 pass", fontsize=13)
            if j == 0:
                ax.set_ylabel("sequences")
            if i == 1:
                ax.set_xlabel("p-value")
    fig.tight_layout()
    DATA["pvalues_frequency_runs"] = res
    _save(fig, out, "fig19_pvalue_hist")


def fig20_proportion(out, bits, results):
    m = np.arange(20, 1001)
    p = 0.99
    lo = p - 3 * np.sqrt(p * (1 - p) / m)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 4.6), gridspec_kw=dict(width_ratios=[1, 1.4]))
    a1.plot(m, lo * 100, color=C_SIM, lw=2.5)
    a1.axhline(99, color=INK, ls="--", lw=1)
    a1.scatter([100], [lo[80] * 100], color=C_NOISY, zorder=3, s=60)
    a1.annotate("m = 100 → 96.0%: at least 96/100\nsequences must pass", (100, lo[80] * 100), (300, 95),
                arrowprops=dict(arrowstyle="->", color=MUTED), fontsize=11)
    a1.set_xlabel("number of sequences m")
    a1.set_ylabel("minimum pass rate (%)")
    a1.set_title("Proportion rule: 0.99 − 3·√(0.99·0.01/m)")
    a1.set_ylim(92, 100)
    for name, mk in (("urandom", "o"), ("aer_D_ibmlike", "x"), ("aer_D_ibmlike_toeplitz", "s")):
        t = results_lookup(results, name)["nist"]["tests"]
        props = [x["passed"] / x["total"] * 100 for x in t if x["total"] >= 55]
        a2.plot(np.arange(len(props)), props, mk, ms=3.5, color=COLORS[name],
                label=LABELS[name].replace("\n", " "), mfc="none" if mk == "s" else None)
    a2.axhline(96, color=INK, ls="--", lw=1, label="96% pass line")
    a2.set_ylim(-3, 103)
    a2.set_xlabel("NIST sub-test (180 with ≥55 sequences)")
    a2.set_ylabel("% of 100 sequences passing")
    a2.set_title("Proportion passing, every NIST sub-test")
    a2.legend(fontsize=11, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    fig.tight_layout()
    _save(fig, out, "fig20_proportion")


def fig21_nist_heatmap(out, bits, results):
    """Per test family: sub-tests passed, per dataset (families as rows)."""
    fam_order = [f["test"] for f in results_lookup(results, "urandom")["nist"]["families"]]
    nice = {"NonOverlappingTemplate": "Non-overlapping template", "OverlappingTemplate": "Overlapping template",
            "RandomExcursions": "Random excursions", "RandomExcursionsVariant": "Random excursions variant",
            "BlockFrequency": "Block frequency", "CumulativeSums": "Cumulative sums", "LongestRun": "Longest run",
            "ApproximateEntropy": "Approximate entropy", "LinearComplexity": "Linear complexity",
            "FFT": "Spectral (DFT)", "Rank": "Binary matrix rank", "Universal": "Maurer universal"}
    V = np.full((len(fam_order), len(DATASETS)), np.nan)
    txt = [["" for _ in DATASETS] for _ in fam_order]
    for j, name in enumerate(DATASETS):
        fams = {f["test"]: f for f in results_lookup(results, name)["nist"]["families"]}
        for i, fam in enumerate(fam_order):
            f = fams.get(fam)
            if f is None:
                txt[i][j] = "not run*"
                continue
            ok = f["subtests"] - f["failed"]
            txt[i][j] = f"{ok}/{f['subtests']}"
            V[i, j] = {"pass": 2, "marginal": 1, "fail": 0}[f["verdict"]]
    fig, ax = plt.subplots(figsize=(10.5, 6.6))
    cm = LinearSegmentedColormap.from_list("v", ["#FCA5A5", "#FDE68A", "#BBF7D0"], N=3)
    ax.imshow(np.ma.masked_invalid(V), cmap=cm, vmin=0, vmax=2, aspect="auto")
    ax.imshow(np.where(np.isnan(V), 1, np.nan), cmap=LinearSegmentedColormap.from_list("g", ["#E5E7EB", "#E5E7EB"]),
              aspect="auto")
    for i in range(len(fam_order)):
        for j in range(len(DATASETS)):
            ax.text(j, i, txt[i][j], ha="center", va="center", fontsize=12.5,
                    color=MUTED if txt[i][j] == "not run*" else INK)
    ax.set_xticks(range(len(DATASETS)))
    ax.set_xticklabels([SHORT[d] for d in DATASETS], fontsize=12.5)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(fam_order)))
    ax.set_yticklabels([nice.get(f, f) for f in fam_order], fontsize=12.5)
    ax.set_xticks(np.arange(-0.5, len(DATASETS)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(fam_order)), minor=True)
    ax.grid(False)
    ax.grid(which="minor", color="white", lw=2)
    ax.tick_params(which="minor", length=0)
    fig.text(0.5, 0.02, "green = pass · amber = within chance · red = fail\n"
             "*random excursions need ≥ 500 returns to zero; a biased walk rarely returns",
             ha="center", fontsize=12, color=MUTED)
    _save(fig, out, "fig21_nist_heatmap")
    DATA["nist_summary"] = [dict(dataset=r["dataset"], passed=sum(x["ok"] for x in r["nist"]["tests"]),
                                 total=len(r["nist"]["tests"]),
                                 families=[dict(test=f["test"], verdict=f["verdict"], failed=f["failed"],
                                                subtests=f["subtests"]) for f in r["nist"]["families"]],
                                 seconds=r["nist"]["seconds"]) for r in results]


def fig22_testu01_strip(out, bits, results):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    bats = ["rabbit", "alphabit", "lincomp"]
    summary = []
    for ax, bat in zip(axes, bats):
        ax.axhspan(0, 0.001, color="#FEE2E2")
        ax.axhspan(0.999, 1, color="#FEE2E2")
        for i, name in enumerate(DATASETS):
            b = next(x for x in results_lookup(results, name)["testu01"]["batteries"] if x["battery"] == bat)
            p = np.array([t["p_value"] for t in b["tests"]])
            jit = np.random.default_rng(i).uniform(-0.25, 0.25, len(p))
            bad = (p < 0.001) | (p > 0.999)
            ax.scatter(i + jit[~bad], p[~bad], s=16, color=COLORS[name], alpha=0.8)
            ax.scatter(i + jit[bad], p[bad], s=40, color=C_FAIL, marker="x", lw=1.6)
            summary.append(dict(dataset=name, battery=bat, tests=len(p), failed=b["failed"],
                                suspicious=b["suspicious"], nb=b.get("nb"), seconds=b.get("seconds")))
        ax.set_xticks(range(len(DATASETS)))
        ax.set_xticklabels([SHORT[d] for d in DATASETS], fontsize=10.5, rotation=35, ha="right")
        ax.set_title({"rabbit": "Rabbit (38 results)", "alphabit": "Alphabit (17)",
                      "lincomp": "LinearComp (4)"}[bat])
        ax.set_ylim(-0.03, 1.03)
    axes[0].set_ylabel("p-value")
    fig.tight_layout()
    DATA["testu01_summary"] = summary
    _save(fig, out, "fig22_testu01_strip")


def fig23_random_walk(out, bits, results):
    n = 1_000_000
    fig, ax = plt.subplots(figsize=(11, 4.6))
    k = np.arange(1, n + 1)
    ax.fill_between(k, -3 * np.sqrt(k), 3 * np.sqrt(k), color=GRID, label="±3√n: where a fair walk stays")
    for name in ("urandom", "aer_D_ibmlike", "aer_D_ibmlike_toeplitz"):
        s = np.cumsum(2 * bits(name, n).astype(np.int32) - 1)
        ax.plot(k[::200], s[::200], color=COLORS[name], lw=1.8, label=LABELS[name].replace("\n", " "))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1e6:.1f} M"))
    ax.set_xlabel("bits n")
    ax.set_ylabel("running sum of ±1")
    ax.set_title("Random walk / cumulative-sum view: 1.3% bias drifts away by ~26,000 steps")
    ax.legend(fontsize=11, loc="lower left")
    _save(fig, out, "fig23_random_walk")


def fig24_throughput(out, bits, results):
    from .generate import generate
    ws = [1, 2, 4, 8, 16]
    if "throughput" in DATA and not os.environ.get("HQRNG_REMEASURE"):
        rates = DATA["throughput"]["mbit_per_s"]          # timing is only meaningful on an idle machine
    else:
        rates = []
        with tempfile.TemporaryDirectory() as td:
            for w in ws:
                f = os.path.join(td, "t.bin")
                n = 32 * 25_000 * 32
                t = time.time()
                generate(f, n, model="D", shots_per_circuit=25_000, seed=1, workers=w, quiet=True)
                rates.append(n / (time.time() - t) / 1e6)
        DATA["throughput"] = dict(workers=ws, mbit_per_s=rates, cpu_count=os.cpu_count(),
                                  bits_per_run=32 * 25_000 * 32)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar([str(w) for w in ws], rates, color=C_SIM)
    for i, r in enumerate(rates):
        ax.text(i, r + 0.05, f"{r:.1f}", ha="center")
    ax.set_xlabel("worker processes")
    ax.set_ylabel("Mbit / s")
    ax.set_title(f"Bit generation speed (Aer, variant D, {os.cpu_count()} logical CPUs)")
    _save(fig, out, "fig24_throughput")


def fig25_parking_lot(out, bits, results):
    """Diehard parking-lot test, illustrated with real bits from the control file."""
    b = bits.bytes("urandom")[: 4 * 2 * 1200].view(">u4").astype(np.float64) / 2 ** 32
    pts = (b.reshape(-1, 2) * 40)
    parked = []
    crashed = []
    for x, y in pts:
        if all(abs(x - px) > 1 or abs(y - py) > 1 for px, py in parked):
            parked.append((x, y))
        else:
            crashed.append((x, y))
    fig, ax = plt.subplots(figsize=(6.4, 6.4))
    for x, y in parked:
        ax.add_patch(plt.Rectangle((x - 0.5, y - 0.5), 1, 1, color=C_SIM, alpha=0.85, lw=0))
    cx, cy = zip(*crashed)
    ax.scatter(cx, cy, s=6, color=C_NOISY, alpha=0.6, label=f"crash ({len(crashed)})")
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 40)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    ax.set_title(f"{len(pts)} random attempts: {len(parked)} parked (purple),\n{len(crashed)} crashed (orange dots)", fontsize=15)
    DATA["parking_lot_demo"] = dict(attempts=len(pts), parked=len(parked), lot=40,
                                    diehard_full=dict(lot=100, attempts=12000, mean_parked=3523, sd=21.9))
    _save(fig, out, "fig25_parking_lot")


def fig26_toeplitz_universal(out, bits, results):
    """Why random Toeplitz matrices are 2-universal, plus a Monte Carlo check."""
    rng = np.random.default_rng(12)
    n, m = 12, 7
    seed = rng.integers(0, 2, n + m - 1)
    T = toeplitz_matrix(seed, n, m)
    d = np.zeros(n, int)
    d[[3, 6, 7, 10]] = 1
    j0 = int(np.flatnonzero(d)[0])

    # Monte Carlo: P[T d = 0] over random seeds and random non-zero d, versus 2^-m
    N, nn = 400_000, 16
    mc = []
    for mm in (2, 4, 6, 8):
        S = rng.integers(0, 2, (N, nn + mm - 1), dtype=np.uint8)
        D = rng.integers(0, 2, (N, nn), dtype=np.uint8)
        D[D.sum(1) == 0, 0] = 1
        zero = np.ones(N, bool)
        for i in range(mm):
            acc = np.zeros(N, np.uint8)
            for j in range(nn):
                acc ^= S[:, i - j + nn - 1] & D[:, j]
            zero &= acc == 0
        mc.append(dict(m=mm, measured=float(zero.mean()), theory=2.0 ** -mm, trials=N))
    DATA["toeplitz_universal"] = dict(n=nn, checks=mc)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.5, 4.5), gridspec_kw=dict(width_ratios=[1.35, 1]))
    cm = LinearSegmentedColormap.from_list("t", ["#F3F0FA", C_SIM])
    a1.imshow(np.vstack([d, np.full(n, -1), T]), cmap=cm, vmin=0, vmax=1, aspect="equal")
    a1.imshow(np.vstack([np.where(d == 1, 1.0, np.nan), np.full((m + 1, n), np.nan)]),
              cmap=LinearSegmentedColormap.from_list("o", [C_NOISY, C_NOISY]), aspect="equal")
    for i in range(m):
        a1.add_patch(plt.Rectangle((j0 - 0.5, i + 1.5), 1, 1, fill=False, ec=C_NOISY, lw=2.5))
        a1.text(n - 0.2, i + 2, f"  s[{i - j0 + n - 1}]", va="center", fontsize=11, color=C_NOISY)
    a1.text(-0.8, 0, "d", ha="right", va="center", fontsize=13, fontweight="bold", color=C_NOISY)
    a1.text(-0.8, 2 + m / 2 - 0.5, "T", ha="right", va="center", fontsize=13, fontweight="bold", color=C_SIM)
    a1.set_xlim(-1.5, n + 2.3)
    a1.set_xticks([])
    a1.set_yticks([])
    a1.grid(False)
    for sp in a1.spines.values():
        sp.set_visible(False)
    a1.set_title(f"First 1 of d at column j₀ = {j0}:\nevery row gets a new seed bit", fontsize=14)
    ms = [c["m"] for c in mc]
    a2.bar(np.arange(len(ms)) - 0.18, [c["theory"] for c in mc], 0.36, color=GRID, ec=C_SIM, label="2⁻ᵐ (theory)")
    a2.bar(np.arange(len(ms)) + 0.18, [c["measured"] for c in mc], 0.36, color=C_SIM, label="measured")
    a2.set_yscale("log")
    a2.set_xticks(range(len(ms)))
    a2.set_xticklabels([f"m = {x}" for x in ms])
    a2.set_ylabel("P[ h(x) = h(x′) ]")
    a2.set_title(f"Collision probability\n(n = {nn}, {N // 1000:,}k trials each)", fontsize=14)
    a2.legend(fontsize=11)
    fig.tight_layout()
    _save(fig, out, "fig26_toeplitz_universal")


def fig27_lhl_tradeoff(out, bits, results):
    """Security (−log2 ε) versus bits kept, for our block."""
    l = DATA.get("lhl") or {}
    k = l.get("entropy_in", 15739.7)
    m = np.linspace(14900, k, 300)
    sec = (k - m) / 2
    m0 = l.get("m", 15536)
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ax.plot(m, sec, color=C_SIM, lw=2.8)
    ax.fill_between(m, sec, 0, where=sec >= 100, color="#EDE9FE")
    ax.axhline(100, color=C_NOISY, ls="--", lw=1.4)
    ax.text(14920, 104, "target: ε = 2⁻¹⁰⁰", color=C_NOISY, fontsize=12)
    ax.scatter([m0], [(k - m0) / 2], color=C_NOISY, s=80, zorder=3)
    sup = str(round((k - m0) / 2)).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))
    ax.annotate(f"our choice: m = {m0:,}, ε ≈ 2⁻{sup}", (m0, (k - m0) / 2), (15020, 35),
                arrowprops=dict(arrowstyle="->", color=MUTED), fontsize=12)
    ax.axvline(k, color=MUTED, ls=":", lw=1.2)
    ax.text(k - 8, 380, f"k = {k:,.0f}\n(all the\nmin-entropy)", ha="right", va="top", fontsize=11, color=MUTED)
    ax.set_xlabel("output bits kept per 16,384-bit block (m)")
    ax.set_ylabel("security: −log₂ ε (bits)")
    ax.set_ylim(0, 430)
    ax.set_title("Each bit kept costs ½ bit of security: −log₂ ε = (k − m)/2", fontsize=13.5)
    _save(fig, out, "fig27_lhl_tradeoff")


def data_extras(results):
    """Small worked examples and tables for native slides."""
    DATA["monobit_example"] = dict(bits="1011010101", n=10, S=2, s_obs=round(2 / math.sqrt(10), 6),
                                   p=float(erfc(2 / math.sqrt(10) / math.sqrt(2))))
    seq = np.array([int(c) for c in "1001101011"])
    pi = seq.mean()
    v = 1 + int((seq[1:] != seq[:-1]).sum())
    p = float(erfc(abs(v - 2 * 10 * pi * (1 - pi)) / (2 * math.sqrt(2 * 10) * pi * (1 - pi))))
    DATA["runs_example"] = dict(bits="1001101011", n=10, pi=pi, V=v, p=p)
    DATA["scoreboard"] = [dict(
        dataset=r["dataset"], ones_percent=r["entropy"]["ones_fraction"] * 100, h_min=r["entropy"]["h_min"],
        lincomp_columns=r["lincomp"]["columns"], mt19937=r["lincomp"]["mt19937_signature"],
        nist_passed=sum(x["ok"] for x in r["nist"]["tests"]), nist_total=len(r["nist"]["tests"]),
        testu01={b["battery"]: dict(tests=len(b["tests"]), failed=b["failed"], suspicious=b["suspicious"])
                 for b in r["testu01"]["batteries"]},
        dieharder=({k: r["dieharder"][k] for k in ("passed", "weak", "failed")}
                   if r["dieharder"].get("status") == "ok" else r["dieharder"].get("status"))) for r in results]


FIGURES = {f.__name__.split("_")[0]: f for f in [
    fig01_circuits, fig02_variants_uniform, fig03_noise_bias, fig04_readout_table, fig05_entropy_saturation,
    fig06_correlation_floor, fig07_linear_complexity, fig08_lfsr_example, fig09_entropy_curves,
    fig10_hmin_datasets, fig11_piling_up, fig12_toeplitz_structure, fig13_toeplitz_example, fig14_lhl_length,
    fig15_column_bias, fig16_column_heatmap, fig17_bytepair, fig18_autocorr, fig19_pvalue_hist,
    fig20_proportion, fig21_nist_heatmap, fig22_testu01_strip, fig23_random_walk, fig24_throughput,
    fig25_parking_lot, fig26_toeplitz_universal, fig27_lhl_tradeoff]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--results", default="results/full/summary.json")
    ap.add_argument("--out", default="figures")
    ap.add_argument("--only", default="", help="comma-separated figure ids, e.g. fig07,fig11")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    results = json.loads(Path(a.results).read_text())
    data_path = out / "data.json"
    if data_path.exists():
        DATA.update(json.loads(data_path.read_text()))
    bits = Bits(a.data_dir)
    wanted = [w.strip() for w in a.only.split(",") if w.strip()] or list(FIGURES)
    for key in wanted:
        t = time.time()
        print(f"{key} ...")
        FIGURES[key](out, bits, results)
        print(f"  {time.time() - t:.0f}s")
    data_extras(results)
    data_path.write_text(json.dumps(DATA, indent=1, default=float))
    print(f"wrote {data_path}")


if __name__ == "__main__":
    main()
