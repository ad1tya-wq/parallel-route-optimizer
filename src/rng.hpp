#pragma once
#include <random>
#include <cstdint>

// -----------------------------------------------------------------------------
// Rng: a thin wrapper over std::mt19937_64.
//
// Each island (and therefore each OpenMP thread) owns its own Rng, seeded with a
// distinct value (base_seed + island_id). Independent per-thread streams are a
// hard correctness requirement for parallel stochastic search: sharing a single
// global RNG across threads would both race and destroy reproducibility.
// -----------------------------------------------------------------------------
struct Rng {
    std::mt19937_64 eng;

    explicit Rng(uint64_t seed) : eng(seed) {}

    // Uniform integer in [lo, hi] (inclusive).
    inline int uniform_int(int lo, int hi) {
        return std::uniform_int_distribution<int>(lo, hi)(eng);
    }

    // Uniform real in [0, 1).
    inline double uniform01() {
        return std::uniform_real_distribution<double>(0.0, 1.0)(eng);
    }
};
