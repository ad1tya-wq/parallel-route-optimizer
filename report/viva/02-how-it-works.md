# How the Project Works: Top-Down

Course: HPC (BCSE414L), Mini-Project Review 2. Source of every number in this document is
`results/FINDINGS.md`; no number here is invented, re-rounded, or extrapolated from it.

---

## PART A — The whole thing in one page

Worked example, taken verbatim from `PROJECT-GUIDE.md`:

```powershell
.\build\ParallelRoute.exe --in data\berlin52.tsp --mode island-dtam --engine opt `
    --islands 8 --threads 4 --generations 3000 --twoopt --validate
```

Trace of this exact command through `src/main.cpp`:

1. **Argument parsing.** `main()` walks `argv` in a flat `if/else` chain and fills an
   `EngineParams P` (declared in `src/island.hpp`). `--mode island-dtam` sets `P.mode =
   Mode::IslandDTAM`. `--engine opt` sets `P.use_opt_engine = true`. `--islands 8` and
   `--threads 4` are stored separately — this is deliberate (see B4/B6): 8 islands will be
   evolved by 4 OpenMP threads, not one island per thread. `--generations 3000` is the work
   budget. `--twoopt` sets `P.ga.use_2opt = true` (the *naive* bounded 2-opt in `ga.hpp`; note
   this command does **not** pass `--twoopt-fast`, so the slower reference local search runs).
   `--validate` sets a local `bool validate = true`.

2. **Instance construction.** Because `--in data\berlin52.tsp` is given, `load_tsplib()` (in
   `src/tsp.hpp`) parses the TSPLIB file: it reads `NAME`, `EDGE_WEIGHT_TYPE`, and the
   `NODE_COORD_SECTION` coordinate list, sorts points by their TSPLIB index, sets `rounded =
   true` because `EDGE_WEIGHT_TYPE` is `EUC_2D`, looks up the published optimum for
   `"berlin52"` (7542, from the table in `lookup_known_opt`), and calls `build_matrix()` to
   precompute the full `n×n` distance matrix with TSPLIB integer rounding
   (`std::floor(d + 0.5)`).

3. **Neighbour lists.** `P.ga.use_fast_2opt` is false here (no `--twoopt-fast`), so the
   `NeighbourLists nbr` in `main()` is never built and `P.ga.nbr` stays `nullptr` — the naive
   `two_opt()` will be used instead of `two_opt_fast()`.

4. **Engine dispatch.** `P.mode != Mode::Serial && P.use_opt_engine` is true, so
   `run_islands_opt(inst, P)` (in `src/island_opt.hpp`) runs, not the frozen
   `run_islands()` in `island.hpp`. It allocates 8 `IslandSlot`s (one per island, not per
   thread), seeds each island's RNG as `Rng(P.seed + 1 + i)` — keyed to island id — and
   initialises each island's population with `island_pop = max(4, pop_size / 8)` random tours.
   It then enters the `#pragma omp parallel num_threads(4)` region and repeats, until 3000
   generations are done: (i) an `omp for` over the 8 islands that runs `epoch_len` (default
   10) generations of `step_generation_opt` per island, computes the bitset diversity metric,
   and publishes each island's best tour and top-`K` migrants; (ii) an `omp for` over islands
   that performs DTAM migration — a stagnating island (diversity below `tau = 0.15`) pulls
   from the most genetically different non-stagnating peer, or the most distant peer overall
   if none is healthy; (iii) an `omp single` block that updates the global best, logs a row
   every `log_interval` generations, and checks the time budget. Because `--islands 8` with
   `--threads 4`, each of the 4 threads is handed `ceil(8/4) = 2` islands per `omp for`
   (`schedule(static)`).

5. **Return and validation.** `run_islands_opt` returns a `Result R` holding the best
   individual seen across all islands, migration/stagnation/donor counters, and a convergence
   log. Because `--validate` was passed, `validate_tour()` (in `ga.hpp`) checks that
   `R.best.tour` is a genuine permutation of `0..n-1` and that `inst.tour_length(tour)`
   matches `R.best.len` to within a relative tolerance of `1e-6`; a mismatch sets a non-zero
   process exit code.

6. **Reporting.** With `--quiet` absent, `main()` prints a human summary: instance name,
   engine/mode, thread/island/population breakdown, generations completed, best length, the
   known optimum and percentage gap, wall time, migration count, and the DTAM-specific
   stagnation rate and donor-found rate. On this exact instance the solver reaches the
   published optimum, 7542, to a 0.00% gap (`results/FINDINGS.md`, section 1) once
   candidate-list 2-opt is used; with the naive `--twoopt` used in this particular example
   command the FINDINGS table does not report berlin52's own naive-vs-fast gap, but it does
   record that naive 2-opt stalls short of optimum on the harder instances (kroA200 at 29491,
   a280 at 2602, eil51 at 427) before candidate-list 2-opt was added.

That is the entire path: parse flags → build instance and distance matrix → optionally build
neighbour lists → dispatch to one of `run_serial` / `run_islands` / `run_islands_opt` →
validate → print / log / render.

---

## PART B — Subsystems

### B1. Problem representation and instances

