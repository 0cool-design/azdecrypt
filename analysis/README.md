# Analysis scripts

Reproduce the figures and tables in [`../README.md`](../README.md).

- `frequency.py` rune/letter and word frequencies of the solved corpus (+ IoC).
- `gematria_primes.py` sums each solved verse's rune primes and tests the total for primality
  (45 of 102 lines are prime, about 3x the chance rate).
- `difficulty.py` ranks every page by IoC (predicted statistical difficulty).
- `charts.py` renders the solved-corpus + difficulty PNGs into `../assets/` (needs matplotlib).
- `charts_probes.py` renders the probe/identification figures: doublet bar, bigram heatmap,
  cipher-family fingerprint heatmap, periodic-IoC curves (needs matplotlib + numpy).
- `triage.py` structure probes (chi-squared, digraphic IoC, autocorrelation, compression).
- `keystream_search.py` number-theoretic keystream search, with An End as a positive control.
- `deep_probes.py` further cipher-class probes: periodic (Friedman) IoC, isomorph test,
  unigram chi-squared vs English, bigram distribution, and entropy.
- `identify.py` identifies the unsolved cipher *family* by enciphering known English runes
  under each candidate cipher and matching the fingerprint to the observed pages.
- `antidoublet.py` shows the doublet suppression is non-additive (An End, an additive stream,
  does not suppress) and that the increment/de-chaining stream is still flat.
- `cicada_primes.py` tests the Cicada OS prime list (`../data/cicada_os_primes.txt`, 2..3301)
  as a keystream against the unsolved pages; recovers An End as control, nothing else.
- `arith_search.py` exhaustive arithmetic-progression (Trithemius) keystream search.
- `solved_vocab_attack.py` uses the solved-page words as Vigenère keys, the solved plaintext
  as a running key, and the words as cribs.
- `more_attacks.py` ciphertext/plaintext autokey, Beaufort, and interrupter-aware keystream.
- `attack_p40.py` focused Kasiski + crib + running-key attack on the most tractable page.

```
python3 frequency.py
python3 difficulty.py
python3 charts.py
python3 triage.py
python3 keystream_search.py
python3 deep_probes.py
python3 identify.py
python3 antidoublet.py
python3 cicada_primes.py
python3 charts.py
python3 charts_probes.py
```
