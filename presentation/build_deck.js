// Builds presentation/QRNG_Testing_Lecture.pptx from figures/ and results/.
//
//   NODE_PATH=<dir with pptxgenjs> node presentation/build_deck.js
//
// Figures come from `python -m hqrng.figures`; numbers from figures/data.json,
// results/full/summary.json and (if present) results/dieharder/summary.json.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const FIG = path.join(ROOT, "figures");
const OUT = path.join(__dirname, "QRNG_Testing_Lecture.pptx");
const DATA = JSON.parse(fs.readFileSync(path.join(FIG, "data.json"), "utf8"));
const SIZES = JSON.parse(fs.readFileSync(path.join(FIG, "sizes.json"), "utf8"));
const RESULTS = JSON.parse(fs.readFileSync(path.join(ROOT, "results/full/summary.json"), "utf8"));
const DH_PATH = path.join(ROOT, "results/dieharder/summary.json");
const DH = fs.existsSync(DH_PATH) ? JSON.parse(fs.readFileSync(DH_PATH, "utf8")) : null;

// ---- theme --------------------------------------------------------------------
const THEME = {
  name: "QRNG Purple",
  headFontFace: "Poppins",
  bodyFontFace: "Poppins",
  colors: {
    dk1: "111111", lt1: "FFFFFF", dk2: "2E1065", lt2: "F5F3FF",
    accent1: "6D28D9", accent2: "A78BFA", accent3: "C2410C", accent4: "0F766E",
    accent5: "6B7280", accent6: "4C1D95", hlink: "6D28D9", folHlink: "4C1D95",
  },
};
const INK = "111111", PURPLE = "6D28D9", DEEP = "2E1065", LAV = "EDE9FE", LAV2 = "F5F3FF",
  MID = "A78BFA", GRAY = "6B7280", ORANGE = "C2410C", TEAL = "0F766E", LINE = "DDD6FE",
  PASS_BG = "E6F4F1", FAIL_BG = "FCE9DF", NA_BG = "F3F4F6";
const FONT = "Poppins", MONO = "Consolas";
const W = 13.333, H = 7.5, MX = 0.6, CW = W - 2 * MX;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Testing Quantum Random Number Generators";
pres.author = "Aradhya Mahajan, Amee Ghai";
pres.subject = "Entropy estimation, Toeplitz extraction and statistical test suites";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: "FFFFFF" },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.62, w: 11.2, h: 0.8,
        fontFace: FONT, fontSize: 26, bold: true, color: INK, valign: "top", align: "left", margin: 0 }, text: "" } },
    { text: { text: "Testing Quantum Random Number Generators  ·  Aradhya Mahajan & Amee Ghai", options: {
        x: MX, y: 7.02, w: 9, h: 0.3, fontFace: FONT, fontSize: 9, color: GRAY, margin: 0 } } },
  ],
  slideNumber: { x: 12.13, y: 7.02, w: 0.6, h: 0.3, fontFace: FONT, fontSize: 9, color: GRAY, align: "right" },
});
pres.defineSlideMaster({ title: "BLANK", background: { color: "FFFFFF" }, objects: [] });

// ---- helpers ------------------------------------------------------------------
let slideNo = 0;

function bitPattern(seed, n) {
  let s = (seed * 2654435761) >>> 0;
  const out = [];
  for (let i = 0; i < n; i++) {
    s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0;
    out.push(s & 1);
  }
  return out;
}

function motif(slide, seed) {
  // the deck's motif: a small block of "bits" in the top-right corner
  const bits = bitPattern(seed + 7, 16), sz = 0.12, gap = 0.045;
  const x0 = W - MX - 8 * sz - 7 * gap;
  bits.forEach((b, i) => {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: x0 + (i % 8) * (sz + gap), y: 0.3 + Math.floor(i / 8) * (sz + gap), w: sz, h: sz,
      fill: { color: b ? PURPLE : LAV }, line: { color: b ? PURPLE : LAV, width: 0 },
      objectName: "bit motif",
    });
  });
}

function content(section, chip, title, notes) {
  slideNo++;
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(chip.toUpperCase(), {
    shape: pres.shapes.ROUNDED_RECTANGLE, x: MX, y: 0.26, w: Math.max(1.6, 0.095 * chip.length + 0.5), h: 0.27,
    rectRadius: 0.13, fill: { color: LAV }, line: { color: LAV, width: 0 }, fontFace: FONT, fontSize: 9,
    bold: true, color: PURPLE, align: "center", valign: "middle", margin: 0, charSpacing: 1,
    objectName: "section chip",
  });
  motif(s, slideNo);
  s.addText(title, { placeholder: "title" });
  if (notes) s.addNotes(notes);
  return s;
}

// "**bold**" → purple bold run; "__x__" → bold ink run
function md(text, base = {}) {
  const runs = [];
  const re = /(\*\*[^*]+\*\*|__[^_]+__)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) runs.push({ text: text.slice(last, m.index), options: { ...base } });
    const t = m[0];
    if (t.startsWith("**")) runs.push({ text: t.slice(2, -2), options: { ...base, bold: true, color: PURPLE } });
    else runs.push({ text: t.slice(2, -2), options: { ...base, bold: true } });
    last = m.index + t.length;
  }
  if (last < text.length) runs.push({ text: text.slice(last), options: { ...base } });
  // explicit line breaks: split runs at "\n" so a styled run after a break stays on its own line correctly
  const out = [];
  runs.forEach((r) => {
    const parts = r.text.split("\n");
    parts.forEach((t, i) => out.push({ text: t, options: { ...r.options, ...(i < parts.length - 1 ? { breakLine: true } : {}) } }));
  });
  return out.filter((r) => r.text.length || r.options.breakLine);
}

// items: strings, or {t: string, sub: true} for an indented item, or {h: string} for a small heading
function bullets(slide, items, box, o = {}) {
  const fs_ = o.fontSize || 13;
  const runs = [];
  items.forEach((it, i) => {
    const last = i === items.length - 1;
    let r;
    if (typeof it === "object" && it.h) {
      r = md(it.h, { fontSize: fs_ - 1, bold: true, color: PURPLE });
      r[0].options.paraSpaceBefore = i ? 6 : 0;
    } else {
      const sub = typeof it === "object" && it.sub;
      const txt = typeof it === "object" ? it.t : it;
      r = md(txt, { fontSize: sub ? fs_ - 1 : fs_, color: INK });
      r[0].options.bullet = sub ? { indent: 14, characterCode: "2013" } : { indent: 14 };
      if (sub) r[0].options.indentLevel = 1;
    }
    r[0].options.paraSpaceAfter = o.space ?? 5;
    if (!last) r[r.length - 1].options.breakLine = true;
    runs.push(...r);
  });
  slide.addText(runs, { x: box.x, y: box.y, w: box.w, h: box.h, fontFace: FONT, valign: o.valign || "top",
    margin: o.margin ?? 0.02, isTextBox: true, lineSpacingMultiple: 1.05, objectName: o.name || "bullets" });
}

function para(slide, text, box, o = {}) {
  slide.addText(md(text, { fontSize: o.fontSize || 13, color: o.color || INK, bold: o.bold, italic: o.italic }), {
    x: box.x, y: box.y, w: box.w, h: box.h, fontFace: FONT, valign: o.valign || "top", align: o.align || "left",
    margin: o.margin ?? 0.02, isTextBox: true, lineSpacingMultiple: 1.05, objectName: o.name || "text",
  });
}

function img(slide, file, box, o = {}) {
  const [pw, ph] = SIZES[file];
  const r = pw / ph;
  let w = box.w, h = box.w / r;
  if (h > box.h) { h = box.h; w = h * r; }
  const ax = o.align || "center", ay = o.valign || "top";
  const x = box.x + (ax === "left" ? 0 : ax === "right" ? box.w - w : (box.w - w) / 2);
  const y = box.y + (ay === "top" ? 0 : ay === "bottom" ? box.h - h : (box.h - h) / 2);
  slide.addImage({ path: path.join(FIG, file), x, y, w, h, altText: o.alt || file, objectName: file });
  return { x, y, w, h };
}

function card(slide, { x, y, w, h, head, big, body, color = PURPLE, fill = LAV2, bigSize = 26, bodySize = 11.5 }) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill },
    line: { color: fill, width: 0 }, objectName: "card" });
  let cy = y + 0.12;
  if (head) {
    slide.addText(head, { x: x + 0.16, y: cy, w: w - 0.32, h: 0.28, fontFace: FONT, fontSize: 10, bold: true,
      color, margin: 0, isTextBox: true, charSpacing: 0.5 });
    cy += 0.3;
  }
  if (big) {
    const bh = bigSize / 72 * 1.35;
    slide.addText(big, { x: x + 0.16, y: cy, w: w - 0.32, h: bh, fontFace: FONT, fontSize: bigSize, bold: true,
      color: INK, margin: 0, isTextBox: true, valign: "top" });
    cy += bh + 0.02;
  }
  if (body) {
    slide.addText(md(body, { fontSize: bodySize, color: INK }), { x: x + 0.16, y: cy, w: w - 0.32,
      h: Math.max(0.3, y + h - cy - 0.08), fontFace: FONT, margin: 0, isTextBox: true, valign: "top",
      lineSpacingMultiple: 1.05 });
  }
}

function code(slide, text, box, fontSize = 10.5) {
  slide.addText(text, { x: box.x, y: box.y, w: box.w, h: box.h, fontFace: MONO, fontSize, color: DEEP,
    fill: { color: LAV2 }, margin: [8, 10, 8, 10], valign: "top", isTextBox: true, objectName: "code",
    lineSpacingMultiple: 1.0 });
}

function caption(slide, text, box) {
  para(slide, text, box, { fontSize: 10, color: GRAY });
}

function arrow(slide, x1, y1, x2, y2, color = MID) {
  slide.addShape(pres.shapes.LINE, { x: x1, y: y1, w: x2 - x1, h: y2 - y1,
    line: { color, width: 1.75, endArrowType: "triangle" }, objectName: "arrow" });
}

const cell = (text, o = {}) => ({ text, options: { fontFace: FONT, fontSize: o.fontSize || 11, color: o.color || INK,
  bold: !!o.bold, align: o.align || "left", valign: "middle", fill: { color: o.fill || "FFFFFF" },
  margin: o.margin || [3, 6, 3, 6] } });
const hcell = (text, o = {}) => cell(text, { ...o, bold: true, color: "FFFFFF", fill: PURPLE });
const TB = { type: "solid", pt: 0.75, color: LINE };

const fmtP = (p) => (p >= 0.9995 ? "1.000" : p < 0.001 ? p.toExponential(1) : p.toFixed(3));
const R = (name) => RESULTS.find((r) => r.dataset === name);
const SB = (name) => DATA.scoreboard.find((r) => r.dataset === name);
const NAMES = {
  urandom: "Control (OS random)", aer_D_5k: "Simulator, 5k shots/run", aer_D_ideal: "Simulator, 100k shots/run",
  aer_D_sym2pct: "Simulator, 2% symmetric noise", aer_D_ibmlike: "Simulator, uneven read-out noise",
  aer_D_ibmlike_toeplitz: "Same noisy bits after Toeplitz",
};
const ORDER = Object.keys(NAMES);