**Problem it solves.** TSP needs (a) a way to hold city coordinates and pairwise distances
efficiently, (b) a way to represent a candidate tour, and (c) reproducible, self-contained
test instances so the solver can be exercised without external downloads, plus real TSPLIB
instances for externally verifiable correctness claims.

**Mechanics.** `TSPInstance` (`src/tsp.hpp`) stores `xs`, `ys` (coordinates) and a full
row-major `dmat` distance matrix (`dist(i,j) = dmat[i*n+j]`), built once by `build_matrix()`
in O(n²). A tour is represented simply as `std::vector<int>` — a permutation of `0..n-1`; the
`Individual` struct (`ga.hpp`) pairs a tour with its cached length. `raw_dist` rounds with
`std::floor(d + 0.5)` when `rounded` is true (TSPLIB EUC_2D convention) and otherwise keeps
full double precision.

Three generators:
- `gen_uniform(n, seed, side)` — random points in `[0,side]²`; reference length is the
  Beardwood–Halton–Hammersley asymptotic estimate `L* ≈ 0.7124·√(n·Area)`, stored as
  `known_opt` with `opt_is_exact = false`.
- `gen_clustered(n, seed, k, side)` — `k` cluster centres, each city placed near one centre
  (`spread = side/40`); deliberately a rugged, multi-modal landscape with no closed-form
  optimum (`known_opt = -1`), meant to stress premature convergence.
- `gen_circle(n, R)` — points evenly spaced on a circle. The optimal tour visits them in
  angular order and its length is exactly `n · 2R · sin(π/n)` (`opt_is_exact = true`). This is
  the project's exact correctness gate.

**Key design decisions and rejected alternatives.**
- *Full O(n²) distance matrix* rather than computing distances on the fly. Rejected
  alternative: recompute `sqrt` per lookup. The matrix trades memory (`n²` doubles — e.g.
  n=500 → 2 MB) for O(1) lookups, which matters because both the GA inner loop and 2-opt
  perform enormous numbers of distance queries; recomputation would dominate runtime.
- *TSPLIB integer rounding* is implemented (`std::floor(d+0.5)`), not skipped, because
  published TSPLIB optima (7542 for berlin52, etc.) are themselves computed under that
  rounding convention — using unrounded distances would make an exact-gap comparison to a
  published optimum meaningless (the solver could reach a tour whose *true* Euclidean length
  is below the published value while still not matching it under the rounded metric, or vice
  versa).
- *BHH for uniform, closed form for circle.* The BHH constant is an asymptotic estimate, so a
  "gap" against it can even be negative (over- or under-shoot); it is not used as a
  correctness gate for that reason. The circle instance's closed-form optimum is exact, so it
  is used as `build.ps1`'s pass/fail correctness gate instead.

**Where it lives.** `src/tsp.hpp` (184 lines): `TSPInstance`, `load_tsplib`, `gen_uniform`,
`gen_clustered`, `gen_circle`, `lookup_known_opt`.

**Measured numbers (FINDINGS.md §1).** All seven TSPLIB instances (berlin52 7542, eil51 426,
st70 675, kroA100 21282, ch150 6528, kroA200 29368, a280 2579) are reached to a **0.00% gap**
with candidate-list 2-opt within a 3-second budget. The circle generator's closed-form optimum
is reached to 0.00% and gates every build via `build.ps1`.

---

### B2. The genetic algorithm core

**Problem it solves.** A GA needs a representation, a way to select promising parents, a way
to combine them into valid children, a way to introduce variation, and a way to avoid losing
the best solution found so far — all specialised to permutations, since a "tour" is not a
free-form bit string.

**Mechanics** (`src/ga.hpp`).

*Representation*: `Individual{ std::vector<int> tour; double len; }`; `Population =
std::vector<Individual>`.

*Tournament selection* (`tournament`): sample `tournament_k` (default 4) individuals uniformly
at random with replacement, return the index of the fittest (lowest `len`) among them.

*Order Crossover (OX)* (`order_crossover`): pick a random slice `[a,b]` of parent 1, copy it
into the child unchanged, then fill the remaining child positions, starting just after `b` and
wrapping around, with parent 2's cities taken in their own relative order, skipping any city
already placed. Worked micro-example, n = 8, slice `[2,4]`:

```
p1 = [A B C D E F G H]     slice [2,4] = C D E
p2 = [E B A D C F H G]
child = [_ _ C D E _ _ _]                     (p1's slice copied)
fill order from p2 starting at index 5, wrapping: F H G E B A D C
  skip E, B, A (used), D (used), C (used) -> take F, H, G, then continue skipping used
child[5]=F, child[6]=H, child[7]=G, wrap to child[0]=B... (continue skipping used cities in p2's order)
```
The mechanical rule implemented is exactly: `idx = (b+1) % n`; walk `p2` starting at `(b+1)%n`
for `n` steps, and whenever a city is not yet `used`, place it at `idx` and advance `idx`. This
guarantees every city appears exactly once in the child — the crossover is permutation-safe by
construction.

*Why permutation-safe crossover is necessary*: a naive one-point crossover (copy `p1[0..k]`,
then `p2[k..n]` verbatim) would in general duplicate some cities and omit others, because the
two parents are different permutations of the same city set — the child would not be a valid
tour at all. OX is the standard fix: it preserves the permutation invariant by construction.

