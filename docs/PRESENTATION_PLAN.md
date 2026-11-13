# Presentation plan: Testing Quantum Random Number Generators

Built: `presentation/QRNG_Testing_Lecture.pptx` (generator: `presentation/build_deck.js`).

**Revision 2 (built deck, 29 slides):** sections A and B simplified (noise and read-out profile merged into one slide, less text throughout); two maths slides added to section C (why Toeplitz hashing is 2-universal, with a Monte Carlo check, and a derivation of the Leftover Hash Lemma); section D text shortened and the worked NIST examples (19) removed; the limitations slide (29) removed; authors Aradhya Mahajan (B23CS1088) and Amee Ghai (B23PH1003) added. The outline below is the original plan.

Long-form lecture, 30 slides, about 75–90 minutes (2.5–3 minutes per slide).
Every figure below is already generated in `figures/` by `python -m hqrng.figures`;
the numbers for native PowerPoint charts and tables are in `figures/data.json`.
"Native" means built as a PowerPoint chart, table or diagram rather than an image.

Scope rules:
- This is a standalone project on testing QRNGs. Earlier reports are not quoted or referred to.
  The circuit variants are presented as our test source, nothing more.
- No introductory quantum mechanics (qubits, Hadamard, Bloch sphere).
- Every result shown comes from our code and data.

---

## Part A — Problem and test source (slides 1–5)

### 1. Title
Testing Quantum Random Number Generators: entropy estimation, Toeplitz extraction and four statistical test suites.
Visual: the pipeline strip (native): source → raw bits → entropy estimate → Toeplitz → NIST · TestU01 · Dieharder → verdict.

### 2. Why randomness quality matters
- Uses: key generation, nonces/IVs, one-time pads, Monte Carlo, lotteries.
- Two real failures: Debian OpenSSL 2006–2008 (seed reduced to the process ID → only 32,768 possible keys per type);
  Sony PS3 2010 (ECDSA nonce reused → private signing key recovered).
- PRNG vs classical TRNG vs QRNG: deterministic/physical, predictable with the seed / in principle / not at all, speed.
Visual: native comparison table + two-event timeline.

### 3. What can go wrong in a QRNG, and how we test for it
- Failure modes: physical bias, uneven read-out, drift and correlation, a classical PRNG hidden in the chain, too little data.
- Our pipeline and what each stage answers: how much entropy? → make it uniform → can we find any pattern?
- Five tools: NIST SP 800-22, TestU01, Dieharder, Toeplitz extractor, SP 800-90B-style entropy estimate (data needed, platform).
Visual: native pipeline diagram + tool table.

### 4. The test source: four circuit variants
- 32 qubits; X gates from seed bits, H on every qubit, optional random CNOT matching (B, D), optional shuffled read-out (C, D).
- Statevector check: all four give exactly uniform, completely unentangled states. CNOT on |±⟩ products only maps them to other |±⟩ products.
  A Bell pair (H then CNOT on |00⟩) is shown for contrast: 1 bit of entanglement.
- Consequence: on a simulator the variants are statistically identical; they differ only on hardware (CNOTs add two-qubit error).
Visuals: `fig01_circuits.png`, `fig02_variants_uniform.png`.

### 5. Generating bits at scale
- Code: `build_circuit()` + `AerSimulator.run(..., memory=True)` keeps shot order; one `SeedSequence` child per circuit,
  so output is identical whatever the number of workers. Format: raw bits packed MSB-first.
- Six datasets, 10⁸ bits each: control (OS random), simulator with 5k and 100k shots per circuit, 2% symmetric noise,
  uneven read-out noise, the same noisy bits after Toeplitz.
- Speed: up to 3.3 Mbit/s with 8 workers on 22 logical CPUs.
Visuals: code snippet, native dataset table, `fig24_throughput.png` (or native chart from `data.json → throughput`).

## Part B — Noise and measurement pitfalls (slides 6–9)

### 6. Which noise can bias a fair qubit?
- Symmetric flip with any rate: fair bit XOR independent flip = fair bit, so P(1) stays 0.5.
- Uneven read-out: P(1) = ½(1 − P(0|1)) + ½·P(1|0), so the output leans towards 0.
- Aer simulation at six error rates matches the formula.
Visual: `fig03_noise_bias.png`.

### 7. A realistic read-out profile
- IBM-like preset: per-qubit P(0|1) 1–6 % (decay during read-out), P(1|0) 0.2–1.5 %.
- Every qubit leans towards 0; mean P(1) = 48.69 %; worst qubit −2.7 points.
Visual: `fig04_readout_table.png`.

### 8. Simple metrics can mislead
- Entropy of outcome counts: with 2³² outcomes and N shots every outcome appears once, so Shannon = min-entropy = log₂N
  (12.29 bits at N = 5000) for any good source. One repeat (birthday collision, p ≈ 0.29 % at N = 5000) drops min-entropy by 1 bit.
