#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <vector>

#include "solver.hpp"

// ---------------------------------------------------------------------------
// Error helper
// ---------------------------------------------------------------------------
#define CUDA_OK(call)                                                             \
    do {                                                                          \
        cudaError_t _e = (call);                                                  \
        if (_e != cudaSuccess) {                                                  \
            std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(_e), \
                         __FILE__, __LINE__);                                      \
            std::abort();                                                         \
        }                                                                         \
    } while (0)

// Plain-old-data view of SolverCtx scalars, passed to the kernel by value.
struct GpuCtx {
    int l, s, n, A, al;
    double ngfal, onesixl, start_temp;
};

// ---------------------------------------------------------------------------
// Device PRNG — identical generator to the CPU reference (xorshift128+).
// ---------------------------------------------------------------------------
struct DRng {
    unsigned long long s0, s1;
    __device__ void seed(unsigned long long seed) {
        auto sm = [&]() -> unsigned long long {
            seed += 0x9E3779B97F4A7C15ULL;
            unsigned long long z = seed;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
            return z ^ (z >> 31);
        };
        s0 = sm();
        s1 = sm();
    }
    __device__ unsigned long long next() {
        unsigned long long x = s0, y = s1;
        s0 = y;
        x ^= x << 23;
        s1 = x ^ y ^ (x >> 17) ^ (y >> 26);
        return s1 + y;
    }
    __device__ int below(int bound) { return (int)(next() % (unsigned long long)bound); }
};

// ---------------------------------------------------------------------------
// One annealing restart on the device. Mirrors anneal_once() in solver.cpp.
// All per-chain working storage is passed in (lives in global memory).
// ---------------------------------------------------------------------------
__device__ double anneal_once_gpu(const GpuCtx c, const unsigned char* __restrict__ g,
                                   const int* __restrict__ cipher,
                                   const int* __restrict__ win_off,
                                   const int* __restrict__ win_idx,
                                   const int* __restrict__ mape2,
                                   const int* __restrict__ pos_count,
                                   const double* __restrict__ enttable, long long iterations,
                                   unsigned long long seed, int* sol, int* stl, int* frq,
                                   unsigned char* ngr, unsigned char* scratch, int* order,
                                   int* out_key) {
    const int l = c.l, s = c.s, n = c.n, A = c.A, al = c.al;
    DRng rng;
    rng.seed(seed);

    for (int i = 0; i < s; i++) stl[i] = rng.below(A);
    for (int i = 0; i < l; i++) sol[i] = stl[cipher[i]];
    for (int i = 0; i <= A; i++) frq[i] = 0;
    for (int i = 0; i < s; i++) frq[stl[i]] += mape2[i];

    double entropy = 0;
    for (int a = 0; a < A; a++) entropy += enttable[frq[a]];

    auto score_window = [&](int w) -> unsigned char {
        size_t li = 0;
        for (int k = 0; k < n; k++) li = li * (size_t)A + (size_t)sol[w + k];
        return g[li];
    };

    long long new_ngram_score = 0;
    for (int w = 0; w < al; w++) {
        unsigned char v = score_window(w);
        ngr[w] = v;
        new_ngram_score += v;
    }

    double old_score = 0, new_score = 0, best_score = 0;
    for (int i = 0; i < s; i++) out_key[i] = stl[i];

    double temp = c.start_temp;
    double temp_min = temp / (double)iterations;
    int accept = 1;

    for (int i = 0; i < s; i++) order[i] = i;
    int mi = s;

    for (long long it = 0; it < iterations; it++) {
        if (mi >= s) {
            for (int i = s - 1; i > 0; i--) {
                int j = rng.below(i + 1);
                int tmp = order[i];
                order[i] = order[j];
                order[j] = tmp;
            }
            mi = 0;
        }
        int curr = order[mi++];

        if (!accept && new_score != 0.0)
            old_score -= temp * pos_count[curr] * c.onesixl * old_score / new_score;
        temp -= temp_min;

        int old_letter = stl[curr];
        int new_letter = rng.below(A);
        if (new_letter == old_letter) new_letter = (new_letter + 1 + rng.below(A - 1)) % A;

        int wo = win_off[curr], we = win_off[curr + 1];
        for (int wi = wo; wi < we; wi++) {
            int w = win_idx[wi];
            for (int k = 0; k < n; k++)
                if (cipher[w + k] == curr) sol[w + k] = new_letter;
        }

        double old_entropy = entropy;
        int wgt = mape2[curr];
        entropy += enttable[frq[old_letter] - wgt] - enttable[frq[old_letter]];
        entropy += enttable[frq[new_letter] + wgt] - enttable[frq[new_letter]];

        long long old_ngram = new_ngram_score;
        long long delta = 0;
        for (int wi = wo; wi < we; wi++) {
            int w = win_idx[wi];
            unsigned char nv = score_window(w);
            scratch[w] = nv;
            delta += (long long)nv - (long long)ngr[w];
        }
        new_ngram_score += delta;

        new_score = (double)new_ngram_score * c.ngfal * entropy;

        if (new_score > old_score) {
            accept = 1;
            frq[old_letter] -= wgt;
            frq[new_letter] += wgt;
            stl[curr] = new_letter;
            for (int wi = wo; wi < we; wi++) {
                int w = win_idx[wi];
                ngr[w] = scratch[w];
            }
            old_score = new_score;
            if (new_score > best_score) {
                best_score = new_score;
                for (int i = 0; i < s; i++) out_key[i] = stl[i];
            }
        } else {
            accept = 0;
            new_ngram_score = old_ngram;
            entropy = old_entropy;
            for (int wi = wo; wi < we; wi++) {
                int w = win_idx[wi];
                for (int k = 0; k < n; k++)
                    if (cipher[w + k] == curr) sol[w + k] = old_letter;
            }
        }
    }
    return best_score;
}

