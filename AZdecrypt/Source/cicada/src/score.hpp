#pragma once
#include <string>
#include <vector>

// Rune language model: log-probability n-gram scoring over the 29-rune alphabet, loaded
// from the relikd LiberPrayground rune n-gram counts (data/rune-Ngram.txt). Used to rank
// candidate decryptions of unsolved pages.
namespace lp {

struct RuneModel {
    int n = 0;
    std::vector<float> logp;  // size 29^n, natural-log probability (unseen -> floor)
    double floor_lp = 0;

    double score(const std::vector<int>& idx) const;  // sum of window log-probs
};

// Load an n-gram model from a counts file: each line "<n runes> <count>".
RuneModel load_rune_model(const std::string& path, int n);

// Index of coincidence over 29 symbols.
double ioc(const std::vector<int>& idx);

}  // namespace lp
