# Randomness test suites: how to run them

This harness takes bits from any source (the Aer models, a file from real
hardware, ANU data), estimates their min-entropy, optionally runs them through
a Toeplitz extractor, and runs the standard test suites on the result.

```
raw bits ──► SP 800-90B entropy estimate ──► Toeplitz extractor ──► NIST SP 800-22
 (Aer or        (MCV, Markov, per qubit)        (m = n·h − 2·log₂(1/ε))   TestU01
  hardware)                                                               Dieharder
```

## The suites and what each one is for

| # | Suite | What it is | What it catches | Data it needs | Runs on |
|---|---|---|---|---|---|
| 1 | **NIST SP 800-22** (official STS 2.1.2) | 15 tests, 188 sub-tests, judged over many sequences | bias, runs, periodicity, template patterns, low linear complexity *within 500–5000-bit blocks* | 100 × 10⁶ bits (the standard protocol) | Windows, Linux, macOS |
| 2 | **TestU01** (Rabbit, Alphabit, LinearComp; SmallCrush optional) | L'Ecuyer & Simard's library; Rabbit/Alphabit were designed for finite hardware-RNG files | everything above, plus long-range linear structure (LinearComp on 400k-bit sequences, which is what exposes a Mersenne Twister) | Rabbit/Alphabit: any size; LinearComp: 2.6×10⁷ bits; SmallCrush: 7.3×10⁹ bits | Windows (MinGW), Linux, macOS |
| 3 | **Dieharder** | Marsaglia's Diehard tests + extras, ~114 results | distributional tests on 32-bit words (birthday spacings, parking lot, etc.) | `-a` wants GBs; smaller files get **rewound**, which causes false failures | Linux / WSL / CI only |
| 4 | **Toeplitz extractor** | not a test — the post-processing step real QRNGs need | turns biased raw bits with min-entropy *h* into ε-uniform output | — | everywhere |
| 5 | **SP 800-90B entropy estimate** (suggested fifth) | min-entropy of the *raw* source | sizes the extractor; a source fails if *h* is far below what is claimed | ≥ 10⁶ samples | everywhere (subset here; full NIST tool on Linux) |

NIST and Dieharder test *statistical* randomness of the output. Neither can
prove a bit is quantum or unpredictable: a good PRNG passes both. That is why
the entropy estimate of the raw source (5) and the extractor (4) belong in any
QRNG evaluation, and why it matters what the raw bits came from (see
[FINDINGS.md](FINDINGS.md)).

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # Linux/macOS: .venv/bin/python
bash tools/setup_tools.sh                                    # downloads + builds STS and TestU01
```

`setup_tools.sh` builds into `third_party/` (ignored by git). On **Windows**,
paths longer than 260 characters break both gcc and Qiskit Aer's DLL loading:
if the repo lives under a long path, put the tools and the venv somewhere short:

```bash
export HQRNG_TOOLS=C:/qrng-tools
bash tools/setup_tools.sh
```

Windows needs Git-Bash or MSYS2 with MinGW gcc (no autotools needed; TestU01 is
built by `tools/build_testu01_mingw.sh`). Dieharder has no Windows build: use
WSL (`sudo apt install dieharder`) or the GitHub Actions workflow
(`.github/workflows/randomness.yml`, run it from the Actions tab).

## Everything at once

```bash
python -m hqrng.pipeline --profile quick --out results/quick     # 3.2e7 bits/dataset, ~10 min
python -m hqrng.pipeline --profile full  --out results/full      # 1e8 bits/dataset (NIST protocol), ~12 min on 22 cores
```

Writes `results/<name>/summary.md` (table) and `summary.json` (every p-value).
Generated data goes to `data/` and is reused on the next run.

## One step at a time

```bash
# 1. Generate (Model A-D; noise: none | symmetric:P | readout:P10,P01 | ibm-like)
python -m hqrng.generate --model D --bits 1.1e8 --noise ibm-like --seed 1 --out data/ibm.bin

# 2. Estimate min-entropy per bit of the raw source
python -m hqrng.entropy data/ibm.bin --width 32

# 3. Extract with that estimate
python -m hqrng.extractor data/ibm.bin data/ibm_toeplitz.bin --h-min 0.95 --block 16384

# 4. Test
python -m hqrng.suites.nist_sts  data/ibm_toeplitz.bin --streams 100 --keep results/nist_ibm
python -m hqrng.suites.testu01   data/ibm_toeplitz.bin --batteries rabbit,alphabit,lincomp
python -m hqrng.suites.dieharder data/ibm_toeplitz.bin          # Linux/WSL

# Diagnostics
python -m hqrng.lincomp data/ibm.bin          # per-qubit linear complexity
python -m hqrng.audit                         # re-check docs/FINDINGS.md
```

### Testing bits from real hardware or other sources

Every tool reads a raw file of packed bits, MSB first (`numpy.packbits`).
To convert:

```python
import numpy as np
from hqrng.bitio import write_bits, read_qrng_header_bin
write_bits("data/hw.bin", my_0_1_array)                          # any 0/1 array
write_bits("data/old.bin", read_qrng_header_bin("qrng_output_AFTER_noise.bin").ravel())
```

For IBM Quantum hardware results, keep shot order (`memory=True` / the
SamplerV2 `get_bitstrings()`), not `get_counts()`.

## Reading the results

* **NIST**: each of the 188 sub-tests passes if at least 0.99 − 3σ of the
  sequences pass (96/100) *and* the p-values are uniform (P ≥ 10⁻⁴). With 188
  sub-tests, one marginal NonOverlappingTemplate failure is expected by chance;
  the summary marks that as "marginal", not "fail".
* **TestU01**: p outside [0.001, 0.999] is "suspicious", outside
  [10⁻¹⁰, 1 − 10⁻¹⁰] is a clear failure (the TestU01 guide's convention).
  A suspicious p on one test is normal across ~50 tests; a repeatable one is not.
* **Dieharder**: PASSED / WEAK / FAILED per test. WEAK results are expected
  (about 1 in 100); check the "rewound" count before believing a FAILED.
* **Entropy**: `h_min` is the most conservative estimate per raw bit. An ideal
  fair coin gives ≈ 0.9996 at 10⁸ bits (the 99% confidence bound costs a little).
