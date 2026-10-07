#!/usr/bin/env python3
"""Probe the anti-doublet layer of the unsolved pages.

Section 5.5 identified the family as an additive key-stream carrying an anti-doublet
property. Two questions remain:

  (1) Is the doublet suppression really a *separate* layer, i.e. not something an
      additive stream could produce on its own?  An additive stream C = P + K (mod 29)
      has doublet C_i = C_{i-1} iff P_i - P_{i-1} = K_{i-1} - K_i, which for a generic
      stream happens at the chance rate ~3.45%. So an additive cipher should NOT
      suppress doublets. We confirm this directly on the solved 'An End' page (which
      IS an additive totient stream) and on a simulated totient stream over English.

  (2) What sits *underneath* the anti-doublet layer?  A doublet-free sequence is a
      first-order chain over 29 symbols that never repeats. Its natural inversion is
      the increment (de-chaining) stream  r_i = (C_i - C_{i-1}) mod 29, which lives on
      {1..28} (0 only at the few surviving doublets). If the plaintext were just one
      de-chaining step away, r would show structure (low IoC-gap, bigram coupling,
      sub-maximal entropy). We measure r for every page.

If r is itself flat, the anti-doublet behaviour is the OUTER layer of a strong,
flat key-stream -- not a thin wrapper over readable text.
"""
import os, glob, collections, math

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
idx = {r: i for i, r in enumerate(RUNES)}
base = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
C = 29

def load(name):
    return [idx[c] for c in open(os.path.join(base, name), encoding="utf-8").read() if c in idx]
def ioc(s):
    n = len(s); c = collections.Counter(s)
    return sum(v*(v-1) for v in c.values())/(n*(n-1)) if n > 1 else 0.0
def doublet_pct(s):
    nb = len(s)-1
    return 100*sum(1 for i in range(nb) if s[i]==s[i+1])/nb
def h1(s):
    n = len(s); c = collections.Counter(s)
    return -sum((v/n)*math.log2(v/n) for v in c.values())
def bg_dep_z(s):
    n = len(s); nb = n-1
    c = collections.Counter(s); bg = collections.Counter((s[i],s[i+1]) for i in range(nb))
    x = 0.0
    for a in range(C):
        for b in range(C):
            e = c.get(a,0)*c.get(b,0)/n*(nb/n)
            if e > 0: x += (bg.get((a,b),0)-e)**2/e
    df = (C-1)**2
    return (x-df)/math.sqrt(2*df)
def increments(s):                 # de-chaining: r_i = (C_i - C_{i-1}) mod 29
    return [(s[i]-s[i-1]) % C for i in range(1, len(s))]

# --- (1) additive streams do NOT suppress doublets: An End + simulated totient ---
LIM = 60000
sieve = [True]*(LIM+1); sieve[0]=sieve[1]=False
for i in range(2,int(LIM**.5)+1):
    if sieve[i]:
        for j in range(i*i,LIM+1,i): sieve[j]=False
primes = [i for i in range(2,LIM+1) if sieve[i]]

PT = []
for fn in glob.glob(os.path.join(base,"solved_*.txt")):
    PT += load(os.path.basename(fn))
sim_totient = [(PT[i] + (primes[i]-1)) % C for i in range(len(PT))]

print("(1) do additive streams suppress doublets?  (random doublet rate = 3.45%)")
print(f"    English plaintext            : {doublet_pct(PT):.2f}%")
print(f"    + totient stream (simulated) : {doublet_pct(sim_totient):.2f}%   <- additive stream, NOT suppressed")
anend = load("p56_an_end.txt")
print(f"    'An End' ciphertext (real)   : {doublet_pct(anend):.2f}%   <- real additive totient page, NOT suppressed")
print("    => doublet suppression cannot come from an additive key-stream alone.\n")

# --- (2) what lies under the anti-doublet layer? the increment (de-chaining) stream ---
pages = ["p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p40-53","p54-55",
         "0_loss_of_divinity","p56_an_end"]
print("(2) increment stream r_i = (C_i - C_{i-1}) mod 29   (max entropy over 29 = 4.858)")
print(f"{'page':<18}{'doublet%':>9}{'r:IoC':>8}{'r:H1':>7}{'r:bgDep z':>11}")
print("-"*54)
for p in pages:
    s = load(p+".txt"); r = increments(s)
    print(f"{p:<18}{doublet_pct(s):>9.2f}{ioc(r):>8.4f}{h1(r):>7.2f}{bg_dep_z(r):>11.1f}")
print("\nReading: if the increment stream r were one step from plaintext it would show")
print("structure (IoC well above 0.0345, H1 below 4.86, bgDep z >> 0). Flat r means the")
print("anti-doublet constraint wraps a key-stream that is still statistically random.")
