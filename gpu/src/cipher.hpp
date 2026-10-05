#pragma once
#include <cstdint>
#include <string>
#include <vector>

// A loaded cipher: a sequence of symbols (0..n_symbols-1) laid out in a grid.
// First-milestone parser: one byte = one symbol (correct for the Zodiac ciphers).
struct Cipher {
    int length = 0;                 // number of symbols
    int n_symbols = 0;              // distinct symbols
    int dim_x = 0, dim_y = 0;       // grid width / height
    std::vector<int> seq;           // length `length`, each 0..n_symbols-1
    std::vector<char> symbol_glyph; // n_symbols: the glyph each id came from
};

// Load a cipher grid from a text file. Throws std::runtime_error on failure.
Cipher load_cipher(const std::string& path);

// Load a plaintext solution and return its letters mapped to alphabet indices
// (via alpharev), skipping any character not in the alphabet.
std::vector<int> load_plaintext_indices(const std::string& path, const int alpharev[256]);
