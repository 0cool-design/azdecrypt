#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

#include "gematria.hpp"
#include "score.hpp"
#include "search.hpp"
#include "transforms.hpp"

using namespace lp;

// Transliterate rune indices to Latin for display (no separators).
static std::string latin_of(const std::vector<int>& idx) {
    std::vector<gematria::Token> t;
    for (int r : idx) t.push_back({r, 0});
    return gematria::to_latin(t);
}

static std::string read_file(const std::string& p) {
    std::ifstream f(p, std::ios::binary);
    if (!f) { std::fprintf(stderr, "cannot open %s\n", p.c_str()); std::exit(1); }
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

static int cmd_translit(int argc, char** argv) {
    if (argc < 1) { std::fprintf(stderr, "usage: cicada translit <file>\n"); return 2; }
    std::string raw = read_file(argv[0]);
    auto toks = gematria::parse(raw);
    std::printf("%s\n", gematria::to_latin(toks).c_str());
    std::fprintf(stderr, "[%zu runes, gematria sum %lld]\n",
                 gematria::parse_runes(raw).size(), gematria::gematria_sum(toks));
    return 0;
}

static int cmd_stats(int argc, char** argv) {
    if (argc < 1) { std::fprintf(stderr, "usage: cicada stats <file>\n"); return 2; }
    auto idx = gematria::parse_runes(read_file(argv[0]));
    long long f[29] = {0};
    for (int r : idx) f[r]++;
    std::printf("runes=%zu  IoC=%.4f  (random 29-sym IoC ~= %.4f)\n", idx.size(), ioc(idx),
                1.0 / 29);
    std::printf("frequencies (rune: Latin count):\n");
    for (int i = 0; i < 29; i++)
        std::printf("  %2d %-3s %lld\n", i, gematria::LATIN[i], f[i]);
    return 0;
}

static int cmd_decode(int argc, char** argv) {
    // cicada decode <file> <method> [args...]
    //   atbash
    //   caesar <shift>
    //   vigenere <KEY> [interrupt_rune_index|-1]
    //   totient [offset]
    //   primes  [offset]
    if (argc < 2) {
        std::fprintf(stderr,
                     "usage: cicada decode <file> <atbash|caesar|vigenere|totient|primes> "
                     "[args]\n");
        return 2;
    }
    std::string raw = read_file(argv[0]);
    auto toks = gematria::parse(raw);
    std::vector<int> idx;
    for (auto& t : toks) if (t.rune >= 0) idx.push_back(t.rune);

    std::string method = argv[1];
    std::vector<int> out;
    if (method == "atbash") {
        out = atbash(idx);
    } else if (method == "caesar") {
        int sh = argc > 2 ? std::atoi(argv[2]) : 0;
        out = caesar(idx, sh, true);
    } else if (method == "vigenere") {
        if (argc < 3) { std::fprintf(stderr, "vigenere needs a KEY\n"); return 2; }
        auto key = key_from_latin(argv[2]);
        int interrupt = argc > 3 ? std::atoi(argv[3]) : 0;
        out = vigenere(idx, key, true, interrupt);
        std::fprintf(stderr, "[key '%s' -> %zu runes, interrupt=%d]\n", argv[2], key.size(),
                     interrupt);
    } else if (method == "totient" || method == "primes") {
        auto stream = method == "totient" ? totient_primes_stream((int)idx.size() + 8)
                                          : primes_stream((int)idx.size() + 8);
        int off = argc > 2 ? std::atoi(argv[2]) : 0;
        out = keystream(idx, stream, true, off);
    } else {
        std::fprintf(stderr, "unknown method: %s\n", method.c_str());
        return 2;
    }

    // Re-emit with the original separators interleaved for readability.
    std::string latin;
    size_t ri = 0;
    for (auto& t : toks) {
        if (t.rune >= 0) latin += gematria::LATIN[out[ri++]];
        else latin += t.sep;
    }
    std::printf("%s\n", latin.c_str());
    return 0;
}

// Built-in validation: page 0 ("A Warning") is plaintext, so transliteration must match the
// published reading exactly. Proves the Gematria table, UTF-8 parsing, and separators.
static int cmd_selftest(int, char**) {
    struct Case { const char* runes; const char* expect; };
    const Case cases[] = {
        {"ᚪ•ᚹᚪᚱᚾᛝ⁜", "A WARNNG#"},
        {"ᛒᛖᛚᛁᛖᚢᛖ•ᚾᚩᚦᛝ•ᚠᚱᚩᛗ•ᚦᛁᛋ•ᛒᚩᚩᚳ⁘", "BELIEUE NOTHNG FROM THIS BOOC."},
        {"ᛖᛉᚳᛖᛈᛏ•ᚹᚻᚪᛏ•ᚣᚩᚢ•ᚳᚾᚩᚹ•ᛏᚩ•ᛒᛖ•ᛏᚱᚢᛖ⁘",
         "EXCEPT WHAT YOU CNOW TO BE TRUE."},
    };
    int fails = 0;
    for (auto& c : cases) {
        std::string got = gematria::to_latin(gematria::parse(c.runes));
        bool ok = got == c.expect;
        std::printf("[%s] %s\n      expected: %s\n", ok ? "PASS" : "FAIL", got.c_str(),
                    c.expect);
        if (!ok) fails++;
    }
    // Pure Vigenere (no interrupter) must be perfectly invertible: decrypt(encrypt(pt))==pt.
    // The F-skip interrupter is a decrypt-side convention keyed on specific ciphertext
    // positions, so it is validated by decoding a real page, not by round-trip.
    {
        std::vector<int> pt = gematria::parse_runes("ᚹᛖᛚᚳᚩᛗᛖᚦᛁᛋᛁᛋᚪᛏᛖᛋᛏ");
        auto key = key_from_latin("DIVINITY");
        auto ct = vigenere(pt, key, false, -1);
        auto back = vigenere(ct, key, true, -1);
        bool ok = back == pt && ct != pt;
        std::printf("[%s] vigenere round-trip (key DIVINITY)\n", ok ? "PASS" : "FAIL");
        if (!ok) fails++;
    }
    std::printf("%s\n", fails ? "SELFTEST FAILED" : "ALL TESTS PASSED");
    return fails ? 1 : 0;
}

static RuneModel load_model(int n) {
    char path[256];
    std::snprintf(path, sizeof(path), "data/rune-%dgram.txt", n);
    return load_rune_model(path, n);
}

static int cmd_vigcrack(int argc, char** argv) {
    // cicada vigcrack <file> [maxlen=16] [ngram=3] [restarts=6] [interrupt=-1]
    if (argc < 1) {
        std::fprintf(stderr,
                     "usage: cicada vigcrack <file> [maxlen=16] [ngram=3] [restarts=6] "
                     "[interrupt=-1]\n");
        return 2;
    }
    auto idx = gematria::parse_runes(read_file(argv[0]));
    int maxlen = argc > 1 ? std::atoi(argv[1]) : 16;
    int n = argc > 2 ? std::atoi(argv[2]) : 3;
    int restarts = argc > 3 ? std::atoi(argv[3]) : 6;
    int interrupt = argc > 4 ? std::atoi(argv[4]) : -1;

    RuneModel model = load_model(n);
    std::fprintf(stderr, "[%zu runes, %d-gram model, key lengths 1..%d x %d restarts]\n",
                 idx.size(), n, maxlen, restarts);
    VigResult r = vigenere_crack(idx, model, 1, maxlen, restarts, interrupt, 1);

    std::printf("best key length = %d   score = %.1f\n", r.key_len, r.score);
    std::printf("key (Latin)      = %s\n", latin_of(r.key).c_str());
    std::printf("plaintext        = %s\n", latin_of(r.plain).c_str());
    std::fprintf(stderr,
                 "NOTE: this is a best-fit hypothesis from a statistical search, not a\n"
                 "confirmed solve. Readable English indicates success; gibberish does not.\n");
    return 0;
}

static int cmd_subsolve(int argc, char** argv) {
    // cicada subsolve <file> [ngram=3] [restarts=30] [iters=200000]
    if (argc < 1) {
        std::fprintf(stderr, "usage: cicada subsolve <file> [ngram=3] [restarts=30] "
                             "[iters=200000]\n");
        return 2;
    }
    auto idx = gematria::parse_runes(read_file(argv[0]));
    int n = argc > 1 ? std::atoi(argv[1]) : 3;
    int restarts = argc > 2 ? std::atoi(argv[2]) : 30;
    long long iters = argc > 3 ? std::atoll(argv[3]) : 200000;

    RuneModel model = load_model(n);
    std::fprintf(stderr, "[%zu runes, %d-gram model, %d restarts x %lld iters]\n", idx.size(),
                 n, restarts, iters);
    SubResult r = substitution_solve(idx, model, restarts, iters, 1);
    std::printf("score     = %.1f\n", r.score);
    std::printf("plaintext = %s\n", latin_of(r.plain).c_str());
    std::fprintf(stderr, "NOTE: hypothesis from a statistical search, not a confirmed solve.\n");
    return 0;
}

// Controlled validation of the search harness: take real English-in-runes (the solved
// warning passage), encrypt it with a known Vigenere key, and confirm vigcrack recovers
// readable plaintext. Proves the search works on a case we know the answer to.
static int cmd_cracktest(int, char**) {
    const char* english_runes =
        "ᛒᛖᛚᛁᛖᚢᛖᚾᚩᚦᛝᚠᚱᚩᛗᚦᛁᛋᛒᚩᚩᚳᛖᛉᚳᛖᛈᛏᚹᚻᚪᛏᚣᚩᚢᚳᚾᚩᚹᛏᚩᛒᛖᛏᚱᚢᛖ"
        "ᛏᛖᛋᛏᚦᛖᚳᚾᚩᚹᛚᛖᛞᚷᛖᚠᛁᚾᛞᚣᚩᚢᚱᛏᚱᚢᚦᛖᛉᛈᛖᚱᛁᛖᚾᚳᛖᚣᚩᚢᚱᛞᛠᚦ";
    std::vector<int> pt = gematria::parse_runes(english_runes);
    std::vector<int> key = {3, 17, 9, 24, 11};  // arbitrary known 5-rune key
    std::vector<int> ct = vigenere(pt, key, false, -1);

    RuneModel model;
    try {
        model = load_model(3);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "cracktest skipped (run from cicada/ dir): %s\n", e.what());
        return 0;
    }
    std::printf("plaintext   : %s\n", latin_of(pt).c_str());
    std::printf("encrypted   : %s\n", latin_of(ct).c_str());
    VigResult r = vigenere_crack(ct, model, 1, 8, 10, -1, 1);
    std::string got = latin_of(r.plain);
    std::printf("recovered   : %s  (key len %d, score %.1f)\n", got.c_str(), r.key_len,
                r.score);
    bool ok = got == latin_of(pt);
    std::printf("%s\n", ok ? "RECOVERED EXACTLY" : "did not fully recover (search is heuristic)");
    return 0;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr,
                     "cicada — Liber Primus / Gematria Primus toolkit\n"
                     "usage: cicada <command> [args]\n"
                     "  translit <file>                 runes -> Latin\n"
                     "  stats <file>                    frequency + IoC\n"
                     "  decode <file> <method> [args]   atbash|caesar|vigenere|totient|primes\n"
                     "  vigcrack <file> [maxlen] ...     search for a Vigenere key (hypothesis)\n"
                     "  subsolve <file> ...             29-symbol substitution search (hypothesis)\n"
                     "  selftest                        validate against known solved page\n");
        return 2;
    }
    std::string cmd = argv[1];
    if (cmd == "translit") return cmd_translit(argc - 2, argv + 2);
    if (cmd == "stats") return cmd_stats(argc - 2, argv + 2);
    if (cmd == "decode") return cmd_decode(argc - 2, argv + 2);
    if (cmd == "vigcrack") return cmd_vigcrack(argc - 2, argv + 2);
    if (cmd == "subsolve") return cmd_subsolve(argc - 2, argv + 2);
    if (cmd == "selftest") return cmd_selftest(argc - 2, argv + 2);
    if (cmd == "cracktest") return cmd_cracktest(argc - 2, argv + 2);
    std::fprintf(stderr, "unknown command: %s\n", cmd.c_str());
    return 2;
}
