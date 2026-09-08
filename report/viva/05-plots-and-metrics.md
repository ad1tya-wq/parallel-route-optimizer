# Every Figure and Every Metric, Explained

Scope: this document covers every figure in `results/figures/` (the Review-2 set) and
`results/m3_original/figures/` (the superseded Review-1 set), every evaluation metric
computed anywhere in the pipeline, and every derived table in `results/analysis/`. All
numbers are copied verbatim from `results/FINDINGS.md`; none are re-derived, re-rounded,
or extrapolated here. Where FINDINGS.md does not give a number for something the plotting
code computes, that is stated explicitly rather than guessed.

Source of truth for numbers: `results/FINDINGS.md`.
Source of truth for what is plotted: `bench/analyze_study.py`, `bench/plot_review2.py`,
`bench/plot_results.py`.

---

## PART 1 — FIGURE BY FIGURE

### 1.1 `results/figures/i5_scaling.png`

**File and experiment.** Produced by `fig_scaling()` in `bench/analyze_study.py` from
experiment E1 (strong scaling, islands fixed at 8, 2-opt off, 4000 generations).
Regenerate with:
```
python bench/run_study.py
python bench/analyze_study.py
```

**What is plotted.** Two side-by-side panels sharing an x-axis of thread count
(1, 2, 3, 4, 6, 8).
- Left panel: speedup `S(p) = T(1)/T(p)` on the y-axis. Four series: `baseline`/`opt`
  engine crossed with `island-fixed`/`island-dtam` mode, distinguished by colour
  (blue = fixed, red = dtam) and line style (dotted = baseline engine, solid = opt
  engine). A grey dashed line labelled "ideal (linear)" plots `y = x`, i.e. the speedup
  a perfectly parallel program with no overhead would show. A vertical black line at
  `threads = 4` marks the physical core count, annotated "4 physical cores (8 threads =
  SMT)" — beyond this line, thread pairs share one physical core's execution resources.
- Right panel: parallel efficiency `E(p) = S(p)/p` on the y-axis, same four series and
  colour/style scheme, y-axis clipped to [0, 1.15]. A horizontal dashed grey line at
  `efficiency = 1` is the ideal-efficiency reference. The same vertical line at 4 threads
  is repeated.

**How to read it.** The `opt`-engine, `island-fixed` solid blue curve rises steadily to
about 3.3x at 4 threads, dips at 6 threads, then recovers to its highest value (3.93x) at
8. Efficiency for that same curve starts near 1.0 at low thread counts, sits around 0.83
at 3–4 threads, drops sharply at 6, and partially recovers at 8 threads but stays below
0.5. The dip at p = 6 is a visible non-monotonicity in both panels: speedup at 6 threads
is lower than at 4 threads even though more hardware is in use.

**The insight.** The optimised engine scales to a real, sub-linear-but-substantial 3.93x
on 8 threads of a 4-physical-core part, and it scales markedly better than the previous
platform (Apple M3, ~2.5x), confirming the Review-1 hypothesis that a homogeneous-core
CPU would scale more evenly than a performance/efficiency hybrid.

**What else can be inferred.**
- The p = 6 dip is not measurement noise; it is explained by integer division. With
  8 islands and `schedule(static)`, an epoch costs `ceil(islands/p)` island-units, so
  both p = 4 and p = 6 cost 2 units of work per thread, but p = 6 additionally contends
  four extra threads for only 4 physical cores. The load-balance-corrected view of the
  same data (`eff_vs_lb` in `scaling_E1.csv`, not directly the y-axis here) shows p = 3
  at 0.93 rather than the naive 0.83.
