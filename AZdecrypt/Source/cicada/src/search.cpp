#include "search.hpp"

#include <cmath>
#include <random>

#include "transforms.hpp"

namespace lp {

namespace {
struct Rng {
    std::mt19937_64 g;
    explicit Rng(uint64_t s) : g(s) {}
    int below(int n) { return (int)(g() % (uint64_t)n); }
    double unit() { return (g() >> 11) * (1.0 / 9007199254740992.0); }
};

// Decrypt with a Vigenere key (optionally honoring an interrupter rune).
void vig_decrypt_into(const std::vector<int>& c, const std::vector<int>& key, int interrupt,
                      std::vector<int>& out) {
    out.resize(c.size());
    size_t kp = 0;
    for (size_t i = 0; i < c.size(); i++) {
        if (interrupt >= 0 && c[i] == interrupt) { out[i] = c[i]; continue; }
        int k = key[kp % key.size()];
        out[i] = ((c[i] - k) % N + N) % N;
        kp++;
    }
}
}  // namespace

VigResult vigenere_crack(const std::vector<int>& cipher, const RuneModel& model, int min_len,
                         int max_len, int restarts, int interrupt, uint64_t seed) {
    VigResult best;
    best.score = -1e300;
    std::vector<int> plain;

    for (int L = min_len; L <= max_len; L++) {
        for (int r = 0; r < restarts; r++) {
            Rng rng(seed + (uint64_t)L * 1000003ULL + (uint64_t)r * 97ULL);
            std::vector<int> key(L);
            for (int i = 0; i < L; i++) key[i] = rng.below(N);
            vig_decrypt_into(cipher, key, interrupt, plain);
            double cur = model.score(plain);

            // Annealed hillclimb on individual key positions.
            long long iters = 4000LL * L;
            double temp = 4.0;
            double tmin = temp / iters;
            for (long long it = 0; it < iters; it++) {
                int pos = rng.below(L);
                int old = key[pos];
                int nv = rng.below(N);
                if (nv == old) continue;
                key[pos] = nv;
                vig_decrypt_into(cipher, key, interrupt, plain);
                double s = model.score(plain);
                if (s > cur || rng.unit() < std::exp((s - cur) / temp)) {
                    cur = s;
                } else {
                    key[pos] = old;  // revert
                }
                temp -= tmin;
            }
            vig_decrypt_into(cipher, key, interrupt, plain);
            cur = model.score(plain);
            if (cur > best.score) {
                best.score = cur;
                best.key = key;
                best.key_len = L;
                best.plain = plain;
            }
        }
    }
    return best;
}

SubResult substitution_solve(const std::vector<int>& cipher, const RuneModel& model,
                             int restarts, long long iters, uint64_t seed) {
    SubResult best;
    best.score = -1e300;
    std::vector<int> plain(cipher.size());

    auto apply = [&](const std::vector<int>& map) {
        for (size_t i = 0; i < cipher.size(); i++) plain[i] = map[cipher[i]];
    };

    for (int r = 0; r < restarts; r++) {
        Rng rng(seed + (uint64_t)r * 2654435761ULL);
        std::vector<int> map(N);
        for (int i = 0; i < N; i++) map[i] = rng.below(N);
        apply(map);
        double cur = model.score(plain);
        double temp = 6.0;
        double tmin = temp / iters;
        for (long long it = 0; it < iters; it++) {
            int sym = rng.below(N);
            int old = map[sym];
            int nv = rng.below(N);
            if (nv == old) continue;
            map[sym] = nv;
            apply(map);
            double s = model.score(plain);
            if (s > cur || rng.unit() < std::exp((s - cur) / temp)) {
                cur = s;
            } else {
                map[sym] = old;
            }
            temp -= tmin;
        }
        apply(map);
        cur = model.score(plain);
        if (cur > best.score) {
            best.score = cur;
            best.map = map;
            best.plain = plain;
        }
    }
    return best;
}

}  // namespace lp
