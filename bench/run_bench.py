#!/usr/bin/env python3
"""
Benchmark harness for ParallelRoute.

Runs three families of experiments and writes CSVs into results/:

  1. speedup   -> results/summary.csv
       Equal-work runs (same total population x generations) for the serial
       baseline and both island modes across a thread sweep, over several seeds.
       Speedup(T) = time_serial / time_island(T); efficiency = speedup / T.

  2. quality   -> results/convergence/<inst>_<mode>_<seed>.csv
       Equal-wall-clock-budget runs; per-row convergence logs (best gap and
       diversity vs elapsed time) for serial / P1 / P2.

  3. (time-to-target is captured in summary.csv via --target-gap.)

Usage:
    python bench/run_bench.py                 # sensible defaults
    python bench/run_bench.py --seeds 10      # more repetitions (recommended for a report)
    python bench/run_bench.py --quick         # tiny/fast smoke run
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def find_binary() -> str:
    candidates = [
        ROOT / "build" / "ParallelRoute",
        ROOT / "build" / "Release" / "ParallelRoute.exe",
        ROOT / "build" / "ParallelRoute.exe",
        ROOT / "build" / "Debug" / "ParallelRoute.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    sys.exit("ParallelRoute binary not found. Build first:\n"
             "  cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build")


def inst_args(spec: str):
    """spec: 'uniform:500' | 'circle:100' | 'file:data/berlin52.tsp'"""
    kind, val = spec.split(":", 1)
    if kind == "uniform":
        return ["--gen", "uniform", "--n", val]
    if kind == "circle":
        return ["--gen", "circle", "--n", val]
    if kind == "file":
        return ["--in", val]
    sys.exit(f"unknown instance spec: {spec}")


def run(binary, args, env_note=""):
    cmd = [binary] + [str(a) for a in args]
    print("  " + " ".join(cmd[1:]))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", nargs="+", default=["uniform:500"],
                    help="instances for the speedup sweep")
    ap.add_argument("--conv-instance", default="uniform:500",
                    help="instance for the convergence / quality-vs-time study")
    ap.add_argument("--threads", nargs="+", type=int, default=[1, 2, 4, 6, 8])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--pop", type=int, default=240)
    ap.add_argument("--generations", type=int, default=400)
    ap.add_argument("--epoch-len", type=int, default=10)
    ap.add_argument("--time-budget", type=float, default=3.0,
                    help="wall-clock budget (s) for the convergence study")
    ap.add_argument("--target-gap", type=float, default=5.0,
                    help="%% gap for time-to-target")
    ap.add_argument("--twoopt", action="store_true", default=True)
    ap.add_argument("--no-twoopt", dest="twoopt", action="store_false")
    ap.add_argument("--twoopt-rate", type=float, default=0.2)
    ap.add_argument("--quick", action="store_true",
                    help="tiny fast run for smoke-testing the pipeline")
    args = ap.parse_args()

    if args.quick:
        args.instances = ["uniform:300"]
        args.conv_instance = "uniform:300"
        args.threads = [1, 2, 4]
        args.seeds = 2
        args.generations = 150
        args.time_budget = 1.5

    binary = find_binary()
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "convergence").mkdir(exist_ok=True)
    summary = RESULTS / "summary.csv"
    if summary.exists():
        summary.unlink()  # fresh sweep

    seeds = list(range(1, args.seeds + 1))
    common = ["--pop", args.pop, "--target-gap", args.target_gap,
              "--epoch-len", args.epoch_len, "--quiet"]
    if args.twoopt:
        common += ["--twoopt", "--twoopt-rate", args.twoopt_rate]

    # ---- 1. speedup sweep (equal work) --------------------------------------
    print("\n=== speedup sweep (equal work: pop x generations fixed) ===")
    for inst in args.instances:
        ia = inst_args(inst)
        for seed in seeds:
            run(binary, ["--mode", "serial", *ia, "--generations", args.generations,
                         "--seed", seed, *common, "--out", summary])
            for T in args.threads:
                for mode in ("island-fixed", "island-dtam"):
                    run(binary, ["--mode", mode, *ia, "--generations", args.generations,
                                 "--threads", T, "--seed", seed, *common, "--out", summary])

    # ---- 2. convergence / quality-vs-time (equal wall-clock) ----------------
    print("\n=== convergence study (equal wall-clock budget) ===")
    Tmax = max(args.threads)
    ia = inst_args(args.conv_instance)
    tag = args.conv_instance.replace(":", "")
    for seed in seeds:
        for mode, T in (("serial", 1), ("island-fixed", Tmax), ("island-dtam", Tmax)):
            log = RESULTS / "convergence" / f"{tag}_{mode}_{seed}.csv"
            run(binary, ["--mode", mode, *ia, "--generations", 10_000_000,
                         "--time", args.time_budget, "--threads", T, "--seed", seed,
                         *common, "--log-interval", 5, "--csv-log", log])

    print(f"\nDone. Summary -> {summary}")
    print(f"Convergence logs -> {RESULTS / 'convergence'}")
    print("Next: python bench/plot_results.py")


if __name__ == "__main__":
    main()
