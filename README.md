# 🔬 Hybrid Quantum Random Number Generator (QRNG)

> **B.S. Physics Project** | Qiskit AerSimulator | 32-Qubit System | NIST SP 800-22 Validated  
> **Author:** Amee Ghai — B23PH1003

---

> **🧪 New: randomness test suites.** Test any bit stream with **NIST SP 800-22**,
> **TestU01** and **Dieharder**, with **Toeplitz** extraction, in one command.
> Start here: [Randomness Test Suites — Quick Start](#-randomness-test-suites--quick-start).
> Latest results: [results/full/summary.md](results/full/summary.md).
> Review notes that affect some results below: [docs/FINDINGS.md](docs/FINDINGS.md).

---

## 📌 Table of Contents

- [Randomness Test Suites — Quick Start](#-randomness-test-suites--quick-start)
- [Overview](#-overview)
- [Motivation](#-motivation)
- [Circuit Architectures](#-circuit-architectures)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
- [Usage](#-usage)
- [Results — Report I (Model Comparison)](#-results--report-i-model-comparison)
- [Results — Report II (Noise Robustness)](#-results--report-ii-noise-robustness)
- [NIST SP 800-22 Validation](#-nist-sp-800-22-validation)
- [ANU Hardware Comparison](#-anu-hardware-comparison)
- [Key Findings](#-key-findings)
- [Limitations & Future Work](#-limitations--future-work)
- [References](#-references)

---

## 🧪 Randomness Test Suites — Quick Start

The `hqrng/` package runs the whole testing pipeline for you and writes one summary table:

```
raw bits ──► entropy estimate ──► Toeplitz extractor ──► NIST SP 800-22 · TestU01 · Dieharder ──► summary.md
```

| Suite | What it checks |
|---|---|
| **NIST SP 800-22** | The US standard: 15 tests (188 results) for bias, streaks and repeated patterns, run on 100 × 1 million bits |
| **TestU01** | Tougher academic tests (Rabbit, Alphabit, LinearComp). LinearComp spots bits that come from a formula |
| **Dieharder** | Classic Diehard tests: small simulations whose answer is known for true randomness |
| **Toeplitz extractor** | Not a test: turns slightly biased raw bits into fair ones, with a proven guarantee |
| **Entropy estimate** | How much real randomness each raw bit holds (SP 800-90B style). Sets how much Toeplitz keeps |

### What you need

| | Linux / macOS | Windows |
|---|---|---|
| Python 3.10+ | ✓ | ✓ |
| `gcc`, `curl`, `unzip` (to build the test tools) | `sudo apt install build-essential curl unzip` (macOS: Xcode command-line tools) | Git Bash plus MinGW `gcc`, e.g. from [MSYS2](https://www.msys2.org/) or [w64devkit](https://github.com/skeeto/w64devkit) |
| Dieharder | `sudo apt install dieharder` | Built natively by `tools/setup_tools.sh` (see [Dieharder on Windows](#dieharder-on-windows)) |

### Step 1 — Install (once)

```bash
git clone -c core.longpaths=true https://github.com/Ameeghai/Quantum-RNG-Hybrid.git
cd Quantum-RNG-Hybrid
python -m venv .venv
source .venv/bin/activate              # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
bash tools/setup_tools.sh              # downloads and builds NIST STS and TestU01 into third_party/
python -m pytest -q tests              # should end with "19 passed"
```

> **Windows:** keep the project on a short path such as `C:\qrng`. Paths longer than
> 260 characters break `gcc` and Qiskit Aer. If you build the tools somewhere else,
> tell the scripts where: `export HQRNG_TOOLS=C:/qrng-tools`.

### Step 2 — Run everything with one command

```bash
python -m hqrng.pipeline --profile quick --out results/quick   # 32 million bits per dataset, fastest
python -m hqrng.pipeline --profile full  --out results/full    # 100 million bits per dataset (NIST's standard protocol)
```

This generates the data, runs every suite, and writes:

- `results/<name>/summary.md`: one table with every dataset and suite
- `results/<name>/summary.json`: every individual p-value

Generated bits are saved in `data/` and reused next time. Run time depends on your CPU (the full profile took about 12 minutes on a 22-core machine).

The datasets it tests by default:

| Dataset | What it is |
|---|---|
| `urandom` | Your operating system's secure random generator: a control that should pass everything |
| `aer_D_5k` | Model D exactly as in the notebooks (5000 shots per run) |
| `aer_D_ideal` | Model D with large runs (100,000 shots per run) |
| `aer_D_sym2pct` | Model D with the notebooks' 2% symmetric noise |
| `aer_D_ibmlike` | Model D with realistic, uneven read-out errors like a real IBM chip |
| `aer_D_ibmlike_toeplitz` | The same noisy bits after Toeplitz extraction |

Useful options: `--datasets urandom,aer_D_ibmlike` (run only some), `--suites nist,testu01` (skip a suite), `--workers 4` (CPU cores to use).

### Step 3 — Test your own bits (real hardware, ANU, notebook output)

Save the bits as a file (raw bits packed 8 per byte, in the order they were measured):

```python
from hqrng.bitio import write_bits, read_qrng_header_bin

write_bits("data/mybits.bin", bits)    # bits = any list/array of 0s and 1s

# or convert a file saved by the notebooks:
write_bits("data/notebook.bin", read_qrng_header_bin("qrng_output_AFTER_noise.bin").ravel())
```

For IBM Quantum hardware, keep the shot order: use `memory=True` or SamplerV2's `get_bitstrings()`, not `get_counts()`.

Then run the steps one at a time:

```bash
python -m hqrng.entropy   data/mybits.bin --width 32                      # 1. prints h_min (randomness per bit)
python -m hqrng.extractor data/mybits.bin data/mybits_clean.bin --h-min 0.95  # 2. Toeplitz; use the h_min from step 1
python -m hqrng.suites.nist_sts  data/mybits_clean.bin                    # 3. NIST SP 800-22
python -m hqrng.suites.testu01   data/mybits_clean.bin                    # 4. TestU01
python -m hqrng.suites.dieharder data/mybits_clean.bin --reference data/urandom.bin  # 5. Dieharder, sized to the file
```

How much data each test needs:

| Test | Minimum | Recommended |
|---|---|---|
| NIST SP 800-22 | 100 × 1 million bits (12.5 MB) for the standard protocol | same |
| TestU01 Rabbit / Alphabit | ~1.6 million / ~0.6 million bits | 100 million bits |
| TestU01 LinearComp | ~26 million bits (3.2 MB) | same |
| Dieharder | 10⁸ bits runs 19 of its tests, each sized so the file is never re-read | gigabytes for the full `-a` battery |

### Dieharder on Windows

Dieharder is a Linux tool, but `tools/setup_tools.sh` builds a native `dieharder.exe` on Windows
(`tools/build_dieharder_mingw.sh`: Dieharder 3.31.1 + GSL, statically linked, MinGW `gcc` and `zstd` needed).
Alternatives:

- **WSL:** run `wsl --install` in PowerShell, open Ubuntu, then
  `sudo apt install dieharder build-essential curl unzip python3-venv` and follow Steps 1–2 inside it.
- **GitHub Actions:** on GitHub, open **Actions → randomness-tests → Run workflow**, pick `quick` or `full`,
  and download the `randomness-results-…` artifact when it finishes. It runs all suites, including Dieharder.

### Reading the results

- **NIST:** `188/188 ✓` is a pass. With 148 NonOverlappingTemplate tests, perfect random bits still fail
  up to 3 by chance; the table marks that as "within chance".
- **TestU01:** each test gives a p-value. Anything between 0.001 and 0.999 is a pass; a value stuck at 0 or 1 is a fail.
- **Dieharder:** `PASSED` / `WEAK` / `FAILED`. A few `WEAK` results are normal.
- **h_min:** 1.0 means perfectly fair bits. Real random data at this size gives about 0.997.
- **Important:** tests can only find patterns. Passing does not prove the bits are quantum: a good formula passes too.
  See [docs/FINDINGS.md](docs/FINDINGS.md).

### Troubleshooting

| Problem | Fix |
|---|---|
| `Filename too long` when cloning | Clone with `-c core.longpaths=true` into a short folder like `C:\qrng` |
| `DLL load failed … filename too long` from Qiskit Aer (Windows) | Move the project and `.venv` to a short path |
| `gcc: command not found` during setup | Install `gcc` (see [What you need](#what-you-need)) and run setup in a shell where `gcc --version` works |
| NIST or TestU01 shows `unavailable` | The tools aren't built yet: run `bash tools/setup_tools.sh`, or set `HQRNG_TOOLS` to where you built them |
| NIST or TestU01 reports `insufficient-data` | The file is too small; see the data table above |
| Dieharder shows `unavailable` | Run `bash tools/setup_tools.sh` (Windows) or `sudo apt install dieharder` (Linux/WSL) |

More detail, including every option: [docs/TEST_SUITES.md](docs/TEST_SUITES.md).

---

## 🧭 Overview

This project designs, implements, and rigorously evaluates a **Hybrid Quantum Random Number Generator (QRNG)** using Qiskit's `AerSimulator`. The system combines classical shot-noise seeding with quantum superposition (Hadamard gates) and entanglement (CNOT gates) to generate cryptographically-grade 32-bit random integers.

Four distinct circuit architectures (Models A–D) are designed and compared across entropy, correlation, and NIST statistical test compliance. The best-performing model (Model D) is then subjected to a full **five-layer noise robustness pipeline** to simulate real hardware error conditions.

**Key outcome:** Model D (Dice-CNOT + Dice-Measurement, 5000 shots) achieves maximum entropy (12.29 bits), zero Shannon–Min entropy gap, and lowest average off-diagonal correlation (0.0110), passing 15/16 NIST SP 800-22 tests and matching ANU real quantum hardware benchmarks.

---

## 💡 Motivation

Classical Pseudo-Random Number Generators (PRNGs) are **deterministic** — given a seed, the sequence is entirely reproducible. This makes them unsuitable for:

- Cryptographic key generation
- Quantum cryptography protocols (BB84, E91)
- Monte Carlo simulations requiring true unpredictability
- Hardware security modules (HSMs)

Quantum mechanics provides a fundamentally different approach. When a qubit is placed in superposition via a **Hadamard gate** and measured, the outcome is **intrinsically random** — not just computationally hard to predict, but physically impossible to predict even in principle. This project exploits that property to build a practical QRNG.

---

## ⚛️ Circuit Architectures

All four models share the same base pipeline:

```
Classical Shot-Noise Seed → X Gates → Hadamard Gates (Superposition) → [Optional CNOT] → Measure → Sample
```

| Model | Name | Dice Ordering | CNOT Entanglement | Description |
|-------|------|:---:|:---:|---|
| **A** | Baseline | ✗ | ✗ | Sequential Hadamard + direct measurement (q0–q31). Reference architecture. |
| **B** | CNOT Layer | ✗ | ✓ | Hadamard + CNOT gates with fixed shuffle-and-pair entanglement structure. |
| **C** | Dice Measure | ✓ | ✗ | Hadamard + randomised dice-based measurement ordering. No entanglement. |
| **D ★** | Full Hybrid | ✓ | ✓ | Dice-based CNOT pairing + dice measurement ordering. Both entanglement and readout fully randomised each run. **Best model.** |

### Model D — Circuit Design Detail

- **32 qubits** (q0–q31) each producing 1 bit → 32-bit integer output per shot
- **Classical seed:** NumPy-generated 32-bit string at `p = 0.5` applied via X gates
- **Hadamard layer:** Primary entropy source — puts each qubit into equal superposition
- **Dice-CNOT:** CNOT target pairs randomised each run using a dice roll — prevents fixed entanglement bias
- **Dice-Measurement:** Qubit readout order randomised each run — adds unpredictability in classical post-processing

---

## 📁 Project Structure

```
QRNG-Project/
│
├── notebooks/
│   ├── Quantum_random_number_generator.ipynb   # Report I: 4 model designs & comparison
│   └── noise_analysis.ipynb                    # Report II: Noise robustness pipeline
│
├── reports/
│   ├── QRNG_Model_Comparison_Report.docx       # Detailed Report I write-up
│   └── Noise_Analysis_Report.docx              # Detailed Report II write-up
│
├── presentation/
│   └── QRNG_Presentation.pdf                   # Full project presentation slides
│
├── results/
│   ├── nist_input.txt                          # Binary output for NIST test suite
│   ├── correlation_matrices/                   # Saved correlation heatmaps (PNG)
│   └── full/summary.md                         # Test-suite results (NIST, TestU01, Toeplitz)
│
├── hqrng/                                      # Test-suite harness: generate, entropy, Toeplitz, suites, pipeline
├── tools/                                      # Build scripts for NIST STS and TestU01
├── tests/                                      # Unit tests (pytest)
├── docs/                                       # TEST_SUITES.md (how-to), FINDINGS.md (review notes)
├── requirements.txt
│
└── README.md
```

---

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.9+
- Qiskit (AerSimulator)
- NumPy, Matplotlib, SciPy

### Install Dependencies

```bash
pip install qiskit qiskit-aer numpy matplotlib scipy
```

To run the randomness test suites as well, follow the [Quick Start](#-randomness-test-suites--quick-start) instead (`pip install -r requirements.txt` plus a one-time tool build).

### Optional: NIST SP 800-22 Test Suite

Download and compile from the official NIST source:

```bash
# Clone the NIST randomness test suite
git clone https://github.com/dj-on-github/sp800_22_tests.git
cd sp800_22_tests
make
```

Or use the GUI version from [https://csrc.nist.gov/projects/random-bit-generation](https://csrc.nist.gov/projects/random-bit-generation)

---

## 🚀 Usage

### Run Report I — Model Comparison

Open and run all cells in:

```
notebooks/Quantum_random_number_generator.ipynb
```

This notebook:
1. Defines all four circuit architectures (Models A–D)
2. Runs each model at 2000 and 5000 shots
3. Computes Shannon entropy, Min-entropy, and qubit-wise Pearson correlation matrices
4. Plots correlation heatmaps for visual inspection
5. Exports a binary output file for NIST testing

### Run Report II — Noise Analysis

Open and run all cells in:

```
notebooks/noise_analysis.ipynb
```

This notebook:
1. Takes Model D as the base architecture
2. Passes output through a 5-layer noise pipeline (see below)
3. Compares noisy vs. noiseless entropy and correlation metrics
4. Benchmarks against ANU real quantum hardware data

### Quick Example — Generate a Random 32-bit Integer (Model D)

```python
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
import numpy as np

def generate_qrng_modelD(shots=5000):
    n_qubits = 32
    seed_bits = np.random.choice([0, 1], size=n_qubits, p=[0.5, 0.5])
    
    # Dice-based CNOT pairs and measurement order
    qubits = list(range(n_qubits))
    np.random.shuffle(qubits)
    cnot_pairs = [(qubits[i], qubits[i+1]) for i in range(0, n_qubits-1, 2)]
    measure_order = list(range(n_qubits))
    np.random.shuffle(measure_order)
    
    qc = QuantumCircuit(n_qubits, n_qubits)
    
    # Apply seed via X gates
    for i, bit in enumerate(seed_bits):
        if bit == 1:
            qc.x(i)
    
    # Hadamard layer
    for i in range(n_qubits):
        qc.h(i)
    
    # Dice-CNOT entanglement
    for ctrl, tgt in cnot_pairs:
        qc.cx(ctrl, tgt)
    
    # Dice-ordered measurement
    for i, q in enumerate(measure_order):
        qc.measure(q, i)
    
    simulator = AerSimulator()
    job = simulator.run(transpile(qc, simulator), shots=shots)
    counts = job.result().get_counts()
    
    # Sample one bitstring and convert to integer
    bitstring = max(counts, key=counts.get)
    return int(bitstring, 2)

random_number = generate_qrng_modelD()
print(f"Generated 32-bit random number: {random_number}")
```

---

## 📊 Results — Report I (Model Comparison)

### Entropy & Correlation Summary

| Model | Shots | Shannon Entropy (bits) | Min-Entropy (bits) | Avg Off-Diag Correlation | Status |
|-------|:---:|:---:|:---:|:---:|:---:|
| Model A | 2000 | 10.97 | 10.97 | 0.0190 | ✅ Pass |
| Model A | 5000 | 12.29 | 12.29 | 0.0150 | ✅ Pass |
| Model B | 2000 | 10.97 | 10.97 | 0.0180 | ✅ Pass |
| Model B | 5000 | 12.29 | 11.29 | 0.0140 | ⚠️ Partial |
| Model C | 2000 | 10.97 | 10.97 | 0.0170 | ✅ Pass |
| Model C | 5000 | 12.29 | 12.29 | 0.0130 | ✅ Pass |
| **Model D ★** | **2000** | **10.97** | **10.97** | **0.0150** | ✅ **Pass** |
| **Model D ★** | **5000** | **12.29** | **12.29** | **0.0110** | 🏆 **Best** |

> ★ **Model D at 5000 shots** is selected as the best architecture — highest entropy, zero Shannon/Min gap, lowest correlation.

### Qubit-wise Correlation Matrices

All models produce 32×32 Pearson correlation matrices. In a good QRNG, only the diagonal (self-correlation = 1.0) should be red; all off-diagonal elements should be near zero (pale/white). All models achieve this, confirming qubit independence.

**Model B Note:** At 5000 shots, Model B shows a Shannon–Min entropy gap (12.29 vs 11.29 bits), indicating occasional distributional skew introduced by the **fixed** CNOT pairing structure. Randomising the CNOT pairs (Model D) eliminates this.

---

## 📊 Results — Report II (Noise Robustness)

### Five-Layer Noise Pipeline

```
L1: Classical Shot-Noise Seed
    └─ 32-bit NumPy seed, p=0.5 · Per-bit entropy ≈ 0.9994 bits
       ↓
L2: Initialisation Noise (Bit-Flip Error)
    └─ Seed bits flip with p_init = 0.02 (2%) · Models state preparation errors
       ↓
L3: Quantum Circuit — Model D
    └─ Hadamard + Dice-CNOT + Dice-Measurement · Per-bit entropy ≈ 0.9998 bits
       ↓
L4: Measurement Noise (Bit-Flip Error)
    └─ Output bits flip with p_meas = 0.02 (2%) · Models readout error
       ↓
L5: Correlation Analysis
    └─ 32×32 Pearson matrix · Avg off-diagonal ≈ 0.0115
```

### Noisy vs. Noiseless Results

| Metric | Noiseless (`p=0`) | Noisy (`p=0.02`) | Verdict |
|--------|:---:|:---:|:---:|
| Per-Bit Entropy | ≈ 0.9998 bits/bit | ≈ 0.9998 bits/bit | ✅ Identical |
| Min-Entropy | ≈ 31.99 bits | ≈ 31.99 bits | ✅ Identical |
| Shannon Entropy (strings) | ≈ 12.29 bits | ≈ 12.29 bits | ✅ Identical |
| Avg Off-Diagonal Correlation | ≈ 0.0112 | ≈ 0.0115 | ✅ Negligible difference |

> **Key Finding:** The Hadamard + CNOT structure effectively "washes out" low-level (2%) bit-flip noise. The pipeline is noise-robust.

---

## ✅ NIST SP 800-22 Validation

The binary output of Model D (5000 shots) was tested against the full NIST SP 800-22 statistical test suite for random number generators.

| # | Test | Result |
|---|------|:---:|
| 01 | Frequency (Monobit) | ✅ Random |
| 02 | Frequency within Block | ✅ Random |
| 03 | Runs Test | ✅ Random |
| 04 | Longest Run of 1s | ✅ Random |
| 05 | Binary Matrix Rank | ✅ Random |
| 06 | DFT (Spectral) | ✅ Random |
| 07 | Non-overlapping Template Matching | ✅ Random |
| 08 | Overlapping Template Matching | ✅ Random |
| **09** | **Maurer's Universal Statistical** | **⚠️ Non-Random** |
| 10 | Linear Complexity | ✅ Random |
| 11 | Serial Test | ✅ Random |
| 12 | Approximate Entropy | ✅ Random |
| 13 | Cumulative Sums (Forward) | ✅ Random |
| 14 | Cumulative Sums (Backward) | ✅ Random |
| 15 | Random Excursions | ✅ Random |
| 16 | Random Excursions Variant | ✅ Random |

**Result: 15/16 PASS**

### Note on Test 09 (Maurer's Universal)

Test 09 returned `p-value = −1.0`, flagged as Non-Random. This is **not a randomness failure**. A p-value of exactly `−1.0` is a **sentinel value** indicating the test could not execute — the bit sequence was too short. Maurer's Universal test requires a minimum of **387,840 bits** to produce meaningful results. The current output (~160,000 bits at 5000 shots × 32 bits) is insufficient for this specific test. All other 15 tests passed with `p > 0.05`.

To pass Test 09, significantly more quantum shots or real hardware execution would be required.

---

## 🔬 ANU Hardware Comparison

The simulated QRNG output was benchmarked against the **Australian National University (ANU) QRNG**, which generates true random numbers from quantum vacuum fluctuations in a real optical setup. 1024 `uint8` values (8192 bits) were fetched from the ANU API for comparison.

| Metric | Simulated QRNG (Model D) | ANU Real QRNG | Assessment |
|--------|:---:|:---:|:---:|
| Per-Bit Entropy | ≈ 0.9999 bits/bit | ≈ 0.9997 bits/bit | ✅ Both near-ideal |
| Sequential (Lag-1) Autocorrelation | ≈ −0.003 | ≈ +0.009 | ✅ Both near-zero |
| Source | Qiskit AerSimulator | Real optical hardware | ✅ Comparable quality |

> The simulation faithfully models real QRNG behaviour at both per-bit entropy and autocorrelation metrics. The difference between simulated and real hardware is statistically negligible at these metrics.

---

## 🔑 Key Findings

1. **Shot count is the primary driver of entropy.** Increasing shots from 2000 → 5000 consistently improved Shannon entropy from ~10.97 to ~12.29 bits across all models. At 2000 shots, all models appear nearly identical.

2. **The Hadamard layer does the heavy lifting.** The superposition layer generates the majority of randomness. CNOT entanglement and dice-based ordering provide secondary improvements in correlation and distributional uniformity.

3. **Fixed CNOT structure introduces distributional skew.** Model B (fixed CNOT pairs) showed a Shannon–Min entropy gap at 5000 shots (12.29 vs 11.29 bits), indicating bias from fixed entanglement patterns. Randomising CNOT pairs (Model D) eliminates this.

4. **Model D wins on all three metrics.** Maximum entropy (12.29 bits), zero Shannon–Min gap, and lowest correlation (0.0110). Randomised CNOT + randomised measurement ordering prevents systematic patterns.

5. **The pipeline is noise-robust at 2% error rates.** Noisy and noiseless configurations produce virtually identical statistical outputs, confirming that the quantum circuit absorbs low-level hardware noise.

6. **Simulation matches real quantum hardware.** Per-bit entropy ≥ 0.9997 and near-zero autocorrelation in both simulated and ANU real hardware outputs confirm the validity of the simulation approach.

---

## ⚠️ Limitations & Future Work

### Current Limitations

- Noise levels tested (2%) are mild — real quantum hardware error rates can be 5–20%
- Independent bit-flip noise model used; real hardware noise is **correlated** across qubit pairs (crosstalk, coherence decay)
- Per-bit entropy near 1.0 is necessary but not sufficient for full output uniformity
- ANU comparison limited to only 8,192 bits — too small for rigorous statistical inference
- Test 09 (Maurer's Universal) could not be evaluated due to insufficient sample size

### Future Work

- [ ] Re-run noise analysis at 5%, 10%, 20% error rates to identify degradation threshold
- [ ] Implement correlated, structured noise models matching real IBM Quantum chip topologies
- [ ] Run full NIST SP 800-22 suite with a much larger sample (1M+ bits)
- [ ] Deploy on real IBM Quantum hardware (via IBM Quantum Network) for direct physical validation
- [ ] Explore qubit count scaling (64, 128-qubit systems) for higher-bit output
- [ ] Investigate post-processing extractors (e.g., Toeplitz hashing) to further whiten output

---

## 📚 References

1. Nielsen, M. A., & Chuang, I. L. (2010). *Quantum Computation and Quantum Information*. Cambridge University Press.
2. NIST SP 800-22 Rev 1a — *A Statistical Test Suite for Random and Pseudorandom Number Generators for Cryptographic Applications*. [https://csrc.nist.gov/publications/detail/sp/800-22/rev-1a/final](https://csrc.nist.gov/publications/detail/sp/800-22/rev-1a/final)
3. Qiskit Documentation — AerSimulator. [https://qiskit.github.io/qiskit-aer/](https://qiskit.github.io/qiskit-aer/)
4. ANU Quantum Random Numbers Server. [https://qrng.anu.edu.au/](https://qrng.anu.edu.au/)
5. Maurer, U. M. (1992). A universal statistical test for random bit generators. *Journal of Cryptology*, 5(2), 89–105.
6. Ma, X., et al. (2016). Quantum random number generation. *npj Quantum Information*, 2, 16021.

---

## 📄 License

This project was developed as a B.S. Physics project at IIT Jodhpur. For academic and research use only.

---

<div align="center">
  <sub>Built with ⚛️ Qiskit · Python · NumPy · Matplotlib</sub>
</div>
