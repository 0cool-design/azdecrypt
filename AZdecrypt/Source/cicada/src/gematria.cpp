#include "gematria.hpp"

#include <cstring>
#include <unordered_map>

namespace gematria {

const char* const LATIN[N] = {"F",  "U", "TH", "O",  "R", "C",  "G",  "W",  "H", "N",
                              "I",  "J", "EO", "P",  "X", "S",  "T",  "B",  "E", "M",
                              "L",  "NG","OE", "D",  "A", "AE", "Y",  "IA", "EA"};

const int PRIME[N] = {2,  3,  5,  7,  11, 13, 17, 19, 23, 29,  31,  37,  41, 43, 47,
                      53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109};

// Runic block glyphs (each 3 bytes in UTF-8), index order matching LATIN/PRIME.
const char* const RUNE_UTF8[N] = {
    "ᚠ", "ᚢ", "ᚦ", "ᚩ", "ᚱ", "ᚳ", "ᚷ", "ᚹ", "ᚻ", "ᚾ", "ᛁ", "ᛄ", "ᛇ", "ᛈ", "ᛉ",
    "ᛋ", "ᛏ", "ᛒ", "ᛖ", "ᛗ", "ᛚ", "ᛝ", "ᛟ", "ᛞ", "ᚪ", "ᚫ", "ᚣ", "ᛡ", "ᛠ"};

namespace {

// Decode one UTF-8 codepoint starting at s[i]; advance i past it. Returns the codepoint,
// or 0xFFFD on a malformed byte (and advances one byte).
uint32_t next_cp(const std::string& s, size_t& i) {
    unsigned char c = (unsigned char)s[i];
    if (c < 0x80) { i += 1; return c; }
    if ((c >> 5) == 0x6 && i + 1 < s.size()) {
        uint32_t cp = ((c & 0x1F) << 6) | ((unsigned char)s[i + 1] & 0x3F);
        i += 2;
        return cp;
    }
    if ((c >> 4) == 0xE && i + 2 < s.size()) {
        uint32_t cp = ((c & 0x0F) << 12) | (((unsigned char)s[i + 1] & 0x3F) << 6) |
                      ((unsigned char)s[i + 2] & 0x3F);
        i += 3;
        return cp;
    }
    if ((c >> 3) == 0x1E && i + 3 < s.size()) {
        uint32_t cp = ((c & 0x07) << 18) | (((unsigned char)s[i + 1] & 0x3F) << 12) |
                      (((unsigned char)s[i + 2] & 0x3F) << 6) | ((unsigned char)s[i + 3] & 0x3F);
        i += 4;
        return cp;
    }
    i += 1;
    return 0xFFFD;
}

// Codepoint -> rune index (0..28), built once from RUNE_UTF8.
const std::unordered_map<uint32_t, int>& rune_cp_map() {
    static const std::unordered_map<uint32_t, int> m = [] {
        std::unordered_map<uint32_t, int> t;
        for (int i = 0; i < N; i++) {
            size_t p = 0;
            std::string g = RUNE_UTF8[i];
            t[next_cp(g, p)] = i;
        }
        return t;
    }();
    return m;
}

// Separator codepoints used in the Liber Primus transcriptions.
char sep_for(uint32_t cp) {
    switch (cp) {
        case 0x2022: return ' ';  // • word break
        case 0x2058: return '.';  // ⁘
        case 0x205A: return ',';  // ⁚
        case 0x2056: return ';';  // ⁖
        case 0x205C: return '#';  // ⁜ section break
        case 0x000A: return '\n'; // newline (preserve line layout)
        default: return 0;
    }
}

}  // namespace

std::vector<Token> parse(const std::string& utf8) {
    const auto& rm = rune_cp_map();
    std::vector<Token> out;
    size_t i = 0;
    while (i < utf8.size()) {
        uint32_t cp = next_cp(utf8, i);
        auto it = rm.find(cp);
        if (it != rm.end()) {
            out.push_back({it->second, 0});
        } else if (char s = sep_for(cp)) {
            out.push_back({-1, s});
        }
        // anything else (quotes, apostrophes marking unknowns) is ignored
    }
    return out;
}

std::vector<int> parse_runes(const std::string& utf8) {
    std::vector<int> out;
    for (const Token& t : parse(utf8))
        if (t.rune >= 0) out.push_back(t.rune);
    return out;
}

std::string to_latin(const std::vector<Token>& toks) {
    std::string out;
    for (const Token& t : toks) {
        if (t.rune >= 0)
            out += LATIN[t.rune];
        else
            out += t.sep;
    }
    return out;
}

std::string to_runes(const std::vector<int>& idx) {
    std::string out;
    for (int r : idx)
        if (r >= 0 && r < N) out += RUNE_UTF8[r];
    return out;
}

long long gematria_sum(const std::vector<Token>& toks) {
    long long s = 0;
    for (const Token& t : toks)
        if (t.rune >= 0) s += PRIME[t.rune];
    return s;
}

}  // namespace gematria
