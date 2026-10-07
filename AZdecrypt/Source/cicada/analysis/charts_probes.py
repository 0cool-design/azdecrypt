#!/usr/bin/env python3
"""Figures for the structure-probe / cipher-identification sections (5.3-5.6).

Renders four PNGs into ../assets/:
  doublets.png        observed vs expected doublet rate per page (the one non-flat signal)
  bigram_heatmap.png  29x29 adjacent-pair heatmaps: plaintext control vs an unsolved page
                      (the dark diagonal on the unsolved page IS the doublet suppression)
  fingerprint.png     cipher-family fingerprint heatmap: which family matches the observed row
  periodic_ioc.png    column-IoC vs period d: a repeating key spikes, the unsolved pages stay flat

Needs matplotlib + numpy.  Run with an interpreter that has them:  python analysis/charts_probes.py
"""
import os, glob, collections, math, random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT = ["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B",
       "E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
idx = {r: i for i, r in enumerate(RUNES)}
base = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
out = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/assets"
os.makedirs(out, exist_ok=True)
C = 29
random.seed(3301)

INK="#1b2a4a"; BLUE="#3b6ea5"; GREEN="#4a9b5e"; AMBER="#d99a2b"; RED="#c0493b"
plt.rcParams.update({"font.size":11,"axes.edgecolor":"#888","figure.dpi":130})

def load(name):
    return [idx[c] for c in open(os.path.join(base, name), encoding="utf-8").read() if c in idx]
def ioc(s):
    n=len(s); c=collections.Counter(s)
    return sum(v*(v-1) for v in c.values())/(n*(n-1)) if n>1 else 0.0
def doublet_pct(s):
    nb=len(s)-1
    return 100*sum(1 for i in range(nb) if s[i]==s[i+1])/nb
def col_ioc(s,d):
    return sum(ioc(s[j::d])*len(s[j::d]) for j in range(d))/len(s)
def periodic_curve(s,maxd=40):
    return [col_ioc(s,d) for d in range(1,maxd+1)]
def bigram_matrix(s):
    m=np.zeros((C,C))
    for i in range(len(s)-1): m[s[i],s[i+1]]+=1
    return m/m.sum()
def bg_dep_z(s):
    n=len(s); nb=n-1; c=collections.Counter(s)
    bg=collections.Counter((s[i],s[i+1]) for i in range(nb)); x=0.0
    for a in range(C):
        for b in range(C):
            e=c.get(a,0)*c.get(b,0)/n*(nb/n)
            if e>0: x+=(bg.get((a,b),0)-e)**2/e
    return (x-(C-1)**2)/math.sqrt(2*(C-1)**2)

UNSOLVED=["p0-2","p3-7","p8-14","p15-22","p23-26","p27-32","p33-39","p40-53","p54-55"]

# ======================================================================= 1. doublets
pages=UNSOLVED+["0_loss_of_divinity","p56_an_end"]
rates=[doublet_pct(load(p+".txt")) for p in pages]
labels=[p.replace("0_loss_of_divinity","Loss of Divinity\n(plaintext)").replace("p56_an_end","An End") for p in pages]
cols=[RED]*len(UNSOLVED)+[GREEN,AMBER]
fig,ax=plt.subplots(figsize=(11,4.8))
ax.bar(range(len(pages)),rates,color=cols,edgecolor=INK,linewidth=.6)
ax.axhline(100/C,color="#444",ls="--",lw=1.2)
ax.text(len(pages)-0.4,100/C+0.08,"expected by chance (3.45%)",color="#444",ha="right",fontsize=9)
ax.set_xticks(range(len(pages))); ax.set_xticklabels(labels,rotation=35,ha="right",fontsize=9)
ax.set_ylabel("doublet rate (%)  — adjacent identical runes")
ax.set_title("Doublet suppression: the one place the unsolved pages are NOT random")
ax.margins(x=0.01); ax.grid(axis="y",alpha=0.25)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=RED,label="unsolved (suppressed ~0.5-1%)"),
                   Patch(color=GREEN,label="plaintext control"),
                   Patch(color=AMBER,label="An End (additive stream)")],fontsize=8)
fig.tight_layout(); fig.savefig(out+"/doublets.png"); plt.close(fig)

# ======================================================================= 2. bigram heatmaps
pl=bigram_matrix(load("0_loss_of_divinity.txt"))
# pool the whole unsolved corpus (break adjacency between pages) for a clean diagonal
um=np.zeros((C,C))
for p in UNSOLVED:
    s=load(p+".txt")
    for i in range(len(s)-1): um[s[i],s[i+1]]+=1
un=um/um.sum()
# each panel on its OWN scale: plaintext by its 98th pct (shows English digraphs),
# unsolved at ~2x its uniform mean (makes the suppressed diagonal read as a dark line).
panels=[(pl,"plaintext control — Loss of Divinity",np.percentile(pl[pl>0],98)),
        (un,"unsolved corpus (pooled, 9 pages)",2*un[un>0].mean())]
fig,axes=plt.subplots(1,2,figsize=(13,6.2))
for ax,(m,title,vmax) in zip(axes,panels):
    im=ax.imshow(m,cmap="magma",vmin=0,vmax=vmax,aspect="equal")
    ax.set_xticks(range(C)); ax.set_xticklabels(LAT,fontsize=6,rotation=90)
    ax.set_yticks(range(C)); ax.set_yticklabels(LAT,fontsize=6)
    ax.set_title(title,fontsize=12); ax.set_xlabel("second rune"); ax.set_ylabel("first rune")
    fig.colorbar(im,ax=ax,fraction=0.046,pad=0.04)