- Pairwise correlation of independent bits has a floor of √(2/πN): 0.0178 at N = 2000, 0.0113 at N = 5000.
- Lesson: use per-bit entropy estimators and proper test suites.
Visuals: `fig05_entropy_saturation.png`, `fig06_correlation_floor.png`.

### 9. The simulator's hidden formula
- Aer runs X/H/CNOT circuits with its stabilizer method; every random outcome comes from a Mersenne Twister (MT19937).
  Same `seed_simulator` → bit-identical output.
- Linear complexity (Berlekamp–Massey): a sequence from a linear recurrence of size L can be reproduced from 2L bits.
  Random bits: L ≈ n/2. One bit position of Aer's output: L stops at exactly 19,937 (the MT state size).
- Implication: a simulator validates the pipeline, not quantum randomness.
Visuals: `fig07_linear_complexity.png`, small inset `fig08_lfsr_example.png` (4-bit LFSR: L = 4, period 15).

## Part C — Entropy and extraction (slides 10–16)

### 10. Shannon vs min-entropy
- H = −Σ p log₂ p (average surprise) vs H∞ = −log₂ max p (best single guess); crypto uses H∞.
- Worked example from our noisy data: P(1) = 0.4869 → Shannon 0.9995, min-entropy 0.9626.
Visual: `fig09_entropy_curves.png`.

### 11. Estimating min-entropy (SP 800-90B style)
- Most common value: p_u = p̂ + 2.576·√(p̂(1−p̂)/(L−1)), H = −log₂ p_u (99 % upper bound).
- Markov: first-order transition probabilities, most likely 128-bit path.
- Per bit position (catches per-qubit bias). h_min = minimum of the three.
- Results: 0.997 for every fair dataset (the confidence bound costs 0.003), 0.961 for the noisy source.
Visual: `fig10_hmin_datasets.png`.

### 12. Why extract, and why XOR works
- Raw physical bits are biased and possibly correlated; tests would (rightly) reject them.
- Von Neumann (01→0, 10→1, drop 00/11): needs i.i.d. input, keeps ≤ 25 %.
- XOR of k independent bits with bias ε has bias 2^(k−1)·εᵏ (piling-up lemma): 0.0132 → 0.00035 for k = 2, measured.
Visual: `fig11_piling_up.png`.

### 13. The Toeplitz matrix
- T[i, j] = s[i − j + n − 1]: constant diagonals, so n + m − 1 seed bits define an m × n matrix.
- Random Toeplitz matrices form a 2-universal hash family; output y = T·x mod 2.
- Worked 4 × 6 example by hand.
Visuals: `fig12_toeplitz_structure.png`, `fig13_toeplitz_example.png`.

### 14. How many bits can we keep? The Leftover Hash Lemma
- m = ⌊n·h − 2·log₂(1/ε)⌋ makes the output ε-close to uniform; ε = 2⁻¹⁰⁰ costs 200 bits per block.
- Our run: n = 16,384, h = 0.9607 → m = 15,536 (keeps 94.8 %).
- Strong extractor: the seed can be public and reused across blocks; it came from `os.urandom`.
Visual: `fig14_lhl_length.png`.

### 15. Implementation and effect on the bits
- T·x computed as a convolution with FFT: O(n log n) instead of O(n·m); checked against the explicit matrix in unit tests.
- Code snippet from `hqrng/extractor.py`.
- Effect: 48.69 % → 50.002 % ones; every bit position back inside ±3σ.
Visual: code + `fig15_column_bias.png`.

### 16. Looking at the bits: visual diagnostics
- Bias map (10,000-shot blocks × 32 positions): stripes before, noise after.
- Byte-pair heat map (bytes sorted by number of 1s): a gradient before, flat after.
- Autocorrelation (lags 1–70, 50 M bits): inside ±3σ both before and after, so it cannot see bias.
Visuals: `fig16_column_heatmap.png`, `fig17_bytepair.png`, `fig18_autocorr.png`.

## Part D — Statistical test suites (slides 17–25)

### 17. Hypothesis testing for randomness
- H₀: the bits are i.i.d. fair. p-value = probability of a result at least this extreme under H₀; reject at α = 0.01.
- Under H₀ p-values are uniform: a perfect source still fails 1 % of tests (type I error).
- Tests can only reject; a good PRNG passes everything.
Visual: `fig19_pvalue_hist.png` (monobit and runs, 100 sequences, control vs noisy vs Toeplitz).

### 18. NIST SP 800-22: the 15 tests
- Grouped by what they detect: frequency (monobit, block, cumulative sums), oscillation (runs, longest run),
  structure (rank, DFT), patterns (non-overlapping 148 templates, overlapping), compressibility (Maurer, approximate entropy, serial),
  linearity (linear complexity, 500-bit blocks), random walks (excursions, variant).
Visual: native grouped table.

### 19. Two NIST tests by hand
- Monobit: ε = 1011010101 → S = 2, s_obs = 0.632, p = 0.527.
- Runs: ε = 1001101011 → π = 0.6, V = 7, p = 0.147.
Visual: native worked tables (numbers in `data.json → monobit_example, runs_example`).

