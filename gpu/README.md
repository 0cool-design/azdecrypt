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
5. [done] Performance profiling + tuning (see findings below)
6. [later] Expand to the other solver types; algorithmic convergence (greedy "best letter"
   moves like the original's g6b cache) to need fewer iterations

### Benchmark & tuning findings (Zodiac-408, RTX 4070 Laptop)

Kernel throughput (compute only, table upload excluded):

| n-gram | table size | throughput | note |
|--------|-----------|-----------|------|
| 6-gram | 309 MB | ~22 Miter/s | exceeds L2 -> scattered-read bound |
| 5-gram | 12 MB  | ~50 Miter/s | fits in L2 -> 2.3x faster |

Aggregate vs the OpenMP CPU build (8 threads, ~4.3 Miter/s): GPU 6-gram ~5x, 5-gram ~11x.

**The 6-gram kernel is memory-access-pattern bound, not occupancy bound.** Each annealing
step does scattered 1-byte reads into the 309 MB table (each read pulls a full 32 B sector),
and that table far exceeds the ~32 MB L2. Measured, and confirming this:

- Register-cap sweep (`-maxrregcount` 64/48/40/32) to raise occupancy: no change (~21-22).
- Thread-count sweep (8k -> 128k chains): throughput *fell* (21 -> 18) from L2/DRAM
  contention. ~8-16k chains already saturates the memory subsystem.
- `__ldg` read-only path and struct-of-arrays layout: neutral / negative (threads diverge,
  so thread-local contiguous AoS caches better).

So the real levers are NOT GPU knobs but **algorithmic**: use 5-grams when speed matters,
or add greedy "best-letter" moves so fewer iterations are needed to converge. GPU's
structural win is parallel breadth — thousands of independent restarts — which pays off on
hard ciphers needing huge restart counts, more than on an easy one like 408.

Tunables (env): `AZ_BLOCK` (threads/block, default 128), `AZ_MAXCHAINS` (default 16384).

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