*Mutation*: `inversion_mutation` reverses a random contiguous sub-tour `t[a..b]`
(`std::reverse`). Because reversing a segment only changes which cities are adjacent to the two
endpoints of the segment, **an inversion changes exactly two undirected edges regardless of
segment length**: the edge before the segment (previously `(t[a-1],t[a])`, becomes
`(t[a-1],t[b])`) and the edge after it (previously `(t[b],t[b+1])`, becomes `(t[a],t[b+1])`);
every internal edge inside the reversed segment is preserved, just traversed in the opposite
direction, which does not change an undirected tour. This is also, geometrically, a random
2-opt move (B3 performs the same reversal but chooses the segment to guarantee non-worsening).

*Elitism*: `step_generation` copies the top `p.elites` (default 1) individuals from the sorted
parent population directly into the next generation before generating any offspring, so the
best tour seen so far cannot be lost to crossover/mutation noise.

*Generation loop* (`step_generation`): sort population by length; copy elites; while the next
population is not full, run two tournaments to pick parents `i, j`, produce a child via OX,
mutate it with probability `mutation_rate`, optionally run bounded 2-opt on it with probability
`two_opt_rate` (memetic step, off by default), evaluate its length, append; finally replace the
population and re-sort.

**Where it lives.** `src/ga.hpp` lines 26-148 (structures, selection, OX, mutation,
`step_generation`); the allocation-free twin `step_generation_opt` at lines 234-256 (see B7).

**Measured numbers.** None specific to isolated GA-core behaviour are reported separately in
FINDINGS.md; its effect is measured jointly with local search and the island engines in later
sections (B3-B5).

---

### B3. Local search: 2-opt

**Problem it solves.** A pure GA on TSP plateaus well above the optimum because crossover and
mutation are poor at fine local refinement. A memetic (GA + local search) step — 2-opt — lets
each candidate tour be locally polished before being scored, closing much of that gap.

**Mechanics.**

*Geometric picture*: a 2-opt move removes two edges `(A,B)` and `(C,D)` from the tour and
reconnects the four endpoints as `(A,C)` and `(B,D)`, reversing the tour segment between `B`
and `C` so the tour stays a single cycle. This "uncrosses" edges that cross each other in the
plane.

*Delta formula* (`ga.hpp::two_opt`): `delta = dist(A,C) + dist(B,D) - dist(A,B) - dist(C,D)`; a
move is applied when `delta < -1e-9` (strict improvement).

*First-improvement vs best-improvement*: the reference `two_opt()` applies the **first**
improving move it finds while scanning (updates `B` and continues from the current `i`,
rather than scanning the full neighbourhood of `i` before deciding). This is "first-improvement
2-opt," not "best-improvement," which would search all `(i,j)` pairs at each position and take
the best delta before moving — first-improvement is cheaper per pass and empirically similar
in outcome for this problem size.

*Naive scan*: `two_opt(t, inst, max_passes)` is `O(passes · n²)` — for each `i` it scans every
`j > i+1`, recomputing the delta from the full distance matrix, and repeats up to
`max_passes` full sweeps or until a sweep finds no improvement.

*Candidate-list version with don't-look bits* (`src/twoopt_fast.hpp`, Bentley 1992):
1. **Neighbour lists** (`NeighbourLists::build`): for every city, precompute its `k` nearest
   other cities, sorted ascending by distance, once per instance (`O(n² log k)`, amortised
   over the whole run).
2. **Sorted-candidate early break**: when searching for an improving move anchored at city
   `a` with current tour-neighbour `b`, the code scans `a`'s neighbour list only, and stops as
   soon as `dist(a,c) >= dist(a,b)` — because the list is sorted ascending, no closer candidate
   remains, and `dist(a,c) < dist(a,b)` is a necessary condition for this move to have positive
   gain.
3. **Don't-look bits**: a queue of "active" cities starts with every city in it. A city is
   popped, and if no improving move anchored at it is found, its don't-look bit is set and it
   is not re-examined until re-activated. When a move is applied, every city in the reversed
   segment (`[lo,hi]`) plus the four move endpoints is reactivated — the code's own comment
   explains this is broader than the textbook "reactivate only the four endpoints" rule
   because reversal flips each interior city's successor/predecessor labelling, which this
   implementation treats as a distinct search direction; reactivating the whole reversed span
   closes that gap.
4. **Bounded reversal**: the reversal cost is bounded by the segment length actually being
   reversed, and (per the code's own "REVERSAL CAVEAT" comment) this implementation always
   reverses the interior, non-wrapping span rather than picking the shorter of the two
   possible arcs — correct, but it forgoes the `O(n/2)` worst-case bound that shorter-arc
   selection would give. The speed win here comes from candidate pruning and don't-look bits,
   not from cheaper reversals.

After the don't-look-bit queue drains, an exhaustive verification sweep (documented in the
code as a correctness backstop for the direction-flip subtlety above) re-scans every city once;
if it finds no improving move anywhere, the tour is a true local optimum with respect to the
candidate lists.

**Design decisions and rejected alternative.** The candidate-list restriction searches only
moves through a k-nearest-neighbour edge, a strict subset of all possible 2-opt moves — this
can converge to a very slightly worse local optimum than the exhaustive scan in principle, but
in measured practice (below) it does not: it is both faster and finds better tours, because
exhaustion of the don't-look-bit queue converges further than the naive scan's fixed pass cap.