- Baseline (dotted) and opt (solid) curves are close for `island-fixed` (the "engine
  rewrite" bought speed, not scaling shape) — see the engine-comparison table for the
  actual per-thread multiplier.
- SMT threads (6, 8) never reach the efficiency of the physical-core region; this is
  expected, not an engine defect.

**Likely examiner question and answer.**
- Q: "Why is speedup at 6 threads lower than at 4 threads? Isn't more threads always
  better?" A: No — with `schedule(static)` and 8 islands, both 4 and 6 threads perform
  the same 2 island-units of work per thread (`ceil(8/6) = 2 = ceil(8/4)`), so 6 threads
  buys nothing in island-units but adds contention on only 4 physical cores. This is
  quantified by the load-balance ceiling column in `scaling_E1.csv`.
- Q: "What does the vertical line at 4 threads mean, and why does efficiency fall past
  it?" A: It marks the physical core count; beyond it, threads share SMT execution
  resources on the same physical core, so per-thread throughput naturally degrades and a
  fall in efficiency past that line is expected, not a bug.
- Q: "Is 3.93x a good speedup for 8 threads?" A: It is well below linear (8x) but is the
  best-of-the-two-engines number on this exact workload; the Amdahl fit (serial fraction
  f = 0.155) predicts a ceiling of 6.47x, so 3.93x is roughly 61% of the theoretical
  ceiling for this decomposition, with the shortfall attributable mostly to SMT and to
  the p=6 anomaly's neighbourhood.

**Honest caveats.** E1 timing uses 3 seeds and reports the minimum over seeds/repeats
(justified because with 2-opt off every seed performs identical work, so the minimum is
the closest estimate of true throughput — see `analyze_study.py`'s `scaling_table()`
docstring). There are no error bars on this figure; the underlying dispersion is not
shown, only the best observed time per configuration. The figure does not show quality
(tour length) at all — it is a pure timing figure, and a fast run here says nothing about
solution quality (see the epoch-tradeoff figure for why that separation matters).

---

### 1.2 `results/figures/i5_protocol_effect.png`

**File and experiment.** Produced by `fig_protocol()` in `bench/analyze_study.py`,
combining E1 (islands fixed at 8, the corrected protocol) and E2 (islands = threads, the
original Review-1 protocol). Regenerated by the same `analyze_study.py` run as above
(requires both `study_E1.csv` and `study_E2.csv`).

**What is plotted.** A single panel, x-axis threads, y-axis "reported speedup". Three
series: a grey dashed ideal-linear reference (`y = x`); an orange line labelled "E2:
islands = threads (original protocol)", whose speedup is measured against the *serial*
engine's median time (this matches how Review 1 originally reported it); and a blue line
labelled "E1: islands fixed at 8 (isolated)", the corrected protocol from Figure 1.1. A
vertical line at 4 threads marks the physical core boundary.

**How to read it.** The orange (E2) curve tracks closer to, or even briefly exceeds, the
ideal-linear reference at low-to-moderate thread counts — this is the artefact. The blue
(E1) curve sits further below the ideal line throughout, which is the honest reading once
the algorithm-decomposition/cache-size confound has been removed.

**The insight.** The measurement protocol changes the reported answer: letting the number
of islands equal the thread count folds a cache-size effect (smaller per-thread working
set as islands shrink) and an algorithm-shape effect (many small islands search
differently from one big population) into what is reported as pure parallel speedup.

**What else can be inferred.**
- The gap between the two curves is largest exactly where the E2 protocol shrinks the
  per-thread population the most, consistent with the stated mechanism (island size
  240 x 500 ints ≈ 480 KB, overflowing L2, vs. 30 individuals ≈ 60 KB, fitting
  comfortably).
- Because each island's RNG stream is keyed by island id rather than thread id, the E1
  curve is measuring wall-clock only — every thread count in E1 runs a bit-identical
  search trajectory (verified by the project's differential tests), so nothing but timing
  varies along that curve.

**Likely examiner question and answer.**
- Q: "Which of the two curves is 'more correct'?" A: E1 (blue). E2 conflates three
  effects (parallelism, algorithm change, cache-working-set shrink) into one number; E1
  isolates parallelism alone by holding islands fixed while sweeping threads.
- Q: "If E2 is confounded, why keep it in the study at all?" A: To quantify the size of
  the artefact directly, since Review 1 used exactly the E2 protocol; showing both curves
  side by side is what makes the artefact demonstrable rather than merely asserted.
- Q: "Is the E2 curve simply wrong?" A: Its timing numbers are correct; its
  interpretation as "parallel speedup" is what is wrong, because a component of the
  apparent speedup is a cache effect, not parallelism.

**Honest caveats.** The figure only shows the *shape* of the artefact; it does not
decompose the E2 speedup into "parallel" and "cache" components numerically — that
attribution is argued qualitatively in FINDINGS.md section 3.2, not measured as a
separate number. No error bars; both curves use single best/median times per the same
minimum-over-samples estimator as E1.

---

### 1.3 `results/figures/i5_epoch_tradeoff.png`

**File and experiment.** Produced by the E7/E8 block in `bench/plot_review2.py`. E7
measures wall-clock at identical total work as epoch length varies; E8 measures tour
quality under an equal wall-clock budget as epoch length varies. Regenerate with:
```
python bench/run_study.py             # E7
python bench/exp_epoch_quality.py     # E8
python bench/plot_review2.py
```

**What is plotted.** Two panels sharing a log-scaled x-axis "epoch length (generations
between syncs)": 1, 2, 5, 10, 25, 50, 100, 250 (left) and 5, 10, 25, 50, 100, 200 (right,
E8's own epoch grid).
- Left (E7): y-axis wall-clock in seconds for identical total work, three series by
  thread count (1 = grey, 4 = blue, 8 = red), each the minimum observed time over the
  configuration.
- Right (E8): y-axis "tour length vs epoch=5 (%), lower is better" — each series is
  normalised to its own value at the shortest epoch length in the E8 grid, so all four
  series start at 0%. Four series: uniform500 with 2-opt off (solid blue), clustered600
  with 2-opt off (solid red), uniform500 with 2-opt on (dashed blue), clustered600 with
  2-opt on (dashed red). A horizontal line at 0% is the reference.

**How to read it.** Left panel: all three thread-count curves fall steeply as epoch
length grows from 1 to about 25, then flatten — the return from lengthening the epoch
further is small. Right panel: the solid (2-opt off) curves climb well above 0%, meaning
longer epochs produce measurably worse tours (up to roughly +42% worse for
clustered600, per FINDINGS.md 4.2, at the longest epoch tested), while the dashed
(2-opt on) curves stay close to the 0% line throughout, i.e. epoch length barely matters
once 2-opt is enabled.

**The insight.** Longer epochs make the program faster (E7) but make solutions worse
(E8, when 2-opt is off) — this is a genuine Pareto trade-off, not a free win, and it is
why the project's default epoch length was deliberately left at 10 rather than raised
after seeing E7 alone.

**What else can be inferred.**
- Because the p=1 curve in E7 also falls 3x from epoch 1 to epoch 250, and p=1 has no
  barriers at all, the dominant cost being amortised by longer epochs is per-epoch serial
  bookkeeping (the diversity metric and publish copies), not synchronisation overhead —
  synchronisation cost is visible separately as the gap between the p=8 and p=1 curves,
  which narrows as epoch length grows (E7's reported p=8 speedup rises from 2.45x at
  epoch=1 to 4.00x at epoch=250).
- The right panel shows 2-opt is a quality stabiliser against epoch-length choice: with
  2-opt on, generation count no longer matters much because the local search compensates.
- Longer epochs still complete more generations overall (up to 68% more, per FINDINGS.md)
  yet the tours are worse, because the epoch length also controls the migration period,
  and migration is shown elsewhere (section 6 of FINDINGS.md) to be load-bearing for this
  algorithm.

**Likely examiner question and answer.**
- Q: "If longer epochs give more generations AND run faster, why not always use a long
  epoch?" A: Because epoch length is coupled to migration frequency in this design; a
  longer epoch means islands migrate less often, and less migration measurably degrades
  quality when 2-opt is off (up to +42% worse on clustered600). Generation count and
  quality are not the same axis.
- Q: "Why does the quality penalty disappear when 2-opt is on?" A: 2-opt's local search
  repairs much of the damage that reduced migration would otherwise cause, so its
  presence masks the epoch-length effect (moves from ~42% swing down to about 0.8%).
- Q: "Why does time still fall at p=1 as epoch length grows, if there's no parallelism to
  synchronise?" A: Because the epoch boundary also triggers serial per-epoch work
  (diversity computation, publishing best tours), and that overhead is amortised over
  more generations as the epoch lengthens — this is the actual bottleneck the experiment
  was designed to locate.

**Honest caveats.** E8 uses 8 seeds per cell (stated in FINDINGS.md 4.2) and reports the
median; no error bars or seed-to-seed spread are drawn on the figure itself. The E7 panel
uses the same minimum-over-samples estimator as the scaling figures, so it shows the best
observed case, not a distribution. The right panel's normalisation to each series' own
epoch=5 value means the panel cannot be used to compare absolute tour length between
landscapes, only relative degradation within a landscape.

---

### 1.4 `results/figures/i5_fast_twoopt.png`

**File and experiment.** Produced by the E9 block in `bench/plot_review2.py`, from
experiment E9 (candidate-list 2-opt vs. naive 2-opt, equal 3-second budget, 10 seeds,
paired Wilcoxon test). Regenerate with:
```
python bench/exp_review2_extensions.py
python bench/plot_review2.py
```

**What is plotted.** Two panels sharing an x-axis of four instances (uniform500,
clustered600, kroA200, a280).
- Left: grouped bar chart, y-axis "tour length vs naive (%), lower is better". Two bars
  per instance: grey = "naive 2-opt" (the reference, always 0% by construction) and blue
  = "fast 2-opt" (candidate-list with don't-look bits), each bar showing the percentage
  change in median tour length relative to naive at the same instance. A horizontal line
  at 0% is the naive baseline.
- Right: single-series bar chart in orange/gold, y-axis "generations completed, fast /
  naive" — the ratio of generations completed by the fast variant to the naive variant
  under the same 3-second budget. Each bar is annotated with its multiplier (e.g. "Nx").

**How to read it.** All four blue bars in the left panel sit below 0%, meaning the fast
variant reaches strictly shorter (better) tours than naive at every instance tested,
under the same time budget. The right panel bars are all well above 1, meaning the fast
variant completes many more generations than naive in the same wall-clock time.

**The insight.** Candidate-list 2-opt with don't-look bits is both faster (far more
generations per second) and produces better tours than the naive O(n^2) 2-opt scan under
an equal time budget — a rare case where there is no speed/quality trade-off at all.

**What else can be inferred.**
- The magnitude of the quality gain differs by instance: FINDINGS.md's E9 table shows
  −3.9% (uniform500, fixed), −2.4% (clustered600), down to −0.4% (kroA200) and −1.3%
  (a280) — the TSPLIB instances, already closer to their known optimum, have less room to
  improve, so the percentage gain is naturally smaller there even though the throughput
  multiplier (generations naive→fast) is largest exactly on those instances (e.g.
  kroA200: 1255→8900 generations).
- The throughput multiplier varies far more across instances than the quality gain does,
  suggesting the primary value of the fast 2-opt is the generation-count headroom it
  buys, with quality gain riding on top of that headroom via don't-look-bit exhaustion.

**Likely examiner question and answer.**
- Q: "How can the fast variant be both faster and better? Isn't there usually a
  speed/quality trade-off?" A: Because the naive O(n^2) 2-opt caps out on a fixed pass
  budget within the time limit and stops "improving" even when moves remain, whereas the
  candidate-list version with don't-look bits exhausts genuinely improving moves faster
  per pass and so converges further within the same wall-clock budget — see FINDINGS.md
  5.1: "faster and better: don't-look-bit exhaustion converges further than the
  reference's fixed pass cap."
- Q: "Why is the percentage quality gain so much smaller on kroA200 and a280 than on
  uniform500?" A: Those are TSPLIB instances the solver already reaches close to the
  published optimum on (kroA200 reaches 29368, the exact optimum, with fast 2-opt), so
  there is far less headroom left to improve versus a synthetic instance like uniform500
  that has no exact optimum to converge to.
- Q: "What statistical test backs the 'better' claim, and how strong is it?" A: A paired
  Wilcoxon signed-rank test over 10 seeds; the smallest attainable p-value at n=10 is
  0.0020, and every instance except a280 (p=0.0078) reaches that floor.

**Honest caveats.** n = 10 seeds per cell; the Wilcoxon p-value floor of 0.0020 at that
sample size is a limitation of the test, not evidence of an arbitrarily strong effect —
it is the smallest p-value achievable regardless of effect size at n=10. No error bars
are drawn on the bars themselves. The candidate-list size k=8 was chosen from a separate
sweep (k=5 loses 9.1%; k=10/16 gain about 1% more at higher build cost) that is not shown
in this figure at all.

---

### 1.5 `results/figures/i5_tau_sweep.png`

**File and experiment.** Produced by `fig_tau()` in `bench/analyze_study.py`, from
experiment E4 (DTAM stagnation-threshold sweep). Regenerate with:
```
python bench/run_study.py
python bench/analyze_study.py
```

**What is plotted.** A single panel with twin y-axes sharing the x-axis
`tau` (stagnation threshold), plotted on the taus actually swept
(0.9 down to 0.01, per FINDINGS.md 6.2).
- Left y-axis (red, "DTAM trigger rate"): percentage of island-epochs whose diversity
  fell below tau and therefore triggered migration.
- Right y-axis (blue, "median tour length, lower is better"): the median best tour length
  at each tau.
- A vertical dashed black line at `tau = 0.15` is annotated "tau=0.15 used in Review 1
  (fires on nearly every epoch)" — this marks the threshold value the original project
  used.
- A horizontal dotted grey line, taken from the fixed-migration reference run at the same
  settings, is labelled "fixed-migration reference" — this is the tour length fixed
  (non-adaptive) migration achieves, for comparison against DTAM at each tau.

**How to read it.** The red trigger-rate curve is pinned near 100% across almost the
entire swept range and only begins to fall meaningfully at very small tau (down to
78.55% at tau=0.01, per FINDINGS.md). The vertical line at tau=0.15 sits inside this
flat, saturated region. The blue tour-length curve is comparatively flat/worse across
most of the range and only drops toward (but does not beat) the fixed-migration reference
line at the smallest tau values, where the trigger rate finally departs from ~100%.

**The insight.** At tau=0.15 — the value used throughout Review 1 — DTAM's stagnation
condition fires on essentially every island-epoch, so it is not functioning as a
*trigger* at all; it behaves as fixed migration with a different source-selection rule,
which invalidates any claim that the diversity-triggering mechanism was actually being
tested.

**What else can be inferred.**
- Population diversity for this problem collapses into a very narrow operating range
  (mean 0.0181, min 0.0029, max 0.2236, per FINDINGS.md 6.2), which sits almost entirely
  below tau=0.15; this explains mechanistically, not just empirically, why the trigger
  rate is saturated at that threshold.
- Only tau=0 fully suppresses migration (0% trigger rate), and that configuration is
  markedly worse (46382 vs. ~31000 median length, per the tau_sweep table), showing that
  migration itself — regardless of how it is triggered — is essential to this algorithm's
  quality.
- No swept tau value causes DTAM's tour length to beat the fixed-migration reference line
  outright; the curve approaches it only at the very low-tau end.

**Likely examiner question and answer.**
- Q: "Why does the trigger rate stay near 100% for most of the tau range?" A: Because the
  underlying diversity metric collapses to a very small operating range (roughly
  0.003–0.22, mean 0.018) within about 100 generations, so almost any tau above roughly
  0.02 sits above the entire range the metric actually visits, guaranteeing the condition
  `diversity < tau` is nearly always true.
- Q: "Does lowering tau to get real discrimination help quality?" A: It restores
  discrimination but does not close the gap to fixed migration in this figure; the
  companion rescue experiment (E10, section 1.6) shows a comparable low-firing "relative
  trigger" mechanism actually makes quality substantially worse, because it suppresses
  migration and migration turns out to be load-bearing.
- Q: "What does the horizontal reference line represent and why is it useful here?" A: It
  is the tour length achieved by fixed (non-triggered) migration at the same settings; it
  lets an examiner see directly whether any tau value makes triggered DTAM competitive
  with the untriggered baseline — in this figure, no swept value does.

**Honest caveats.** The sweep was run on one instance family only (stated explicitly in
FINDINGS.md's known limitations, section 8); it is not shown to generalise across
landscapes. The figure gives no seed count or error bars directly, though the underlying
`analyze_tau()` computes medians over seeds recorded in `tau_sweep.csv` (8 seeds per row,
per that table).

---

### 1.6 `results/figures/i5_dtam_factorial.png`

**File and experiment.** Produced by the E10 block in `bench/plot_review2.py`, from
experiment E10 (DTAM rescue-mechanism factorial: stock, heterogeneous islands, random
immigrants, their combination, relative trigger, and relative trigger + heterogeneous —
each measured against a fixed-migration reference, equal 3-second budget, 10 seeds).
Regenerate with:
```
python bench/exp_review2_extensions.py
python bench/plot_review2.py
```

**What is plotted.** Two panels, one per landscape (uniform500 left, clustered600
right), both with 2-opt off. X-axis: six configurations (stock, heterogeneous,
immigrants, het+immigrants, rel-trigger, het+rel). Y-axis: "tour length vs fixed
migration (%)". A horizontal line at 0% marks the fixed-migration reference (median tour
length of the `FIXED-ref` configuration at that landscape/2-opt setting). Bars above 0%
are worse than fixed migration; bars are coloured red (`DTAM red`, `#dc2626`) when above
zero and green (`#1e7a5a`) when at or below zero. Each bar carries a text annotation
"donor D%" — the percentage of that configuration's migrations that found a genuinely
non-stagnating donor to pull from, rather than falling back to "most distant island
overall."

**How to read it.** In both panels, `stock`, `immigrants`, `rel-trigger`, and `het+rel`
sit visibly above the 0% line (worse than fixed migration), with `rel-trigger` and
`het+rel` the tallest red bars by a wide margin. `heterogeneous` and `het+immigrants` sit
closest to, and in the uniform500 panel below, the 0% line. Donor percentages annotated
on the bars are low (well under 5%) for stock/heterogeneous/immigrants/het+immigrants,
and near 100% for rel-trigger/het+rel.

**The insight.** No rescue configuration meaningfully beats fixed migration; the
configuration that restores the mechanism's intended discrimination (rel-trigger, donor%
near 100%) is the *worst* performer, because it achieves that discrimination by
suppressing migration frequency, and migration turns out to be the dominant source of
genetic material once islands collapse.

