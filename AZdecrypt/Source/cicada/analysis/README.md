# Analysis scripts

Reproduce the figures and tables in [`../RESEARCH.md`](../RESEARCH.md).

- `frequency.py` rune/letter and word frequencies of the solved corpus (+ IoC).
- `difficulty.py` ranks every page by IoC (predicted statistical difficulty).
- `charts.py` renders the solved-corpus + difficulty PNGs into `../assets/` (needs matplotlib).
- `charts_probes.py` renders the probe/identification figures — doublet bar, bigram heatmap,
  cipher-family fingerprint heatmap, periodic-IoC curves (needs matplotlib + numpy).
- `triage.py` structure probes (chi-squared, digraphic IoC, autocorrelation, compression).
- `keystream_search.py` number-theoretic keystream search, with An End as a positive control.
- `deep_probes.py` further cipher-class probes: periodic (Friedman) IoC, isomorph test,
  unigram chi-squared vs English, bigram distribution, and entropy.
- `identify.py` identifies the unsolved cipher *family* by enciphering known English runes
  under each candidate cipher and matching the fingerprint to the observed pages.
- `antidoublet.py` shows the doublet suppression is non-additive (An End, an additive stream,
  does not suppress) and that the increment/de-chaining stream is still flat.

```
python3 frequency.py
python3 difficulty.py
python3 charts.py
python3 triage.py
python3 keystream_search.py
python3 deep_probes.py
python3 identify.py
python3 antidoublet.py
python3 charts.py
python3 charts_probes.py
```
