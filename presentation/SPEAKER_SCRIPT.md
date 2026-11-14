# Speaker script: Testing Quantum Random Number Generators

Aradhya Mahajan (B23CS1088) · Amee Ghai (B23PH1003)

About 57 minutes plus questions at a relaxed pace (~130 words a minute, with time on each figure); the maths in section C can comfortably take longer. Every slide below is also in the deck's speaker notes
(`presentation/build_deck.js` reads this file). Text in [square brackets] is a stage cue,
not something to say.

Suggested split (change freely): **Amee**, slides 1–8 (motivation, the quantum source,
noise); **Aradhya**, slides 9–28 (entropy, extraction, test suites, results);
**together**, slide 29 and questions.

| Section | Slides | Time |
|---|---|---|
| A. Problem and test source | 1–5 | 10.5 min |
| B. Noise and pitfalls | 6–8 | 7 min |
| C. Entropy and extraction | 9–17 | 18 min |
| D. Statistical test suites | 18–25 | 15.5 min |
| E. Results and conclusion | 26–29 | 6 min |

---

## Slide 1 — Testing Quantum Random Number Generators · 2 min

Good morning, everyone. I'm Amee, and this is Aradhya. Today's lecture is about one question
that sounds simple and turns out not to be: how do you know that a random number generator,
and in particular a quantum one, is actually producing good random bits?

We'll answer it by building a complete testing pipeline. We generate bits from a quantum
circuit, estimate how much genuine randomness they contain, clean them with a Toeplitz
extractor, and then put them through five statistical test suites: NIST SP 800-22, three
test batteries from the TestU01 library (Rabbit, Alphabit and LinearComp) and Dieharder.

Two things to keep in mind as we go. First, every chart you'll see was computed from our own
code and our own data; nothing is copied from a paper. Second, the most interesting results
are the ones where a test *fails*, because that's where we learn what each tool can and
cannot see.

---

## Slide 2 — Weak randomness breaks real systems · 2.5 min

Why care about randomness quality at all? Because almost all of modern security quietly
assumes that random numbers cannot be guessed: encryption keys, the nonces in digital
signatures, session tokens, one-time pads. Simulations rely on it too.

The scary part is that bad randomness doesn't crash anything. [point to the first card]
In 2006 a change to Debian's copy of OpenSSL accidentally removed most of the seed. The
generator was left with only the process ID, so for two years every Debian machine could only
produce 32,768 different keys of each type. Anyone could precompute all of them.

[second card] In 2010 researchers showed that Sony's PlayStation 3 signed its software with
ECDSA but used the same "random" number for every signature. With two signatures and a bit of
algebra, the private signing key falls out.

[table] So there are three families of generators. A pseudo-random generator is a formula plus a
seed: fast, statistically excellent, and completely predictable to anyone who has the seed.
A classical true random generator measures thermal or electrical noise; it's unpredictable only
because we can't model the physics well enough. A quantum generator measures a quantum
outcome, which, by the Born rule, isn't decided until it's measured, so in principle nobody
can predict it. But all three still need testing, and that's what this talk is about.

---

## Slide 3 — From a quantum source to a verdict · 2 min

Here's the roadmap for the whole lecture. [walk the boxes left to right]

A quantum source produces raw bits, which we store in the order they were measured. Before
using them, we estimate how much genuine unpredictability each bit carries: the min-entropy.
That number decides how hard the Toeplitz extractor has to compress the raw bits to make them
uniform. Then the test suites look for any pattern at all, and we get a verdict: either a test
finds something and rejects the bits, or nothing is found.

[purple boxes] Notice that the two highlighted stages are the ones that turn a physical source
into a usable generator. The suites only judge the result.

[cards] We ran this on six datasets of 100 million bits each, which is the size NIST's protocol
asks for. One is a control, the operating system's own cryptographic generator, so that we know
what "good" looks like. Four come from our quantum simulator under different conditions, and
one is the extractor's output. And we used the five test suites listed on the right.

---

## Slide 4 — Four circuit variants, one identical distribution · 2 min

