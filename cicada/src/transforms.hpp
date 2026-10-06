#pragma once
#include <string>
#include <vector>

#include "gematria.hpp"

// Cipher transforms over Gematria Primus rune indices (0..28), covering the methods used
// on the solved Liber Primus pages. All operate mod 29.
namespace lp {

constexpr int N = gematria::N;  // 29

inline int mod29(int x) { return ((x % N) + N) % N; }

// Atbash: reverse the 29-rune alphabet (idx -> 28 - idx). Self-inverse.
std::vector<int> atbash(const std::vector<int>& in);

// Caesar / fixed shift. decrypt: idx - shift; encrypt: idx + shift (mod 29).
std::vector<int> caesar(const std::vector<int>& in, int shift, bool decrypt);

// Vigenere over rune indices with a key given as rune indices.
//   decrypt: p = (c - k) mod 29      encrypt: c = (p + k) mod 29
// Interrupt (F-rune "skip") rule: when a ciphertext rune equals `interrupt` (default 0 = F),
// it is passed through unchanged and the key position does NOT advance. Set interrupt < 0
// to disable. The same rule is applied on encrypt for round-trip symmetry.
std::vector<int> vigenere(const std::vector<int>& in, const std::vector<int>& key,
                          bool decrypt, int interrupt = 0);

// Keystream cipher from an arbitrary integer stream (e.g. primes or totients), each value
// taken mod 29. decrypt subtracts, encrypt adds. `offset` skips leading stream elements.
std::vector<int> keystream(const std::vector<int>& in, const std::vector<long long>& stream,
                           bool decrypt, int offset = 0);

// Build the totient keystream phi(p_i) = p_i - 1 for the i-th prime (primes are prime,
// so phi(prime) = prime - 1). Length `n`.
std::vector<long long> totient_primes_stream(int n);

// Build the prime keystream p_i (the i-th prime). Length `n`.
std::vector<long long> primes_stream(int n);

// Parse a Latin key string (e.g. "DIVINITY") into rune indices using the Gematria mapping.
std::vector<int> key_from_latin(const std::string& s);

}  // namespace lp