__global__ void anneal_kernel(GpuCtx c, const unsigned char* g, const int* cipher,
                              const int* win_off, const int* win_idx, const int* mape2,
                              const int* pos_count, const double* enttable,
                              long long iterations, int restarts_per_thread, int n_chains,
                              unsigned long long base_seed, int* sol_all, int* stl_all,
                              int* frq_all, unsigned char* ngr_all, unsigned char* scratch_all,
                              int* order_all, int* bestkey_all, double* bestscore_all) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= n_chains) return;

    const int l = c.l, s = c.s, A = c.A, al = c.al;
    int* sol = sol_all + (size_t)tid * l;
    int* stl = stl_all + (size_t)tid * s;
    int* frq = frq_all + (size_t)tid * (A + 1);
    unsigned char* ngr = ngr_all + (size_t)tid * al;
    unsigned char* scratch = scratch_all + (size_t)tid * al;
    int* order = order_all + (size_t)tid * s;
    int* out_key = bestkey_all + (size_t)tid * s;

    double thread_best = -1;
    int tmp_key[256];  // s <= alphabet-of-symbols cap; 256 is safe for these ciphers

    for (int r = 0; r < restarts_per_thread; r++) {
        unsigned long long seed =
            base_seed + ((unsigned long long)tid * restarts_per_thread + r) * 0x100000001B3ULL;
        double sc = anneal_once_gpu(c, g, cipher, win_off, win_idx, mape2, pos_count, enttable,
                                    iterations, seed, sol, stl, frq, ngr, scratch, order,
                                    tmp_key);
        if (sc > thread_best) {
            thread_best = sc;
            for (int i = 0; i < s; i++) out_key[i] = tmp_key[i];
        }
    }
    bestscore_all[tid] = thread_best;
}