Our test source is a 32-qubit circuit. [point to variant A] Classical seed bits decide which
qubits get an X gate, every qubit gets a Hadamard, and then we measure. Variants B and D add a
random layer of CNOT gates; C and D shuffle which qubit is written to which output bit.

The natural expectation is that more gates means more randomness. We checked that with an exact
statevector simulation of all four variants, twenty random circuits each. [bottom charts] Two
results. Every one of the 2⁶ outcomes has probability exactly 1/64, up to floating-point
round-off at 10⁻¹⁷. And the entanglement of every qubit is 10⁻¹⁵, which is zero. For comparison
the orange bar is a real Bell pair, with one full bit of entanglement.

The reason is neat. After the Hadamards every qubit is in |+⟩ or |−⟩. A CNOT acting on a product
of |+⟩ and |−⟩ states just maps it to another product of |+⟩ and |−⟩ states, so it never creates
entanglement. So on a simulator the four variants are statistically identical. On real hardware
they would differ, but only because every CNOT adds two-qubit gate error.

---

## Slide 5 — Generating 10⁸ bits per dataset, reproducibly · 2 min

[code] This is the core of our generator. Each circuit gets its own random-number stream,
derived from one master seed, so the output is bit-for-bit identical no matter how many worker
processes we use. We simulate with memory equal to true, which keeps the shots in the order they
happened. The more common get_counts call groups identical outcomes together and destroys the
time order, which is exactly what several tests look at. Finally we pack the bits eight to a
byte and write them out.

[table] These are the six datasets. Look at the last column: everything sits at 50 percent ones
within a few thousandths, except one: the simulator with realistic read-out noise, at 48.69
percent. Keep that number in mind; it's the protagonist of the next twenty slides.

[chart] Generation speed tops out at about 3.3 million bits per second with eight workers;
beyond that, process start-up and memory bandwidth take over. So 100 million bits takes about
half a minute.

---

## Slide 6 — Only uneven read-out error can bias a fair qubit · 2.5 min

Real qubits are noisy, so we added noise to the simulator. The first instinct is a symmetric
bit-flip: flip each output bit with some probability p. [left chart, purple line] But look what
happens: whatever p is, the output stays at exactly 50 percent ones. The algebra is one line: a
fair bit becomes one with probability one half times one minus p, plus one half times p, which
is one half. So a symmetric noise model can never make a simulated QRNG fail a bias test,
however large the error rate. It looks robust by construction.

Real superconducting qubits behave differently. While a qubit in state |1⟩ is being read out it
can relax to |0⟩, so reading a 1 as a 0 is several times more likely than the reverse. [orange
line] Then the fraction of ones drops linearly with the error rate. The dots are our Aer
simulations at six error rates, and they sit exactly on the formula.

[right chart] So we built an IBM-like preset: each of the 32 qubits gets its own read-out error,
1 to 6 percent for reading 1 as 0, and 0.2 to 1.5 percent the other way. Every single qubit leans
towards 0, by up to 2.7 percentage points, and the stream as a whole has 48.69 percent ones.
That looks small. At a hundred million bits it's an enormous signal.

---

## Slide 7 — Simple metrics measure the sample size, not the source · 2 min

Before the real tools, two metrics that look informative but aren't.

[left chart] A common thing to do is to count how often each 32-bit outcome appears and compute
the entropy of those counts. But there are four billion possible outcomes. With 5,000 shots
almost every outcome appears exactly once, so the entropy comes out as log₂ of 5,000, 12.29
bits, for *any* good source. The curve just follows log₂N until N gets close to a few hundred
thousand. It's measuring the sample size, not the generator. The true answer for 32 fair bits
is 32.

[right chart] The second is correlation between bit positions. Even perfectly independent bits
show some correlation in a finite sample. The average size is √(2/πN): 0.018 at 2,000 shots,
0.011 at 5,000. Our control data sits exactly on that theoretical curve. Only correlation
clearly above this floor would mean anything.

The lesson is that we need proper per-bit entropy estimators and proper test suites, which is
where we're heading.

