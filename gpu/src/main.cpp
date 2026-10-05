#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

#include "cipher.hpp"
#include "ngram.hpp"
#include "solver.hpp"

// Raw n-gram score of a letter-index sequence: sum of table values over all
// length-n windows. Mirrors the "ngram_score" accumulation in the original.
static long long ngram_score(const NgramTable& t, const std::vector<int>& idx) {
    const int n = t.n;
    const int A = t.alpha_size;
    long long s = 0;
    for (int i = 0; i + n <= (int)idx.size(); i++) {
        size_t li = 0;
        for (int k = 0; k < n; k++) li = li * (size_t)A + (size_t)idx[i + k];
        s += t.table[li];
    }
    return s;
}

static int cmd_score(int argc, char** argv) {
    if (argc < 4) {
        std::fprintf(stderr,
                     "usage: azgpu score <ngrams.gz> <cipher.txt> <solution.txt>\n");
        return 2;
    }
    NgramTable t = load_ngrams(argv[1]);
    std::printf("n-grams: n=%d alphabet='%s' (size %d) factor=%.4f entweight=%.2f temp=%.0f\n",
                t.n, t.alphabet.c_str(), t.alpha_size, t.ngram_factor, t.entropy_weight,
                t.temperature);
    std::printf("         table cells=%zu highgram=%d\n", t.table.size(), t.highgram);

    Cipher c = load_cipher(argv[2]);
    std::printf("cipher:  length=%d symbols=%d grid=%dx%d\n", c.length, c.n_symbols,
                c.dim_x, c.dim_y);

    std::vector<int> sol = load_plaintext_indices(argv[3], t.alpharev);
    std::printf("solution: %d letters\n", (int)sol.size());

    int windows = (int)sol.size() - (t.n - 1);
    if (windows <= 0) {
        std::fprintf(stderr, "solution too short for %d-grams\n", t.n);
        return 1;
    }

    long long sol_score = ngram_score(t, sol);

    // Baseline: a random symbol->letter mapping applied to the cipher.
    std::mt19937 rng(12345);
    std::uniform_int_distribution<int> pick(0, t.alpha_size - 1);
    std::vector<int> map(c.n_symbols);
    for (int& m : map) m = pick(rng);
    std::vector<int> dec(c.length);
    for (int i = 0; i < c.length; i++) dec[i] = map[c.seq[i]];
    long long rnd_score = ngram_score(t, dec);
    int cwindows = c.length - (t.n - 1);

    std::printf("\n%-22s raw=%-12lld  avg/window=%.2f\n", "known solution:", sol_score,
                (double)sol_score / windows);
    std::printf("%-22s raw=%-12lld  avg/window=%.2f\n", "random mapping:", rnd_score,
                (double)rnd_score / cwindows);
    std::printf(
        "\nThe known English plaintext should score far higher per window than a\n"
        "random mapping. If so, the n-gram table load + indexing are correct.\n");
    return 0;
}

static void print_grid(const std::string& text, int dim_x) {
    if (dim_x <= 0) dim_x = (int)text.size();
    for (int i = 0; i < (int)text.size(); i += dim_x)
        std::printf("  %s\n", text.substr(i, dim_x).c_str());
}

static int cmd_solve(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr,
                     "usage: azgpu solve <ngrams.gz> <cipher.txt> "
                     "[iterations] [restarts] [threads]\n");
        return 2;
    }
    NgramTable t = load_ngrams(argv[1]);
    Cipher c = load_cipher(argv[2]);

    SolveParams p;
    if (argc > 3) p.iterations = std::atoll(argv[3]);
    if (argc > 4) p.restarts = std::atoi(argv[4]);
    if (argc > 5) p.threads = std::atoi(argv[5]);

    std::printf("solving %s: length=%d symbols=%d grid=%dx%d with %d-grams\n", argv[2],
                c.length, c.n_symbols, c.dim_x, c.dim_y, t.n);
    std::printf("iterations/restart=%lld restarts=%d\n", p.iterations, p.restarts);

    SolverCtx ctx(c, t, p.multiplicity_weight);
    SolveResult r = solve_cpu(ctx, p);

    std::printf("\nbest score = %.2f\n", r.score);
    print_grid(r.text, c.dim_x);
    return 0;
}

#ifdef USE_CUDA
static int cmd_gsolve(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr,
                     "usage: azgpu gsolve <ngrams.gz> <cipher.txt> "
                     "[iterations] [restarts]\n");
        return 2;
    }
    NgramTable t = load_ngrams(argv[1]);
    Cipher c = load_cipher(argv[2]);

    SolveParams p;
    if (argc > 3) p.iterations = std::atoll(argv[3]);
    if (argc > 4) p.restarts = std::atoi(argv[4]);

    std::printf("GPU solving %s: length=%d symbols=%d grid=%dx%d with %d-grams\n", argv[2],
                c.length, c.n_symbols, c.dim_x, c.dim_y, t.n);
    std::printf("iterations/restart=%lld restarts=%d\n", p.iterations, p.restarts);

    SolverCtx ctx(c, t, p.multiplicity_weight);
    SolveResult r = solve_gpu(ctx, p);

    std::printf("\nbest score = %.2f\n", r.score);
    print_grid(r.text, c.dim_x);
    return 0;
}
#endif

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: azgpu <command> ...\n  commands: score solve gsolve\n");
        return 2;
    }
    try {
        if (std::strcmp(argv[1], "score") == 0) return cmd_score(argc - 1, argv + 1);
        if (std::strcmp(argv[1], "solve") == 0) return cmd_solve(argc - 1, argv + 1);
#ifdef USE_CUDA
        if (std::strcmp(argv[1], "gsolve") == 0) return cmd_gsolve(argc - 1, argv + 1);
#endif
        std::fprintf(stderr, "unknown command: %s\n", argv[1]);
        return 2;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "error: %s\n", e.what());
        return 1;
    }
}
