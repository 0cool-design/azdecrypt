#!/usr/bin/env python3
"""Deeper structure probes for the unsolved Liber Primus pages.

Section 4-5 ruled out monoalphabetic, short-period Vigenere, and the common
number-theoretic keystreams. This script tests three further cipher *classes*,
a bigram-distribution analysis, and a calibrated redundancy number:

  1. Periodic (Friedman) IoC  -> repeating-key Vigenere at any period 1..40.
     For each candidate period d, split into d columns and average the per-column
     IoC. A real repeating key of length d makes every column monoalphabetic, so
     column-IoC jumps to English-level (~0.06); random stays at 1/29.
  2. Isomorph test            -> homophonic substitution. A repeated plaintext
     substring containing a repeated letter survives homophonic encipherment as a
     repeated 'first-occurrence pattern' (isomorph). We count non-trivial repeated
     isomorphs and compare to the mean over random shuffles of the same symbols.
  3. Unigram chi^2 vs English -> pure transposition / plaintext. Transposition
     permutes positions but preserves symbol identities, so a transposed English
     page keeps English's rune distribution (small chi^2). A flattened page does not.
  4. Bigram distribution      -> adjacency structure. Top digraphs per page, plus a
     chi^2 'dependence' z-score comparing observed adjacent-pair counts to the
     independence model E[ab]=n_a*n_b/N. English couples neighbours strongly
     (large +z, e.g. TH/HE); a polyalphabetic/keystream cipher decouples them (~0).
  5. Entropy (H1, conditional H2) in bits -> redundancy, calibrated against the
     29-symbol maximum log2(29)=4.858 bits.

Controls: 0_loss_of_divinity (plaintext English) and p56_an_end (solved keystream)
are included so each probe can be read against a known-positive and a known-hard page.
"""
import os, glob, collections, math, random

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT = ["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B",
       "E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
idx = {r: i for i, r in enumerate(RUNES)}
base = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
C = 29
random.seed(3301)

def load(name):
    return [idx[c] for c in open(os.path.join(base, name), encoding="utf-8").read() if c in idx]

def ioc(s):
    n = len(s)
    if n < 2: return 0.0
    c = collections.Counter(s)
    return sum(v * (v - 1) for v in c.values()) / (n * (n - 1))

# ---- English-rune reference distribution from the solved plaintext corpus ----
ref = collections.Counter()
refbg = collections.Counter()
for fn in glob.glob(os.path.join(base, "solved_*.txt")):
    seq = [idx[c] for c in open(fn, encoding="utf-8").read() if c in idx]
    ref.update(seq)
    refbg.update((seq[i], seq[i + 1]) for i in range(len(seq) - 1))
reftot = sum(ref.values())
p_eng = [(ref.get(i, 0) + 1) / (reftot + C) for i in range(C)]   # +1 smoothed

# ---- 1. periodic (Friedman) IoC ----
def periodic_ioc(s, maxd=40):
    best = (1, ioc(s))
    for d in range(1, min(maxd, len(s) // 4) + 1):
        cols = [s[j::d] for j in range(d)]
        m = sum(ioc(col) * len(col) for col in cols) / len(s)   # length-weighted mean column IoC
        if m > best[1]:
            best = (d, m)
    return best   # (period, best mean column IoC)

# ---- 2. isomorph test ----
def iso_pattern(window):
    seen = {}; pat = []
    for x in window:
        if x not in seen: seen[x] = len(seen)
        pat.append(seen[x])
    return tuple(pat)

def iso_excess(s, L):
    """excess = sum over non-trivial patterns of (count-1); i.e. #repeated isomorphs."""
    pats = collections.Counter()
    for i in range(len(s) - L + 1):
        w = s[i:i + L]
        if len(set(w)) < L:                 # non-trivial: has a repeated symbol
            pats[iso_pattern(w)] += 1
    return sum(k - 1 for k in pats.values() if k >= 2)

def iso_z(s, L, trials=200):
    obs = iso_excess(s, L)
    sym = list(s); samp = []
    for _ in range(trials):
        random.shuffle(sym)
        samp.append(iso_excess(sym, L))
    mu = sum(samp) / len(samp)
    sd = (sum((x - mu) ** 2 for x in samp) / len(samp)) ** 0.5 or 1e-9
    return obs, mu, (obs - mu) / sd

# ---- 3. unigram chi^2 vs English ----
def chi2_english(s):
    n = len(s); c = collections.Counter(s)
    x = sum((c.get(i, 0) - p_eng[i] * n) ** 2 / (p_eng[i] * n) for i in range(C))
    return x, (x - 28) / math.sqrt(2 * 28)    # value, z-score (df=28)

# ---- 4. bigram distribution ----
def bigrams(s):
    return collections.Counter((s[i], s[i + 1]) for i in range(len(s) - 1))

def bg_dependence_z(s):
    """chi^2 of adjacent pairs vs the independence model E[ab]=n_a*n_b/N, as a z-score."""
    n = len(s); nb = n - 1
    c = collections.Counter(s); bg = bigrams(s)
    x = 0.0
    for a in range(C):
        for b in range(C):
            e = c.get(a, 0) * c.get(b, 0) / n * (nb / n)
            if e <= 0: continue
            o = bg.get((a, b), 0)
            x += (o - e) ** 2 / e
    df = (C - 1) ** 2
    return (x - df) / math.sqrt(2 * df)

def top_bigrams(bg, k=8):
    return [(LAT[a] + LAT[b], v) for (a, b), v in bg.most_common(k)]

# ---- 5. entropy ----
def entropy(s):
    n = len(s); c = collections.Counter(s)
    h1 = -sum((v / n) * math.log2(v / n) for v in c.values())
    bg = bigrams(s); nb = n - 1
    hpair = -sum((v / nb) * math.log2(v / nb) for v in bg.values())
    return h1, hpair - h1    # H1, conditional H2 = H(pair)-H(single)

# ---- 6. doublets + first-difference (delta) distribution ----
# The one place the unsolved corpus is NOT flat (noted by the CicadaSolvers community /
# uncovering-cicada wiki): adjacent identical runes occur far less often than chance.
def doublets(s):
    nb = len(s) - 1
    d = sum(1 for i in range(nb) if s[i] == s[i + 1])
    p = 1 / C
    z = (d - nb * p) / math.sqrt(nb * p * (1 - p))
    return d, nb, d / nb, z           # count, pairs, rate, binomial z

def delta_chi2(s):
    """nonzero first-differences (s[i+1]-s[i]) mod C should be uniform on 1..28 if the
    step is independent of position; returns a chi^2 z-score over deltas 1..28."""
    nz = [(s[i + 1] - s[i]) % C for i in range(len(s) - 1)]
    nz = [d for d in nz if d != 0]
    n = len(nz); exp = n / (C - 1); c = collections.Counter(nz)
    x = sum((c.get(k, 0) - exp) ** 2 / exp for k in range(1, C))
    df = C - 2
    return (x - df) / math.sqrt(2 * df)

pages = ["p0-2", "p3-7", "p8-14", "p15-22", "p23-26", "p27-32", "p33-39", "p40-53",
         "p54-55", "0_loss_of_divinity", "p56_an_end"]

print("English-rune reference built from solved corpus:", reftot, "runes")
print("solved-corpus top bigrams:",
      ", ".join(f"{g}:{v}" for g, v in top_bigrams(refbg, 8)), "\n")

print(f"{'page':<18}{'N':>5}{'perIoC':>9}{'(d)':>5}"
      f"{'isoL6 z':>9}{'chi2Eng z':>11}{'bgDep z':>9}{'H1':>7}{'Hcond':>7}")
print("-" * 90)
rows = {}
for p in pages:
    s = load(p + ".txt"); n = len(s)
    d, pio = periodic_ioc(s)
    _, _, z6 = iso_z(s, 6)
    _, cz = chi2_english(s)
    bz = bg_dependence_z(s)
    h1, hc = entropy(s)
    rows[p] = bigrams(s)
    print(f"{p:<18}{n:>5}{pio:>9.4f}{d:>5}{z6:>9.1f}{cz:>11.1f}{bz:>9.1f}{h1:>7.2f}{hc:>7.2f}")

print("\n=== top bigrams per page (Latin digraphs) ===")
for p in pages:
    print(f"{p:<18} " + "  ".join(f"{g}:{v}" for g, v in top_bigrams(rows[p], 8)))

# ---- doublets + delta uniformity (the one non-flat signal) ----
print("\n=== doublets (adjacent identical runes) + first-difference uniformity ===")
print(f"{'page':<18}{'N':>5}{'doublets':>9}{'rate%':>8}{'exp%':>7}{'binom z':>9}{'deltaChi2 z':>12}")
print("-" * 70)
unsolved = ["p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p40-53","p54-55"]
pool = []
for p in unsolved + ["0_loss_of_divinity", "p56_an_end"]:
    s = load(p + ".txt")
    if p in unsolved: pool += s + [None]      # None breaks cross-page adjacency
    d, nb, rate, z = doublets(s); dz = delta_chi2(s)
    print(f"{p:<18}{len(s):>5}{d:>9}{rate*100:>7.2f}{100/C:>7.2f}{z:>9.1f}{dz:>12.1f}")
# pooled over the unsolved corpus (break adjacency between pages)
runs = []; cur = []
for x in pool:
    if x is None:
        if len(cur) > 1: runs.append(cur)
        cur = []
    else: cur.append(x)
if len(cur) > 1: runs.append(cur)
D = sum(sum(1 for i in range(len(r)-1) if r[i]==r[i+1]) for r in runs)
NB = sum(len(r)-1 for r in runs)
pexp = NB / C
zz = (D - pexp) / math.sqrt(pexp * (1 - 1/C))
print("-" * 70)
print(f"{'UNSOLVED POOLED':<18}{sum(len(r) for r in runs):>5}{D:>9}{D/NB*100:>7.2f}{100/C:>7.2f}{zz:>9.1f}")
print(f"  observed {D} doublets vs {pexp:.0f} expected  ({D/NB*100:.2f}% vs {100/C:.2f}%)")

print(f"\nmax entropy (log2 29) = {math.log2(C):.3f} bits")
print("Reading:")
print("  perIoC  ~0.034 at every d  => no repeating Vigenere key (jump to ~0.06 would reveal period d)")
print("  isoL6 z ~0                 => no homophonic-substitution isomorphs above chance")
print("  chi2Eng large +z           => distribution unlike English => not transposition/plaintext")
print("  bgDep z ~0                 => adjacent runes independent => no English-like digraph structure")
print("  H1 ~4.86, Hcond ~4.86      => near-maximal entropy, no exploitable redundancy")
