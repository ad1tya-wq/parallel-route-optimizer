#!/usr/bin/env python3
"""
Render figures from the benchmark CSVs into results/figures/:

  speedup_<inst>.png      speedup vs threads (with ideal line + Amdahl-style ceiling)
  efficiency_<inst>.png   parallel efficiency (speedup / threads) vs threads
  quality_<inst>.png      solution gap vs threads at equal work (all modes)
  convergence.png         best gap vs wall-clock time (serial / P1 / P2)
  diversity.png           population diversity vs generation (why DTAM helps)
  ttt.png                 time-to-target-gap by mode

Reads results/summary.csv and results/convergence/*.csv.
Depends only on numpy + matplotlib.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGS = RESULTS / "figures"
COLORS = {"serial": "#e53e3e", "island-fixed": "#3182ce", "island-dtam": "#38a169"}
LABEL = {"serial": "serial", "island-fixed": "P1 island-fixed", "island-dtam": "P2 island-DTAM"}


def load_summary():
    path = RESULTS / "summary.csv"
    if not path.exists():
        sys.exit("results/summary.csv not found. Run: python bench/run_bench.py")
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            for k in ("n", "threads", "island_pop", "total_pop", "generations", "seed", "twoopt", "migrations"):
                r[k] = int(float(r[k]))
            for k in ("best_len", "gap", "total_time", "time_to_target"):
                r[k] = float(r[k])
            rows.append(r)
    return rows


def instances(rows):
    return sorted({r["instance"] for r in rows})


def speedup_efficiency(rows, inst):
    """Return threads sorted, and dict mode -> (speedup[], efficiency[]) meaned over seeds."""
    sub = [r for r in rows if r["instance"] == inst]
    serial_t = defaultdict(list)          # seed -> serial time
    for r in sub:
        if r["mode"] == "serial":
            serial_t[r["seed"]].append(r["total_time"])
    serial_mean = {s: np.mean(v) for s, v in serial_t.items()}

    threads = sorted({r["threads"] for r in sub if r["mode"] != "serial"})
    out = {}
    for mode in ("island-fixed", "island-dtam"):
        sp, ef = [], []
        for T in threads:
            ratios = [serial_mean[r["seed"]] / r["total_time"]
                      for r in sub if r["mode"] == mode and r["threads"] == T
                      and r["seed"] in serial_mean and r["total_time"] > 0]
            sp.append(np.mean(ratios) if ratios else np.nan)
            ef.append((np.mean(ratios) / T) if ratios else np.nan)
        out[mode] = (np.array(sp), np.array(ef))
    return threads, out


def plot_speedup(rows, inst):
    threads, out = speedup_efficiency(rows, inst)
    if not threads:
        return
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.plot(threads, threads, "k--", alpha=0.5, label="ideal (linear)")
    for mode in ("island-fixed", "island-dtam"):
        ax.plot(threads, out[mode][0], "o-", color=COLORS[mode], label=LABEL[mode])
    ax.set_xlabel("threads (islands)")
    ax.set_ylabel("speedup  (t_serial / t_parallel)")
    ax.set_title(f"Speedup vs threads — {inst}")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / f"speedup_{inst}.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.axhline(1.0, color="k", ls="--", alpha=0.5, label="ideal (100%)")
    for mode in ("island-fixed", "island-dtam"):
        ax.plot(threads, out[mode][1], "o-", color=COLORS[mode], label=LABEL[mode])
    ax.set_xlabel("threads (islands)")
    ax.set_ylabel("parallel efficiency  (speedup / threads)")
    ax.set_title(f"Parallel efficiency — {inst}")
    ax.set_ylim(0, 1.2)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / f"efficiency_{inst}.png", dpi=140)
    plt.close(fig)


def plot_quality(rows, inst):
    sub = [r for r in rows if r["instance"] == inst]
    threads = sorted({r["threads"] for r in sub if r["mode"] != "serial"})
    if not threads:
        return
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    serial_gap = np.mean([r["gap"] for r in sub if r["mode"] == "serial"])
    ax.axhline(serial_gap, color=COLORS["serial"], ls="--", label=f"{LABEL['serial']} ({serial_gap:.2f}%)")
    for mode in ("island-fixed", "island-dtam"):
        gaps = [np.mean([r["gap"] for r in sub if r["mode"] == mode and r["threads"] == T]) for T in threads]
        ax.plot(threads, gaps, "o-", color=COLORS[mode], label=LABEL[mode])
    ax.set_xlabel("threads (islands)")
    ax.set_ylabel("gap to optimum (%)  — lower is better")
    ax.set_title(f"Solution quality at equal work — {inst}")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / f"quality_{inst}.png", dpi=140)
    plt.close(fig)


def load_convergence():
    """mode -> list of (elapsed[], gap[], generation[], diversity[]) per seed."""
    d = defaultdict(list)
    cdir = RESULTS / "convergence"
    if not cdir.exists():
        return d
    for path in sorted(cdir.glob("*.csv")):
        mode = None
        for m in ("island-fixed", "island-dtam", "serial"):
            if f"_{m}_" in path.name:
                mode = m
                break
        if mode is None:
            continue
        el, gp, gn, dv = [], [], [], []
        with open(path) as f:
            for r in csv.DictReader(f):
                el.append(float(r["elapsed"])); gp.append(float(r["gap"]))
                gn.append(float(r["generation"])); dv.append(float(r["diversity"]))
        if el:
            d[mode].append((np.array(el), np.array(gp), np.array(gn), np.array(dv)))
    return d


def mean_on_grid(series_list, xidx, yidx, npts=100):
    xmax = min(s[xidx][-1] for s in series_list)
    xmin = max(s[xidx][0] for s in series_list)
    if xmax <= xmin:
        xmax = max(s[xidx][-1] for s in series_list); xmin = 0.0
    grid = np.linspace(xmin, xmax, npts)
    ys = [np.interp(grid, s[xidx], s[yidx]) for s in series_list]
    return grid, np.mean(ys, axis=0)


def plot_convergence(conv):
    if not conv:
        return
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for mode in ("serial", "island-fixed", "island-dtam"):
        if mode not in conv:
            continue
        grid, y = mean_on_grid(conv[mode], 0, 1)
        ax.plot(grid, y, color=COLORS[mode], label=LABEL[mode], lw=2)
    ax.set_xlabel("wall-clock time (s)")
    ax.set_ylabel("best-tour gap to optimum (%)")
    ax.set_title("Solution quality vs time (equal wall-clock budget)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / "convergence.png", dpi=140)
    plt.close(fig)


def plot_diversity(conv):
    if not conv:
        return
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for mode in ("serial", "island-fixed", "island-dtam"):
        if mode not in conv:
            continue
        grid, y = mean_on_grid(conv[mode], 2, 3)
        ax.plot(grid, y, color=COLORS[mode], label=LABEL[mode], lw=2)
    ax.set_xlabel("generation")
    ax.set_ylabel("population diversity (mean edge distance)")
    ax.set_title("Diversity over time — why DTAM resists premature convergence")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / "diversity.png", dpi=140)
    plt.close(fig)


def plot_ttt(rows, inst):
    sub = [r for r in rows if r["instance"] == inst]
    Tmax = max((r["threads"] for r in sub if r["mode"] != "serial"), default=1)
    means, labels, colors = [], [], []
    for mode, T in (("serial", 1), ("island-fixed", Tmax), ("island-dtam", Tmax)):
        vals = [r["time_to_target"] for r in sub
                if r["mode"] == mode and r["threads"] == T and r["time_to_target"] >= 0]
        if vals:
            means.append(np.mean(vals)); labels.append(LABEL[mode] + (f"\n(T={T})" if mode != "serial" else "")); colors.append(COLORS[mode])
    if not means:
        return
    fig, ax = plt.subplots(figsize=(6.0, 4.6))
    ax.bar(labels, means, color=colors)
    ax.set_ylabel("time to reach target gap (s)  — lower is better")
    ax.set_title(f"Time-to-target — {inst}")
    for i, v in enumerate(means):
        ax.text(i, v, f"{v:.2f}s", ha="center", va="bottom")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(FIGS / "ttt.png", dpi=140)
    plt.close(fig)


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    rows = load_summary()
    conv = load_convergence()
    for inst in instances(rows):
        plot_speedup(rows, inst)
        plot_quality(rows, inst)
        plot_ttt(rows, inst)
    plot_convergence(conv)
    plot_diversity(conv)
    print(f"Figures written to {FIGS}")
    for p in sorted(FIGS.glob("*.png")):
        print("  " + p.name)


if __name__ == "__main__":
    main()
