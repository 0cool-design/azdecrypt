#!/usr/bin/env python3
"""Number-theoretic keystream search.
Tries a library of deterministic integer sequences (mod 29) as keystreams against
each page, both subtract (decrypt) and add, over small offsets, scored by a rune
4-gram model. Includes totient-of-primes as a positive control: it must recover
'An End'. Flags any page whose best decrypt looks like English."""
import glob, os, collections, math

RUNES="ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT=["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B",
     "E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
idx={r:i for i,r in enumerate(RUNES)}
base="/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
C=29
MAXN=3200

def load(name):
    return [idx[c] for c in open(os.path.join(base,name),encoding="utf-8").read() if c in idx]
def ioc(s):
    n=len(s); c=collections.Counter(s)
    return sum(v*(v-1) for v in c.values())/(n*(n-1)) if n>1 else 0
def latin(s): return "".join(LAT[x] for x in s)

# ---- rune 4-gram model ----
print("loading 4-gram model ...", flush=True)
cnt={}; tot=0
for line in open(base+"/../rune-4gram.txt",encoding="utf-8"):
    line=line.rstrip("\n")
    if not line: continue
    sp=line.rfind(" ")
    runes=line[:sp]; c=float(line[sp+1:])
    t=tuple(idx[ch] for ch in runes if ch in idx)
    if len(t)==4: cnt[t]=cnt.get(t,0)+c; tot+=c
V=C**4
floor=math.log(1.0/(tot+V))
logp={k:math.log((v+1.0)/(tot+V)) for k,v in cnt.items()}
def score(s):
    if len(s)<4: return -1e9
    acc=0.0
    for i in range(len(s)-3):
        acc+=logp.get((s[i],s[i+1],s[i+2],s[i+3]),floor)
    return acc/(len(s)-3)         # avg log-prob per window (higher = more English)

# ---- number theory ----
LIM=40000
sieve=[True]*(LIM+1); sieve[0]=sieve[1]=False
for i in range(2,int(LIM**.5)+1):
    if sieve[i]:
        for j in range(i*i,LIM+1,i): sieve[j]=False
primes=[i for i in range(2,LIM+1) if sieve[i]][:MAXN+10]
# totient, mobius, tau, sigma via sieve
phi=list(range(MAXN+10)); mu=[1]*(MAXN+10); tau=[0]*(MAXN+10); sig=[0]*(MAXN+10)
for i in range(2,MAXN+10):
    if phi[i]==i:  # i prime
        for j in range(i,MAXN+10,i):
            phi[j]-=phi[j]//i
for i in range(1,MAXN+10):
    for j in range(i,MAXN+10,i):
        tau[j]+=1; sig[j]+=i
# mobius
mu=[0]*(MAXN+10); mu[1]=1
primelist=[p for p in range(2,MAXN+10) if phi[p]==p-1]
for p in primelist:
    for j in range(p,MAXN+10,p): mu[j]-= mu[j//p] if False else 0
# simpler mobius
mu=[1]*(MAXN+10)
isprime=[True]*(MAXN+10)
for i in range(2,MAXN+10):
    if isprime[i]:
        for j in range(i,MAXN+10,i):
            if j>i: isprime[j]=False
            mu[j]*=-1
        ii=i*i
        for j in range(ii,MAXN+10,ii): mu[j]=0
def fib():
    a,b=1,1
    while True: yield a; a,b=b,a+b
def lucas():
    a,b=2,1
    while True: yield a; a,b=b,a+b
def take(g,n):
    out=[];
    for _ in range(n): out.append(next(g))
    return out

def seqs():
    yield "primes",           [primes[i] for i in range(MAXN)]
    yield "totient(primes)",  [primes[i]-1 for i in range(MAXN)]   # == phi(prime)
    yield "primes+1",         [primes[i]+1 for i in range(MAXN)]
    yield "totient(n)",       [phi[i+1] for i in range(MAXN)]
    yield "mobius(n)",        [mu[i+1] for i in range(MAXN)]
    yield "tau(n)",           [tau[i+1] for i in range(MAXN)]
    yield "sigma(n)",         [sig[i+1] for i in range(MAXN)]
    yield "fibonacci",        take(fib(),MAXN)
    yield "lucas",            take(lucas(),MAXN)
    yield "triangular",       [i*(i+1)//2 for i in range(1,MAXN+1)]
    yield "squares",          [i*i for i in range(1,MAXN+1)]
    yield "n (trithemius)",   [i for i in range(MAXN)]
    yield "prime_gaps",       [primes[i+1]-primes[i] for i in range(MAXN)]
    yield "thue_morse",       [bin(i).count("1")%2 for i in range(MAXN)]

PI="31415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679"*40
seqs_list=list(seqs())
seqs_list.append(("digits_of_pi",[int(ch) for ch in PI[:MAXN]]))

OFFS=[0,1,2,3]
def search(cipher):
    best=None
    for name,S in seqs_list:
        for off in OFFS:
            for op in (-1,+1):
                out=[(cipher[i]+op*(S[off+i]%C))%C for i in range(len(cipher))]
                sc=score(out)
                if best is None or sc>best[0]:
                    best=(sc,name,off,("-" if op<0 else "+"),out)
    return best

pages=["p56_an_end","p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p40-53","p54-55"]
print(f"\n{'page':<12}{'best stream':<18}{'off':>4}{'op':>3}{'score':>9}{'IoC':>8}   preview")
print("-"*100)
for p in pages:
    c=load(p+".txt")
    sc,name,off,op,out=search(c)
    print(f"{p:<12}{name:<18}{off:>4}{op:>3}{sc:>9.3f}{ioc(out):>8.4f}   {latin(out)[:40]}")
print("\n(positive control: p56_an_end should recover 'AN END WITHIN THE DEEP WEB...' via totient(primes), op -)")
print("A genuine hit on an unsolved page = IoC jumping to ~0.06+ and readable Latin.")
