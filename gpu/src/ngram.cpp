#include "ngram.hpp"

#include <zlib.h>

#include <cmath>
#include <cstring>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace {

// Read the entire gzip file into memory (decompressed).
std::vector<uint8_t> gunzip_all(const std::string& path) {
    gzFile gz = gzopen(path.c_str(), "rb");
    if (!gz) throw std::runtime_error("cannot open gz: " + path);
    std::vector<uint8_t> out;
    out.reserve(1u << 26);
    uint8_t buf[1 << 20];
    int got;
    while ((got = gzread(gz, buf, sizeof(buf))) > 0)
        out.insert(out.end(), buf, buf + got);
    int err = 0;
    const char* msg = gzerror(gz, &err);
    gzclose(gz);
    if (err != 0 && err != Z_STREAM_END)
        throw std::runtime_error(std::string("gz read error: ") + msg);
    return out;
}

std::string replace_ext_with_ini(const std::string& gz_path) {
    auto pos = gz_path.rfind(".gz");
    if (pos == std::string::npos) throw std::runtime_error("expected a .gz path");
    return gz_path.substr(0, pos + 1) + "ini";  // "...v1912." + "ini"  (original keeps the dot)
}

// Parse "Key=Value" and return the trimmed value, or "" if the key's '=' is absent.
std::string after_eq(const std::string& line) {
    auto pos = line.find('=');
    if (pos == std::string::npos) return "";
    std::string v = line.substr(pos + 1);
    // strip trailing CR / whitespace
    while (!v.empty() && (v.back() == '\r' || v.back() == '\n' || v.back() == ' '))
        v.pop_back();
    return v;
}

inline int digitval(uint8_t c) { return (c >= '0' && c <= '9') ? (c - '0') : 0; }

}  // namespace

NgramTable load_ngrams(const std::string& gz_path) {
    NgramTable t;
    for (int i = 0; i < 256; i++) t.alpharev[i] = -1;

    // --- .ini sidecar -------------------------------------------------------
    std::string ini_path = replace_ext_with_ini(gz_path);
    std::ifstream ini(ini_path);
    if (!ini) throw std::runtime_error("cannot open ini: " + ini_path);

    std::string line;
    // Line 1: N-gram size=  (we only support the plain default system here)
    std::getline(ini, line);
    t.n = std::atoi(after_eq(line).c_str());
    std::getline(ini, line);
    t.ngram_factor = std::atof(after_eq(line).c_str());
    std::getline(ini, line);
    t.entropy_weight = std::atof(after_eq(line).c_str());
    std::getline(ini, line);
    t.alphabet = after_eq(line);
    std::getline(ini, line);
    t.temperature = std::atof(after_eq(line).c_str());

    if (t.n < 2 || t.n > 6)
        throw std::runtime_error("unsupported n-gram size (this build supports 2..6): " +
                                 std::to_string(t.n));
    if (t.alphabet.empty()) throw std::runtime_error("empty alphabet in ini");

    t.alpha_size = (int)t.alphabet.size();
    for (int i = 0; i < t.alpha_size; i++)
        t.alpharev[(uint8_t)t.alphabet[i]] = i;

    // --- allocate table -----------------------------------------------------
    size_t cells = 1;
    for (int i = 0; i < t.n; i++) cells *= (size_t)t.alpha_size;
    t.table.assign(cells, 0);

    // --- decompress payload -------------------------------------------------
    std::vector<uint8_t> data = gunzip_all(gz_path);
    if (data.empty()) throw std::runtime_error("empty n-gram payload");

    // --- auto-detect text vs binary (mirrors the original) ------------------
    // Read the first n bytes; if any is not an alphabet letter, it's binary.
    bool binary = false;
    for (int i = 0; i < t.n && i < (int)data.size(); i++) {
        if (t.alpharev[data[i]] < 0) { binary = true; break; }
    }

    if (binary) {
        // Dense row-major dump, one byte per cell.
        if (data.size() < cells)
            throw std::runtime_error("binary n-gram payload smaller than table (" +
                                     std::to_string(data.size()) + " < " +
                                     std::to_string(cells) + ")");
        std::memcpy(t.table.data(), data.data(), cells);
        for (size_t i = 0; i < cells; i++)
            if (t.table[i] > t.highgram) t.highgram = t.table[i];
    } else {
        // Text: fixed-width records = n alphabet bytes + 3-char value.
        const size_t rec = (size_t)t.n + 3;
        size_t bl = 0;
        const size_t N = data.size();
        while (bl + rec <= N) {
            int idx[8];
            bool ok = true;
            for (int k = 0; k < t.n; k++) {
                int a = t.alpharev[data[bl + k]];
                if (a < 0) { ok = false; break; }
                idx[k] = a;
            }
            if (ok) {
                int h = digitval(data[bl + t.n]) * 100 +
                        digitval(data[bl + t.n + 1]) * 10 +
                        digitval(data[bl + t.n + 2]);
                if (h > 255) h = 255;
                if (h > t.highgram) t.highgram = h;
                // compute linear index
                size_t li = 0;
                for (int k = 0; k < t.n; k++) li = li * t.alpha_size + idx[k];
                t.table[li] = (uint8_t)h;
            }
            bl += rec;
            while (bl < N && data[bl] < 32) bl++;  // skip newlines/separators
        }
    }

    return t;
}