fig.suptitle("Adjacent-pair (bigram) heatmaps (each panel on its own scale).  English lights up specific\n"
             "digraphs (THE, ER …); the unsolved corpus is uniform EXCEPT the dark diagonal — doublets suppressed.",
             fontsize=11)
fig.tight_layout(rect=[0,0,1,0.95]); fig.savefig(out+"/bigram_heatmap.png"); plt.close(fig)

# ======================================================================= 3. fingerprint heatmap
# plaintext source + number theory for simulated families
PT=[]
for fn in glob.glob(base+"/solved_*.txt"): PT+=[idx[c] for c in open(fn,encoding="utf-8").read() if c in idx]
LIM=60000; sieve=[True]*(LIM+1); sieve[0]=sieve[1]=False
for i in range(2,int(LIM**.5)+1):
    if sieve[i]:
        for j in range(i*i,LIM+1,i): sieve[j]=False
primes=[i for i in range(2,LIM+1) if sieve[i]]
def fp(s): return [ioc(s),doublet_pct(s),max(periodic_curve(s)),bg_dep_z(s)]
def sim(fn,trials):
    acc=np.zeros(4)
    for _ in range(trials): acc+=np.array(fp(fn()))
    return acc/trials
def f_plain():  return PT[:]
def f_mono():   perm=list(range(C)); random.shuffle(perm); return [perm[x] for x in PT]
def f_vig(L=10):k=[random.randrange(C) for _ in range(L)]; return [(PT[i]+k[i%L])%C for i in range(len(PT))]
def f_run():    h=len(PT)//2; return [(PT[i]+PT[h+i])%C for i in range(h)]
def f_num():    return [(PT[i]+(primes[i]-1))%C for i in range(len(PT))]
def f_otp():    return [(PT[i]+random.randrange(C))%C for i in range(len(PT))]
def f_nd():
    o=[]
    for i in range(len(PT)):
        c=(PT[i]+random.randrange(C))%C
        if o and c==o[-1]: c=(c+1+random.randrange(C-1))%C
        o.append(c)
    return o
fam=[("plaintext / monoalphabetic",f_mono,20),("Vigenère (period 10)",f_vig,20),
     ("running key (Eng+Eng)",f_run,20),("number stream (totient)",f_num,1),
     ("one-time pad (uniform)",f_otp,20),("stream + anti-doublet",f_nd,20)]
rows=[name for name,_,_ in fam]+["UNSOLVED (observed)"]
M=[sim(fn,t) for _,fn,t in fam]
obs=np.mean([fp(load(p+".txt")) for p in UNSOLVED],axis=0)
M.append(obs); M=np.array(M)
metrics=["IoC","doublet %","periodic IoC","|bigram dep. z|"]
raw=M.copy(); raw[:,3]=np.abs(raw[:,3])
norm=(raw-raw.min(0))/(raw.max(0)-raw.min(0)+1e-9)       # per-column 0..1 for colour
fig,ax=plt.subplots(figsize=(9,5.6))
im=ax.imshow(norm,cmap="RdYlGn_r",aspect="auto",vmin=0,vmax=1)
ax.set_xticks(range(4)); ax.set_xticklabels(metrics)
ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows)
ax.axhline(len(rows)-1.5,color=INK,lw=2)   # separate observed row
for i in range(len(rows)):
    for j in range(4):
        v=raw[i,j]; txt=f"{v:.3f}" if j in (0,2) else f"{v:.2f}"
        ax.text(j,i,txt,ha="center",va="center",fontsize=9,
                color="white" if norm[i,j]>0.6 or norm[i,j]<0.12 else "black")
ax.set_title("Cipher-family fingerprint (on known English runes) vs the observed pages\n"
             "green = close to the random/observed value, red = far",fontsize=10)
fig.tight_layout(); fig.savefig(out+"/fingerprint.png"); plt.close(fig)

# ======================================================================= 4. periodic IoC curves
ds=list(range(1,41))
fig,ax=plt.subplots(figsize=(10,4.8))
ax.plot(ds,periodic_curve(f_vig(10)),color=AMBER,marker="o",ms=3,label="Vigenère period 10 (simulated)")
ax.plot(ds,periodic_curve(load("0_loss_of_divinity.txt")),color=GREEN,marker="s",ms=3,label="plaintext control")
ax.plot(ds,periodic_curve(load("p40-53.txt")),color=RED,marker="^",ms=3,label="unsolved p40-53")
ax.axhline(1/C,color="#444",ls="--",lw=1); ax.text(40,1/C+0.001,"random 1/29",color="#444",ha="right",fontsize=8)
ax.set_xlabel("candidate key period  d"); ax.set_ylabel("mean column IoC")
ax.set_title("Friedman periodic-IoC test: a repeating key spikes at its period; the unsolved pages stay flat")
ax.legend(fontsize=9); ax.grid(alpha=0.25); ax.margins(x=0.01)
fig.tight_layout(); fig.savefig(out+"/periodic_ioc.png"); plt.close(fig)

print("wrote:", sorted(f for f in os.listdir(out) if f.endswith(".png")))
