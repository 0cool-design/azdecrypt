# Reproducing and stress‑testing Liber Primus decryptions

*A small toolkit, the pages it can and cannot read, and a skeptic's audit of a popular "solution."*

---

## TL;DR

- I built a tiny, self‑contained toolkit (`cicada`) for Cicada 3301's **Liber Primus**: it
  transliterates the 29‑rune **Gematria Primus** alphabet and applies the cipher methods
  used on the solved pages (Atbash, Vigenère, totient/prime key‑streams), plus a
  statistical search harness.
- It **reproduces the known solves exactly**. The *A Warning* page (Atbash) and the
  *An End* page (totient) decrypt to clean English, and *The Loss of Divinity* turns out to
  be plaintext.
- Run systematically against the **unsolved** pages, it produces **nothing**, and the
  Index of Coincidence explains why: those pages are statistically flat (~0.034, i.e.
  random over 29 symbols), which rules out the whole class of attacks that cracked the
  easy pages.
- I also audited a widely shared "27×27 totient map" solution. **Its arithmetic is
  genuinely correct, but the arithmetic does not verify the decryption.** I explain the
  difference, and what *would* constitute proof.

Everything here is reproducible with the commands shown.

---

## 1. Background: Gematria Primus

The Liber Primus is written in a 29‑symbol runic alphabet. Each rune maps to a Latin
letter (or digraph) and to a prime number, in a fixed order (index 0–28):

| idx | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|-----|---|---|---|---|---|---|---|---|---|---|----|----|----|----|----|
| rune| ᚠ | ᚢ | ᚦ | ᚩ | ᚱ | ᚳ | ᚷ | ᚹ | ᚻ | ᚾ | ᛁ | ᛄ | ᛇ | ᛈ | ᛉ |
| lat | F | U | TH| O | R | C | G | W | H | N | I | J | EO | P | X |
| pri | 2 | 3 | 5 | 7 | 11| 13| 17| 19| 23| 29| 31 | 37 | 41 | 43 | 47 |

| idx | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 |
|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| rune| ᛋ | ᛏ | ᛒ | ᛖ | ᛗ | ᛚ | ᛝ | ᛟ | ᛞ | ᚪ | ᚫ | ᚣ | ᛡ | ᛠ |
| lat | S | T | B | E | M | L | NG | OE | D | A | AE | Y | IA | EA |
| pri | 53 | 59 | 61 | 67 | 71 | 73 | 79 | 83 | 89 | 97 | 101 | 103 | 107 | 109 |

Two facts matter throughout: several runes are **digraphs** (TH, EO, NG, OE, AE, IA, EA),
and several Latin letters are **ambiguous** (U/V, C/K, S/Z share a rune). This ambiguity is
a recurring source of false confidence, since it gives any decoder extra freedom.

Of ~74 pages, **17 were solved within months of release in 2014**; the remaining ~57 have
resisted the entire internet for over a decade.

---

## 2. The toolkit

`cicada` is a few hundred lines of C++ with no dependencies. It reads the same rune files
the community uses and offers:

```
cicada translit <file>     runes -> Latin (+ gematria sum)
cicada stats    <file>     rune frequencies + Index of Coincidence
cicada decode   <file> <atbash|caesar|vigenere|totient|primes> [args]
cicada vigcrack <file> ...  annealed Vigenère-key search (hypothesis tester)
cicada subsolve <file> ...  29-symbol substitution hillclimb (hypothesis tester)
cicada selftest / cracktest validation on known answers
```

It is **validated on known answers**: `selftest` reproduces the published *A Warning*
transliteration exactly, and `cracktest` encrypts known English‑in‑runes with a hidden key
and confirms the search recovers it. That matters: a search tool you can't trust on a
known case is worthless on an unknown one.

---

## 3. Reproducing the solved pages

### 3.1 *A Warning*: Atbash

The first page is the 29‑rune alphabet reversed (index → 28 − index):

```
cicada decode 0_warning.txt atbash
```
> A WARNING. BELIEVE NOTHING FROM THIS BOOK. EXCEPT WHAT YOU KNOW TO BE TRUE.
> TEST THE KNOWLEDGE. FIND YOUR TRUTH. EXPERIENCE YOUR DEATH. DO NOT EDIT OR
> CHANGE THIS BOOK, OR THE MESSAGE CONTAINED WITHIN, EITHER THE WORDS OR THEIR
> NUMBERS. FOR ALL IS SACRED.

(BOOC→BOOK, CNOW→KNOW, BELIEUE→BELIEVE from the C/K and U/V ambiguity.)

### 3.2 *An End* (p56): totient key‑stream

