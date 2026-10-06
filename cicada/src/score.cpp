#include "score.hpp"

#include <cmath>
#include <fstream>
#include <stdexcept>

#include "gematria.hpp"
#include "transforms.hpp"

namespace lp {

double RuneModel::score(const std::vector<int>& idx) const {
    if ((int)idx.size() < n) return 0;
    double s = 0;
    for (size_t i = 0; i + n <= idx.size(); i++) {
        size_t li = 0;
        for (int k = 0; k < n; k++) li = li * N + idx[i + k];
        s += logp[li];
    }
    return s;
}

RuneModel load_rune_model(const std::string& path, int n) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("cannot open rune model: " + path);

    size_t cells = 1;
    for (int i = 0; i < n; i++) cells *= N;

    RuneModel m;
    m.n = n;
    std::vector<double> counts(cells, 0.0);
    double total = 0;

    std::string line;
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        // Split "<runes> <count>" on the last space.
        auto sp = line.find_last_of(" \t");
        if (sp == std::string::npos) continue;
        std::string runes = line.substr(0, sp);
        double cnt = std::atof(line.c_str() + sp + 1);
        std::vector<int> idx = gematria::parse_runes(runes);
        if ((int)idx.size() != n) continue;
        size_t li = 0;
        for (int k = 0; k < n; k++) li = li * N + idx[k];
        counts[li] += cnt;
        total += cnt;
    }
    if (total <= 0) throw std::runtime_error("empty rune model: " + path);

    // Laplace-smoothed log probabilities; unseen n-grams get a floor.
    m.logp.resize(cells);
    double denom = total + (double)cells;  // add-one smoothing
    m.floor_lp = std::log(1.0 / denom);
    for (size_t i = 0; i < cells; i++)
        m.logp[i] = (float)std::log((counts[i] + 1.0) / denom);
    return m;
}

double ioc(const std::vector<int>& idx) {
    long long f[N] = {0};
    for (int r : idx)
        if (r >= 0 && r < N) f[r]++;
    long long n = 0;
    for (int i = 0; i < N; i++) n += f[i];
    if (n < 2) return 0;
    double num = 0;
    for (int i = 0; i < N; i++) num += (double)f[i] * (f[i] - 1);
    return num / ((double)n * (n - 1));
}

}  // namespace lp
