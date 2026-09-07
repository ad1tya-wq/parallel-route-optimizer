#!/usr/bin/env python3
"""
Review-2 performance study for ParallelRoute.

This is a new harness, written after auditing the original `run_bench.py`. It
keeps that script's spirit but fixes three measurement problems that made the
original numbers hard to interpret:

  1. ONE SAMPLE PER CONFIGURATION. The original timed each configuration once.
     On a 15 W laptop part (i5-10210U) that is well inside the thermal noise
     floor. Here every configuration is measured `--repeats` times and we report
     the MINIMUM (the least noise-contaminated estimate of the machine's real
     throughput) alongside the median and the spread.

  2. REPEATS RUN BACK-TO-BACK. Repeating a configuration consecutively bakes any
     thermal drift into that one configuration. Here the whole configuration list
     is run round-robin, so drift is spread evenly across all of them.

  3. NO DRIFT CONTROL AT ALL. A fixed "canary" configuration is timed at the
     start of every round; comparing canary times across rounds quantifies how
     much the CPU slowed down over the session, and that number is reported.

It also adds the experiments the original study was missing: a clean strong-
scaling protocol that holds the island count fixed (see E1), a baseline-vs-
optimised engine comparison, a tau sweep for DTAM, and TSPLIB validation.

Usage:
    python bench/run_study.py                 # full study
    python bench/run_study.py --quick         # fast smoke run
    python bench/run_study.py --only E1 E4    # selected experiments
"""
import argparse
import csv
import itertools
import platform
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
BIN_CANDIDATES = [
    ROOT / "build" / "ParallelRoute.exe",
    ROOT / "build" / "ParallelRoute",
    ROOT / "build" / "Release" / "ParallelRoute.exe",
]


def find_binary() -> str:
    for c in BIN_CANDIDATES:
        if c.exists():
            return str(c)
    sys.exit("ParallelRoute binary not found. Build it first (see README).")


def run_one(binary, args):
    """Run one configuration; return the parsed summary row as a dict."""
    out = RESULTS / "_tmp_row.csv"
    if out.exists():
        out.unlink()
    cmd = [binary] + [str(a) for a in args] + ["--quiet", "--validate", "--out", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"run failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr}")
    with open(out, newline="") as f:
        row = list(csv.DictReader(f))[-1]
    out.unlink()
    return row


def measure(binary, args, repeats, store):
    """Run one configuration `repeats` times; append every sample to `store`."""
    for _ in range(repeats):
        store.append(run_one(binary, args))


def aggregate(samples):
    """Collapse repeated samples of one configuration into a summary dict."""
    times = [float(s["total_time"]) for s in samples]
    lens = [float(s["best_len"]) for s in samples]
    base = dict(samples[0])
    base["reps"] = len(samples)
    base["t_min"] = min(times)
    base["t_med"] = statistics.median(times)
    base["t_max"] = max(times)
    base["t_cv"] = (statistics.pstdev(times) / statistics.mean(times)) if len(times) > 1 else 0.0
    base["len_med"] = statistics.median(lens)
    return base


def write_csv(path, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"  -> {path.relative_to(ROOT)}  ({len(rows)} rows)")


# --------------------------------------------------------------------------
# Experiment definitions. Each returns a list of (label_dict, cli_args) pairs.
# --------------------------------------------------------------------------

