# ParallelRoute

A parallel **island-model genetic algorithm** for the Euclidean Travelling-Salesman Problem
(route optimisation), built as an HPC serial-vs-parallel case study in C++17/OpenMP. It ships
three interchangeable engines so the speedup and solution-quality effects of parallelism, and of
a specific migration policy, can be measured head-to-head on real hardware rather than assumed.

**Course:** High Performance Computing (BCSE414L), Mini-Project, Review 2.
**Measurement platform:** Intel Core i5-10210U (4 physical cores / 8 SMT threads, 1.6 GHz base,
6 MB L3, 15 W), 8 GB RAM, Windows 11, GCC 15.1 (MSYS2 UCRT64), `-O3 -march=native -fopenmp`.

## The three engines

| Mode | What it is | Role |
|---|---|---|
| `serial` | one panmictic population on one core | baseline |
| `island-fixed` | *I* islands of size *P/I*; every island copies its ring neighbour's best-*K* over its own worst-*K*, every `migrate_interval` epochs | naive parallel (**P1**) |
| `island-dtam` | same engine; an island migrates **only when its diversity collapses**, and **pulls** from the most genetically different island | adaptive parallel (**P2**) |

**DTAM** = Diversity-Triggered, distant-source (Adaptive) Migration.

## Honest novelty statement

Diversity-driven and adaptive migration for island GAs is established prior work; this project
does not originate it (see `report/report.md` and `report/REFERENCES.md`). What it contributes:

1. A specific, self-implemented policy: a stagnation trigger paired with distant-source *pull*
   selection chosen at runtime, rather than a fixed ring neighbour on a fixed schedule.
2. An HPC-framed evaluation — speedup, efficiency, Karp-Flatt serial fraction, Amdahl ceiling —
   alongside quality, which is what exposed two Review-1 headline numbers as measurement
   artefacts (see Results below) and located the project's real performance bottleneck.
3. A mechanistically diagnosed negative result rather than a bare "no difference": donor-
   availability instrumentation shows stock DTAM finds a genuinely healthy donor on only
   0.3-0.6% of migrations, which is *why* it does not beat fixed migration, not just *that* it
   doesn't.

**DTAM does not beat fixed migration.** No configuration in this study was found where it
meaningfully does; see Results and `results/FINDINGS.md` section 6.

## Build

### Windows (primary path)

```powershell
.\build.ps1
```

This locates a g++ with OpenMP, compiles with `-O3 -march=native -fopenmp`, links **statically**
(so `build\ParallelRoute.exe` runs on a machine with no MSYS2 on `PATH`), and then runs a
correctness self-test on the `circle` instance, whose optimal tour length is known in closed
form. If that self-test does not report a `0.00%` gap, the build is rejected — this is a build
gate, not just a sanity check.

### Linux / macOS / MSYS2

```bash
make          # build
make test     # differential + correctness tests
```

### CMake (still works, alternative path)

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build --config Release
```

## Usage

```powershell
# Solve a real TSPLIB instance and check against its published optimum
.\build\ParallelRoute.exe --in data\berlin52.tsp --mode island-dtam --engine opt `
    --islands 8 --threads 4 --generations 3000 --twoopt --twoopt-fast --validate

# 500 random cities, fixed migration, render the tour
.\build\ParallelRoute.exe --gen uniform --n 500 --mode island-fixed --engine opt `
    --islands 8 --threads 4 --pop 240 --generations 2000 --twoopt --svg results\route.svg

# Clustered landscape with heterogeneous island parameters
.\build\ParallelRoute.exe --gen clustered --n 600 --mode island-dtam --engine opt `
    --islands 8 --threads 4 --heterogeneous --rel-trigger --immigrants --validate

# Full help
.\build\ParallelRoute.exe --help
```

Key flags:

| Flag | Meaning |
|---|---|
| `--mode serial\|island-fixed\|island-dtam` | which engine |
| `--engine baseline\|opt` | frozen Review-1 island engine, or the re-engineered one |
| `--islands I` | number of islands (decoupled from `--threads`; see Results) |
| `--threads T` | OpenMP threads |
| `--twoopt` / `--twoopt-fast` | bounded 2-opt, or the candidate-list + don't-look-bits fast variant |
| `--tau t` | DTAM stagnation threshold |
| `--rel-trigger` | DTAM trigger relative to the population's own diversity range, not an absolute threshold |
| `--heterogeneous` | vary mutation rate / tournament size across islands |
| `--immigrants` | periodic random-immigrant injection alongside DTAM |
| `--validate` | verify the returned tour is a permutation and its length is correct; non-zero exit if not |
| `--gen uniform\|clustered\|circle --n N` | generated instance (`clustered` exists and is used by the benchmark, but was missing from the old README) |
| `--in file.tsp` | TSPLIB `EUC_2D` instance |

Run `.\build\ParallelRoute.exe --help` for the complete list.

## Reproducing the study

```powershell
python bench\run_study.py               # ~45 min on the i5; writes results\study_E*.csv
python bench\analyze_study.py           # writes results\analysis\*.csv and results\figures\*.png
python bench\exp_epoch_quality.py       # epoch-length speed/quality trade-off (E7/E8)
python bench\exp_review2_extensions.py  # heterogeneous islands, immigrants, relative trigger (E10)
```

