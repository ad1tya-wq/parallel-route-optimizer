// Differential test at the engine level: run_islands (baseline) vs
// run_islands_opt with islands == threads. Reports the first divergent epoch.
#include <cstdio>
#include "../src/tsp.hpp"
#include "../src/ga.hpp"
#include "../src/island.hpp"
#include "../src/island_opt.hpp"

static int cmp(Mode m, int T, int gens) {
    TSPInstance inst = gen_uniform(200, 11);
    EngineParams P;
    P.mode = m; P.threads = T; P.islands = T; P.generations = gens;
    P.ga.pop_size = 160; P.epoch_len = 10; P.log_interval = 10; P.seed = 4;
    Result a = run_islands(inst, P);
    Result b = run_islands_opt(inst, P);
    printf("  %-12s T=%d: baseline best=%.4f migr=%d | opt best=%.4f migr=%d",
           mode_name(m), T, a.best.len, a.total_migrations, b.best.len, b.total_migrations);
    if (a.best.len == b.best.len && a.total_migrations == b.total_migrations) { printf("  OK\n"); return 0; }
    size_t n = a.log.size() < b.log.size() ? a.log.size() : b.log.size();
    for (size_t i = 0; i < n; ++i)
        if (a.log[i].best_len != b.log[i].best_len || a.log[i].migrations != b.log[i].migrations) {
            printf("\n     first divergence at gen %d: base(len=%.4f,migr=%d) opt(len=%.4f,migr=%d)\n",
                   a.log[i].generation, a.log[i].best_len, a.log[i].migrations,
                   b.log[i].best_len, b.log[i].migrations);
            return 1;
        }
    printf("\n     logs agree but totals differ\n");
    return 1;
}

int main() {
    int bad = 0;
    for (int T : {1, 2, 4}) { bad += cmp(Mode::IslandFixed, T, 200); bad += cmp(Mode::IslandDTAM, T, 200); }
    printf(bad ? "FAIL (%d)\n" : "PASS\n", bad);
    return bad ? 1 : 0;
}
