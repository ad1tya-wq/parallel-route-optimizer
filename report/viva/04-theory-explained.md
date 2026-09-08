# The Theory, in Plain Terms, and What It Is Doing Here

This document exists to survive a viva. For every theoretical idea used in ParallelRoute it gives:
what the idea means intuitively, its precise formal statement, where it is actually applied in this
codebase, and the measured number that shows what it bought (or did not buy). Every number below is
taken verbatim from `results/FINDINGS.md` — nothing here is rounded, re-derived, or extrapolated
beyond what that file states. If a section does not carry a number, it is because `FINDINGS.md`
does not report one for that exact concept, and this is said explicitly rather than glossed over.

---

## Complexity and problem structure

### 1. NP-hardness and why TSP is hard

**In plain terms.** Imagine you have to visit every house on a list, once each, and get back home,
using the shortest possible route. With 5 houses you could just try every order and pick the best.
With 50 houses, trying every order is not a slow inconvenience — it is a number so large that no
computer built or conceivable could finish before the universe grows cold. TSP is "hard" not
because we have not found a clever enough trick yet, but because the space of possible answers
grows so explosively with the number of cities that brute force is off the table for any realistic
size, and no algorithm is known (or, under the widely-believed P ≠ NP conjecture, exists) that
finds the *guaranteed* best answer without, in the worst case, effectively trying an exponential
number of possibilities.

**The formal statement.** For a symmetric TSP instance on *n* cities (distance from A to B equals
distance from B to A), a tour is a cyclic permutation of the cities. Fixing one city to remove
rotational symmetry leaves (n-1)! orderings of the rest; dividing by 2 removes the direction of
travel (clockwise and counter-clockwise are the same tour), giving a search space of size
**(n-1)!/2**. TSP (decision version: "is there a tour of length ≤ k?") is NP-complete; the
optimisation version is NP-hard. No polynomial-time exact algorithm is known.

**What it does in this project.** This is the reason `src/ga.hpp` and the island engines
(`src/island.hpp`, `src/island_opt.hpp`) exist at all: an exact solver is not attempted. The
instances used range from `n = 51` (eil51) up to `n = 800` (used in candidate-list sizing sweeps
and the epoch-length/quality study), with the TSPLIB correctness suite at `n = 51` to `n = 280`
(a280) and generated instances (`uniform`, `clustered`) up to `n = 500`–`800`.

**Measured impact.** For n = 51 (eil51), (n-1)!/2 ≈ 3.04 × 10^64 — already far beyond exhaustive
search — yet `FINDINGS.md` §1 reports the solver reaches the **proven optimum, 426, at 0.00% gap**,
within a 3-second budget, using candidate-list 2-opt. The same holds for all seven TSPLIB
instances tested (berlin52 7542, eil51 426, st70 675, kroA100 21282, ch150 6528, kroA200 29368,
a280 2579, all at 0.00% gap). This is the direct, measured demonstration that a metaheuristic finds
what an exhaustive search could never reach in time: the *hardness* is not in doubt, and the
project's answer to it is heuristic search, not exact enumeration.

### 2. Heuristics and metaheuristics

