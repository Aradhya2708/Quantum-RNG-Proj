# Randomness test summary (full profile)

Generated 2026-11-13 18:57 UTC by `python -m hqrng.pipeline`.

| Dataset | Bits | Ones % | h_min/bit | Linear complexity per qubit (ideal ≈ n/2) | NIST SP 800-22 sub-tests passed | TestU01 Rabbit | TestU01 Alphabit | TestU01 LinearComp | Dieharder |
|---|---:|---:|---:|---|---|---|---|---|---|
| `urandom` | 1.00e+08 | 50.003 | 0.9971 | 25000, 25000, 25000 (n=50000) | 188/188 (100 seq) ✓ | 38/38 ✓ | 17/17 ✓ | 4/4 ✓ | 48P/1W/0F |
| `aer_D_5k` | 1.00e+08 | 49.994 | 0.9973 | 25000, 25001, 25000 (n=50000) | 187/188 (100 seq) ✓ (within chance: NonOverlappingTemplate) | 38/38 ✓ | 17/17 ✓ | 4/4 ✓ | 49P/0W/0F |
| `aer_D_ideal` | 1.00e+08 | 50.002 | 0.9973 | 19937, 19937, 19937 (n=50000) **MT19937** | 188/188 (100 seq) ✓ | 38/38 ✓ | 17/17 ✓ | 2/4 ✗ | 46P/3W/0F |
| `aer_D_sym2pct` | 1.00e+08 | 50.005 | 0.9971 | 25000, 25000, 25001 (n=50000) | 187/188 (100 seq) ✓ (within chance: NonOverlappingTemplate) | 38/38 ✓ | 17/17 ✓ | 4/4 ✓ | 47P/2W/0F |
| `aer_D_ibmlike` | 1.10e+08 | 48.688 | 0.9607 | 25002, 25003, 25000 (n=50000) | 70/162 (100 seq) ✗ Frequency, BlockFrequency, CumulativeSums, Runs, LongestRun, NonOverlappingTemplate, OverlappingTemplate, Universal, ApproximateEntropy, Serial | 14/38, 3 susp. ✗ | 2/17, 2 susp. ✗ | 4/4 ✓ | 26P/1W/22F |
| `aer_D_ibmlike_toeplitz` | 1.04e+08 | 50.002 | 0.9972 | 25000, 25001, 25001 (n=50000) | 187/188 (100 seq) ✓ (within chance: NonOverlappingTemplate) | 38/38 ✓ | 17/17 ✓ | 4/4 ✓ | 48P/1W/0F |

## Failing or suspicious results

**urandom**

- Dieharder sts_serial (ntup 16): p = 0.00377 (weak)

**aer_D_5k**

- NIST NonOverlappingTemplate: 1/148 sub-tests failed (min proportion 0.95, min uniformity P 0.000233)

**aer_D_ideal**

- TestU01 lincomp / LinearComp r=0 s=1 n=400020 (jump count): p = 1 (fail)
- TestU01 lincomp / LinearComp r=29 s=1 n=400020 (jump count): p = 1 (fail)
- Dieharder sts_serial (ntup 9): p = 0.00216 (weak)
- Dieharder sts_serial (ntup 9): p = 0.00175 (weak)
- Dieharder sts_serial (ntup 10): p = 0.00231 (weak)

**aer_D_sym2pct**

- NIST NonOverlappingTemplate: 1/148 sub-tests failed (min proportion 0.95, min uniformity P 0.00716)
- Dieharder diehard_rank_32x32 (ntup 0): p = 0.998 (weak)
- Dieharder diehard_craps (ntup 0): p = 0.000758 (weak)

**aer_D_ibmlike**