---

## Slide 8 — The simulator's randomness is a formula · 2.5 min

One more surprise before we move on. Qiskit Aer simulates X, H and CNOT circuits with its
stabilizer method, and every random measurement outcome is drawn from a classical
pseudo-random generator, the Mersenne Twister, MT19937. Run it twice with the same seed and you
get identical bits.

Can we see that in the data? Yes, with linear complexity: the length of the shortest linear
feedback shift register that reproduces a sequence. [right figure] A shift register is a tiny
circuit that produces each new bit as the XOR of a few earlier bits. This four-bit one repeats
every 15 bits, and its linear complexity stays at 4 forever. The Berlekamp–Massey algorithm
finds this length for any sequence.

[left chart] For random bits, linear complexity grows like n over 2: the grey line. Now take
one bit position from Aer's output, followed across 50,000 shots. It grows exactly like random
data, and then, at 19,937, it stops dead. 19,937 is the size of the Mersenne Twister's state:
every later bit is a linear function of the previous 19,937.

So the consequence: a simulator is perfect for building and validating the pipeline, but it
cannot tell us anything about quantum randomness. For that you need hardware. And as we'll see,
only one of our five test suites notices this.

---

## Slide 9 — Min-entropy is the measure that matters for security · 2 min

[handover] Thanks, Amee. I'll take us through entropy, extraction and the test suites.

How much randomness is in a biased bit? There are two standard answers. Shannon entropy is the
average surprise per bit, minus the sum of p log p. Min-entropy is minus log₂ of the single most
likely outcome: it tells you how often the *best possible* guesser would be right. Security uses
min-entropy, because an attacker doesn't average; they always guess the most likely value.

[chart] The two curves agree at a fair coin and diverge quickly with bias. For our noisy source,
with 48.69 percent ones, Shannon entropy is 0.9995 bits per bit, essentially perfect, while
min-entropy is only 0.9626. If we sized the extractor using Shannon entropy we'd claim almost 4
percent more randomness than is really there, and the security guarantee would be void.

---

## Slide 10 — Estimating min-entropy from data (SP 800-90B style) · 1.5 min

In practice we don't know the probabilities; we have to estimate them from data. NIST SP
800-90B is the standard for exactly that, and we implemented three of its estimators.

[cards] The most-common-value estimator takes the share of the most common symbol and adds a 99
percent confidence margin, so we never overstate the entropy. The Markov estimator models
dependence between consecutive bits and finds the most likely 128-bit path. And because each
qubit can be biased differently, we also run the most-common-value estimator separately on each
of the 32 bit positions.

We take the lowest of the three: the cautious choice. [chart] Every fair dataset gives 0.997,
not 1. That missing 0.003 is just the cost of the confidence margin at 10⁸ bits. The noisy
source gives 0.961, and that's the number that sizes our extractor.

---

## Slide 11 — Extraction: XOR shrinks bias geometrically · 2 min

So we have bits that are random, but slightly biased. Test suites will rightly reject them, and
an attacker's best guess is right more than half the time. Extraction fixes that.

The classic trick is von Neumann's: read bits in pairs, output 0 for "01", 1 for "10", and throw
away "00" and "11". It works, but it assumes the bits are independent and identically
distributed, and it throws away at least three quarters of the input.

The better idea is XOR. If you XOR k independent bits that each have bias ε, the bias of the
result is 2ᵏ⁻¹ εᵏ: it shrinks geometrically. That's called the piling-up lemma. [chart] Our
source starts at ε = 0.013. XOR two bits and the theory says 0.00035; we measured 0.00026, which
agrees within the statistical error. By k = 3 the bias is already below what 64 million bits can
even resolve: that's the flat dotted line.

A real extractor does this systematically: every output bit is the XOR of many input bits, chosen
by a matrix.

---

## Slide 12 — The Toeplitz matrix: a hash with constant diagonals · 2 min

That matrix is a Toeplitz matrix. [left figure] Its defining property is that every diagonal is
constant: the entry in row i, column j depends only on i minus j. So instead of storing all m
times n entries you only need the first row and the first column: n plus m minus 1 seed bits.
Here 37 bits define all 336 entries.