**Where it lives.** Naive: `src/ga.hpp` (`two_opt`, lines 105-125). Fast: `src/twoopt_fast.hpp`
(`NeighbourLists`, `two_opt_fast`), enabled via `--twoopt-fast [--twoopt-k K]` (default k=8).

**Measured numbers (FINDINGS.md §5.1, E9, equal 3 s budget, 10 seeds, Wilcoxon).**

| instance | mode | naive | fast | change | generations naive/fast | p |
|---|---|--:|--:|--:|--:|--:|
| uniform500 | fixed | 17285.3 | 16615.8 | −3.9% | 210 / 3015 | 0.0020 |
| uniform500 | dtam | 17248.5 | 16642.3 | −3.5% | 200 / 2695 | 0.0020 |
| clustered600 | fixed | 5340.8 | 5212.9 | −2.4% | 140 / 2525 | 0.0020 |
| kroA200 | fixed | 29499.0 | **29368.0** | −0.4% | 1255 / 8900 | 0.0020 |
| a280 | fixed | 2614.0 | **2579.0** | −1.3% | 640 / 9150 | 0.0078 |

Overall: candidate-list 2-opt is **7.8–13.2× faster on the local search itself**, and completes
**10–14× more generations** in the same wall-clock budget. Candidate list size k=8 was chosen
from a sweep: k=5 loses 9.1% quality; k=10/16 gain a further ~1% at higher build cost. Before
candidate-list 2-opt existed, the naive scan stalled at kroA200 29491, a280 2602, eil51 427
(vs. published optima 29368, 2579, 426 — FINDINGS §1).

---

### B4. The island model and the three engines