**Leave the machine idle while the timing scripts run.** These are wall-clock measurements on a
15 W laptop part; background load shows up directly in the numbers. The harness reports a
thermal-drift figure at the end of each experiment so a run can be judged clean or discarded.

## Results summary

All figures below are from `results/FINDINGS.md`, the single source of truth for every number in
this project; nothing here is estimated or rounded differently.

- **Strong scaling (islands fixed at 8, 2-opt off):** speedup peaks at **3.93x at 8 SMT threads**
  on 4 physical cores, efficiency **0.83 at 4 threads**. Amdahl fit gives serial fraction
  **f = 0.155** (ceiling 6.47x). Karp-Flatt and a load-balance ceiling are used to separate real
  scaling loss from `schedule(static)` integer-division artefacts (p=6 being slower than p=4 is
  real, not noise, and is explained in `results/FINDINGS.md` section 2).
- **Parallel versus serial depends on local search.** Under an equal 4 s budget (12 seeds), the
  island engines find **74.0%** shorter tours on clustered-600 and **68.8%** shorter on uniform-500
  with 2-opt disabled, but only **0.8-2.5%** shorter with it enabled, because the local search does
  most of the optimisation. Review 1's "60-67%" figure is reproducible but holds only in the
  no-local-search configuration.
- **Correctness:** all seven TSPLIB instances tested (berlin52, eil51, st70, kroA100, ch150,
  kroA200, a280) are solved to their published optimum within a 3 s budget, using candidate-list
  2-opt. Before that optimisation, three of them stalled short.
- **Candidate-list 2-opt + don't-look bits:** 7.8-13.2x faster than the naive 2-opt local search,
  and reaches 2.4-3.9% better tours under an equal time budget (Wilcoxon signed-rank, p as low as
  0.0020).
- **Diversity metric:** the bitset edge-set diversity metric is ~6x faster than a hash-set
  reference implementation, bitwise-identical output.
- **Two Review-1 measurement flaws corrected.** Review 1's "equal work" protocol ran with 2-opt
  enabled, whose cost depends on tour quality, so runs were not doing equal work; and its speedup
  numbers conflated real parallelism with a cache effect because island count was tied to thread
  count. Both are fixed here (`--islands` decouples island count from `--threads`; speedup is now
  measured with 2-opt off). Details and the corrected protocol comparison are in
  `results/FINDINGS.md` section 3.
- **DTAM does not beat fixed migration.** Stock DTAM's stagnation trigger fires on essentially
  every island-epoch because diversity collapses within ~100 generations and stays there; as a
  result it finds a genuinely healthy donor on only **0.3-0.6% of migrations**, so its distinguishing
  mechanism is almost never exercised. Across a ten-seed factorial (stock, heterogeneous islands,
  random immigrants, relative trigger, and combinations), no configuration meaningfully beats
  fixed migration; heterogeneous island parameters is the only mechanism that consistently
  improves on *stock* DTAM (about -2.8% to -4.9%) without closing that gap. Full breakdown in
  `results/FINDINGS.md` section 6.

The previous README's "~2.5x on 8 threads", "60-67% shorter tours" and Apple-M3 framing were
Review-1 numbers measured on different hardware under the flawed protocols above; they are
superseded by the figures in this section and in `results/FINDINGS.md`. The Apple-M3 raw results
are preserved unchanged in `results/m3_original/` for reference.

Full write-up with methodology, statistical tests, and figures: **[report/report.md](report/report.md)**.

## Layout

```
src/                 C++17 header-only engine + main.cpp (CLI)
  rng.hpp             per-island mt19937_64, seeded base_seed + island_id
  tsp.hpp             TSPLIB loader, instance generators, published-optimum table
  ga.hpp              GA core: selection, OX crossover, mutation, elitism, bounded 2-opt,
                       edge-set diversity metric, validate_tour()
  island.hpp           frozen Review-1 island engine (audit baseline)
  island_opt.hpp       re-engineered island engine (--engine opt)
  twoopt_fast.hpp       candidate-list 2-opt with don't-look bits
  diversity.hpp         bitset edge-set diversity metric
  timer.hpp / svg.hpp   timing wrapper / tour rendering
tests/                differential tests: optimised engine vs frozen baseline, generation-by-generation
bench/
  run_study.py           Review-2 harness (E1-E6), repeat/round-robin scheduling, thermal canary
  analyze_study.py        speedup, efficiency, Karp-Flatt, Amdahl fit, tau analysis, figures
  exp_epoch_quality.py    epoch-length speed/quality trade-off (E7, E8)
  exp_review2_extensions.py  heterogeneous islands, immigrants, relative trigger (E10)
  run_bench.py / plot_results.py / analyze.py   original Review-1 harness, kept for re-running
data/                TSPLIB EUC_2D instances with published optima
results/
  study_E*.csv          raw Review-2 measurements from this machine
  analysis/              derived tables quoted in the report
  figures/                PNG/SVG figures
  m3_original/            Review-1 result set from the Apple M3, preserved unchanged
  FINDINGS.md             single source of truth for every number in this project
report/               report.md, slide deck build scripts, REFERENCES.md, research/ literature notes
```

See `PROJECT-GUIDE.md` for full component descriptions, CLI reference, and the methodology
write-up behind the numbers above.
