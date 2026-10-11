#!/usr/bin/env python3
"""Gematria of the solved verses: is each line's prime-sum itself prime?

Each Gematria Primus rune carries a prime value (2, 3, 5, … 109). For every line of
the solved (decrypted) pages we sum those prime values and test the total for
primality. Cicada's taste for primes makes this a natural structural probe: if the
verses were engineered to have prime gematria, the hit rate will sit far above the
chance level predicted by the prime-number theorem (about 1/ln(sum) per line).
"""
import os, glob, math, collections

RUNES = "ᚠᚢᚦᚩᚱᚳᚷᚹᚻᚾᛁᛄᛇᛈᛉᛋᛏᛒᛖᛗᛚᛝᛟᛞᚪᚫᚣᛡᛠ"
LAT = ["F","U","TH","O","R","C","G","W","H","N","I","J","EO","P","X","S","T","B",
       "E","M","L","NG","OE","D","A","AE","Y","IA","EA"]
PRIME = [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,101,103,107,109]
idx = {r:i for i,r in enumerate(RUNES)}
HERE = os.path.dirname(os.path.abspath(__file__))
base = os.path.join(HERE, "..", "data", "pages")

def is_prime(n):
    if n < 2: return False
    if n < 4: return True
    if n % 2 == 0: return False
    i = 3
    while i*i <= n:
        if n % i == 0: return False
        i += 2
    return True

def gematria(line):      # sum of prime values of the runes on a line
    return sum(PRIME[idx[c]] for c in line if c in idx)
def latin(line):
    return "".join(LAT[idx[c]] for c in line if c in idx)

files = sorted(glob.glob(os.path.join(base, "solved_*.txt")))
tot_lines = tot_prime = 0
exp_prime = 0.0
page_hits = []
print(f"{'page':<22}{'line':>4}{'gematria':>9}{'prime?':>7}  text")
print("-"*90)
for fn in files:
    name = os.path.basename(fn)[:-4].replace("solved_","")
    ph = pl = 0
    for li, raw in enumerate(open(fn, encoding="utf-8").read().splitlines(), 1):
        g = gematria(raw)
        if g == 0: continue
        pl += 1; tot_lines += 1
        p = is_prime(g); exp_prime += 1.0/math.log(g) if g > 2 else 0
        if p: ph += 1; tot_prime += 1
        print(f"{name:<22}{li:>4}{g:>9}{('PRIME' if p else '-'):>7}  {latin(raw)[:46]}")
    page_hits.append((name, ph, pl))

print("-"*90)
print("per page (prime lines / lines):")
for name, ph, pl in page_hits:
    print(f"  {name:<24}{ph:>3}/{pl:<3}")
print(f"\nTOTAL: {tot_prime}/{tot_lines} lines have a prime gematria "
      f"({100*tot_prime/tot_lines:.1f}%)")
print(f"Expected by chance (prime-number theorem): {exp_prime:.1f} lines "
      f"({100*exp_prime/tot_lines:.1f}%)")
ratio = tot_prime/exp_prime if exp_prime else 0
print(f"Observed / expected = {ratio:.2f}x  "
      f"({'above chance' if ratio>1.3 else 'consistent with chance'})")