Here the key‑stream is φ(pₙ) = pₙ − 1 for the n‑th prime, mod 29, subtracted from the text:

```
cicada decode p56_an_end.txt totient
```
> AN END. WITHIN THE DEEP WEB, THERE EXISTS A PAGE THAT HASHES TO …

### 3.3 *The Loss of Divinity*: not a cipher at all

A good lesson in not assuming encryption. This page's Index of Coincidence is **0.0612**
(English‑level, not random), and the raw transliteration is already plain English:

```
cicada translit 0_loss_of_divinity.txt
```
> THE LOSS OF DIVINITY. THE CIRCUMFERENCE PRACTICES THREE BEHAVIOURS WHICH CAUSE
> THE LOSS OF DIVINITY. CONSUMPTION: WE CONSUME TOO MUCH … PRESERVATION … ADHERENCE …

There is nothing to "solve": it is a direct rune transliteration.

### 3.4 *Welcome*: Vigenère (key DIVINITY), with a caveat

Vigenère with key `DIVINITY` decrypts the opening correctly (`WELCO…`) and then drifts,
because the real page uses an **interrupter / skip rule** at specific documented indices
(the key pauses at certain ᚠ positions). Modelling *every* ᚠ as an interrupter is close but
not exact. It is a reminder that these pages hide small, deliberate structural rules.

---

## 4. The unsolved pages, and why IoC is the triage tool

### A quick primer on the Index of Coincidence

Not everyone has met this measure, so it is worth a paragraph. The **Index of Coincidence**
(IC or IoC), introduced by William F. Friedman in the 1920s, is the probability that two
symbols picked at random from a text are the same letter. You compute it from the symbol
counts `nᵢ` over an alphabet of size `c`, with `N` symbols total:

```
IC = Σ nᵢ(nᵢ − 1) / [ N(N − 1) ]
```

The useful property is that natural language is *lumpy*: a few letters (E, T, A …) are very
common, so two random draws land on the same letter more often than pure chance. The
reference values for the ordinary **26‑letter English** alphabet are:

| text | IC |
|------|----|
| English prose | **≈ 0.0667** (commonly quoted in the 0.0667–0.0686 range) |
| uniform random over 26 letters | 1/26 ≈ 0.0385 |

So English is almost **1.75×** as "coincidental" as random noise. That gap is what makes IC
a cheap, powerful first test.

Two caveats matter for the Liber Primus. First, the classic 0.0667 figure is specific to a
**26‑letter** alphabet; the Gematria Primus has **29 symbols**, which spreads the
probability thinner and lowers every baseline. For 29 symbols, uniform random is
1/29 ≈ **0.0345**, and real English written in the 29 runes measures lower than 0.0667 as
well (the plaintext *Loss of Divinity* page comes in at **0.0612**). Second, and crucially:
IC is **invariant under monoalphabetic ciphers** (Atbash, Caesar, simple substitution just
relabel the symbols, leaving the counts `nᵢ` untouched), but it **collapses toward the
random baseline under polyalphabetic or running‑key ciphers**, which smear each plaintext
letter across many ciphertext symbols. That single number therefore tells you *which family*
of cipher you are even allowed to hope for, before you spend a second of CPU.

### Running the full unsolved corpus

| page group | runes | IoC | periodic‑Vigenère + substitution search |
|------------|------:|-----:|:--|
| p0‑2   | 729  | 0.0341 | no English |
| p3‑7   | 1145 | 0.0346 | no English |
| p8‑14  | 1729 | 0.0345 | no English |
| p15‑22 | 1903 | 0.0345 | no English |
| p23‑26 | 1021 | 0.0343 | no English |
| p27‑32 | 1433 | 0.0342 | no English |
| p33‑39 | 1680 | 0.0344 | no English |
| p40‑53 | 3008 | 0.0345 | no English |
| p54‑55 | 308  | 0.0338 | no English |

**Every unsolved page sits on the random baseline.** That is a strong, honest signal: the
statistics are flat, so there is no periodic key or monoalphabetic mapping to recover. The
substitution hillclimber degenerates to smearing everything onto a couple of common runes
(`SSESSEE…`), the textbook failure mode on near‑random input, and the Vigenère search
returns gibberish at every key length.

This is not a weakness of the tool; it's the tool telling the truth. The solved pages used
*simple* ciphers and left *detectable* structure. The unsolved pages left none, consistent
with a non‑repeating key‑stream (or something stronger), exactly the class these attacks
cannot break, and exactly why no one has broken them.

---

## 5. A skeptic's audit of the "27×27 totient map" solution

