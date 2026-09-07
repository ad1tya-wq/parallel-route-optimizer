#pragma once
#include <vector>
#include <string>
#include <limits>
#include <cmath>
#include "tsp.hpp"
#include "ga.hpp"
#include "rng.hpp"
#include "timer.hpp"

#ifdef _OPENMP
#include <omp.h>
#else
inline int  omp_get_thread_num()  { return 0; }
inline int  omp_get_max_threads() { return 1; }
inline void omp_set_num_threads(int) {}
#endif

// -----------------------------------------------------------------------------
// The three optimisation engines under comparison:
//
//   Serial      : one panmictic population on one core.
//   IslandFixed : T islands (one per OpenMP thread) evolving independently in
//                 epochs; every `migrate_interval` epochs each island copies its
//                 source ring-neighbour's best-K over its own worst-K. This is
//                 the textbook parallel GA (our "naive parallel", P1).
//   IslandDTAM  : same island engine, but migration is Diversity-Triggered and
//                 Distant-source: an island migrates ONLY when it has stagnated
//                 (mean edge-diversity < tau), and it PULLS from the most
//                 genetically different healthy island (our contribution, P2).
//
// Only barriers + a single-thread bookkeeping block synchronise the islands;
// the per-epoch evolution runs lock-free, which is what yields the speedup.
// -----------------------------------------------------------------------------

enum class Mode { Serial, IslandFixed, IslandDTAM };

inline const char* mode_name(Mode m) {
    switch (m) {
        case Mode::Serial:      return "serial";
        case Mode::IslandFixed: return "island-fixed";
        case Mode::IslandDTAM:  return "island-dtam";
    }
    return "?";
}

struct EngineParams {
    Mode     mode = Mode::Serial;
    GAParams ga;
    int      threads = 1;
    int      islands = 0;          // 0 => one island per thread (baseline behaviour)
    bool     use_opt_engine = false; // --engine opt selects src/island_opt.hpp
    int      generations = 1000;   // total generations (equal-work budget)
    double   time_budget = -1.0;   // seconds; if > 0 terminate by wall-clock
    int      epoch_len = 10;       // generations per epoch (island modes)
    int      migrate_interval = 1; // epochs between migrations (P1)
    int      migrants = 4;         // K migrants exchanged
    double   tau = 0.15;           // DTAM stagnation threshold on diversity (absolute)
    // --- Review-2 additions -----------------------------------------------------
    // Absolute tau is badly conditioned: the diversity metric collapses into the
    // 0.003-0.05 band within ~100 generations, so tau=0.15 fires on 99.7% of
    // island-epochs and the trigger never discriminates. A relative trigger keyed
    // to each island's OWN recent diversity is scale-free and keeps discriminating
    // wherever the metric happens to sit.
    bool     relative_trigger = false;  // --rel-trigger
    double   rel_drop = 0.5;            // stagnant if div < rel_drop * moving average
    int      rel_window = 5;            // epochs in the moving average
    // All islands share identical parameters, so they converge at the same time and
    // DTAM's "pull from a NON-stagnating island" clause finds no healthy donor.
    // Heterogeneous islands spread mutation rate / tournament size across islands to
    // desynchronise collapse. Gong & Fukunaga (CEC 2011); Luo et al. (2019).
    bool     heterogeneous = false;     // --heterogeneous
    double   het_mut_lo = 0.10, het_mut_hi = 0.45;
    int      het_k_lo = 2,      het_k_hi = 6;
    int      random_immigrants = 0;     // --immigrants N: fresh random tours per island per epoch
    int      log_interval = 10;    // CSV row cadence in generations
    double   target_gap = -1.0;    // % gap for time-to-target (needs known_opt)
    uint64_t seed = 1;
};

struct LogRow {
    int    generation;
    double elapsed;
    double best_len;
    double gap;         // % over known/estimated opt (-1 if unknown)
    double diversity;   // mean across islands (or single-pop diversity)
    int    migrations;  // cumulative migration events
};

