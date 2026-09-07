# Original results (Apple M3) — preserved for comparison

Everything in this directory is the **Review-1 result set**, produced on an
Apple M3 (4 performance + 4 efficiency cores) by the original `bench/run_bench.py`.
It is kept unchanged so the Review-2 numbers can be compared against it rather
than silently replacing it.

Two cautions when reading these files, both established in the Review-2 audit:

1. `summary.csv` was produced with 2-opt enabled. 2-opt's cost depends on how
   good the tour already is, so runs performing the same number of fitness
   evaluations do **not** perform the same amount of work. The "equal-work"
   speedup computed from this file is therefore confounded.

2. Both `summary.csv` and `policy.csv` use the protocol `islands == threads`, so
   raising the thread count also shrinks each island (`pop/T`) and shrinks the
   per-thread working set. The reported speedup mixes parallel speedup with a
   cache effect.

The Review-2 results live in `results/study_E*.csv` and `results/analysis/`.
