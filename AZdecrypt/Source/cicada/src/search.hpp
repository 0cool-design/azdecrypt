#pragma once
#include <cstdint>
#include <string>
#include <vector>

#include "score.hpp"

// Automated hypothesis-testing attacks on Liber Primus pages. These are standard
// cryptanalytic searches scored by the rune language model — a faster way to test ideas,
// NOT a guaranteed solver (the unsolved LP pages have resisted years of such attacks).
namespace lp {

struct VigResult {
    int key_len = 0;
    std::vector<int> key;   // rune indices
    double score = 0;
    std::vector<int> plain; // decrypted rune indices
};

// Hillclimb (annealed) the Vigenere key for each length in [min_len, max_len], return best.
// `restarts` random restarts per length. interrupt rune index, or -1 to disable.
VigResult vigenere_crack(const std::vector<int>& cipher, const RuneModel& model, int min_len,
                         int max_len, int restarts, int interrupt, uint64_t seed);

// Hillclimb a free 29->29 symbol substitution (not necessarily a permutation), scored by
// the model. Returns the best mapping applied to the cipher.
struct SubResult {
    std::vector<int> map;   // 29 entries: cipher symbol -> plaintext rune
    double score = 0;
    std::vector<int> plain;
};
SubResult substitution_solve(const std::vector<int>& cipher, const RuneModel& model,
                             int restarts, long long iters, uint64_t seed);

}  // namespace lp
