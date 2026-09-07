#!/usr/bin/env python3
"""
Analysis for the Review-2 study. Reads results/study_E*.csv and writes
results/analysis/*.csv plus results/figures/*.png, and prints the tables that
go into the report.

Metrics computed here:

  Speedup      S(p) = T(1) / T(p)
  Efficiency   E(p) = S(p) / p
  Karp-Flatt   e(p) = (1/S - 1/p) / (1 - 1/p)
               The experimentally determined serial fraction. Its value matters
               less than its TREND: if e is roughly constant as p grows, the
               limit really is a serial section (Amdahl); if e rises with p, the
               limit is parallel overhead - synchronisation, false sharing,
               memory bandwidth - which is a fixable engineering problem rather
               than a law of nature. This distinction is the whole reason the
               optimised engine exists, and the original study never computed it.
  Amdahl fit   least-squares fit of S(p) = 1 / (f + (1-f)/p) for the serial
               fraction f, reported with the speedup ceiling 1/f it implies.

Statistics: DTAM vs fixed migration is compared with a paired Wilcoxon signed-
rank test over seeds (paired because both policies see the same seed, and
non-parametric because tour lengths are not normally distributed).
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
ANALYSIS = RESULTS / "analysis"
FIGURES = RESULTS / "figures"

try:
    from scipy.stats import wilcoxon
    HAVE_SCIPY = True
except ImportError:
    HAVE_SCIPY = False

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9,
    "axes.grid": True, "grid.alpha": 0.25, "axes.spines.top": False,
    "axes.spines.right": False, "figure.autolayout": True,
})
C_FIXED, C_DTAM, C_SERIAL, C_IDEAL = "#2563eb", "#dc2626", "#6b7280", "#9ca3af"


def load(name):
    p = RESULTS / f"study_{name}.csv"
    if not p.exists():
        return []
    with open(p, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("t_min", "t_med", "t_max", "t_cv", "best_len", "len_med", "gap", "tau",
                  "total_time", "canary_drift_pct"):
            if k in r and r[k] not in ("", None):
                try:
                    r[k] = float(r[k])
                except ValueError:
                    pass
        for k in ("threads", "islands", "seed", "migrations", "stag_epochs",
                  "island_epochs", "generations", "n", "valid", "island_pop"):
            if k in r and r[k] not in ("", None):
                try:
                    r[k] = int(float(r[k]))
                except ValueError:
                    pass
    return rows


def write_table(name, rows, keys=None):
    if not rows:
        return
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    keys = keys or list(rows[0].keys())
    with open(ANALYSIS / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  -> results/analysis/{name}")


def karp_flatt(speedup, p):
    if p <= 1 or speedup <= 0:
        return float("nan")
    return (1.0 / speedup - 1.0 / p) / (1.0 - 1.0 / p)


def amdahl_fit(ps, speedups):
    """Least-squares f for S(p) = 1/(f + (1-f)/p), scanned on a fine grid."""
    ps, speedups = np.asarray(ps, float), np.asarray(speedups, float)
    best_f, best_err = 0.0, float("inf")
    for f in np.linspace(0.0, 0.999, 20000):
        pred = 1.0 / (f + (1.0 - f) / ps)
        err = float(np.sum((pred - speedups) ** 2))
        if err < best_err:
            best_err, best_f = err, f
    return best_f


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


# ---------------------------------------------------------------------------
def scaling_table(rows, exp_label):
    """Per (engine, mode, threads): min time over seeds+repeats -> speedup."""
    by = defaultdict(list)
    for r in rows:
        by[(r["engine"], r["mode"], r["threads"])].append(r)

    # With 2-opt off, every seed at a given (engine, mode, threads) performs an
    # IDENTICAL number of operations - only the tours differ. So all seed x
    # repeat samples are repeated measurements of the same workload, and the
    # right estimator is the minimum over all of them: timing noise on a
    # thermally-throttled laptop is strictly additive (interrupts, migrations,
    # frequency dips), so the fastest observed run is the closest estimate of
    # the machine's true throughput. Medians would fold in that additive noise.
    perf = {}
    for k, rs in by.items():
        perf[k] = min(float(r["t_min"]) for r in rs)

    islands_by = {}
    for r in rows:
        islands_by[(r["engine"], r["mode"], r["threads"])] = r.get("islands") or r["threads"]

    out = []
    for (engine, mode) in sorted({(e, m) for (e, m, _) in perf}):
        if mode == "serial":
            continue
        islands = islands_by.get((engine, mode, 1), 0)
        ts = sorted(t for (e, m, t) in perf if e == engine and m == mode)
        if 1 not in ts:
            continue
        t1 = perf[(engine, mode, 1)]
        for p in ts:
            tp = perf[(engine, mode, p)]
            s = t1 / tp
            # Load-balance ceiling. Islands are distributed with schedule(static),
            # so an epoch costs ceil(I/p) island-units regardless of how many
            # threads are idle. With I=8, p=3 and p=6 can therefore never beat
            # 8/3 and 8/2 respectively -- measuring them against a linear ideal
            # would report "poor scaling" for what is really integer division.
            lb = (islands / math.ceil(islands / p)) if islands else float(p)
            out.append(dict(exp=exp_label, engine=engine, mode=mode, threads=p,
                            islands=islands, time_s=round(tp, 4), speedup=round(s, 4),
                            efficiency=round(s / p, 4),
                            lb_ceiling=round(lb, 3),
                            eff_vs_lb=round(s / lb, 4),
                            karp_flatt=round(karp_flatt(s, p), 4) if p > 1 else ""))
        ss = [t1 / perf[(engine, mode, p)] for p in ts]
        f = amdahl_fit(ts, ss)
        for o in out:
            if o["engine"] == engine and o["mode"] == mode:
                o["amdahl_f"] = round(f, 4)
                o["amdahl_ceiling"] = round(1.0 / f, 2) if f > 1e-6 else float("inf")
    return out, perf


def fig_scaling(e1, perf1, perf2):
    ts = sorted({r["threads"] for r in e1})
    fig, ax = plt.subplots(1, 2, figsize=(9.2, 3.6))

    ax[0].plot(ts, ts, "--", color=C_IDEAL, lw=1.2, label="ideal (linear)")
    for engine, ls in (("baseline", ":"), ("opt", "-")):
        for mode, col in (("island-fixed", C_FIXED), ("island-dtam", C_DTAM)):
            pts = [(r["threads"], r["speedup"]) for r in e1
                   if r["engine"] == engine and r["mode"] == mode]
            if pts:
                pts.sort()
                ax[0].plot([p for p, _ in pts], [s for _, s in pts], ls, color=col, marker="o",
                           ms=3.5, lw=1.5, label=f"{engine} {mode.replace('island-','')}")
    ax[0].axvline(4, color="k", lw=0.8, alpha=0.35)
    ax[0].text(4.06, 0.55, "4 physical cores\n(8 threads = SMT)", fontsize=6.6, alpha=0.75)
    ax[0].set_xlabel("threads"); ax[0].set_ylabel("speedup  S(p) = T(1)/T(p)")
    ax[0].set_title("Strong scaling, islands fixed at 8 (E1)", fontsize=9.5)
    ax[0].legend(fontsize=6.4, loc="upper left")

    for engine, ls in (("baseline", ":"), ("opt", "-")):
        for mode, col in (("island-fixed", C_FIXED), ("island-dtam", C_DTAM)):
            pts = [(r["threads"], r["efficiency"]) for r in e1
                   if r["engine"] == engine and r["mode"] == mode]
            if pts:
                pts.sort()
                ax[1].plot([p for p, _ in pts], [s for _, s in pts], ls, color=col, marker="o",
                           ms=3.5, lw=1.5, label=f"{engine} {mode.replace('island-','')}")
    ax[1].axhline(1.0, color=C_IDEAL, ls="--", lw=1.2)
    ax[1].axvline(4, color="k", lw=0.8, alpha=0.35)
    ax[1].set_ylim(0, 1.15)
    ax[1].set_xlabel("threads"); ax[1].set_ylabel("parallel efficiency  S(p)/p")
    ax[1].set_title("Parallel efficiency (E1)", fontsize=9.5)
    ax[1].legend(fontsize=6.4, loc="lower left")

    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "i5_scaling.png"); plt.close(fig)
    print("  -> results/figures/i5_scaling.png")


def fig_protocol(e1rows, e2rows, perf1, perf2):
    """E1 (islands fixed) vs E2 (islands == threads): the protocol artefact."""
    ts = sorted({r["threads"] for r in e1rows if r["engine"] == "baseline"})
    s1 = {r["threads"]: r["speedup"] for r in e1rows
          if r["engine"] == "baseline" and r["mode"] == "island-fixed"}
    # E2's speedup is conventionally quoted against the SERIAL engine, which is
    # how the original study reported it.
    ser = median([v for (e, m, t), v in perf2.items() if m == "serial"] or [float("nan")])
    s2 = {}
    for t in ts:
        k = ("baseline", "island-fixed", t)
        if k in perf2:
            s2[t] = ser / perf2[k]
    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    ax.plot(ts, ts, "--", color=C_IDEAL, lw=1.2, label="ideal (linear)")
    if s2:
        ax.plot(sorted(s2), [s2[t] for t in sorted(s2)], "-o", color="#b45309", ms=4,
                label="E2: islands = threads (original protocol)")
    if s1:
        ax.plot(sorted(s1), [s1[t] for t in sorted(s1)], "-o", color=C_FIXED, ms=4,
                label="E1: islands fixed at 8 (isolated)")
    ax.axvline(4, color="k", lw=0.8, alpha=0.35)
    ax.text(4.06, 0.4, "4 physical cores", fontsize=6.8, alpha=0.75)
    ax.set_xlabel("threads"); ax.set_ylabel("reported speedup")
    ax.set_title("The measurement protocol changes the answer", fontsize=9.5)
    ax.legend(fontsize=6.8, loc="upper left")
    fig.savefig(FIGURES / "i5_protocol_effect.png"); plt.close(fig)
    print("  -> results/figures/i5_protocol_effect.png")


def analyse_engines(e1):
    """baseline vs opt at each thread count: what did the rewrite buy?"""
    out = []
    for mode in ("island-fixed", "island-dtam"):
        for t in sorted({r["threads"] for r in e1}):
            b = [r for r in e1 if r["engine"] == "baseline" and r["mode"] == mode and r["threads"] == t]
            o = [r for r in e1 if r["engine"] == "opt" and r["mode"] == mode and r["threads"] == t]
            if b and o:
                out.append(dict(mode=mode, threads=t,
                                baseline_s=b[0]["time_s"], opt_s=o[0]["time_s"],
                                speedup_from_rewrite=round(b[0]["time_s"] / o[0]["time_s"], 4),
                                baseline_eff=b[0]["efficiency"], opt_eff=o[0]["efficiency"]))
    return out


def analyse_tau(e4):
    by = defaultdict(list)
    for r in e4:
        key = r["tau"] if r["mode"] == "island-dtam" else "fixed"
        by[key].append(r)
    out = []
    for k, rs in sorted(by.items(), key=lambda kv: (kv[0] == "fixed", kv[0])):
        trig = [100.0 * r["stag_epochs"] / r["island_epochs"] for r in rs if r["island_epochs"]]
        out.append(dict(
            tau=k,
            trigger_rate_pct=round(median(trig), 2) if trig else "",
            migrations=round(median([r["migrations"] for r in rs]), 1),
            best_len_med=round(median([r["len_med"] for r in rs]), 1),
            time_s=round(median([r["t_min"] for r in rs]), 4),
            seeds=len({r["seed"] for r in rs})))
    return out


def fig_tau(tau_rows):
    d = [r for r in tau_rows if r["tau"] != "fixed"]
    if not d:
        return
    fixed = [r for r in tau_rows if r["tau"] == "fixed"]
    taus = [r["tau"] for r in d]
    fig, ax1 = plt.subplots(figsize=(5.4, 3.6))
    ax1.plot(taus, [r["trigger_rate_pct"] for r in d], "-o", color=C_DTAM, ms=4,
             label="DTAM trigger rate")
    ax1.set_xlabel(r"stagnation threshold  $\tau$")
    ax1.set_ylabel("island-epochs that triggered (%)", color=C_DTAM)
    ax1.tick_params(axis="y", labelcolor=C_DTAM)
    ax1.axvline(0.15, color="k", ls="--", lw=1.0, alpha=0.6)
    ax1.text(0.155, 50, r"$\tau=0.15$ used in Review 1" + "\n(fires on nearly every epoch)",
             fontsize=6.6, alpha=0.8)
    ax2 = ax1.twinx()
    ax2.plot(taus, [r["best_len_med"] for r in d], "-s", color=C_FIXED, ms=4,
             label="median tour length")
    if fixed:
        ax2.axhline(fixed[0]["best_len_med"], color=C_SERIAL, ls=":", lw=1.4)
        ax2.text(taus[0], fixed[0]["best_len_med"], " fixed-migration reference",
                 fontsize=6.6, va="bottom", color=C_SERIAL)
    ax2.set_ylabel("median tour length (lower is better)", color=C_FIXED)
    ax2.tick_params(axis="y", labelcolor=C_FIXED)
    ax2.grid(False)
    ax1.set_title(r"DTAM is only a *trigger* for small $\tau$ (E4)", fontsize=9.5)
    fig.savefig(FIGURES / "i5_tau_sweep.png"); plt.close(fig)
    print("  -> results/figures/i5_tau_sweep.png")


def compare_policies(rows, label, group_keys):
    """Paired DTAM-vs-fixed comparison over seeds."""
    out = []
    groups = defaultdict(dict)
    for r in rows:
        if r["mode"] not in ("island-fixed", "island-dtam"):
            continue
        key = tuple(r.get(k) for k in group_keys)
        groups[key].setdefault(r["mode"], {})[r["seed"]] = r["len_med"]
    for key, d in sorted(groups.items(), key=lambda kv: str(kv[0])):
        if "island-fixed" not in d or "island-dtam" not in d:
            continue
        seeds = sorted(set(d["island-fixed"]) & set(d["island-dtam"]))
        if len(seeds) < 3:
            continue
        f = [d["island-fixed"][s] for s in seeds]
        t = [d["island-dtam"][s] for s in seeds]
        diff_pct = 100.0 * (median(t) - median(f)) / median(f)
        wins = sum(1 for a, b in zip(t, f) if a < b)
        p = ""
        if HAVE_SCIPY and any(a != b for a, b in zip(t, f)):
            try:
                p = round(float(wilcoxon(t, f).pvalue), 4)
            except ValueError:
                p = ""
        out.append(dict(comparison=label, **dict(zip(group_keys, key)),
                        n_seeds=len(seeds),
                        fixed_med=round(median(f), 1), dtam_med=round(median(t), 1),
                        dtam_minus_fixed_pct=round(diff_pct, 2),
                        dtam_wins=f"{wins}/{len(seeds)}", wilcoxon_p=p))
    return out


def analyse_twoopt_confound(e3):
    """Is wall-clock correlated with solution quality when 2-opt is on?"""
    out = []
    for t in sorted({r["threads"] for r in e3}):
        rs = [r for r in e3 if r["threads"] == t]
        if len(rs) < 4:
            continue
        x = np.array([r["len_med"] for r in rs], float)
        y = np.array([r["t_min"] for r in rs], float)
        if x.std() == 0 or y.std() == 0:
            continue
        r_pear = float(np.corrcoef(x, y)[0, 1])
        out.append(dict(threads=t, n=len(rs),
                        corr_len_vs_time=round(r_pear, 3),
                        time_spread_pct=round(100.0 * (y.max() - y.min()) / y.min(), 1),
                        len_spread_pct=round(100.0 * (x.max() - x.min()) / x.min(), 1)))
    return out


def main():
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    e1, e2, e3, e4, e5, e6 = (load(f"E{i}") for i in range(1, 7))

    print("\n=== E1: strong scaling, islands fixed ===")
    if e1:
        t1, perf1 = scaling_table(e1, "E1")
        write_table("scaling_E1.csv", t1)
        for r in t1:
            if r["engine"] == "opt":
                print(f"  {r['mode']:<13} p={r['threads']}  t={r['time_s']:.3f}s  "
                      f"S={r['speedup']:.2f}x  E={r['efficiency']:.2f}  "
                      f"KF-e={r['karp_flatt'] if r['karp_flatt'] != '' else '-'}")
        for m in ("island-fixed", "island-dtam"):
            rs = [r for r in t1 if r["engine"] == "opt" and r["mode"] == m]
            if rs:
                print(f"  {m}: Amdahl f={rs[0]['amdahl_f']:.4f} -> ceiling {rs[0]['amdahl_ceiling']}x")

        print("\n=== Engine rewrite: baseline vs opt ===")
        eng = analyse_engines(t1)
        write_table("engine_comparison.csv", eng)
        for r in eng:
            print(f"  {r['mode']:<13} p={r['threads']}  baseline={r['baseline_s']:.3f}s  "
                  f"opt={r['opt_s']:.3f}s  gain={r['speedup_from_rewrite']:.2f}x  "
                  f"(eff {r['baseline_eff']:.2f} -> {r['opt_eff']:.2f})")

        if e2:
            t2, perf2 = scaling_table(e2, "E2")
            write_table("scaling_E2.csv", t2)
            fig_protocol(t1, t2, perf1, perf2)
        fig_scaling(t1, perf1, None)

    print("\n=== E3: does 2-opt break equal work? ===")
    if e3:
        conf = analyse_twoopt_confound(e3)
        write_table("twoopt_confound.csv", conf)
        for r in conf:
            print(f"  p={r['threads']}  corr(tour length, wall time)={r['corr_len_vs_time']:+.3f}  "
                  f"time spread={r['time_spread_pct']}%  length spread={r['len_spread_pct']}%")

    print("\n=== E4: DTAM tau sweep ===")
    if e4:
        tau_rows = analyse_tau(e4)
        write_table("tau_sweep.csv", tau_rows)
        for r in tau_rows:
            print(f"  tau={str(r['tau']):>6}  trigger={str(r['trigger_rate_pct']):>6}%  "
                  f"migrations={r['migrations']:>7}  len={r['best_len_med']:>9}  t={r['time_s']:.3f}s")
        fig_tau(tau_rows)

    print("\n=== Policy comparison: DTAM vs fixed (paired over seeds) ===")
    pol = []
    if e1:
        pol += compare_policies(e1, "E1 equal-work", ["engine", "threads"])
    if e5:
        pol += compare_policies(e5, "E5 equal-wall-clock", ["landscape", "twoopt"])
    if e6:
        pol += compare_policies(e6, "E6 TSPLIB", ["instance_file"])
    if pol:
        write_table("policy_comparison.csv", pol)
        for r in pol:
            extra = {k: v for k, v in r.items()
                     if k not in ("comparison", "n_seeds", "fixed_med", "dtam_med",
                                  "dtam_minus_fixed_pct", "dtam_wins", "wilcoxon_p")}
            print(f"  {r['comparison']:<22} {str(extra):<42} "
                  f"DTAM-fixed={r['dtam_minus_fixed_pct']:+6.2f}%  "
                  f"wins={r['dtam_wins']:>6}  p={r['wilcoxon_p']}")

    print("\n=== E5 / E6: quality under an equal wall-clock budget ===")
    for rows, name, keys in ((e5, "E5", ["landscape", "twoopt"]), (e6, "E6", ["instance_file"])):
        if not rows:
            continue
        agg = defaultdict(lambda: defaultdict(list))
        for r in rows:
            agg[tuple(r.get(k) for k in keys)][r["mode"]].append(r)
        out = []
        for key, bymode in sorted(agg.items(), key=lambda kv: str(kv[0])):
            row = dict(zip(keys, key))
            for mode in ("serial", "island-fixed", "island-dtam"):
                if mode in bymode:
                    row[f"{mode}_len"] = round(median([x["len_med"] for x in bymode[mode]]), 1)
                    g = [x["gap"] for x in bymode[mode] if x.get("gap", -1) >= 0]
                    if g:
                        row[f"{mode}_gap"] = round(median(g), 3)
            if "serial_len" in row and "island-fixed_len" in row:
                row["parallel_vs_serial_pct"] = round(
                    100.0 * (row["island-fixed_len"] - row["serial_len"]) / row["serial_len"], 2)
            out.append(row)
        write_table(f"quality_{name}.csv", out)
        for r in out:
            print(f"  {name} {str([r.get(k) for k in keys]):<26} " +
                  "  ".join(f"{m}={r.get(m+'_len','-')}" for m in
                            ("serial", "island-fixed", "island-dtam")) +
                  (f"  parallel vs serial: {r['parallel_vs_serial_pct']:+.1f}%"
                   if "parallel_vs_serial_pct" in r else ""))

    print("\nDone.")


if __name__ == "__main__":
    main()