**Problem it solves.** A single panmictic GA population does not parallelise across cores by
itself (the generation loop is inherently sequential in its dependency on the previous
generation's whole population). The island model splits the population into independent
sub-populations ("islands"), each evolved on its own thread with no synchronisation during
evolution, periodically exchanging individuals ("migration") to share genetic material.

**The three engines** (`src/island.hpp`, `src/island_opt.hpp`, dispatched via `--mode` and
`--engine`):
- `serial` — one panmictic population of size P on one core (`run_serial`). Baseline.
- `island-fixed` (**P1**) — I islands of size `P/I`; every island copies its fixed ring
  neighbour's best-K individuals over its own worst-K, every `migrate_interval` epochs. The
  textbook "naive parallel" island GA.
- `island-dtam` (**P2**) — same underlying engine, but an island migrates only when its own
  diversity has collapsed below `tau`, and it *pulls* from the most genetically different
  healthy island rather than a fixed neighbour (project's own contribution — see B5).

**Equal-work vs equal-wall-clock protocol, and why both are needed.** Equal work (fixed total
generations `P.generations`, 2-opt off so per-generation cost is fixed) isolates *parallel
speedup* — same amount of computation, less wall time. Equal wall-clock (fixed `P.time_budget`
seconds) answers a different, and for a user more relevant, question: "for N seconds, which
engine reaches the better tour?" These are not interchangeable, and the project shows a
concrete case where they disagree in direction: DTAM is **8.6% better** under equal work but
**8.4% worse** under equal wall-clock on clustered-600 (FINDINGS §6.1), because DTAM's
migration decision itself costs about 30% throughput (2.24 s vs 1.72 s for identical
generations). Measuring only one protocol would have reported only one, contradictory, half of
this result.

**Why islands help at all.** Splitting the population (a) lets independent sub-searches
explore different regions of the search space in parallel with zero synchronisation cost
during evolution, and (b) — as an accidental but measured effect — shrinks each thread's
working set enough to change cache behaviour (see B6/B7): at pop=240, n=500, a 30-individual
island's population is ≈60 KB, versus ≈480 KB for the full 240-individual population, and this
CPU's shared L2 is smaller than the latter.

**Where it lives.** `src/island.hpp` (frozen baseline engine, `run_serial`, `run_islands`,
`run_engine`), `src/island_opt.hpp` (`run_islands_opt`, the re-engineered engine).

**Measured numbers (FINDINGS.md §2, E1: islands fixed at 8, 2-opt off, 4000 generations).**

| threads | time (s) | speedup | efficiency | Karp–Flatt |
|--:|--:|--:|--:|--:|
| 1 | 4.240 | 1.00× | 1.00 | — |
| 4 | 1.284 | **3.30×** | 0.83 | 0.070 |
| 8 | 1.080 | **3.93×** | 0.49 | 0.148 |

Amdahl fit: serial fraction f = **0.155**, implying a scaling ceiling of **6.47×**.

---

### B5. DTAM, the project's own migration policy

**The four steps** (`PROJECT-GUIDE.md` §3.2, implemented in both `island.hpp` and
`island_opt.hpp`), once per epoch, on each island:

1. **Measure diversity** — mean edge-set distance between the island's population and its own
   best tour (see `population_diversity` / `population_diversity_fast`, B and diversity.hpp
   below). Low value ⇒ converged.
2. **Publish a signature** — the island's best tour, visible to peers after the epoch's
   barrier.
3. **Flag stagnation** — `stag = (diversity < tau)`, default `tau = 0.15`.
4. **Pull migrants** — a stagnating island imports the top-K individuals from the
   non-stagnating island whose published signature is *most different* from its own (measured
   by `edge_distance`), falling back to the overall-most-distant island if every peer is also
   stagnating. Non-stagnating islands do not migrate at all.

**Diversity metric definition.** A tour is a set of n undirected edges; `edge_distance(tA,tB)
= (n - shared_edges) / n` — the fraction of edges present in one tour but not the other.
`population_diversity(pop, best)` is the mean of this quantity between `best` and every
individual in the population.

**The three design shifts vs P1**, stated explicitly in the code and guide: fixed periodic
schedule → diversity-triggered; fixed ring neighbour → runtime-selected distant source;
push (a source pushes its migrants onto everyone) → pull (a stagnating island chooses its own
source).

**Measured reality (FINDINGS.md §6).**

*Diversity collapse*: logged every 10 generations, 8 islands of 30, uniform-500 — diversity
falls from 0.224 (generation 10) to 0.004 (generation 1450); across the whole run, min
0.0029, max 0.2236, **mean 0.0181**.

*Trigger saturation*: because `tau = 0.15` sits far above where the metric actually lives
(0.003–0.05), the trigger fires on **99.7%** of island-epochs — a tau sweep shows firing rates
from 100% (tau=0.9) down to 78.55% (tau=0.05) and only 90.62%/93.94%/97.2%/99.06% etc. at
intermediate values; only tau=0 stops migration entirely, and that is markedly worse (46382 vs
~31000).

*Donor availability*: instrumentation counting genuinely non-stagnant donors vs. the fallback
branch shows **stock DTAM finds a healthy donor on only 0.3–0.6% of migrations** — on over 99%
of migrations the distant-source-pull mechanism (DTAM's actual contribution) is not exercised
as designed, because every island typically collapses at the same time.

**Where it lives.** `src/island.hpp` lines 217-241 (`IslandDTAM` branch inside `run_islands`);
`src/island_opt.hpp` lines 198-230 (migration phase of `run_islands_opt`, including the
`--heterogeneous`, `--rel-trigger`, `--immigrants` rescue mechanisms and the `donor_found` /
`donor_fb` counters).

---

### B6. Parallelisation with OpenMP

**Parallel region structure** (`PROJECT-GUIDE.md` §3.3, `island_opt.hpp`):

```
#pragma omp parallel num_threads(T)
  loop over epochs:
     #pragma omp for schedule(static)   // evolve E generations per island, publish state
     ---- implicit barrier ----
     #pragma omp for schedule(static)   // migrate: read peers' published slots, write own
     ---- implicit barrier ----
     #pragma omp single                 // global best, logging, termination check
```

**The two `omp for` loops and the `omp single`.** The first `omp for` (phase 1) runs
`step_generation_opt` for `epoch_len` generations on each of the `I` islands, then computes
that island's diversity and publishes its best tour/migrants into its own `IslandSlot`. The
second `omp for` (phase 2) is the migration step: each iteration only *reads* other islands'
already-published slots and only *writes* its own island's population — no two iterations ever
write the same memory. The `omp single` (phase 3) is executed by exactly one thread and updates
shared bookkeeping (`gens_done`, `R.best`, the log, the stop flag).

**Where the implicit barriers are.** Every `omp for` and every `omp single` inside a `#pragma
omp parallel` region carries an implicit barrier at its exit (not its entry) unless suppressed
with `nowait`, which is not used here. So: all islands finish evolving and publishing *before*
any thread starts migrating (barrier after phase 1); all migration reads/writes finish *before*
the single-threaded bookkeeping runs (barrier after phase 2); and bookkeeping finishes before
the next epoch's evolution begins (barrier after phase 3, i.e. after `omp single`).

**Why the code is race-free without locks.** During phase 1, each loop iteration `i` touches
only `slot[i]` — no shared mutable state is written by more than one thread. During phase 2,
each iteration `i` writes only `slot[i].pop`/`slot[i].migrations`/etc. and only *reads* other
slots' `best_tour`/`migrants`/`stag`, all of which were fully written and barrier-published in
phase 1. Because publish (phase 1) and read (phase 2) are separated by a barrier, and read
(phase 2) and the next epoch's evolution (next phase 1) are separated by two more barriers, no
write ever races a read of the same data — synchronisation is achieved entirely through barrier
ordering, no mutex or atomic is needed on the hot path (the frozen baseline's migration count
does use `#pragma omp atomic` on a shared counter, but that is bookkeeping, not the search
state).

**Thread-to-island mapping.** `--islands I --threads T` are independent: `schedule(static)`
distributes `I` islands across `T` threads, giving each thread `ceil(I/T)` islands per `omp
for` (with the last thread getting fewer if `I` doesn't divide evenly).

**Why the RNG is keyed to the island, not the thread.** Each island owns its own
`mt19937_64`-based `Rng`, seeded `P.seed + 1 + island_id` (`rng.hpp`, `island_opt.hpp` line
111) — not by thread id. Because OpenMP's static schedule can assign different islands to
different threads depending on `T`, if the RNG were seeded by thread id, changing the thread
count would change which random stream drives which island's search, changing the outcome.
Seeding by island id instead means island `i`'s sequence of random draws is identical
regardless of how many threads execute the run — this is what makes the search trajectory
**bit-identical across thread counts** (verified, not assumed, per `tests/test_island_equiv.cpp`
and FINDINGS §3.2), so that a speedup measurement's only varying quantity is wall-clock time.

**Load-imbalance consequence of `ceil(I/p)`.** Because islands are distributed
`schedule(static)`, an epoch costs `ceil(I/p)` island-units of work regardless of how much
slack that leaves on other threads. With I=8: p=4 and p=6 both cost `ceil(8/4)=2` and
`ceil(8/6)=2` island-units — so p=6 gets **no** extra parallel benefit over p=4 while
additionally contending for only 4 physical cores. This directly explains the measured
anomaly in B4/B7: **p=6 is slower than p=4** (1.498 s vs 1.284 s, FINDINGS §2) purely from
integer-division load imbalance, not from a scaling failure — the "load-balance ceiling"
column in FINDINGS corrects for this (p=3's raw efficiency of 0.83 becomes 0.93 against the
ceiling).

**Where it lives.** `src/island_opt.hpp` lines 128-256 (the parallel region); `src/rng.hpp`
(per-island RNG).

---

### B7. The optimised engine vs the frozen baseline

**What `--engine opt` changes.** Selecting `opt` (vs the default `baseline`) switches
`main.cpp` to call `run_islands_opt` (`island_opt.hpp`) instead of `run_engine`→`run_islands`
(`island.hpp`). Three engineering changes, in order of measured impact (FINDINGS §5): (1)
islands decoupled from threads via `--islands`/`--threads`, isolating the cache-working-set
effect from true parallel speedup; (2) per-island state moved into a single `alignas(64)`
padded `IslandSlot` struct so no two islands share a cache line (no false sharing); (3) no
per-generation heap allocation — `step_generation_opt` writes into caller-owned, reused double
buffers (`Population next`, `used_buf`) instead of allocating fresh vectors every generation
the way `step_generation` does.

**Why `island.hpp` is kept frozen.** It serves as the audit baseline: the Review-2 rewrite is
measured *against* it, not by replacing it and hoping the new numbers are comparable to old
mental models. Its own header comment states it is "kept byte-for-byte as the audit baseline
so the Review-2 rewrite can be measured against it rather than replacing it."

**Differential tests asserting bit-for-bit equivalence.** `tests/test_equiv.cpp` runs
`step_generation` (baseline) and `step_generation_opt` (optimised) side by side, same seed,
same starting population, for 200 generations, and fails if the best length or any
individual's tour ever diverges. `tests/test_island_equiv.cpp` does the same at the engine
level: `run_islands` vs `run_islands_opt` at T ∈ {1,2,4}, both modes, and fails on the first
epoch where best length or migration count disagree.

**The tie-ordering subtlety.** `sort_population` (`ga.hpp`) sorts strictly by `len`:
```cpp
std::sort(pop.begin(), pop.end(),
          [](const Individual& a, const Individual& b) { return a.len < b.len; });
```
Individuals with **equal** length are therefore not totally ordered by this comparator, and
`std::sort` is free to place them in any relative order consistent with the comparator — it is
not guaranteed stable. `step_generation` sorts on entry *and* on exit; removing the entry sort
looks like a free optimisation because the population is already sorted from the previous
call's exit sort. It is not free: elitism and migration both create individuals with *exactly*
equal lengths (elites are literal copies; migrants overwrite several worst slots at once), so
a second, different `std::sort` invocation over the same equal-length individuals can permute
them differently than the first invocation did. Because tournament selection samples by
*index* into the sorted population, a different permutation of tied individuals changes which
concrete individual a given tournament draw returns, which changes which parents are chosen,
which changes the entire subsequent search. This was implemented as an optimisation, measured,
and the two engines were found to drift apart within about 15 generations — caught by
`tests/test_equiv.cpp` — and the change was **reverted**; both sorts are kept in
`step_generation_opt` specifically so `--engine opt` reproduces `--engine baseline` bit-for-bit
(see the code comment at `ga.hpp` lines 225-233 and `island_opt.hpp` lines 157-161).

**Where it lives.** `src/island.hpp` (frozen), `src/island_opt.hpp` (optimised),
`tests/test_equiv.cpp`, `tests/test_island_equiv.cpp`.

**Measured numbers.** The three "textbook" changes that were expected to matter did not
(FINDINGS §5): cache-line padding against false sharing measured **0.92–0.99×** (slightly
*slower*); eliminating per-generation heap allocation is folded into the same figure (no
separate gain); moving the RNG to thread-local storage also measured 0.92–0.99×. What did
matter: the **bitset edge-set diversity metric** (~6× on the metric itself, 1.11–1.16×
end-to-end at the default epoch length, bitwise-identical output — see B5/B9) and
**candidate-list 2-opt** (7.8–13.2× on local search, 10–14× more generations completed — B3),
by far the largest gain.

---

### B8. Correctness and validation

**`--validate`.** `validate_tour(tour, inst, reported_len, why)` (`ga.hpp`) performs two
independent checks: (1) the tour has exactly `n` entries, each city index in `[0,n)`, with no
duplicates (a `std::vector<char> seen` marks each city as it is visited); (2) the tour's length
is independently recomputed via `inst.tour_length(tour)` and compared to the engine-reported
length with a relative tolerance of `1e-6`. Any run in the study is validated this way; `main`
exits with status 3 if validation fails.

**The circle build gate.** `build.ps1` builds the binary and then runs a self-test on
`--gen circle`, whose optimum is exact (`n·2R·sin(π/n)`); if the reported gap is not exactly
0.00%, the build script rejects the build. This catches any regression in the core GA/2-opt
machinery before it can be silently shipped.

**The TSPLIB published optima.** Seven instances with externally-published optimal tour
lengths — berlin52 (7542), eil51 (426), st70 (675), kroA100 (21282), ch150 (6528), kroA200
(29368), a280 (2579) — are all reached to a 0.00% gap with candidate-list 2-opt within a
3-second budget (FINDINGS §1). Because these values come from an external, independently
maintained benchmark set rather than being self-generated, matching them exactly is a much
stronger correctness claim than matching an internally computed reference.

**The four test suites in `tests/`.**
- `test_equiv.cpp` — differential test, `step_generation` vs `step_generation_opt`, 200
  generations, individual-by-individual.
- `test_island_equiv.cpp` — differential test, `run_islands` vs `run_islands_opt`, T ∈
  {1,2,4}, both modes, checking best length and migration count.
- `test_diversity.cpp` — asserts the bitset diversity metric (`diversity_fast`) is bitwise
  `==` to the hash-set reference (`ga.hpp`) across 9 problem sizes (3 to 800) and 4 population
  sizes (1, 2, 30, 240), plus identity/rotation/reversal-invariant checks and a speed
  benchmark.
- `test_twoopt_fast.cpp` — validity (output is a permutation), monotone improvement (never
  worse than the input), candidate-set local optimality (no improving candidate-list move
  remains after convergence), and a quality/speed sweep over neighbour-list size k ∈
  {5,8,10,16}.

**Where it lives.** Validation: `src/ga.hpp` (`validate_tour`), invoked from `src/main.cpp`.
Build gate: `build.ps1`. Tests: `tests/test_equiv.cpp`, `tests/test_island_equiv.cpp`,
`tests/test_diversity.cpp`, `tests/test_twoopt_fast.cpp`.

---

### B9. The measurement harness

**Repeats and round-robin scheduling.** Per `PROJECT-GUIDE.md` §6.3, the harness measures
every configuration multiple times and schedules repeats round-robin across the *whole*
configuration list, rather than running all repeats of one configuration consecutively — this
spreads any thermal drift evenly across configurations instead of concentrating it in whichever
configuration happened to run during a hot patch of the machine's thermal cycle.

**Thermal-drift canary.** A fixed canary configuration is timed at the start of every round, so
the harness can report how much the machine's throughput drifted between rounds and flag runs
that were not clean.

**The min-over-samples estimator and its justification.** With 2-opt off, every sample at a
given configuration performs identical work (fixed generations, fixed per-generation cost), so
any variation between repeated timings of the same configuration is pure measurement noise
(scheduling jitter, thermal throttling, OS interference) that can only ever *add* time, never
subtract it. The harness therefore reports the **minimum** wall-clock time observed across
repeats as the estimate of true throughput, on the reasoning that the fastest observed run is
the one least contaminated by additive noise.

**Experiments E1–E10** (`PROJECT-GUIDE.md` §8):

| Experiment | Question it answers |
|---|---|
| E1 | Strong scaling with islands fixed — speedup/efficiency/Karp–Flatt, frozen and optimised engines. |
| E2 | The original protocol (islands = threads) re-run, to quantify the cache-conflation artefact. |
| E3 | Does enabling 2-opt break the equal-work assumption? (quality/wall-clock correlation) |
| E4 | tau sweep: at what threshold does DTAM actually trigger, and does triggering less help? |
| E5 | Equal wall-clock quality across landscapes, with and without local search. |
| E6 | TSPLIB instances with published optima — externally verifiable quality. |
| E7 | Synchronisation frequency: wall-clock vs epoch length at identical total work. |
| E8 | Epoch length vs *quality* at equal wall-clock — the other half of E7. |
| E9 | Candidate-list 2-opt vs the naive scan, at equal wall-clock. |
| E10 | DTAM rescue factorial: heterogeneous islands, relative trigger, random immigrants. |

**Scale of the study (FINDINGS.md preamble).** 1,600+ measured configurations across the ten
experiments, every one validated via `--validate`, zero validation failures.

**Where it lives.** `bench/run_study.py` (E1–E7, repeat/round-robin scheduling, thermal-drift
canary), `bench/exp_epoch_quality.py` (E8), `bench/exp_review2_extensions.py` (E9/E10),
`bench/analyze_study.py` (speedup, efficiency, Karp–Flatt, Amdahl fit, tau analysis, paired
Wilcoxon tests).

---

## PART C — Glossary

**Island model.** A parallel/distributed evolutionary algorithm architecture in which the
population is partitioned into semi-isolated sub-populations ("islands"), each evolved mostly
independently, with occasional exchange of individuals between islands.

**Migration.** The act of copying one or more individuals from one island's population into
another's, used to share genetic material across otherwise-isolated sub-populations.

**Epoch.** A fixed number of generations of independent evolution on each island, after which
all islands synchronise (publish state, possibly migrate, log).

**Deme.** A synonym for "island" or sub-population in the evolutionary-computation literature;
a semi-isolated breeding group.

**Panmictic.** Describing a single, undivided population in which any individual may mate with
any other — the opposite of an island/deme-structured population.

**Elitism.** Guaranteeing that the best individual(s) from one generation survive unchanged
into the next, so that genetic operators cannot cause the best-known solution to be lost.

**Tournament selection.** A parent-selection method that samples a small random subset of the
population and returns its fittest member, with selection pressure controlled by the subset
size.

**Order Crossover (OX).** A permutation-safe crossover operator that copies a contiguous slice
from one parent verbatim and fills the remaining positions with the other parent's cities in
their relative order, skipping duplicates, guaranteeing the child is itself a valid
permutation.

**Inversion mutation.** A mutation operator that reverses a randomly chosen contiguous segment
of a permutation; equivalent to a random 2-opt move, and it changes exactly two edges of a
tour regardless of segment length.

**Memetic algorithm.** A genetic algorithm augmented with a local-search step applied to
individuals (here, optional bounded 2-opt on children), combining global exploration with
local exploitation.

**Local search.** An optimisation method that repeatedly moves from a candidate solution to a
"nearby" one (by some defined move) whenever that move improves the objective, until no
improving move remains.

**2-opt.** A local-search move for tour-construction problems that removes two edges and
reconnects the resulting two paths the other way, reversing the segment between them; a
classic local search for TSP.

**Don't-look bit.** A per-city flag set when a local-search pass has found no improving move
anchored at that city, used to skip re-examining it until something in its neighbourhood
changes — a standard technique for speeding up repeated local search.

**Candidate/neighbour list.** A precomputed, per-city list of its k nearest other cities, used
to restrict a local search's per-city move search to a small, promising subset instead of
scanning every other city.

**Premature convergence.** The failure mode in which a population (or island) loses genetic
diversity and converges on a suboptimal solution before the search has adequately explored the
space, because all individuals have become near-identical.

**Diversity.** A measure of how different the individuals in a population (or island) are from
one another (or from a reference individual); here, mean fraction of tour edges that differ
from the population's own best tour.

**Edge set.** The set of undirected edges a tour traverses (each edge being an unordered pair
of adjacent cities in the tour); used as the basis for comparing two tours' similarity.

**Speedup.** The ratio of the time taken by a serial (single-thread) execution to the time
taken by a parallel execution of the same total work, at a given thread count.

**Parallel efficiency.** Speedup divided by the number of threads/processors used; measures
how well the added computational resources are actually being used (1.0 = perfectly linear).

**Strong vs weak scaling.** Strong scaling fixes the total problem size and increases the
number of processors (speedup is the target metric, as measured in E1); weak scaling grows the
problem size in proportion to the number of processors, aiming to hold time-per-processor
constant instead.

**Amdahl's law.** A model stating that the maximum possible speedup from parallelising a
program is bounded by `1 / (f + (1-f)/p)` as processor count `p → ∞`, approaching `1/f`, where
`f` is the fraction of the program's work that is inherently serial.

**Karp–Flatt metric.** An empirical estimator of the serial fraction `f` of a parallel program,
computed from measured speedup at a given processor count, used (unlike Amdahl's law, which
requires assuming `f`) to infer `f` directly from observed data.

**False sharing.** A performance problem in which two threads modify logically independent
variables that happen to reside on the same cache line, causing needless cache-coherence
traffic between cores as if they were contending for the same data.

**Cache line.** The fixed-size block (typically 64 bytes on x86) that a CPU cache manages and
transfers as a single unit; the unit at which false sharing occurs and at which alignment
padding is applied to avoid it.

**SMT (simultaneous multithreading).** A CPU feature (e.g. Intel Hyper-Threading) that lets a
single physical core execute more than one hardware thread concurrently by sharing its
execution resources between them, as opposed to each thread having a dedicated physical core.

**Barrier.** A synchronisation point at which every participating thread must arrive before any
of them is allowed to proceed past it.

**Race condition.** A defect where the outcome of concurrent operations depends on their
unsynchronised relative timing, typically because more than one thread accesses shared mutable
state without adequate ordering or exclusion.

**Thread affinity.** The binding of software threads to specific physical processing units
(here controlled via `OMP_PROC_BIND`/`OMP_PLACES`), which matters for consistent performance
and reproducible measurements on machines with heterogeneous core layouts or SMT.

**Wall-clock vs CPU time.** Wall-clock time is elapsed real-world time between the start and
end of an operation; CPU time is the time a processor actually spent executing that operation's
instructions — the two diverge under multithreading (CPU time can exceed wall-clock time) or
when a process is idle/waiting (wall-clock exceeds CPU time).

**Wilcoxon signed-rank test.** A non-parametric statistical test for comparing two paired
samples (here, matched runs of two configurations on the same seeds) to determine whether their
median difference is significantly different from zero, without assuming normally distributed
data.

**Bonferroni correction.** A method for controlling the overall false-positive rate when
performing multiple statistical tests simultaneously, by dividing the significance threshold
(e.g. 0.05) by the number of comparisons made — used in FINDINGS §6.4 to note that a
nominally-significant p=0.0273 result does not survive correction across 24 comparisons
(corrected threshold 0.002).