The output is y = T·x mod 2. [worked example] Each output bit is the XOR of the input bits in the
positions where that row has a 1. Take the first row: 0 0 1 1 0 1. The input is 0 1 1 1 0 1. The
row picks out positions 3, 4 and 6, which are 1, 1 and 1. Their sum is 3, and 3 mod 2 is 1. So
the first output bit is 1. The T·x column counts the matches, and mod 2 keeps only the parity.

The important property, which the next slide proves, is that random Toeplitz matrices form a
2-universal hash family.

---

## Slide 13 — Why Toeplitz hashing works: 2-universality · 2.5 min

What does 2-universal mean? [top card] A family of hash functions is 2-universal if, for any two
different inputs, a randomly chosen member of the family maps them to the same output with
probability at most 2⁻ᵐ. That's as good as a truly random function.

[second card] Because our hash is linear, we can simplify. T·x equals T·x′ exactly when T times
their difference is zero. The difference d = x XOR x′ is a non-zero vector, so all we need to
show is that for any non-zero d, the probability that T·d is the zero vector is 2⁻ᵐ.

[third card, figure] Here's the proof. Let j₀ be the position of the first 1 in d: the orange
column. Row i of T·d is the XOR of some seed bits. The one with the largest index is
s[i − j₀ + n − 1], the outlined cell. Now go down the rows: every row's largest seed index is
one more than the row above, so every row brings in a seed bit that no earlier row has used.
Conditioned on all the rows above, each row is a fresh fair coin. The m rows are independent fair
coins, and the chance they're all zero is exactly 2⁻ᵐ.

[bottom card, right chart] We also checked it numerically: 400,000 random seeds and random pairs
for each output size. At m = 8 we measured 0.0040; the theory says 2⁻⁸, which is 0.0039.

---

## Slide 14 — Deriving the Leftover Hash Lemma · 2.5 min

Now the central result: how many output bits can we safely keep? The Leftover Hash Lemma says
m = k − 2 log₂(1/ε). Here's where that comes from, in four steps.

[step 1] Collision probability: the chance that two independent draws from a distribution are
equal, the sum of the squared probabilities. If X has min-entropy k, every probability is at most
2⁻ᵏ, so its collision probability is at most 2⁻ᵏ.

[step 2] Now pick a random hash T from our 2-universal family and look at the pair (T, T·X). Two
independent copies collide only if they picked the same T, which has probability one over the size
of the family. Then either the inputs were equal, at most 2⁻ᵏ, or the hash collided anyway, at most
2⁻ᵐ.

[step 3] A distribution whose collision probability is almost as small as uniform's must be close
to uniform. Precisely, the statistical distance is at most one half of the square root of N times
CP minus 1, where N is the number of possible values. That's just Cauchy–Schwarz.

[step 4] Plug in: the distance is at most one half times √(2ᵐ⁻ᵏ). Ask for that to be at most ε, and
you get m = k − 2 log₂(1/ε).

[chart] For our block, k is 15,740. Every extra output bit costs half a bit of security. We keep
15,536 bits, which gives ε of about 2⁻¹⁰². And because the bound covers the pair (T, T·X), it holds
even if the seed is public.

---

## Slide 15 — How many bits can we keep? The Leftover Hash Lemma · 1.5 min

Let's put concrete numbers on it. [cards] We hash blocks of 16,384 raw bits. At 0.9607 bits of
min-entropy per bit, each block holds about 15,740 bits of genuine randomness. We ask for
ε = 2⁻¹⁰⁰, which costs 200 bits, and we keep 15,536 bits per block: 94.8 percent of the input.

[chart] The general picture: the kept fraction is almost exactly the min-entropy, minus a small
fixed cost. That fixed cost matters less for larger blocks, which is why the solid line for
16,384-bit blocks hugs the ideal.