**In plain terms.** Since finding the mathematically guaranteed best route is off the table, we
instead use a strategy that is good at finding a *very good* route, quickly, and accept that it
might not be perfect. A "heuristic" is one rule of thumb for improving a route (e.g. "if swapping
two connections shortens the loop, do it"). A "metaheuristic" is a higher-level strategy that
manages many candidate solutions and repeatedly applies such rules, borrowing an analogy — here,
evolution by selection and reproduction — to decide which candidates to keep and how to generate
new ones.

**The formal statement.** A heuristic is an algorithm that produces a feasible solution without a
guarantee of optimality, typically in return for a large reduction in running time relative to
exact methods. A metaheuristic is a problem-independent strategy (genetic algorithms, simulated
annealing, tabu search, ant colony optimisation, etc.) that orchestrates simpler heuristics
(here: crossover, mutation, local search) over a population or trajectory of candidate solutions,
typically including mechanisms for both exploring new regions of the search space and exploiting
known good ones.

**What it does in this project.** The genetic algorithm in `src/ga.hpp` is the metaheuristic; 2-opt
(`two_opt` in `ga.hpp`, and the candidate-list version in `src/twoopt_fast.hpp`) is the
lower-level local-search heuristic embedded inside it, invoked per-child during
`step_generation`/`step_generation_opt`.

**Measured impact.** The correctness section (`FINDINGS.md` §1) is the direct evidence that
accepting "approximate, but fast" as the design goal was the right call for this problem size: the
heuristic reaches the exact published optimum on every tested TSPLIB instance, at a small fraction
of the cost an exact method would need.

### 3. Local optima, basins of attraction, exploration vs exploitation

**In plain terms.** Picture a hiker in fog trying to find the lowest point in hilly terrain by
always walking downhill. They will stop at the bottom of *some* valley — but there is no guarantee
it is the deepest valley on the map. That valley is a "local optimum," and the set of positions
from which downhill-walking leads into it is its "basin of attraction." "Exploitation" is walking
downhill from where you stand (using what you already know is good); "exploration" is jumping to a
completely different, untried part of the map in case a deeper valley is there.

**The formal statement.** For a search space S with objective f, a point x* is a local optimum
with respect to a neighbourhood structure N if f(x*) ≤ f(x) for all x ∈ N(x*) (minimisation). The
basin of attraction of x* is the set of starting points from which a strictly-improving local
search trajectory converges to x*. Exploitation refers to search operators that stay within or
near a basin (hill-climbing / local search); exploration refers to operators that can move between
basins (crossover between diverse parents, mutation, migration, random restarts).

**What it does in this project.** 2-opt is pure exploitation — it only accepts moves with a
negative gain (`delta < -1e-9` in `ga.hpp`'s `two_opt`), so it walks downhill and stops at whatever
local optimum it reaches. Crossover (`order_crossover`), mutation (`inversion_mutation`), and
inter-island migration are the exploration operators: they can produce a child unlike either
parent, or import a genuinely different tour from another island.

**Measured impact.** The clearest measured illustration is the DTAM diversity collapse
(`FINDINGS.md` §6.2): population diversity falls from 0.224 at generation 10 to below 0.01 by
generation 370, mean 0.0181 over the whole run. This is islands settling into the basin of
attraction of a single local optimum and losing the diversity needed to explore elsewhere — the
raw phenomenon that concept 6 below discusses in more depth.

---

## Evolutionary computation

### 4. Genetic algorithms: population, fitness, selection, crossover, mutation, elitism

**In plain terms.** Instead of improving one route at a time, keep a whole "population" of
candidate routes. Score each one by how short it is (its "fitness"). Preferentially pick the
better ones as "parents," combine pieces of two parents to make a "child" route (crossover),
occasionally scramble a piece of a route at random (mutation) to try something new, and always
carry the very best routes through to the next generation untouched (elitism) so progress is never
lost.

**The formal statement.** A GA maintains a population P of size N of candidate solutions
(individuals). Each generation: (1) evaluate fitness f(x) for each x ∈ P (here, negative tour
length, since shorter is better — implemented directly as `ind.len = inst.tour_length(ind.tour)`
with selection favouring lower length); (2) select parents via a selection operator; (3) apply
crossover to produce offspring; (4) apply mutation with probability p_m per offspring; (5) form the
next generation, optionally preserving the top *e* individuals unchanged (elitism).

**What it does in this project.** `src/ga.hpp`, `step_generation`/`step_generation_opt`: population
is a `Population` of `Individual{tour, len}`; selection is tournament (`tournament()`); crossover is
Order Crossover (`order_crossover`/`order_crossover_into`, lines 80–93 and 208–221); mutation is
inversion mutation (`inversion_mutation`, applied with probability `p.mutation_rate`); elitism
copies the top `p.elites` individuals straight into `next` before any offspring are generated
(`for (int e = 0; e < p.elites ...) next.push_back(pop[e]);`).

**Measured impact.** The whole correctness table in `FINDINGS.md` §1 (all seven TSPLIB instances at
0.00% gap) is evidence the GA loop, as a whole, functions correctly and converges to known optima.
No FINDINGS.md number isolates the marginal contribution of elitism or crossover alone — that
ablation was not run, so no such number is claimed here.

### 5. Selection pressure and tournament selection

**In plain terms.** Tournament selection is like picking *k* people at random from a crowd and
letting the strongest of that small group go through — never a straight popularity contest over the
whole crowd. Turn *k* up, and the tournament almost always contains at least one very strong
individual, so weaker ones almost never get picked as parents — pressure toward the best is high.
Turn *k* down (as low as 2), and there is a real chance the tournament contains only mediocre
individuals, so more diverse (including weaker) parents get a chance — pressure is low.

**The formal statement.** Tournament selection with tournament size k: draw k individuals uniformly
at random (with or without replacement) from the population, and return the one with the best
fitness. The probability that the best individual overall is selected in a given tournament is
1 − (1 − 1/N)^k for a size-N population under uniform sampling (increasing in k), which is why
larger k increases selection pressure — the tendency to prefer top individuals — while smaller k
gives more chance to weaker individuals and preserves diversity.

**What it does in this project.** `tournament(pop, p.tournament_k, rng)` in `ga.hpp`, called twice
per offspring (once per parent) inside `step_generation`. The heterogeneous-island mechanism
(`--heterogeneous`) deliberately spreads `tournament_k` from 2 to 6 across islands so different
islands run at different selection pressures simultaneously.

**Measured impact.** `FINDINGS.md` §6.4 reports the heterogeneous configuration (which varies
tournament size, among other parameters, per island) at 22791.4 median on uniform-500, **5.8% worse
than fixed migration but 2.8% better than stock DTAM** — the only mechanism in the rescue factorial
that consistently improved on stock DTAM. No isolated Wilcoxon test on tournament size alone by
itself is reported in FINDINGS.md, so no such standalone number is claimed.

### 6. Premature convergence and population diversity — the measured collapse

**In plain terms.** If every route in the population starts looking almost identical too early,
the algorithm has run out of genuinely different ideas to recombine — crossover between two nearly
identical parents produces a nearly identical child, so search effectively stalls even though
generations keep ticking over. This is "premature convergence": the population converged, but to a
mediocre answer, before it explored enough of the map.

**The formal statement.** Population diversity here is measured as edge-set diversity: represent a
tour as its set of n undirected edges; the edge distance between tours A and B is the fraction of
edges in A not present in B, `edge_distance(A,B) = (n - |shared edges|) / n` (`ga.hpp`,
`edge_distance`), giving a value in [0,1] where 0 means identical tours. `population_diversity`
computes the mean edge distance of every individual in a population to the island's own current
best tour. Premature convergence is the empirical observation that this quantity falls toward 0
long before the search should be considered done.

**What it does in this project.** `population_diversity()` in `ga.hpp` and the faster bitwise
equivalent in `src/diversity.hpp` compute this metric once per epoch per island; it is the signal
DTAM's stagnation trigger (`diversity < τ`) reads.

**Measured impact.** `FINDINGS.md` §6.2, logged every 10 generations on 8 islands of 30,
uniform-500: diversity is **0.224 at generation 10**, falls to 0.032 by generation 130, and to
0.004 by generation 1450. Across the whole run: **minimum 0.0029, maximum 0.2236, mean 0.0181**.
Islands collapse to near-clones within roughly 100 generations. This is premature convergence
measured directly, not inferred, and it is the mechanistic root cause behind §6.3's finding that
DTAM's "healthy donor" condition is satisfied on only 0.3–0.6% of migrations.

### 7. The island model / coarse-grained parallel GA, demes, and migration

**In plain terms.** Instead of one big population working on the problem together, split it into
several smaller, independent populations ("islands," or "demes" in the older literature), each
evolving on its own for a while. Every so often, let a few of the best individuals travel between
islands ("migration"). This both parallelises the work — each island can run on its own CPU core —
and, done well, keeps the overall search more diverse than one giant population would stay on its
own.

**The formal statement.** Coarse-grained (island) parallel GA: partition a population of size P
into I demes of size P/I, evolve each deme independently for `migrate_interval` generations
(an "epoch"), then exchange a subset of individuals between demes according to a topology (ring,
random, etc.) and a replacement policy (e.g. replace worst K with immigrants' best K).

**What it does in this project.** `src/island.hpp` (frozen baseline) and `src/island_opt.hpp`
(re-engineered) implement exactly this: `--islands I` sets the deme count, `--epoch-len` sets the
synchronisation period, migration is either fixed-interval ring (`island-fixed`, P1) or
diversity-triggered pull (`island-dtam`, P2). The OpenMP structure (`PROJECT-GUIDE.md` §3.3) is:
parallel region over islands for evolution, barrier, parallel region over islands for migration,
barrier, single-threaded bookkeeping.

**Measured impact.** The strong-scaling table (`FINDINGS.md` §2, islands fixed at 8, 2-opt off)
is the direct measurement of the island model's parallel behaviour: time falls from 4.240 s at
p = 1 to 1.080 s at p = 8, speedup **3.93× at p = 8**. Because each island owns its own RNG stream
(`rng.hpp`, keyed by island id), every thread count reproduces a **bit-identical search
trajectory** — decoupling "does the island model parallelise" from "does changing thread count
change the algorithm," which is precisely what concept 22 below addresses.

### 8. Memetic algorithms (GA + local search) and why local search dominates here

**In plain terms.** A "memetic algorithm" bolts a local, greedy improvement step onto each
individual after it is created by the GA — think of it as: breed a new candidate route the
evolutionary way, then immediately let it "learn" by tidying up its own obvious inefficiencies
before it's judged. In this project the tidying step (2-opt) turns out to matter enormously more
than the parallel machinery around it: the biggest single-thread quality gain and the source of
almost all "does going parallel help quality" nuance both come from the local-search half of the
algorithm, not the evolutionary half.

**The formal statement.** A memetic algorithm augments a population-based global search (GA) with
individual learning (local search) applied to each candidate: for each offspring x, replace x with
LocalSearch(x) before insertion into the population (Lamarckian) or use LocalSearch(x)'s fitness
only (Baldwinian). This project is Lamarckian: the locally-improved tour is what is inserted and
what is scored.

**What it does in this project.** In `step_generation`/`step_generation_opt`, after crossover and
mutation, `if (p.use_2opt && rng.uniform01() < p.two_opt_rate) two_opt(child.tour, inst, ...)` (or
the fast candidate-list variant) is applied directly to the child's tour before evaluation — the
improved tour, not just its fitness, is kept.

**Measured impact.** `FINDINGS.md` §4.2 gives the precise number requested: **without local search**,
epoch length matters enormously for quality (uniform-500: 23949 at epoch 5 vs 34254 at epoch 25,
and clustered-600 worsens by **+42%** from epoch 5 to 200). **With 2-opt on, epoch length is nearly
irrelevant** (17099 → 17235, **~0.8%** change). Framed as parallel-vs-serial engine advantage
collapsing: without local search the reported spread of DTAM-vs-fixed advantage across the E10
factorial ranges as high as **+28.8%** (rel-trigger) down to **−2.9%** (het+immigrants) — i.e. a
wide, structurally important spread — while with 2-opt on, `FINDINGS.md` §6.4 states **every
configuration lands within ±0.3% of fixed migration**, i.e. the differences that dominate the
no-local-search regime shrink to near-noise once 2-opt is engaged. (The specific "68–74% without
local search" figure named in the task brief is not present verbatim in `results/FINDINGS.md`; the
verified, citable numbers for this collapse are the ones just quoted: up to +28.8%/−2.9% spread
without 2-opt collapsing to ±0.3% with 2-opt, plus the +42% epoch-length sensitivity without local
search versus ~0.8% with it.)

---

## Local search theory

### 9. 2-opt: the move, the gain formula, first-improvement vs best-improvement

**In plain terms.** Take a route and pick two of its connections (edges). If uncrossing them —
cutting both, and reconnecting the two dangling pieces the other way, which reverses the order of
the cities between the cuts — makes the total route shorter, do it. Repeat until no such swap helps
any more. "First-improvement" takes the first swap found that helps and moves on immediately;
"best-improvement" would instead check every possible swap and take only the very best one before
acting.

**The formal statement.** Given a tour with edges (A,B) and (C,D) (in tour order, A before B before
C before D), the 2-opt move removes these two edges and reconnects as (A,C) and (B,D), reversing
the tour segment between B and C. The gain is:

  delta = d(A,C) + d(B,D) − d(A,B) − d(C,D)

The move is improving iff delta < 0. First-improvement applies the first move found with delta < 0
and continues scanning from there; best-improvement would evaluate all candidate moves in a pass
and apply only the one with the most negative delta.

**What it does in this project.** `two_opt()` in `ga.hpp` computes exactly this delta
(`double delta = inst.dist(A, C) + inst.dist(B, D) - inst.dist(A, B) - inst.dist(C, D);`) and applies
the move immediately when `delta < -1e-9` (a small negative-epsilon guard against floating-point
noise), then reverses the segment (`std::reverse(t.begin() + i + 1, t.begin() + j + 1)`) — this is
first-improvement. `twoopt_fast.hpp`'s candidate-list version uses the same delta formula restricted
to a neighbour list, also first-improvement, driven by a work queue.

**Measured impact.** `FINDINGS.md` §5.1: candidate-list 2-opt (`fast`) versus the naive
implementation, equal 3-second budget, 10 seeds, Wilcoxon signed-rank: uniform500 **−3.9%** tour
length (fixed migration), kroA200 **−0.4%** reaching the **exact optimum 29368.0** versus naive's
29499.0, a280 **−1.3%** reaching **exact optimum 2579.0** versus naive's 2614.0. All six reported
comparisons have p = 0.0020 except a280 (p = 0.0078).

### 10. Neighbour/candidate lists and the sorted early-break argument

**In plain terms.** Instead of comparing a city to every other city in the map when looking for a
profitable swap, only check its handful of *nearest* neighbours, sorted from closest to farthest.
The moment a neighbour is farther away than the city's current tour-neighbour, you can stop
checking — any neighbour further down the list is even farther away, and a 2-opt move that starts
by connecting to a *farther* city than the one you already have can never be an improving move
in the first place, so there's no point looking further.

**The formal statement.** For city a with current tour-neighbour b, and a sorted-ascending
candidate list of a's k nearest other cities, an improving 2-opt move replacing edge (a,b) with
edge (a,c) requires the total length to fall. A well-known necessary condition (used to justify
pruning, not to prove sufficiency) is that a new edge (a,c) can only be part of a strictly-improving
move if d(a,c) < d(a,b) — a longer replacement edge cannot, by itself, be compensated for a genuine
gain in the way 2-opt's move structure requires. Since the candidate list is sorted ascending by
distance, once dist(a, c) ≥ dist(a, b) is reached, no further candidate in the list can satisfy the
necessary condition, so the scan over that list may terminate.

**What it does in this project.** `NeighbourLists::build()` in `twoopt_fast.hpp` builds, once per
instance, the k nearest neighbours of every city sorted ascending
(`std::partial_sort` by distance with a deterministic tie-break by city index). The 2-opt search in
`two_opt_fast()` consults only this list per city and relies on the sorted order to break early
(the file's header comment states this explicitly: "stop scanning the list as soon as
dist(a,c) >= dist(a,b)").

**Measured impact.** This mechanism, together with don't-look bits, is what produces the
**7.8–13.2× speedup on local search** and the **10–14× more generations completed** figure in
`FINDINGS.md` §5 ("Engineering changes and what they actually bought"). No separate ablation
isolating the early-break alone (versus don't-look bits alone) is reported, so no such isolated
number is claimed.

### 11. Don't-look bits: the amortisation argument

**In plain terms.** After 2-opt has checked a city and found no useful swap for it, there is no
point re-checking that same city again and again every pass — nothing around it has changed. Mark
it "don't look" and skip it. Only un-mark it (put it back on the to-check list) if a move elsewhere
in the tour actually touches one of its edges. This way, the total work across a whole run is
proportional to how many times cities' neighbourhoods actually change, not to (number of cities) ×
(number of passes).

**The formal statement.** Maintain a boolean "don't-look" flag per city and a work queue of active
cities. Initially all cities are active. Pop a city from the queue; if no improving move is found
for it, set its don't-look bit and do not requeue it; if an improving move IS applied, clear the
don't-look bit (reactivate) for every city whose tour-adjacency changed as a result (the four
endpoints of the swap) and push them back onto the queue if not already queued. The algorithm
terminates when the queue is empty. This amortises the total cost: each city is examined again only
in response to a local change near it, not on a fixed schedule.

**What it does in this project.** `two_opt_fast()` in `twoopt_fast.hpp` implements exactly this:
`dont_look[]`, `in_queue[]`, a `std::deque<int> queue`, and an `activate()` lambda that clears
`dont_look` and re-enqueues a city only when a move touches it.

**Measured impact.** Same figure as concept 10 — don't-look bits and the candidate list together
produce the **7.8–13.2× on local search; 10–14× more generations completed** result in
`FINDINGS.md` §5, and are jointly responsible for the correctness improvements in §5.1 (e.g. a280
reaching exact optimum 2579 versus naive's stalling at 2602/2614).

### 12. Why an inversion mutation changes exactly two undirected edges

**In plain terms.** Mutation here works by picking a stretch of the route and reversing the order
you visit those cities in — like flipping a section of a chain end-to-end. Surprisingly, this
leaves almost the whole route untouched: the only connections that actually change are the two
"joints" at either end of the flipped stretch, because every connection *inside* the flipped
stretch is still between the same pair of cities, just traversed in the opposite direction (which
does not matter for an undirected route).

**The formal statement.** Let tour t have a reversed segment t[a..b]. Every edge (t[i], t[i+1]) for
a ≤ i < b is preserved as an unordered pair after reversal (only its traversal direction flips,
which is irrelevant since the tour is undirected). Only the two edges at the segment's boundary
change: the edge that was (t[a-1], t[a]) becomes (t[a-1], t[b]), and the edge that was
(t[b], t[b+1]) becomes (t[a], t[b+1]). Hence an inversion of any length changes exactly two
undirected edges (assuming a and b are not adjacent to the wrap boundary in a degenerate way).

**What it does in this project.** `inversion_mutation()` in `ga.hpp`:
`std::reverse(t.begin() + a, t.begin() + b + 1)` for randomly chosen a ≤ b. This is also why the
edge-distance diversity metric (concept 6) responds sensitively but not chaotically to mutation: a
single mutation event perturbs the edge set by at most 2 edges out of n, a small, bounded, and
easily interpretable change.

**Measured impact.** No number in `FINDINGS.md` isolates the marginal effect of inversion mutation
in edges-changed terms; this is a structural/combinatorial fact about the operator, stated here as
a formal property, not as a measured result. It underlies (but is not directly measured in) the
diversity numbers of concept 6.

---

## Parallel computing theory

### 13. Speedup S(p) = T(1)/T(p), and what T(1) should be

**In plain terms.** Speedup answers "how many times faster is running on p workers compared to
running on one?" The honest way to compute this is to time the *same* algorithm doing the *same*
amount of work, once on one processor and once on p — not to compare against a different, weaker,
or artificially slowed single-processor version, which would inflate the apparent speedup.

**The formal statement.** S(p) = T(1) / T(p), where T(p) is the wall-clock time to solve a fixed
problem instance using p processors, and T(1) is the time for the best available sequential
execution of the same algorithm on the same instance (not a deliberately crippled baseline).

**What it does in this project.** `FINDINGS.md` §2 (E1) computes S(p) with islands **held fixed at
8** across all thread counts, 2-opt off, so that the amount of work per generation is identical
regardless of p — exactly the fix described in §6.2 of `PROJECT-GUIDE.md`: without holding island
count fixed, T(1) would correspond to a *different algorithm* (one big island) than T(8) (eight
small islands with a smaller, cache-friendlier working set), corrupting the meaning of S(p).

**Measured impact.** T(1) = 4.240 s, T(8) = 1.080 s, giving **S(8) = 3.93×** (`FINDINGS.md` §2).
The table also reports S(2) = 1.96×, S(3) = 2.49×, S(4) = 3.30×, S(6) = 2.83×.

### 14. Parallel efficiency E(p) = S(p)/p

**In plain terms.** Efficiency asks "of the p workers you paid for, how much of a full worker's
worth of extra speed did each one actually deliver, on average?" Perfect scaling gives efficiency
1.0 (every worker pulls its full weight); efficiency below 1.0 means some capacity is lost to
overhead, contention, or imbalance.

**The formal statement.** E(p) = S(p) / p. E(p) = 1 is ideal (linear) scaling; E(p) < 1 indicates
sub-linear scaling.

**What it does in this project.** Computed directly from the E1 speedups in `FINDINGS.md` §2.

**Measured impact.** E(1) = 1.00, E(2) = 0.98, E(3) = 0.83, E(4) = 0.83, E(6) = **0.47**, E(8) =
0.49. The load-balance-corrected efficiency column ("eff. vs ceiling") tells a different, fairer
story at p = 3 and p = 6: 0.93 and 0.71 respectively, once the unavoidable integer-division load
imbalance (concept 19) is accounted for.

### 15. Strong scaling vs weak scaling

**In plain terms.** Strong scaling asks: "if I keep the total problem exactly the same size and
just add more workers, how much faster does it finish?" Weak scaling asks a different question:
"if I give each worker the same amount of work and add more workers (so the *total* problem grows
too), does the time per worker stay flat?" This project only ever asks the first question.

**The formal statement.** Strong scaling: fix total problem size N, vary p, measure T(p) (and
derive S(p), E(p) as above). Weak scaling: fix per-processor problem size N/p (so total problem
size scales with p), and measure whether T(p) stays roughly constant as p grows.

**What it does in this project.** E1 (`FINDINGS.md` §2) fixes the number of islands at I = 8 (fixed
total population and fixed total work per epoch) and varies only the thread count p — this is
strong scaling by definition. No experiment in `FINDINGS.md` grows the total problem size (more
islands, larger population, or larger n) in proportion to p, so **weak scaling is not measured in
this project**.

**Measured impact.** The full strong-scaling table is §2's speedup/efficiency/Karp–Flatt columns,
already quoted above. There is no weak-scaling number to report, and none is claimed.

### 16. Amdahl's law: derivation, the serial-fraction ceiling, and this project's f = 0.155

**In plain terms.** However many workers you throw at a job, the part of the job that fundamentally
cannot be split up between them — the strictly serial part — puts a hard ceiling on how much total
speedup is possible, no matter how many workers you add. If 15% of the job simply cannot be
parallelised, you can never get faster than roughly 1/0.15 ≈ 6.5× no matter how many thousand cores
you use.

**The formal statement.** If a fraction f of a program's work is inherently serial and (1-f) is
perfectly parallelisable across p processors, the execution time is T(p) = T(1)·(f + (1-f)/p), so

  S(p) = 1 / (f + (1 - f)/p)

As p → ∞, S(p) → 1/f. This is the serial-fraction ceiling.

**What it does in this project.** `bench/analyze_study.py`'s `amdahl_fit()` performs a least-squares
fit of the measured S(p) values from E1 against this model to estimate f.

**Measured impact.** `FINDINGS.md` §2: the Amdahl fit on the E1 strong-scaling data gives
**f = 0.155**, implying a ceiling of **S(∞) = 1/0.155 ≈ 6.47×**. This is a fitted, empirical
estimate of the model's serial-fraction parameter against the measured S(p) curve, not a
theoretically derived value.

### 17. Gustafson's law and how it differs from Amdahl

**In plain terms.** Amdahl's law imagines a fixed job that you're trying to finish faster and faster
by adding workers — and finds a ceiling. Gustafson's law asks a different, often more realistic
question for real-world use: if you had more workers available, would you not also tackle a
*bigger* job in the same amount of time? Under that framing, the achievable "scaled speedup" is not
capped the same way, because the serial part does not grow while the parallel part is allowed to
grow with the machine.

**The formal statement.** Gustafson's law: if a fraction f of the (now scaled) execution time on p
processors is serial, the scaled speedup is S(p) = p − f·(p − 1) = f + (1-f)·p — linear in p, with
no fixed asymptotic ceiling as p grows, because the workload itself is assumed to grow with p
(weak-scaling framing), unlike Amdahl's fixed-workload framing.

**What it does in this project.** Nothing directly. This project never scales the problem size (or
island count) in proportion to thread count and measures whether time-per-worker stays flat — that
would be the Gustafson/weak-scaling experiment, and it is absent.

**Measured impact.** None. `FINDINGS.md` contains no Gustafson-law fit or scaled-speedup number.
This project measures strong scaling only (concept 15), so Gustafson's law is discussed here for
theoretical completeness but is explicitly **not measured** in this project — stated honestly
rather than implied.

### 18. The Karp-Flatt metric — the single most important theoretical point here

**In plain terms.** Amdahl's law and the Karp–Flatt metric both try to explain *why* speedup falls
short of ideal, but they disagree about how to tell two very different causes apart. Cause one: a
fixed chunk of the work genuinely cannot be split up, no matter how carefully the code is written
(an inherent serial fraction). Cause two: the work *could* in principle all be split up, but
splitting it introduces its own extra cost — communication, synchronisation, load imbalance — and
that cost gets proportionally worse as you add more workers (parallel overhead). Amdahl's law
alone cannot tell these apart from a single speedup number. The Karp–Flatt metric can, because of
how it behaves as you add more processors: if the *inferred* serial fraction stays roughly the same
number no matter how many processors you use, the limiting factor really is an inherent serial
section. If that inferred number keeps climbing as you add more processors, the limiting factor is
overhead that gets worse with scale, not an inherent serial ceiling — and no amount of removing
serial code will fix that; the fix is to reduce coordination cost.

**The formal statement.** Given measured speedup S(p) at p processors, the Karp–Flatt experimentally
determined serial fraction is:

  e(p) = (1/S(p) − 1/p) / (1 − 1/p)

If the true bottleneck is a constant Amdahl-style serial fraction f, then e(p) ≈ f for all p (a
flat line as p varies). If e(p) increases with p, the excess is attributable to overhead that
itself scales with the number of processors (synchronisation, contention, communication), which
Amdahl's single-fraction model cannot represent, since Amdahl's model assumes a fixed non-parallel
fraction independent of p.

**What it does in this project.** `bench/analyze_study.py`'s `karp_flatt()` function computes e(p)
directly from the E1 measured speedups for every p > 1.

**Measured impact.** `FINDINGS.md` §2 reports e = 0.020 at p = 2, 0.104 at p = 3, 0.070 at p = 4,
**0.224 at p = 6**, 0.148 at p = 8. The value at p = 2 (0.020) is far below the Amdahl-fitted
f = 0.155, and the sequence is **not flat** — it rises sharply toward p = 6 before falling back
somewhat at p = 8 (which coincides with switching from purely physical cores to SMT threads at
p = 6, i.e. p = 6 uses 6 of 4 physical cores + 2 SMT threads, discussed further in concept 19/23).
This rising trend is the evidence, internal to the project's own data, that the scaling limit
observed near p = 4–6 is **not** best explained as a single fixed inherent serial fraction (which
would keep e roughly constant near 0.155 at every p) but rather as **parallel overhead that grows
with processor count** — consistent with the project's own explanation (load imbalance from
`ceil(I/p)` island scheduling at non-divisor thread counts, concept 19, and per-epoch serial
bookkeeping, concept 20/4.1) rather than a fixed portion of the algorithm being condemned to run
serially forever. This is presented as the project's central HPC-theoretic argument precisely
because it distinguishes "the algorithm has a ceiling" from "the scheduling and synchronisation
mechanism has a fixable cost," which are different diagnoses with different remedies.

### 19. Load balancing and the ceil(I/p) argument

**In plain terms.** If you have 8 tasks and 3 workers, you cannot split the tasks perfectly evenly —
someone has to take 3 tasks while others take fewer, so the whole job takes as long as the busiest
worker's pile, which is `ceil(8/3) = 3` task-units, not the ideal `8/3 ≈ 2.67`. This is not a bug —
it is basic integer arithmetic — but it means the "ideal" speedup line is unreachable whenever the
number of workers does not evenly divide the number of independent chunks of work.

**The formal statement.** With I independent, equal-cost work units (islands) statically scheduled
across p workers (`schedule(static)`), the slowest worker is assigned `ceil(I/p)` units, so the
epoch's wall-clock cost is proportional to `ceil(I/p)` regardless of how evenly I actually divides
by p. The load-balance ceiling for speedup at p workers is I / ceil(I/p) (relative to the p=1 case,
this ratio caps the achievable speedup independent of any other overhead).

**What it does in this project.** I = 8 islands are distributed with `schedule(static)` across the
`omp for` in `island_opt.hpp`'s evolution phase (`PROJECT-GUIDE.md` §3.3). With I = 8:
`ceil(8/3) = 3`, `ceil(8/4) = 2`, `ceil(8/6) = 2`, `ceil(8/8) = 1`.

**Measured impact.** `FINDINGS.md` §2: "with I = 8, both p = 6 and p = 4 cost 2 units [ceil(8/6) =
ceil(8/4) = 2], and p = 6 additionally contends for 4 physical cores." This is exactly why **p = 6
measured slower than p = 4** (time 1.498 s vs 1.284 s, speedup 2.83× vs 3.30×): both configurations
do the identical amount of "island-unit" work per epoch (2 units each, since 8 does not divide
evenly by 6 or by 4, both round up to 2), but p = 6 additionally forces 2 of its 6 OpenMP threads
onto SMT siblings of already-busy physical cores (only 4 physical cores exist), adding contention
with no matching increase in island-units processed per epoch. The load-balance ceiling column in
the same table corrects the "raw" efficiency 0.83 at p = 3 up to **0.93 relative to what integer
scheduling could ever deliver**, showing that a chunk of the apparent inefficiency at p = 3 is pure
arithmetic, not a flaw in the parallel implementation.

### 20. Granularity and synchronisation cost; the barrier; epoch length as the knob

**In plain terms.** "Granularity" is how much work each processor does between check-ins with the
others. Fine granularity (check in constantly) means workers spend a larger fraction of their time
waiting at check-in points ("barriers") relative to the useful work between them; coarse
granularity (check in rarely) reduces that overhead but delays the exchange of new information
(e.g. migrated individuals) between workers. In this project, "epoch length" — how many generations
each island runs before all islands synchronise — is exactly this granularity knob.

**The formal statement.** A barrier is a synchronisation point at which every participating thread
must arrive before any may proceed past it. If a parallel region does W units of useful work
followed by a barrier costing B (waiting for the slowest thread plus barrier implementation
overhead), the fraction of time spent on overhead relative to useful work is B/(W+B); increasing
work-per-synchronisation-interval (granularity) reduces this ratio, at the cost of less frequent
information exchange.

**What it does in this project.** `--epoch-len E` sets the number of generations each island
computes before the two `omp for` synchronisation points and the `omp single` bookkeeping block
described in `PROJECT-GUIDE.md` §3.3.

**Measured impact.** `FINDINGS.md` §4.1 (E7), identical total work per cell: at p = 8, raising
epoch length from 1 to 250 drops time from 4.50 s to **0.91 s** and raises speedup from 2.45× to
**4.00×**. Critically, the same experiment at **p = 1** (no barriers exist at all when p = 1) still
shows time falling from 11.04 s to **3.63 s** — a 3× improvement with zero synchronisation present
— which is the project's evidence that most of this particular cost is **not** synchronisation
overhead per se but **per-epoch serial bookkeeping** (the diversity metric computation and the
"publish" copies that happen once per epoch regardless of thread count). True synchronisation cost
shows up separately as the p=8 efficiency numbers rising from lower values toward 0.50 as epoch
length grows (i.e., in the gap between the p=1 curve's improvement and the extra improvement seen
at p=8).

### 21. False sharing and cache lines — the honest null result

**In plain terms.** Modern CPUs move memory around in fixed-size chunks called cache lines (64
bytes here). If two different CPU cores are frequently writing to two different variables that
happen to live in the *same* 64-byte chunk, the hardware has to keep shuffling that whole chunk
back and forth between the cores' private caches even though the cores are not actually touching
each other's data — this is "false sharing," and it can silently slow things down. The textbook
fix is to pad each core's data out so no two cores' variables share a chunk. This project tried
that fix and measured that it did not help.

**The formal statement.** False sharing occurs when independent variables used by different threads
are placed within the same cache-line-sized memory block, causing cache-coherence traffic
(invalidations, line transfers) on every write to either variable, even though there is no logical
data dependency. The standard mitigation is padding/alignment (e.g. `alignas(64)`) so that each
thread's frequently-written data occupies its own cache line(s).

**What it does in this project.** `PROJECT-GUIDE.md` §7.1 describes the frozen baseline's per-island
state as parallel `std::vector`s where `pub_best_len[]` (8 doubles = exactly one 64-byte line) and
`pub_stag[]` (8 chars = one line) are written by all 8 threads every epoch, and where `island[id]`'s
vector header (24 bytes) means three islands' headers fit in one line, rewritten every generation.
The fix moved all per-island state into a single `alignas(64)`-padded `IslandSlot` per island in
`island_opt.hpp` so no two islands share a cache line.

**Measured impact.** `FINDINGS.md` §5: cache-line padding to remove false sharing produced
**0.92–0.99× (slightly slower)**. Verdict stated explicitly: "**No gain.** Not the bottleneck." This
is an honest negative result: the theoretical mechanism is real, and the fix was implemented
correctly, but at this problem's actual working-set sizes and write frequency it was not the
limiting factor.

### 22. Memory hierarchy: L1/L2/L3, working-set size, and the 480 KB vs 60 KB argument

**In plain terms.** A CPU core can access its small, very fast private cache (L1, then L2) far
quicker than the larger, shared, slower cache (L3) or main memory. If the data a core is actively
working on ("working set") fits inside its fast private cache, everything runs quickly; if it
overflows into slower memory, every access gets more expensive. This project found that its
original experiment accidentally changed working-set size at the same time as changing thread
count, which meant part of what looked like "parallel speedup" was actually just "the data got
small enough to fit in a faster cache" — a completely different, non-parallel effect.

**The formal statement.** The memory hierarchy comprises L1 (smallest, fastest, per-core), L2
(larger, still generally per-core, on this CPU), and L3 (largest, shared across cores, 6 MB on the
measurement platform's i5-10210U). Working-set size is the amount of actively-touched memory during
a computational phase; when it exceeds a cache level's capacity, accesses spill to the next, slower
level, increasing average memory latency.

**What it does in this project.** The frozen baseline hard-wires one island per thread, so
`island_pop = P/T`: raising thread count T shrinks each thread's own working set even though the
*total* population stays fixed. `PROJECT-GUIDE.md` §6.2 computes: at P = 240 and n = 500, the
serial (T=1) population is 240 × 500 × 4 bytes ≈ **480 KB**, which overflows this CPU's L2, while
one island of 30 individuals at T = 8 is ≈ **60 KB**, which fits comfortably in L2. `--islands I`
(decoupled from `--threads T`) was introduced specifically to break this conflation, by holding the
per-island working set (and hence I) fixed while sweeping T.

**Measured impact.** `FINDINGS.md` §3.2 states this conflation directly: raising T under the frozen
engine "simultaneously adds parallelism, changes the algorithm, and shrinks the per-thread working
set (240 individuals × 500 ints ≈ 480 KB overflows L2; 30 individuals ≈ 60 KB fits)." The fix
(`--islands` decoupling, verified bit-identical trajectories across thread counts via the per-island
RNG streams) is what makes the E1 strong-scaling numbers (§2, S(8) = 3.93×) attributable to
parallelism alone rather than partly to this cache effect. No separate micro-benchmark isolating the
480 KB vs 60 KB cache-effect magnitude on its own (in seconds or ×) is reported in `FINDINGS.md`;
the number that exists is the corrected, cache-effect-free E1 table itself.

### 23. SMT / hyper-threading: why 8 threads on 4 physical cores does not give 8x

**In plain terms.** This CPU has 4 physical cores, but each core can pretend to be two logical
processors (Simultaneous Multi-Threading / hyper-threading) by interleaving two threads' instructions
through the same physical execution hardware. Those two logical threads are still sharing one
core's actual arithmetic units, caches, and pipeline — so going from 4 threads (one per physical
core) to 8 threads (two per physical core) adds much less real extra throughput than going from 1
thread to 4 did, because you are no longer adding hardware, only adding scheduling opportunities on
hardware you already had.

**The formal statement.** SMT allows multiple hardware threads to share the execution resources of
a single physical core, exploiting instruction-level parallelism gaps but not providing an
independent set of execution units per logical thread. Consequently, for compute-bound workloads
(as opposed to memory-latency-bound ones, which SMT helps more), speedup from p ≤ (physical cores)
tends to be substantially better per added thread than from p in (physical cores, logical threads].

**What it does in this project.** The i5-10210U has 4 physical cores / 8 SMT threads
(`FINDINGS.md` platform description). E1 sweeps thread count from 1 to 8, crossing the physical-core
boundary at p = 4.

**Measured impact.** `FINDINGS.md` §2: efficiency climbs from 1.00 (p=1) down only modestly through
the physical-core range (0.98 at p=2, 0.83 at p=3, 0.83 at p=4), then drops sharply once SMT
threads are engaged: **0.47 at p=6, 0.49 at p=8** — i.e. going from 4 to 8 threads (doubling
thread count, but using SMT beyond the 4 physical cores) raises speedup from only 3.30× to 3.93×,
far short of a further doubling. §8 (Known limitations) states this explicitly: "4 physical cores;
results at 6 and 8 threads use SMT, so efficiency past 4 is expected to fall" — matching the
measured drop.

### 24. Race conditions, data races, barriers, and why this code is race-free without locks

**In plain terms.** A "race condition" is a bug where the correctness of a program depends on the
unpredictable timing of different threads — two threads reading and writing the same piece of
memory at overlapping times, with the result depending on who gets there first. This project avoids
that entire class of bug by design: during the part where real computation happens, each thread
only ever touches its *own* island's data, never anyone else's, so there is nothing to race over.
The only place threads read each other's data (migration) happens strictly after a synchronisation
point that guarantees the writes are all finished and visible first.

**The formal statement.** A data race occurs when two or more threads access the same memory
location concurrently, at least one access is a write, and the accesses are not ordered by a
synchronisation mechanism (locks, atomics, barriers with well-defined happens-before semantics).
A program is race-free if every pair of conflicting accesses is ordered by some synchronisation
relation. An OpenMP barrier (implicit at the end of `omp for`/`omp single` without `nowait`) is a
full synchronisation point: no thread may proceed past it until all threads have arrived, and all
writes before the barrier are visible to all threads after it (a happens-before edge).

**What it does in this project.** `PROJECT-GUIDE.md` §3.3's OpenMP structure: the evolution phase
(`omp for` over islands) has each thread write only into its own island's slot; the implicit
barrier at the end of that `omp for` orders every island's "publish" write before any thread enters
the migration phase (`omp for` over islands reading peers' published state and writing only its
own); another implicit barrier orders migration completion before the single-threaded bookkeeping
phase. `PROJECT-GUIDE.md` §7.4 additionally documents a **found and fixed defect**: the frozen
baseline's `omp single` used its implicit barrier believing it guaranteed migration was already
complete, but `omp single`'s implicit barrier is at its *exit*, not entry, so bookkeeping could
read `total_migrations` while other threads were still migrating — the optimised engine instead
uses `omp for`, whose exit barrier correctly orders the phases.

**Measured impact.** This is a structural/correctness property (verified by the differential tests
`tests/test_equiv.cpp` and `tests/test_island_equiv.cpp`, which assert bit-for-bit agreement between
baseline and optimised engines), not something FINDINGS.md reports as a throughput or quality
number. The one measurable symptom of the §7.4 defect that FINDINGS.md-adjacent material identifies
is that it makes "the logged migration counts... unreliable" (`PROJECT-GUIDE.md` §7.4) — a
correctness/reliability finding, not a numeric one, and no such number appears in `FINDINGS.md`
because the defect did not corrupt final results (the exit barrier still orders migration before
the next epoch), only the per-epoch log.

### 25. Reproducibility in parallel stochastic programs: per-island RNG streams

**In plain terms.** A genetic algorithm is driven by randomness (which parents get picked, where
mutations land). If that randomness were seeded per *thread* instead of per *island*, then simply
changing how many threads you run with — a purely technical, "how do I use my hardware" decision —
would silently also change which random numbers each island sees, and therefore change the actual
search the program performs. That would make it impossible to say cleanly "the only thing that
changed was speed" when comparing thread counts, because the search itself would have changed too.
Seeding randomness by island identity instead of by thread identity fixes this: each island always
sees exactly the same sequence of random numbers no matter which thread, or how many threads, ends
up running it.

**The formal statement.** Reproducibility of a stochastic parallel program under a varying degree of
parallelism requires that the sequence of pseudo-random values consumed by each independent unit of
work (here, an island) be a deterministic function of that unit's identity alone, not of the thread,
core, or scheduling decision that happens to execute it. This is achieved by keying each PRNG
stream's seed to the island id (`base_seed + island_id`) rather than to a thread-local or global
shared generator.

**What it does in this project.** `src/rng.hpp`: "One stream per ISLAND (not per thread), seeded
`base_seed + island_id`." Both `island.hpp` and `island_opt.hpp` draw exclusively from their own
island's stream during evolution.

**Measured impact.** `FINDINGS.md` §3.2 states this was **verified, not assumed**: "every thread
count now produces a bit-identical search trajectory." This is what makes the E1 strong-scaling
table (concept 13/14/18) a clean measurement of parallel speedup alone — since the search path is
provably identical at every p, any time difference between thread counts is due only to execution
speed, never to a different random walk through the search space. Without this property, a faster
time at higher p could always be dismissed as "maybe it just got a luckier random search," which
this design rules out by construction and by verification.

---

## Statistics and measurement

### 26. Why wall-clock measurement on a laptop is hard; the min-over-samples estimator

**In plain terms.** A laptop's CPU secretly speeds itself up and slows itself down constantly
(turbo boost when cool, throttling when hot, background OS work stealing cycles) — none of which
has anything to do with the algorithm being measured. If you only time something once, you might
catch it during an unlucky slow moment and wrongly conclude the algorithm is slow. The fix used
here: since noise can only ever make a run slower than its true best-case speed (never genuinely
faster than what the hardware can do), take many repeated timings of the identical work and report
the *fastest* one observed — that is the measurement least contaminated by transient slowdowns.

**The formal statement.** Given a true underlying execution time T for a fixed amount of work, and
additive non-negative noise (thermal throttling, OS scheduling jitter, background interrupts) that
can only inflate observed time above T, never deflate it below T, the minimum of n independent
observed samples is a consistent estimator that converges toward T as n grows, and is less biased
upward by noise than the mean.

**What it does in this project.** `PROJECT-GUIDE.md` §6.3: the harness "measures every configuration
multiple times, schedules repeats round-robin across the whole configuration list... and times a
fixed 'canary' configuration at the start of every round to quantify drift." With 2-opt off, all
seeds at a given configuration do identical work, so "the estimator is the **minimum** over all
samples: timing noise is additive, so the fastest observed run is the closest estimate of true
throughput."

**Measured impact.** `FINDINGS.md`'s header states the scale this estimator was applied over:
"1,600+ measured configurations across ten experiments, every one of them validated... Zero
validation failures." No specific thermal-drift percentage is quoted in `FINDINGS.md` itself, so
none is stated here as a number.

### 27. Median vs mean for skewed timing data

**In plain terms.** If you average a handful of numbers and one of them is a huge outlier (say, a
run that got interrupted by a background update), that single outlier can drag the average far
from what's "typical." The median — the middle value when everything is sorted — mostly ignores how
extreme an outlier is and just cares about its rank, so it is much more robust to skewed data.

**The formal statement.** For a sample X₁...Xₙ, the mean is sensitive to the magnitude of every
observation, so a single arbitrarily large outlier can shift it arbitrarily far; the median (the
middle order statistic, or average of the two middle order statistics for even n) has a breakdown
point of 50% and is unaffected by the specific magnitude of outliers, only their rank.

**What it does in this project.** Quality comparisons in `FINDINGS.md` (e.g. §5.1's candidate-list
2-opt table, §6.4's DTAM rescue table) are reported as **medians** across seeds ("median tour
length" is the explicit column header in §4.2 and the values quoted in §5.1/§6.4), reflecting a
deliberate choice for the (typically right-)skewed distribution of stochastic-GA tour-length
outcomes across seeds.

**Measured impact.** Every quality number quoted throughout `FINDINGS.md`'s §4.2, §5.1, and §6.4
tables is a median over the stated seed count (8 or 10 seeds), not a mean — this choice is baked
into the reported numbers themselves rather than being a separate measured quantity.

### 28. The Wilcoxon signed-rank test

**In plain terms.** To decide whether one method is genuinely better than another (not just
luckily better on the particular random seeds tried), you need a statistical test. The Wilcoxon
signed-rank test is well suited here because it compares two methods on *the same* set of seeds,
one seed at a time (paired), and it does not assume the underlying data follows a bell curve
(non-parametric) — reasonable for tour lengths from a stochastic search, which have no guaranteed
distributional shape. With only a handful of paired samples, though, there's a mathematical floor
on how small a p-value the test can possibly report, no matter how large or consistent the
difference is.

**The formal statement.** The Wilcoxon signed-rank test evaluates the null hypothesis that the
median of the paired differences (dᵢ = Xᵢ − Yᵢ, for paired observations Xᵢ, Yᵢ under two conditions
on the same unit i, here the same random seed) is zero. It ranks the absolute differences |dᵢ|,
sums the ranks associated with positive and negative differences separately, and derives a p-value
from the distribution of the smaller rank sum under the null. It is paired because it removes
seed-to-seed variance common to both conditions; it is non-parametric because it uses ranks rather
than assuming a normal distribution of differences. For n paired non-zero-difference samples with
no ties, the smallest attainable two-sided p-value under the exact distribution is 2/2ⁿ; for n = 10
this floor is **2/1024 ≈ 0.00195**, which rounds to the commonly reported **p = 0.0020**.

**What it does in this project.** `bench/analyze_study.py` calls `scipy.stats.wilcoxon(t, f)` to
compare paired per-seed timings/lengths between two conditions (e.g. DTAM vs fixed migration,
naive vs fast 2-opt).

**Measured impact.** `FINDINGS.md` §5.1 reports **p = 0.0020** for four of six candidate-list-2-opt
comparisons (uniform500 fixed and dtam, clustered600 fixed and dtam, kroA200 fixed), explicitly
described in the text as "the smallest value attainable with n = 10 paired samples" — i.e. these
results are as statistically significant as 10 paired seeds can ever show, and the floor itself,
not a stronger true effect that a bigger sample would somehow reveal as an even smaller p, is why
the number does not go lower. a280's comparison (n=10 as well but likely containing ties or fewer
non-zero differences) reports p = 0.0078. §6.1 (equal-wall-clock DTAM comparison) reports
**p = 0.001** on a different (larger) paired sample. §6.4's table gives p ranging from 0.0020 to
0.0371 for the rescue-configuration comparisons.

### 29. Multiple comparisons and the Bonferroni correction

**In plain terms.** If you run 24 separate statistical tests and consider "p < 0.05" as your bar
for "significant," you should expect roughly one of those 24 tests to cross that bar purely by
chance, even if nothing real is going on in any of them — because a 5%-chance false alarm rate,
multiplied across 24 independent rolls of the dice, adds up. The Bonferroni correction protects
against this by making the bar per-test much stricter (dividing the overall 5% budget by the number
of tests), so that the *overall* chance of any false alarm across the whole set stays near 5%.

**The formal statement.** The Bonferroni correction controls the family-wise error rate across m
simultaneous hypothesis tests by requiring each individual test's p-value to fall below α/m (rather
than the uncorrected α) to be declared significant at overall level α. With α = 0.05 and m = 24
comparisons, the corrected per-comparison threshold is **0.05/24 ≈ 0.00208**.

**What it does in this project.** `FINDINGS.md` §6.4/§6.5 point 4: the DTAM-rescue factorial in §6.4
constitutes a table of 24 comparisons (multiple configurations × multiple instances/conditions).

**Measured impact.** One cell in that table (het+rel, clustered-600 with 2-opt) shows DTAM ahead by
−0.2% at **p = 0.0273** — nominally "significant" against the naive α = 0.05 threshold, but
"with 24 comparisons in the table a Bonferroni-corrected threshold is 0.05/24 = 0.002" (`FINDINGS.md`
§6.5, point 4), and **0.0273 > 0.002**, so this result is explicitly stated as **not significant**
and must not be reported as a DTAM win. This is a direct, correctly-applied worked example of why
the Bonferroni correction matters: a single "significant-looking" p-value out of many comparisons
is exactly what you'd expect from noise alone, and the project's own conclusion (§6.4, "No
configuration was found in which DTAM meaningfully beats fixed migration") is consistent with
having correctly discounted this one cell.

### 30. Correlation vs causation, and the confound this project actually found

**In plain terms.** Two things being correlated (they tend to move together) does not tell you that
one *causes* the other, or which direction any causal arrow points — there might be a third factor
driving both. In this project's original speedup measurement, tour quality and wall-clock time were
correlated not because faster machines happen to also produce better tours by magic, but because
both were being driven by a shared underlying factor: 2-opt's cost genuinely depends on tour
quality, so runs that (for whatever reason) found better tours also, mechanically, ran faster —
making "speedup" partly a measurement of tour-quality luck rather than of parallel hardware
performance.

**The formal statement.** Correlation between two measured variables X and Y (here, tour length and
wall-clock time at a fixed thread count) is consistent with several causal structures: X causes Y,
Y causes X, or a third variable Z causes both. Observing correlation alone cannot distinguish these
without additional structural knowledge or a controlled intervention. A confounded experimental
protocol is one in which the variable of interest (parallelism) and a nuisance variable (tour
quality, via 2-opt's variable per-tour cost) are not held independent, so an observed effect
(speedup) cannot be cleanly attributed to the variable of interest alone.

**What it does in this project.** `FINDINGS.md` §3.1 (E3) directly measures the correlation between
tour length and wall-clock time at fixed thread count under the original ("equal work," 2-opt-on)
protocol.

**Measured impact.** "Measured correlation between tour length and wall-clock at fixed thread count:
**+0.15 to +0.31**, with a 6–8% time spread and 4.8% length spread. The effect is real and in the
predicted direction, though modest." The mechanism is explicit, not merely statistical: 2-opt is
first-improvement local search whose cost depends on incoming tour quality (concept 8/9), so this
positive correlation is causally explained (better tour → less 2-opt work → faster wall-clock),
which is precisely why the project's fix (§3.1's resolution) is to measure speedup with 2-opt off,
where correlation cannot arise because work per generation is fixed, and to measure quality
separately under an equal wall-clock budget instead of conflating the two.

---

## FORMULA SHEET

| Concept | Formula | Symbols | This project's measured value |
|---|---|---|---|
| Search space size (symmetric TSP) | (n-1)!/2 | n = number of cities | n=51 (eil51): ≈3.04×10^64 possible tours; solver reaches the proven optimum 426 (0.00% gap) |
| Speedup | S(p) = T(1)/T(p) | T(p) = wall-clock time on p processors | S(8) = 3.93×, T(1)=4.240 s, T(8)=1.080 s (E1) |
| Parallel efficiency | E(p) = S(p)/p | S(p) = speedup, p = processor count | E(2)=0.98, E(4)=0.83, E(6)=0.47, E(8)=0.49 |
| Load-balance ceiling | I / ceil(I/p) | I = islands, p = threads | I=8: p=3 and p=6 both ceiling at 2.67x/4.00x band, correcting p=3 eff. to 0.93 |
| Karp-Flatt experimentally-determined serial fraction | e(p) = (1/S − 1/p) / (1 − 1/p) | S = S(p), p = processor count | e: 0.020 (p=2) → 0.104 (p=3) → 0.070 (p=4) → 0.224 (p=6) → 0.148 (p=8) |
| Amdahl's law | S(p) = 1 / (f + (1-f)/p) | f = serial fraction | fitted f = 0.155, ceiling 1/f ≈ 6.47× |
| Gustafson's law (not measured here) | S(p) = p − f(p−1) | f = serial fraction, p = processors | not applicable — this project measures strong, not weak, scaling |
| Euclidean distance | d(i,j) = sqrt((xi−xj)² + (yi−yj)²) | (xi,yi), (xj,yj) = city coordinates | underlies `TSPInstance::raw_dist` in `src/tsp.hpp` |
| TSPLIB EUC_2D rounding | d_rounded = floor(d + 0.5) | d = raw Euclidean distance | applied when `rounded == true` (all TSPLIB instances); e.g. berlin52 reaches exactly 7542 |
| BHH asymptotic estimate | L* ≈ 0.7124 · sqrt(n · A) | n = city count, A = area | `src/tsp.hpp` line 136; an asymptotic approximation only — FINDINGS.md §1 notes a "gap" against it can even be negative, hence it is not used as the optimum reference |
| Circle-instance closed-form optimum | L = n · 2R · sin(π/n) | n = cities, R = radius | reached to 0.00% gap; used as a build gate (`build.ps1`) |
| Edge distance between two tours | edge_distance(A,B) = (n − |shared edges|) / n | n = cities, shared edges = edges common to both tours | underlies all diversity numbers, e.g. mean 0.0181 |
| Population diversity | mean over population of edge_distance(individual, island-best) | — | 0.224 (gen 10) → 0.0029 min, mean 0.0181 (whole DTAM run) |
| 2-opt gain | delta = d(A,C) + d(B,D) − d(A,B) − d(C,D) | edges (A,B), (C,D) removed; (A,C), (B,D) added | move applied iff delta < −1e-9; candidate-list version gives 7.8–13.2× speedup |
| Percentage gap | gap% = (result − optimum) / optimum × 100 | result = achieved tour length | 0.00% on all 7 TSPLIB instances with candidate-list 2-opt |
| Wilcoxon significance floor (n=10) | p_min = 2 / 2ⁿ | n = number of paired samples | 2/1024 ≈ 0.00195, reported as p = 0.0020 |
| Bonferroni-corrected threshold | α_corrected = α / m | α = 0.05, m = number of comparisons | 0.05 / 24 = 0.00208 ≈ 0.002; the observed p=0.0273 cell fails this |

---

## THEORY THAT WAS TESTED AND DID NOT APPLY

A negative result — "we correctly predicted a mechanism should help, implemented it correctly, and
measured that it did not" — is a legitimate and valuable application of theory. It is not a failure
of the project; it is a demonstration that theory was used to generate a testable prediction, and
that the prediction was checked against measurement rather than assumed. All three cases below are
reported in `FINDINGS.md` §5 ("Engineering changes and what they actually bought") with an explicit
verdict of "No gain."

| Theory applied | Prediction | Measured result | Why it did not apply here |
|---|---|---|---|
| False sharing / cache-line contention (concept 21) | Padding per-island state to separate cache lines should reduce coherence traffic and speed up the parallel region | **0.92–0.99×** (slightly slower) | The theoretical mechanism is real, but at this problem's actual shared-write frequency the cost is negligible against roughly 15,000 operations of useful work per shared write (`PROJECT-GUIDE.md` §7.0); the padding's own extra memory footprint and reduced cache locality cost slightly more than the coherence traffic it removed |
| Per-generation heap allocation / allocator contention | Eliminating `pop_size` allocations per generation per thread should reduce contention on the shared heap arena | **No gain** (effect included in the same 0.92–0.99× band as the false-sharing fix, since both were bundled into the same re-engineered engine) | Modern allocators (the measurement platform's libc/MSYS2 allocator) use per-thread arenas, so the presumed shared-heap contention was not actually occurring |
| RNG locality (moving RNG state to thread-local storage) | Centralised/shared RNG state could be a source of false sharing or contention across threads | **0.92–0.99×** | "Hypothesis tested and rejected" (`FINDINGS.md` §5, table) — the per-island RNG design (concept 25) already isolated RNG state adequately; moving it to thread-local storage bought nothing further |

What did locate the real cost, by contrast, was not pattern-matching against a list of textbook HPC
bottlenecks but a controlled experiment: E7 (concept 20), which showed that even at p = 1 — where no
barriers exist at all — time still fell 3× as epoch length grew, pointing at per-epoch serial
bookkeeping (the diversity metric and publish copies) rather than at synchronisation, false sharing,
or allocation. The methodological lesson, stated in `PROJECT-GUIDE.md` §7.0: "the presumed
bottlenecks were not the bottleneck... guessing at bottlenecks by pattern-matching does not pay."
