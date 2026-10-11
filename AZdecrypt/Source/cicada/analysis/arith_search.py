#!/usr/bin/env python3
"""Exhaustive search for an arithmetic-progression key-stream.

Model: C_i = (P_i + a + i*d) mod 29  for an intercept a and common difference d.
This is a progressive (Trithemius-style) key.  It is worth a dedicated search for
two reasons:

  * It is the one additive stream whose doublet rate is *tunable*: for an arithmetic
    key the step K_{i+1}-K_i = d is constant, so a ciphertext doublet occurs exactly
    when the plaintext step P_{i+1}-P_i = -d.  Choosing d = the rarest English step
    would suppress doublets, which is the one anomaly the unsolved pages show.
  * Because 29 is prime, K_i = a + i*d has period 29 for any d != 0, so it also makes
    a concrete prediction the Friedman test (Section 5.3) can confirm or deny.

We brute-force all 29*29 = 841 (a, d) pairs per page (both cipher directions are
covered, since -a,-d are in range mod 29), score each decrypt by the rune 4-gram
model, and report the best.  A planted-key control validates the search.
"""
import os, glob, math, collections

R="ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT=["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B","E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
idx={r:i for i,r in enumerate(R)}
base="/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
root="/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data"
C=29

def load(n): return [idx[c] for c in open(f"{base}/{n}.txt",encoding="utf-8").read() if c in idx]
def ioc(s):
    n=len(s);c=collections.Counter(s);return sum(v*(v-1) for v in c.values())/(n*(n-1)) if n>1 else 0
def dbl(s):
    nb=len(s)-1;return 100*sum(1 for i in range(nb) if s[i]==s[i+1])/nb
def latin(s): return "".join(LAT[x] for x in s)

# 4-gram model
cnt={};tot=0
for line in open(root+"/rune-4gram.txt",encoding="utf-8"):
    line=line.rstrip("\n")
    if not line: continue
    sp=line.rfind(" ");t=tuple(idx[ch] for ch in line[:sp] if ch in idx)
    if len(t)==4: v=float(line[sp+1:]);cnt[t]=cnt.get(t,0)+v;tot+=v
floor=math.log(1/(tot+C**4));logp={k:math.log((v+1)/(tot+C**4)) for k,v in cnt.items()}
def score(s):
    if len(s)<4: return -1e9
    return sum(logp.get((s[i],s[i+1],s[i+2],s[i+3]),floor) for i in range(len(s)-3))/(len(s)-3)

def search_arith(c):
    best=None
    n=len(c)
    for d in range(C):
        # precompute i*d mod C incrementally
        step=[(i*d)%C for i in range(n)]
        for a in range(C):
            dec=[(c[i]-a-step[i])%C for i in range(n)]
            sc=score(dec)
            if best is None or sc>best[0]: best=(sc,a,d,dec)
    return best

# ---- control: plant an arithmetic key on English and recover it ----
PT=[]
for fn in glob.glob(base+"/solved_*.txt"): PT+=load(os.path.basename(fn)[:-4])
A0,D0=7,11
ct=[(PT[i]+A0+i*D0)%C for i in range(len(PT))]
bsc,ba,bd,bdec=search_arith(ct)
print(f"CONTROL  planted (a={A0}, d={D0}) on English -> recovered (a={ba}, d={bd}) "
      f"score={bsc:.2f} IoC={ioc(bdec):.4f}")
print(f"         decrypt: {latin(bdec)[:48]}  (should read English)\n")

# ---- the unsolved pages ----
pages=["p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p40-53","p54-55"]
print(f"{'page':<10}{'best a':>7}{'best d':>7}{'score':>9}{'IoC':>8}{'dbl%':>7}  preview")
print("-"*92)
for p in pages:
    c=load(p); sc,a,d,dec=search_arith(c)
    print(f"{p:<10}{a:>7}{d:>7}{sc:>9.2f}{ioc(dec):>8.4f}{dbl(dec):>7.2f}  {latin(dec)[:32]}")
print("\nEnglish 4-gram score ~ -12; random ~ -14.6.  A real arithmetic key would give")
print("IoC ~0.06 and readable Latin, and would also spike the Friedman test at period 29.")
