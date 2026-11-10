# Findings from reviewing the Hybrid QRNG notebooks

A review of `Quantum_random_number_generator.ipynb` (Report I) and
`noise_analysis.ipynb` (Report II), done while building the test-suite harness.
Every number below is reproduced by `python -m hqrng.audit` (about 15 s) or by
the pipeline (`results/`). These points should be settled before the four test
suites are run and written up, because several change what the tests can
legitimately claim.

## Summary

| # | Finding | Effect on the report |
|---|---|---|
| 1 | AerSimulator's measurement outcomes come from a Mersenne Twister (MT19937) PRNG | Results so far characterise MT19937, not quantum randomness |
| 2 | Models A–D prepare the identical quantum state | Model differences in the tables are sampling noise |
| 3 | "Shannon entropy 12.29 bits" equals log₂(5000) | The entropy columns measure the shot count, not the generator |
| 4 | The noise pipeline cannot produce a bias, whatever its error rate | The robustness result holds by construction |
| 5 | NIST was run on one 160,000-bit sequence | That is not the SP 800-22 protocol |
| 6 | Smaller data-handling problems | Shot order lost; README example returns a mode |

## 1. The simulator's randomness is a Mersenne Twister

Aer runs these circuits with its **stabilizer** method (they use only X, H and
CNOT), and every random measurement outcome is drawn from Aer's classical PRNG:

