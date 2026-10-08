#!/usr/bin/env python3
"""Test the Cicada 3301 'OS' prime list as a key-stream against the unsolved pages.

The prime_echo script in the gpg-signed Cicada 3301 OS emits the first 464 primes,
2 .. 3301 (3301 is the 464th prime).  Cicada's solved 'An End' page uses a running
totient-of-primes stream mod 29, so the natural question is whether this exact bounded
list, applied directly, deciphers any unsolved page.

For each page we try the list four ways (raw prime, totient p-1, p+1, prime index n),
reduced mod 29, added and subtracted, over small offsets, and in two modes:
  linear  S[off+i]                 (only covers pages <= 464 runes fully)
  cyclic  S[(off+i) % 464]         (a repeating prime key of period 464)
Each decrypt is scored by the rune 4-gram model; we also report its IoC and doublet
rate (a correct additive key should lift the decrypted doublet rate toward English's
~2.6% and raise IoC toward ~0.06).  'An End' is the positive control.
"""
import os, math, collections

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT = ["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B",
       "E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
idx = {r: i for i, r in enumerate(RUNES)}
base = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
root = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data"
C = 29

def load(name):
    return [idx[c] for c in open(os.path.join(base, name), encoding="utf-8").read() if c in idx]
def ioc(s):
    n=len(s); c=collections.Counter(s)
    return sum(v*(v-1) for v in c.values())/(n*(n-1)) if n>1 else 0.0
def doublet_pct(s):
    nb=len(s)-1
    return 100*sum(1 for i in range(nb) if s[i]==s[i+1])/nb
def latin(s): return "".join(LAT[x] for x in s)

# ---- Cicada OS primes ----
primes=[int(l) for l in open(os.path.join(root,"cicada_os_primes.txt"),encoding="utf-8")
        if l.strip() and not l.startswith("#")]
P=len(primes)
print(f"Cicada OS primes loaded: {P}  ({primes[0]} .. {primes[-1]})")

# ---- rune 4-gram model ----
cnt={}; tot=0
for line in open(root+"/rune-4gram.txt",encoding="utf-8"):
    line=line.rstrip("\n")
    if not line: continue
    sp=line.rfind(" ")
    t=tuple(idx[ch] for ch in line[:sp] if ch in idx)
    if len(t)==4: v=float(line[sp+1:]); cnt[t]=cnt.get(t,0)+v; tot+=v
floor=math.log(1.0/(tot+C**4))
logp={k:math.log((v+1.0)/(tot+C**4)) for k,v in cnt.items()}
def score(s):
    if len(s)<4: return -1e9
    return sum(logp.get((s[i],s[i+1],s[i+2],s[i+3]),floor) for i in range(len(s)-3))/(len(s)-3)

# ---- stream variants from the prime list ----
def variants():
    yield "prime",          [p % C for p in primes]
    yield "totient(p-1)",   [(p-1) % C for p in primes]
    yield "p+1",            [(p+1) % C for p in primes]
    yield "index n",        [(i+1) % C for i in range(P)]

OFFS=[0,1,2,3]
def search(cipher):
    best=None
    for name,S in variants():
        for mode in ("linear","cyclic"):
            if mode=="linear" and len(cipher) > P-max(OFFS): continue
            for off in OFFS:
                for op in (-1,+1):
                    if mode=="linear":
                        out=[(cipher[i]+op*S[off+i])%C for i in range(len(cipher))]
                    else:
                        out=[(cipher[i]+op*S[(off+i)%P])%C for i in range(len(cipher))]
                    sc=score(out)
                    if best is None or sc>best[0]:
                        best=(sc,name,mode,off,"-" if op<0 else "+",out)
    return best

pages=["p56_an_end","p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p40-53","p54-55"]
print(f"\n{'page':<12}{'stream':<14}{'mode':<8}{'off':>3}{'op':>3}{'score':>8}{'IoC':>8}{'dbl%':>7}  preview")
print("-"*100)
for p in pages:
    c=load(p+".txt")
    sc,name,mode,off,op,out=search(c)
    print(f"{p:<12}{name:<14}{mode:<8}{off:>3}{op:>3}{sc:>8.2f}{ioc(out):>8.4f}{doublet_pct(out):>7.2f}  {latin(out)[:34]}")
print("\ncontrol: p56_an_end should read AN END... via totient(p-1), subtract.")
print("a real hit on an unsolved page: IoC -> ~0.06, doublet% -> ~2.6, readable Latin.")