// =================================================================================
// 1. Title
// =================================================================================
pres.addSection({ title: "A. Problem and test source" });
{
  slideNo++;
  const s = pres.addSlide({ masterName: "BLANK", sectionTitle: "A. Problem and test source" });
  // big bit field on the right
  const cols = 14, rows = 17, sz = 0.3, gap = 0.08, x0 = W - 0.55 - cols * (sz + gap) + gap, y0 = 0.56;
  const bits = bitPattern(2026, cols * rows);
  bits.forEach((b, i) => {
    const r = Math.floor(i / cols), c = i % cols;
    const col = b ? (c < 4 ? MID : PURPLE) : LAV;   // softer towards the text
    s.addShape(pres.shapes.RECTANGLE, { x: x0 + c * (sz + gap), y: y0 + r * (sz + gap), w: sz, h: sz,
      fill: { color: col }, line: { color: col, width: 0 }, objectName: "bit field" });
  });
  s.addText("LECTURE  ·  QUANTUM RANDOMNESS", { shape: pres.shapes.ROUNDED_RECTANGLE, x: MX, y: 1.55, w: 3.6, h: 0.32,
    rectRadius: 0.16, fill: { color: LAV }, line: { color: LAV, width: 0 }, fontFace: FONT, fontSize: 10, bold: true,
    color: PURPLE, align: "center", valign: "middle", margin: 0, charSpacing: 1 });
  s.addText("Testing Quantum Random Number Generators", { x: MX, y: 2.05, w: 6.6, h: 1.9, fontFace: FONT,
    fontSize: 40, bold: true, color: INK, margin: 0, valign: "top", isTextBox: true });
  s.addText("Entropy estimation, Toeplitz extraction and five statistical test suites", { x: MX, y: 4.05, w: 6.4,
    h: 0.8, fontFace: FONT, fontSize: 17, color: INK, margin: 0, isTextBox: true });
  s.addText([
    { text: "NIST SP 800-22", options: { bold: true, color: PURPLE } }, { text: "  ·  ", options: { color: GRAY } },
    { text: "Rabbit", options: { bold: true, color: PURPLE } }, { text: "  ·  ", options: { color: GRAY } },
    { text: "Alphabit", options: { bold: true, color: PURPLE } }, { text: "  ·  ", options: { color: GRAY } },
    { text: "LinearComp", options: { bold: true, color: PURPLE } }, { text: "  ·  ", options: { color: GRAY } },
    { text: "Dieharder", options: { bold: true, color: PURPLE } },
  ], { x: MX, y: 5.0, w: 7.2, h: 0.4, fontFace: FONT, fontSize: 13, margin: 0, isTextBox: true });
  s.addText("Aradhya Mahajan (B23CS1088)  ·  Amee Ghai (B23PH1003)", { x: MX, y: 5.95, w: 6.8, h: 0.4, fontFace: FONT, fontSize: 13, bold: true,
    color: INK, margin: 0, isTextBox: true });
  s.addText("IIT Jodhpur  ·  November 2026", { x: MX, y: 6.4, w: 6, h: 0.35, fontFace: FONT, fontSize: 11,
    color: GRAY, margin: 0, isTextBox: true });
  s.addNotes("Welcome. This lecture is about one question: how do you know that a random number generator, and in particular a quantum one, is actually producing good random bits? We will build a complete testing pipeline: generate bits from a quantum circuit, estimate how much real randomness they contain, clean them with a Toeplitz extractor, and run them through five standard test suites. Every chart in this talk comes from our own code and data.");
}

// =================================================================================
// 2. Why randomness quality matters
// =================================================================================
{
  const s = content("A. Problem and test source", "A · Motivation", "Weak randomness breaks real systems",
    "Random numbers protect keys, nonces and signatures. Two real incidents show what happens when they are weak: Debian's OpenSSL (2006-2008) seeded its generator with only the process ID, so there were only 32,768 possible keys per key type; and Sony's PS3 firmware signed code with ECDSA using the same 'random' nonce every time, which let attackers compute the private key. On the right: the three families of generators. A PRNG is a formula and is predictable by anyone with the seed; a classical TRNG measures physical noise that is unpredictable only because we lack information; a QRNG measures a quantum outcome that is undetermined until it is measured.");
  para(s, "Keys, nonces and simulations assume the random bits **cannot be guessed**. When they can, nothing crashes: the system is silently broken.",
    { x: MX, y: 1.5, w: 5.6, h: 1.05 }, { fontSize: 14 });
  card(s, { x: MX, y: 2.75, w: 5.6, h: 1.75, head: "DEBIAN OPENSSL · 2008", big: "32,768 keys",
    body: "were all that was possible: the generator was seeded only with the process ID", bodySize: 12 });
  card(s, { x: MX, y: 4.7, w: 5.6, h: 1.75, head: "SONY PS3 · 2010", big: "1 nonce",
    body: "reused for every signature, so the private signing key could be computed", bodySize: 12 });
  const rows = [
    [hcell(""), hcell("PRNG"), hcell("Classical TRNG"), hcell("Quantum RNG")],
    [cell("Source", { bold: true, fontSize: 12 }), cell("Formula + seed", { fontSize: 12 }), cell("Thermal noise", { fontSize: 12 }), cell("Quantum measurement", { fontSize: 12 })],
    [cell("Predictable by", { bold: true, fontSize: 12 }), cell("Anyone with the seed", { fontSize: 12 }), cell("A better model", { fontSize: 12 }), cell("Nobody", { fontSize: 12, bold: true, color: PURPLE })],
    [cell("Example", { bold: true, fontSize: 12 }), cell("Mersenne Twister", { fontSize: 12 }), cell("Ring oscillators", { fontSize: 12 }), cell("Qubits, photons", { fontSize: 12 })],
  ];
  s.addTable(rows, { x: 6.55, y: 1.55, w: 6.18, colW: [1.5, 1.5, 1.5, 1.68], border: TB, rowH: 0.75 });
  caption(s, "Every generator needs testing; only the quantum one is unpredictable in principle.", { x: 6.55, y: 4.75, w: 6.18, h: 0.4 });
}

// =================================================================================
// 3. Pipeline
// =================================================================================
{
  const s = content("A. Problem and test source", "A · Approach", "From a quantum source to a verdict",
    "This is the roadmap for the rest of the talk. A quantum source produces raw bits. Before using them we estimate their min-entropy: how much genuine unpredictability each bit carries. That number sizes a Toeplitz extractor, which compresses the raw bits into nearly uniform output. Then three independent statistical suites look for any pattern at all. We run this on six datasets of 100 million bits each.");
  const steps = [
    ["Quantum source", "32-qubit circuit"], ["Raw bits", "in shot order"],
    ["Entropy estimate", "how random?"], ["Toeplitz extractor", "make uniform"],
    ["Test suites", "find patterns"], ["Verdict", "reject or pass"],
  ];
  const gap = 0.3, bw = (CW - 5 * gap) / 6, y = 1.85;
  steps.forEach(([t, sub], i) => {
    const x = MX + i * (bw + gap);
    const strong = i === 3 || i === 4;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: bw, h: 1.55, rectRadius: 0.1,
      fill: { color: strong ? PURPLE : LAV2 }, line: { color: strong ? PURPLE : LINE, width: 1 } });
    s.addText(t, { x: x + 0.08, y: y + 0.25, w: bw - 0.16, h: 0.65, fontFace: FONT, fontSize: 14, bold: true,
      color: strong ? "FFFFFF" : INK, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(sub, { x: x + 0.08, y: y + 0.95, w: bw - 0.16, h: 0.4, fontFace: FONT, fontSize: 12,
      color: strong ? "FFFFFF" : GRAY, align: "center", margin: 0, isTextBox: true });
    if (i < steps.length - 1) arrow(s, x + bw + 0.04, y + 0.775, x + bw + gap - 0.04, y + 0.775, PURPLE);
  });
  card(s, { x: MX, y: 4.35, w: 3.9, h: 1.6, head: "DATASETS", big: "6", body: "a control, four simulator set-ups, one extracted" });
  card(s, { x: MX + 4.11, y: 4.35, w: 3.9, h: 1.6, head: "PER DATASET", big: "10⁸ bits", body: "the size NIST's protocol asks for" });
  card(s, { x: MX + 8.22, y: 4.35, w: 3.91, h: 1.6, head: "TEST SUITES", big: "5", body: "NIST SP 800-22, Rabbit, Alphabit, LinearComp, Dieharder" });
}

// =================================================================================
// 4. Circuit variants
// =================================================================================
{
  const s = content("A. Problem and test source", "A · Test source", "Four circuit variants, one identical distribution",
    "Our test source is a 32-qubit circuit. Seed bits set X gates, every qubit gets a Hadamard, variants B and D add a random layer of CNOTs, and C and D shuffle which qubit is written to which classical bit. A statevector simulation of all four variants (20 random circuits each) shows two things: the state is exactly uniform, and there is no entanglement at all. The reason: a CNOT acting on a product of plus and minus states only maps it to another product of plus and minus states. For contrast, a Bell pair carries one full bit of entanglement. So on a simulator the four variants are statistically identical; on hardware they would differ, because every CNOT adds two-qubit gate error.");
  img(s, "fig01_circuits.png", { x: MX, y: 1.5, w: 5.9, h: 4.35 }, { align: "left", alt: "Circuit diagrams of variants A to D, 6 qubits each" });
  caption(s, "Variants A–D drawn with 6 qubits (we run 32). X = seed bit, H = Hadamard.", { x: MX, y: 5.95, w: 5.9, h: 0.4 });
  bullets(s, [
    "**X → H** on every qubit; B, D add **CNOTs**; C, D **shuffle the read-out**",
    "All four give an **exactly uniform**, **unentangled** state",
    "So on a simulator the variants are **identical**",
  ], { x: 6.85, y: 1.6, w: 5.88, h: 1.85 }, { fontSize: 15, space: 12 });
  img(s, "fig02_variants_uniform.png", { x: 6.85, y: 3.55, w: 5.88, h: 2.9 }, { alt: "Entanglement and deviation from uniform per variant" });
}