* `seed_simulator=42` twice gives **bit-identical** output;
* following one classical bit across the 50,000 shots of a circuit, the
  Berlekamp–Massey linear complexity is **exactly 19937** for every bit position
  tested. A random sequence of that length has ≈ 25,000; 19937 is the degree of
  the MT19937 recurrence. (numpy's PCG64 on the same length: 24,999.)

So "intrinsically random… physically impossible to predict" applies to a
quantum device, not to this output. With the seed, the output is fully predictable.
Using a simulator to **build and validate the pipeline** is fine; claims about
quantum randomness need hardware bits (IBM Quantum's free plan, ANU's archive,
or any hardware QRNG). The harness takes any bit file, so swapping the source
is a one-line change.

This is also the best argument for running several suites: NIST SP 800-22
cannot see this structure (its linear-complexity test uses 500–5000-bit
blocks), but **TestU01's LinearComp** (400,020-bit sequences) can. See the
pipeline results.

## 2. Models A, B, C and D are the same distribution

H|0⟩ = |+⟩ and H|1⟩ = |−⟩, and CNOT maps a product of |±⟩ states to another
product of |±⟩ states (|−⟩|−⟩ → |+⟩|−⟩, etc.). So after the CNOT layer
the register is still an unentangled product state, and every outcome has
probability exactly 2⁻³² in all four models. Statevector simulation confirms
entanglement entropy ≈ 10⁻¹⁵ and |P(x) − 1/64| ≈ 10⁻¹⁷ for every model
(6-qubit version). The X-gate seed only changes signs, and the "dice"
measurement order permutes independent fair bits; neither changes the output
distribution.

The average |off-diagonal correlation| expected from sampling noise alone for N
independent fair bits is √(2/πN): **0.0178** at 2000 shots and **0.0113** at
5000. The reported values (0.015–0.019 and 0.011–0.015) are exactly that
floor. Model D's 0.0110 vs Model A's 0.0150 is noise, and a rerun reorders the
models. "Model D wins" and "fixed CNOT structure introduces skew" are not
supported.

On real hardware the comparison flips: CNOTs add two-qubit gate error and
crosstalk without adding randomness, so Model A plus an extractor is the
stronger design. That is a testable claim once hardware data is available.

## 3. The entropy columns measure the number of shots

With 2³² possible outcomes and 5000 shots, every outcome is (almost always)
seen once, so the plug-in Shannon and min-entropy of the counts are both
log₂(5000) = 12.2877 (and log₂(2000) = 10.9658), independent of how good the
generator is. Model B's min-entropy 11.29 = log₂(2500) is one outcome seen
twice, a birthday collision with probability 0.3% per run, not distributional
skew. Better measures: per-bit entropy on large samples, and the SP 800-90B
estimators in `hqrng.entropy`.

## 4. The noise model cannot fail

* Layer 2 flips seed bits before the Hadamards. That turns |+⟩ into |−⟩,
  which still measures 50/50.
* Layer 4 flips output bits symmetrically. A fair bit XOR an independent
  flip is still a fair bit, at any flip rate.

So "noise-robust at 2%" would hold at 20% or 50% as well. (The standalone
Layer 2 cell also uses `p_init = 0.5`, not 0.02.) The noise that matters on
superconducting hardware is **asymmetric readout error**: |1⟩ decays to |0⟩
during measurement, so P(0|1) is several times P(1|0), which biases each qubit
towards 0 by a different amount. The `ibm-like` preset in `hqrng.noise`
models this. It makes the raw bits fail NIST's frequency tests, and Toeplitz
extraction then fixes them. That is the result a noise chapter should show.

## 5. The NIST run is not the SP 800-22 protocol

`NIST TEST.png` shows a single 160,000-bit sequence through a Python GUI.
SP 800-22 tests many sequences (NIST uses 100 × 10⁶ bits) and judges each
test by the proportion that pass and the uniformity of their p-values. One
sequence gives one p-value per test, and at α = 0.01 a perfect generator
fails about one test in a hundred anyway. The README's explanation of the
Maurer p = −1 is correct (the minimum is 387,840 bits). `hqrng.suites.nist_sts`
runs the official C suite on the full protocol.

## 6. Smaller issues

* **Shot order.** The bit matrices are rebuilt from `get_counts()`
  with `np.repeat`, which groups identical outcomes and loses time order.
  Harmless at 32 bits and 5000 shots; with fewer qubits (real devices) or more
  shots it creates artificial runs. Use `memory=True` (done in
  `hqrng.generate`).
* **README example.** `generate_qrng_modelD()` returns
  `max(counts, key=counts.get)`, the most frequent outcome. With all counts
  equal to 1 this is just the first key, and it spends 5000 shots on one number.
  Use `shots=1`, or keep all shots as output.
* **The correlation matrix** checks only pairwise linear dependence between
  bit positions *within* a shot. Dependence *across* shots, which is where a
  PRNG's structure is, isn't measured. The test suites cover this.
* **ANU comparison.** 8192 bits estimate the bias to ±0.0055, so both sources
  look identical at that size. The README already notes this.

## Results of the test suites (full profile)

`python -m hqrng.pipeline --profile full`: 10⁸ bits per dataset, NIST at
100 × 10⁶ bits, Model D with 32 qubits. Full table, with every p-value, in
[results/full/summary.md](../results/full/summary.md).

| Dataset | Ones % | NIST SP 800-22 | TestU01 Rabbit | TestU01 Alphabit | TestU01 LinearComp |
|---|---:|---|---|---|---|
| `urandom` (control: OS CSPRNG) | 50.003 | 188/188 ✓ | 38/38 ✓ | 17/17 ✓ | 4/4 ✓ |
| `aer_D_5k` (the notebooks' setup) | 49.994 | 187/188 ✓ | 38/38 ✓ | 17/17 ✓ | 4/4 ✓ |
| `aer_D_ideal` (100k shots/circuit) | 50.002 | 188/188 ✓ | 38/38 ✓ | 17/17 ✓ | **2/4 ✗** |
| `aer_D_sym2pct` (notebook noise) | 50.005 | 187/188 ✓ | 38/38 ✓ | 17/17 ✓ | 4/4 ✓ |
| `aer_D_ibmlike` (asymmetric readout) | 48.688 | **70/162 ✗** | **14/38 ✗** | **2/17 ✗** | 4/4 ✓ |
| `aer_D_ibmlike_toeplitz` | 50.002 | 187/188 ✓ | 38/38 ✓ | 17/17 ✓ | 4/4 ✓ |

187/188 is within chance: an ideal source fails up to 3 of the 148
NonOverlappingTemplate sub-tests at the 99% level. Dieharder was not run here
(no Windows build); use WSL or the GitHub Actions workflow.

What this shows:

1. **Only TestU01 catches the simulator.** In the ideal run every qubit's bit
   sequence has linear complexity 19937. LinearComp's "jump count" p-value is 1
   on both bit positions. NIST and Rabbit/Alphabit pass the same data.
2. **Passing ≠ quantum.** The notebooks' setup (`aer_D_5k`) passes everything,
   including LinearComp, only because Aer re-seeds its PRNG every 5000-shot
   circuit, which leaves segments too short for the test. With 2% readout
   noise the LinearComp failure also disappears: the noise is sampled by
   comparing PRNG doubles to a threshold, which is non-linear. Both datasets
   are still fully determined by their seeds. Statistical tests can reject a
   bad source; they cannot certify a quantum one.
3. **Realistic noise is caught, and extraction fixes it.** Per-qubit
   asymmetric readout error (P(0|1) = 1–6%, P(1|0) = 0.2–1.5%) gives 48.7%
   ones. NIST fails every bias-sensitive test, and Rabbit/Alphabit fail their
   Hamming-weight and random-walk tests. The 800-90B-style estimate gives
   h_min = 0.961 bits/bit. Toeplitz hashing with n = 16384, m = 15536
   (ε = 2⁻¹⁰⁰) brings the output back to 50.002% ones and a clean pass on every
   suite, at a cost of 5.2% of the bits.

## Suggested framing for the write-up

1. Simulator stage: the pipeline is correct (bits, file formats, extractor,
   suites), and the four suites agree with expectations for an ideal 50/50
   source. TestU01 also detects that the "ideal" source is a PRNG.
2. Noise stage: with realistic asymmetric readout error the raw bits are
   biased and fail; entropy estimation plus Toeplitz extraction recovers
   output that passes all suites.
3. Hardware stage (next): run Model A on IBM hardware, keep shot order, and
   push the bits through the same harness.
