# Analysis scripts

Reproduce the figures and tables in [`../RESEARCH.md`](../RESEARCH.md).

- `frequency.py` rune/letter and word frequencies of the solved corpus (+ IoC).
- `difficulty.py` ranks every page by IoC (predicted statistical difficulty).
- `charts.py` renders the PNG histograms into `../assets/` (needs matplotlib).
- `triage.py` structure probes (chi-squared, digraphic IoC, autocorrelation, compression).
- `keystream_search.py` number-theoretic keystream search, with An End as a positive control.

```
python3 frequency.py
python3 difficulty.py
python3 charts.py
python3 triage.py
python3 keystream_search.py
```
