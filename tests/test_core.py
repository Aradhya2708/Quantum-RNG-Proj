import math
import struct

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

from hqrng import bitio, entropy, extractor, lincomp
from hqrng.circuits import build_circuit
from hqrng.noise import expected_p1, readout_table


# ---------------------------------------------------------------- extractor
@pytest.mark.parametrize("n,m", [(64, 40), (257, 128), (1024, 960)])
def test_toeplitz_fft_matches_explicit_matrix(n, m):
    rng = np.random.default_rng(n)
    x = rng.integers(0, 2, 5 * n + 7, dtype=np.uint8)       # 5 blocks + leftover
    seed = rng.integers(0, 2, n + m - 1, dtype=np.uint8)
    T = extractor.toeplitz_matrix(seed, n, m)
    expect = np.concatenate([(T.astype(int) @ x[k * n:(k + 1) * n]) % 2 for k in range(5)])
    got = extractor.toeplitz_extract(x, n, m, seed, blocks_per_batch=2)
    assert got.dtype == np.uint8 and np.array_equal(got, expect)


def test_toeplitz_matrix_is_toeplitz():
    seed = np.arange(10) % 2
    T = extractor.toeplitz_matrix(seed, 6, 5)
    assert all(np.all(np.diag(T, k) == np.diag(T, k)[0]) for k in range(-4, 6))


def test_output_length():
    assert extractor.output_length(16384, 1.0) == 16384 - 200
    assert extractor.output_length(16384, 0.9) == math.floor(16384 * 0.9 - 200) // 8 * 8
    with pytest.raises(ValueError):
        extractor.output_length(128, 0.5)


def test_extractor_removes_bias():
    rng = np.random.default_rng(0)
    x = (rng.random(2_000_000) < 0.42).astype(np.uint8)       # strongly biased input
    h = entropy.assess(x, 32)["h_min"]
    m = extractor.output_length(4096, h)
    y = extractor.toeplitz_extract(x, 4096, m, extractor.random_seed(4096, m))
    assert abs(y.mean() - 0.5) < 5 * 0.5 / math.sqrt(len(y))


# ---------------------------------------------------------------- entropy
def test_mcv_and_markov_on_known_sources():
    rng = np.random.default_rng(1)
    fair = rng.integers(0, 2, 1_000_000, dtype=np.uint8)
    assert entropy.mcv(fair) > 0.99 and entropy.markov(fair) > 0.99
    biased = (rng.random(1_000_000) < 0.3).astype(np.uint8)   # P(0) = 0.7
    assert entropy.mcv(biased) == pytest.approx(-math.log2(0.7), abs=0.005)
    sticky = np.repeat(fair[:100_000], 4)                      # strongly correlated
    assert entropy.markov(sticky) < 0.5 < entropy.mcv(sticky)


def test_per_qubit_mcv_sees_one_bad_qubit():
    rng = np.random.default_rng(2)
    rows = rng.integers(0, 2, (100_000, 32), dtype=np.uint8)
    rows[:, 5] = rng.random(100_000) < 0.2
    cols = entropy.per_column_mcv(rows.reshape(-1), 32)
    assert cols[5] < 0.35 and np.delete(cols, 5).min() > 0.97


# ---------------------------------------------------------------- lincomp
def test_linear_complexity():
    # LFSR x^5 + x^2 + 1 has linear complexity 5
    s = [1, 0, 0, 1, 0]
    while len(s) < 200:
        s.append(s[-5] ^ s[-3])
    assert lincomp.linear_complexity(np.array(s)) == 5
    r = np.random.default_rng(3).integers(0, 2, 2000)
    assert abs(lincomp.linear_complexity(r) - 1000) <= 5


# ---------------------------------------------------------------- bitio
def test_bit_roundtrip(tmp_path):
    bits = np.random.default_rng(4).integers(0, 2, 8000, dtype=np.uint8)
    p = bitio.write_bits(tmp_path / "x.bin", bits)
    assert np.array_equal(bitio.read_bits(p), bits)
    assert p.stat().st_size == 1000