// =================================================================================
// 5. Generating bits at scale
// =================================================================================
{
  const s = content("A. Problem and test source", "A · Data", "Generating 10⁸ bits per dataset, reproducibly",
    "Each circuit is simulated with memory=True, which keeps the shots in the order they were produced; get_counts would group identical outcomes and destroy time order. Every circuit gets its own child of one SeedSequence, so the output is bit-identical no matter how many worker processes run it. Bits are written packed, most significant bit first. We built six datasets of 100 million bits; the control is the operating system's cryptographic generator. Throughput peaks around 3.3 Mbit/s with 8 workers; beyond that, process start-up and memory bandwidth dominate.");
  code(s, [
    "rng  = np.random.default_rng(SeedSequence(seed, spawn_key=(i,)))",
    "qc   = build_circuit(\"D\", n_qubits=32, rng=rng)",
    "sim  = AerSimulator(noise_model=noise_model(spec, 32))",
    "mem  = sim.run(qc, shots=100_000, memory=True,      # keep shot order",
    "               seed_simulator=seed_i).result().get_memory()",
    "bits = np.frombuffer(\"\".join(mem).encode(), np.uint8) - ord(\"0\")",
    "out.write(np.packbits(bits).tobytes())              # MSB-first",
  ].join("\n"), { x: MX, y: 1.5, w: 6.3, h: 1.85 }, 10.5);
  const tp = DATA.throughput;
  s.addChart(pres.charts.BAR, [{ name: "Mbit/s", labels: tp.workers.map(String), values: tp.mbit_per_s.map((v) => +v.toFixed(2)) }], {
    x: MX, y: 3.55, w: 6.3, h: 3.0, barDir: "col", chartColors: [PURPLE], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.0", dataLabelFontFace: FONT, dataLabelFontSize: 10, dataLabelColor: INK,
    showTitle: true, title: "Generation speed vs worker processes (Mbit/s)", titleFontFace: FONT, titleFontSize: 11, titleColor: INK,
    catAxisLabelFontFace: FONT, catAxisLabelFontSize: 10, catAxisLabelColor: GRAY, valAxisLabelFontFace: FONT,
    valAxisLabelFontSize: 9, valAxisLabelColor: GRAY, valGridLine: { color: "ECE9F5", size: 0.5 },
    catGridLine: { style: "none" }, showLegend: false, valAxisMinVal: 0, catAxisTitle: "workers", showCatAxisTitle: true,
    catAxisTitleFontSize: 10, catAxisTitleColor: GRAY, catAxisTitleFontFace: FONT,
  });
  const rows = [[hcell("Dataset"), hcell("What it is"), hcell("Ones %", { align: "right" })]];
  const what = {
    urandom: "OS cryptographic generator", aer_D_5k: "Variant D, 5,000 shots per circuit",
    aer_D_ideal: "Variant D, 100,000 shots per circuit", aer_D_sym2pct: "+ 2% symmetric bit flips",
    aer_D_ibmlike: "+ uneven per-qubit read-out error", aer_D_ibmlike_toeplitz: "Noisy bits, Toeplitz-extracted",
  };
  ORDER.forEach((d) => rows.push([cell(NAMES[d].replace("Simulator, ", "Sim, "), { bold: true, fontSize: 10.5 }),
    cell(what[d], { fontSize: 10.5 }),
    cell(SB(d).ones_percent.toFixed(3), { align: "right", fontSize: 10.5, color: d === "aer_D_ibmlike" ? ORANGE : INK, bold: d === "aer_D_ibmlike" })]));
  s.addTable(rows, { x: 7.15, y: 1.5, w: 5.58, colW: [2.15, 2.53, 0.9], border: TB, rowH: 0.7 });
}

// =================================================================================
// 6. Noise and bias (merged with read-out profile)
// =================================================================================
pres.addSection({ title: "B. Noise and pitfalls" });
{
  const rb = DATA.readout_ibm_like;
  const s = content("B. Noise and pitfalls", "B · Noise", "Only uneven read-out error can bias a fair qubit",
    "A fair bit XORed with an independent flip is still fair, at any flip rate: P(1) = 1/2 (1-p) + 1/2 p = 1/2. So a symmetric noise model can never make a simulated QRNG fail a bias test, however large the error rate. Real superconducting qubits are different: during read-out a qubit in state 1 can decay to 0, so P(read 0 | was 1) is several times larger than P(read 1 | was 0). Then P(1) = 1/2 (1 - P(0|1)) + 1/2 P(1|0), which is below one half. The dots are Aer simulations at six error rates, 1.28 million bits each; they sit on the formula. To make the simulator behave like a real chip, each of the 32 qubits gets its own read-out error, drawn from the range seen on IBM devices: 1 to 6 percent for reading a 1 as 0, and 0.2 to 1.5 percent the other way round. The bottom panel is the consequence: every qubit produces fewer than 50 percent ones, by up to 2.7 percentage points, and the average output is 48.69 percent ones. That is a small bias by eye, but at 10 to the 8 bits it is overwhelming statistical evidence.");
  img(s, "fig03_noise_bias.png", { x: MX, y: 1.5, w: 5.95, h: 3.7 }, { alt: "P(1) versus error rate for symmetric and uneven noise" });
  img(s, "fig04_readout_table.png", { x: 6.78, y: 1.5, w: 5.95, h: 3.7 }, { alt: "Per-qubit read-out error rates and resulting bias" });
  card(s, { x: MX, y: 5.35, w: 5.95, h: 1.2, head: "SYMMETRIC FLIP, ANY RATE", big: "P(1) = ½(1 − p) + ½p = ½", bigSize: 17 });
  card(s, { x: 6.78, y: 5.35, w: 5.95, h: 1.2, head: "UNEVEN READ-OUT (IBM-LIKE, 32 QUBITS)", big: `${(rb.mean_p1 * 100).toFixed(2)} % ones`, bigSize: 17, fill: "FDF2EC", color: ORANGE });
}

// =================================================================================
// 8. Simple metrics mislead
// =================================================================================
{
  const s = content("B. Noise and pitfalls", "B · Pitfalls", "Simple metrics measure the sample size, not the source",
    "Two common metrics look informative but are not. Left: if you count 32-bit outcomes, there are four billion possible values, so with N shots almost every outcome appears exactly once and both Shannon and min-entropy of the counts equal log2 N: 12.29 bits at 5,000 shots, for any good source. A single repeated outcome, which happens about 0.3 percent of the time at 5,000 shots, drops the min-entropy by a full bit. Right: the average absolute correlation between bit positions of independent bits is not zero but sqrt(2 / pi N), the sampling-noise floor. Measured values on our control sit exactly on that curve. Neither metric can tell a good source from a bad one; that is what entropy estimators and test suites are for.");
  img(s, "fig05_entropy_saturation.png", { x: MX, y: 1.5, w: 5.95, h: 3.9 }, { alt: "Entropy of counts versus number of shots" });
  img(s, "fig06_correlation_floor.png", { x: 6.78, y: 1.5, w: 5.95, h: 3.9 }, { alt: "Mean absolute correlation versus shots, and a correlation matrix" });
  para(s, "Entropy of 32-bit outcome counts is just **log₂N**: 12.29 bits at N = 5,000 for any good source.",
    { x: MX, y: 5.6, w: 5.95, h: 0.9 }, { fontSize: 13.5 });
  para(s, "Independent bits still correlate by **√(2/πN)**; our control sits exactly on that floor.",
    { x: 6.78, y: 5.6, w: 5.95, h: 0.9 }, { fontSize: 13.5 });
}

// =================================================================================
// 9. Hidden formula
// =================================================================================
{
  const s = content("B. Noise and pitfalls", "B · Pitfalls", "The simulator's randomness is a formula",
    "Qiskit Aer simulates X, H and CNOT circuits with its stabilizer method, and draws every random measurement outcome from a Mersenne Twister, MT19937. The same seed_simulator gives bit-identical output. Linear complexity makes this visible: it is the length of the shortest linear feedback shift register that reproduces a sequence, found by the Berlekamp-Massey algorithm. Random bits have linear complexity close to n over 2. For one bit position of Aer's output, the complexity grows like random data and then stops at exactly 19,937 - the size of the Mersenne Twister state - because every later bit is a linear function of the previous 19,937. The small example: a 4-bit LFSR has linear complexity 4 forever. Conclusion: simulation is good for building and validating the pipeline, but claims about quantum randomness need hardware.");
  img(s, "fig07_linear_complexity.png", { x: MX, y: 1.5, w: 7.3, h: 3.95 }, { align: "left", alt: "Linear complexity profile: random vs Aer" });
  card(s, { x: MX, y: 5.6, w: 7.3, h: 0.9, head: "CONSEQUENCE",
    body: "A simulator validates the **pipeline**, not the **physics**.", bodySize: 12.5 });
  img(s, "fig08_lfsr_example.png", { x: 8.2, y: 1.5, w: 4.53, h: 2.6 }, { alt: "4-bit LFSR example with linear complexity 4" });
  bullets(s, [
    "Aer draws every outcome from **MT19937**: same seed → same bits",
    "Linear complexity stops at **19,937** instead of growing as n/2",
  ], { x: 8.2, y: 4.35, w: 4.53, h: 2.2 }, { fontSize: 13.5, space: 10 });
}

// =================================================================================
// 10. Shannon vs min-entropy
// =================================================================================
pres.addSection({ title: "C. Entropy and extraction" });
{
  const e = DATA.entropy_example;
  const s = content("C. Entropy and extraction", "C · Entropy", "Min-entropy is the measure that matters for security",
    "Shannon entropy is the average surprise per bit. Min-entropy is minus log2 of the probability of the single most likely outcome: it says how well the best possible guesser does. Security definitions use min-entropy because an attacker will always guess the most likely value. The two diverge quickly with bias. For our noisy source, P(1) = 0.4869: Shannon entropy is 0.9995 bits per bit - almost perfect - while min-entropy is only 0.9626. If we sized the extractor with Shannon entropy we would keep about 4 percent too many bits.");
  img(s, "fig09_entropy_curves.png", { x: MX, y: 1.5, w: 7.2, h: 5.0 }, { align: "left", alt: "Shannon and min-entropy versus P(1)" });
  card(s, { x: 8.15, y: 1.5, w: 4.58, h: 1.45, head: "SHANNON", big: "H = −Σ pᵢ log₂ pᵢ", bigSize: 18, body: "average surprise per bit" });
  card(s, { x: 8.15, y: 3.1, w: 4.58, h: 1.45, head: "MIN-ENTROPY", big: "H∞ = −log₂ maxᵢ pᵢ", bigSize: 18, body: "the best single guess is right with probability maxᵢ pᵢ" });
  card(s, { x: 8.15, y: 4.7, w: 4.58, h: 1.8, head: `OUR NOISY SOURCE · P(1) = ${e.p1.toFixed(4)}`,
    body: `Shannon **${e.shannon.toFixed(4)}** vs min-entropy **${e.min_entropy.toFixed(4)}** bits per bit.\nSizing by Shannon would overstate the usable randomness by **${((e.shannon / e.min_entropy - 1) * 100).toFixed(1)} %**.`, bodySize: 11.5 });
}

