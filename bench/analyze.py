#!/usr/bin/env python3
"""
Print the summary statistics used in the report, straight from the benchmark CSVs.
Run after bench/run_bench.py. Produces: the speedup/efficiency/quality table
(equal work), the equal-wall-clock convergence finals, and the policy table.

    python bench/analyze.py
"""
import csv
import glob
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def load(path):
    rows = []
    for r in csv.DictReader(open(path)):
        for k in ("threads", "seed"):
            if k in r:
                r[k] = int(r[k])
        for k in ("gap", "total_time", "time_to_target", "best_len"):
            if k in r:
                r[k] = float(r[k])
        rows.append(r)
    return rows


def speedup_table(rows):
    seeds = sorted({r["seed"] for r in rows})
    serial_t = {r["seed"]: r["total_time"] for r in rows if r["mode"] == "serial"}
    serial_gap = st.mean([r["gap"] for r in rows if r["mode"] == "serial"])
    print(f"\n== Equal-work speedup / quality ==  (R={len(seeds)} seeds, "
          f"serial {st.mean(serial_t.values()):.2f}s, gap {serial_gap:.2f}%)")
    print(f"{'T':>3} | {'P1 spd':>7} {'P1 eff':>7} {'P1 gap%':>8} | {'P2 spd':>7} {'P2 eff':>7} {'P2 gap%':>8}")
    for T in sorted({r["threads"] for r in rows if r["mode"] != "serial"}):
        cells = []
        for mode in ("island-fixed", "island-dtam"):
            sp = [serial_t[r["seed"]] / r["total_time"] for r in rows
                  if r["mode"] == mode and r["threads"] == T and r["total_time"] > 0]
            gp = [r["gap"] for r in rows if r["mode"] == mode and r["threads"] == T]
            cells += [st.mean(sp), st.mean(sp) / T, st.mean(gp)]
        print(f"{T:>3} | {cells[0]:>7.2f} {cells[1]:>7.2f} {cells[2]:>8.2f} | "
              f"{cells[3]:>7.2f} {cells[4]:>7.2f} {cells[5]:>8.2f}")


def convergence_finals():
    fin = defaultdict(list)
    for f in glob.glob(str(RESULTS / "convergence" / "*.csv")):
        mode = ("serial" if "_serial_" in f else
                "island-fixed" if "island-fixed" in f else "island-dtam")
        rr = list(csv.DictReader(open(f)))
        if rr:
            fin[mode].append(float(rr[-1]["gap"]))
    if not fin:
        return
    print("\n== Equal-wall-clock convergence: final gap% (mean over seeds) ==")
    for m in ("serial", "island-fixed", "island-dtam"):
        if fin[m]:
            print(f"  {m:14s} {st.mean(fin[m]):6.2f}%   (best {min(fin[m]):.2f}, worst {max(fin[m]):.2f})")


def policy_table():
    path = RESULTS / "policy.csv"
    if not path.exists():
        return
    data = defaultdict(lambda: defaultdict(list))
    for r in load(path):
        key = f"{r['instance']}/{'2opt' if r['twoopt'] == '1' else 'no-2opt'}"
        data[key][r["mode"]].append(r["best_len"])
    print("\n== Policy across landscapes: mean best tour length ==")
    for key, d in data.items():
        s, f, dd = st.mean(d["serial"]), st.mean(d["island-fixed"]), st.mean(d["island-dtam"])
        print(f"  {key:22s} serial={s:9.1f} P1={f:9.1f} P2={dd:9.1f} | "
              f"parallel vs serial {100*(f-s)/s:+6.1f}%   P2 vs P1 {100*(dd-f)/f:+.2f}%")


def main():
    summary = RESULTS / "summary.csv"
    if summary.exists():
        speedup_table(load(summary))
    convergence_finals()
    policy_table()


if __name__ == "__main__":
    main()
