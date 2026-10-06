# Analysis scripts

Reproduce the figures and tables in [`../RESEARCH.md`](../RESEARCH.md).

- `frequency.py` — rune/letter and word frequencies of the solved corpus (+ IoC).
- `difficulty.py` — ranks every page by IoC (predicted statistical difficulty).
- `charts.py` — renders the PNG histograms into `../assets/` (needs matplotlib).

```
python3 frequency.py
python3 difficulty.py
python3 charts.py
```