// =================================================================================
// 11. Estimating min-entropy
// =================================================================================
{
  const s = content("C. Entropy and extraction", "C · Entropy", "Estimating min-entropy from data (SP 800-90B style)",
    "NIST SP 800-90B gives estimators for the min-entropy of a raw noise source. We implemented three. The most-common-value estimator takes the frequency of the most common symbol and its 99 percent upper confidence bound. The Markov estimator models dependence between consecutive bits and finds the most likely 128-bit sequence. And because each qubit can be biased differently, we also run the most-common-value estimator on each of the 32 bit positions and average. The final h_min is the lowest of the three. Every fair dataset gives 0.997 - the confidence bound costs about 0.003 - while the noisy source gives 0.961, which is what sizes the extractor.");
  img(s, "fig10_hmin_datasets.png", { x: MX, y: 1.5, w: 7.6, h: 3.55 }, { align: "left", alt: "Min-entropy estimates per dataset" });
  card(s, { x: 8.45, y: 1.5, w: 4.28, h: 1.6, head: "MOST COMMON VALUE",
    body: "p = share of the most common value\npᵤ = p + 2.576·√(p(1−p)/(L−1))\nH = −log₂ pᵤ  (99 % upper bound)", bodySize: 11.5 });
  card(s, { x: 8.45, y: 3.25, w: 4.28, h: 1.45, head: "MARKOV",
    body: "first-order transition probabilities; most likely 128-bit path, divided by 128", bodySize: 11.5 });
  card(s, { x: 8.45, y: 4.85, w: 4.28, h: 1.65, head: "PER BIT POSITION",
    body: "MCV on each of the 32 columns; catches **per-qubit** bias that a whole-stream estimate averages away", bodySize: 11.5 });
  bullets(s, [
    "**h_min = min(MCV, Markov, per-position MCV)** — the cautious choice",
    "Fair datasets: **0.997** (the 99 % confidence bound costs 0.003 at 10⁸ bits). Noisy source: **0.961**",
  ], { x: MX, y: 5.25, w: 7.6, h: 1.3 }, { fontSize: 12 });
}

// =================================================================================
// 12. Why extract; XOR
// =================================================================================
{
  const pu = DATA.piling_up;
  const s = content("C. Entropy and extraction", "C · Extraction", "Extraction: XOR shrinks bias geometrically",
    "Raw physical bits are almost never perfectly fair, and the test suites will rightly reject them. Randomness extraction turns many slightly biased bits into fewer, nearly uniform ones. The classic von Neumann trick reads pairs: 01 becomes 0, 10 becomes 1, 00 and 11 are dropped. It needs independent, identically distributed input and keeps at most a quarter of the bits. Hashing does better. The intuition is the piling-up lemma: XOR of k independent bits with bias epsilon has bias 2 to the k minus 1 times epsilon to the k. Our source starts at epsilon = 0.013; XOR of two bits is already at 0.00035, which we measured directly. Beyond k = 3 the bias is below what 64 million bits can resolve.");
  bullets(s, [
    { h: "Why not use the raw bits?" },
    "Biased or correlated bits fail tests, and an attacker's best guess beats ½",
    { h: "Von Neumann debiasing" },
    "Pairs: **01 → 0, 10 → 1**, drop 00 and 11",
    "Needs independent, identical bits; keeps **≤ 25 %** of the input",
    { h: "Hashing (what we use)" },
    "Each output bit is the XOR of many input bits",
    `Piling-up lemma: **bias = 2ᵏ⁻¹·εᵏ**; ε = ${pu.eps0.toFixed(4)} → **${pu.theory_bias[1].toExponential(1)}** at k = 2 (measured ${pu.empirical_bias[1].toExponential(1)})`,
  ], { x: MX, y: 1.5, w: 5.2, h: 5.0 }, { fontSize: 12.5 });
  img(s, "fig11_piling_up.png", { x: 6.1, y: 1.5, w: 6.63, h: 3.75 }, { alt: "Bias after XOR of k bits: theory and measurement" });
  card(s, { x: 6.1, y: 5.4, w: 3.2, h: 1.15, head: "ONE BIT", big: "ε = 0.0132", bigSize: 18, fill: "FDF2EC", color: ORANGE });
  card(s, { x: 9.53, y: 5.4, w: 3.2, h: 1.15, head: "XOR OF TWO BITS", big: "ε = 0.00035", bigSize: 18, fill: PASS_BG, color: TEAL });
}

// =================================================================================
// 13. Toeplitz matrix
// =================================================================================
{
  const s = content("C. Entropy and extraction", "C · Extraction", "The Toeplitz matrix: a hash with constant diagonals",
    "A Toeplitz matrix has the same value along every diagonal: entry (i, j) depends only on i minus j. So an m by n matrix is fully described by n plus m minus 1 seed bits - the first row and the first column - instead of m times n. Random Toeplitz matrices form a 2-universal hash family, which is exactly what the Leftover Hash Lemma needs. The output is y = T x modulo 2: each output bit is the XOR of the input bits in the positions where its row has a 1. Worked example: the first row is 0 0 1 1 0 1 and x is 0 1 1 1 0 1, so the first output bit is x3 XOR x4 XOR x6 = 1 XOR 1 XOR 1 = 1.");
  img(s, "fig12_toeplitz_structure.png", { x: MX, y: 1.5, w: 4.8, h: 3.4 }, { align: "left", alt: "A 14 by 24 Toeplitz matrix with constant diagonals highlighted" });
  bullets(s, [
    "**T[i, j] = s[i − j + n − 1]**: constant along every diagonal",
    "An m × n matrix needs only **n + m − 1** seed bits (here 37 instead of 336)",
    "Random Toeplitz matrices are a **2-universal hash family**",
    "Output **y = T·x mod 2**: each output bit = XOR of the inputs where its row has a 1",
  ], { x: 5.75, y: 1.5, w: 6.98, h: 2.05 }, { fontSize: 12.5 });
  img(s, "fig13_toeplitz_example.png", { x: 5.75, y: 3.45, w: 6.98, h: 2.3 }, { alt: "Worked 4 by 6 Toeplitz example" });
  card(s, { x: MX, y: 5.05, w: 4.8, h: 1.45, head: "FIRST OUTPUT BIT, BY HAND",
    body: "row 1 = 0 0 1 1 0 1,  x = 0 1 1 1 0 1\ny₁ = x₃ ⊕ x₄ ⊕ x₆\n    = 1 ⊕ 1 ⊕ 1 = **1**", bodySize: 11.5 });
  caption(s, "Purple = 1. T·x counts matches; mod 2 keeps the parity.", { x: 5.75, y: 5.85, w: 6.98, h: 0.4 });
}

// =================================================================================
// 131. Why Toeplitz hashing works
// =================================================================================
{
  const tu = DATA.toeplitz_universal.checks.find((c) => c.m === 8);
  const s = content("C. Entropy and extraction", "C · Extraction", "Why Toeplitz hashing works: 2-universality",
    "A hash family is 2-universal if, for any two different inputs, a randomly chosen member maps them to the same output with probability at most 2 to the minus m. For a linear hash this is a statement about one vector: T x equals T x-prime exactly when T times d is zero, where d is x XOR x-prime, which is non-zero. Proof for Toeplitz matrices: let j0 be the first position where d has a 1. Row i of T d is a XOR of seed bits, and the one with the largest index is s[i - j0 + n - 1]. Earlier rows only use seed bits with smaller indices, so going down the rows, every row brings in a seed bit that nothing above it has seen. Each row of T d is therefore a fresh fair coin, the m rows are independent, and the probability that all of them are zero is exactly 2 to the minus m. On the right we checked it numerically: 400,000 random seeds and pairs per output size, and the measured collision rate sits on 2 to the minus m.");
  card(s, { x: MX, y: 1.5, w: 5.1, h: 1.3, head: "2-UNIVERSAL HASH FAMILY", big: "Pr[T·x = T·x′] ≤ 2⁻ᵐ", bigSize: 18, body: "for every pair x ≠ x′" });
  card(s, { x: MX, y: 2.95, w: 5.1, h: 1.3, head: "LINEARITY", big: "T·x = T·x′  ⇔  T·d = 0", bigSize: 18, body: "with d = x ⊕ x′ ≠ 0" });
  card(s, { x: MX, y: 4.4, w: 5.1, h: 2.15, head: "PROOF IN ONE LINE",
    body: "j₀ = first 1 of d. Row i of T·d contains the seed bit\n**s[i − j₀ + n − 1]**, which no earlier row uses.\nEvery row is a **fresh fair coin**, so\nPr[T·d = 0] = 2⁻ᵐ exactly.", bodySize: 13 });
  img(s, "fig26_toeplitz_universal.png", { x: 6.0, y: 1.45, w: 6.73, h: 3.45 }, { alt: "Fresh seed bit per row, and measured collision probability" });
  card(s, { x: 6.0, y: 5.05, w: 6.73, h: 1.5, head: "CHECKED NUMERICALLY (m = 8, n = 16)",
    big: `${tu.measured.toFixed(4)}  vs  2⁻⁸ = ${tu.theory.toFixed(4)}`, bigSize: 18, fill: PASS_BG, color: TEAL });
}

// =================================================================================
// 132. Deriving the Leftover Hash Lemma
// =================================================================================
{
  const l = DATA.lhl;
  const s = content("C. Entropy and extraction", "C · Extraction", "Deriving the Leftover Hash Lemma",
    "Here is why m = k - 2 log2(1/epsilon) is the right number. The tool is collision probability: the chance that two independent draws are equal, which is the sum of the squared probabilities. If X has min-entropy k, every probability is at most 2 to the -k, so CP(X) is at most 2 to the -k. Now hash with a random member T of a 2-universal family and look at the pair (T, T X). Two independent copies collide only if they picked the same T - probability one over the family size - and then either X equals X-prime, at most 2 to the -k, or the hash collides anyway, at most 2 to the -m. A distribution whose collision probability is close to that of the uniform distribution must itself be close to uniform: the statistical distance is at most one half times the square root of N times CP minus 1. Putting the pieces together, the distance is at most one half times 2 to the (m - k)/2. Requiring that to be at most epsilon gives m = k - 2 log2(1/epsilon). The chart shows the trade-off for our block: every extra output bit costs half a bit of security. With k = 15,740 we keep 15,536 bits and get epsilon about 2 to the -102. Because the bound holds for the pair (T, T X), the seed can be public.");
  bullets(s, [
    { h: "1 · Collision probability" },
    "CP(Z) = Σ P(z)²;  min-entropy k  ⇒  **CP(X) ≤ 2⁻ᵏ**",
    { h: "2 · Hash with a random 2-universal T" },
    "**CP(T, T·X) ≤ (2⁻ᵏ + 2⁻ᵐ) / |𝒯|**",
    { h: "3 · Small CP means nearly uniform" },
    "distance to uniform ≤ ½·√(N·CP − 1), N = |𝒯|·2ᵐ",
    { h: "4 · Put together" },
    "**Δ ≤ ½·√(2ᵐ⁻ᵏ) ≤ ε  ⇔  m = k − 2·log₂(1/ε)**",
  ], { x: MX, y: 1.5, w: 5.6, h: 5.05 }, { fontSize: 15, space: 9 });
  img(s, "fig27_lhl_tradeoff.png", { x: 6.45, y: 1.45, w: 6.28, h: 3.45 }, { alt: "Security versus bits kept for one 16,384-bit block" });
  card(s, { x: 6.45, y: 5.05, w: 6.28, h: 1.5, head: "OUR BLOCK",
    big: `k = ${Math.round(l.entropy_in).toLocaleString("en-US")}  →  m = ${l.m.toLocaleString("en-US")}`, bigSize: 18,
    body: "ε ≈ 2⁻¹⁰², and it holds **even if the seed is public**" });
}

