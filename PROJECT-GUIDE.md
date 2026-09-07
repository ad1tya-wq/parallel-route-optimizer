# ParallelRoute — Project Guide

**Course:** High Performance Computing (BCSE414L) · Mini-Project · Review 2
**Author:** Aditya Sahu — 23BCE0873
**Measurement platform:** Intel Core i5-10210U (4 physical cores / 8 SMT threads, 1.6 GHz base,
6 MB L3, 15 W), 8 GB RAM, Windows 11, GCC 15.1 (MSYS2 UCRT64), `-O3 -march=native -fopenmp`.

This is the working document for the project: how to build and run it, what every component does,
what the novelty actually is and how it holds up against prior work, and why the technology
choices are the right ones. Numbers quoted here are regenerated from this machine — see
[Reproducing every number](#8-reproducing-every-number).

---

## 1. What the project is, in one paragraph

The Travelling-Salesman Problem (TSP) is NP-hard, so production route optimisation uses
metaheuristics rather than exact solvers. A genetic algorithm (GA) is a natural candidate, and the
**island model** is the standard way to parallelise one: split the population into sub-populations
("islands"), evolve each independently on its own core, and periodically exchange a few
individuals ("migration"). This project builds three engines on **one shared GA core** — a serial
baseline, a textbook island model with fixed periodic ring migration (**P1**), and **DTAM**, a
diversity-triggered distant-source migration policy (**P2**) — and measures them as a *parallel
computing* problem: speedup, parallel efficiency, Karp–Flatt serial fraction, and Amdahl ceiling,
alongside tour quality.

---

## 2. Quick start

### 2.1 Prerequisites

| Need | Windows | Linux / macOS |
|---|---|---|
| C++17 compiler with OpenMP | [MSYS2](https://www.msys2.org) → `pacman -S mingw-w64-ucrt-x86_64-gcc` | GCC or Clang (macOS: `brew install libomp`) |
| Python 3.9+ | python.org | system package |
| Python packages | `pip install numpy matplotlib scipy python-pptx python-docx` | same |

CMake is **optional**. The engine is header-only plus one translation unit, so a single compiler
invocation is enough, and the repo ships a script for that.

### 2.2 Build

```powershell
.\build.ps1
```

That locates a g++ with OpenMP, compiles with `-O3 -march=native -fopenmp`, links **statically**
(so `build\ParallelRoute.exe` runs on a machine with no MSYS2 installed), and then runs a
self-test on the `circle` instance, whose optimal tour length is known in closed form. If the
self-test does not report a `0.00%` gap, the build is rejected.

On Linux/macOS, or in an MSYS2 shell:

```bash
make          # build
make test     # differential + correctness tests
```

CMake still works if you prefer it:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build --config Release
```

### 2.3 Run something

```powershell
# Solve a real TSPLIB instance and check against its published optimum
.\build\ParallelRoute.exe --in data\berlin52.tsp --mode island-dtam --engine opt `
    --islands 8 --threads 4 --generations 3000 --twoopt --validate

# 500 random cities, render the tour
.\build\ParallelRoute.exe --gen uniform --n 500 --mode island-dtam --engine opt `
    --islands 8 --threads 4 --pop 240 --generations 2000 --twoopt --svg results\route.svg

# Full help
.\build\ParallelRoute.exe --help
```

### 2.4 Reproduce the study

```powershell
python bench\run_study.py        # ~45 min on the i5; writes results\study_E*.csv
python bench\analyze_study.py    # writes results\analysis\*.csv and results\figures\*.png
```

> **Leave the machine idle while `run_study.py` runs.** It is measuring wall-clock on a 15 W
> laptop part. Browsing during the run will show up in the numbers. The harness reports a thermal
> drift figure at the end of each experiment so you can tell whether a run was clean.

---

## 3. What each component does

```
src/                 C++17 engine (header-only) + CLI
  rng.hpp            Per-island mt19937_64 wrapper. One stream per ISLAND (not per thread),
                     seeded base_seed + island_id. This is what makes a run's result
                     independent of how many threads execute it.
  tsp.hpp            TSPInstance: TSPLIB EUC_2D loader, three instance generators
                     (uniform / clustered / circle), full precomputed distance matrix,
                     published-optimum lookup table, gap computation.
  ga.hpp             The shared GA core: tournament selection, Order Crossover (OX),
                     inversion mutation, elitism, bounded 2-opt local search, and the
                     edge-set diversity metrics DTAM is built on. Also holds the
                     allocation-free variants used by the optimised engine, and
                     validate_tour() (permutation + independent length recomputation).
  island.hpp         FROZEN Review-1 engine. Serial + island (P1/P2), one island per
                     thread. Kept byte-for-byte as the audit baseline so the Review-2
                     rewrite can be measured against it rather than replacing it.
  island_opt.hpp     Re-engineered engine (--engine opt): islands decoupled from threads,
                     cache-line-padded per-island state, no per-generation allocation.
  timer.hpp          omp_get_wtime() wrapper with a std::chrono fallback.
  svg.hpp            Renders the best tour to a standalone SVG.
  main.cpp           CLI, instance construction, engine dispatch, validation gate,
                     human summary, machine-readable CSV row, SVG output.

tests/
  test_equiv.cpp        Differential test: step_generation vs step_generation_opt must
                        agree for 200 consecutive generations, individual by individual.
  test_island_equiv.cpp Differential test at engine level: run_islands vs run_islands_opt
                        must agree on best length and migration count at 1, 2 and 4 threads.

bench/
  run_study.py       Review-2 harness. Six experiments (E1-E6), repeat/round-robin
                     scheduling, thermal-drift canary. See section 6.
  analyze_study.py   Speedup, efficiency, Karp-Flatt, Amdahl fit, tau analysis,
                     paired Wilcoxon policy tests, figures.
  run_bench.py       Original Review-1 harness, kept so the old protocol can be re-run.
  plot_results.py    Original plotting, kept for the same reason.
  analyze.py         Original summary statistics.

data/                TSPLIB EUC_2D instances with published optima.
results/
  study_E*.csv       Raw Review-2 measurements from this machine.
  analysis/*.csv     Derived tables (the ones quoted in the report).
  figures/*.png|svg  Figures.
  m3_original/       The Review-1 result set from the Apple M3, preserved unchanged.
report/              Report and slide deck, plus the scripts that build them.
```

### 3.1 The three engines

| Mode | What it is | Role |
|---|---|---|
| `serial` | one panmictic population of size *P* on one core | baseline |
| `island-fixed` | *I* islands of size *P/I*; every island copies its ring neighbour's best-*K* over its own worst-*K*, every `migrate_interval` epochs | naive parallel (**P1**) |
| `island-dtam` | same engine; an island migrates **only when its diversity collapses**, and **pulls** from the most genetically different island | adaptive parallel (**P2**) |

### 3.2 DTAM, precisely

Once per epoch, on each island:

1. **Measure diversity** — mean edge-set distance between the island's population and its own
   best tour. A tour is a set of *n* undirected edges; the distance between two tours is the
   fraction of edges they do not share. Low value ⇒ the island has converged.
2. **Publish a signature** — the island's best tour, readable by peers.
3. **Flag stagnation** — if diversity < τ.
4. **Pull migrants** — a stagnating island imports the best *K* individuals from the
   non-stagnating island whose signature is *most different* from its own (falling back to the
   most distant island overall if every peer is stagnating), overwriting its own worst *K*.
   Non-stagnating islands skip migration entirely.

Against P1 the design differs in three ways: fixed schedule → diversity-triggered; fixed ring
neighbour → runtime-selected distant source; push → pull.

### 3.3 The OpenMP structure

```
#pragma omp parallel num_threads(T)
  loop over epochs:
     [omp for over islands]  evolve E generations, publish state   <- all the real work
     ---- implicit barrier: every publish visible before any read ----
     [omp for over islands]  migrate (read peers' slots, write own)
     ---- implicit barrier ----
     [omp single]            global best, logging, termination check
```

Each thread touches only its own island's data during evolution, so no locks are needed; the
barriers order publish-before-read and migrate-before-next-epoch. Timing uses `omp_get_wtime()`.

---

## 4. Key CLI flags

| Flag | Meaning |
|---|---|
| `--mode serial\|island-fixed\|island-dtam` | which engine |
| `--engine baseline\|opt` | frozen Review-1 island engine, or the re-engineered one |
| `--islands I` | number of islands (default: equal to `--threads`) |
| `--threads T` | OpenMP threads |
| `--pop P` | **total** population, split across islands |
| `--generations G` / `--time S` | work budget / wall-clock budget |
| `--epoch-len E` | generations between synchronisation points |
| `--migrate-interval` / `--migrants K` | P1 migration schedule and size |
| `--tau t` | DTAM stagnation threshold |
| `--twoopt [--twoopt-rate r] [--twoopt-passes p]` | bounded 2-opt local search |
| `--in file.tsp` / `--gen uniform\|clustered\|circle --n N` | instance |
| `--validate` | verify the returned tour is a permutation and its length is correct; non-zero exit if not |
| `--csv-log` / `--out` / `--svg` | convergence log / summary row / tour rendering |

**`--islands` is the important new one.** See section 6.

---

## 5. Correctness: how we know the solver is right

Three independent checks, all runnable:

1. **Closed-form optimum.** `--gen circle --n 50` places points on a circle, whose optimal tour is
   the polygon visiting them in angular order, of length exactly `n · 2R · sin(π/n)`. The solver
   reaches it with a 0.00% gap. `build.ps1` runs this as a build gate.
2. **Published optima.** On TSPLIB instances the solver reaches the published optimum exactly on
   `berlin52` (7542), `st70` (675), `kroA100` (21282) and `ch150` (6528), and lands within 0.23% on
   `eil51`. These are externally verifiable numbers, not self-generated references.
3. **Structural validation.** `--validate` checks that the returned tour is a genuine permutation
   of `0..n-1` and that its reported length matches an independent recomputation. Every run in the
   study is validated; the harness reports the pass count.

Additionally, `tests/test_equiv.cpp` and `tests/test_island_equiv.cpp` are differential tests
asserting that the optimised engine reproduces the frozen baseline exactly. They are not
decoration — `test_equiv` is what caught the tie-ordering bug described in section 7.3.

---

## 6. The measurement problems this project had to fix

The Review-1 numbers were produced on an Apple M3 by a harness that had three measurement flaws.
Finding and fixing them is a substantial part of the Review-2 contribution, because two of the
Review-1 headline claims do not survive the fix.

### 6.1 "Equal work" was not equal work

The original speedup protocol held total population *P* and total generations *G* fixed, so all
modes perform the same number of fitness evaluations, and ran with **2-opt enabled**.

But 2-opt is a *first-improvement local search*: it keeps sweeping until it finds no improving
move. On a bad tour it performs many improving reversals; on a good tour it exits after one
fruitless pass. **Its cost depends on the quality of the tour it is given.** So two runs that
perform the same number of fitness evaluations do *not* perform the same amount of work, and a run
that happens to find better tours finishes sooner — for reasons that have nothing to do with
parallelism.

This is directly observable. Under the original protocol on this machine, `island-dtam` at 2
threads finished in 7.68 s while `island-fixed` at 2 threads took 14.79 s — a 1.9× difference
between two engines doing nominally identical work, tracking the fact that DTAM reached better
tours. With 2-opt disabled the same sweep is smooth and monotone.

**Fix:** speedup is measured with 2-opt **off**, where work per generation is genuinely fixed.
2-opt's effect on quality is measured separately, under an equal *wall-clock* budget (E5), which
is the protocol that actually answers "which engine should I use for N seconds?". Experiment E3
quantifies the confound rather than hiding it.

### 6.2 Thread count and problem decomposition were entangled

The original engine hard-wires **one island per thread**, so `island_pop = P/T`. Raising *T* from 1
to 8 therefore does three things at once:

1. adds hardware parallelism (what we want to measure),
2. changes the *algorithm* — 8 small islands search differently from 1 big one,
3. shrinks the per-thread working set — at *P* = 240 and *n* = 500 the serial population is
   240 × 500 × 4 B ≈ 480 KB, which overflows this CPU's L2; one island of 30 individuals is
   ≈ 60 KB, which fits comfortably.

Effect (3) alone makes the parallel runs faster per unit work. Folding it into "speedup" is how a
4-core machine produces an apparently super-linear result.

**Fix:** `--islands I` decouples the decomposition from the thread count. Holding *I* = 8 and
sweeping *T* = 1…8 measures parallel speedup alone. Because each island owns an RNG stream keyed by
island id, **every thread count produces a bit-identical search trajectory** — verified, not
assumed — so wall-clock is the only thing that varies. Experiment E2 re-runs the original protocol
so the two can be compared directly and the artefact quantified.

### 6.3 One sample per configuration, no drift control

The original harness timed each configuration once. On a 15 W laptop part with aggressive turbo
and thermal management, that is well inside the noise floor. The new harness measures every
configuration multiple times, schedules repeats **round-robin** across the whole configuration
list (so thermal drift is spread evenly rather than concentrated in whichever configuration ran
during the hot patch), and times a fixed "canary" configuration at the start of every round to
quantify drift. With 2-opt off, all seeds at a given configuration do identical work, so the
estimator is the **minimum** over all samples: timing noise is additive, so the fastest observed
run is the closest estimate of true throughput.

---

## 7. What was broken in the code, and what changed

### 7.1 False sharing on the per-island state

The frozen engine keeps per-island state in parallel `std::vector`s — `island[]`, `pub_best_len[]`,
`pub_div[]`, `pub_stag[]`, `pub_best_tour[]`. Adjacent elements share cache lines. Two consequences:

- `pub_best_len` is 8 doubles = **exactly one 64-byte cache line**, written by all 8 threads every
  epoch. `pub_stag` is 8 `char`s — also one line.
- Worse, `island[id]` is a `std::vector` **header** (three pointers, 24 bytes), and
  `pop = std::move(next)` inside `step_generation` rewrites it on **every generation**. Three
  islands' headers fit in one cache line, so several threads invalidate the same line thousands of
  times per second.

**Change:** all per-island state moved into a single `alignas(64)` padded `IslandSlot`, so no two
islands share a line.

### 7.2 An allocation on every child, every generation

`step_generation` builds a fresh `Population next` each generation, and `order_crossover` returns a
fresh `std::vector<int>` per child. That is `pop_size` allocations of *n* ints per generation —
tens of thousands of `malloc`/`free` pairs per second per thread, contending on a shared heap
arena.

**Change:** `step_generation_opt` writes into caller-owned double buffers that are recycled across
generations, and `order_crossover_into` writes into a provided child buffer. The RNG call sequence
is untouched.

### 7.3 A sort that looks redundant but is not (a bug we introduced and reverted)

`step_generation` sorts the population on entry *and* on exit. Removing the entry sort looks like
free speed. It is not: `sort_population` orders by tour length only, so individuals of **equal
length** are not totally ordered, and `std::sort` breaks those ties arbitrarily. Elitism and
migration both create exact-duplicate lengths, so sorting once instead of twice yields a different
permutation of the tied individuals, which changes which parents tournament selection picks. The
two engines drifted apart within ~15 generations.

`tests/test_equiv.cpp` caught this. The optimisation was **reverted** and the behaviour documented,
which is why `--engine opt` now reproduces `--engine baseline` bit-for-bit. This is recorded here
rather than quietly dropped because "an optimisation that silently changes your search" is exactly
the failure mode an HPC course should care about.

### 7.4 A missing barrier in the frozen engine

The baseline's comment claims that `#pragma omp single`'s "implicit barrier guarantees migration is
done". It does not: `omp single`'s implicit barrier is at its **exit**, not its entry. So the
bookkeeping block can read `total_migrations` while other threads are still migrating, and the
logged migration counts are not well-defined. This does not corrupt the populations (the exit
barrier still orders migration before the next epoch), but it does make the per-epoch migration log
unreliable. The optimised engine uses `omp for`, whose implicit exit barrier orders the phases
correctly.

### 7.5 Documentation and reproducibility gaps

- `--gen clustered` is implemented and used by the benchmark, but is absent from `--help` and the
  README's usage line. Fixed.
- `data/` was referenced by the README but empty, so the TSPLIB examples could not be run as
  written. TSPLIB instances are now committed.
- The build instructions assumed CMake; `build.ps1` and `Makefile` remove that dependency, and the
  binary is now statically linked so it runs without MSYS2 on `PATH`.
- The Review-1 PDF's reference list and `report/report.md`'s reference list were **disjoint** —
  ten references in one, nine different ones in the other. Reconciled into a single list.

---

## 8. Reproducing every number

```powershell
.\build.ps1                                   # build + correctness gate
python bench\run_study.py                     # E1-E6, ~45 min, machine idle
python bench\analyze_study.py                 # tables + figures
python report\build_report.py                 # report .docx
python report\build_deck.py                   # slide deck .pptx
```

| Experiment | Question it answers |
|---|---|
| **E1** | Strong scaling with islands fixed — the clean speedup/efficiency/Karp–Flatt numbers, for both the frozen and re-engineered engines. |
| **E2** | The original protocol (islands = threads), re-run so the artefact in 6.2 can be quantified. |
| **E3** | Does enabling 2-opt break the equal-work assumption? (correlation between tour quality and wall-clock) |
| **E4** | τ sweep: at what threshold is DTAM actually a *trigger*, and does triggering less help? |
| **E5** | Equal wall-clock quality across landscapes, with and without local search. |
| **E6** | TSPLIB instances with published optima — externally verifiable quality. |

---

## 9. Novelty: what is claimed, and what is not

### 9.1 What is *not* claimed

Diversity-driven and adaptive migration for island GAs is an established research area. This
project does **not** claim to originate it. Prior work covers diversity-based migrant selection,
diversity-conditioned immigration, adaptive migration schemes, dual/dynamic migration policies, and
runtime topology adaptation. Any Review-2 claim of a "new category of migration policy" would be
false, and the Review-1 report's novelty section overstates this relative to the deck, which is
more careful. That inconsistency is corrected in the updated report.

### 9.2 What is claimed

**Claim 1 — a specific policy design.** DTAM's particular *combination* is self-implemented and
not taken from a paper: a stagnation trigger computed from a concrete edge-set diversity metric,
coupled with **distant-source pull** selection chosen at runtime from a published signature space.
Most prior schemes key the decision off the target island's own diversity and/or a fixed topology;
DTAM chooses the *source* at runtime by maximising genetic distance. This is an incremental
engineering contribution, and is presented as exactly that.

**Claim 2 — the evaluation is framed as an HPC problem, and the framing changes the answer.**
This is the stronger claim, and Review 2 is what earns it. The metaheuristics literature on
migration policy reports final tour quality. This project reports speedup, parallel efficiency,
Karp–Flatt serial fraction and Amdahl ceiling alongside quality, on a single fair three-engine
testbed with identical GA operators — and in doing so found that **two of its own Review-1
headline results were measurement artefacts** (sections 6.1 and 6.2), not properties of the
algorithm. A quality-only evaluation would never have surfaced either. That is a concrete
demonstration of why the HPC framing is worth having.

**Claim 3 — a negative result, correctly diagnosed.** Review 1 reported that DTAM and fixed
migration land within ~1% of each other and concluded that migration policy is a second-order
factor. The conclusion was reported honestly but the diagnosis was wrong. At the τ = 0.15 used
throughout, DTAM's stagnation condition fires on essentially **every** island-epoch — the
Review-1 data itself shows 313 migrations out of 320 possible island-epochs, and this machine
reproduces the same ~98% trigger rate. At that rate DTAM is not a *triggered* policy at all; it is
fixed migration with a different source. **The Review-1 experiment never tested the mechanism it
was designed to test.** Experiment E4 sweeps τ and reports the trigger rate explicitly, so the
policy is evaluated in the regime where it actually behaves like a trigger.

### 9.3 Defending it against the obvious challenges

> *"Isn't this just a standard island-model GA?"*
> The island model is the vehicle, not the contribution. The contribution is a migration policy
> plus an HPC-grade evaluation of it. The three engines share one GA core precisely so that any
> measured difference is attributable to parallel structure or migration policy and not to the
> search operators.

> *"You didn't beat the baseline, so what's the result?"*
> A correctly diagnosed negative result is a result. The Review-2 finding is sharper than Review 1's:
> the earlier null result was not evidence that migration policy is unimportant, it was evidence
> that the threshold was never tuned. That distinction is only visible because the trigger rate was
> instrumented — which is the sort of thing an HPC-framed evaluation makes you do.

> *"Your speedup dropped after you 'fixed' the measurement."*
> Correct, and that is the point. A speedup figure that includes a cache effect and a
> data-dependent workload is not a speedup figure. The corrected numbers are smaller and defensible;
> the original ones were larger and not.

> *"Why not GPU / MPI?"*
> See section 10.

---

## 10. Defending the technology choices

**C++17.** The inner loop is pointer-chasing over small permutation vectors with a precomputed
distance matrix — allocation behaviour and memory layout dominate, and both need to be
controllable. Section 7.2 is a concrete instance: the single largest engineering win came from
removing per-child heap allocation, which is not expressible in a managed-memory language. C++17
specifically for over-aligned `new` (used for the cache-line-padded island slots) and structured
bindings/`std::optional` conveniences.

**OpenMP rather than `std::thread`.** The parallel structure here is a fork-join loop over islands
with two barriers and a single-threaded bookkeeping section per epoch — precisely OpenMP's model.
Writing it with `std::thread` would mean hand-rolling a barrier and a thread pool, i.e.
reimplementing OpenMP worse. OpenMP also gives `OMP_PROC_BIND`/`OMP_PLACES` affinity control for
free, which matters on an SMT machine where thread placement changes results, and `omp_get_wtime()`
for consistent timing.

**Shared memory rather than MPI.** Migration exchanges *K* tours per island per epoch — kilobytes.
On shared memory that is a pointer copy behind a barrier. The interesting cost is not
communication but *synchronisation and cache behaviour*, which is what this study measures. MPI
would add serialisation and network latency that would dominate and obscure the effect being
studied. MPI becomes the right choice at a scale beyond one node, and that is where DTAM's reduced
migration frequency would start to pay for itself — which is exactly why it is listed as future
work rather than claimed here.

**CPU rather than GPU.** The GA's inner operations are branch-heavy and irregular: OX crossover
walks a permutation with a membership test, 2-opt does data-dependent segment reversals with early
exit, and tournament selection is random gather. That is a poor fit for SIMT — warp divergence
would dominate. A GPU implementation would be a different project (fine-grained/cellular GA with a
restructured representation), not a port. On the stated target hardware — a 4-core mobile i5 —
CPU-only is also simply what is available.

**mt19937_64, one stream per island.** Independent per-island streams are a hard correctness
requirement for parallel stochastic search: a shared generator would both race and destroy
reproducibility. Keying the stream to the **island** rather than the thread is what makes results
independent of thread count, which is what makes the speedup study controlled.

**Header-only engine.** The whole solver is one translation unit, so the compiler inlines across
the GA core and the island loop, and `-march=native` applies throughout. It also makes the build a
single command with no dependency on CMake.

---

## 11. Known limitations

- Results are for Euclidean TSP with tournament/OX/inversion and bounded 2-opt, on one multicore
  machine. Other problem classes may show a larger migration-policy effect.
- The i5-10210U is a 15 W part with 4 physical cores; results at 6 and 8 threads use SMT, where
  two threads share one core's execution resources, so efficiency past 4 threads is expected to
  fall and should not be read as poor scaling.
- `uniform` and `clustered` instances have no exact optimum; `uniform`'s reference length is the
  Beardwood–Halton–Hammersley asymptotic estimate, so a "gap" against it is approximate and can be
  negative. Quality claims that need an exact reference use the TSPLIB instances in `data/`.
- τ was swept on one instance family; a full τ × landscape interaction study is future work.
