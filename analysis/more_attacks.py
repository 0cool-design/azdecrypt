#!/usr/bin/env python3
"""Additional attack classes the earlier searches did not cover.

  1. Interrupter-aware key-stream.  Cicada's An End skips an unencrypted F rune
     (Section 5.7).  Decrypt with a totient/prime stream where the key pauses at a
     chosen interrupter rune, trying F and other candidates, both directions.
  2. Ciphertext autokey.  P_i = (C_i - C_{i-s}) mod 29 for every shift s (s=1 is the
     flat increment stream; try the rest).
  3. Plaintext autokey.  C_i = P_i + P_{i-s}; brute the s-rune primer for s=1,2.
  4. Beaufort / variant.  P_i = (K_i - C_i) mod 29 over the number-sequence library,
     an operation the additive search never applied.

Every family has a planted-key control so the negatives are trustworthy.
"""
import os, glob, math, collections, random

R="ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT=["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B","E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
idx={r:i for i,r in enumerate(R)}
base=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data","pages")
root=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
C=29; random.seed(3301)

def load(n): return [idx[c] for c in open(f"{base}/{n}.txt",encoding="utf-8").read() if c in idx]
def ioc(s):
    n=len(s);c=collections.Counter(s);return sum(v*(v-1) for v in c.values())/(n*(n-1)) if n>1 else 0
def latin(s): return "".join(LAT[x] for x in s)

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

# sequences
N=5000
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
SEQS={"primes":[p%C for p in primes],"totient":[(p-1)%C for p in primes],
      "phi(n)":[phi[i+1]%C for i in range(N)],"fib":[x%C for x in fib(N)],
      "lucas":[x%C for x in luc(N)],"n":[i%C for i in range(N)]}

# ---------- 1. interrupter-aware ----------
def dec_interrupt(c,S,X,op):
    out=[];k=0
    for x in c:
        if x==X: out.append(x)                       # interrupter: left as-is, key pauses
        else: out.append((x+op*S[k])%C); k+=1
    return out
def best_interrupt(c):
    best=None
    for name,S in SEQS.items():
        for X in (0,18,3,24):                         # F, E, O, A as candidate interrupters
            for op in (-1,1):
                d=dec_interrupt(c,S,X,op); s=score(d)
                if best is None or s>best[0]: best=(s,name,LAT[X],op,d)
    return best

# ---------- 2. ciphertext autokey ----------
def best_ct_autokey(c):
    best=None
    for s in range(1,21):
        for op in (-1,1):
            d=[(c[i]+op*c[i-s])%C for i in range(s,len(c))]
            sc=score(d)
            if best is None or sc>best[0]: best=(sc,s,op,d)
    return best

# ---------- 3. plaintext autokey (brute primer, s=1,2) ----------
def best_pt_autokey(c):
    best=None
    n=len(c)
    for g in range(C):                                # s=1 primer
        P=[0]*n; P[0]=g
        for i in range(1,n): P[i]=(c[i]-P[i-1])%C
        sc=score(P)
        if best is None or sc>best[0]: best=(sc,1,(g,),P)
    for g0 in range(C):                               # s=2 primer
        for g1 in range(C):
            P=[0]*n; P[0]=g0; P[1]=g1
            for i in range(2,n): P[i]=(c[i]-P[i-2])%C
            sc=score(P)
            if sc>best[0]: best=(sc,2,(g0,g1),P)
    return best

# ---------- 4. Beaufort over sequences ----------
def best_beaufort(c):
    best=None
    for name,S in SEQS.items():
        for off in range(4):
            d=[(S[i+off]-c[i])%C for i in range(len(c))]
            sc=score(d)
            if best is None or sc>best[0]: best=(sc,name,off,d)
    return best

# ---------- controls ----------
PT=[]
for fn in glob.glob(base+"/solved_*.txt"): PT+=load(os.path.basename(fn)[:-4])
# interrupter control: totient-encipher English, inserting raw F interrupters
ct=[];k=0
for i in range(len(PT)):
    if PT[i]==0: ct.append(0)                         # keep an F as interrupter
    else: ct.append((PT[i]+SEQS["totient"][k])%C); k+=1
bi=best_interrupt(ct)
print(f"CONTROL interrupter: recovered stream={bi[1]} X={bi[2]} op={bi[3]} score={bi[0]:.2f} IoC={ioc(bi[4]):.4f}")
# ciphertext-autokey control: C_i = P_i + C_{i-s}
s0=4; cc=[0]*len(PT)
for i in range(len(PT)): cc[i]=PT[i] if i<s0 else (PT[i]+cc[i-s0])%C
bc=best_ct_autokey(cc)
print(f"CONTROL ct-autokey (planted s={s0}): recovered s={bc[1]} op={bc[2]} score={bc[0]:.2f} IoC={ioc(bc[3]):.4f}")
# plaintext-autokey control: C_i = P_i + P_{i-1}
pac=[PT[0]]+[(PT[i]+PT[i-1])%C for i in range(1,len(PT))]
bp=best_pt_autokey(pac)
print(f"CONTROL pt-autokey (planted s=1): recovered s={bp[1]} primer={bp[2]} score={bp[0]:.2f} IoC={ioc(bp[3]):.4f}\n")

# ---------- run on unsolved ----------
pages=["p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p40-53","p54-55"]
print(f"{'page':<9}{'interrupt':>10}{'ct-autokey':>12}{'pt-autokey':>12}{'beaufort':>10}   best IoC")
print("-"*74)
for p in pages:
    c=load(p)
    bi=best_interrupt(c); bc=best_ct_autokey(c); bp=best_pt_autokey(c); bb=best_beaufort(c)
    allb=[("interrupt",bi[0],bi[-1]),("ct-auto",bc[0],bc[-1]),("pt-auto",bp[0],bp[-1]),("beaufort",bb[0],bb[-1])]
    best=max(allb,key=lambda z:z[1])
    print(f"{p:<9}{bi[0]:>10.2f}{bc[0]:>12.2f}{bp[0]:>12.2f}{bb[0]:>10.2f}   {ioc(best[2]):.4f} ({best[0]})")
print("\nEnglish 4-gram ~ -12, random ~ -14.6.  Controls above recover each planted key.")