// =================================================================================
// 14. Leftover Hash Lemma
// =================================================================================
{
  const l = DATA.lhl;
  const s = content("C. Entropy and extraction", "C · Extraction", "How many bits can we keep? The Leftover Hash Lemma",
    "The Leftover Hash Lemma says: if an n-bit block has min-entropy at least k, hashing it with a randomly chosen 2-universal function to m = k - 2 log2(1/epsilon) bits gives output within statistical distance epsilon of uniform, even to someone who knows the hash. We chose epsilon = 2 to the -100, which costs 200 bits per block. With n = 16,384 and h = 0.9607 the block holds about 15,740 bits of min-entropy and we keep 15,536 - 94.8 percent of the input. Because the extractor is strong, the seed can be public and reused for every block; we drew it once from os.urandom.");
  img(s, "fig14_lhl_length.png", { x: MX, y: 1.5, w: 7.3, h: 4.6 }, { align: "left", alt: "Output length per input bit versus min-entropy" });
  card(s, { x: MX, y: 6.0, w: 7.3, h: 0.55, body: "**m = ⌊n·h − 2·log₂(1/ε)⌋**  →  output is ε-close to uniform, even given the seed", bodySize: 12 });
  const stats = [
    ["BLOCK SIZE n", "16,384 bits"], ["MIN-ENTROPY IN", `${Math.round(l.entropy_in).toLocaleString("en-US")} bits`],
    ["SECURITY ε", "2⁻¹⁰⁰ (200 bits)"], ["KEPT m", `${l.m.toLocaleString("en-US")} (${(l.kept_fraction * 100).toFixed(1)} %)`],
  ];
  stats.forEach(([h_, v], i) => card(s, { x: 8.2 + (i % 2) * 2.3, y: 1.5 + Math.floor(i / 2) * 1.35, w: 2.18, h: 1.22,
    head: h_, big: v, bigSize: 15 }));
  bullets(s, [
    "**Strong extractor**: the seed may be public and reused for every block",
    "Seed = n + m − 1 = **31,919 bits**, drawn once from os.urandom",
    "Too high an h estimate breaks the guarantee: **estimate first, then extract**",
  ], { x: 8.2, y: 4.35, w: 4.53, h: 2.2 }, { fontSize: 12 });
}

// =================================================================================
// 15. Implementation and effect
// =================================================================================
{
  const s = content("C. Entropy and extraction", "C · Extraction", "Fast Toeplitz hashing with the FFT, and its effect",
    "Multiplying by a Toeplitz matrix is a convolution, so we compute it with the FFT in O(n log n) instead of O(n m) per block. The convolution is computed in floating point, rounded, and reduced mod 2; a check guards against rounding error, and a unit test compares the result with an explicit matrix product. On the right, the effect per bit position, using 100,000 shots of one circuit: raw bits sit 0.5 to 2.7 points below 50 percent, every extracted position is back inside the plus-minus 3 sigma band. Overall the output goes from 48.69 to 50.002 percent ones.");
  code(s, [
    "L = 1 << (2*n + m - 2).bit_length()   # FFT size",
    "S = np.fft.rfft(seed, L)              # seed: n+m-1 bits",
    "X = np.fft.rfft(blocks, L, axis=1)    # many n-bit blocks",
    "conv = np.fft.irfft(X * S, L, axis=1)[:, n-1 : n-1+m]",
    "r = np.rint(conv)",
    "assert np.max(np.abs(conv - r)) <= 0.25",
    "y = r.astype(np.int64) & 1            # T·x mod 2",
  ].join("\n"), { x: MX, y: 1.5, w: 5.6, h: 1.85 }, 10.5);
  bullets(s, [
    "Toeplitz product = **convolution** → O(n log n) per block instead of O(n·m)",
    "Unit test: identical to the explicit matrix product",
    "**~20 M bits/s** in NumPy; extraction is not the bottleneck",
  ], { x: MX, y: 3.55, w: 5.6, h: 1.8 }, { fontSize: 12.5 });
  card(s, { x: MX, y: 5.3, w: 2.7, h: 0.98, head: "BEFORE", big: "48.69 % ones", bigSize: 16, fill: "FDF2EC", color: ORANGE });
  card(s, { x: MX + 2.9, y: 5.3, w: 2.7, h: 0.98, head: "AFTER", big: "50.002 % ones", bigSize: 16, fill: PASS_BG, color: TEAL });
  img(s, "fig15_column_bias.png", { x: 6.5, y: 1.5, w: 6.23, h: 3.8 }, { alt: "Per-position ones percentage before and after extraction" });
  card(s, { x: 6.5, y: 5.3, w: 6.23, h: 0.98, head: "RESULT", body: "Every bit position is back inside **±3σ** of 50 % (100,000 shots of one circuit)." });
}

// =================================================================================
// 16. Visual diagnostics
// =================================================================================
{
  const s = content("C. Entropy and extraction", "C · Diagnostics", "Seeing the bias: three pictures before and after",
    "Pictures are a quick sanity check before formal tests. Top left, the bias map: each row is a block of 10,000 shots, each column a bit position, colour is the deviation from 50 percent. The raw bits show vertical stripes - qubits that read 1 as 0 - and the stripes shift every 10 rows because the read-out order is reshuffled for each circuit. After extraction it is noise. Top right, byte-pair heat maps with bytes sorted by their number of ones: the raw bits show a gradient towards zero-heavy bytes; the control and the extracted bits are flat. Bottom right, autocorrelation: both raw and cleaned bits stay inside the 3 sigma band, so an autocorrelation plot alone cannot detect bias.");
  img(s, "fig16_column_heatmap.png", { x: MX, y: 1.5, w: 6.0, h: 2.85 }, { align: "left", alt: "Bias map before and after Toeplitz" });
  img(s, "fig17_bytepair.png", { x: 6.73, y: 1.5, w: 6.0, h: 2.1 }, { alt: "Byte-pair heat maps for control, raw and extracted bits" });
  img(s, "fig18_autocorr.png", { x: 6.73, y: 3.75, w: 6.0, h: 2.8 }, { alt: "Autocorrelation at lags 1 to 70" });
  bullets(s, [
    "**Bias map**: stripes = qubits reading 1 as 0; the pattern shifts each time the read-out order is reshuffled",
    "**Byte-pair map**: a gradient towards bytes with few 1s; flat after extraction",
    "**Autocorrelation**: inside ±3σ **before and after** — it subtracts the mean, so it is blind to bias",
  ], { x: MX, y: 4.5, w: 6.0, h: 2.05 }, { fontSize: 12 });
}

// =================================================================================
// 17. Hypothesis testing
// =================================================================================
pres.addSection({ title: "D. Statistical test suites" });
{
  const s = content("D. Statistical test suites", "D · Testing", "A statistical test can reject randomness, never prove it",
    "Every randomness test is a hypothesis test. The null hypothesis is that the bits are independent and fair. The test computes a statistic and its p-value: the probability of seeing a result at least this extreme if the null hypothesis is true. We reject at alpha = 0.01. Two consequences matter. First, under the null hypothesis p-values are uniformly distributed, so a perfect source still fails one test in a hundred - which is why we look at many sequences, not one. Second, a pass only means this test found no pattern. A good PRNG passes everything; passing never proves that bits are quantum or unpredictable. The histograms: 100 sequences of a million bits each; the control and extracted bits give flat p-values, the noisy bits pile up at zero.");
  bullets(s, [
    "**H₀**: the bits are independent and fair; reject when **p < 0.01**",
    "Under H₀ p-values are **uniform**: even perfect bits fail **1 % of tests**",
    "So we judge **many sequences**, not one",
    "A good PRNG passes too: tests **cannot certify** quantum origin",
  ], { x: MX, y: 1.6, w: 4.75, h: 4.9 }, { fontSize: 15, space: 16 });
  img(s, "fig19_pvalue_hist.png", { x: 5.6, y: 1.5, w: 7.13, h: 3.95 }, { alt: "p-value histograms for monobit and runs tests" });
  const pv = DATA.pvalues_frequency_runs;
  const tag = (d, t) => `${pv[d][t].passed}/100`;
  card(s, { x: 5.6, y: 5.6, w: 2.25, h: 0.95, head: "CONTROL PASSES", big: `${tag("urandom", "Frequency (monobit)")} · ${tag("urandom", "Runs")}`, bigSize: 14 });
  card(s, { x: 8.04, y: 5.6, w: 2.25, h: 0.95, head: "NOISY PASSES", big: `${tag("aer_D_ibmlike", "Frequency (monobit)")} · ${tag("aer_D_ibmlike", "Runs")}`, bigSize: 14, fill: "FDF2EC", color: ORANGE });
  card(s, { x: 10.48, y: 5.6, w: 2.25, h: 0.95, head: "AFTER TOEPLITZ", big: `${tag("aer_D_ibmlike_toeplitz", "Frequency (monobit)")} · ${tag("aer_D_ibmlike_toeplitz", "Runs")}`, bigSize: 14, fill: PASS_BG, color: TEAL });
}