**What else can be inferred.**
- Heterogeneous island parameters are the only rescue that consistently improves on stock
  DTAM (though it still does not beat fixed migration) — visible as the heterogeneous bar
  sitting lower than the stock bar in both panels.
- The donor-percentage annotation tells a mechanistic story on its own: stock DTAM's
  donor-found rate is under 1%, meaning its distant-source-pull logic almost never
  actually executes as designed; rel-trigger's near-100% donor rate proves the
  discrimination mechanism works exactly as intended, and that working exactly as
  intended is precisely what hurts it here.
- The clustered600 panel shows uniformly larger positive (worse) percentages than
  uniform500 for the weak configurations, meaning DTAM's cost relative to fixed migration
  is landscape-dependent and worse on the clustered instance.

**Likely examiner question and answer.**
- Q: "If rel-trigger 'fixes' the trigger discrimination problem shown in the tau-sweep
  figure, why is it the worst configuration here?" A: Because fixing the discrimination
  means the trigger fires far less often (about 26–31%, per FINDINGS.md 6.4), which
  amounts to switching migration off most of the time; migration is shown elsewhere
  (the tau=0 point in the tau-sweep figure) to be essential to quality for this
  algorithm, so suppressing it — even "correctly" — costs quality (18–20% worse in
  FINDINGS.md's characterisation).
- Q: "What does 'donor found' actually measure, and why does it matter?" A: It counts how
  often a stagnating island, on migration, finds a genuinely non-stagnating peer to pull
  from, versus falling back to "most distant island overall" because every peer has also
  collapsed. A low percentage (stock: 0.3–0.6%) means the mechanism's actual novel
  contribution — distant-source selection among healthy peers — almost never executes.
- Q: "Did any configuration beat fixed migration?" A: One cell (het+rel on
  clustered600 with 2-opt on) shows −0.2% at p=0.0273 in the underlying data, but with 24
  comparisons made in the full table, a Bonferroni-corrected significance threshold is
  0.002, so that result is explicitly flagged in FINDINGS.md as not significant and must
  not be reported as a win.

**Honest caveats.** Both panels shown use 2-opt off; FINDINGS.md notes that with 2-opt on,
every configuration lands within ±0.3% of fixed migration and essentially none of the
differences are significant — that regime is not shown in this figure. n = 10 seeds per
configuration/landscape cell. No error bars are drawn on the bars.

---

### 1.7 `results/figures/route_uniform200.svg` and `route_clustered300.svg`

**File and experiment.** Rendered by `svg.hpp`/`main.cpp`'s `--svg` output option, one
run each on a synthetic `uniform`-generator instance (n=200) and a `clustered`-generator
instance (n=300). These are illustrative renders, not part of any numbered experiment.
Regenerate with, e.g.:
```
build\ParallelRoute.exe --gen uniform --n 200 --mode island-dtam --engine opt --islands 8 --threads 4 --pop 240 --generations 2000 --twoopt --svg results\route_uniform200.svg
```
(substitute `--gen clustered --n 300` for the second file).

**What is plotted.** A dark-background SVG canvas (900x900) containing a single closed
polyline in teal (`#4fd1c5`) connecting the city coordinates in visit order, closing back
to the start — i.e. the best tour found for that instance.

**How to read it.** A visually "clean" tour has few long crossing edges and traces a
roughly convex, non-self-intersecting sweep through the points; a poor tour shows visible
edge crossings and unnecessary backtracking. The clustered instance's tour should visibly
group into tight loops within each cluster connected by longer inter-cluster edges,
distinguishing it structurally from the uniform instance's more evenly spread tour.

**The insight.** These are qualitative sanity figures: they let a human visually confirm
the solver produces a sensible, non-crossing (or minimally-crossing) tour on two
structurally different instance types, complementing the numeric gap-to-optimum results
which are the actual evidence of correctness.

**What else can be inferred.** The uniform instance has no exact optimum to compare
against visually (it uses the BHH asymptotic estimate, see Part 2), so this rendering is
the only intuitive "does this look right" check available for that instance type; for
TSPLIB instances with known optima, the numeric gap is stronger evidence and these
particular SVGs are not TSPLIB renders.

**Likely examiner question and answer.**
- Q: "How do you know this tour is good, just from looking at it?" A: Visual inspection
  alone is not proof; the actual evidence is the numeric gap to a published or
  closed-form optimum. This figure is a sanity check, not a validation method.
- Q: "Why show a clustered and a uniform instance rather than a TSPLIB one?" A: To
  illustrate the solver's behaviour on the two synthetic generators used throughout the
  quality experiments (E5, E7, E8, E9), which have no exact optimum and are otherwise
  represented only by numbers in the report.

**Honest caveats.** These are single-run illustrations, not aggregated over seeds, and
carry no statistical claim. They do not show timing, threads, or migration policy at all.

---

### 1.8 The superseded Review-1 figures — `results/m3_original/figures/*.png`

**Files.** `speedup_uniform500.png`, `efficiency_uniform500.png`, `quality_uniform500.png`,
`convergence.png`, `diversity.png`, `policy.png`. Produced by the original
`bench/plot_results.py` against `results/m3_original/summary.csv` and
`results/m3_original/policy.csv`, on an Apple M3 (Review 1's measurement platform), kept
unchanged in `results/m3_original/`. **Why retained:** so the Review-2 numbers can be
compared against the original claims directly rather than silently overwriting them, per
`results/m3_original/README.md` and `PROJECT-GUIDE.md` section 3.

**What is plotted (per `plot_results.py`).**
- `speedup_uniform500.png`: speedup vs. threads for `island-fixed` and `island-dtam`
  (colours blue/green respectively), against a black dashed ideal-linear reference,
  computed as serial mean time divided by parallel mean time at each thread count
  (`speedup_efficiency()` in `plot_results.py`), i.e. the **islands = threads** protocol
  — the same protocol later shown to be confounded (Figure 1.2's E2 curve).
- `efficiency_uniform500.png`: the same speedup divided by thread count, against a
  horizontal ideal-100% line.
- `quality_uniform500.png`: gap to optimum (%) vs. threads for serial (horizontal dashed
  reference), island-fixed, and island-dtam.
- `convergence.png`: best-tour gap (%) vs. wall-clock time (s) for serial / island-fixed
  / island-dtam, from `results/convergence/*.csv`, means interpolated onto a common time
  grid.
- `diversity.png`: population diversity (mean edge distance) vs. generation, same three
  modes — this is the figure meant to visually motivate DTAM.
- `policy.png`: grouped bar chart of mean tour length normalised to serial (=1.0), across
  landscape/2-opt settings and the three modes, from `results/m3_original/policy.csv`.

**How to read them, and why their numbers differ from the Review-2 figures.** These
figures were produced with 2-opt enabled and with the `islands = threads` protocol
throughout, which `results/m3_original/README.md` states explicitly as their two known
confounds: (1) 2-opt's cost depends on tour quality, so equal-generation runs did not
perform equal work, and (2) raising thread count simultaneously shrank each island's
population, entangling parallel speedup with a cache-working-set effect. Both effects
were later isolated and quantified as E3 and E2/E1 respectively in the Review-2 study.
The M3 is also a different, heterogeneous (performance + efficiency core) machine from
the i5-10210U used throughout Review 2, so absolute timings are not comparable across the
two figure sets even where the protocol matches.

**The insight (why keep them at all).** They are the concrete, auditable record of what
was originally claimed, so that Review 2's corrections (a smaller but honestly-measured
i5 speedup, and a mechanistically-diagnosed DTAM negative result rather than the M3
study's "no difference" conclusion) can be checked against a real prior artefact rather
than a paraphrase of it.

**What else can be inferred.** Comparing `speedup_uniform500.png` (M3, confounded
protocol) against `i5_scaling.png` (i5, corrected protocol) is itself a demonstration of
how much of the apparent M3 speedup advantage was protocol artefact versus genuine
hardware difference — FINDINGS.md states the i5 scales considerably better than the M3
(3.93x vs. ~2.5x) even under the *corrected* protocol, so the corrected comparison still
favours the i5, but the size of that advantage cannot be read off the two figure sets
directly since they used different protocols.

**Likely examiner question and answer.**
- Q: "Why are the M3 figures still in the repository if they're wrong?" A: They are not
  fabricated or discarded; they document exactly what was measured and claimed in Review
  1, with their confounds now identified and stated in their own README, which is what
  makes the Review-2 corrections falsifiable and specific rather than assertions.
- Q: "Can you directly compare the M3's `speedup_uniform500.png` number to the i5's
  `i5_scaling.png` number?" A: Not cleanly — they use different protocols (`islands =
  threads` for the M3 figure vs. islands fixed at 8 for the i5 figure) and different
  hardware, so any difference conflates machine, protocol, and 2-opt-on-vs-off effects;
  the honest same-protocol, same-machine comparison is the `i5_protocol_effect.png`
  figure (1.2).
- Q: "Was the diversity.png figure's premise ('diversity motivates DTAM') actually
  confirmed?" A: Diversity does collapse rapidly, which is real and reconfirmed on the i5
  (FINDINGS.md 6.2), but the trigger threshold used throughout Review 1 (tau=0.15) turns
  out to sit entirely above that collapsed range, so while the diversity phenomenon is
  real, the specific trigger built on top of it was never actually being tested at the
  values used — see the tau-sweep figure (1.5).

**Honest caveats.** These figures have no stated seed counts or error bars in the
retained files beyond what `plot_results.py`'s mean-over-seeds computation implies; the
M3 platform's own thermal/measurement characteristics were not audited to the standard
Review 2 applies to the i5 (no thermal-drift canary, no round-robin repeat scheduling).
They should be read as historical record, not as directly comparable evidence.

---

## PART 2 — METRIC BY METRIC

### Tour length
**Definition.** Sum of Euclidean distances between consecutive cities in visit order,
including the closing edge back to the start. **Computed by** the length-recomputation
path inside `validate_tour()` in `ga.hpp` (independent recomputation used for structural
validation) and by the GA's own fitness evaluation during the search. **Units/range.**
Distance units native to the instance (TSPLIB units, or generator coordinate units);
strictly positive, no upper bound. **Good value.** As close as possible to the known or
estimated optimum. **Bad value.** Far above optimum, or (structurally) a value that does
not match an independent recomputation of the same permutation — the latter is a
correctness failure, not a quality one. **Measured values in this project:** the
correctness table (FINDINGS.md section 1) — e.g. berlin52 = 7542, matching the published
optimum exactly. **Failure modes.** Tour length alone says nothing about time budget or
thread count; a slower run given more time will trivially reach a shorter tour, so it
must always be reported alongside the budget it was measured under (generations or
wall-clock).

### Gap to optimum (percentage)
**Definition.** `100 * (found − optimum) / optimum` against either a published TSPLIB
optimum or, for `uniform`/`clustered` synthetic instances with no exact optimum, the
Beardwood–Halton–Hammersley (BHH) asymptotic estimate for random Euclidean TSP.
**Computed by** the gap-computation logic in `tsp.hpp` using its published-optimum lookup
table. **Units/range.** Percentage; 0% is optimal; can, in principle, be negative against
the BHH estimate. **Why it can be negative against BHH:** BHH is an asymptotic
*estimate* of expected optimal tour length as n → infinity, not a guaranteed lower bound
for a specific finite random instance, so a particular instance's true optimum can fall
below the BHH estimate, making a solver's gap against it read as negative even at or near
true optimality. **Good value.** 0.00% against a published TSPLIB optimum (achieved on
all seven TSPLIB instances in this project, per FINDINGS.md section 1). **Bad value.**
Any large positive percentage against a TSPLIB optimum indicates the search has not
converged; against BHH, values must be interpreted cautiously given the estimate's
asymptotic nature. **Measured values.** 0.00% on all seven TSPLIB instances (berlin52,
eil51, st70, kroA100, ch150, kroA200, a280) with candidate-list 2-opt; `quality_E6.csv`
reports non-zero small gaps for `serial`/`island-fixed`/`island-dtam` on a280
specifically (serial_gap = 2.346, island-fixed_gap = 0.892, island-dtam_gap = 1.047).
**Failure mode.** Reporting a "gap" against BHH as if it were a gap against a true
optimum overstates precision; this project restricts exact-reference quality claims to
the TSPLIB instances specifically because of this (FINDINGS.md section 1, known
limitations section 8).

### Wall-clock time
**Definition.** Elapsed real time for a run, measured via `omp_get_wtime()` (with a
`std::chrono` fallback) in `timer.hpp`. **Computed by** `timer.hpp`, invoked around the
timed region in `main.cpp`, aggregated by `run_study.py`'s `measure()`/`aggregate()`.
**Units/range.** Seconds; strictly positive. **Good/bad.** Lower is better for a fixed
work unit; not meaningful in isolation without stating what work was done in that time
(generations, or a stopping condition). **Measured values.** E1's per-thread times, e.g.
`opt`/`island-dtam` at 1 thread = 5.304 s, at 8 threads = (see `scaling_E1.csv`).
**Failure modes.** On a 15 W thermally-managed laptop part, a single timing sample is
inside the noise floor; this project addresses that with repeats, round-robin scheduling,
and a thermal-drift canary (see below) rather than trusting one sample.

### Speedup
**Definition/formula.** `S(p) = T(1) / T(p)`, where T(1) is the same configuration's
single-thread time. **Computed by** `scaling_table()` in `bench/analyze_study.py`, using
the minimum observed time over seeds and repeats at each (engine, mode, threads) cell as
`T(p)`. **Units/range.** Dimensionless multiplier; 1.0 = no speedup; theoretical ceiling
is p (linear); can occasionally exceed p ("super-linear") though this project explicitly
diagnoses one such apparent case (E2, cache effect) as an artefact rather than genuine
super-linear speedup. **Good value.** Close to p. **Bad value.** Close to 1, or falling
as p increases. **Measured values (E1, opt engine, island-fixed, from FINDINGS.md
section 2):** 1.00x (p=1) up to 3.93x (p=8), with a documented dip to 2.83x at p=6.
**Failure modes.** Speedup measured while the workload itself changes with p (E2's
`islands = threads` protocol) conflates parallel speedup with algorithmic/cache effects;
speedup measured with 2-opt on conflates timing with which run happened to find a better
tour faster (E3). Both are documented failure modes this project specifically diagnoses,
not hypothetical ones.

### Parallel efficiency
**Definition/formula.** `E(p) = S(p) / p`. **Computed by** the same `scaling_table()`
function, immediately from the speedup value. **Units/range.** Dimensionless, typically
[0, 1]; 1.0 = perfect scaling. **Good value.** Close to 1.0. **Bad value.** Well below
1.0, especially if falling steeply as p grows. **Measured values (E1, opt engine,
island-fixed):** 1.00 (p=1) down to 0.49 (p=8), with intermediate values 0.98 (p=2), 0.83
(p=3 and p=4), 0.47 (p=6) — FINDINGS.md section 2. **Failure modes.** A raw efficiency
number below 1.0 is frequently misread as "poor scaling" when the true cause is a
load-imbalance artefact from integer division of islands over threads (the p=3/p=6 cases
here) rather than any inherent parallel-overhead problem; the load-balance ceiling metric
exists specifically to separate these two causes.

### Load-balance ceiling and efficiency-versus-ceiling
**Definition/formula.** Load-balance ceiling `= islands / ceil(islands / p)` — the best
speedup obtainable at thread count p given that islands are distributed with
`schedule(static)` and `islands` cannot be split across threads. Efficiency-vs-ceiling
`= S(p) / ceiling`. **Computed by** `scaling_table()` in `bench/analyze_study.py`
(`lb_ceiling`, `eff_vs_lb` columns). **Units/range.** Ceiling is a speedup-like multiplier
capped at p; eff-vs-ceiling is dimensionless, ideally close to 1.0. **Good value.**
Eff-vs-ceiling near 1.0, meaning the engine is extracting essentially all the parallelism
the island/thread decomposition allows, regardless of how that decomposition's own ceiling
compares to a naive linear ideal. **Measured values.** At p=3 with 8 islands, raw
efficiency is 0.83 but eff-vs-ceiling is 0.93, because the ceiling itself is only 2.67x
(8/ceil(8/3)) — the "true" shortfall from the achievable ceiling is much smaller than the
shortfall from a naive linear ideal (FINDINGS.md section 2). **Failure modes.** Without
this correction, integer-division artefacts of a fixed island count over an arbitrary
thread count are systematically misreported as poor parallel scaling.

### Karp-Flatt metric
**Definition/formula.** `e(p) = (1/S − 1/p) / (1 − 1/p)`, the experimentally determined
serial fraction implied by a single measured speedup at thread count p. **Computed by**
`karp_flatt()` in `bench/analyze_study.py`. **Units/range.** Dimensionless fraction,
nominally [0, 1] though it can go negative or above 1 under noisy/anomalous data (as with
E2's slightly negative value at p=2, an artefact of near-linear/mild super-linear timing
noise — see `scaling_E2.csv`, `karp_flatt = -0.0059` at p=2). **Interpretation, not just
value.** Its *trend* as p grows matters more than any single value: roughly constant e(p)
across p indicates a true Amdahl-style fixed serial section; e(p) rising with p indicates
growing parallel overhead (synchronisation, false sharing, memory bandwidth contention) —
an engineering problem rather than an algorithmic ceiling. **Measured values (E1,
island-fixed):** 0.020 (p=2), 0.104 (p=3), 0.070 (p=4), 0.224 (p=6), 0.148 (p=8) —
FINDINGS.md section 2; the non-monotonic jump at p=6 is consistent with the same
load-imbalance anomaly discussed above, since Karp-Flatt does not itself correct for the
static-schedule ceiling. **Failure modes.** Karp-Flatt at any single p can be distorted
by the same integer-division artefact that distorts raw efficiency; reading a single
value in isolation without the trend, or without the load-balance-ceiling correction,
risks over-interpreting a scheduling artefact as a synchronisation problem.

### Amdahl fitted serial fraction and ceiling
**Definition/formula.** Least-squares fit of `S(p) = 1 / (f + (1−f)/p)` over the observed
(p, S(p)) pairs, scanning f on a fine grid (0 to 0.999, 20000 points) to minimise squared
error; ceiling reported as `1/f`. **Computed by** `amdahl_fit()` in
`bench/analyze_study.py`, invoked once per (engine, mode) inside `scaling_table()`.
**Units/range.** f is dimensionless in [0, 1); ceiling is a speedup multiplier, `1/f`.
**Good value.** Small f (large ceiling). **Bad value.** Large f (low ceiling), meaning
the algorithm's serial-equivalent fraction dominates achievable speedup regardless of
thread count. **Measured values.** `opt`/`island-fixed`: f = 0.155, ceiling 6.47x
(FINDINGS.md section 2); `scaling_E1.csv`'s `island-dtam` row separately reports f =
0.1778, ceiling 5.62; `scaling_E2.csv`'s baseline row reports f = 0.2192, ceiling 4.56 —
illustrating that the fitted ceiling is protocol- and mode-dependent, not a fixed
property of the underlying algorithm alone. **Failure modes.** The fit is only as good as
the (p, S(p)) data supplied to it; it is fit over just six thread counts (1,2,3,4,6,8)
here, so it should be read as an indicative fixed-serial-fraction estimate, not a
precision physical constant, and the fit does not itself account for the load-balance
ceiling artefact affecting individual points (e.g. p=6).

### Generations completed
**Definition.** Count of GA generations executed within a work or time budget.
**Computed by** the GA's main loop counter in `island.hpp`/`island_opt.hpp`, logged to
the CSV row written by `main.cpp`. **Units/range.** Non-negative integer. **Good/bad.**
More generations under a fixed time budget generally indicates higher throughput, but
(per the epoch-tradeoff finding) more generations does not guarantee better quality — see
Figure 1.3, where longer epochs complete up to 68% more generations yet find worse tours.
**Measured values.** E8's italicised generation counts, e.g. 5842 (epoch=5) up to 9800
(epoch=200) for uniform-500 (FINDINGS.md section 4.2); E9's generation multipliers, e.g.
naive 210 vs. fast 3015 for uniform500-fixed. **Failure modes.** Used alone as a
throughput metric without a paired quality number, generation count can make a
worse-converging configuration look like the winner (exactly the trap E7-alone would have
set, corrected only by pairing it with E8).

### Time-to-target
**Definition.** Wall-clock time for a run to first reach a specified target gap.
**Computed by** the `time_to_target` field emitted per row and plotted by `plot_ttt()` in
`bench/plot_results.py`. **Units/range.** Seconds, or a sentinel negative value when the
target was never reached within the run. **Status in this project.** The `plot_ttt()`
call is explicitly commented out in `plot_results.py`'s `main()` ("disabled: target
rarely reached at equal-work budget (the quality-vs-time curve conveys this more reliably
")) — so no `ttt.png` figure exists in the current figure set, and no time-to-target
number appears in FINDINGS.md. **Failure modes.** At an equal-work budget, many
configurations never reach the target gap at all, which would make the metric mostly
composed of "did not reach" sentinels rather than informative timings — the documented
reason it was dropped in favour of the continuous convergence curve.

### Population diversity (edge-set)
**Definition/formula.** Mean fraction of edges by which each tour in a population differs
from the island's current best tour, i.e. 1 minus the shared-edge fraction, averaged over
the population. **Computed by** `population_diversity()` in `ga.hpp` (the O(pop*n)
hash-set reference implementation) and by the bitset-based equivalent in `diversity.hpp`
(verified bitwise-identical to the reference by `tests/test_diversity.cpp`). **Units/
range.** Dimensionless fraction in [0, 1]; low value means the population has converged
(individuals nearly identical to the best tour); high value means the population is still
diverse. **Good/bad.** Depends on algorithm intent — for DTAM's design, diversity is
meant to discriminate "healthy" from "stagnating" islands, so a wide, informative spread
of values across islands would be "good" for the mechanism to function; in practice, this
project measures the opposite (see below). **Measured values.** Whole-run statistics:
min 0.0029, max 0.2236, mean 0.0181 (FINDINGS.md section 6.2); at generation 10 the value
is 0.224, collapsing to 0.004 by generation 1450. **Failure modes, and this project's
central negative finding built on it.** Because the metric collapses into a very narrow
range within about 100 generations, a fixed threshold (tau = 0.15) chosen without
reference to that range fires on essentially all island-epochs (99.7%), turning an
intended *trigger* into an unconditional policy — precisely the mechanism failure
documented in FINDINGS.md sections 6.2–6.3 and shown in the tau-sweep figure.

### DTAM trigger rate
**Definition/formula.** `100 * stag_epochs / island_epochs` — the percentage of
island-epochs where the diversity-below-tau stagnation condition fired. **Computed by**
`analyze_tau()` in `bench/analyze_study.py`, from the `stag_epochs`/`island_epochs`
fields logged by the C++ engine. **Units/range.** Percentage, 0–100. **Good value**
(for the mechanism to be meaningfully "adaptive"): a rate well below 100%, showing
genuine discrimination between stagnating and healthy islands. **Bad value.** Near 100%
(no discrimination) or exactly 0% (migration entirely suppressed). **Measured values.**
100 / 100 / 99.97 / 99.89 / 99.73 / 99.59 / 99.06 / 97.2 / 93.94 / 90.62 / 78.55% for
tau = 0.9 down to 0.01 (FINDINGS.md section 6.2); only tau = 0 achieves 0% (migration
fully off). **Failure modes.** A high trigger rate can be mistaken for "the algorithm is
frequently stagnating and correctly responding," when in this project it instead means
the trigger threshold sits above the metric's entire operating range and is not
discriminating at all.

### Donor availability (found vs. fallback)
**Definition.** Of all migrations a stagnating island performs, the percentage that found
a genuinely non-stagnating peer to pull from (`donor_found`) versus fell back to "most
distant island overall" because every peer was also stagnating (`donor_fallback`).
**Computed by** the donor-availability instrumentation added to `island_opt.hpp`, summed
per configuration in the E10 figure code (`i5_dtam_factorial.png`'s "donor %" annotation
= `100 * donor_found / (donor_found + donor_fallback)`). **Units/range.** Percentage,
0–100. **Good value.** High — the mechanism is exercising its intended distant-source
selection among genuinely healthy peers. **Bad value.** Near 0 — the fallback path is
doing essentially all the work, meaning the mechanism's actual novel contribution rarely
executes. **Measured values.** Stock DTAM: 0.3–0.6% (FINDINGS.md section 6.3);
heterogeneous: 1.7%; immigrants: 1.5%; het+immigrants: 4.1%; rel-trigger: 100.0%;
het+rel: 100.0% (FINDINGS.md section 6.4, E10 table). **Failure modes.** A near-100%
donor-found rate might look unambiguously good, but the E10 result shows the
configuration that achieves it (rel-trigger) does so only by drastically suppressing
migration frequency (26–31% trigger rate), which costs quality overall — donor
availability alone is not a proxy for algorithm quality.

### Migration count
**Definition.** Total number of migration events during a run. **Computed by** a counter
(`total_migrations`) incremented in `island.hpp`/`island_opt.hpp` and logged per row.
**Units/range.** Non-negative integer. **Good/bad.** Not inherently good or bad in
isolation; must be read alongside trigger rate and quality — e.g. tau_sweep.csv shows
migrations dropping from thousands at high tau toward 0 at tau=0, tracking the trigger
rate. **Measured values.** `tau_sweep.csv`: e.g. tau=0.01, migrations (median) = 2513.5;
tau=0.0, migrations = 0.0. **Failure modes.** FINDINGS.md section 3.1 notes the frozen
baseline engine has a missing-barrier bug (`omp single`'s implicit barrier is at exit,
not entry) that makes its logged per-epoch migration counts not well-defined, though this
does not corrupt the populations themselves — a caveat specific to the baseline engine's
migration-count logging, not to the search result.

### Thermal drift canary
**Definition.** Percentage change in the wall-clock time of a fixed reference
configuration ("canary": `island-fixed`, `opt` engine, uniform n=400) timed at the start
of every measurement round, computed as `100 * (canary_times[-1] - canary_times[0]) /
canary_times[0]`. **Computed by** `run_study.py`'s `main()`, logged as
`canary_drift_pct`. **Units/range.** Percentage, signed; 0% = no drift; positive = the
machine slowed down (e.g. thermal throttling) over the course of the experiment; negative
= sped up (e.g. turbo ramp-up). **Good value.** Close to 0%. **Bad value.** A large
magnitude, indicating the run's timing comparisons across rounds are contaminated by a
changing machine state rather than the configuration under test. **Measured value.** Not
individually reproduced in FINDINGS.md's prose (the canary numbers are a per-run
diagnostic printed by `run_study.py`, stored per experiment in the raw
`study_E*.csv`/`canary_drift_pct` column rather than summarised as a single headline
statistic); PROJECT-GUIDE.md instructs the operator to keep the machine idle during the
run specifically because of this metric. **Failure modes.** A canary reading near 0% for
one experiment does not guarantee a clean run for a different, later experiment; each
experiment's own canary column should be checked rather than assuming one measurement
carries over.

### Coefficient of variation (CV) of repeated timings
**Definition/formula.** `t_cv = pstdev(times) / mean(times)` over repeated timing samples
of the same configuration. **Computed by** `aggregate()` in `bench/run_study.py`.
**Units/range.** Dimensionless, non-negative; 0 = perfectly repeatable timing. **Good
value.** Small (timings tightly clustered). **Bad value.** Large (timings highly
variable, undermining confidence in any single reported time). **Measured value.** Not
quoted as a single headline number in FINDINGS.md; it is a per-row diagnostic field
(`t_cv`) available in the raw `study_E*.csv` files, used to sanity-check the
minimum-over-samples timing estimator described in `scaling_table()`'s docstring rather
than reported as a summary statistic. **Failure modes.** A high CV at a given
configuration would undermine the minimum-over-samples estimator's implicit assumption
that noise is additive and small; this project does not report an aggregate CV figure, so
an examiner asking for "the" CV value should be told it exists per-row in the raw data
but is not summarised in FINDINGS.md.

### Wilcoxon signed-rank p-value
**Definition.** Non-parametric paired-difference test p-value, used because tour lengths
are not assumed normally distributed and comparisons are paired (both policies see the
same random seed). **Computed by** `compare_policies()` in `bench/analyze_study.py` via
`scipy.stats.wilcoxon`, and directly within the E9/E10 experiment scripts.
**Units/range.** [0, 1]; smaller indicates stronger evidence against the null hypothesis
of no difference between paired samples. **Good/bad depends on the claim being tested**
— a small p-value supports a genuine, non-random difference between the two policies
compared. **Measured values.** E9: p = 0.0020 for most instance/mode pairs (the smallest
value attainable with n=10 paired samples), p = 0.0078 for a280 (FINDINGS.md section
5.1); E10: p ranging from 0.0020 (stock, heterogeneous) to 0.0371 (het+immigrants)
against fixed migration (FINDINGS.md section 6.4); E1's equal-work DTAM comparison:
p = 0.25, the best a Wilcoxon test can return at n=3 pairs (FINDINGS.md section 8, known
limitations). **Failure modes.** With very small sample sizes (E1's n=3), p=0.25 is the
floor regardless of true effect size — a "non-significant" p-value there is a sample-size
artefact, not evidence of no effect. Conversely, with 24 comparisons in the E10 table, an
uncorrected small p-value (e.g. 0.0273 for one het+rel cell) is explicitly not treated as
significant once a Bonferroni correction (threshold 0.002) is applied (FINDINGS.md
section 6.5, point 4) — multiple-comparisons correction changes which results may be
reported as real.

### Validation status
**Definition.** A pass/fail check that (a) the returned tour is a genuine permutation of
`0..n-1` and (b) its reported length matches an independent recomputation.
**Computed by** `validate_tour()` in `ga.hpp`, invoked whenever `--validate` is passed
(every run in the study uses it, per `run_one()` in `bench/run_study.py` which always
appends `--validate`). **Units/range.** Boolean per run; aggregated as a pass count/rate
across the study. **Good value.** 100% pass rate. **Bad value.** Any failure, which
indicates a correctness bug in tour construction or length bookkeeping, not merely a
suboptimal search. **Measured value.** "1,600+ measured configurations across ten
experiments, every one of them validated ... Zero validation failures" (FINDINGS.md,
opening summary). **Failure modes.** Validation confirms structural correctness
(permutation, consistent length) but says nothing about solution *quality* — a validly
returned but very poor tour still passes validation; validation and gap-to-optimum are
independent axes and both are required.

---

## PART 3 — THE DERIVED TABLES (`results/analysis/*.csv`)

### `scaling_E1.csv`
Columns: `exp, engine, mode, threads, islands, time_s, speedup, efficiency, lb_ceiling,
eff_vs_lb, karp_flatt, amdahl_f, amdahl_ceiling`.
- `exp` — fixed literal "E1", identifies the source experiment.
- `engine` — `baseline` (frozen Review-1 engine) or `opt` (re-engineered engine).
- `mode` — `island-fixed` (P1) or `island-dtam` (P2).
- `threads` — OpenMP thread count for this row.
- `islands` — island count held fixed (8, per E1's design) for this engine/mode.
- `time_s` — minimum observed wall-clock time (seconds) at this cell.
- `speedup` — `time_s` at threads=1 divided by this row's `time_s`.
- `efficiency` — `speedup / threads`.
- `lb_ceiling` — the load-balance-corrected maximum achievable speedup at this thread
  count given `islands` and static scheduling.
- `eff_vs_lb` — `speedup / lb_ceiling`, the corrected efficiency.
- `karp_flatt` — the experimentally implied serial fraction at this row (blank at
  threads=1, undefined).
- `amdahl_f`, `amdahl_ceiling` — the single least-squares-fit serial fraction and implied
  ceiling for this whole (engine, mode) series, repeated on every row of that series.
This table backs the entire strong-scaling section of FINDINGS.md (section 2) and both
panels of Figure 1.1, plus the Karp-Flatt and Amdahl claims throughout.

### `scaling_E2.csv`
Same column schema as `scaling_E1.csv`, but from experiment E2 (the original protocol,
`islands == threads`). This table backs the orange curve in Figure 1.2 and the
`amdahl_f`/`amdahl_ceiling` values quoted for the baseline/E2 protocol (e.g. baseline
f = 0.2192, ceiling 4.56) used to contrast against E1's corrected numbers.

### `engine_comparison.csv`
Columns: `mode, threads, baseline_s, opt_s, speedup_from_rewrite, baseline_eff, opt_eff`.
- `mode`, `threads` — as above.
- `baseline_s`, `opt_s` — E1 minimum time for the frozen and re-engineered engines at
  this cell.
- `speedup_from_rewrite` — `baseline_s / opt_s`, i.e. how much the engineering rewrite
  itself (not parallelism) sped things up at this exact thread count.
- `baseline_eff`, `opt_eff` — each engine's own parallel efficiency at this thread count.
This table backs the "what the engineering rewrite bought" claims in FINDINGS.md section
5 and PROJECT-GUIDE.md section 7.0, separating the rewrite's speed gain from parallel
scaling.

### `twoopt_confound.csv`
Columns: `threads, n, corr_len_vs_time, time_spread_pct, len_spread_pct`.
- `threads` — thread count for this row's E3 sample.
- `n` — number of configurations aggregated (10, per FINDINGS.md).
- `corr_len_vs_time` — Pearson correlation between final tour length and wall-clock time
  at fixed thread count, with 2-opt enabled.
- `time_spread_pct`, `len_spread_pct` — the percentage spread (max−min)/min across the
  sampled configurations, for time and length respectively.
This table backs FINDINGS.md section 3.1's claim of a +0.15 to +0.31 correlation with a
6–8% time spread and 4.8% length spread, i.e. the quantified evidence that "equal work"
under 2-opt-enabled timing is confounded.

### `tau_sweep.csv`
Columns: `tau, trigger_rate_pct, migrations, best_len_med, time_s, seeds`.
- `tau` — the swept stagnation threshold, or the literal string `"fixed"` for the
  non-adaptive migration reference row.
- `trigger_rate_pct` — median percentage of island-epochs that triggered migration at
  this tau.
- `migrations` — median migration count at this tau.
- `best_len_med` — median best tour length at this tau.
- `time_s` — median (minimum-based) wall-clock time at this tau.
- `seeds` — number of distinct seeds aggregated into this row (8, per FINDINGS.md 6.2).
This table backs Figure 1.5 directly and every trigger-rate/tour-length number quoted in
FINDINGS.md section 6.2.

### `policy_comparison.csv`
Columns: `comparison, [grouping keys...], n_seeds, fixed_med, dtam_med,
dtam_minus_fixed_pct, dtam_wins, wilcoxon_p`.
- `comparison` — which experiment/protocol produced this row (e.g. "E1 equal-work", "E5
  equal-wall-clock", "E6 TSPLIB").
- grouping keys vary by comparison — `engine, threads` for E1; `landscape, twoopt` for
  E5; `instance_file` for E6.
- `n_seeds` — number of paired seeds used in the Wilcoxon test for this row.
- `fixed_med`, `dtam_med` — median tour length for fixed migration and DTAM respectively
  at this grouping.
- `dtam_minus_fixed_pct` — percentage difference of DTAM relative to fixed (negative =
  DTAM better).
- `dtam_wins` — count of seeds where DTAM's paired result beat fixed's, out of `n_seeds`.
- `wilcoxon_p` — the paired Wilcoxon p-value for this row.
This table is the direct source for FINDINGS.md section 6.1's "equal work: DTAM 8.6%
better, 3/3 seeds" and "equal wall-clock: DTAM 8.4% worse on clustered-600, 1/12 wins,
p=0.001" claims, and for every other DTAM-vs-fixed comparison quoted in the report.

### `quality_E5.csv`
Columns: `landscape, twoopt, serial_len, island-fixed_len, island-dtam_len,
parallel_vs_serial_pct`.
- `landscape` — instance generator/name (e.g. clustered600).
- `twoopt` — 0 or 1, whether 2-opt local search was enabled.
- `serial_len`, `island-fixed_len`, `island-dtam_len` — median tour length per mode at
  this landscape/2-opt setting, under an equal wall-clock budget.
- `parallel_vs_serial_pct` — percentage difference of `island-fixed_len` relative to
  `serial_len` (negative = parallel found a shorter/better tour than serial in the same
  time).
This table backs the equal-wall-clock quality comparisons used throughout section 6 of
FINDINGS.md and is one half of the paired-comparison inputs feeding
`policy_comparison.csv`'s "E5 equal-wall-clock" rows.

### `quality_E6.csv`
Columns: `instance_file, serial_len, serial_gap, island-fixed_len, island-fixed_gap,
island-dtam_len, island-dtam_gap, parallel_vs_serial_pct`.
- `instance_file` — TSPLIB instance name (e.g. a280, berlin52).
- `*_len` — median tour length per mode.
- `*_gap` — gap to the published optimum (%) per mode, computed against the exact TSPLIB
  optimum rather than the BHH estimate, so these gap values are exact and unambiguous
  unlike the synthetic-landscape gaps discussed in Part 2.
- `parallel_vs_serial_pct` — as in `quality_E5.csv`.
This table backs the correctness/quality claims for real TSPLIB instances (FINDINGS.md
section 1's exact-optimum table draws on the `--twoopt-fast` runs; `quality_E6.csv`
specifically captures the equal-wall-clock mode-by-mode comparison on those same
instances, e.g. berlin52 reaching 0.0% gap in every mode).

---

## PART 4 — WHICH FIGURE OR TABLE ANSWERS WHICH QUESTION

| Examiner question | Figure / table that answers it |
|---|---|
| "What speedup did you actually get, and on how many threads?" | `i5_scaling.png` (left panel); `scaling_E1.csv` |
| "Why does speedup fall at 6 threads?" | `i5_scaling.png` + `scaling_E1.csv`'s `lb_ceiling`/`eff_vs_lb` columns |
| "What's your parallel efficiency, and where does it break down?" | `i5_scaling.png` (right panel); `scaling_E1.csv` |
| "Is your serial-fraction bottleneck a hardware limit or an engineering one?" | `scaling_E1.csv`'s `karp_flatt` trend across threads |
| "What's the theoretical ceiling on your speedup?" | `scaling_E1.csv`'s `amdahl_f`/`amdahl_ceiling`; FINDINGS.md section 2 |
| "How do you know your original (Review-1) speedup number was wrong?" | `i5_protocol_effect.png`; `scaling_E2.csv` vs `scaling_E1.csv` |
| "What did the engineering rewrite actually buy you?" | `engine_comparison.csv`; FINDINGS.md section 5 |
| "Does 2-opt break your equal-work assumption?" | `twoopt_confound.csv`; FINDINGS.md section 3.1 |
| "Why keep the epoch length at 10 instead of raising it for speed?" | `i5_epoch_tradeoff.png`; FINDINGS.md section 4 |
| "What's the actual bottleneck — synchronisation or something else?" | `i5_epoch_tradeoff.png` left panel, p=1 curve; FINDINGS.md section 4.1 |
| "Does your faster 2-opt cost you solution quality?" | `i5_fast_twoopt.png`; FINDINGS.md section 5.1 |
| "Was DTAM's stagnation trigger actually tested at tau=0.15?" | `i5_tau_sweep.png`; FINDINGS.md section 6.2 |
| "Did any of your DTAM fixes actually beat fixed migration?" | `i5_dtam_factorial.png`; FINDINGS.md section 6.4-6.5 |
| "Why does 'fixing' the trigger discrimination make things worse?" | `i5_dtam_factorial.png` (rel-trigger bars); FINDINGS.md section 6.5 point 2 |
| "How often does DTAM's distant-source-pull mechanism actually fire as designed?" | `i5_dtam_factorial.png` donor-% annotations; FINDINGS.md section 6.3 |
| "Is your solver actually correct?" | FINDINGS.md section 1 correctness table; `quality_E6.csv`; `route_uniform200.svg`/`route_clustered300.svg` as a visual sanity check |
| "Why can your quality 'gap' be negative on synthetic instances?" | Part 2, "Gap to optimum" entry; FINDINGS.md section 1 |
| "How do the DTAM-vs-fixed comparisons differ by budget type (work vs wall-clock)?" | `policy_comparison.csv`; FINDINGS.md section 6.1 |
| "How significant are your DTAM/2-opt comparisons statistically?" | Part 2, "Wilcoxon signed-rank p-value" entry; `policy_comparison.csv`, E9/E10 tables in FINDINGS.md |
| "Why do the original (M3) figures look so much better than the i5 ones?" | `results/m3_original/figures/*.png` + its README; FINDINGS.md section 3 |
| "Did you control for thermal throttling / timing noise?" | Part 2, "Thermal drift canary" and "Coefficient of variation" entries; PROJECT-GUIDE.md section 6.3 |