def e1_strong_scaling(a):
    """E1 - Strong scaling with the ISLAND COUNT HELD FIXED.

    The original study swept threads with islands == threads, so raising T also
    shrank each island (pop/T). That changes the algorithm and the per-thread
    working set at the same time as the parallelism, which is why it produced an
    apparently super-linear 5.9x on a 4-core machine. Fixing islands = I and
    sweeping only T measures parallel speedup alone; because each island keeps
    its own RNG stream, every T produces an identical search trajectory, so the
    only thing that varies is wall-clock.

    2-opt is OFF here on purpose: 2-opt's cost depends on how good the tour
    already is, so with it enabled two runs doing the same number of fitness
    evaluations do NOT do the same amount of work, and "equal work" speedup
    becomes meaningless. E3 quantifies that effect separately.
    """
    jobs = []
    # Only the optimised engine appears here: the frozen baseline hard-wires
    # islands == threads and ignores --islands, so it cannot participate in a
    # fixed-island protocol. The two engines are compared in E2 instead, where
    # both run the decomposition the baseline is capable of.
    for engine, T in itertools.product(["opt"], a.threads):
        for mode in ("island-fixed", "island-dtam"):
            for seed in range(1, a.seeds + 1):
                jobs.append((
                    dict(exp="E1", engine=engine, mode=mode, threads=T, seed=seed),
                    ["--mode", mode, "--engine", engine, "--gen", "uniform", "--n", a.n,
                     "--generations", a.generations, "--pop", a.pop,
                     "--islands", a.islands, "--threads", T, "--seed", seed,
                     "--epoch-len", a.epoch_len],
                ))
    # Serial reference at the same total work.
    for seed in range(1, a.seeds + 1):
        jobs.append((
            dict(exp="E1", engine="baseline", mode="serial", threads=1, seed=seed),
            ["--mode", "serial", "--gen", "uniform", "--n", a.n,
             "--generations", a.generations, "--pop", a.pop, "--seed", seed],
        ))
    return jobs


def e2_legacy_protocol(a):
    """E2 - The ORIGINAL protocol (islands == threads), reproduced verbatim.

    Kept so the Review-1 numbers can be checked on this machine and compared
    like-for-like against E1's cleaner protocol. The difference between E1 and
    E2 speedup at the same T is the cache/working-set effect that the original
    protocol silently folded into its "speedup".
    """
    jobs = []
    for engine in a.engines:
        for T in a.threads:
            for mode in ("island-fixed", "island-dtam"):
                for seed in range(1, a.seeds + 1):
                    # islands defaults to threads, which is the only decomposition
                    # the frozen baseline supports -- so both engines are doing
                    # identical work here and the comparison is like-for-like.
                    jobs.append((
                        dict(exp="E2", engine=engine, mode=mode, threads=T, seed=seed),
                        ["--mode", mode, "--engine", engine, "--gen", "uniform", "--n", a.n,
                         "--generations", a.generations, "--pop", a.pop,
                         "--threads", T, "--seed", seed, "--epoch-len", a.epoch_len],
                    ))
    for seed in range(1, a.seeds + 1):
        jobs.append((
            dict(exp="E2", engine="baseline", mode="serial", threads=1, seed=seed),
            ["--mode", "serial", "--gen", "uniform", "--n", a.n,
             "--generations", a.generations, "--pop", a.pop, "--seed", seed],
        ))
    return jobs


def e3_twoopt_confound(a):
    """E3 - Does enabling 2-opt break the equal-work assumption?

    Same equal-work protocol as E1 but with 2-opt on. If wall-clock at a fixed
    thread count varies with the tour quality a run happens to reach, then work
    is data-dependent and 2-opt runs cannot be used for speedup measurement.
    """
    jobs = []
    for T in a.threads:
        for mode in ("island-fixed", "island-dtam"):
            for seed in range(1, a.seeds + 1):
                jobs.append((
                    dict(exp="E3", engine="opt", mode=mode, threads=T, seed=seed),
                    ["--mode", mode, "--engine", "opt", "--gen", "uniform", "--n", a.n,
                     "--generations", a.twoopt_generations, "--pop", a.pop,
                     "--islands", a.islands, "--threads", T, "--seed", seed,
                     "--epoch-len", a.epoch_len, "--twoopt", "--twoopt-rate", 0.2],
                ))
    return jobs


def e4_tau_sweep(a):
    """E4 - DTAM's stagnation threshold tau.

    The committed results used tau = 0.15 and reported ~=313 migrations out of
    320 possible island-epochs, i.e. DTAM fired on ~98% of epochs. At that
    trigger rate DTAM is not a diversity-triggered policy at all - it is fixed
    migration with a different source. This sweep records the trigger rate and
    the resulting quality so the policy can be evaluated where it actually
    behaves like a trigger.
    """
    jobs = []
    for tau in a.taus:
        for seed in range(1, a.seeds + 1):
            jobs.append((
                dict(exp="E4", engine="opt", mode="island-dtam", threads=a.threads[-1],
                     seed=seed, tau=tau),
                ["--mode", "island-dtam", "--engine", "opt", "--gen", "uniform", "--n", a.n,
                 "--generations", a.generations, "--pop", a.pop,
                 "--islands", a.islands, "--threads", a.threads[-1], "--seed", seed,
                 "--epoch-len", a.epoch_len, "--tau", tau],
            ))
    # Fixed-migration reference at the same settings.
    for seed in range(1, a.seeds + 1):
        jobs.append((
            dict(exp="E4", engine="opt", mode="island-fixed", threads=a.threads[-1],
                 seed=seed, tau=-1),
            ["--mode", "island-fixed", "--engine", "opt", "--gen", "uniform", "--n", a.n,
             "--generations", a.generations, "--pop", a.pop,
             "--islands", a.islands, "--threads", a.threads[-1], "--seed", seed,
             "--epoch-len", a.epoch_len],
        ))
    return jobs


