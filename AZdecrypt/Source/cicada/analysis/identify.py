#!/usr/bin/env python3
"""Identify the cipher *family* of the unsolved pages by fingerprint matching.

We cannot read the unsolved pages (Sections 4-5 show they are statistically opaque),
but we can ask which cipher, applied to *known English runes*, reproduces their
statistical fingerprint. We encipher the pooled solved-corpus plaintext under each
candidate family and measure the same five numbers used on the real pages:

    IoC            single-symbol index of coincidence      (random 1/29 = 0.0345)
    doublet%       adjacent identical runes                 (random 3.45%)
    periodic IoC   best mean column-IoC over periods 1..40  (reveals a repeating key)
    bigram-dep z   chi^2 of adjacent pairs vs independence  (English couples neighbours)
    delta0?        whether the zero first-difference (doublet) is present at chance

The observed unsolved fingerprint is: IoC 0.0343, doublet 0.66% (5x BELOW random),
no period, neighbours independent, nonzero deltas uniform. The family that matches on
every axis -- including the anomalous doublet suppression -- is the identification.
"""
import os, glob, collections, math, random

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
idx = {r: i for i, r in enumerate(RUNES)}
base = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
C = 29
random.seed(3301)

def ioc(s):
    n = len(s)
    if n < 2: return 0.0
    c = collections.Counter(s)
    return sum(v * (v - 1) for v in c.values()) / (n * (n - 1))

def doublet_rate(s):
    nb = len(s) - 1
    return sum(1 for i in range(nb) if s[i] == s[i + 1]) / nb

def periodic_ioc(s, maxd=40):
    best = ioc(s)
    for d in range(1, min(maxd, len(s) // 4) + 1):
        cols = [s[j::d] for j in range(d)]
        m = sum(ioc(col) * len(col) for col in cols) / len(s)
        best = max(best, m)
    return best

def bg_dep_z(s):
    n = len(s); nb = n - 1
    c = collections.Counter(s); bg = collections.Counter((s[i], s[i+1]) for i in range(nb))
    x = 0.0
    for a in range(C):
        for b in range(C):
            e = c.get(a, 0) * c.get(b, 0) / n * (nb / n)
            if e > 0: x += (bg.get((a, b), 0) - e) ** 2 / e
    df = (C - 1) ** 2
    return (x - df) / math.sqrt(2 * df)

# ---- pooled English-rune plaintext from the solved corpus ----
PT = []
for fn in glob.glob(os.path.join(base, "solved_*.txt")):
    PT += [idx[c] for c in open(fn, encoding="utf-8").read() if c in idx]
N = len(PT)

# ---- number-theoretic stream (totient of primes), as in 'An End' ----
LIM = 60000
sieve = [True] * (LIM + 1); sieve[0] = sieve[1] = False
for i in range(2, int(LIM ** .5) + 1):
    if sieve[i]:
        for j in range(i*i, LIM+1, i): sieve[j] = False
primes = [i for i in range(2, LIM+1) if sieve[i]]

def fp(s):
    return (ioc(s), doublet_rate(s) * 100, periodic_ioc(s), bg_dep_z(s))

# ---- cipher families applied to the English plaintext PT ----
def f_plain():          return PT[:]
def f_mono():
    perm = list(range(C)); random.shuffle(perm)
    return [perm[x] for x in PT]
def f_vigenere(L=10):
    k = [random.randrange(C) for _ in range(L)]
    return [(PT[i] + k[i % L]) % C for i in range(N)]
def f_runningkey():                      # English + English (two halves of the corpus)
    h = N // 2; P, K = PT[:h], PT[h:2*h]
    return [(P[i] + K[i]) % C for i in range(h)]
def f_numberstream():                    # P + phi(prime_n), the 'An End' construction
    return [(PT[i] + (primes[i] - 1)) % C for i in range(N)]
def f_otp():                             # P + uniform random (one-time pad)
    return [(PT[i] + random.randrange(C)) % C for i in range(N)]
def f_otp_nodup():                       # OTP-like but forced doublet-free (anti-doublet rule)
    out = []
    for i in range(N):
        c = (PT[i] + random.randrange(C)) % C
        if out and c == out[-1]: c = (c + 1 + random.randrange(C - 1)) % C
        out.append(c)
    return out

families = [
    ("plaintext (English)",      f_plain,        1),
    ("monoalphabetic sub",       f_mono,        30),
    ("Vigenere (period 10)",     f_vigenere,    30),
    ("running key (Eng+Eng)",    f_runningkey,  30),
    ("number stream (totient)",  f_numberstream, 1),
    ("one-time pad (uniform)",   f_otp,         30),
    ("stream + anti-doublet",    f_otp_nodup,   30),
]

def observed():
    pages = ["p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p40-53","p54-55"]
    iocs, drs, pers, bzs = [], [], [], []
    for p in pages:
        s = [idx[c] for c in open(os.path.join(base, p + ".txt"), encoding="utf-8").read() if c in idx]
        iocs.append(ioc(s)); drs.append(doublet_rate(s)*100)
        pers.append(periodic_ioc(s)); bzs.append(bg_dep_z(s))
    return (sum(iocs)/len(iocs), sum(drs)/len(drs), sum(pers)/len(pers), sum(bzs)/len(bzs))

print(f"English plaintext pooled from solved corpus: {N} runes\n")
print(f"{'cipher family':<26}{'IoC':>8}{'doublet%':>10}{'perIoC':>8}{'bgDep z':>9}")
print("-" * 61)
for name, fn, trials in families:
    acc = [0.0, 0.0, 0.0, 0.0]
    for _ in range(trials):
        f = fp(fn())
        for k in range(4): acc[k] += f[k]
    a = [v / trials for v in acc]
    print(f"{name:<26}{a[0]:>8.4f}{a[1]:>10.2f}{a[2]:>8.4f}{a[3]:>9.1f}")
print("-" * 61)
o = observed()
print(f"{'>> UNSOLVED (observed)':<26}{o[0]:>8.4f}{o[1]:>10.2f}{o[2]:>8.4f}{o[3]:>9.1f}")
print(f"\nrandom baselines: IoC {1/C:.4f}, doublet {100/C:.2f}%, perIoC ~{1/C:.4f}, bgDep z ~0")
print("Match the observed row against the families above on ALL four axes.")
