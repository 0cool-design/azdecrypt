# Liber Primus pages (rune transcriptions)

UTF-8 rune transcriptions of the Liber Primus, grouped as in the source project
[relikd/LiberPrayground](https://github.com/relikd/LiberPrayground).

- `0_*.txt` / `p*.txt` / `jpg*.txt` — the raw runes of each page (group).
- `solved_*.txt` — reference plaintext for the pages that have been solved.

The named pages (`0_warning`, `0_welcome`, `0_wisdom`, `0_koan_1`, `0_loss_of_divinity`,
`p56_an_end`, `p57_parable`, `jpg107-167`, `jpg229`) are solved; the numbered `p*` ranges
are largely unsolved.

Use with the toolkit, e.g.:

```
./cicada translit data/pages/0_warning.txt
./cicada stats    data/pages/p8-14.txt
./cicada vigcrack data/pages/p8-14.txt 20 4 10
```
