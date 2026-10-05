#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <vector>

#include "solver.hpp"

#define CUDA_OK(call)                                                             \
    do {                                                                          \
        cudaError_t _e = (call);                                                  \
        if (_e != cudaSuccess) {                                                  \
            std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(_e), \
                         __FILE__, __LINE__);                                      \
            std::abort();                                                         \
        }                                                                         \
    } while (0)

struct GpuCtx {
    int l, s, n, A, al;
    double ngfal, onesixl, start_temp;
};

// Device PRNG — identical generator to the CPU reference (xorshift128+).
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

// One annealing restart. All per-chain arrays are *base* pointers into
// struct-of-arrays storage, indexed [logical_index * stride + tid] so that
// threads in a warp touch contiguous addresses (coalesced). Best key written
// to out_key (same SoA layout). Mirrors anneal_once() in solver.cpp.
__device__ double anneal_once_gpu(const GpuCtx c, const unsigned char* __restrict__ g,
                                  const int* __restrict__ cipher,
                                  const int* __restrict__ win_off,
                                  const int* __restrict__ win_idx,
                                  const int* __restrict__ mape2,
                                  const int* __restrict__ pos_count,
                                  const double* __restrict__ enttable, long long iterations,
                                  unsigned long long seed, int tid, long long stride, int* sol,
                                  int* stl, int* frq, unsigned char* ngr, unsigned char* scratch,
                                  int* order, int* out_key) {
    const int l = c.l, s = c.s, n = c.n, A = c.A, al = c.al;

    // AoS: each thread owns a contiguous slice (compact working set, cache-friendly
    // under the divergent access pattern). `stride` is unused in this layout.
    (void)stride;
    sol += (long long)tid * l;
    stl += (long long)tid * s;
    frq += (long long)tid * (A + 1);
    ngr += (long long)tid * al;
    scratch += (long long)tid * al;
    order += (long long)tid * s;
    out_key += (long long)tid * s;

#define SOL(i) sol[(i)]
#define STL(i) stl[(i)]
#define FRQ(i) frq[(i)]
#define NGR(i) ngr[(i)]
#define SCR(i) scratch[(i)]
#define ORD(i) order[(i)]
#define KEY(i) out_key[(i)]

    DRng rng;
    rng.seed(seed);

    for (int i = 0; i < s; i++) STL(i) = rng.below(A);
    for (int i = 0; i <= A; i++) FRQ(i) = 0;
    for (int i = 0; i < l; i++) SOL(i) = STL(cipher[i]);
    for (int i = 0; i < s; i++) FRQ(STL(i)) += mape2[i];

    double entropy = 0;
    for (int a = 0; a < A; a++) entropy += enttable[FRQ(a)];

    long long new_ngram_score = 0;
    for (int w = 0; w < al; w++) {
        size_t li = 0;
        for (int k = 0; k < n; k++) li = li * (size_t)A + (size_t)SOL(w + k);
        unsigned char v = __ldg(&g[li]);
        NGR(w) = v;
        new_ngram_score += v;
    }

    double old_score = 0, new_score = 0, best_score = 0;
    for (int i = 0; i < s; i++) KEY(i) = STL(i);

    double temp = c.start_temp;
    double temp_min = temp / (double)iterations;
    int accept = 1;

    for (int i = 0; i < s; i++) ORD(i) = i;
    int mi = s;

    for (long long it = 0; it < iterations; it++) {
        if (mi >= s) {
            for (int i = s - 1; i > 0; i--) {
                int j = rng.below(i + 1);
                int tmp = ORD(i);
                ORD(i) = ORD(j);
                ORD(j) = tmp;
            }
            mi = 0;
        }
        int curr = ORD(mi++);

        if (!accept && new_score != 0.0)
            old_score -= temp * pos_count[curr] * c.onesixl * old_score / new_score;
        temp -= temp_min;

        int old_letter = STL(curr);
        int new_letter = rng.below(A);
        if (new_letter == old_letter) new_letter = (new_letter + 1 + rng.below(A - 1)) % A;

        int wo = win_off[curr], we = win_off[curr + 1];
        for (int wi = wo; wi < we; wi++) {
            int w = win_idx[wi];
            for (int k = 0; k < n; k++)
                if (cipher[w + k] == curr) SOL(w + k) = new_letter;
        }

        double old_entropy = entropy;
        int wgt = mape2[curr];
        entropy += enttable[FRQ(old_letter) - wgt] - enttable[FRQ(old_letter)];
        entropy += enttable[FRQ(new_letter) + wgt] - enttable[FRQ(new_letter)];

        long long old_ngram = new_ngram_score;
        long long delta = 0;
        for (int wi = wo; wi < we; wi++) {
            int w = win_idx[wi];
            size_t li = 0;
            for (int k = 0; k < n; k++) li = li * (size_t)A + (size_t)SOL(w + k);
            unsigned char nv = __ldg(&g[li]);
            SCR(w) = nv;
            delta += (long long)nv - (long long)NGR(w);
        }
        new_ngram_score += delta;

        new_score = (double)new_ngram_score * c.ngfal * entropy;

        if (new_score > old_score) {
            accept = 1;
            FRQ(old_letter) -= wgt;
            FRQ(new_letter) += wgt;
            STL(curr) = new_letter;
            for (int wi = wo; wi < we; wi++) {
                int w = win_idx[wi];
                NGR(w) = SCR(w);
            }
            old_score = new_score;
            if (new_score > best_score) {
                best_score = new_score;
                for (int i = 0; i < s; i++) KEY(i) = STL(i);
            }
        } else {
            accept = 0;
            new_ngram_score = old_ngram;
            entropy = old_entropy;
            for (int wi = wo; wi < we; wi++) {
                int w = win_idx[wi];
                for (int k = 0; k < n; k++)
                    if (cipher[w + k] == curr) SOL(w + k) = old_letter;
            }
        }
    }
    return best_score;

#undef SOL
#undef STL
#undef FRQ
#undef NGR
#undef SCR
#undef ORD
#undef KEY
}

