#pragma once
#include <vector>
#include <string>
#include <limits>
#include <cmath>
#include <new>
#include "tsp.hpp"
#include "ga.hpp"
#include "rng.hpp"
#include "timer.hpp"
#include "island.hpp"    // Mode, EngineParams, LogRow, Result, target_length
#include "diversity.hpp"   // bitset edge-set metric, bitwise-identical to ga.hpp's
#include "twoopt_fast.hpp" // candidate-list 2-opt with don't-look bits

// -----------------------------------------------------------------------------
// Optimised island engine (P1/P2), selected with `--engine opt`.
//
// src/island.hpp is kept frozen as the audit baseline. This file is the
// re-engineered version. Four changes, each motivated by a measurement:
//
//  1. ISLANDS DECOUPLED FROM THREADS (--islands I --threads T).
//     The baseline hard-wires one island per thread, so changing T changes the
//     *algorithm* (island_pop = P/T) at the same time as it changes hardware
//     parallelism. Speedup measured that way conflates two effects: true
//     parallel speedup, and a cache effect (240 individuals x 500 ints = 480 KB
//     overflows this CPU's 1 MB shared L2; 30 individuals = 60 KB fits easily).
//     Holding I fixed while sweeping T isolates parallel speedup, and makes the
//     search trajectory bit-identical across thread counts, because each island
//     carries its own RNG stream keyed by island id rather than thread id.
//
//  2. NO FALSE SHARING. The baseline keeps per-island state in parallel
//     std::vectors (island[], pub_best_len[], pub_div[], pub_stag[], ...).
//     Adjacent elements share cache lines, and the 24-byte vector header of
//     island[id] is rewritten by `pop = std::move(next)` on EVERY generation,
//     so several threads write the same line thousands of times per second.
//     Here all per-island state lives in one 64-byte-aligned, padded slot.
//
//  3. NO PER-GENERATION ALLOCATION (step_generation_opt's double buffer).
//
// Changes 2 and 3 do not touch the RNG call sequence or the sort schedule, so
// for a given seed and island count `--engine opt` reproduces `--engine
// baseline` bit-for-bit; the difference is wall-clock only. (A fourth change --
// dropping the baseline's apparently redundant entry sort -- was implemented,
// measured, and then REVERTED: it perturbs the tie order among equal-length
// individuals and silently changes the search. See the note in ga.hpp.)
// -----------------------------------------------------------------------------

#ifdef _OPENMP
#include <omp.h>
#endif

struct alignas(64) IslandSlot {
    Population        pop;          // private working population
    Population        scratch;      // double buffer for step_generation_opt
    std::vector<char> used_buf;     // OX scratch
    diversity_fast::EdgeSet div_scratch;  // reused edge-set buffer for the diversity metric
    GAParams          ga;           // per-island operators (differ when --heterogeneous)
    std::vector<double> div_hist;   // recent diversity values, for the relative trigger
    Individual        best;         // best seen on this island
    Population        migrants;     // published: this island's top-K
    std::vector<int>  best_tour;    // published: signature
    double            best_len = 0.0;
    double            div      = 1.0;
    char              stag     = 0;
    long long         stag_epochs = 0;   // epochs this island was flagged stagnant
    long long         epochs      = 0;   // epochs this island ran
    long long         migrations  = 0;   // migrations this island performed
    long long         donor_found = 0;   // migrations that found a non-stagnant donor
    long long         donor_fb    = 0;   // migrations forced onto the fallback branch
    char              _pad[64] = {};     // keep neighbouring slots off this line
};

