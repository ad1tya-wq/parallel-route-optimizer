#pragma once
#include <vector>
#include <algorithm>
#include <unordered_set>
#include <numeric>
#include "tsp.hpp"
#include "rng.hpp"

// -----------------------------------------------------------------------------
// Genetic-algorithm building blocks shared by all three modes (serial, P1, P2).
//   Representation : permutation of city indices (a tour).
//   Selection      : tournament.
//   Crossover      : Order Crossover (OX) — the standard permutation-safe op.
//   Mutation       : segment inversion (also a random 2-opt move).
//   Local search   : bounded 2-opt (optional "memetic" step, flag-gated).
// Plus edge-set diversity helpers, which are the raw material for DTAM (P2):
//   both the per-island stagnation signal and the "most-different island"
//   comparison are computed from tour edge sets.
// -----------------------------------------------------------------------------

struct Individual {
    std::vector<int> tour;
    double len = 0.0;
};
using Population = std::vector<Individual>;

struct GAParams {
    int  pop_size      = 240;    // total population (islands split this across threads)
    int  tournament_k  = 4;
    double mutation_rate = 0.25; // probability a child is mutated
    int  elites        = 1;      // elitism per population/island
    bool use_2opt      = false;  // memetic local search on/off
    int  two_opt_passes = 1;     // bounded sweeps when 2-opt is enabled
    double two_opt_rate = 0.15;  // probability a child receives 2-opt
};

inline void evaluate(Individual& ind, const TSPInstance& inst) {
    ind.len = inst.tour_length(ind.tour);
}

inline Individual make_random(const TSPInstance& inst, Rng& rng) {
    Individual ind;
    ind.tour.resize(inst.n);
    std::iota(ind.tour.begin(), ind.tour.end(), 0);
    for (int i = inst.n - 1; i > 0; --i) std::swap(ind.tour[i], ind.tour[rng.uniform_int(0, i)]);
    evaluate(ind, inst);
    return ind;
}

inline void sort_population(Population& pop) {
    std::sort(pop.begin(), pop.end(),
              [](const Individual& a, const Individual& b) { return a.len < b.len; });
}

// Tournament selection: sample k competitors, return the fittest one's index.
inline int tournament(const Population& pop, int k, Rng& rng) {
    int best = rng.uniform_int(0, (int)pop.size() - 1);
    for (int i = 1; i < k; ++i) {
        int c = rng.uniform_int(0, (int)pop.size() - 1);
        if (pop[c].len < pop[best].len) best = c;
    }
    return best;
}

// Order Crossover (OX): keep parent-1's slice [a,b], fill the rest with
// parent-2's cities in their relative order.
inline std::vector<int> order_crossover(const std::vector<int>& p1,
                                        const std::vector<int>& p2, Rng& rng) {
    int n = (int)p1.size();
    int a = rng.uniform_int(0, n - 1), b = rng.uniform_int(0, n - 1);
    if (a > b) std::swap(a, b);
    std::vector<int> child(n, -1);
    std::vector<char> used(n, 0);
    for (int i = a; i <= b; ++i) { child[i] = p1[i]; used[p1[i]] = 1; }
    int idx = (b + 1) % n;
    for (int k = 0; k < n; ++k) {
        int city = p2[(b + 1 + k) % n];
        if (!used[city]) { child[idx] = city; used[city] = 1; idx = (idx + 1) % n; }
    }
    return child;
}

inline void inversion_mutation(std::vector<int>& t, Rng& rng) {
    int n = (int)t.size();
    int a = rng.uniform_int(0, n - 1), b = rng.uniform_int(0, n - 1);
    if (a > b) std::swap(a, b);
    std::reverse(t.begin() + a, t.begin() + b + 1);
}

// Bounded first-improvement 2-opt. O(passes * n^2). Deliberately "heavy":
// it both sharpens solution quality and raises compute-per-individual, which
// improves parallel efficiency (more work per thread between syncs).
inline void two_opt(std::vector<int>& t, const TSPInstance& inst, int max_passes) {
    int n = (int)t.size();
    for (int pass = 0; pass < max_passes; ++pass) {
        bool improved = false;
        for (int i = 0; i < n - 1; ++i) {
            int A = t[i], B = t[i + 1];
            for (int j = i + 2; j < n; ++j) {
                if (i == 0 && (j + 1) % n == 0) continue;   // skip degenerate wrap
                int C = t[j], D = t[(j + 1) % n];
                double delta = inst.dist(A, C) + inst.dist(B, D)
                             - inst.dist(A, B) - inst.dist(C, D);
                if (delta < -1e-9) {
                    std::reverse(t.begin() + i + 1, t.begin() + j + 1);
                    improved = true;
                    B = t[i + 1];   // t[i+1] changed after the reversal
                }
            }
        }
        if (!improved) break;
    }
}

// Advance one population by a single generation (elitism + offspring). Assumes
// nothing about order on entry; sorts internally. Returns the best length.
inline double step_generation(Population& pop, const TSPInstance& inst,
                              const GAParams& p, Rng& rng) {
    sort_population(pop);
    Population next;
    next.reserve(pop.size());
    for (int e = 0; e < p.elites && e < (int)pop.size(); ++e) next.push_back(pop[e]);
    while ((int)next.size() < (int)pop.size()) {
        int i = tournament(pop, p.tournament_k, rng);
        int j = tournament(pop, p.tournament_k, rng);
        Individual child;
        child.tour = order_crossover(pop[i].tour, pop[j].tour, rng);
        if (rng.uniform01() < p.mutation_rate) inversion_mutation(child.tour, rng);
        if (p.use_2opt && rng.uniform01() < p.two_opt_rate) two_opt(child.tour, inst, p.two_opt_passes);
        evaluate(child, inst);
        next.push_back(std::move(child));
    }
    pop = std::move(next);
    sort_population(pop);
    return pop.front().len;
}

// ---- Edge-set diversity helpers (raw material for DTAM) ---------------------

inline long long enc_edge(int a, int b, int n) {
    if (a > b) std::swap(a, b);
    return (long long)a * n + b;
}

inline void build_edge_set(const std::vector<int>& t, std::unordered_set<long long>& s) {
    int n = (int)t.size();
    s.clear();
    s.reserve(n * 2);
    for (int i = 0; i < n; ++i) s.insert(enc_edge(t[i], t[(i + 1) % n], n));
}

inline int shared_edges(const std::unordered_set<long long>& setA, const std::vector<int>& tB) {
    int n = (int)tB.size(), cnt = 0;
    for (int i = 0; i < n; ++i)
        if (setA.count(enc_edge(tB[i], tB[(i + 1) % n], n))) ++cnt;
    return cnt;
}

// Normalised edge distance in [0,1]: fraction of edges that differ.
inline double edge_distance(const std::vector<int>& tA, const std::vector<int>& tB) {
    int n = (int)tA.size();
    std::unordered_set<long long> setA;
    build_edge_set(tA, setA);
    return (double)(n - shared_edges(setA, tB)) / (double)n;
}

// Mean edge distance of the population to its own best tour: our cheap,
// O(pop*n) per-island diversity metric. Low value => converged/stagnating.
inline double population_diversity(const Population& pop, const std::vector<int>& best) {
    if (pop.empty()) return 0.0;
    std::unordered_set<long long> setB;
    build_edge_set(best, setB);
    int n = (int)best.size();
    double sum = 0.0;
    for (const auto& ind : pop) sum += (double)(n - shared_edges(setB, ind.tour)) / (double)n;
    return sum / pop.size();
}
