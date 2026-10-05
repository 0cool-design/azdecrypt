# AZdecrypt GPU port

A ground-up CUDA C++ reimplementation of AZdecrypt's hillclimbing cipher solver,
targeting NVIDIA GPUs. The goal is to run thousands of independent simulated-annealing
restarts concurrently on the GPU instead of ~N CPU threads.

This lives alongside the original FreeBASIC source (`AZdecrypt/Source/AZdecrypt/AZdecrypt.bas`)
and is designed to read the **same** n-gram and cipher files, so results can be validated
against the original.

## Status

Working end-to-end for homophonic substitution with 6-grams. The GPU kernel recovers
Zodiac-408 with a score bit-identical to the CPU reference.

Roadmap:
1. [done] n-gram + cipher loaders, reference scorer
2. [done] CPU reference simulated-annealing hillclimb (ground truth)
3. [done] CUDA kernel: thousands of parallel annealing chains, homophonic subst., 6-grams
4. [done] Validate on Zodiac-408 (GPU == CPU plaintext & score)
5. [next] Performance tuning (the 309 MB 6-gram table is the memory bottleneck:
   it far exceeds L2, so random lookups dominate — options: 5-gram fast path in cache,
   shared-memory staging of hot state, texture/`__ldg` reads, fewer threads/block)
6. [later] Expand to the other solver types

### Benchmark (Zodiac-408, 6-grams, 102.4M total annealing steps)

| build | hardware | time | throughput |
|-------|----------|------|-----------|
| CPU   | 8 threads          | 24.1 s | 4.3M iters/s |
| GPU   | RTX 4070 Laptop    | 9.7 s  | 10.6M iters/s (incl. table upload) |

At larger scale the GPU sustains ~21M iters/s (~5.5x the 8-thread CPU).

## Commands

```
make           # CPU build  -> ./azgpu   (score, solve)
make gpu       # GPU build  -> ./azgpu   (score, solve, gsolve)

./azgpu solve  <ngrams.gz> <cipher.txt> [iterations] [restarts] [threads]
./azgpu gsolve <ngrams.gz> <cipher.txt> [iterations] [restarts]
./azgpu score  <ngrams.gz> <cipher.txt> <solution.txt>
```

## File formats (reverse-engineered from AZdecrypt.bas `thread_load_ngrams`)

### N-grams
- `<name>.ini` — text header: `N-gram size=`, `N-gram factor=`, `Entropy weight=`,
  `Alphabet=`, `Temperature=`.
- `<name>.gz` — gzip payload, format auto-detected from the first `N` bytes:
  - **text**: fixed-width records, `N` alphabet bytes + a 3-char right-justified
    (space-padded) value 0..255. Records may be separated by bytes < 32.
  - **binary**: dense row-major dump, one byte per table cell, `alpha_size^N` bytes.
    Linear index of (x1..xN) = ((..(x1*A + x2)*A + x3)..)*A + xN, A = alpha_size.
- The stored value is a 1-byte log-probability score.

### Ciphers
- Plain text grid; each row is a line (CRLF). Each glyph is one cipher symbol.
  (The first milestone treats one byte = one symbol, which is correct for Zodiac-408.)

## Build

Requires g++ and zlib (`zlib.h`). CUDA (`nvcc`) is only needed for the GPU kernel (step 3).

```
make            # builds the CPU tools
./azgpu score "../AZdecrypt/N-grams/6-grams_english_jarlve_reddit_v1912.gz" \
              "../AZdecrypt/Ciphers/Zodiac ciphers/Zodiac 408.txt" \
              "../AZdecrypt/Ciphers/Zodiac ciphers/Zodiac 408 solved.txt"
```