### 20. Running NIST properly
- 100 sequences × 10⁶ bits. Proportion rule: pass rate ≥ 0.99 − 3√(0.99·0.01/m) → at least 96/100.
- Uniformity: χ² over 10 bins of p-values, P ≥ 10⁻⁴ (only with ≥ 55 sequences).
- 148 template sub-tests: up to 3 may fail by chance (binomial, 99 % level).
- Official STS 2.1.2 driven non-interactively from Python.
Visual: `fig20_proportion.png` + code snippet.

### 21. NIST results
- Every fair dataset passes; 147/148 templates is within chance.
- Noisy source fails 10 of the 13 families that ran (70/162 sub-tests pass; rank, DFT and linear complexity still pass); random excursions cannot run (a drifting walk rarely returns to 0).
- Toeplitz output passes. NIST's linear-complexity test misses the Mersenne Twister (blocks too short).
Visual: `fig21_nist_heatmap.png`.

### 22. TestU01
- L'Ecuyer & Simard (2007). SmallCrush/Crush/BigCrush need 10⁹–10¹² bits; Rabbit and Alphabit were designed for finite files.
- Our harness reads the file directly, never rewinds, and sizes each battery to the file (Rabbit reads ~23 × nb bits).
- Example statistic: random walks (Rabbit's RandomWalk1, NIST cumulative sums): the noisy walk drifts ~26,000 steps in 10⁶ bits.
Visual: `fig23_random_walk.png` + C harness snippet.

### 23. LinearComp: catching a linear generator
- Berlekamp–Massey on 400,020-bit sequences (bits 0 and 29 of each word); two statistics: jump count and jump size.
- MT19937 is linear over GF(2): the complexity stops jumping at 19,937 → jump-count p = 1.0 (fail) on the 100k-shot data.
- Passes on the 5k-shot data (the generator is re-seeded every 5000 shots, so segments are too short) and on the noisy data
  (noise is drawn by comparing PRNG doubles to a threshold, which is non-linear). Both are still fully deterministic.
Visual: native table of LinearComp p-values per dataset + `fig08_lfsr_example.png` reminder.

### 24. TestU01 results
- Control, simulator variants and Toeplitz output: 38/38 Rabbit, 17/17 Alphabit.
- Noisy source: 14/38 Rabbit, 2/17 Alphabit (Hamming weight, random walks, multinomial).
- 100k-shot simulator: LinearComp 2/4 (the only suite that catches it).
Visual: `fig22_testu01_strip.png`.

### 25. Dieharder
- Marsaglia's Diehard (1995) extended by R. G. Brown: birthday spacings, overlapping permutations, matrix ranks,
  bitstream, parking lot, minimum distance, 3D spheres, squeeze, craps, plus extra tests.
- File input rewinds when the data runs out, which causes false failures, so the file size is chosen per test.
- Results: each test sized to the 10⁸-bit file (19 tests, 49 results, no rewinds): control and simulator pass; noisy source fails 22; after Toeplitz passes. A full `-a` run on a 1 GB control file re-read it 89+ times.
Visuals: `fig25_parking_lot.png` + native results table.

## Part E — Engineering and conclusions (slides 26–30)

### 26. The pipeline as software
- Modules: generate, noise, entropy, extractor, lincomp, suites (nist_sts, testu01, dieharder), pipeline, figures.
- One command: `python -m hqrng.pipeline --profile full` → summary table + every p-value; 12 minutes on 22 cores.
- Reproducible: seeds, worker-invariant output, 19 unit tests, GitHub Actions workflow.
Visual: native module diagram + command.

### 27. Scoreboard
- Six datasets × ones %, h_min, linear complexity, NIST, Rabbit, Alphabit, LinearComp, Dieharder.
Visual: native colour-coded table (`data.json → scoreboard`).

### 28. Which tool catches which flaw
- Matrix: bias / per-qubit bias / linear PRNG structure / short-range correlation × entropy estimate, NIST, TestU01, Dieharder, visual checks.
- Three lessons: run several suites; passing is not proof of quantum origin; extraction is part of the generator, not optional.
Visual: native matrix with ticks.

### 29. Limitations and next steps
- Source is simulated; noise model covers read-out only; the 800-90B estimators are a subset; 8 Dieharder tests need more than 10⁸ bits.
- Next: real hardware run (variant A, shot order kept), full 800-90B tool, BigCrush on GB-scale files,
  device-independent QRNG via Bell tests.
Visual: native three-stage roadmap.

### 30. Conclusion and references
- Key numbers recap; references: NIST SP 800-22 Rev. 1a, NIST SP 800-90B, L'Ecuyer & Simard (ACM TOMS 2007),
  Brown (Dieharder), Marsaglia (Diehard), Impagliazzo–Levin–Luby (LHL), Krawczyk (Toeplitz hashing),
  Berlekamp (1968) / Massey (1969), Matsumoto & Nishimura (MT19937, 1998), Herrero-Collantes & Garcia-Escartin (Rev. Mod. Phys. 2017),
  Qiskit Aer.