def e5_equal_wallclock(a):
    """E5 - Solution quality under an equal WALL-CLOCK budget.

    This is the comparison that actually matters to a user: given N seconds,
    which engine returns the better tour? Run on both landscapes, with and
    without local search.
    """
    jobs = []
    settings = [("uniform", a.n, False), ("uniform", a.n, True),
                ("clustered", 600, False), ("clustered", 600, True)]
    for gen_kind, n, twoopt in settings:
        for mode, T in (("serial", 1), ("island-fixed", a.threads[-1]), ("island-dtam", a.threads[-1])):
            for seed in range(1, a.seeds + 1):
                args = ["--mode", mode, "--gen", gen_kind, "--n", n,
                        "--generations", 100000000, "--time", a.budget,
                        "--pop", a.pop, "--seed", seed, "--epoch-len", a.epoch_len]
                if mode != "serial":
                    args += ["--engine", "opt", "--islands", a.islands, "--threads", T]
                if twoopt:
                    args += ["--twoopt", "--twoopt-rate", 0.2]
                jobs.append((
                    dict(exp="E5", engine="opt", mode=mode, threads=T, seed=seed,
                         landscape=f"{gen_kind}{n}", twoopt=int(twoopt)),
                    args,
                ))
    return jobs


def e6_tsplib(a):
    """E6 - Real TSPLIB instances with PUBLISHED optima.

    The original study reported gaps against the Beardwood-Halton-Hammersley
    asymptotic estimate for random points, which is an approximation, not an
    optimum - a "gap" against it can even be negative. These instances have
    exact published optima, so the gaps here are meaningful.
    """
    jobs = []
    files = sorted((ROOT / "data").glob("*.tsp"))
    if not files:
        return jobs
    for f in files:
        for mode, T in (("serial", 1), ("island-fixed", a.threads[-1]), ("island-dtam", a.threads[-1])):
            for seed in range(1, a.seeds + 1):
                args = ["--mode", mode, "--in", str(f), "--generations", 100000000,
                        "--time", a.budget, "--pop", a.pop, "--seed", seed,
                        "--epoch-len", a.epoch_len, "--twoopt", "--twoopt-rate", 0.2]
                if mode != "serial":
                    args += ["--engine", "opt", "--islands", a.islands, "--threads", T]
                jobs.append((
                    dict(exp="E6", engine="opt", mode=mode, threads=T, seed=seed,
                         instance_file=f.stem),
                    args,
                ))
    return jobs


def e7_epoch_len(a):
    """E7 - Synchronisation frequency.

    E1's Karp-Flatt metric rises with thread count (0.02 at p=2 to 0.22 at p=6),
    which says the scaling limit is parallel OVERHEAD rather than a fixed serial
    section. The dominant overhead candidate is the per-epoch synchronisation:
    every epoch costs two implicit barriers plus a single-threaded bookkeeping
    block, and epoch_len sets how much parallel work is amortised against them.

    If that diagnosis is right, wall-clock should fall steeply as epoch_len grows
    and then flatten once the barriers stop mattering. If it is wrong -- if the
    limit were memory bandwidth or SMT contention -- epoch_len would barely
    matter. Total work is identical at every epoch_len, so this is a clean test.
    """
    jobs = []
    for T in a.threads:
        for E in a.epoch_lens:
            for seed in range(1, a.seeds + 1):
                jobs.append((
                    dict(exp="E7", engine="opt", mode="island-fixed", threads=T,
                         seed=seed, epoch_len=E),
                    ["--mode", "island-fixed", "--engine", "opt", "--gen", "uniform",
                     "--n", a.n, "--generations", a.generations, "--pop", a.pop,
                     "--islands", a.islands, "--threads", T, "--seed", seed,
                     "--epoch-len", E],
                ))
    return jobs


