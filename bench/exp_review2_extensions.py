#!/usr/bin/env python3
"""E9 + E10 - the two Review-2 extensions, measured at equal wall-clock.

E9  candidate-list 2-opt (Bentley 1992: neighbour lists + don't-look bits)
    versus the naive O(n^2) first-improvement 2-opt.

E10 does making the DTAM trigger actually work rescue the policy?
    Factorial over: heterogeneous island parameters, relative stagnation
    trigger, random immigrants. The measured failure mode is that all islands
    collapse together, so DTAM finds a healthy donor only 4.8% of the time and
    falls through to its "most distant overall" branch on 95% of migrations.
"""
import csv, os, subprocess, sys
BIN = os.path.join("build", "ParallelRoute.exe")

def run(extra, tag, budget=3.0, seed=1):
    tmp = "results/_tmp_ext.csv"
    if os.path.exists(tmp): os.remove(tmp)
    a = [BIN, "--engine", "opt", "--generations", "100000000", "--time", str(budget),
         "--pop", "240", "--islands", "8", "--threads", "4", "--epoch-len", "10",
         "--seed", str(seed), "--quiet", "--validate", "--out", tmp] + extra
    subprocess.run(a, check=True, capture_output=True)
    r = list(csv.DictReader(open(tmp)))[-1]; os.remove(tmp)
    r.update(tag)
    return r

rows = []
SEEDS = range(1, 11)

# ---- E9: fast vs naive 2-opt -------------------------------------------------
print("E9: candidate-list 2-opt vs naive 2-opt", flush=True)
for inst_args, land in ((["--gen", "uniform", "--n", "500"], "uniform500"),
                        (["--gen", "clustered", "--n", "600"], "clustered600"),
                        (["--in", "data/a280.tsp"], "a280"),
                        (["--in", "data/kroA200.tsp"], "kroA200")):
    for mode in ("island-fixed", "island-dtam"):
        for variant, flags in (("naive", ["--twoopt", "--twoopt-rate", "0.2"]),
                               ("fast",  ["--twoopt-fast", "--twoopt-rate", "0.2"])):
            for s in SEEDS:
                rows.append(run(["--mode", mode] + inst_args + flags,
                                dict(exp="E9", landscape=land, mode=mode, variant=variant, seed=s), seed=s))
    print(f"  {land} done", flush=True)

# ---- E10: DTAM rescue attempts ----------------------------------------------
print("E10: DTAM mechanism factorial", flush=True)
CONFIGS = [
    ("stock",              []),
    ("heterogeneous",      ["--heterogeneous"]),
    ("rel-trigger",        ["--rel-trigger"]),
    ("het+rel",            ["--heterogeneous", "--rel-trigger"]),
    ("immigrants",         ["--immigrants", "2"]),
    ("het+immigrants",     ["--heterogeneous", "--immigrants", "2"]),
]
for inst_args, land in ((["--gen", "uniform", "--n", "500"], "uniform500"),
                        (["--gen", "clustered", "--n", "600"], "clustered600")):
    for twoopt, tflags in ((0, []), (1, ["--twoopt-fast", "--twoopt-rate", "0.2"])):
        for cname, cflags in CONFIGS:
            for s in SEEDS:
                rows.append(run(["--mode", "island-dtam"] + inst_args + tflags + cflags,
                                dict(exp="E10", landscape=land, twoopt=twoopt, config=cname, seed=s), seed=s))
        # fixed-migration reference at the same settings
        for s in SEEDS:
            rows.append(run(["--mode", "island-fixed"] + inst_args + tflags,
                            dict(exp="E10", landscape=land, twoopt=twoopt, config="FIXED-ref", seed=s), seed=s))
    print(f"  {land} done", flush=True)

keys = sorted({k for r in rows for k in r})
with open("results/study_E9_E10.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print(f"-> results/study_E9_E10.csv ({len(rows)} rows)")
