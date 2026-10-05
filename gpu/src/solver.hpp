#pragma once
#include <cstdint>
#include <string>
#include <vector>

#include "cipher.hpp"
#include "ngram.hpp"

// Parameters for a homophonic-substitution solve (matches the original's knobs).
struct SolveParams {
    long long iterations = 400000;   // simulated-annealing steps per restart
    int restarts = 1000;             // number of random restarts (total work)
    double multiplicity_weight = 0;  // solvesub_multiplicityweight (default 0)
    uint64_t seed = 1;               // base RNG seed
    int threads = 0;                 // 0 = use all cores (OpenMP)
    bool quiet = false;
};

// Precomputed, read-only context shared by all annealing chains (CPU and GPU).
// Everything here depends only on the cipher + n-gram table, not on the key.
struct SolverCtx {
    int l = 0;       // cipher length
    int s = 0;       // distinct symbols
    int n = 0;       // n-gram size
    int A = 0;       // alphabet size
    int al = 0;      // number of n-gram windows = l - (n-1)

    double ngfal = 0;      // ngram_factor * ent_norm / al  (score scale)
    double onesixl = 0;    // 1.7 / l
    double start_temp = 0; // initial annealing temperature

    std::vector<int> cipher;         // l, each 0..s-1
    std::vector<int> pos_count;      // s: number of positions per symbol (map1 count)
    std::vector<int> mape2;          // s: entropy weight per symbol
    std::vector<double> enttable;    // size l*n+1

    // CSR-style adjacency: windows affected by each symbol (map2).
    std::vector<int> win_off;        // s+1
    std::vector<int> win_idx;        // flattened window starts

    const NgramTable* ng = nullptr;  // borrowed

    SolverCtx(const Cipher& c, const NgramTable& t, double multiplicity_weight);
};

struct SolveResult {
    double score = 0;
    std::vector<int> key;        // s: letter index per symbol
    std::vector<int> plaintext;  // l: letter indices
    std::string text;            // decoded plaintext
};

// CPU reference solver (OpenMP across restarts). Ground truth for the GPU kernel.
SolveResult solve_cpu(const SolverCtx& ctx, const SolveParams& p);

#ifdef USE_CUDA
// GPU solver: thousands of independent annealing chains on the device.
SolveResult solve_gpu(const SolverCtx& ctx, const SolveParams& p);
#endif
