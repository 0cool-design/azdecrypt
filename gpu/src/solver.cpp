#include "solver.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <set>
#include <stdexcept>

#ifdef _OPENMP
#include <omp.h>
#endif

// ---------------------------------------------------------------------------
// Context precompute
// ---------------------------------------------------------------------------
SolverCtx::SolverCtx(const Cipher& c, const NgramTable& t, double multiplicity_weight) {
    ng = &t;
    l = c.length;
    s = c.n_symbols;
    n = t.n;
    A = t.alpha_size;
    al = l - (n - 1);
    if (al <= 0) throw std::runtime_error("cipher shorter than n-gram size");

    cipher = c.seq;

    // mape1[i] = number of windows covering position i.
    std::vector<int> mape1(l, 0);
    for (int w = 0; w < al; w++)
        for (int k = 0; k < n; k++) mape1[w + k]++;

    pos_count.assign(s, 0);
    mape2.assign(s, 0);
    for (int i = 0; i < l; i++) {
        pos_count[cipher[i]]++;
        mape2[cipher[i]] += mape1[i];
    }
    long long total_weight = 0;
    for (int i = 0; i < l; i++) total_weight += mape1[i];

    // Windows affected by each symbol (map2), built as CSR.
    std::vector<std::set<int>> wsets(s);
    for (int w = 0; w < al; w++)
        for (int k = 0; k < n; k++) wsets[cipher[w + k]].insert(w);
    win_off.assign(s + 1, 0);
    for (int sym = 0; sym < s; sym++) win_off[sym + 1] = win_off[sym] + (int)wsets[sym].size();
    win_idx.resize(win_off[s]);
    for (int sym = 0; sym < s; sym++) {
        int o = win_off[sym];
        for (int w : wsets[sym]) win_idx[o++] = w;
    }

    // enttable(x) = |log2(x/(l*n)) * (x/(l*n))|, enttable(0)=0.
    int emax = l * n;
    enttable.assign(emax + 1, 0.0);
    for (int i = 1; i <= emax; i++) {
        double p = (double)i / (double)emax;
        enttable[i] = std::fabs(std::log2(p) * p);
    }

    // Score scaling: ngf = ngram_factor * ent_norm / (1 + (s/l)*multweight)
    double ent_norm = (double)(l * n) / (double)total_weight;  // = l/al in practice
    double ngf = t.ngram_factor * ent_norm / (1.0 + ((double)s / l) * multiplicity_weight);
    ngfal = ngf / al;
    onesixl = 1.7 / l;

    // m_ioc2(cipher, l, s, n=2) = ((l/s)*((l/s)-1)*s) / sum f(f-1)
    double ioc = 1.0;
    {
        std::vector<long long> f(s, 0);
        for (int i = 0; i < l; i++) f[cipher[i]]++;
        double denom = 0;
        for (int sym = 0; sym < s; sym++) denom += (double)f[sym] * (f[sym] - 1);
        if (denom > 0 && l != s) {
            double ls = (double)l / s;
            ioc = (ls * (ls - 1.0) * s) / denom;
        }
    }
    // start_temp = (temp/4.61538) / ((s/l)/ln(l)) / ioc^0.75
    double temp1 = t.temperature > 0 ? t.temperature : 800.0;
    start_temp = (temp1 / 4.61538) / (((double)s / l) / std::log((double)l));
    start_temp /= std::pow(ioc, 0.75);
}

// ---------------------------------------------------------------------------
// Fast per-chain PRNG (xorshift128+ style). Same generator we'll use on GPU.
// ---------------------------------------------------------------------------
struct Rng {
    uint64_t s0, s1;
    explicit Rng(uint64_t seed) {
        // splitmix64 to seed the state
        auto sm = [&]() {
            seed += 0x9E3779B97F4A7C15ULL;
            uint64_t z = seed;
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
            return z ^ (z >> 31);
        };
        s0 = sm();
        s1 = sm();
    }
    inline uint64_t next() {
        uint64_t x = s0, y = s1;
        s0 = y;
        x ^= x << 23;
        s1 = x ^ y ^ (x >> 17) ^ (y >> 26);
        return s1 + y;
    }
    inline int below(int bound) { return (int)(next() % (uint64_t)bound); }
};