// ---------------------------------------------------------------------------
// Host entry point
// ---------------------------------------------------------------------------
SolveResult solve_gpu(const SolverCtx& ctx, const SolveParams& p) {
    GpuCtx c;
    c.l = ctx.l;
    c.s = ctx.s;
    c.n = ctx.n;
    c.A = ctx.A;
    c.al = ctx.al;
    c.ngfal = ctx.ngfal;
    c.onesixl = ctx.onesixl;
    c.start_temp = ctx.start_temp;

    if (c.s > 256) throw std::runtime_error("GPU build caps symbols at 256");

    // Decide concurrency: cap simultaneous chains, loop the rest per thread.
    int n_chains = p.restarts;
    const int kMaxChains = 16384;
    if (n_chains > kMaxChains) n_chains = kMaxChains;
    int restarts_per_thread = (p.restarts + n_chains - 1) / n_chains;

    const size_t table_bytes = ctx.ng->table.size();
    const int emax = ctx.l * ctx.n;
    const int W = ctx.win_off[ctx.s];

    // --- device allocations -------------------------------------------------
    unsigned char* d_table;
    int *d_cipher, *d_win_off, *d_win_idx, *d_mape2, *d_pos_count;
    double* d_enttable;
    CUDA_OK(cudaMalloc(&d_table, table_bytes));
    CUDA_OK(cudaMalloc(&d_cipher, sizeof(int) * ctx.l));
    CUDA_OK(cudaMalloc(&d_win_off, sizeof(int) * (ctx.s + 1)));
    CUDA_OK(cudaMalloc(&d_win_idx, sizeof(int) * W));
    CUDA_OK(cudaMalloc(&d_mape2, sizeof(int) * ctx.s));
    CUDA_OK(cudaMalloc(&d_pos_count, sizeof(int) * ctx.s));
    CUDA_OK(cudaMalloc(&d_enttable, sizeof(double) * (emax + 1)));

    CUDA_OK(cudaMemcpy(d_table, ctx.ng->table.data(), table_bytes, cudaMemcpyHostToDevice));
    CUDA_OK(cudaMemcpy(d_cipher, ctx.cipher.data(), sizeof(int) * ctx.l, cudaMemcpyHostToDevice));
    CUDA_OK(cudaMemcpy(d_win_off, ctx.win_off.data(), sizeof(int) * (ctx.s + 1),
                       cudaMemcpyHostToDevice));
    CUDA_OK(cudaMemcpy(d_win_idx, ctx.win_idx.data(), sizeof(int) * W, cudaMemcpyHostToDevice));
    CUDA_OK(cudaMemcpy(d_mape2, ctx.mape2.data(), sizeof(int) * ctx.s, cudaMemcpyHostToDevice));
    CUDA_OK(cudaMemcpy(d_pos_count, ctx.pos_count.data(), sizeof(int) * ctx.s,
                       cudaMemcpyHostToDevice));
    CUDA_OK(cudaMemcpy(d_enttable, ctx.enttable.data(), sizeof(double) * (emax + 1),
                       cudaMemcpyHostToDevice));

    // --- per-chain working buffers -----------------------------------------
    int *d_sol, *d_stl, *d_frq, *d_order, *d_bestkey;
    unsigned char *d_ngr, *d_scratch;
    double* d_bestscore;
    CUDA_OK(cudaMalloc(&d_sol, sizeof(int) * (size_t)n_chains * ctx.l));
    CUDA_OK(cudaMalloc(&d_stl, sizeof(int) * (size_t)n_chains * ctx.s));
    CUDA_OK(cudaMalloc(&d_frq, sizeof(int) * (size_t)n_chains * (ctx.A + 1)));
    CUDA_OK(cudaMalloc(&d_order, sizeof(int) * (size_t)n_chains * ctx.s));
    CUDA_OK(cudaMalloc(&d_ngr, (size_t)n_chains * ctx.al));
    CUDA_OK(cudaMalloc(&d_scratch, (size_t)n_chains * ctx.al));
    CUDA_OK(cudaMalloc(&d_bestkey, sizeof(int) * (size_t)n_chains * ctx.s));
    CUDA_OK(cudaMalloc(&d_bestscore, sizeof(double) * n_chains));

    // --- launch -------------------------------------------------------------
    int block = 128;
    int grid = (n_chains + block - 1) / block;
    if (!p.quiet)
        std::printf("GPU: %d chains x %d restart(s) each, %lld iters/restart (block %d grid %d)\n",
                    n_chains, restarts_per_thread, p.iterations, block, grid);

    anneal_kernel<<<grid, block>>>(c, d_table, d_cipher, d_win_off, d_win_idx, d_mape2,
                                   d_pos_count, d_enttable, p.iterations, restarts_per_thread,
                                   n_chains, p.seed, d_sol, d_stl, d_frq, d_ngr, d_scratch,
                                   d_order, d_bestkey, d_bestscore);
    CUDA_OK(cudaGetLastError());
    CUDA_OK(cudaDeviceSynchronize());

    // --- reduce on host -----------------------------------------------------
    std::vector<double> scores(n_chains);
    CUDA_OK(cudaMemcpy(scores.data(), d_bestscore, sizeof(double) * n_chains,
                       cudaMemcpyDeviceToHost));
    int best_tid = 0;
    for (int i = 1; i < n_chains; i++)
        if (scores[i] > scores[best_tid]) best_tid = i;

    SolveResult r;
    r.score = scores[best_tid];
    r.key.resize(ctx.s);
    CUDA_OK(cudaMemcpy(r.key.data(), d_bestkey + (size_t)best_tid * ctx.s, sizeof(int) * ctx.s,
                       cudaMemcpyDeviceToHost));

    r.plaintext.resize(ctx.l);
    r.text.resize(ctx.l);
    for (int i = 0; i < ctx.l; i++) {
        int letter = r.key[ctx.cipher[i]];
        r.plaintext[i] = letter;
        r.text[i] = ctx.ng->alphabet[letter];
    }

    cudaFree(d_table);
    cudaFree(d_cipher);
    cudaFree(d_win_off);
    cudaFree(d_win_idx);
    cudaFree(d_mape2);
    cudaFree(d_pos_count);
    cudaFree(d_enttable);
    cudaFree(d_sol);
    cudaFree(d_stl);
    cudaFree(d_frq);
    cudaFree(d_order);
    cudaFree(d_ngr);
    cudaFree(d_scratch);
    cudaFree(d_bestkey);
    cudaFree(d_bestscore);
    return r;
}