def test_read_notebook_qrng_format(tmp_path):
    rows = np.random.default_rng(5).integers(0, 2, (10, 32), dtype=np.uint8)
    p = tmp_path / "q.bin"
    with open(p, "wb") as f:                          # exactly as noise_analysis.ipynb writes it
        f.write(b"QRNG" + struct.pack("<I", 10) + struct.pack("<I", 32))
        for row in rows:
            f.write(struct.pack("<I", int("".join(map(str, row)), 2)))
    assert np.array_equal(bitio.read_qrng_header_bin(p), rows)


# ---------------------------------------------------------------- circuits / noise
@pytest.mark.parametrize("model", list("ABCD"))
def test_every_model_gives_exactly_uniform_product_state(model):
    rng = np.random.default_rng(6)
    for _ in range(5):
        qc = build_circuit(model, 6, rng).remove_final_measurements(inplace=False)
        probs = Statevector(qc).probabilities()
        assert np.allclose(probs, 1 / 64, atol=1e-12)


def test_model_structure():
    qc = build_circuit("D", 32, np.random.default_rng(7))
    ops = qc.count_ops()
    assert ops["h"] == 32 and ops["cx"] == 16 and ops["measure"] == 32
    assert "cx" not in build_circuit("A", 32).count_ops()


def test_noise_presets():
    assert readout_table("none", 4) is None
    assert np.allclose(expected_p1("symmetric:0.02", 4), 0.5)       # symmetric flips keep 50/50
    p1 = expected_p1("readout:0.05,0.01", 4)
    assert np.allclose(p1, 0.5 * 0.95 + 0.5 * 0.01)
    ibm = expected_p1("ibm-like", 32)
    assert ibm.mean() < 0.49 and len(set(ibm.round(6))) == 32


# ---------------------------------------------------------------- NIST judging
def test_nist_rules_match_sts():
    from hqrng.suites import nist_sts
    assert nist_sts.min_pass_count(100) == 96                 # STS: "approximately = 96"
    report = "\n".join([
        "  9  11  10  10  10  10  10  10  10  10  0.911413     96/100      Frequency",
        "  9  11  10  10  10  10  10  10  10  10  0.911413     95/100  *   Runs",
        " 30  11   5   5   5   5   5  10  10  14  0.000001 *  100/100      Rank",
        "  1   0   1   1   0   0   2   0   0   0     ----       5/5       RandomExcursions",
    ])
    rows = {r["test"]: r for r in nist_sts.parse_report(report)}
    assert rows["Frequency"]["ok"] and not rows["Runs"]["ok"] and not rows["Rank"]["ok"]
    assert rows["RandomExcursions"]["ok"]                     # too few sequences for uniformity
    assert nist_sts.allowed_failures(148, 100) == 3 and nist_sts.allowed_failures(1, 100) == 0


def test_testu01_nb_fits_file():
    from hqrng.suites import testu01
    words = 100_000_000 // 32
    assert testu01.choose_nb("rabbit", words) == 1 << 21      # 2^22 needs 3.15M words > 3.125M
    assert testu01.choose_nb("alphabit", words) == 1 << 23
    assert testu01.choose_nb("rabbit", 1000) is None


def test_dieharder_parse_rows_and_rewinds():
    from hqrng.suites.dieharder import parse
    text = """
   diehard_birthdays|   0|       100|       1|0.35850958|  PASSED
# The file file_input_raw was rewound 2 times
          sts_serial|   9|    100000|       1|0.00215623|   WEAK
      diehard_craps|   0|    200000|       1|0.00000000|  FAILED
"""
    tests, rewinds = parse(text)
    assert rewinds == 2
    assert [t["verdict"] for t in tests] == ["passed", "weak", "failed"]
    assert tests[1]["ntup"] == 9 and tests[0]["psamples"] == 1
