#include "transforms.hpp"

#include <algorithm>
#include <cctype>
#include <utility>

namespace lp {

std::vector<int> atbash(const std::vector<int>& in) {
    std::vector<int> out(in.size());
    for (size_t i = 0; i < in.size(); i++) out[i] = N - 1 - in[i];
    return out;
}

std::vector<int> caesar(const std::vector<int>& in, int shift, bool decrypt) {
    std::vector<int> out(in.size());
    int s = decrypt ? -shift : shift;
    for (size_t i = 0; i < in.size(); i++) out[i] = mod29(in[i] + s);
    return out;
}

std::vector<int> vigenere(const std::vector<int>& in, const std::vector<int>& key,
                          bool decrypt, int interrupt) {
    std::vector<int> out(in.size());
    if (key.empty()) return in;
    size_t kp = 0;
    for (size_t i = 0; i < in.size(); i++) {
        int c = in[i];
        if (interrupt >= 0 && c == interrupt) {
            out[i] = c;  // interrupter passes through, key does not advance
            continue;
        }
        int k = key[kp % key.size()];
        out[i] = decrypt ? mod29(c - k) : mod29(c + k);
        kp++;
    }
    return out;
}

std::vector<int> keystream(const std::vector<int>& in, const std::vector<long long>& stream,
                           bool decrypt, int offset) {
    std::vector<int> out(in.size());
    for (size_t i = 0; i < in.size(); i++) {
        long long sv = stream.empty() ? 0 : stream[(offset + i) % stream.size()];
        int k = (int)(((sv % N) + N) % N);
        out[i] = decrypt ? mod29(in[i] - k) : mod29(in[i] + k);
    }
    return out;
}

namespace {
std::vector<long long> first_primes(int n) {
    std::vector<long long> p;
    for (long long cand = 2; (int)p.size() < n; cand++) {
        bool prime = true;
        for (long long d = 2; d * d <= cand; d++)
            if (cand % d == 0) { prime = false; break; }
        if (prime) p.push_back(cand);
    }
    return p;
}
}  // namespace

std::vector<long long> primes_stream(int n) { return first_primes(n); }

std::vector<long long> totient_primes_stream(int n) {
    std::vector<long long> p = first_primes(n);
    for (auto& v : p) v -= 1;  // phi(prime) = prime - 1
    return p;
}

std::vector<int> key_from_latin(const std::string& s) {
    // Longest-match Latin -> rune index, honoring digraphs and alternate spellings.
    static const std::vector<std::pair<std::string, int>> MAP = {
        {"ING", 21}, {"TH", 2}, {"EO", 12}, {"OE", 22}, {"AE", 25}, {"IA", 27},
        {"IO", 27},  {"EA", 28}, {"NG", 21}, {"F", 0},  {"U", 1},  {"V", 1},
        {"O", 3},    {"R", 4},  {"C", 5},   {"K", 5},   {"G", 6},  {"W", 7},
        {"H", 8},    {"N", 9},  {"I", 10},  {"J", 11},  {"P", 13}, {"X", 14},
        {"S", 15},   {"Z", 15}, {"T", 16},  {"B", 17},  {"E", 18}, {"M", 19},
        {"L", 20},   {"D", 23}, {"A", 24},  {"Y", 26}};
    std::string up;
    for (char c : s)
        if (std::isalpha((unsigned char)c)) up += (char)std::toupper((unsigned char)c);

    std::vector<int> out;
    size_t i = 0;
    while (i < up.size()) {
        bool matched = false;
        for (const auto& [lat, idx] : MAP) {
            if (up.compare(i, lat.size(), lat) == 0) {
                out.push_back(idx);
                i += lat.size();
                matched = true;
                break;
            }
        }
        if (!matched) i++;  // skip anything unmappable
    }
    return out;
}

}  // namespace lp
