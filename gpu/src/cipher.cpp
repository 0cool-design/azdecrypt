#include "cipher.hpp"

#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>

static std::string read_file(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cannot open cipher: " + path);
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

Cipher load_cipher(const std::string& path) {
    std::string raw = read_file(path);

    Cipher c;
    std::map<char, int> glyph_to_id;
    int max_line_len = 0, cur_line_len = 0, lines = 0;
    bool any_on_line = false;

    auto end_line = [&]() {
        if (any_on_line) {
            lines++;
            if (cur_line_len > max_line_len) max_line_len = cur_line_len;
        }
        cur_line_len = 0;
        any_on_line = false;
    };

    for (char ch : raw) {
        if (ch == '\n' || ch == '\r') {
            end_line();
            continue;
        }
        if (ch == ' ' || ch == '\t') continue;  // treat whitespace as non-symbol
        auto it = glyph_to_id.find(ch);
        int id;
        if (it == glyph_to_id.end()) {
            id = c.n_symbols++;
            glyph_to_id[ch] = id;
            c.symbol_glyph.push_back(ch);
        } else {
            id = it->second;
        }
        c.seq.push_back(id);
        cur_line_len++;
        any_on_line = true;
    }
    end_line();

    c.length = (int)c.seq.size();
    c.dim_x = max_line_len;
    c.dim_y = lines;
    if (c.length == 0) throw std::runtime_error("cipher is empty: " + path);
    return c;
}

std::vector<int> load_plaintext_indices(const std::string& path, const int alpharev[256]) {
    std::string raw = read_file(path);
    std::vector<int> out;
    for (unsigned char ch : raw) {
        int a = alpharev[ch];
        if (a >= 0) out.push_back(a);
    }
    return out;
}
