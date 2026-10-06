#!/usr/bin/env python3
import glob, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT = ["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B",
       "E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
idx = {r:i for i,r in enumerate(RUNES)}
SEP = set("•⁘⁚⁖⁜\n")
base = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
out  = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/assets"
os.makedirs(out, exist_ok=True)

INK="#1b2a4a"; BLUE="#3b6ea5"; GREEN="#4a9b5e"; AMBER="#d99a2b"; RED="#c0493b"
plt.rcParams.update({"font.size":11,"axes.edgecolor":"#888","axes.grid":True,
                     "grid.alpha":0.25,"figure.dpi":130})

# ---- gather solved corpus ----
seq=[]; words=[]
for fn in sorted(glob.glob(base+"/solved_*.txt")):
    cur=""
    for ch in open(fn,encoding="utf-8").read():
        if ch in idx: seq.append(idx[ch]); cur+=LAT[idx[ch]]
        elif ch in SEP:
            if cur: words.append(cur); cur=""
    if cur: words.append(cur)
N=len(seq); cnt=collections.Counter(seq)

# ---- 1. letter/rune frequency ----
items=cnt.most_common()
labels=[LAT[i] for i,_ in items]; pct=[100*c/N for _,c in items]
fig,ax=plt.subplots(figsize=(11,4.5))
ax.bar(range(len(labels)),pct,color=BLUE,edgecolor=INK,linewidth=.6)
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
ax.set_ylabel("frequency (%)"); ax.set_xlabel("Gematria Primus rune (Latin reading)")
ax.set_title(f"Liber Primus solved corpus: rune frequency  (N={N} runes, 9 pages)")
ax.margins(x=0.01)
fig.tight_layout(); fig.savefig(out+"/freq_letters.png"); plt.close(fig)

# ---- 2. top words ----
wc=collections.Counter(words).most_common(18)
ws=[w for w,_ in wc][::-1]; wv=[c for _,c in wc][::-1]
fig,ax=plt.subplots(figsize=(8,5.2))
ax.barh(range(len(ws)),wv,color=GREEN,edgecolor=INK,linewidth=.6)
ax.set_yticks(range(len(ws))); ax.set_yticklabels(ws)
ax.set_xlabel("count"); ax.set_title("Solved corpus: most common words")
for i,v in enumerate(wv): ax.text(v+0.3,i,str(v),va="center",fontsize=9)
fig.tight_layout(); fig.savefig(out+"/freq_words.png"); plt.close(fig)

# ---- 3. difficulty by IoC ----
SOLVED={"0_warning","0_welcome","0_wisdom","0_koan_1","0_loss_of_divinity",
        "p56_an_end","p57_parable","jpg107-167","jpg229"}
rows=[]
for fn in sorted(glob.glob(base+"/*.txt")):
    name=os.path.basename(fn)[:-4]
    if name.startswith("solved_") or name=="README": continue
    s=[idx[c] for c in open(fn,encoding="utf-8").read() if c in idx]
    if len(s)<10: continue
    c=collections.Counter(s); n=len(s)
    ic=sum(v*(v-1) for v in c.values())/(n*(n-1))
    rows.append((ic,name,name in SOLVED))
rows.sort()  # hardest (low IoC) first -> we plot ascending so easiest on right
ics=[r[0] for r in rows]; names=[r[1] for r in rows]; solved=[r[2] for r in rows]
def color(ic):
    return GREEN if ic>0.055 else AMBER if ic>0.045 else "#cf7d2b" if ic>0.038 else RED
cols=[color(x) for x in ics]
fig,ax=plt.subplots(figsize=(11,5.5))
bars=ax.barh(range(len(names)),ics,color=cols,edgecolor=INK,linewidth=.6)
ax.set_yticks(range(len(names)))
ax.set_yticklabels([f"{n}{'  *' if sv else ''}" for n,sv in zip(names,solved)])
ax.axvline(1/29,color="#444",ls="--",lw=1); ax.text(1/29,len(names)-0.5,"  random (1/29)",color="#444",fontsize=8,va="top")
ax.axvline(0.0667,color="#444",ls=":",lw=1); ax.text(0.0667,len(names)-0.5,"  English-26",color="#444",fontsize=8,va="top")
ax.set_xlabel("Index of Coincidence  (higher = more structure = easier to attack)")
ax.set_title("Liber Primus pages ranked by predicted difficulty   (* = solved)")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=GREEN,label="easy (monoalphabetic/plaintext)"),
                   Patch(color=AMBER,label="medium"),
                   Patch(color="#cf7d2b",label="hard (near-random)"),
                   Patch(color=RED,label="hardest (flat / running-key)")],
          loc="lower right",fontsize=8,framealpha=.9)
fig.tight_layout(); fig.savefig(out+"/difficulty.png"); plt.close(fig)

print("wrote:",os.listdir(out))