EXPERIMENTS = {
    "E1": ("strong scaling, islands fixed (clean speedup)", e1_strong_scaling),
    "E2": ("legacy protocol, islands == threads (original study)", e2_legacy_protocol),
    "E3": ("2-opt equal-work confound", e3_twoopt_confound),
    "E4": ("DTAM tau sweep / trigger rate", e4_tau_sweep),
    "E5": ("equal wall-clock quality", e5_equal_wallclock),
    "E6": ("TSPLIB instances with published optima", e6_tsplib),
    "E7": ("synchronisation frequency (epoch length)", e7_epoch_len),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", default=list(EXPERIMENTS), choices=list(EXPERIMENTS))
    ap.add_argument("--threads", nargs="+", type=int, default=[1, 2, 3, 4, 6, 8])
    ap.add_argument("--engines", nargs="+", default=["baseline", "opt"])
    ap.add_argument("--islands", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--pop", type=int, default=240)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--generations", type=int, default=1200)
    ap.add_argument("--twoopt-generations", type=int, default=200)
    ap.add_argument("--epoch-len", type=int, default=10)
    ap.add_argument("--epoch-lens", nargs="+", type=int,
                    default=[1, 2, 5, 10, 25, 50, 100, 250])
    ap.add_argument("--budget", type=float, default=4.0)
    ap.add_argument("--taus", nargs="+", type=float,
                    default=[0.0, 0.02, 0.05, 0.08, 0.12, 0.15, 0.25, 0.40, 0.60, 0.90])
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()

    if a.quick:
        a.threads = [1, 2, 4]
        a.islands = 4
        a.seeds, a.repeats = 2, 2
        a.generations, a.twoopt_generations = 200, 60
        a.budget = 1.0
        a.taus = [0.0, 0.15, 0.6]
        a.epoch_lens = [1, 10, 100]

    binary = find_binary()
    RESULTS.mkdir(exist_ok=True)

    print(f"binary   : {binary}")
    print(f"platform : {platform.processor() or platform.machine()} | {platform.system()}")
    print(f"protocol : {a.repeats} repeats x {a.seeds} seeds, round-robin, min-of-repeats\n")

    # The canary must be long enough that process start-up is not the dominant
    # term, otherwise the "drift" it reports is just scheduler noise.
    canary = ["--mode", "island-fixed", "--engine", "opt", "--gen", "uniform", "--n", 400,
              "--generations", 800, "--pop", 240, "--islands", 4, "--threads", 4, "--seed", 1]

    for name in a.only:
        desc, builder = EXPERIMENTS[name]
        jobs = builder(a)
        if not jobs:
            print(f"[{name}] {desc}: SKIPPED (no inputs)\n")
            continue
        print(f"[{name}] {desc}: {len(jobs)} configs x {a.repeats} repeats")
        buckets = {i: [] for i in range(len(jobs))}
        canary_times = []
        t_start = time.time()
        for rep in range(a.repeats):
            canary_times.append(float(run_one(binary, canary)["total_time"]))
            for i, (label, args) in enumerate(jobs):
                row = run_one(binary, args)
                row.update(label)
                buckets[i].append(row)
            done = (rep + 1) / a.repeats
            print(f"  round {rep+1}/{a.repeats} done ({time.time()-t_start:.0f}s elapsed, "
                  f"canary={canary_times[-1]:.3f}s)")
        drift = 100.0 * (canary_times[-1] - canary_times[0]) / canary_times[0]
        print(f"  thermal drift over experiment: {drift:+.1f}% "
              f"(canary {canary_times[0]:.3f}s -> {canary_times[-1]:.3f}s)")
        rows = [aggregate(buckets[i]) for i in range(len(jobs))]
        for r in rows:
            r["canary_drift_pct"] = round(drift, 2)
        write_csv(RESULTS / f"study_{name}.csv", rows)
        bad = [r for r in rows if r.get("valid") == "1"]
        print(f"  validation: {len(rows)-len(bad)}/{len(rows)} configs returned valid tours\n")

    print("Done. Next: python bench/analyze_study.py")


if __name__ == "__main__":
    main()