// ---------------------------------------------------------------------------
// One annealing restart. Writes best key found into out_key (length s) and
// returns its score. Self-contained so it is trivially parallelizable.
// ---------------------------------------------------------------------------
static double anneal_once(const SolverCtx& c, long long iterations, uint64_t seed,
                          std::vector<int>& out_key) {
    const int l = c.l, s = c.s, n = c.n, A = c.A, al = c.al;
    const uint8_t* g = c.ng->table.data();

    Rng rng(seed);

    std::vector<int> sol(l);     // current plaintext letters
    std::vector<int> stl(s);     // symbol -> letter
    std::vector<int> frq(A + 1, 0);
    std::vector<uint8_t> ngr(al);     // per-window score
    std::vector<uint8_t> scratch(al); // candidate per-window score

    // random initial key
    for (int i = 0; i < s; i++) stl[i] = rng.below(A);
    for (int i = 0; i < l; i++) sol[i] = stl[c.cipher[i]];
    for (int i = 0; i < s; i++) frq[stl[i]] += c.mape2[i];

    double entropy = 0;
    for (int a = 0; a < A; a++) entropy += c.enttable[frq[a]];

    // linear index of a window
    auto score_window = [&](int w) -> uint8_t {
        size_t li = 0;
        for (int k = 0; k < n; k++) li = li * (size_t)A + (size_t)sol[w + k];
        return g[li];
    };

    long long new_ngram_score = 0;
    for (int w = 0; w < al; w++) {
        ngr[w] = score_window(w);
        new_ngram_score += ngr[w];
    }

    double old_score = 0;
    double new_score = 0;
    double best_score = 0;
    out_key = stl;

    double temp = c.start_temp;
    double temp_min = temp / (double)iterations;
    int accept = 1;

    // symbol visitation order, reshuffled each pass
    std::vector<int> order(s);
    for (int i = 0; i < s; i++) order[i] = i;
    int mi = s;  // forces a shuffle + reset on first use

    for (long long it = 0; it < iterations; it++) {
        if (mi >= s) {
            for (int i = s - 1; i > 0; i--) std::swap(order[i], order[rng.below(i + 1)]);
            mi = 0;
        }
        int curr = order[mi++];

        if (!accept && new_score != 0.0)
            old_score -= temp * c.pos_count[curr] * c.onesixl * old_score / new_score;
        temp -= temp_min;

        int old_letter = stl[curr];
        int new_letter = rng.below(A);
        if (new_letter == old_letter) new_letter = (new_letter + 1 + rng.below(A - 1)) % A;

        // Apply the new letter to every position of this symbol, touching only the
        // affected windows' cells (O(affected) rather than O(l)).
        for (int wi = c.win_off[curr]; wi < c.win_off[curr + 1]; wi++) {
            int w = c.win_idx[wi];
            for (int k = 0; k < n; k++)
                if (c.cipher[w + k] == curr) sol[w + k] = new_letter;
        }

        double old_entropy = entropy;
        int wgt = c.mape2[curr];
        entropy += c.enttable[frq[old_letter] - wgt] - c.enttable[frq[old_letter]];
        entropy += c.enttable[frq[new_letter] + wgt] - c.enttable[frq[new_letter]];

        long long old_ngram = new_ngram_score;
        long long delta = 0;
        for (int wi = c.win_off[curr]; wi < c.win_off[curr + 1]; wi++) {
            int w = c.win_idx[wi];
            uint8_t nv = score_window(w);
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
            for (int wi = c.win_off[curr]; wi < c.win_off[curr + 1]; wi++) {
                int w = c.win_idx[wi];
                ngr[w] = scratch[w];
            }
            old_score = new_score;
            if (new_score > best_score) {
                best_score = new_score;
                out_key = stl;
            }
        } else {
            accept = 0;
            new_ngram_score = old_ngram;
            entropy = old_entropy;
            for (int wi = c.win_off[curr]; wi < c.win_off[curr + 1]; wi++) {
                int w = c.win_idx[wi];
                for (int k = 0; k < n; k++)
                    if (c.cipher[w + k] == curr) sol[w + k] = old_letter;
            }
        }
    }
    return best_score;
}

SolveResult solve_cpu(const SolverCtx& ctx, const SolveParams& p) {
#ifdef _OPENMP
    if (p.threads > 0) omp_set_num_threads(p.threads);
#endif

    SolveResult best;
    best.score = -1;

#pragma omp parallel
    {
        std::vector<int> local_key;
        double local_best = -1;
        std::vector<int> local_best_key;

#pragma omp for schedule(dynamic)
        for (int r = 0; r < p.restarts; r++) {
            double sc = anneal_once(ctx, p.iterations, p.seed + (uint64_t)r * 0x1000193ULL,
                                    local_key);
            if (sc > local_best) {
                local_best = sc;
                local_best_key = local_key;
            }
        }

#pragma omp critical
        {
            if (local_best > best.score) {
                best.score = local_best;
                best.key = local_best_key;
            }
        }
    }

    // decode
    best.plaintext.resize(ctx.l);
    best.text.resize(ctx.l);
    for (int i = 0; i < ctx.l; i++) {
        int letter = best.key[ctx.cipher[i]];
        best.plaintext[i] = letter;
        best.text[i] = ctx.ng->alphabet[letter];
    }
    return best;
}