[bullets] Two practical notes. Toeplitz hashing is a *strong* extractor, so the seed can be public
and reused for every block; ours is 31,919 bits drawn once from the operating system. And
everything depends on the entropy estimate: estimate too high, and the guarantee silently breaks.
Estimate first, then extract.

---

## Slide 16 — Fast Toeplitz hashing with the FFT, and its effect · 2 min

Multiplying a 16,384-bit block by a 15,536 × 16,384 matrix directly would be about 250 million
operations per block. But a Toeplitz product is a convolution, so we do it with the fast Fourier
transform in n log n time. [code] Transform the seed once, transform a batch of blocks, multiply,
transform back, round to integers, and keep the parity. The assert guards against floating-point
rounding, and a unit test checks the result against the explicit matrix product.

That runs at about 5 million bits per second in plain NumPy, faster than the simulator produces
them, so extraction is never the bottleneck.

[chart and cards] And the effect: overall, from 48.69 to 50.002 percent ones. Per bit position,
every orange bar sat 0.5 to 2.7 points below 50 percent; every green bar is now inside the ±3σ band
you'd expect from a fair coin.

---

## Slide 17 — Seeing the bias: three pictures before and after · 2 min

Before the formal tests, three quick pictures; they're a good sanity check.

[top left] The bias map: each row is a block of 10,000 shots, each column is a bit position, and
colour is the deviation from 50 percent. The raw bits show vertical stripes: the qubits that read 1
as 0. Every ten rows the pattern shifts, because the read-out order is reshuffled for each
circuit. After extraction, it's just noise.

[top right] Byte-pair heat maps: count how often each pair of consecutive bytes appears, with bytes
sorted by how many ones they contain. The raw bits show a clear gradient towards zero-heavy bytes.
The control and the extracted bits are flat.

[bottom right] Autocorrelation, the usual go-to check. Raw and extracted bits look exactly the same:
everything inside the ±3σ band. That's not a coincidence: autocorrelation subtracts the mean first,
so it's blind to bias. A clean autocorrelation plot does not mean clean bits.

---

## Slide 18 — A statistical test can reject randomness, never prove it · 2 min

Now the test suites. First, what a statistical test actually does.

Every randomness test is a hypothesis test. The null hypothesis is that the bits are independent
and fair. The test computes a statistic, and the p-value is the probability of seeing something at
least that extreme if the null hypothesis were true. We reject when p is below 0.01.

Two consequences. First, if the bits really are random, p-values are uniformly distributed. So even
perfect bits fail 1 percent of tests, and a single failure means nothing. That's why we judge many
sequences. [histograms] Here are 100 sequences of a million bits for two tests. The control and the
extracted bits give flat histograms. The noisy source puts all 100 p-values in the first bin: 0 out
of 100 pass.

Second, a pass only means "this test found nothing". A good pseudo-random generator passes
everything. So tests can reject a bad source, but they can never certify that bits are quantum.

---

## Slide 19 — NIST SP 800-22: 15 tests, 188 sub-tests · 1.5 min

The first suite is NIST Special Publication 800-22, the US government's statistical test suite for
random bit generators. [table] It has fifteen tests, and with the template and excursion variants
that becomes 188 sub-tests.

Grouped by what they look for: overall and local frequency of ones; oscillation, meaning runs of
identical bits; linear structure, through matrix ranks and the Fourier spectrum; specific bit
patterns, including 148 nine-bit templates; compressibility; linear complexity in short blocks; and
random-walk excursions.

[cards] The standard protocol is 100 sequences of a million bits, judged at α = 0.01. We run the
official NIST C code, not a re-implementation, driven automatically from Python.

---

## Slide 20 — Running NIST properly: many sequences, two criteria · 2 min

One sequence gives one p-value per test, and a perfect generator fails about one in a hundred. So
NIST judges each sub-test over all 100 sequences, with two criteria.

[left chart] Proportion: at least 0.99 minus three standard deviations of the sequences must pass.
For 100 sequences that's 96. [middle chart] Here's every sub-test for three datasets: the control
and the extracted bits sit at the top, the noisy source is scattered all the way down to zero.

