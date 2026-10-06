#!/usr/bin/env python3
"""Structure-probe triage for Liber Primus pages.
For each page: IoC, chi-squared flatness, digraphic IoC, best autocorrelation
period (Kasiski-style), and zlib compressibility vs a random baseline.
A page that is 'more structured than random' on any probe is worth deeper attack."""
import glob, os, collections, zlib, random, math

RUNES="ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
idx={r:i for i,r in enumerate(RUNES)}
base="/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
C=29

def load(name):
    return [idx[c] for c in open(os.path.join(base,name),encoding="utf-8").read() if c in idx]

def ioc(s):
    n=len(s); c=collections.Counter(s)
    return sum(v*(v-1) for v in c.values())/(n*(n-1)) if n>1 else 0

def chi2_flat(s):
    n=len(s); exp=n/C; c=collections.Counter(s)
    x=sum((c.get(i,0)-exp)**2/exp for i in range(C))
    # normalize to a z-score: chi2 has mean dof=28, std=sqrt(2*28)
    return (x-28)/math.sqrt(2*28)

def digraphic_ioc(s):
    bg=[ (s[i],s[i+1]) for i in range(len(s)-1)]
    n=len(bg); c=collections.Counter(bg)
    rand=1/(C*C)
    val=sum(v*(v-1) for v in c.values())/(n*(n-1)) if n>1 else 0
    return val, val/rand  # ratio: 1.0 == random

def best_period(s,maxd=60):
    n=len(s); best=(0,0)
    exp=1/C
    for d in range(1,min(maxd,n//2)):
        m=sum(1 for i in range(n-d) if s[i]==s[i+d])/(n-d)
        z=(m-exp)/math.sqrt(exp*(1-exp)/(n-d))
        if z>best[1]: best=(d,z)
    return best  # (period, z-score of coincidence spike)

def compress_ratio(s):
    b=bytes(s)
    cr=len(zlib.compress(b,9))/len(b)
    # random baseline of same length/alphabet
    rnd=bytes(random.randrange(C) for _ in range(len(s)))
    rr=len(zlib.compress(rnd,9))/len(rnd)
    return cr, cr/rr  # <1.0 means more compressible than random

pages=["p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p40-53","p54-55",
       "0_loss_of_divinity","p56_an_end"]
print(f"{'page':<18}{'N':>5}{'IoC':>8}{'chi2z':>7}{'digrIoC(x)':>11}{'bestPer(z)':>14}{'compVSrand':>11}")
print("-"*80)
for p in pages:
    s=load(p+".txt"); n=len(s)
    di,dr=digraphic_ioc(s); per,pz=best_period(s); cr,crr=compress_ratio(s)
    print(f"{p:<18}{n:>5}{ioc(s):>8.4f}{chi2_flat(s):>7.1f}{dr:>10.2f}x  d={per:<3}z={pz:>4.1f}{crr:>10.2f}x")
print("\nReading: digrIoC≈1.0 and compVSrand≈1.0 => indistinguishable from random.")
print("A bestPer z-score >~4 would hint at a repeating period; chi2z>>0 => non-flat.")
