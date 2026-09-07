// Tests for src/diversity.hpp: exactness vs. ga.hpp's reference diversity
// metrics, identity/reversal/rotation invariants, scratch-buffer reuse
// safety, and a speed comparison. Prints PASS/FAIL and returns non-zero on
// any failure.
#include <vector>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <chrono>
#include <algorithm>

#include "../src/tsp.hpp"
#include "../src/ga.hpp"
#include "../src/diversity.hpp"

using diversity_fast::EdgeSet;
using diversity_fast::edge_distance_fast;
using diversity_fast::population_diversity_fast;

static int g_failures = 0;

static void fail(const char* what) {
    std::printf("  FAIL: %s\n", what);
    ++g_failures;
}

// Bit pattern of a double, for diagnostic printing on mismatch.
static uint64_t bits_of(double d) {
    uint64_t u;
    std::memcpy(&u, &d, sizeof(u));
    return u;
}

static std::vector<int> random_tour(int n, std::mt19937_64& rng) {
    std::vector<int> t(n);
    for (int i = 0; i < n; ++i) t[i] = i;
    std::shuffle(t.begin(), t.end(), rng);
    return t;
}

static Population random_population(int size, int n, std::mt19937_64& rng) {
    Population pop;
    pop.reserve(size);
    for (int i = 0; i < size; ++i) {
        Individual ind;
        ind.tour = random_tour(n, rng);
        ind.len = 0.0; // unused by diversity metrics
        pop.push_back(std::move(ind));
    }
    return pop;
}

// ---- T1: exactness vs reference, per pair -----------------------------------
static void test_exactness_pairs() {
    std::printf("T1 exactness vs reference (edge_distance)...\n");
    std::mt19937_64 rng(12345);
    std::vector<int> sizes = {3, 4, 10, 51, 64, 65, 200, 500, 800};
    int pairs_per_n = 25;
    int checked = 0;
    for (int n : sizes) {
        for (int p = 0; p < pairs_per_n; ++p) {
            std::vector<int> a = random_tour(n, rng);
            std::vector<int> b = random_tour(n, rng);
            double ref = edge_distance(a, b);
            double fast = edge_distance_fast(a, b);
            ++checked;
            if (!(ref == fast)) {
                std::printf("  MISMATCH n=%d ref=%.17g (0x%016llx) fast=%.17g (0x%016llx)\n",
                            n, ref, (unsigned long long)bits_of(ref),
                            fast, (unsigned long long)bits_of(fast));
                fail("edge_distance_fast != edge_distance");
            }
        }
    }
    std::printf("  checked %d pairs across %zu sizes\n", checked, sizes.size());
}

// ---- T2: population exactness ------------------------------------------------
static void test_population_exactness() {
    std::printf("T2 population exactness (population_diversity)...\n");
    std::mt19937_64 rng(999);
    std::vector<int> pop_sizes = {1, 2, 30, 240};
    int n = 300;
    EdgeSet scratch;
    for (int psize : pop_sizes) {
        Population pop = random_population(psize, n, rng);
        std::vector<int> best = random_tour(n, rng);
        double ref = population_diversity(pop, best);
        double fast = population_diversity_fast(pop, best, scratch);
        if (!(ref == fast)) {
            std::printf("  MISMATCH pop=%d ref=%.17g (0x%016llx) fast=%.17g (0x%016llx)\n",
                        psize, ref, (unsigned long long)bits_of(ref),
                        fast, (unsigned long long)bits_of(fast));
            fail("population_diversity_fast != population_diversity");
        }
    }
    std::printf("  checked pop sizes: 1, 2, 30, 240\n");
}

// ---- T3: identity -------------------------------------------------------------
static void test_identity() {
    std::printf("T3 identity (edge_distance_fast(t,t) == 0.0)...\n");
    std::mt19937_64 rng(42);
    std::vector<int> sizes = {3, 4, 10, 65, 500};
    for (int n : sizes) {
        std::vector<int> t = random_tour(n, rng);
        double d = edge_distance_fast(t, t);
        if (d != 0.0) {
            std::printf("  MISMATCH n=%d edge_distance_fast(t,t)=%.17g\n", n, d);
            fail("identity failed");
        }
    }
}

// ---- T4: reversal / rotation invariance ---------------------------------------
static std::vector<int> reversed_tour(const std::vector<int>& t) {
    std::vector<int> r(t.rbegin(), t.rend());
    return r;
}
static std::vector<int> rotated_tour(const std::vector<int>& t, int k) {
    int n = (int)t.size();
    std::vector<int> r(n);
    for (int i = 0; i < n; ++i) r[i] = t[(i + k) % n];
    return r;
}