struct Result {
    Individual best;
    std::vector<LogRow> log;
    double total_time = 0.0;
    double time_to_target = -1.0;  // seconds to reach target_gap (-1 = not reached)
    int    total_migrations = 0;
    int    threads = 1;
    int    islands = 1;
    int    island_pop = 0;
    int    effective_generations = 0;
    long long stag_epochs = 0;     // island-epochs flagged stagnant (DTAM trigger rate)
    long long island_epochs = 0;   // island-epochs executed in total
    long long donor_found = 0;     // DTAM migrations that found a healthy (non-stagnant) donor
    long long donor_fallback = 0;  // DTAM migrations forced onto the most-distant-overall fallback
    Mode   mode = Mode::Serial;
};

inline double target_length(const TSPInstance& inst, double target_gap) {
    if (target_gap <= 0.0 || inst.known_opt <= 0.0) return -1.0;
    return inst.known_opt * (1.0 + target_gap / 100.0);
}

// ---- Serial engine ----------------------------------------------------------
inline Result run_serial(const TSPInstance& inst, const EngineParams& P) {
    Rng rng(P.seed);
    Population pop;
    pop.reserve(P.ga.pop_size);
    for (int i = 0; i < P.ga.pop_size; ++i) pop.push_back(make_random(inst, rng));
    sort_population(pop);

    Result R;
    R.mode = Mode::Serial;
    R.threads = 1;
    R.island_pop = P.ga.pop_size;
    R.best = pop.front();
    double tgt = target_length(inst, P.target_gap);

    double t0 = wall_time();
    int gen = 0;
    for (; gen < P.generations; ++gen) {
        double b = step_generation(pop, inst, P.ga, rng);
        if (b < R.best.len) R.best = pop.front();
        double elapsed = wall_time() - t0;
        if (tgt > 0 && R.time_to_target < 0 && R.best.len <= tgt) R.time_to_target = elapsed;
        if ((gen + 1) % P.log_interval == 0) {
            double div = population_diversity(pop, pop.front().tour);
            R.log.push_back({gen + 1, elapsed, R.best.len, inst.gap_percent(R.best.len), div, 0});
        }
        if (P.time_budget > 0 && elapsed >= P.time_budget) { ++gen; break; }
    }
    R.total_time = wall_time() - t0;
    R.effective_generations = gen;
    return R;
}