Uniformity: the 100 p-values themselves must be spread evenly across 0 to 1, checked with a
chi-square test.

And one subtlety that's easy to get wrong. [right card] There are 148 template sub-tests, so even a
perfect source is expected to fail one or two of them by chance. We work out the binomial allowance:
up to three failures out of 148 is fine. So "147 out of 148" is a pass, not a problem.

---

## Slide 21 — NIST results: bias fails everywhere, extraction fixes it · 2 min

[grid] For each test family and dataset, the number of sub-tests passed. Green passes, amber is
within chance, red fails.

The control passes everything, which tells us the harness itself works. All the simulator datasets
pass; their single template misses are within chance. The noisy source fails 10 of the 13 families
that could run: everything sensitive to bias. Two random-excursion families couldn't run at all,
because they need the random walk to return to zero at least 500 times, and a walk that drifts by
26,000 steps hardly ever comes back. Rank, spectral and linear complexity still pass: bias doesn't
create linear structure or periodicity. After Toeplitz extraction, everything passes again.

[bottom right] And notice: NIST's own linear-complexity test passes the simulator that we know is a
Mersenne Twister. Its blocks are 500 bits long, far too short to see a 19,937-bit structure.

---

## Slide 22 — TestU01: a tougher library, adapted to finite files · 2 min

Three of our five suites come from TestU01, written by Pierre L'Ecuyer and Richard Simard in 2007.
It's the most demanding standard library for random number generators.

[table] Its famous batteries, SmallCrush, Crush and BigCrush, ask the generator for billions of
numbers. We measured SmallCrush alone at 7.3 billion bits, far more than any QRNG experiment
produces. But Rabbit and Alphabit were designed for exactly our case: a fixed file of bits from a
physical generator. And LinearComp is a single test, which we took from BigCrush.

[code] We wrote a small C harness. It reads the whole file into memory, feeds it to TestU01 32 bits
at a time, and if a test asks for more data than we have, it stops with an explicit "exhausted"
error rather than silently starting again from the beginning.

[chart] One of the things Rabbit looks at is the random walk: add +1 for each one and −1 for each
zero. Fair bits stay inside the ±3√n envelope. With 1.3 percent bias, the walk drifts steadily away:
26,000 steps below zero after a million bits.

---

## Slide 23 — LinearComp: catching a linear generator · 2 min

LinearComp is the test that matters most for simulators. It runs Berlekamp–Massey over sequences
of 400,020 bits, taken from one bit position of each 32-bit word, positions 0 and 29, as in
BigCrush. It looks at how the linear complexity jumps as each new bit arrives. For random bits, the
number of jumps and their sizes follow known distributions.

[table] The Mersenne Twister is linear over GF(2). So on the 100k-shot simulator data, the
complexity stops jumping at 19,937, and the jump-count p-value is exactly 1.000, on both bit
positions. A clear failure, and it's the only test in this entire study that detects the simulator.

[cards] It doesn't catch the 5k-shot simulator, because Aer re-seeds its generator for every
circuit, and no 5,000-shot segment is long enough to reveal a 19,937-bit recurrence. And it doesn't
catch the noisy data, because the noise is drawn by comparing random numbers with a threshold, and
that comparison isn't linear.

But note: both of those datasets are still completely determined by their seed. Passing LinearComp
doesn't make them random.

---

## Slide 24 — TestU01 results: every p-value, all six datasets · 1.5 min

Every dot on this slide is one p-value, for each battery and dataset. Values extremely close to 0 or
1 are flagged as failures.

[left and middle panels] For the control, the simulator datasets and the extracted bits, the
p-values spread evenly from 0 to 1, which is exactly what random data should do. The noisy source
collapses to zero in the Hamming-weight, random-walk and multinomial tests: only 14 of 38 Rabbit
results and 2 of 17 Alphabit results survive.

[right panel] In LinearComp the only failures in the entire table are the two red crosses at
p = 1.0, for the 100k-shot simulator.

---

## Slide 25 — Dieharder: Marsaglia's classic tests, extended · 2.5 min