// =================================================================================
// 18. NIST tests
// =================================================================================
{
  const s = content("D. Statistical test suites", "D · NIST SP 800-22", "NIST SP 800-22: 15 tests, 188 sub-tests",
    "NIST Special Publication 800-22 is the US government's statistical test suite for random bit generators. It has fifteen tests; with the template and excursion variants, 188 sub-tests in total. Grouped by what they look for: overall and local frequency; oscillation, that is runs of identical bits; linear structure in matrices and spectra; specific bit patterns; compressibility; linear complexity in short blocks; and random-walk excursions. The parameters shown are the defaults of the official STS 2.1.2 code we run.");
  const T = [
    ["Frequency", "Monobit", "Overall share of 1s", "n ≥ 100"],
    ["", "Block frequency", "Share of 1s inside blocks", "M = 128"],
    ["", "Cumulative sums", "Max excursion of the ±1 walk", "forward, backward"],
    ["Oscillation", "Runs", "Number of runs of identical bits", "needs monobit pass"],
    ["", "Longest run of ones", "Longest run per block", "M = 10,000"],
    ["Structure", "Binary matrix rank", "Linear dependence of 32×32 blocks", "rank over GF(2)"],
    ["", "Spectral (DFT)", "Periodic features", "peak height"],
    ["Patterns", "Non-overlapping template", "148 aperiodic 9-bit templates", "148 sub-tests"],
    ["", "Overlapping template", "Runs of nine 1s", "m = 9"],
    ["Compression", "Maurer universal", "Compressibility", "n ≥ 387,840"],
    ["", "Approximate entropy", "m vs m+1 bit pattern frequencies", "m = 10"],
    ["", "Serial", "All overlapping 16-bit patterns", "2 sub-tests"],
    ["Linearity", "Linear complexity", "Shortest LFSR per block", "M = 500"],
    ["Random walk", "Random excursions", "Cycles visiting states ±1…±4", "8 sub-tests"],
    ["", "Random excursions variant", "Visits to states ±1…±9", "18 sub-tests"],
  ];
  const rows = [[hcell("Group"), hcell("Test"), hcell("Looks for"), hcell("Parameters")]];
  T.forEach(([g, t, d, p]) => rows.push([cell(g, { bold: true, color: PURPLE, fontSize: 10.5 }), cell(t, { bold: true, fontSize: 10.5 }),
    cell(d, { fontSize: 10.5 }), cell(p, { fontSize: 10.5, color: GRAY })]));
  s.addTable(rows, { x: MX, y: 1.45, w: 8.9, colW: [1.45, 2.4, 3.25, 1.8], border: TB, rowH: 0.315 });
  card(s, { x: 9.75, y: 1.45, w: 2.98, h: 1.5, head: "SUB-TESTS", big: "188", body: "from 15 tests" });
  card(s, { x: 9.75, y: 3.1, w: 2.98, h: 1.5, head: "PROTOCOL", big: "100 × 10⁶", body: "sequences × bits" });
  card(s, { x: 9.75, y: 4.75, w: 2.98, h: 1.8, head: "SIGNIFICANCE", big: "α = 0.01", body: "official STS 2.1.2 code, run non-interactively" });
}

// =================================================================================
// 20. Running NIST properly
// =================================================================================
{
  const s = content("D. Statistical test suites", "D · NIST SP 800-22", "Running NIST properly: many sequences, two criteria",
    "One sequence gives one p-value per test, and at alpha 0.01 a perfect generator fails about one test in a hundred, so a single run cannot judge a generator. The protocol runs 100 sequences of a million bits. A sub-test passes if two things hold. Proportion: at least 0.99 minus 3 sigma of the sequences pass, which is 96 out of 100. Uniformity: the 100 p-values are spread evenly - a chi-square test over ten bins must give at least 10 to the -4; NIST applies this only with at least 55 sequences. And with 148 template sub-tests, even a perfect source fails up to 3 of them by chance at the 99 percent level, so we judge each family with a binomial allowance. Our harness drives the official C program through its interactive prompts.");
  img(s, "fig20_proportion.png", { x: MX, y: 1.5, w: 7.95, h: 2.7 }, { align: "left", alt: "Proportion rule and per-sub-test pass proportions" });
  code(s, [
    "# drive the official STS 2.1.2 'assess'",
    "answers = (\"0\\ndata.bin\\n1\\n0\\n\"",
    "           f\"{streams}\\n1\\n\")",
    "subprocess.run([assess, str(n)],",
    "               input=answers, cwd=work)",
    "# → finalAnalysisReport.txt",
    "#   proportion + uniformity",
    "#   for all 188 sub-tests",
  ].join("\n"), { x: 8.75, y: 1.5, w: 3.98, h: 2.7 }, 9.5);
  card(s, { x: MX, y: 4.4, w: 3.9, h: 2.15, head: "PROPORTION", big: "≥ 96 / 100",
    body: "sequences must pass each sub-test", bodySize: 12.5 });
  card(s, { x: MX + 4.1, y: 4.4, w: 3.9, h: 2.15, head: "UNIFORMITY", big: "P ≥ 10⁻⁴",
    body: "the p-values must be spread evenly", bodySize: 12.5 });
  card(s, { x: MX + 8.2, y: 4.4, w: 3.93, h: 2.15, head: "148 TEMPLATES", big: "≤ 3 failures",
    body: "are expected by chance, so 147/148 is fine", bodySize: 12.5 });
}

// =================================================================================
// 21. NIST results
// =================================================================================
{
  const nb = DATA.nist_summary;
  const g = (d) => nb.find((r) => r.dataset === d);
  const s = content("D. Statistical test suites", "D · NIST SP 800-22", "NIST results: bias fails everywhere, extraction fixes it",
    "The grid shows, for each test family and dataset, how many sub-tests passed. The control and every simulator dataset pass; the single template failures are within chance. The noisy source fails ten of the thirteen families that could run - everything sensitive to bias - and the random-excursion tests cannot even run, because a walk that drifts by tens of thousands of steps almost never returns to zero. Rank, spectral and linear complexity still pass: bias does not create linear structure or periodicity. After Toeplitz extraction everything passes again. Note one more thing: NIST's linear-complexity test passes the 100k-shot simulator data, because its 500-bit blocks are far shorter than the 19,937-bit structure.");
  img(s, "fig21_nist_heatmap.png", { x: MX, y: 1.45, w: 7.85, h: 5.1 }, { align: "left", alt: "NIST family pass counts per dataset" });
  card(s, { x: 8.7, y: 1.45, w: 4.03, h: 1.25, head: "CONTROL AND SIMULATOR", big: `${g("urandom").passed}/${g("urandom").total} · ${g("aer_D_5k").passed}/${g("aer_D_5k").total}`, bigSize: 20 });
  card(s, { x: 8.7, y: 2.85, w: 4.03, h: 1.25, head: "NOISY SOURCE", big: `${g("aer_D_ibmlike").passed}/${g("aer_D_ibmlike").total} sub-tests`, bigSize: 20, fill: "FDF2EC", color: ORANGE });
  card(s, { x: 8.7, y: 4.25, w: 4.03, h: 1.25, head: "AFTER TOEPLITZ", big: `${g("aer_D_ibmlike_toeplitz").passed}/${g("aer_D_ibmlike_toeplitz").total}`, bigSize: 20, fill: PASS_BG, color: TEAL });
  para(s, "NIST's own linear-complexity test **misses** the simulator's formula.",
    { x: 8.7, y: 5.75, w: 4.03, h: 0.8 }, { fontSize: 13 });
}

// =================================================================================
// 22. TestU01
// =================================================================================
{
  const s = content("D. Statistical test suites", "D · TestU01", "TestU01: a tougher library, adapted to finite files",
    "TestU01, by Pierre L'Ecuyer and Richard Simard (2007), is the most demanding standard library for random number generators. Its big batteries - SmallCrush, Crush and BigCrush - ask the generator for billions of numbers; SmallCrush alone needs about 7.3 billion bits, far beyond a file from a QRNG experiment. Rabbit and Alphabit were designed for exactly our case: a fixed file of bits. We wrote a small C harness that reads the file into memory, feeds it to TestU01 32 bits at a time, and stops with an explicit 'exhausted' status rather than silently wrapping around. On the right is one statistic Rabbit uses: the random walk. Bias makes the walk drift steadily away - 26,000 steps in a million bits for the noisy source - while fair bits stay inside plus or minus 3 root n.");
  const rows = [
    [hcell("Battery"), hcell("Tests"), hcell("Data needed")],
    [cell("SmallCrush", { bold: true }), cell("10"), cell("≈ 7.3 × 10⁹ bits (measured)")],
    [cell("Crush / BigCrush", { bold: true }), cell("96 / 106"), cell("≈ 2³⁵ / 2³⁸ numbers")],
    [cell("Rabbit", { bold: true, color: PURPLE }), cell("38 results"), cell("any file; reads ≈ 23 × nb bits")],
    [cell("Alphabit", { bold: true, color: PURPLE }), cell("17 results"), cell("any file; reads ≈ 9 × nb bits")],
    [cell("LinearComp", { bold: true, color: PURPLE }), cell("4 results"), cell("2 × 400,020-bit sequences")],
  ];
  s.addTable(rows, { x: MX, y: 1.5, w: 5.9, colW: [1.75, 1.2, 2.95], border: TB, rowH: 0.36 });
  code(s, [
    "static unsigned int next_word(void) {",
    "  if (pos >= n_words) {          /* never rewind */",
    "    printf(\"EXHAUSTED\\t%ld\\n\", n_words);",
    "    exit(3);",
    "  }",
    "  return words[pos++];          /* big-endian 32-bit */",
    "}",
    "gen = unif01_CreateExternGenBits(file, next_word);",
    "bbattery_Rabbit(gen, nbits);",
  ].join("\n"), { x: MX, y: 3.95, w: 5.9, h: 2.45 }, 10.5);
  img(s, "fig23_random_walk.png", { x: 6.75, y: 1.5, w: 5.98, h: 3.55 }, { alt: "Random walks of control, noisy and extracted bits" });
  bullets(s, [
    "**Three of our five suites** come from TestU01: Rabbit, Alphabit, LinearComp",
    "Bias shows up as a **steady drift** of the random walk",
  ], { x: 6.75, y: 5.25, w: 5.98, h: 1.3 }, { fontSize: 13.5, space: 8 });
}

// =================================================================================
// 23. LinearComp
// =================================================================================
{
  const s = content("D. Statistical test suites", "D · TestU01", "LinearComp: catching a linear generator",
    "LinearComp runs Berlekamp-Massey over 400,020 bits taken from one bit position of each 32-bit word - positions 0 and 29, as in BigCrush - and looks at how the linear complexity jumps as bits arrive. For random bits the number and size of the jumps follow known distributions. MT19937 is linear over GF(2), so for the 100k-shot data the complexity stops jumping once it reaches 19,937, and the jump-count p-value is exactly 1: a clear failure, and the only test in the whole study that detects the simulator. It does not fail the 5k-shot data, because Aer re-seeds its generator for every circuit, so no 5,000-shot segment is long enough. And it does not fail the noisy data: the read-out errors are sampled by comparing random doubles with a threshold, which is not linear. Both datasets are still completely determined by their seed.");
  const rows = [[hcell("Dataset"), hcell("Jump count, bit 0", { align: "center" }), hcell("Jump size, bit 0", { align: "center" }),
    hcell("Jump count, bit 29", { align: "center" }), hcell("Jump size, bit 29", { align: "center" })]];
  ORDER.forEach((d) => {
    const b = R(d).testu01.batteries.find((x) => x.battery === "lincomp");
    const p = b.tests.map((t) => t.p_value);
    rows.push([cell(NAMES[d], { bold: true, fontSize: 10.5 }), ...p.map((v) => {
      const bad = v > 0.999 || v < 0.001;
      return cell(fmtP(v), { align: "center", fontSize: 10.5, bold: bad, color: bad ? ORANGE : INK, fill: bad ? FAIL_BG : "FFFFFF" });
    })]);
  });
  s.addTable(rows, { x: MX, y: 1.5, w: 7.6, colW: [2.8, 1.2, 1.2, 1.2, 1.2], border: TB, rowH: 0.42 });
  caption(s, "TestU01 LinearComp, n = 400,020 bits per sequence, bit positions 0 and 29 (BigCrush parameters).", { x: MX, y: 4.55, w: 7.6, h: 0.35 });
  card(s, { x: MX, y: 5.0, w: 3.7, h: 1.55, head: "WHY 5K SHOTS PASSES", body: "Re-seeded every 5,000 shots: too short to show", bodySize: 12.5 });
  card(s, { x: MX + 3.9, y: 5.0, w: 3.7, h: 1.55, head: "WHY NOISY DATA PASSES", body: "The noise adds **non-linear** steps", bodySize: 12.5 });
  img(s, "fig08_lfsr_example.png", { x: 8.55, y: 1.5, w: 4.18, h: 1.75 }, { alt: "LFSR linear complexity example" });
  bullets(s, [
    "Berlekamp–Massey on **400,020-bit** sequences",
    "MT19937 is linear: L stops at 19,937 → **p = 1.000**",
    "The passing runs are **still predictable** from the seed",
  ], { x: 8.55, y: 3.55, w: 4.18, h: 3.0 }, { fontSize: 13.5, space: 10 });
}

