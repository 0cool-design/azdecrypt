#!/usr/bin/env python3
import glob, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import _theme
from _theme import INK, BLUE, TEAL, DEEP, SAND, ORANGE, RED, SLATE, GRID
_theme.apply()

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT = ["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B",
       "E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
idx = {r:i for i,r in enumerate(RUNES)}
SEP = set("•⁘⁚⁖⁜\n")
base = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
out  = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/assets"
os.makedirs(out, exist_ok=True)

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
fig,ax=plt.subplots(figsize=(11,4.6))
ax.bar(range(len(labels)),pct,color=TEAL,edgecolor=INK,linewidth=.5,zorder=3)
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
ax.set_ylabel("frequency (%)"); ax.set_xlabel("Gematria Primus rune (Latin reading)")
ax.grid(axis="x"); ax.set_axisbelow(True)
_theme.titled(ax,"Solved corpus: rune frequency",
              f"{N} runes across 9 pages — E dominates, matching English")
ax.margins(x=0.01)
fig.savefig(out+"/freq_letters.png"); plt.close(fig)

# ---- 2. top words ----
wc=collections.Counter(words).most_common(18)
ws=[w for w,_ in wc][::-1]; wv=[c for _,c in wc][::-1]
fig,ax=plt.subplots(figsize=(8,5.4))
ax.barh(range(len(ws)),wv,color=DEEP,edgecolor=INK,linewidth=.5,zorder=3)
ax.set_yticks(range(len(ws))); ax.set_yticklabels(ws)
ax.set_xlabel("count"); ax.grid(axis="y")
_theme.titled(ax,"Solved corpus: most common words",
              "the English function-word skeleton (THE, TO, YOU, IS, WE …)")
for i,v in enumerate(wv): ax.text(v+0.3,i,str(v),va="center",fontsize=8.5,color=SLATE)
ax.margins(y=0.01)
fig.savefig(out+"/freq_words.png"); plt.close(fig)

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
rows.sort()
ics=[r[0] for r in rows]; names=[r[1] for r in rows]; solved=[r[2] for r in rows]
def color(ic):
    return TEAL if ic>0.055 else SAND if ic>0.045 else ORANGE if ic>0.038 else RED
cols=[color(x) for x in ics]
fig,ax=plt.subplots(figsize=(11,5.8))
ax.barh(range(len(names)),ics,color=cols,edgecolor=INK,linewidth=.5,zorder=3)
ax.set_yticks(range(len(names)))
ax.set_yticklabels([f"{n}{'  ★' if sv else ''}" for n,sv in zip(names,solved)])
ax.grid(axis="y"); ax.set_axisbelow(True)
# reference lines, labelled in a clear band above the bars (no overlap)
top=len(names)
ax.set_ylim(-0.7, top+0.9)
for x,lab in [(1/29,"random  1/29"),(0.0667,"English (26-letter)")]:
    ax.axvline(x,color=SLATE,ls=(0,(4,3)),lw=1,zorder=2)
    ax.text(x,top+0.15,lab,ha="center",va="center",fontsize=8.5,color=SLATE,
            bbox=dict(boxstyle="round,pad=0.25",fc=_theme.CANVAS,ec=GRID,lw=.6))
ax.set_xlabel("Index of Coincidence   (higher = more structure = easier to attack)")
_theme.titled(ax,"Liber Primus pages ranked by predicted difficulty",
              "★ = solved. Every statistically flat page (red) is unsolved")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=TEAL,label="easy — monoalphabetic / plaintext"),
                   Patch(color=SAND,label="medium"),
                   Patch(color=ORANGE,label="hard — near-random"),
                   Patch(color=RED,label="hardest — flat / running-key")],
          loc="lower right")
fig.savefig(out+"/difficulty.png"); plt.close(fig)

print("wrote:", sorted(f for f in os.listdir(out) if f.endswith('.png')))
