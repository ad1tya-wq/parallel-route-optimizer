#pragma once
#include <string>
#include <vector>
#include <fstream>
#include <algorithm>
#include "tsp.hpp"

// -----------------------------------------------------------------------------
// write_svg(): render a tour as a standalone SVG (the "product" artefact).
// Cities are dots; the tour is a closed polyline. Coordinates are auto-scaled
// into a fixed canvas with margins. No external library required.
// -----------------------------------------------------------------------------
inline void write_svg(const std::string& path, const TSPInstance& inst,
                      const std::vector<int>& tour, double length) {
    const double W = 900, H = 900, M = 40;
    double minx = *std::min_element(inst.xs.begin(), inst.xs.end());
    double maxx = *std::max_element(inst.xs.begin(), inst.xs.end());
    double miny = *std::min_element(inst.ys.begin(), inst.ys.end());
    double maxy = *std::max_element(inst.ys.begin(), inst.ys.end());
    double sx = (maxx - minx) < 1e-9 ? 1.0 : (W - 2 * M) / (maxx - minx);
    double sy = (maxy - miny) < 1e-9 ? 1.0 : (H - 2 * M) / (maxy - miny);
    double s = std::min(sx, sy);
    auto px = [&](int i) { return M + (inst.xs[i] - minx) * s; };
    // SVG y grows downward; flip so the picture matches usual orientation.
    auto py = [&](int i) { return H - (M + (inst.ys[i] - miny) * s); };

    std::ofstream o(path);
    o << "<svg xmlns='http://www.w3.org/2000/svg' width='" << W << "' height='" << H
      << "' viewBox='0 0 " << W << " " << H << "'>\n";
    o << "<rect width='100%' height='100%' fill='#0b0e14'/>\n";
    o << "<polyline fill='none' stroke='#4fd1c5' stroke-width='1.6' points='";
    for (int i = 0; i < inst.n; ++i) o << px(tour[i]) << "," << py(tour[i]) << " ";
    o << px(tour[0]) << "," << py(tour[0]) << "'/>\n";
    for (int i = 0; i < inst.n; ++i)
        o << "<circle cx='" << px(i) << "' cy='" << py(i) << "' r='3' fill='#f6ad55'/>\n";
    o << "<text x='" << M << "' y='" << (H - 12) << "' fill='#e2e8f0' font-family='monospace' "
      << "font-size='18'>" << inst.name << "  n=" << inst.n
      << "  length=" << (long long)(length + 0.5) << "</text>\n";
    o << "</svg>\n";
}