Our fifth suite is Dieharder, Robert Brown's extension of George Marsaglia's 1995 Diehard battery.
Many of its tests are small simulations whose answer is known for true randomness.

[parking lot] The easiest to picture is the parking lot. Use the random numbers as coordinates and
try to park cars one at a time; a car that would touch an already-parked car crashes. For truly
random coordinates, the number of cars that manage to park is known: in Diehard's version, about
3,523 out of 12,000 attempts. What you see here is a small version, run on our real control bits.
Others include birthday spacings, overlapping permutations, matrix ranks, 3D spheres and the game
of craps.

[middle] There's one practical trap. When Dieharder reads from a file and runs out of data, it
silently goes back to the beginning and reuses the same bits, which makes good data fail for the
wrong reason. Run the full battery on a 1-gigabyte control file, and it had re-read the file 89 times
before we stopped it. So we ran each test on its own, with as much data as our file supports
without ever re-reading: 19 tests and 49 results per dataset.

[table] The control and every simulator dataset pass, with a few "weak" results, about what chance
predicts. The noisy source fails 22 of 49. After Toeplitz extraction, it passes.

---

## Slide 26 — The pipeline as software: one command, fully reproducible · 1.5 min

Everything in this talk comes from one Python package. [diagram] generate and noise produce the bits;
entropy and lincomp analyse them; extractor cleans them; three drivers run the official NIST code,
our TestU01 harness and Dieharder; and pipeline ties it all together into one summary table, with
every p-value saved as JSON. A separate figures module draws every chart in this deck from those
results.

[command] One command runs the whole study: six datasets at a hundred million bits, all five suites,
in about 12 minutes on a 22-core machine.

It's reproducible: seeds are recorded, the output doesn't depend on the number of workers, 20 unit
tests check the mathematics, for example that the FFT extractor matches the explicit matrix, and a
GitHub Actions workflow can re-run everything on Linux.

---

## Slide 27 — Scoreboard: six datasets against every tool · 1.5 min

Here's everything on one slide. Green passes, orange fails. Read it row by row.

The control passes everything, which shows the harness is sound. The 5k-shot simulator passes
everything too, even though it's a formula. The 100k-shot simulator fails in exactly two places, and
they agree: our own linear-complexity diagnostic shows 19,937, and TestU01's LinearComp gives 2 out
of 4. The symmetric-noise simulator passes everything, as the algebra predicted. The realistic noisy
source fails its entropy estimate, NIST, Rabbit, Alphabit and Dieharder; only LinearComp passes. And
after Toeplitz extraction those same bits pass everything again.

---

## Slide 28 — No single tool catches every flaw · 1.5 min

Turn the scoreboard around and ask: which tool caught which flaw?

[table] Bias is easy: almost everything catches it, except LinearComp and autocorrelation. The linear
structure of the Mersenne Twister is caught by exactly one suite, LinearComp; NIST, Rabbit, Alphabit
and Dieharder all miss it. And the 5k-shot simulator, which is just as deterministic, is caught by
nothing at all.

[bottom] Three lessons. One: run several independent suites; any single suite would have missed
something here. Two: a pass is not proof; the re-seeded simulator passes all five suites and is still
completely predictable from its seed. Three: estimate, then extract. Raw device bits fail, and
extraction sized by min-entropy fixes them at a cost of about 5 percent of the bits.

---

## Slide 29 — Conclusion · 1.5 min + questions

To close, four numbers. [left column] Realistic read-out noise gives 48.7 percent ones, and every
bias test rejects it. Min-entropy estimation measured 0.961 bits of genuine randomness per raw bit.
Toeplitz extraction kept 94.8 percent of the bits and restored a clean pass on every suite. And only
one test in the whole study noticed that the simulator's randomness is a Mersenne Twister.

So passing statistical tests is necessary, but not sufficient. Where the bits come from, and how they
are extracted, matter just as much as the tests.

The natural next step is to replace the simulator with real quantum hardware and run exactly this
pipeline on those bits.

The references are on the right. Thank you; we're happy to take questions.
