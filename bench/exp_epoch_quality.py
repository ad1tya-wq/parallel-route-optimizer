#!/usr/bin/env python3
"""E8 - epoch length vs SOLUTION QUALITY at an equal wall-clock budget.

E7 showed that raising epoch_len cuts wall-clock sharply for identical work.
But epoch_len is also the migration period, so a longer epoch means rarer
migration. Raising the default is only justified if quality holds up when both
effects act together, which is what an equal-wall-clock budget measures.
"""
import csv, os, subprocess, statistics, sys
BIN = os.path.join("build", "ParallelRoute.exe")
OUT = os.path.join("results", "study_E8.csv")

EPOCHS = [5, 10, 25, 50, 100, 200]
SEEDS = range(1, 9)
BUDGET = 4.0
rows = []
for gen_kind, n, twoopt in (("uniform", 500, False), ("uniform", 500, True),
                            ("clustered", 600, False), ("clustered", 600, True)):
    for mode in ("island-fixed", "island-dtam"):
        for E in EPOCHS:
            for seed in SEEDS:
                tmp = "results/_e8.csv"
                if os.path.exists(tmp): os.remove(tmp)
                a = [BIN, "--mode", mode, "--engine", "opt", "--gen", gen_kind, "--n", str(n),
                     "--generations", "100000000", "--time", str(BUDGET), "--pop", "240",
                     "--islands", "8", "--threads", "4", "--epoch-len", str(E),
                     "--seed", str(seed), "--quiet", "--validate", "--out", tmp]
                if twoopt: a += ["--twoopt", "--twoopt-rate", "0.2"]
                subprocess.run(a, check=True, capture_output=True)
                r = list(csv.DictReader(open(tmp)))[-1]; os.remove(tmp)
                r.update(landscape=f"{gen_kind}{n}", twoopt=int(twoopt), epoch_len=E, mode=mode)
                rows.append(r)
        print(f"  {gen_kind}{n} twoopt={int(twoopt)} {mode} done", flush=True)
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"-> {OUT} ({len(rows)} rows)")

def med(x):
    x = sorted(x); n = len(x)
    return x[n//2] if n % 2 else 0.5*(x[n//2-1]+x[n//2])
print("\nMedian tour length and generations completed in a fixed 4s budget")
for land in ("uniform500", "clustered600"):
    for t in (0, 1):
        print(f"\n{land}  2opt={t}")
        print("  epoch_len " + "".join(f"{E:>12}" for E in EPOCHS))
        for mode in ("island-fixed", "island-dtam"):
            ls = [med([float(r["best_len"]) for r in rows
                       if r["landscape"]==land and r["twoopt"]==t and r["mode"]==mode and r["epoch_len"]==E])
                  for E in EPOCHS]
            gs = [med([float(r["generations"]) for r in rows
                       if r["landscape"]==land and r["twoopt"]==t and r["mode"]==mode and r["epoch_len"]==E])
                  for E in EPOCHS]
            print(f"  {mode:<10}" + "".join(f"{v:>12.1f}" for v in ls))
            print(f"    gens    " + "".join(f"{v:>12.0f}" for v in gs))