// =================================================================================
// 24. TestU01 results
// =================================================================================
{
  const tu = (d, b) => SB(d).testu01[b];
  const ok = (d, b) => tu(d, b).tests - tu(d, b).failed - tu(d, b).suspicious;
  const s = content("D. Statistical test suites", "D · TestU01", "TestU01 results: every p-value, all six datasets",
    "Each dot is one p-value. Shaded bands are outside 0.001 to 0.999, where TestU01's authors call a result suspicious; beyond 10 to the -10 it is a clear failure. The control, the simulator datasets and the extracted bits spread evenly over zero to one in Rabbit and Alphabit. The noisy source collapses to zero in Hamming-weight, random-walk and multinomial tests: 14 of 38 Rabbit results and 2 of 17 Alphabit results survive. In LinearComp, the only failures in the whole table are the two jump-count p-values of 1.0 for the 100k-shot simulator.");
  img(s, "fig22_testu01_strip.png", { x: MX, y: 1.45, w: CW, h: 3.95 }, { alt: "All TestU01 p-values per dataset and battery" });
  card(s, { x: MX, y: 5.5, w: 3.9, h: 1.05, head: "NOISY SOURCE", big: `Rabbit ${ok("aer_D_ibmlike", "rabbit")}/38 · Alphabit ${ok("aer_D_ibmlike", "alphabit")}/17`, bigSize: 15, fill: "FDF2EC", color: ORANGE });
  card(s, { x: MX + 4.1, y: 5.5, w: 3.9, h: 1.05, head: "SIMULATOR, 100K SHOTS/RUN", big: `LinearComp ${4 - tu("aer_D_ideal", "lincomp").failed}/4`, bigSize: 15, fill: "FDF2EC", color: ORANGE });
  card(s, { x: MX + 8.2, y: 5.5, w: 3.93, h: 1.05, head: "EVERYTHING ELSE", big: "38/38 · 17/17 · 4/4", bigSize: 15, fill: PASS_BG, color: TEAL });
}

// =================================================================================
// 25. Dieharder
// =================================================================================
{
  const s = content("D. Statistical test suites", "D · Dieharder", "Dieharder: Marsaglia's classic tests, extended",
    "Dieharder, by Robert G. Brown, extends George Marsaglia's 1995 Diehard battery. Many of its tests are small simulations whose answer is known for true randomness. The parking-lot test is the easiest to picture: try to park cars at random positions in a square lot; a car that would touch an already-parked car crashes. For random coordinates the number of successfully parked cars is known - about 3,523 out of 12,000 attempts in Diehard's 100 by 100 lot. Others: birthday spacings, overlapping permutations, matrix ranks, minimum distance between random points, 3D spheres, squeeze, and craps. One practical trap: when Dieharder reads from a file and runs out of data it silently rewinds and reuses it, which causes failures for the wrong reason. To give a sense of scale: a full -a run on a 1-gigabyte control file had already re-read the file 89 times before we stopped it. So we ran each test on its own, with as many p-samples as the 100-million-bit file supports without rewinding, calibrated on the control: 19 tests and 49 results per dataset; eight tests need more data and were left out. Results: the control and the simulator datasets pass, with a few WEAK results as expected by chance; the noisy source fails 22 results in the bias-sensitive tests; after Toeplitz extraction it passes.");
  img(s, "fig25_parking_lot.png", { x: MX, y: 1.5, w: 3.9, h: 4.35 }, { align: "left", alt: "Parking lot test illustration" });
  caption(s, "Parking lot with real control bits: purple = parked, orange = crashed.", { x: MX, y: 5.95, w: 3.9, h: 0.6 });
  bullets(s, [
    "Small simulations with a **known answer**: birthday spacings, parking lot, 3D spheres, craps…",
    "File input **re-reads** the data when it runs out → false failures",
    "We size each test so it **never re-reads**: 19 tests per dataset",
  ], { x: 4.75, y: 1.5, w: 3.6, h: 5.05 }, { fontSize: 13, space: 12 });
  if (DH && DH.datasets) {
    const short = (d) => (NAMES[d] || d).replace("Simulator, ", "Sim, ").replace("Same noisy bits after Toeplitz", "After Toeplitz")
      .replace("Control (OS random)", "Control").replace("uneven read-out noise", "read-out noise").replace("2% symmetric noise", "2% sym. noise");
    para(s, `**Results per dataset** (${DH.tests_run} tests, 49 results)`, { x: 8.55, y: 1.5, w: 4.18, h: 0.35 }, { fontSize: 12 });
    const rows = [[hcell("Dataset", { fontSize: 10.5 }), hcell("Pass", { align: "center", fontSize: 10.5 }),
      hcell("Weak", { align: "center", fontSize: 10.5 }), hcell("Fail", { align: "center", fontSize: 10.5 })]];
    DH.datasets.forEach((d) => {
      const bad = d.failed > 0;
      rows.push([cell(short(d.dataset), { bold: true, fontSize: 10.5 }),
        cell(String(d.passed), { align: "center", fontSize: 11, color: TEAL, fill: PASS_BG, bold: true }),
        cell(String(d.weak), { align: "center", fontSize: 11, color: GRAY }),
        cell(String(d.failed), { align: "center", fontSize: 11, bold: bad, color: bad ? ORANGE : GRAY, fill: bad ? FAIL_BG : "FFFFFF" })]);
    });
    s.addTable(rows, { x: 8.55, y: 1.92, w: 4.18, colW: [2.08, 0.7, 0.7, 0.7], border: TB, rowH: 0.44 });
    para(s, DH.note || "", { x: 8.55, y: 5.2, w: 4.18, h: 1.35 }, { fontSize: 11, color: GRAY });
  } else {
    card(s, { x: 8.55, y: 1.5, w: 4.18, h: 5.05, head: "RESULTS", body: "Dieharder results are added here by build_deck.js from results/dieharder/summary.json." });
  }
}

// =================================================================================
// 26. Software
// =================================================================================
pres.addSection({ title: "E. Engineering and conclusions" });
{
  const s = content("E. Engineering and conclusions", "E · Engineering", "The pipeline as software: one command, fully reproducible",
    "Everything in this talk is produced by one Python package. generate and noise produce the bits; entropy, lincomp and extractor analyse and clean them; three drivers run the external suites - the official NIST C code, our TestU01 harness and Dieharder; pipeline ties it together and writes a summary table plus every p-value as JSON; figures draws every chart in this deck from those results. A full run of six datasets at 10 to the 8 bits takes about 12 minutes on 22 cores. Seeds are recorded, output does not depend on the number of workers, 19 unit tests check the maths, and a GitHub Actions workflow re-runs everything on Linux.");
  const BH = 0.8;
  const box = (x, y, w, t, sub, strong) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: BH, rectRadius: 0.08, fill: { color: strong ? PURPLE : LAV2 }, line: { color: strong ? PURPLE : LINE, width: 1 } });
    s.addText(t, { x: x + 0.08, y: y + 0.07, w: w - 0.16, h: 0.36, fontFace: MONO, fontSize: 12, bold: true, color: strong ? "FFFFFF" : DEEP, align: "center", margin: 0, isTextBox: true });
    s.addText(sub, { x: x + 0.08, y: y + 0.43, w: w - 0.16, h: 0.32, fontFace: FONT, fontSize: 9.5, color: strong ? "FFFFFF" : GRAY, align: "center", margin: 0, isTextBox: true });
  };
  const bw = 2.05, gx = (CW - 5 * bw) / 4, col = (i) => MX + i * (bw + gx);
  const r1 = 1.65, r2 = 2.6, r3 = 3.55, mid = r2;
  box(col(0), r1 + 0.45, bw, "generate", "Aer circuits → .bin");
  box(col(0), r2 + 0.45, bw, "noise", "read-out models");
  box(col(1), r1 + 0.45, bw, "entropy", "SP 800-90B style");
  box(col(1), r2 + 0.45, bw, "lincomp", "Berlekamp–Massey");
  box(col(2), mid, bw, "extractor", "Toeplitz via FFT", true);
  box(col(3), r1, bw, "nist_sts", "official STS 2.1.2");
  box(col(3), r2, bw, "testu01", "C harness");
  box(col(3), r3, bw, "dieharder", "sized, no rewinds");
  box(col(4), mid, bw, "pipeline", "summary.md / .json", true);
  const cy = (y) => y + BH / 2;
  arrow(s, col(0) + bw + 0.05, cy(r1 + 0.45), col(1) - 0.05, cy(r1 + 0.45));
  arrow(s, col(1) + bw + 0.05, cy(r1 + 0.45), col(2) - 0.05, cy(mid) - 0.1);
  arrow(s, col(2) + bw + 0.05, cy(mid), col(3) - 0.05, cy(mid));
  arrow(s, col(3) + bw + 0.05, cy(mid), col(4) - 0.05, cy(mid));
  code(s, "python -m hqrng.pipeline --profile full --out results/full\npython -m hqrng.figures   # every chart in this deck", { x: MX, y: 4.45, w: 6.3, h: 0.85 }, 11);
  bullets(s, [
    "Seeds recorded; output **identical for any worker count**",
    "**19 unit tests**: Toeplitz vs explicit matrix, estimators, NIST rules, file formats",
    "GitHub Actions workflow re-runs every suite on Linux",
  ], { x: MX, y: 5.45, w: 6.3, h: 1.15 }, { fontSize: 12 });
  card(s, { x: 7.2, y: 4.45, w: 2.65, h: 2.1, head: "FULL RUN", big: "≈ 12 min", body: "6 datasets × 10⁸ bits, 22 cores" });
  card(s, { x: 10.05, y: 4.45, w: 2.68, h: 2.1, head: "OUTPUT", big: "1 table", body: "+ every p-value as JSON, + 25 figures" });
}

