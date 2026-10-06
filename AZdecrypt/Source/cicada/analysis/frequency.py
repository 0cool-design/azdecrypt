#!/usr/bin/env python3
import glob, os, collections

RUNES = ["ᚠ","ᚢ","ᚦ","ᚩ","ᚱ","ᚳ","ᚷ","ᚹ","ᚻ","ᚾ","ᛁ","ᛄ","ᛇ","ᛈ","ᛉ","ᛋ","ᛏ","ᛒ",
         "ᛖ","ᛗ","ᛚ","ᛝ","ᛟ","ᛞ","ᚪ","ᚫ","ᚣ","ᛡ","ᛠ"]
LAT   = ["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B",
         "E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
PRIME = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,101,103,107,109]
idx = {r:i for i,r in enumerate(RUNES)}
SEP = {"•":" ","⁘":" ","⁚":" ","⁖":" ","⁜":" ","\n":" "}

base = "/home/Ocool/Cicada/azdecrypt/AZdecrypt/Source/cicada/data/pages"
files = sorted(glob.glob(os.path.join(base,"solved_*.txt")))

seq = []        # rune indices across all solved plaintext
words = []      # Latin words
for fn in files:
    txt = open(fn, encoding="utf-8").read()
    cur = ""
    for ch in txt:
        if ch in idx:
            seq.append(idx[ch]); cur += LAT[idx[ch]]
        elif ch in SEP:
            if cur: words.append(cur); cur = ""
        # ignore digits/quotes/etc.
    if cur: words.append(cur)

N = len(seq)
print(f"solved pages analyzed : {len(files)}")
print(f"total runes           : {N}")
print(f"total words           : {len(words)}")

# Index of Coincidence (29-symbol)
cnt = collections.Counter(seq)
ic = sum(c*(c-1) for c in cnt.values())/(N*(N-1))
print(f"IoC (29-symbol)       : {ic:.4f}   (random 1/29={1/29:.4f}, English-26 ~0.0667)")

print("\n=== rune / letter frequency (top 29) ===")
print(f"{'rune':>4} {'lat':>3} {'prime':>5} {'count':>6} {'pct':>6}")
for i,c in cnt.most_common():
    print(f"{RUNES[i]:>4} {LAT[i]:>3} {PRIME[i]:>5} {c:>6} {100*c/N:>5.1f}%")

print("\n=== top 25 words ===")
wc = collections.Counter(words)
print(f"unique words: {len(wc)}")
for w,c in wc.most_common(25):
    print(f"  {c:>4}  {w}")

# crude letter-ish comparison: collapse digraph runes to show English-like ranking
print("\n=== most common runes vs typical English letters ===")
top = [LAT[i] for i,_ in cnt.most_common(8)]
print("  solved top-8 runes :", " ".join(top))
print("  English top-8       : E T A O I N S H R (approx)")