- NIST Frequency: 1/1 sub-tests failed (min proportion 0.00, min uniformity P 0.0)
- NIST BlockFrequency: 1/1 sub-tests failed (min proportion 0.00, min uniformity P 0.0)
- NIST CumulativeSums: 2/2 sub-tests failed (min proportion 0.00, min uniformity P 0.0)
- NIST Runs: 1/1 sub-tests failed (min proportion 0.00, min uniformity P 0.0)
- NIST LongestRun: 1/1 sub-tests failed (min proportion 0.73, min uniformity P 0.0)
- NIST NonOverlappingTemplate: 82/148 sub-tests failed (min proportion 0.00, min uniformity P 0.0)
- NIST OverlappingTemplate: 1/1 sub-tests failed (min proportion 0.01, min uniformity P 0.0)
- NIST Universal: 1/1 sub-tests failed (min proportion 0.92, min uniformity P 0.0)
- NIST ApproximateEntropy: 1/1 sub-tests failed (min proportion 0.00, min uniformity P 0.0)
- NIST Serial: 1/2 sub-tests failed (min proportion 0.31, min uniformity P 0.0)
- TestU01 rabbit / AppearanceSpacings: p = 0.999 (suspicious)
- TestU01 rabbit / LempelZiv: p = 1 (fail)
- TestU01 rabbit / HammingWeight: p = 0 (fail)
- TestU01 rabbit / HammingCorr, L = 32: p = 0 (fail)
- TestU01 rabbit / HammingCorr, L = 64: p = 0 (fail)
- TestU01 rabbit / HammingCorr, L = 128: p = 0 (fail)
- TestU01 rabbit / HammingIndep, L = 16: p = 0 (fail)
- TestU01 rabbit / HammingIndep, L = 32: p = 0 (fail)
- TestU01 rabbit / HammingIndep, L = 64: p = 0 (fail)
- TestU01 rabbit / Run of bits: p = 0 (fail)
- TestU01 rabbit / RandomWalk1 H: p = 0 (fail)
- TestU01 rabbit / RandomWalk1 M: p = 0 (fail)
- TestU01 rabbit / RandomWalk1 J: p = 0 (fail)
- TestU01 rabbit / RandomWalk1 C: p = 0.000592 (suspicious)
- TestU01 rabbit / RandomWalk1 H (L = 1024): p = 0 (fail)
- TestU01 rabbit / RandomWalk1 M (L = 1024): p = 0 (fail)
- TestU01 rabbit / RandomWalk1 J (L = 1024): p = 0 (fail)
- TestU01 rabbit / RandomWalk1 R (L = 1024): p = 3.27e-08 (suspicious)
- TestU01 rabbit / RandomWalk1 C (L = 1024): p = 5.89e-11 (fail)
- TestU01 rabbit / RandomWalk1 H (L = 10016): p = 0 (fail)
- TestU01 rabbit / RandomWalk1 M (L = 10016): p = 0 (fail)
- TestU01 rabbit / RandomWalk1 J (L = 10016): p = 0 (fail)
- TestU01 rabbit / RandomWalk1 R (L = 10016): p = 0 (fail)
- TestU01 rabbit / RandomWalk1 C (L = 10016): p = 0 (fail)
- TestU01 alphabit / MultinomialBitsOver, L = 2: p = 0 (fail)
- TestU01 alphabit / MultinomialBitsOver, L = 4: p = 0 (fail)
- TestU01 alphabit / MultinomialBitsOver, L = 8: p = 0 (fail)
- TestU01 alphabit / MultinomialBitsOver, L = 16: p = 0 (fail)
- TestU01 alphabit / HammingIndep, L = 16: p = 0 (fail)
- TestU01 alphabit / HammingIndep, L = 32: p = 0 (fail)
- TestU01 alphabit / HammingCorr, L = 32: p = 0 (fail)
- TestU01 alphabit / RandomWalk1 H (L = 64): p = 0 (fail)
- TestU01 alphabit / RandomWalk1 M (L = 64): p = 0 (fail)
- TestU01 alphabit / RandomWalk1 J (L = 64): p = 0 (fail)
- TestU01 alphabit / RandomWalk1 H (L = 320): p = 0 (fail)
- TestU01 alphabit / RandomWalk1 M (L = 320): p = 0 (fail)
- TestU01 alphabit / RandomWalk1 J (L = 320): p = 0 (fail)
- TestU01 alphabit / RandomWalk1 R (L = 320): p = 7.2e-05 (suspicious)
- TestU01 alphabit / RandomWalk1 C (L = 320): p = 7.32e-08 (suspicious)
- Dieharder diehard_bitstream (ntup 0): p = 0 (failed)
- Dieharder diehard_count_1s_str (ntup 0): p = 0 (failed)
- Dieharder diehard_count_1s_byt (ntup 0): p = 0 (failed)
- Dieharder diehard_craps (ntup 0): p = 1 (failed)
- Dieharder sts_monobit (ntup 1): p = 1 (failed)
- Dieharder sts_serial (ntup 1): p = 1 (failed)
- Dieharder sts_serial (ntup 2): p = 0 (failed)
- Dieharder sts_serial (ntup 3): p = 0 (failed)
- Dieharder sts_serial (ntup 4): p = 0 (failed)
- Dieharder sts_serial (ntup 5): p = 0 (failed)
- Dieharder sts_serial (ntup 6): p = 0 (failed)
- Dieharder sts_serial (ntup 7): p = 0 (failed)
- Dieharder sts_serial (ntup 8): p = 0 (failed)
- Dieharder sts_serial (ntup 9): p = 0 (failed)
- Dieharder sts_serial (ntup 10): p = 0 (failed)
- Dieharder sts_serial (ntup 11): p = 0 (failed)
- Dieharder sts_serial (ntup 12): p = 0 (failed)
- Dieharder sts_serial (ntup 13): p = 0 (failed)
- Dieharder sts_serial (ntup 14): p = 0 (failed)
- Dieharder sts_serial (ntup 15): p = 0 (failed)
- Dieharder sts_serial (ntup 16): p = 0 (failed)
- Dieharder rgb_lagged_sum (ntup 0): p = 1 (failed)
- Dieharder rgb_kstest_test (ntup 0): p = 0.00393 (weak)

**aer_D_ibmlike_toeplitz**

- NIST NonOverlappingTemplate: 1/148 sub-tests failed (min proportion 0.95, min uniformity P 0.000883)
- Dieharder sts_serial (ntup 12): p = 0.997 (weak)


## Notes

- NIST: 188 sub-tests, each judged on proportion (≥ 0.99 − 3σ) and P-value uniformity (≥ 1e-4; only applied with ≥ 55 sequences, per SP 800-22 §4.2.2). Random Excursions only uses sequences with ≥ 500 cycles (~60%), so its sample is smaller. With 148 NonOverlappingTemplate sub-tests an ideal source fails up to 3 by chance (99% level); the table calls that "marginal".
- TestU01 Rabbit/Alphabit: nb (sequence length) is chosen so the file is never exhausted (they read ~23× and ~9× nb bits).
- TestU01: suspicious = p outside [0.001, 0.999]; fail = outside [1e-10, 1 − 1e-10]. LinearComp uses BigCrush's parameters (n = 400020, bits 0 and 29 of each word).
- h_min: most conservative of the SP 800-90B MCV, Markov and per-qubit MCV estimates.
- Linear complexity: Berlekamp–Massey on single bit positions followed across shots; 19937 is the Mersenne Twister state size.