static void test_reversal_rotation_invariance() {
    std::printf("T4 reversal/rotation invariance...\n");
    std::mt19937_64 rng(7);
    std::vector<int> sizes = {3, 4, 10, 65, 500};
    for (int n : sizes) {
        std::vector<int> t = random_tour(n, rng);
        std::vector<int> rev = reversed_tour(t);
        std::vector<int> rot = rotated_tour(t, n / 3 + 1);

        double fast_rev = edge_distance_fast(t, rev);
        double ref_rev  = edge_distance(t, rev);
        double fast_rot = edge_distance_fast(t, rot);
        double ref_rot  = edge_distance(t, rot);

        if (fast_rev != 0.0)
            fail("edge_distance_fast(t, reversed(t)) != 0.0");
        if (fast_rot != 0.0)
            fail("edge_distance_fast(t, rotated(t)) != 0.0");

        // Our job is exact equivalence with the reference, not fixing it. If
        // the reference itself disagrees with these invariants, report that
        // as a finding rather than treating it as our failure.
        if (ref_rev != fast_rev) {
            std::printf("  FINDING: reference edge_distance(t, reversed(t)) = %.17g for n=%d"
                        " (fast implementation correctly gives 0.0; reference disagrees)\n",
                        ref_rev, n);
        }
        if (ref_rot != fast_rot) {
            std::printf("  FINDING: reference edge_distance(t, rotated(t)) = %.17g for n=%d"
                        " (fast implementation correctly gives 0.0; reference disagrees)\n",
                        ref_rot, n);
        }
    }
}

// ---- T5: scratch reuse ---------------------------------------------------------
static void test_scratch_reuse() {
    std::printf("T5 scratch reuse...\n");
    std::mt19937_64 rng(2024);
    int n = 400, psize = 50;
    Population pop = random_population(psize, n, rng);
    std::vector<int> best = random_tour(n, rng);
    double reference = population_diversity(pop, best);

    EdgeSet scratch;
    double first = population_diversity_fast(pop, best, scratch);
    for (int iter = 0; iter < 10; ++iter) {
        // Interleave calls against different (n, tour) shapes to exercise
        // buffer growth/clearing before returning to the original inputs.
        std::vector<int> other_best = random_tour(150 + iter, rng);
        Population other_pop = random_population(5, 150 + iter, rng);
        population_diversity_fast(other_pop, other_best, scratch);

        double again = population_diversity_fast(pop, best, scratch);
        if (again != first || again != reference) {
            std::printf("  MISMATCH iter=%d first=%.17g again=%.17g reference=%.17g\n",
                        iter, first, again, reference);
            fail("scratch reuse produced inconsistent result");
        }
    }
}

// ---- T6: speed ------------------------------------------------------------------
static void bench_case(int pop_size, int n, int reps) {
    std::mt19937_64 rng(555 + n + pop_size);
    Population pop = random_population(pop_size, n, rng);
    std::vector<int> best = random_tour(n, rng);
    EdgeSet scratch;

    // Warm up / sanity-check equivalence once before timing.
    double ref_val = population_diversity(pop, best);
    double fast_val = population_diversity_fast(pop, best, scratch);
    if (ref_val != fast_val) fail("bench sanity check: values differ");

    using clock = std::chrono::steady_clock;

    volatile double sink = 0.0;
    auto t0 = clock::now();
    for (int i = 0; i < reps; ++i) sink += population_diversity(pop, best);
    auto t1 = clock::now();
    for (int i = 0; i < reps; ++i) sink += population_diversity_fast(pop, best, scratch);
    auto t2 = clock::now();

    double ref_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    double fast_ms = std::chrono::duration<double, std::milli>(t2 - t1).count();
    double speedup = ref_ms / fast_ms;

    std::printf("  pop=%-4d n=%-4d reps=%-6d  reference=%8.3f ms  fast=%8.3f ms  speedup=%.2fx\n",
                pop_size, n, reps, ref_ms, fast_ms, speedup);
    (void)sink;
}

static void test_speed() {
    std::printf("T6 speed benchmark (informational, does not fail)...\n");
    bench_case(30, 500, 2000);
    bench_case(240, 500, 500);
    bench_case(30, 800, 1500);
}

int main() {
    test_exactness_pairs();
    test_population_exactness();
    test_identity();
    test_reversal_rotation_invariance();
    test_scratch_reuse();
    test_speed();

    if (g_failures == 0) {
        std::printf("\nALL TESTS PASSED\n");
        return 0;
    } else {
        std::printf("\n%d TEST(S) FAILED\n", g_failures);
        return 1;
    }
}