A detailed and sincere reconstruction circulating online proposes that pages 0–2 (the first
729 runes = 27×27 grid) decrypt via a custom route (mirrored 3‑rune nodes, Euler‑totient
transforms, Möbius‑function phase selection, coordinate selectors, a "hidden value" rule)
to the text *"AS I GO, THE WEATHER TURNS COLD … THE IDEA OF THE END IS DEATH. SEE YOU
SOON,"* supported by striking numerology.

I checked the numbers independently. **They are all correct:**

| claim | verified |
|-------|:--------:|
| "AS I GO THE WEATHER TURNS COLD" = 21 runes, index‑sum 233 | ✅ |
| COLD = 51 (0‑based indices) | ✅ |
| 233 is the 51st prime | ✅ |
| Fibonacci F₇ = 13, F₁₃ = 233 | ✅ |
| φ(233) = 232 (the next block's sum) | ✅ |
| 2163 = 3 × 7 × 103 = U · O · Y (prime values) → "YOU" | ✅ |

So the arithmetic is real. **But correct arithmetic is not a verified decryption**, for
three concrete reasons:

1. **Degrees of freedom.** The method has many tunable choices: route selection through
   the grid, which 3‑rune nodes to use, mirrored vs non‑mirrored, phase selection,
   coordinate selectors, state roles, a "hidden value" rule. Combined with the Gematria
   ambiguity (U/V, C/K, S/Z, and digraph‑vs‑two‑letters), a system with this much freedom
   can be *steered* toward a pre‑chosen sentence. The more free parameters a "solution" has,
   the less any single output means.
2. **Post‑hoc numerology.** The relationships were found *after* fixing the plaintext.
   Across primes, totients, Fibonacci numbers, indices, and factorizations, the space of
   "striking" coincidences is enormous, so finding several for a short chosen phrase is
   expected by chance (apophenia). The author even notes the Y·O·U product "does not
   determine letter order."
3. **It doesn't match how the genuine pages work.** Every confirmed solve uses *one simple,
   deterministic* cipher with unambiguous output, reproducible by anyone in a single step,
   and Cicada built in hard verification (e.g. *An End* literally hashes to a specific
   value). A real solution of 0–2 would be similarly clean and independently checkable.

None of this means the author was dishonest. The work is careful, and the structure (e.g.
21 = 3 × 7 = the central rune NG; 27 = 3³ and 343 = 7³ in the final blocks) is genuinely
elegant. It means the evidence offered is not the *kind* of evidence that settles a cipher.

### What would actually verify it

- A **deterministic, parameter‑free** procedure mapping the exact 729 ciphertext runes to
  the plaintext, reproducible by an independent implementation.
- A **null‑hypothesis control**: the same ruleset yields English from the real ciphertext
  but *not* from shuffled/random runes of identical statistics. If it can produce English
  from anything, it proves nothing.
- An **independently checkable artifact**: a valid hash/onion like the real pages, or
  correctly solving a *different* unsolved page that then matches a known Cicada value.

Until one of those holds, it is best described as an elegant *hypothesis*, not a solve.

---

## 6. Lessons

- **Measure before you attack.** IoC tells you in milliseconds whether a page is even in
  reach of your method. Most of the unsolved Liber Primus is not.
- **Validate on known answers.** A search tool is only trustworthy if it recovers a plaintext
  you planted. Ours does; many "solvers" are never tested this way.
- **Numerology is not cryptanalysis.** A rich symbol system will always yield striking
  coincidences for any short text. Proof comes from *constraint and reproducibility*, not
  from the number of patterns you can find after the fact.
- **The honest negative result is a result.** "These pages are statistically flat and resist
  this entire class of attack" is more useful, and more truthful, than a forced reading.

---

## 7. Reproduce it yourself

```bash
cd AZdecrypt/Source/cicada
make
./cicada selftest                               # validates the toolkit
./cicada decode  data/pages/0_warning.txt atbash
./cicada decode  data/pages/p56_an_end.txt totient
./cicada translit data/pages/0_loss_of_divinity.txt
for p in p0-2 p3-7 p8-14 p15-22 p23-26 p27-32 p33-39 p40-53 p54-55; do
  ./cicada stats    data/pages/$p.txt
  ./cicada vigcrack data/pages/$p.txt 15 4 6
done
```

## Credits

Rune transcriptions and rune n‑gram corpus from the community project
[relikd/LiberPrayground](https://github.com/relikd/LiberPrayground). Gematria table and
cipher mechanics from community research (the uncovering‑cicada wiki and boxentriq's guide).
The audited 27×27 proposal is a published community reconstruction; this post evaluates its
*evidentiary standard*, not the sincerity of its author.

*This toolkit lives in a fork of Jarl Van Eycke's AZdecrypt; the same repo also contains a
CUDA/GPU port of the AZdecrypt homophonic solver.*
