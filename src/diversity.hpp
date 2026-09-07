#pragma once
#include <vector>
#include <cstdint>
#include <cstring>
#include "ga.hpp"   // Individual, Population, enc_edge (kept as the canonical edge encoding)

// -----------------------------------------------------------------------------
// Fast, allocation-free diversity metrics.
//
// WHY: ga.hpp's population_diversity builds an std::unordered_set<long long> per
// call and does n hash lookups per individual — O(pop*n) hash operations with
// poor cache behaviour, and it is one of the top serial costs per epoch (see
// task notes: raising epoch length from 1 to 250 cut single-threaded runtime
// from 11.04s to 3.63s for identical work). This header replaces the hash set
// with a dense bitset over the n*n possible undirected-edge slots. At n=500
// that's n*n/8 = 31 KB, at n=800 it's 80 KB — both comfortably cache-resident,
// and membership tests become a shift + mask instead of a hash + probe.
//
// EXACTNESS: every function here must return bit-for-bit identical doubles to
// ga.hpp's edge_distance / population_diversity, because the engine's
// stagnation trigger thresholds this value and the whole engine is verified
// bit-reproducible against a frozen baseline. We therefore compute the exact
// same arithmetic in the exact same order: (n - shared) / n as double, and the
// population mean via sum accumulated in loop order / pop.size().
// -----------------------------------------------------------------------------

namespace diversity_fast {

// Dense bitset over undirected tour edges, reused across calls to avoid
// per-call allocation.
//
// Edge encoding: for edge {a,b} with a<b (0 <= a < b < n), the bit index is
// a*n + b — i.e. the same packed (non-triangular-compacted) index enc_edge()
// in ga.hpp produces, just interpreted as a bit position instead of a hash-set
// key. This wastes the n*n/2 "impossible" slots where index-form a>=b would
// have landed, but keeps the indexing arithmetic identical to enc_edge and
// therefore trivially easy to verify by inspection; even at n=800 the buffer
// is only 80 KB, so the waste costs nothing that matters here.
class EdgeSet {
public:
    // Build the edge-set bitset for `tour`. n is inferred from tour.size().
    // Reuses the existing buffer whenever n hasn't grown, clearing only the
    // words that were actually set on the previous build (tracked via
    // `set_words_`) rather than paying for a full std::fill every time.
    void build(const std::vector<int>& tour) {
        int n = (int)tour.size();
        size_t need_words = ((size_t)n * (size_t)n + 63) / 64;
        if (n != n_ || bits_.size() < need_words) {
            n_ = n;
            bits_.assign(need_words, 0ULL);
            set_words_.clear();
        } else {
            // Same n as last time (or bigger buffer already allocated): clear
            // only the words we touched last build instead of the whole vector.
            for (size_t w : set_words_) bits_[w] = 0ULL;
            set_words_.clear();
        }
        for (int i = 0; i < n; ++i) {
            long long idx = enc_edge(tour[i], tour[(i + 1) % n], n);
            size_t word = (size_t)idx >> 6;
            uint64_t mask = 1ULL << (idx & 63);
            if ((bits_[word] & mask) == 0) set_words_.push_back(word);
            bits_[word] |= mask;
        }
    }

    // Count how many of `other`'s n undirected edges are present in this set.
    int shared_with(const std::vector<int>& other) const {
        int n = (int)other.size();
        int cnt = 0;
        for (int i = 0; i < n; ++i) {
            long long idx = enc_edge(other[i], other[(i + 1) % n], n);
            size_t word = (size_t)idx >> 6;
            uint64_t mask = 1ULL << (idx & 63);
            if (bits_[word] & mask) ++cnt;
        }
        return cnt;
    }

    // Reset to empty (next build() will reinitialise for whatever n it gets).
    void clear() {
        for (size_t w : set_words_) bits_[w] = 0ULL;
        set_words_.clear();
    }

private:
    int n_ = 0;
    std::vector<uint64_t> bits_;      // one bit per possible a*n+b slot
    std::vector<size_t> set_words_;   // words touched by the last build(), for cheap clearing
};

// Drop-in replacement for ga.hpp's edge_distance(). Builds a scratch EdgeSet
// internally (matching the reference's own per-call allocation shape) —
// callers on a hot path that call this repeatedly against the same tA should
// prefer population_diversity_fast, which reuses one EdgeSet across the whole
// population.
inline double edge_distance_fast(const std::vector<int>& tA, const std::vector<int>& tB) {
    int n = (int)tA.size();
    EdgeSet setA;
    setA.build(tA);
    return (double)(n - setA.shared_with(tB)) / (double)n;
}

// Drop-in replacement for ga.hpp's population_diversity(). `scratch` is
// caller-owned and reused across epochs/islands so there is no allocation on
// the steady-state path; build() re-clears it correctly for the new `best`.
inline double population_diversity_fast(const Population& pop, const std::vector<int>& best,
                                         EdgeSet& scratch) {
    if (pop.empty()) return 0.0;
    scratch.build(best);
    int n = (int)best.size();
    double sum = 0.0;
    for (const auto& ind : pop) sum += (double)(n - scratch.shared_with(ind.tour)) / (double)n;
    return sum / pop.size();
}

// NOTE ON INCREMENTAL UPDATES: since each generation only replaces a handful
// of individuals in the population (elitism keeps most of it), an incremental
// scheme that updates a running sum of edge-distances as individuals change
// (rather than recomputing population_diversity_fast from scratch) is
// plausible in principle. It is NOT implemented here: it would require
// threading extra state through island.hpp/island_opt.hpp (which we are not
// allowed to touch), and it would change the accumulation order of the sum,
// which risks breaking bit-for-bit equivalence with the frozen baseline. The
// bitset alone already removes the hashing cost, which is the dominant term.

} // namespace diversity_fast
