# ParallelRoute

A parallel **island-model genetic algorithm** for the Euclidean Travelling-Salesman
Problem (route optimization), built as an **HPC serial-vs-parallel case study** in
C++/OpenMP. It ships three interchangeable engines so the speedup and solution-quality
gains of parallelism can be measured head-to-head:

| Mode | What it is | Role |
|------|------------|------|
| `serial` | one panmictic population on one core | baseline |
| `island-fixed` | T islands (one per thread), **fixed** periodic ring migration | naive parallel (**P1**) |
| `island-dtam` | T islands with **DTAM** migration (our contribution) | smart parallel (**P2**) |

**DTAM — Diversity-Triggered, Distant-source Migration.** An island migrates *only
when it has stagnated* (its mean edge-diversity falls below a threshold), and it then
**pulls** migrants from the **most genetically different healthy island** — rather than
pushing to a fixed neighbour on a fixed schedule as the textbook island model does.

### Honest novelty statement
Diversity-driven / adaptive migration for island GAs is an established research area
(see the report's related-work section). This project does **not** claim a new
primitive. Its contributions are (1) a specific, self-implemented policy that *couples*
a stagnation trigger with **distant-source pull selection**, and (2) evaluating it as a
**shared-memory HPC problem** — reporting parallel speedup / efficiency / Amdahl and
time-to-target, where the metaheuristics literature reports mainly final quality.

---

## Build

Requires a C++17 compiler with OpenMP and CMake ≥ 3.16.

**Windows (target platform, MSVC):**
```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```
`ParallelRoute.exe` lands in `build\Release\`. (MinGW-w64 `g++ -fopenmp` also works.)

**macOS (Apple clang needs Homebrew libomp):**
```
brew install cmake libomp
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

**Linux (GCC/Clang):** same two CMake commands.

---

## Usage

```
# Generate a 500-city instance, optimize with DTAM on 6 threads, render the route
./build/ParallelRoute --mode island-dtam --gen uniform --n 500 --threads 6 \
    --pop 240 --generations 2000 --twoopt --svg results/route.svg

# Validate correctness on a circle (its optimal length is known in closed form)
./build/ParallelRoute --mode serial --gen circle --n 50 --generations 400 --twoopt

# Load a real TSPLIB instance (auto-reports gap to the published optimum)
./build/ParallelRoute --mode island-dtam --in data/berlin52.tsp --threads 4
```

Run `./build/ParallelRoute --help` for the full flag list. Key knobs: `--pop` (total
population, split across islands), `--generations` / `--time` (budget), `--epoch-len`,
`--migrate-interval`, `--migrants`, `--tau` (DTAM threshold), `--target-gap` (record
time-to-target), `--csv-log`, `--out`.

### Instances
- **Generated (no download):** `--gen circle` (exact known optimum → correctness) and
  `--gen uniform` (random; reference via the Beardwood–Halton–Hammersley estimate).
- **TSPLIB:** drop `EUC_2D` files (e.g. `berlin52`, `kroA100`, `pr1002`) into `data/`.
  Get them from the official TSPLIB: <http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/>.

---

## Reproduce the performance study

```
python bench/run_bench.py     # sweeps modes × threads × instances × seeds -> results/*.csv
python bench/plot_results.py  # renders speedup / efficiency / convergence / TTT figures
```
Set thread affinity for stable timings: `OMP_PROC_BIND=close OMP_PLACES=cores`.

---

## Results (summary)

Full write-up with methodology, figures, and references: **[report/report.md](report/report.md)**.
Headline findings (development machine: Apple M3, 8 cores; regenerate on your own hardware):

- **Parallel vs serial (the main comparison).** At an equal wall-clock budget the island engines
  reach much better tours than the serial GA — ≈6.0% vs ≈9.9% gap on uniform-500 with 2-opt, and
  **60–67% shorter tours** on instances without local search (serial completes far fewer
  generations). Raw speedup at equal work peaks at **≈2.5× on 8 threads** (efficiency ≈0.90 at 2
  threads, tailing off as the M3's efficiency-cores engage past 4 threads).
- **DTAM vs fixed migration.** Across every landscape and local-search setting tested, DTAM and
  fixed migration land **within ~1% of each other** — neither is consistently better. With strong
  2-opt local search and the diversity the island structure already provides, the migration
  *policy* is a second-order factor for Euclidean TSP. We report this as measured rather than
  claiming an improvement the data does not support; DTAM's practical upside is that it is
  self-tuning (no migration schedule to hand-pick).

Example optimized route (clustered-300, DTAM):

![Optimized route](results/figures/route_clustered300.svg)

## Layout
```
src/         C++17 header-only engine + main.cpp (CLI)
bench/       benchmark harness + plotting (Python)
data/        TSPLIB instances (user-provided)
results/     CSV logs + figures
report/      paper-style performance report
```

Course project: an HPC application demonstrating parallel speedup and a small
methodological novelty. Target hardware: Intel i5 10th-gen (4–6 cores), CPU-only.