// ---- Island engine (P1 + P2) ------------------------------------------------
inline Result run_islands(const TSPInstance& inst, const EngineParams& P) {
    const int T = std::max(1, P.threads);
    const int island_pop = std::max(4, P.ga.pop_size / T);
    const int K = std::min(P.migrants, island_pop - 1);

    // Per-island populations and their published state (each index owned by one thread).
    std::vector<Population>       island(T);
    std::vector<Individual>       island_best(T);
    std::vector<Population>       pub_migrants(T);
    std::vector<std::vector<int>> pub_best_tour(T);
    std::vector<double>           pub_best_len(T, 0.0), pub_div(T, 1.0);
    std::vector<char>             pub_stag(T, 0);

    Result R;
    R.mode = P.mode;
    R.threads = T;
    R.islands = T;
    R.island_pop = island_pop;
    R.best.len = std::numeric_limits<double>::infinity();

    const double tgt = target_length(inst, P.target_gap);
    double t0 = 0.0;
    bool   stop = false;
    int    total_migrations = 0;
    int    gens_done = 0;
    long long stag_count = 0;   // island-epochs flagged stagnant (instrumentation only)

    GAParams ga = P.ga;
    ga.pop_size = island_pop;   // each island evolves its own slice

    #pragma omp parallel num_threads(T)
    {
        const int id = omp_get_thread_num();
        Rng rng(P.seed + 1 + id);                 // independent per-island stream

        island[id].reserve(island_pop);
        for (int i = 0; i < island_pop; ++i) island[id].push_back(make_random(inst, rng));
        sort_population(island[id]);
        island_best[id] = island[id].front();

        #pragma omp single
        { t0 = wall_time(); }                     // implicit barrier: all start together

        int epoch = 0;
        while (gens_done < P.generations && !stop) {
            const int this_epoch = std::min(P.epoch_len, P.generations - gens_done);

            // --- independent evolution (no synchronisation) ---
            for (int g = 0; g < this_epoch; ++g) step_generation(island[id], inst, ga, rng);
            sort_population(island[id]);
            if (island[id].front().len < island_best[id].len) island_best[id] = island[id].front();

            // --- publish state for this epoch ---
            pub_best_len[id]  = island_best[id].len;
            pub_best_tour[id] = island_best[id].tour;
            pub_div[id]       = population_diversity(island[id], island[id].front().tour);
            pub_stag[id]      = (pub_div[id] < P.tau) ? 1 : 0;
            pub_migrants[id].assign(island[id].begin(), island[id].begin() + K);

            #pragma omp barrier   // all publishes visible before any migration reads

            // --- migration: each thread reads others' published state, writes only its own island ---
            if (T > 1) {
                if (P.mode == Mode::IslandFixed) {
                    if ((epoch + 1) % P.migrate_interval == 0) {
                        int src = (id - 1 + T) % T;               // fixed ring source
                        int base = island_pop - K;                // overwrite worst-K
                        for (int m = 0; m < K; ++m) island[id][base + m] = pub_migrants[src][m];
                        #pragma omp atomic
                        total_migrations++;
                    }
                } else { // IslandDTAM
                    if (pub_stag[id]) {                            // migrate only when stagnating
                        // Pull from the most genetically different island (prefer a healthy one),
                        // maximising the diversity injected into a converging island.
                        int src = -1; double bestd = -1.0;
                        for (int j = 0; j < T; ++j) {
                            if (j == id || pub_stag[j]) continue;
                            double d = edge_distance(pub_best_tour[id], pub_best_tour[j]);
                            if (d > bestd) { bestd = d; src = j; }
                        }
                        if (src < 0) {                             // all peers stagnant: most-distant overall
                            for (int j = 0; j < T; ++j) {
                                if (j == id) continue;
                                double d = edge_distance(pub_best_tour[id], pub_best_tour[j]);
                                if (d > bestd) { bestd = d; src = j; }
                            }
                        }
                        if (src >= 0) {
                            int base = island_pop - K;
                            for (int m = 0; m < K; ++m) island[id][base + m] = pub_migrants[src][m];
                            #pragma omp atomic
                            total_migrations++;
                        }
                    }
                }
            }

            // --- bookkeeping (one thread; implicit barrier guarantees migration is done) ---
            #pragma omp single
            {
                gens_done += this_epoch;
                for (int j = 0; j < T; ++j) if (pub_stag[j]) ++stag_count;
                int gbest = 0;
                for (int j = 1; j < T; ++j) if (pub_best_len[j] < pub_best_len[gbest]) gbest = j;
                if (pub_best_len[gbest] < R.best.len) {
                    R.best.len = pub_best_len[gbest];
                    R.best.tour = pub_best_tour[gbest];
                }
                double elapsed = wall_time() - t0;
                if (tgt > 0 && R.time_to_target < 0 && R.best.len <= tgt) R.time_to_target = elapsed;
                double avgdiv = 0.0;
                for (int j = 0; j < T; ++j) avgdiv += pub_div[j];
                avgdiv /= T;
                if (gens_done % P.log_interval == 0 || gens_done >= P.generations)
                    R.log.push_back({gens_done, elapsed, R.best.len,
                                     inst.gap_percent(R.best.len), avgdiv, total_migrations});
                if (P.time_budget > 0 && elapsed >= P.time_budget) stop = true;
            }
            ++epoch;
        }
    } // end parallel

    R.total_time = wall_time() - t0;
    R.total_migrations = total_migrations;
    R.effective_generations = gens_done;
    R.stag_epochs = stag_count;
    R.island_epochs = (long long)T * ((gens_done + P.epoch_len - 1) / std::max(1, P.epoch_len));
    return R;
}

// Forward declaration; the optimised engine lives in island_opt.hpp, which
// includes this header. main.cpp dispatches on P.use_opt_engine.
inline Result run_engine(const TSPInstance& inst, const EngineParams& P) {
    if (P.mode == Mode::Serial) return run_serial(inst, P);
    return run_islands(inst, P);
}
