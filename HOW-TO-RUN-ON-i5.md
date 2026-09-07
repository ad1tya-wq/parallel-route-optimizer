# Running ParallelRoute on the i5 (Windows) — step-by-step

This guide reproduces **all** results (speedup, efficiency, quality, convergence, diversity,
policy) and the route SVGs on your Intel i5 10th-gen Windows machine, and refreshes the report's
numbers with your hardware's figures. Follow it top to bottom the first time.

> Why re-run on the i5? The committed numbers were produced on an Apple M3 (4 performance + 4
> efficiency cores). Your i5 has homogeneous cores, so the speedup/efficiency curves will look
> different (and cleaner). For the submission, the numbers should come from the machine you present.

---

## 1. Install the tools (once)

You need a C++17 compiler with **OpenMP**, **CMake**, **Python 3**, and **Git**.

**Recommended — MSVC (Microsoft's compiler):**
1. Install **Build Tools for Visual Studio** (free): <https://visualstudio.microsoft.com/downloads/>
   → under "Tools for Visual Studio" pick *Build Tools for Visual Studio*.
2. In the installer, check the **"Desktop development with C++"** workload. This gives you MSVC
   (`cl.exe`, which supports `/openmp`) **and** a bundled CMake.
3. Install **Python 3** from <https://python.org> (tick "Add python.exe to PATH").
4. Install **Git** from <https://git-scm.com>.

**Alternative — MinGW-w64 (GNU g++):** install [MSYS2](https://www.msys2.org), then
`pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake`. Use the "MINGW64" shell.

**Verify** (open the *"x64 Native Tools Command Prompt for VS"* for MSVC):
```bat
cl            :: should print the MSVC version (MSVC path)
cmake --version
python --version
git --version
```

---

## 2. Get the code
```bat
git clone https://github.com/Navaneeth-H-K/parallel-route-optimizer.git
cd parallel-route-optimizer
```

---

## 3. Build (Release)

**MSVC** — from the *x64 Native Tools Command Prompt for VS*:
```bat
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```
→ executable at `build\Release\ParallelRoute.exe`.

**MinGW-w64** — from the MINGW64 shell:
```bash
cmake -S . -B build -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build build
```
→ executable at `build\ParallelRoute.exe`.

*(In the commands below, replace `ParallelRoute.exe` with the correct path for your build.)*

---

## 4. Correctness check (do this first)

The `circle` instance has a mathematically known optimal tour, so a correct build reaches ~0% gap:
```bat
build\Release\ParallelRoute.exe --mode serial --gen circle --n 50 --generations 400 --twoopt
```
Expect `gap=0.00%` (or a hair below due to rounding). Then confirm threads/OpenMP work:
```bat
build\Release\ParallelRoute.exe --mode island-dtam --gen uniform --n 300 --threads 6 --pop 240 --generations 500
```
The summary should print `threads : 6`. If it prints 1, OpenMP isn't active (see §8).

---

## 5. Know your core count and pin threads

i5 10th-gen models vary — e.g. **i5-10400** = 6 cores / 12 threads; **i5-10210U** = 4 cores / 8
threads. Check:
```bat
echo %NUMBER_OF_PROCESSORS%      :: logical processors (threads)
wmic cpu get NumberOfCores,NumberOfLogicalProcessors
```
Pin threads for stable timings (Command Prompt):
```bat
set OMP_PROC_BIND=close
set OMP_PLACES=cores
```
PowerShell equivalent: `$env:OMP_PROC_BIND="close"; $env:OMP_PLACES="cores"`.

---

## 6. Python environment for plots
```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r bench\requirements.txt
```

---

## 7. Run the full study

**Set the thread sweep to match your CPU.** For a 6-core / 12-thread i5 use `1 2 4 6` (physical)
and optionally add `8 12` to show hyper-threading falloff; for a 4-core / 8-thread i5 use `1 2 4`
(+ `8`):
```bat
python bench\run_bench.py --seeds 8 --threads 1 2 4 6
.venv\Scripts\python bench\plot_results.py
.venv\Scripts\python bench\analyze.py       :: prints the numbers for the report
```
This writes `results\summary.csv`, `results\policy.csv`, `results\convergence\*.csv`, and figures
in `results\figures\`. Runtime is a few minutes. Use `--quick` first for a fast smoke test.

---

## 8. Generate a product route (for the demo)
```bat
build\Release\ParallelRoute.exe --mode island-dtam --gen clustered --n 300 --threads 6 ^
    --pop 240 --generations 4000 --twoopt --svg results\figures\route.svg
```
Open the `.svg` in any browser to show the optimized route.

---

## 9. Refresh the report with YOUR numbers

The figures in `report\report.md` and `report\PLOTS-AND-STATISTICS.md` point at `results\figures\`,
so they update automatically once you re-run §7. Update the **text** numbers to match
`bench\analyze.py` output:
- `report\report.md` §4 — change the platform note to your i5 model + core/thread count.
- §5.2 speedup/efficiency table, §5.3 convergence gaps, §5.4 policy table.
- `report\PLOTS-AND-STATISTICS.md` — the per-plot numbers in the captions.

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `threads : 1` even with `--threads 6` | Build wasn't OpenMP-enabled. MSVC: build from the *x64 Native Tools* prompt. MinGW: ensure `g++` supports `-fopenmp`. Re-run CMake from a clean `build\`. |
| CMake can't find OpenMP | MSVC ships it; MinGW needs a full gcc. Delete `build\` and reconfigure. |
| `-march=native` error | Harmless — CMake auto-detects and skips it if unsupported. |
| Speedup flattens past physical cores | Expected: hyper-threads add little. Report **efficiency** and discuss Amdahl's law. |
| Very large `--n` slow / high memory | The distance matrix is O(n²) (n≈2000 ≈ 32 MB). Keep n ≤ ~3000. |
| `python` not found | Use `py` instead of `python`, or re-install Python with "Add to PATH". |

---

## Command cheat-sheet
```bat
:: single run, human-readable summary
build\Release\ParallelRoute.exe --mode island-dtam --gen uniform --n 500 --threads 6 --pop 240 --generations 2000 --twoopt

:: help / all flags
build\Release\ParallelRoute.exe --help

:: full study + figures + numbers
python bench\run_bench.py --seeds 8 --threads 1 2 4 6
.venv\Scripts\python bench\plot_results.py
.venv\Scripts\python bench\analyze.py
```