__global__ void anneal_kernel(GpuCtx c, const unsigned char* g, const int* cipher,
                              const int* win_off, const int* win_idx, const int* mape2,
                              const int* pos_count, const double* enttable,
                              long long iterations, int restarts_per_thread, int n_chains,
                              unsigned long long base_seed, int* sol, int* stl, int* frq,
                              unsigned char* ngr, unsigned char* scratch, int* order,
                              int* curkey, int* bestkey, double* bestscore) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= n_chains) return;
    const long long stride = n_chains;
    const int s = c.s;

    double thread_best = -1;
    for (int r = 0; r < restarts_per_thread; r++) {
        unsigned long long seed =
            base_seed + ((unsigned long long)tid * restarts_per_thread + r) * 0x100000001B3ULL;
        double sc = anneal_once_gpu(c, g, cipher, win_off, win_idx, mape2, pos_count, enttable,
                                    iterations, seed, tid, stride, sol, stl, frq, ngr, scratch,
                                    order, curkey);
        if (sc > thread_best) {
            thread_best = sc;
            int* bk = bestkey + (long long)tid * s;
            int* ck = curkey + (long long)tid * s;
            for (int i = 0; i < s; i++) bk[i] = ck[i];
        }
    }
    bestscore[tid] = thread_best;
}

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

    // ~8-16k chains saturates the memory subsystem for the 6-gram table; beyond that,
    // more chains just add L2/DRAM contention (measured). Overridable for experiments.
    int n_chains = p.restarts;
    int kMaxChains = 16384;
    if (const char* mc = getenv("AZ_MAXCHAINS")) kMaxChains = atoi(mc);
    if (n_chains > kMaxChains) n_chains = kMaxChains;
    int restarts_per_thread = (p.restarts + n_chains - 1) / n_chains;

    const size_t table_bytes = ctx.ng->table.size();
    const int emax = ctx.l * ctx.n;
    const int W = ctx.win_off[ctx.s];
    const size_t NC = (size_t)n_chains;

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

    int *d_sol, *d_stl, *d_frq, *d_order, *d_curkey, *d_bestkey;
    unsigned char *d_ngr, *d_scratch;
    double* d_bestscore;
    CUDA_OK(cudaMalloc(&d_sol, sizeof(int) * NC * ctx.l));
    CUDA_OK(cudaMalloc(&d_stl, sizeof(int) * NC * ctx.s));
    CUDA_OK(cudaMalloc(&d_frq, sizeof(int) * NC * (ctx.A + 1)));
    CUDA_OK(cudaMalloc(&d_order, sizeof(int) * NC * ctx.s));
    CUDA_OK(cudaMalloc(&d_ngr, NC * ctx.al));
    CUDA_OK(cudaMalloc(&d_scratch, NC * ctx.al));
    CUDA_OK(cudaMalloc(&d_curkey, sizeof(int) * NC * ctx.s));
    CUDA_OK(cudaMalloc(&d_bestkey, sizeof(int) * NC * ctx.s));
    CUDA_OK(cudaMalloc(&d_bestscore, sizeof(double) * NC));

    int block = 128;
    if (const char* bs = getenv("AZ_BLOCK")) block = atoi(bs);
    if (block <= 0) block = 128;
    int grid = (n_chains + block - 1) / block;
    if (!p.quiet)
        std::printf("GPU: %d chains x %d restart(s) each, %lld iters/restart (block %d grid %d)\n",
                    n_chains, restarts_per_thread, p.iterations, block, grid);

    cudaEvent_t t0, t1;
    CUDA_OK(cudaEventCreate(&t0));
    CUDA_OK(cudaEventCreate(&t1));
    CUDA_OK(cudaEventRecord(t0));
    anneal_kernel<<<grid, block>>>(c, d_table, d_cipher, d_win_off, d_win_idx, d_mape2,
                                   d_pos_count, d_enttable, p.iterations, restarts_per_thread,
                                   n_chains, p.seed, d_sol, d_stl, d_frq, d_ngr, d_scratch,
                                   d_order, d_curkey, d_bestkey, d_bestscore);
    CUDA_OK(cudaGetLastError());
    CUDA_OK(cudaEventRecord(t1));
    CUDA_OK(cudaEventSynchronize(t1));
    float ms = 0;
    CUDA_OK(cudaEventElapsedTime(&ms, t0, t1));
    if (!p.quiet) {
        double total_iters = (double)n_chains * restarts_per_thread * p.iterations;
        std::printf("kernel: %.1f ms, %.1f Miter/s\n", ms, total_iters / (ms * 1e3));
    }

    std::vector<double> scores(n_chains);
    CUDA_OK(cudaMemcpy(scores.data(), d_bestscore, sizeof(double) * n_chains,
                       cudaMemcpyDeviceToHost));
    int best_tid = 0;
    for (int i = 1; i < n_chains; i++)
        if (scores[i] > scores[best_tid]) best_tid = i;

    std::vector<int> allkeys((size_t)n_chains * ctx.s);
    CUDA_OK(cudaMemcpy(allkeys.data(), d_bestkey, sizeof(int) * NC * ctx.s,
                       cudaMemcpyDeviceToHost));

    SolveResult r;
    r.score = scores[best_tid];
    r.key.resize(ctx.s);
    for (int i = 0; i < ctx.s; i++) r.key[i] = allkeys[(size_t)best_tid * ctx.s + i];

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
    cudaFree(d_curkey);
    cudaFree(d_bestkey);
    cudaFree(d_bestscore);
    return r;
}
