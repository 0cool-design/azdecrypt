# cicada — Liber Primus / Gematria Primus toolkit

A module (in this AZdecrypt fork) for working with Cicada 3301's **Liber Primus**: the
29-rune **Gematria Primus** alphabet, the cipher methods used on the *solved* pages, and a
statistical search harness for testing hypotheses about the *unsolved* ones.

## ⚠️ Honest expectations

17 Liber Primus pages were solved within months of release in 2014. The remaining ~58 have
resisted the entire internet for over a decade. **This tool will not magically crack them.**
What it does:

- **Faithfully reproduce the known solves** (transliteration, Atbash, Vigenère + the F-rune
  "interrupter" skip, totient/prime streams) — validated against the published plaintext.
- Provide a fast, scriptable **hypothesis tester** (Vigenère key search, substitution
  hillclimb) scored by a rune language model, so ideas can be checked in seconds.

The `vigcrack`/`subsolve` outputs are *best-fit guesses from a statistical search*, not
confirmed solutions. Readable English means something; gibberish means the hypothesis
(cipher family/parameters) is wrong.

## Build & validate

```
make            # builds ./cicada
make test       # runs the self-test
./cicada selftest    # transliteration vs the solved "A Warning" page + Vigenère round-trip
./cicada cracktest   # encrypts known English-in-runes, confirms the search recovers it
```

`selftest` reproduces the published reading of page 0 exactly
(`A WARNNG`, `BELIEUE NOTHNG FROM THIS BOOC`, …). `cracktest` recovers a known plaintext
encrypted with a hidden 5-rune key — proof the search harness works on a known answer.

## Commands

```
cicada translit <file>                  runes -> Latin (+ gematria sum)
cicada export   <file>                  runes -> space-separated 0-28 (load in AZdecrypt GUI)
cicada stats    <file>                  rune frequencies + Index of Coincidence
cicada decode   <file> <method> [args]  apply a known cipher:
    atbash
    caesar   <shift>
    vigenere <KEY> [interrupt_rune=0]   # e.g. DIVINITY ; interrupt -1 disables F-skip
    totient  [offset]                   # keystream phi(prime)=prime-1 mod 29
    primes   [offset]                   # keystream prime_i mod 29
cicada vigcrack <file> [maxlen=16] [ngram=3] [restarts=6] [interrupt=-1]
cicada subsolve <file> [ngram=3] [restarts=30] [iters=200000]
```

Input files are UTF-8 rune text (runic block glyphs; `•⁘⁚⁖⁜` separators). An unsolved page
has IoC near random (~0.034 over 29 symbols); readable English scores far higher under the
rune n-gram model.

Build/run from this folder: `make && ./cicada selftest`.

### Loading pages in the AZdecrypt GUI

AZdecrypt reads files as single-byte text, so raw UTF-8 runes appear garbled (an encoding
issue, not a missing font — each 3-byte rune becomes 3 characters). Use `cicada export` to
write the page as space-separated symbol numbers 0-28; ready-made number files are in
`AZdecrypt/Ciphers/Liber Primus/`.

## Gematria Primus

29 runes, index 0..28, each with a Latin reading and a prime. Multi-letter runes (TH, EO,
NG, OE, AE, IA, EA) are single symbols; U/V, C/K, S/Z share a rune.

## Data (`data/`)

Rune n-gram counts (`rune-1gram…5gram.txt`), the Liber Primus runes, and the solved
reference text are sourced from the community project
[relikd/LiberPrayground](https://github.com/relikd/LiberPrayground).

## Credits & references

- Gematria table and cipher mechanics: community research
  ([uncovering-cicada wiki](https://uncovering-cicada.fandom.com/),
  [boxentriq guide](https://www.boxentriq.com/guides/cicada-3301-liber-primus)).
- Rune corpus / n-grams: [relikd/LiberPrayground](https://github.com/relikd/LiberPrayground).
