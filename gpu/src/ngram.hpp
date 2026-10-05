#pragma once
#include <cstdint>
#include <string>
#include <vector>

// A loaded letter n-gram scoring table, matching AZdecrypt's default ("ngram_system=1")
// letter n-gram format. One byte (0..255) per table cell: a log-probability score.
struct NgramTable {
    int n = 0;                 // n-gram size (we target 6)
    int alpha_size = 0;        // alphabet size (26 for English)
    std::string alphabet;      // e.g. "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    double ngram_factor = 0;   // from .ini
    double entropy_weight = 0; // from .ini
    double temperature = 0;    // from .ini
    int highgram = 0;          // max value seen (== highgram(ngram_size) in the original)

    std::vector<uint8_t> table; // size = alpha_size^n, row-major (last index contiguous)

    // alpharev[c] = index of ASCII char c in the alphabet, or -1 if not present.
    int alpharev[256];

    // Linear index for a 6-gram given letter indices.
    inline size_t index6(int x1, int x2, int x3, int x4, int x5, int x6) const {
        const size_t A = (size_t)alpha_size;
        return ((((((size_t)x1 * A + x2) * A + x3) * A + x4) * A + x5) * A + x6);
    }

    inline uint8_t at6(int x1, int x2, int x3, int x4, int x5, int x6) const {
        return table[index6(x1, x2, x3, x4, x5, x6)];
    }
};

// Loads the n-gram table from a .gz payload (its .ini sidecar must sit next to it).
// Throws std::runtime_error on failure. Currently supports the default letter system,
// n=2..6, text or binary payload (auto-detected, exactly like the original).
NgramTable load_ngrams(const std::string& gz_path);
