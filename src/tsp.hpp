#pragma once
#include <string>
#include <vector>
#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <algorithm>
#include "rng.hpp"

// -----------------------------------------------------------------------------
// TSPInstance: a Euclidean 2-D Travelling-Salesman instance.
//
//  * Loads TSPLIB EUC_2D files (so real benchmark instances — berlin52,
//    kroA100, pr1002, ... — can be dropped into data/ and used directly).
//  * Generates self-contained instances (no download needed):
//      - uniform : random points, reference length via the Beardwood–Halton–
//                  Hammersley (BHH) asymptotic estimate.
//      - circle  : points on a circle, whose optimal tour length is known in
//                  closed form  ->  used for exact correctness validation.
//  * Precomputes a full distance matrix for O(1) lookups (fast 2-opt).
//
// EUC_2D distances follow the TSPLIB convention of rounding to the nearest
// integer, which is what makes published optima (e.g. berlin52 = 7542) exact.
// Generated instances keep full-precision Euclidean distances.
// -----------------------------------------------------------------------------
struct TSPInstance {
    std::string name = "unnamed";
    int n = 0;
    std::vector<double> xs, ys;   // coordinates
    std::vector<double> dmat;     // n*n distance matrix (row-major)
    bool rounded = false;         // TSPLIB EUC_2D rounding?
    double known_opt = -1.0;      // known/estimated optimal length (<0 = unknown)
    bool opt_is_exact = false;    // true = provably optimal, false = estimate

    inline double dist(int i, int j) const { return dmat[(size_t)i * n + j]; }

    double raw_dist(int i, int j) const {
        double dx = xs[i] - xs[j], dy = ys[i] - ys[j];
        double d = std::sqrt(dx * dx + dy * dy);
        return rounded ? std::floor(d + 0.5) : d;
    }

    void build_matrix() {
        dmat.assign((size_t)n * n, 0.0);
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                dmat[(size_t)i * n + j] = raw_dist(i, j);
    }

    // Length of a closed tour (visits every city once, returns to start).
    double tour_length(const std::vector<int>& t) const {
        double L = 0.0;
        for (int i = 0; i + 1 < n; ++i) L += dist(t[i], t[i + 1]);
        L += dist(t[n - 1], t[0]);
        return L;
    }

    // Percentage gap above the known/estimated optimum.
    double gap_percent(double len) const {
        if (known_opt <= 0.0) return -1.0;
        return 100.0 * (len - known_opt) / known_opt;
    }
};

// A few published TSPLIB optima, so a loaded instance auto-reports its gap.
inline double lookup_known_opt(const std::string& name) {
    static const std::unordered_map<std::string, double> tbl = {
        {"berlin52", 7542}, {"eil51", 426},  {"st70", 675},    {"eil76", 538},
        {"pr76", 108159},   {"rat99", 1211}, {"kroA100", 21282},{"kroB100", 22141},
        {"eil101", 629},    {"ch130", 6110}, {"ch150", 6528},  {"kroA150", 26524},
        {"kroA200", 29368}, {"rat195", 2323},{"pr226", 80369}, {"a280", 2579},
        {"rat783", 8806},   {"pr1002", 259045},
    };
    auto it = tbl.find(name);
    return it == tbl.end() ? -1.0 : it->second;
}

// Parse a TSPLIB EUC_2D file.
inline TSPInstance load_tsplib(const std::string& path) {
    std::ifstream f(path);
    if (!f) throw std::runtime_error("cannot open TSPLIB file: " + path);

    TSPInstance inst;
    std::string line, edge_type = "EUC_2D";
    bool in_coords = false;
    std::vector<std::pair<int, std::pair<double, double>>> pts;

    while (std::getline(f, line)) {
        if (line.find("NODE_COORD_SECTION") != std::string::npos) { in_coords = true; continue; }
        if (line.find("EOF") != std::string::npos) break;

        if (!in_coords) {
            auto colon = line.find(':');
            std::string key = line.substr(0, colon == std::string::npos ? line.size() : colon);
            auto val = colon == std::string::npos ? std::string() : line.substr(colon + 1);
            auto trim = [](std::string s) {
                size_t a = s.find_first_not_of(" \t\r\n");
                size_t b = s.find_last_not_of(" \t\r\n");
                return a == std::string::npos ? std::string() : s.substr(a, b - a + 1);
            };
            key = trim(key); val = trim(val);
            if (key == "NAME") inst.name = val;
            else if (key == "EDGE_WEIGHT_TYPE") edge_type = val;
        } else {
            std::istringstream ss(line);
            int idx; double x, y;
            if (ss >> idx >> x >> y) pts.push_back({idx, {x, y}});
        }
    }
    if (pts.empty()) throw std::runtime_error("no coordinates parsed from " + path);

    std::sort(pts.begin(), pts.end(),
              [](auto& a, auto& b) { return a.first < b.first; });
    inst.n = (int)pts.size();
    inst.xs.resize(inst.n); inst.ys.resize(inst.n);
    for (int i = 0; i < inst.n; ++i) { inst.xs[i] = pts[i].second.first; inst.ys[i] = pts[i].second.second; }
    inst.rounded = (edge_type == "EUC_2D");
    inst.known_opt = lookup_known_opt(inst.name);
    inst.opt_is_exact = (inst.known_opt > 0.0);
    inst.build_matrix();
    return inst;
}

// Uniform-random points in [0, side]^2. Reference length uses the BHH estimate
// L* ~= 0.7124 * sqrt(n * Area) (an asymptotic approximation, hence not exact).
inline TSPInstance gen_uniform(int n, uint64_t seed, double side = 1000.0) {
    TSPInstance inst;
    inst.name = "uniform" + std::to_string(n);
    inst.n = n; inst.rounded = false;
    inst.xs.resize(n); inst.ys.resize(n);
    Rng rng(seed);
    for (int i = 0; i < n; ++i) { inst.xs[i] = rng.uniform01() * side; inst.ys[i] = rng.uniform01() * side; }
    inst.build_matrix();
    inst.known_opt = 0.7124 * std::sqrt((double)n * side * side);
    inst.opt_is_exact = false;
    return inst;
}

// Points evenly spaced on a circle. The optimal tour is the polygon that visits
// them in angular order; its length is exactly n * 2R * sin(pi/n). Provably
// optimal, so this is our exact correctness check.
inline TSPInstance gen_circle(int n, double R = 500.0) {
    TSPInstance inst;
    inst.name = "circle" + std::to_string(n);
    inst.n = n; inst.rounded = false;
    inst.xs.resize(n); inst.ys.resize(n);
    const double PI = 3.14159265358979323846;
    for (int i = 0; i < n; ++i) {
        double a = 2.0 * PI * i / n;   // points created in angular order (shuffle in GA init)
        inst.xs[i] = R * std::cos(a);
        inst.ys[i] = R * std::sin(a);
    }
    inst.build_matrix();
    inst.known_opt = n * 2.0 * R * std::sin(PI / n);
    inst.opt_is_exact = true;
    return inst;
}