inline Result run_islands_opt(const TSPInstance& inst, const EngineParams& P) {
    const int T = std::max(1, P.threads);
    const int I = std::max(1, P.islands > 0 ? P.islands : T);
    const int island_pop = std::max(4, P.ga.pop_size / I);
    const int K = std::min(P.migrants, island_pop - 1);

    std::vector<IslandSlot> slot(I);

    Result R;
    R.mode = P.mode;
    R.threads = T;
    R.islands = I;
    R.island_pop = island_pop;
    R.best.len = std::numeric_limits<double>::infinity();

    const double tgt = target_length(inst, P.target_gap);
    GAParams ga = P.ga;
    ga.pop_size = island_pop;

    // Heterogeneous islands. Every island having identical operators is what makes
    // them collapse in lockstep; spreading mutation rate and tournament size across
    // islands staggers the collapse so that at any epoch some islands are still
    // exploring and can act as donors. Values are assigned deterministically by
    // island index so runs stay reproducible.
    for (int i = 0; i < I; ++i) {
        slot[i].ga = ga;
        if (P.heterogeneous && I > 1) {
            const double f = (double)i / (double)(I - 1);
            slot[i].ga.mutation_rate = P.het_mut_lo + f * (P.het_mut_hi - P.het_mut_lo);
            slot[i].ga.tournament_k  = P.het_k_lo +
                (int)std::lround(f * (double)(P.het_k_hi - P.het_k_lo));
        }
    }

    // ---- initialisation (untimed, mirroring the baseline) ----
    // Each island owns an RNG seeded by ISLAND id, so the trajectory does not
    // depend on how many threads execute it.
    std::vector<Rng> rngs;
    rngs.reserve(I);
    for (int i = 0; i < I; ++i) rngs.push_back(Rng(P.seed + 1 + i));

    #pragma omp parallel for num_threads(T) schedule(static)
    for (int i = 0; i < I; ++i) {
        IslandSlot& s = slot[i];
        s.pop.reserve(island_pop);
        for (int k = 0; k < island_pop; ++k) s.pop.push_back(make_random(inst, rngs[i]));
        sort_population(s.pop);
        s.best = s.pop.front();
        s.used_buf.resize(inst.n);
    }

    double t0 = wall_time();
    bool   stop = false;
    int    gens_done = 0;
    int    epoch = 0;

    #pragma omp parallel num_threads(T)
    {
        while (gens_done < P.generations && !stop) {
            const int this_epoch = std::min(P.epoch_len, P.generations - gens_done);

            // ---- phase 1: independent evolution + publish (implicit barrier) ----
            #pragma omp for schedule(static)
            for (int i = 0; i < I; ++i) {
                IslandSlot& s = slot[i];
                // Pull the RNG onto this thread's stack for the epoch. The baseline
                // keeps its Rng as a stack local inside the parallel region; holding
                // island RNGs in a shared std::vector instead costs locality (an
                // mt19937_64 state is ~2.5 KB, and neighbouring islands' states are
                // contiguous, so they share boundary cache lines). Copying in and
                // out once per epoch is negligible against E generations of work.
                Rng rng = rngs[i];
                for (int g = 0; g < this_epoch; ++g)
                    step_generation_opt(s.pop, s.scratch, inst, s.ga, rng, s.used_buf);

                // Random immigrants: overwrite the worst few with fresh random tours,
                // putting a floor under diversity so the population cannot decay to
                // near-clones. Applied before the diversity measurement so the trigger
                // sees the post-injection state.
                if (P.random_immigrants > 0) {
                    const int R = std::min(P.random_immigrants, island_pop - 1);
                    for (int m = 0; m < R; ++m)
                        s.pop[island_pop - 1 - m] = make_random(inst, rng);
                }
                rngs[i] = rng;
                // The baseline re-sorts here even though the population is already
                // sorted. That is not a no-op: migration and elitism create
                // individuals with *exactly* equal lengths, and std::sort breaks
                // those ties differently on a second pass. Mirroring it is what
                // makes the two engines agree bit-for-bit (tests/test_island_equiv).
                sort_population(s.pop);
                if (s.pop.front().len < s.best.len) s.best = s.pop.front();
                s.best_len  = s.best.len;
                s.best_tour = s.best.tour;
                // Bitset edge-set metric: ~6x faster than the hash-set version in
                // ga.hpp and bitwise-identical to it (tests/test_diversity.cpp
                // asserts operator== on the returned doubles). E7 showed this
                // metric is one of the dominant per-epoch serial costs, and it is
                // recomputed for every island every epoch, so it is worth removing
                // the hashing without perturbing the value the trigger compares.
                s.div       = diversity_fast::population_diversity_fast(
                                  s.pop, s.pop.front().tour, s.div_scratch);
                if (P.relative_trigger) {
                    // Scale-free trigger: stagnant when this island's diversity has
                    // dropped below rel_drop x its own recent moving average. Because
                    // it is keyed to the island's own history it keeps discriminating
                    // wherever the metric currently sits, unlike an absolute tau which
                    // saturates once diversity collapses into the 0.003-0.05 band.
                    if ((int)s.div_hist.size() >= P.rel_window) {
                        double avg = 0.0;
                        for (double v : s.div_hist) avg += v;
                        avg /= (double)s.div_hist.size();
                        s.stag = (s.div < P.rel_drop * avg) ? 1 : 0;
                    } else {
                        s.stag = 0;   // not enough history yet
                    }
                    s.div_hist.push_back(s.div);
                    if ((int)s.div_hist.size() > P.rel_window) s.div_hist.erase(s.div_hist.begin());
                } else {
                    s.stag = (s.div < P.tau) ? 1 : 0;
                }
                s.migrants.assign(s.pop.begin(), s.pop.begin() + K);
                s.epochs++;
                if (s.stag) s.stag_epochs++;
            }

            // ---- phase 2: migration; reads peers' published slots, writes own ----
            if (I > 1) {
                #pragma omp for schedule(static)
                for (int i = 0; i < I; ++i) {
                    IslandSlot& s = slot[i];
                    int src = -1;
                    if (P.mode == Mode::IslandFixed) {
                        if ((epoch + 1) % P.migrate_interval == 0) src = (i - 1 + I) % I;
                    } else if (s.stag) {
                        double bestd = -1.0;
                        for (int j = 0; j < I; ++j) {
                            if (j == i || slot[j].stag) continue;
                            double d = edge_distance(s.best_tour, slot[j].best_tour);
                            if (d > bestd) { bestd = d; src = j; }
                        }
                        if (src >= 0) {
                            s.donor_found++;     // a genuinely non-stagnant donor existed
                        } else {                 // every peer stagnant: most distant overall
                            for (int j = 0; j < I; ++j) {
                                if (j == i) continue;
                                double d = edge_distance(s.best_tour, slot[j].best_tour);
                                if (d > bestd) { bestd = d; src = j; }
                            }
                            if (src >= 0) s.donor_fb++;
                        }
                    }
                    if (src >= 0) {
                        int base = island_pop - K;
                        for (int m = 0; m < K; ++m) s.pop[base + m] = slot[src].migrants[m];
                        s.migrations++;   // re-sorted by the next step_generation_opt, as in the baseline
                    }
                }
            }

            // ---- phase 3: bookkeeping ----
            #pragma omp single
            {
                gens_done += this_epoch;
                int gbest = 0;
                for (int j = 1; j < I; ++j) if (slot[j].best_len < slot[gbest].best_len) gbest = j;
                if (slot[gbest].best_len < R.best.len) {
                    R.best.len  = slot[gbest].best_len;
                    R.best.tour = slot[gbest].best_tour;
                }
                double elapsed = wall_time() - t0;
                if (tgt > 0 && R.time_to_target < 0 && R.best.len <= tgt) R.time_to_target = elapsed;
                double avgdiv = 0.0;
                for (int j = 0; j < I; ++j) avgdiv += slot[j].div;
                avgdiv /= I;
                long long mig = 0;
                for (int j = 0; j < I; ++j) mig += slot[j].migrations;
                if (gens_done % P.log_interval == 0 || gens_done >= P.generations)
                    R.log.push_back({gens_done, elapsed, R.best.len,
                                     inst.gap_percent(R.best.len), avgdiv, (int)mig});
                if (P.time_budget > 0 && elapsed >= P.time_budget) stop = true;
                ++epoch;
            }
        }
    }

    R.total_time = wall_time() - t0;
    for (int i = 0; i < I; ++i) {
        R.total_migrations += (int)slot[i].migrations;
        R.stag_epochs      += slot[i].stag_epochs;
        R.island_epochs    += slot[i].epochs;
        R.donor_found      += slot[i].donor_found;
        R.donor_fallback   += slot[i].donor_fb;
    }
    R.effective_generations = gens_done;
    return R;
}
