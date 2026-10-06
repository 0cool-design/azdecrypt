#!/usr/bin/env python3
import glob, os, collections

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
idx = {r:i for i,r in enumerate(RUNES)}
base = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"

# solved pages (known method) for reference labels
SOLVED = {"0_warning","0_welcome","0_wisdom","0_koan_1","0_loss_of_divinity",
          "p56_an_end","p57_parable","jpg107-167","jpg229"}

rows = []
for fn in sorted(glob.glob(os.path.join(base,"*.txt"))):
    name = os.path.basename(fn)[:-4]
    if name.startswith("solved_") or name=="README": continue
    seq = [idx[c] for c in open(fn,encoding="utf-8").read() if c in idx]
    N = len(seq)
    if N < 10: continue
    cnt = collections.Counter(seq)
    ic = sum(c*(c-1) for c in cnt.values())/(N*(N-1))
    # repeated 4-grams: a handle for cribs / periodic keys
    g4 = collections.Counter(tuple(seq[i:i+4]) for i in range(N-3))
    rep4 = sum(1 for v in g4.values() if v>1)
    rep4_frac = rep4/max(1,(N-3))
    # tractability score: structure (IoC above random) dominates; repeats help a bit
    struct = (ic - 1/29)            # >0 means structure survives
    score = struct*1000 + rep4_frac*50
    rows.append((score, name, N, ic, rep4, rep4_frac, name in SOLVED))

rows.sort(reverse=True)  # easiest (most tractable) first
print(f"{'rank':>4}  {'page':<18} {'runes':>5} {'IoC':>7} {'rep4grams':>9}  class")
print("-"*70)
for r,(score,name,N,ic,rep4,rf,solved) in enumerate(rows,1):
    if ic > 0.055:      cls = "EASY  (monoalphabetic / plaintext)"
    elif ic > 0.045:    cls = "MED   (some structure)"
    elif ic > 0.038:    cls = "HARD  (near-random, faint structure)"
    else:               cls = "HARDEST (flat = polyalphabetic/running-key)"
    tag = " [SOLVED]" if solved else ""
    print(f"{r:>4}  {name:<18} {N:>5} {ic:>7.4f} {rep4:>9}  {cls}{tag}")
