#pragma once
#include <cstdint>
#include <string>
#include <vector>

// Gematria Primus: the 29-rune alphabet of the Liber Primus. Each rune maps to a
// Latin letter/digraph (display form) and a prime, in canonical index order 0..28.
namespace gematria {

constexpr int N = 29;  // alphabet size

// Display Latin for each rune index 0..28 (the form used in the solved transcriptions,
// e.g. U for the U/V rune, C for the C/K rune, S for the S/Z rune).
extern const char* const LATIN[N];
// Prime value for each rune index.
extern const int PRIME[N];
// UTF-8 bytes of each rune glyph, index 0..28.
extern const char* const RUNE_UTF8[N];

// A parsed token from a rune string: either a rune (idx 0..28) or a separator.
struct Token {
    int rune;   // 0..28 for a rune, or -1 if this is a separator
    char sep;   // separator display char (' ', '.', ',', ';', '#') when rune==-1, else 0
};

// Parse a UTF-8 rune string into tokens (runes + separators), ignoring any other chars
// (newlines, quotes, apostrophes used as "unknown" markers, etc.).
std::vector<Token> parse(const std::string& utf8);

// Convenience: just the rune indices (separators dropped).
std::vector<int> parse_runes(const std::string& utf8);

// Transliterate a token stream to Latin text (runes -> LATIN, separators -> their char).
std::string to_latin(const std::vector<Token>& toks);

// Encode rune indices back to a UTF-8 rune string (no separators).
std::string to_runes(const std::vector<int>& idx);

// Gematria sum: total of the prime values of all runes in the token stream.
long long gematria_sum(const std::vector<Token>& toks);

}  // namespace gematria
