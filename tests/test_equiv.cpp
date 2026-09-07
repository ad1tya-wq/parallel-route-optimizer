// Differential test: step_generation (baseline) vs step_generation_opt.
// Same instance, same starting population, same seed => must agree every generation.
#include <cstdio>
#include "../src/tsp.hpp"
#include "../src/ga.hpp"

int main() {
    TSPInstance inst = gen_uniform(120, 7);
    GAParams p; p.pop_size = 40; p.use_2opt = false;

    Rng r1(99), r2(99);
    Population a, b;
    { Rng init(5); for (int i=0;i<p.pop_size;++i) a.push_back(make_random(inst, init)); }
    b = a;
    sort_population(a); sort_population(b);

    Population scratch; std::vector<char> used(inst.n);
    for (int g = 0; g < 200; ++g) {
        double la = step_generation(a, inst, p, r1);
        double lb = step_generation_opt(b, scratch, inst, p, r2, used);
        if (la != lb) { printf("DIVERGED at generation %d: baseline=%.6f opt=%.6f\n", g, la, lb); return 1; }
        for (size_t i = 0; i < a.size(); ++i)
            if (a[i].tour != b[i].tour) { printf("TOUR DIVERGED at generation %d, individual %zu\n", g, i); return 1; }
    }
    printf("PASS: 200 generations identical (best=%.4f)\n", a.front().len);
    return 0;
}
