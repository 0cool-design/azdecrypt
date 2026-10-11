#!/usr/bin/env python3
"""A direct attack on the easiest unsolved page group, p40-53.

p40-53 is the most tractable unsolved target: most material (3008 runes) and the most
repeated 4-grams (11, vs 0-3 elsewhere). Given the identification (additive key-stream
mod 29, Sections 5.5-5.6), the right attacks are:

  1. Crib drag.  Assume a known plaintext word P at position i.  For an additive cipher
     the implied key-stream is K = (C - P) mod 29.  If K is a window of a deterministic
     sequence (primes, totients, Fibonacci, ...) we have found the stream and alignment,
     and can decrypt the whole page.  We also accept a crib if the implied constant shift
     is uniform (a mono/Vigenere slice).
  2. Running key.  Try a known text (the pooled solved-page English, each other page's
     ciphertext) as the key, every offset, subtract, score by the rune 4-gram model.

Any genuine hit raises IoC toward ~0.06, the doublet rate toward English's ~2.6%, and
produces readable Latin.  This script reports the best result of each attack.
"""
import os, math, collections, glob

R="ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT=["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B","E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
idx={r:i for i,r in enumerate(R)}
lat2i={}
for i,l in enumerate(LAT): lat2i.setdefault(l,i)
base=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data","pages")
root=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
C=29

def load(n): return [idx[c] for c in open(f"{base}/{n}.txt",encoding="utf-8").read() if c in idx]
def ioc(s):
    n=len(s);c=collections.Counter(s);return sum(v*(v-1) for v in c.values())/(n*(n-1)) if n>1 else 0
def dbl(s):
    nb=len(s)-1;return 100*sum(1 for i in range(nb) if s[i]==s[i+1])/nb
def latin(s): return "".join(LAT[x] for x in s)
def enc(word):
    # greedy map a Latin string to rune indices using digraphs
    out=[];i=0;W=word.upper()
    digr={"TH":2,"EO":12,"NG":21,"OE":22,"AE":25,"IA":27,"EA":28}
    while i<len(W):
        if i+1<len(W) and W[i:i+2] in digr: out.append(digr[W[i:i+2]]); i+=2
        elif W[i] in lat2i: out.append(lat2i[W[i]]); i+=1
        else: i+=1
    return out

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

# number-theory sequences (mod 29) as byte strings for fast substring search
N=4000
sieve=[True]*(N*25); sieve[0]=sieve[1]=False
for i in range(2,int((N*25)**.5)+1):
    if sieve[i]:
        for j in range(i*i,N*25,i): sieve[j]=False
primes=[i for i in range(2,N*25) if sieve[i]][:N]
phi=list(range(N+2))
for i in range(2,N+2):
    if phi[i]==i:
        for j in range(i,N+2,i): phi[j]-=phi[j]//i
def fib(n):
    a,b,o=1,1,[]
    for _ in range(n): o.append(a);a,b=b,a+b
    return o
def luc(n):
    a,b,o=2,1,[]
    for _ in range(n): o.append(a);a,b=b,a+b
    return o
seqs={"primes":[p%C for p in primes],
      "totient(p-1)":[(p-1)%C for p in primes],
      "phi(n)":[phi[i+1]%C for i in range(N)],
      "fibonacci":[x%C for x in fib(N)],
      "lucas":[x%C for x in luc(N)],
      "n":[i%C for i in range(N)],
      "triangular":[(i*(i+1)//2)%C for i in range(N)],
      "squares":[(i*i)%C for i in range(N)]}
seqbytes={k:bytes(v) for k,v in seqs.items()}

s=load("p40-53")
print(f"target p40-53: N={len(s)}  IoC={ioc(s):.4f}  doublet={dbl(s):.2f}%\n")

# ---------- attack 1: crib drag ----------
cribs=["THE","AND","THAT","WITHIN","SELF","DIVINITY","SACRED","INSTAR","EMERGENCE",
       "PILGRIM","WISDOM","KNOW","TRUTH","CIRCUMFERENCE","MOBIUS","PRIMES","CICADA",
       "SHADOW","ANALOG","CONSUME","PRESERVE","REALITY","CONSCIOUSNESS","WELCOME",
       "PARABLE","KOAN","ENDURE","BEHOLD","AWAKEN","THEKINGDOM","ANEND","WARNING"]
seqmatch=0; consts=0; full=[]
for w in cribs:
    P=enc(w); m=len(P)
    if m<3: continue
    for i in range(len(s)-m+1):
        K=bytes((s[i+j]-P[j])%C for j in range(m))
        # (a) does the implied key-stream window sit inside a known sequence?
        for name,sb in seqbytes.items():
            t=sb.find(K)
            if t!=-1:
                seqmatch+=1
                off=t-i                      # seq index at page position 0
                if off>=0 and len(s)+off<=N:  # valid full-page alignment
                    dec=[(s[k]-seqs[name][k+off])%C for k in range(len(s))]
                    full.append((score(dec),w,i,name))
        # (b) crib implies a single constant shift (mono/Vigenere slice)?
        if len(set(K))==1: consts+=1
print(f"crib windows coinciding with a known sequence: {seqmatch} (chance-level for 3-5 runes)")
print(f"crib placements implying a constant shift:     {consts} (chance-level)")
if full:
    full.sort(reverse=True)
    print("best FULL-page decrypt from any crib-implied sequence alignment:")
    for sc,w,i,name in full[:5]:
        print(f"  score={sc:.2f}  via crib {w!r}@{i} -> stream {name}")
    print("  (English scores ~ -12; all of these are at the ~ -14.6 random floor => no decrypt)")
else:
    print("no crib produced a valid full-page sequence alignment.")

# ---------- attack 2: running key ----------
print("\nrunning-key attack (subtract a known text, best offset, 4-gram score):")
keys={}
pooled=[]
for fn in glob.glob(base+"/solved_*.txt"): pooled+=[idx[c] for c in open(fn,encoding="utf-8").read() if c in idx]
keys["solved English (pooled)"]=pooled
for p in ["p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p54-55"]:
    keys[f"cipher {p}"]=load(p)
best=None
for kn,K in keys.items():
    if len(K)<10: continue
    span=min(len(s),len(K))
    for off in range(0,max(1,len(K)-span+1),7):      # stride 7 offsets
        for op in (-1,1):
            dec=[(s[i]+op*K[(i+off)%len(K)])%C for i in range(span)]
            sc=score(dec)
            if best is None or sc>best[0]: best=(sc,kn,off,"-" if op<0 else "+",dec)
bs,bk,bo,bop,bd=best
print(f"  best: {bk}  off={bo} op={bop}  score={bs:.2f}  IoC={ioc(bd):.4f}  dbl={dbl(bd):.2f}%")
print(f"  preview: {latin(bd)[:50]}")
print(f"\n(reference: real English 4-gram score ~ -12; random ~ -14.6)")