// =================================================================================
// 27. Scoreboard
// =================================================================================
{
  const s = content("E. Engineering and conclusions", "E · Results", "Scoreboard: six datasets against every tool",
    "This table brings everything together. Green cells are passes, orange cells are failures. Read it row by row: the control passes everything, as it must, which shows the harness itself is sound. The simulator datasets pass every statistical suite - except LinearComp on the long 100k-shot runs, which exposes the Mersenne Twister; the linear-complexity column shows the same thing directly. The noisy source fails its entropy estimate, NIST, Rabbit and Alphabit. After Toeplitz extraction it passes everything again.");
  const dh = (d) => {
    if (!DH || !DH.datasets) return { t: "pending", bad: null };
    const r = DH.datasets.find((x) => x.dataset === d);
    if (!r) return { t: "–", bad: null };
    return { t: `${r.passed}/${r.passed + r.weak + r.failed}`, bad: r.failed > 0 };
  };
  const rows = [[hcell("Dataset"), hcell("Ones %", { align: "center" }), hcell("h_min", { align: "center" }),
    hcell("Lin. compl. (bit 0)", { align: "center" }), hcell("NIST", { align: "center" }), hcell("Rabbit", { align: "center" }),
    hcell("Alphabit", { align: "center" }), hcell("LinearComp", { align: "center" }), hcell("Dieharder", { align: "center" })]];
  ORDER.forEach((d) => {
    const r = SB(d);
    const t = r.testu01;
    const c = (txt, bad) => cell(txt, { align: "center", fontSize: 11, bold: bad === true, color: bad === true ? ORANGE : bad === false ? TEAL : GRAY,
      fill: bad === true ? FAIL_BG : bad === false ? PASS_BG : NA_BG });
    const lc = r.lincomp_columns.bit0;
    const ok = (b) => t[b].tests - t[b].failed - t[b].suspicious;
    const dd = dh(d);
    rows.push([cell(NAMES[d], { bold: true, fontSize: 11 }),
      c(r.ones_percent.toFixed(3), Math.abs(r.ones_percent - 50) > 0.05),
      c(r.h_min.toFixed(3), r.h_min < 0.99),
      c(lc.toLocaleString("en-US"), lc === 19937),
      c(`${r.nist_passed}/${r.nist_total}`, r.nist_passed < r.nist_total - 3),
      c(`${ok("rabbit")}/${t.rabbit.tests}`, ok("rabbit") < t.rabbit.tests),
      c(`${ok("alphabit")}/${t.alphabit.tests}`, ok("alphabit") < t.alphabit.tests),
      c(`${ok("lincomp")}/${t.lincomp.tests}`, ok("lincomp") < t.lincomp.tests),
      c(dd.t, dd.bad)]);
  });
  s.addTable(rows, { x: MX, y: 1.5, w: CW, colW: [3.13, 1.05, 0.95, 1.55, 1.05, 1.0, 1.05, 1.25, 1.1], border: TB, rowH: 0.58 });
  para(s, "Green = pass · orange = fail · NIST: 147/188 or better counts as a pass (template failures within chance) · noisy source: random-excursion tests could not run (162 sub-tests).",
    { x: MX, y: 5.75, w: CW, h: 0.5 }, { fontSize: 10.5, color: GRAY });
}

// =================================================================================
// 28. Which tool catches which flaw
// =================================================================================
{
  const s = content("E. Engineering and conclusions", "E · Results", "No single tool catches every flaw",
    "Turning the scoreboard around: which tool caught which kind of flaw? Bias is easy - almost everything catches it except linear-complexity tests and autocorrelation. The linear structure of the Mersenne Twister is caught only by TestU01's LinearComp and our own Berlekamp-Massey diagnostic; NIST misses it. And the 5k-shot simulator, which is just as deterministic, is caught by nothing at all. Three lessons follow: run several independent suites; never read a pass as proof of quantum origin; and treat entropy estimation and extraction as part of the generator, not an optional extra.");
  const dhBias = DH && DH.datasets ? ((DH.datasets.find((d) => d.dataset === "aer_D_ibmlike") || {}).failed > 0 ? "yes" : "no") : "?";
  const dhLin = DH && DH.datasets ? ((DH.datasets.find((d) => d.dataset === "aer_D_ideal") || {}).failed > 0 ? "yes" : "no") : "?";
  const dh5k = DH && DH.datasets ? ((DH.datasets.find((d) => d.dataset === "aer_D_5k") || {}).failed > 0 ? "yes" : "no") : "?";
  const M = [
    ["Bias (48.7 % ones)", "yes", "yes", "yes", "yes", "no", dhBias, "yes*"],
    ["Linear generator, long runs (MT19937)", "no", "no", "no", "no", "yes", dhLin, "no"],
    ["Same generator, re-seeded every 5,000 shots", "no", "no", "no", "no", "no", dh5k, "no"],
  ];
  const heads = ["Flaw", "Entropy estimate", "NIST SP 800-22", "Rabbit", "Alphabit", "LinearComp", "Dieharder", "Visual checks"];
  const rows = [heads.map((h, i) => hcell(h, { align: i ? "center" : "left", fontSize: 10 }))];
  M.forEach((r) => rows.push(r.map((v, i) => i === 0 ? cell(v, { bold: true, fontSize: 11 }) :
    cell(v === "yes" ? "✓ caught" : v === "yes*" ? "✓ caught*" : v === "no" ? "– missed" : "?", { align: "center", fontSize: 10.5, bold: v.startsWith("yes"),
      color: v.startsWith("yes") ? TEAL : v === "no" ? ORANGE : GRAY, fill: v.startsWith("yes") ? PASS_BG : v === "no" ? FAIL_BG : NA_BG }))));
  s.addTable(rows, { x: MX, y: 1.5, w: CW, colW: [3.13, 1.29, 1.29, 1.28, 1.28, 1.29, 1.28, 1.29], border: TB, rowH: 0.62 });
  caption(s, "* bias map and byte-pair heat map catch it; autocorrelation does not.", { x: MX, y: 4.05, w: CW, h: 0.3 });
  const L = [
    ["1", "Run several independent suites", "Only LinearComp saw the Mersenne Twister; NIST and Rabbit passed it."],
    ["2", "A pass is not proof", "The re-seeded simulator passes everything and is still fully predictable."],
    ["3", "Estimate, then extract", "Raw device bits fail; extraction sized by min-entropy fixes them at a 5 % cost."],
  ];
  L.forEach(([n, t, b], i) => {
    const x = MX + i * 4.1;
    s.addShape(pres.shapes.OVAL, { x, y: 4.6, w: 0.62, h: 0.62, fill: { color: PURPLE }, line: { color: PURPLE, width: 0 } });
    s.addText(n, { x, y: 4.6, w: 0.62, h: 0.62, fontFace: FONT, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText(t, { x: x + 0.78, y: 4.6, w: 2.95, h: 0.62, fontFace: FONT, fontSize: 13.5, bold: true, color: INK, valign: "middle", margin: 0, isTextBox: true });
    para(s, b, { x: x + 0.78, y: 5.3, w: 3.15, h: 1.2 }, { fontSize: 12 });
  });
}

// =================================================================================
// 30. Conclusion and references
// =================================================================================
{
  const s = content("E. Engineering and conclusions", "E · Conclusion", "Conclusion",
    "To close: we built a complete, reproducible pipeline for testing quantum random number generators, from circuit to verdict. Four numbers summarise it. Realistic read-out error produces 48.7 percent ones, which every bias test rejects. Min-entropy estimation measured 0.961 bits per raw bit. Toeplitz extraction kept 94.8 percent of the bits and restored a clean pass on every suite. And only one test in the whole study, TestU01's LinearComp, noticed that the simulator's randomness is a Mersenne Twister. Passing statistical tests is necessary, not sufficient; the source and the extraction matter as much as the tests. Thank you - questions welcome.");
  const big = [["48.7 %", "ones from realistic read-out noise: every bias test rejects it"], ["0.961", "bits of min-entropy per raw bit, measured"],
    ["94.8 %", "of the bits kept by Toeplitz extraction, then a clean pass"], ["1 test", "noticed the simulator's Mersenne Twister: LinearComp"]];
  big.forEach(([v, t], i) => {
    const y = 1.5 + i * 1.1;
    s.addText(v, { x: MX, y, w: 2.5, h: 0.75, fontFace: FONT, fontSize: 30, bold: true, color: PURPLE, margin: 0, isTextBox: true, valign: "middle" });
    para(s, t, { x: MX + 2.6, y: y + 0.05, w: 3.9, h: 0.75 }, { fontSize: 12.5, valign: "middle" });
  });
  para(s, "Passing statistical tests is **necessary, not sufficient**: the source and the extraction matter as much as the tests.",
    { x: MX, y: 5.95, w: 6.4, h: 0.6 }, { fontSize: 12 });
  s.addText("Thank you  ·  Aradhya Mahajan (B23CS1088)  ·  Amee Ghai (B23PH1003)", { x: MX, y: 6.62, w: 12.1, h: 0.32, fontFace: FONT, fontSize: 11, bold: true,
    color: PURPLE, margin: 0, isTextBox: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.35, y: 1.5, w: 5.38, h: 5.05, rectRadius: 0.08, fill: { color: LAV2 }, line: { color: LAV2, width: 0 } });
  s.addText("REFERENCES", { x: 7.55, y: 1.62, w: 5, h: 0.3, fontFace: FONT, fontSize: 10, bold: true, color: PURPLE, margin: 0, isTextBox: true });
  const refs = [
    "NIST SP 800-22 Rev. 1a (2010): statistical test suite for RNGs",
    "NIST SP 800-90B (2018): entropy sources used for random bit generation",
    "P. L'Ecuyer, R. Simard, TestU01, ACM TOMS 33(4), 2007",
    "R. G. Brown, Dieharder; G. Marsaglia, Diehard (1995)",
    "R. Impagliazzo, L. Levin, M. Luby, pseudo-random generation from one-way functions, STOC 1989 (Leftover Hash Lemma)",
    "H. Krawczyk, LFSR-based hashing and authentication, CRYPTO 1994 (Toeplitz hashing)",
    "E. Berlekamp (1968); J. Massey, shift-register synthesis, IEEE Trans. IT 1969",
    "M. Matsumoto, T. Nishimura, Mersenne Twister, ACM TOMACS 1998",
    "M. Herrero-Collantes, J. C. Garcia-Escartin, Quantum random number generators, Rev. Mod. Phys. 89, 2017",
    "Qiskit Aer documentation (stabilizer simulation, noise models)",
  ];
  s.addText(refs.map((r, i) => ({ text: r, options: { bullet: { indent: 12 }, breakLine: i < refs.length - 1, paraSpaceAfter: 4 } })),
    { x: 7.55, y: 1.98, w: 5.0, h: 4.45, fontFace: FONT, fontSize: 10.5, color: INK, margin: 0, isTextBox: true, valign: "top" });
}

// ---- write -----------------------------------------------------------------------
(async () => {
  await pres.writeFile({ fileName: OUT });
  const skill = process.env.PPTX_SKILL;
  if (skill) {
    const { applyTheme } = require(path.join(skill, "scripts/apply_theme.js"));
    await applyTheme(OUT, THEME);
  }
  console.log(`wrote ${OUT} (${slideNo} slides)`);
})();
