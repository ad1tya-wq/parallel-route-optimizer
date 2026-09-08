# Review-2 findings — single source of truth

Every number here was measured on the machine below and is reproducible with the commands in
`PROJECT-GUIDE.md`. All documents (report, deck, README) must agree with this file. Where a
Review-1 claim is contradicted, both numbers are given.

**Platform.** Intel Core i5-10210U, 4 physical cores / 8 SMT threads, 1.6 GHz base, 6 MB L3, 15 W
TDP, 8 GB RAM, Windows 11. GCC 15.1 (MSYS2 UCRT64), `-O3 -march=native -fopenmp`, statically
linked. `OMP_PROC_BIND=close`, `OMP_PLACES=cores`.

This is the platform Review 1 named as its target ("Intel Core i5 10th-gen, 4-6 cores, CPU-only")
but never measured on; all Review-1 numbers came from an Apple M3.

**Scale of the study.** 1,600+ measured configurations across ten experiments, every one of them
validated (`--validate`: the returned tour must be a permutation of `0..n-1` and its reported
length must match an independent recomputation). Zero validation failures.

---

## 1. Correctness

| Instance | Published optimum | Result | Gap |
|---|--:|--:|--:|
| berlin52 | 7542 | 7542 | 0.00% |
| eil51 | 426 | 426 | 0.00% |
| st70 | 675 | 675 | 0.00% |
| kroA100 | 21282 | 21282 | 0.00% |
| ch150 | 6528 | 6528 | 0.00% |
| kroA200 | 29368 | 29368 | 0.00% |
| a280 | 2579 | 2579 | 0.00% |

All seven reach the **proven optimum** within a 3-second budget using candidate-list 2-opt.
Before that optimisation, kroA200 stalled at 29491, a280 at 2602 and eil51 at 427.

The `circle` generator's optimum is known in closed form (`n · 2R · sin(π/n)`) and is reached to
0.00%; `build.ps1` runs this as a build gate. Review 1 reported gaps only against the
Beardwood–Halton–Hammersley *estimate* for random points, which is an asymptotic approximation, not
an optimum, and against which a "gap" can even be negative.

---

## 2. Strong scaling (E1) — islands fixed at 8, 2-opt off, 4000 generations

| threads | time (s) | speedup | efficiency | load-balance ceiling | eff. vs ceiling | Karp–Flatt |
|--:|--:|--:|--:|--:|--:|--:|
| 1 | 4.240 | 1.00× | 1.00 | 1.00 | 1.00 | — |
| 2 | 2.162 | 1.96× | 0.98 | 2.00 | 0.98 | 0.020 |
| 3 | 1.706 | 2.49× | 0.83 | 2.67 | **0.93** | 0.104 |
| 4 | 1.284 | 3.30× | 0.83 | 4.00 | 0.83 | 0.070 |
| 6 | 1.498 | 2.83× | 0.47 | 4.00 | 0.71 | 0.224 |
| 8 | 1.080 | **3.93×** | 0.49 | 8.00 | 0.49 | 0.148 |

Amdahl fit: serial fraction **f = 0.155**, implying a ceiling of **6.47×**.

**p = 6 is slower than p = 4, and this is not noise.** Islands are distributed with
`schedule(static)`, so an epoch costs `ceil(I/p)` island-units. With I = 8, both p = 6 and p = 4
cost 2 units, and p = 6 additionally contends for 4 physical cores. Measuring against a linear
ideal would misreport integer division as "poor scaling"; the load-balance ceiling column corrects
for it, and p = 3 then reads 0.93 rather than 0.83.

**The i5 scales considerably better than the M3 (3.93× vs ~2.5×).** Review 1 speculated that
homogeneous cores would scale more evenly than the M3's performance/efficiency split; that
speculation is confirmed.

---

## 3. Two Review-1 measurement flaws

### 3.1 "Equal work" was not equal work (E3)

Review-1 speedup was measured with 2-opt **enabled**. 2-opt is first-improvement local search: its
cost depends on how good the tour already is, so two runs performing the same number of fitness
evaluations do not perform the same amount of work.

Measured correlation between tour length and wall-clock at fixed thread count: **+0.15 to +0.31**,
with a 6–8% time spread and 4.8% length spread. The effect is real and in the predicted direction,
though modest. Speedup is therefore measured with 2-opt off, where work per generation is fixed;
quality is measured separately under an equal wall-clock budget.

### 3.2 Speedup conflated parallelism with a cache effect (E1 vs E2)

The frozen engine hard-wires one island per thread, so `island_pop = P/T`. Raising T
simultaneously adds parallelism, changes the algorithm, and shrinks the per-thread working set
(240 individuals × 500 ints ≈ 480 KB overflows L2; 30 individuals ≈ 60 KB fits). `--islands`
decouples these. Because each island carries its own RNG stream keyed by island id, every thread
count now produces a **bit-identical search trajectory** — verified, not assumed — so wall-clock is
the only variable.

---

## 4. Where the time actually goes (E7, E8)

### 4.1 Synchronisation frequency (E7) — identical total work in every cell

| epoch length | 1 | 2 | 5 | 10 | 25 | 50 | 100 | 250 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| p = 1 | 11.04 | 7.37 | 5.16 | 4.40 | 3.94 | 3.77 | 3.70 | **3.63** |
| p = 4 | 3.80 | 3.12 | 2.05 | 1.67 | 1.46 | 1.38 | 1.34 | **1.31** |
| p = 8 | 4.50 | 2.76 | 1.67 | 1.36 | 1.08 | 1.02 | 0.99 | **0.91** |
| speedup p=8 | 2.45× | 2.67× | 3.09× | 3.24× | 3.64× | 3.70× | 3.74× | **4.00×** |

At p = 1 there are no barriers at all, yet time still falls 3×. **The dominant cost is per-epoch
serial bookkeeping — the diversity metric and the publish copies — not synchronisation.**
Synchronisation shows up separately in the scaling column (efficiency 0.31 → 0.50).

### 4.2 But longer epochs cost quality (E8) — equal 4 s budget, 8 seeds

uniform-500, no local search (median tour length; generations completed in italics):

| epoch length | 5 | 10 | 25 | 50 | 100 | 200 |
|---|--:|--:|--:|--:|--:|--:|
| island-fixed | **23949** | 30402 | 34254 | 30759 | 27967 | 28482 |
| *generations* | *5842* | *4855* | *4812* | *6800* | *9250* | *9800* |

clustered-600, no local search: 6828 → 9680 as epoch length goes 5 → 200 (**+42% worse**).
With 2-opt on, epoch length is nearly irrelevant (17099 → 17235, ~0.8%).

Longer epochs complete 68% more generations and still produce worse tours, because epoch length is
also the migration period and migration is load-bearing (§6). **The default epoch length stays at
10.** E7 in isolation would have justified raising it; measuring quality as well shows it is a
Pareto trade, not a free win. This pair of experiments is the clearest illustration in the project
of why a speed number without a quality number is not a result.

---

## 5. Engineering changes and what they actually bought

| Change | Effect | Verdict |
|---|---|---|
| Cache-line padding to remove false sharing | 0.92–0.99× (slightly slower) | **No gain.** Not the bottleneck. |
| Eliminating per-generation heap allocation | included above | **No gain.** Modern allocators use per-thread arenas. |
| Moving RNG to thread-local storage | 0.92–0.99× | **No gain.** Hypothesis tested and rejected. |
| **Bitset edge-set diversity metric** | **~6× on the metric; 1.11–1.16× end-to-end at the default epoch length**, bitwise-identical output | **Real gain.** |
| **Candidate-list 2-opt + don't-look bits** | **7.8–13.2× on the local search; 10–14× more generations completed** | **Largest gain.** |

The first three are the "textbook" HPC optimisations, and all three did nothing here: their
theoretical cost is real but negligible against ~15,000 operations of useful work per shared write.
Guessing at bottlenecks by pattern-matching does not pay; the epoch-length experiment is what
located the real one.

Micro-benchmark of the diversity metric (bitwise-exact, 225 random pairs across 9 sizes):

| population, n | hash-set reference | bitset | speedup |
|---|--:|--:|--:|
| 30, 500 | 709.7 ms | 113.3 ms | 6.27× |
| 240, 500 | 1312.4 ms | 219.2 ms | 5.99× |
| 30, 800 | 883.3 ms | 147.8 ms | 5.98× |

### 5.1 Candidate-list 2-opt (E9) — equal 3 s budget, 10 seeds, Wilcoxon signed-rank

| instance | mode | naive | fast | change | generations naive/fast | p |
|---|---|--:|--:|--:|--:|--:|
| uniform500 | fixed | 17285.3 | 16615.8 | **−3.9%** | 210 / 3015 | 0.0020 |
| uniform500 | dtam | 17248.5 | 16642.3 | −3.5% | 200 / 2695 | 0.0020 |
| clustered600 | fixed | 5340.8 | 5212.9 | −2.4% | 140 / 2525 | 0.0020 |
| clustered600 | dtam | 5343.8 | 5216.1 | −2.4% | 140 / 2070 | 0.0020 |
| kroA200 | fixed | 29499.0 | **29368.0** | −0.4% | 1255 / 8900 | 0.0020 |
| a280 | fixed | 2614.0 | **2579.0** | −1.3% | 640 / 9150 | 0.0078 |

Faster *and* better: don't-look-bit exhaustion converges further than the reference's fixed pass
cap. p = 0.0020 is the smallest value attainable with n = 10 paired samples.
Candidate-list size k = 8 chosen from a sweep (k = 5 loses 9.1% quality; k = 10 and 16 gain a
further 1% at higher build cost).

---

## 5A. Equal-wall-clock quality: parallel versus serial (E5)

Median tour length under an identical time budget, 12 seeds. This is the comparison a user of the
software actually cares about: given N seconds, which engine returns the better tour?

| landscape | 2-opt | serial | island-fixed | island-dtam | parallel vs serial |
|---|--:|--:|--:|--:|--:|
| clustered-600 | off | 27297.2 | 7100.1 | 7695.7 | **-74.0%** |
| uniform-500 | off | 67353.2 | 21046.2 | 21274.7 | **-68.8%** |
| clustered-600 | on | 5361.5 | 5320.9 | 5331.8 | -0.8% |
| uniform-500 | on | 17714.9 | 17280.9 | 17205.6 | -2.5% |

**The parallel advantage depends almost entirely on whether local search is enabled.** Without
2-opt the island engines find 68-74% shorter tours in the same wall-clock, because the serial GA
completes far fewer generations and has no repair mechanism. With 2-opt the advantage collapses to
0.8-2.5%, because the local search does most of the optimisation and keeps even the serial GA
competitive per generation.

Review 1 quoted the 60-67% figure without this qualification. The number is reproducible, but
quoting it without stating that it only holds with local search disabled overstates the benefit of
parallelism in the configuration anyone would actually run.

On TSPLIB instances (E6) with local search the engines are indistinguishable, because all three
reach the published optimum.

---

## 5B. Measurement metadata: how noisy was the machine?

These are the numbers behind the claim that the study is trustworthy, and they are not uniformly
flattering. Reported so the reader can judge rather than take it on faith.

**Thermal drift.** A fixed canary configuration is timed at the start of every round; the figure
below is the change in canary wall-clock from the first round to the last.

| experiment | canary drift | what it measures |
|---|--:|---|
| E1 strong scaling | **+45.1%** | the headline speedup numbers |
| E2 legacy protocol | -16.1% | protocol comparison |
| E3 2-opt confound | +33.2% | correlation only |
| E4 tau sweep | +30.9% | quality, not timing |
| E5 equal wall-clock | **0.0%** | quality under a fixed budget |
| E6 TSPLIB | **0.0%** | quality under a fixed budget |
| E7 epoch length | +41.0% | timing |

The drift on the timing experiments is large. This is a 15 W laptop part and the drift is real, so
it must not be waved away. Three things bound its effect on the conclusions:

1. **Repeats are scheduled round-robin** across the whole configuration list rather than
   back-to-back, so drift is spread across all configurations instead of concentrating in whichever
   one happened to run during a hot patch. It therefore adds noise rather than a systematic bias
   between the configurations being compared.
2. **The estimator is the minimum over all seed x repeat samples**, not the mean. Timing noise from
   throttling is one-directional: it only ever makes a run slower. The fastest observed run is the
   least contaminated estimate.
3. **The residual spread is measurable.** Coefficient of variation across repeats: E1 median 7.06%
   (max 13.56%), E7 median 1.05% (max 8.02%).

The honest statement is therefore: the machine drifted substantially during the timing experiments,
the protocol was designed to convert that drift into noise rather than bias, and the residual
per-configuration spread is single-digit percent. Differences smaller than roughly 5% in a timing
comparison on this machine should not be treated as meaningful. The scaling result (3.93x) and the
2-opt result (7.8-13.2x) are both far outside that band; the engine-rewrite result (1.11-1.16x) is
close to it, which is why it was confirmed separately with 9 tightly alternated repeats.

The two quality experiments that matter most for the conclusions, E5 and E6, recorded **0.0% drift**
because they are time-budgeted: every run takes the same wall-clock by construction.

**Time-to-target.** The harness records the time to reach a 5% gap. On the equal-work runs the
target was reached by **0 of 39** configurations in E1 and **0 of 75** in E2, because the equal-work
budget is too small to get within 5% of the reference. This metric therefore produced no usable
data and is not reported as a result. The quality-versus-wall-clock comparison in E5 conveys the
same information reliably.

---

## 6. The DTAM result — a sharper negative than Review 1's

**Review 1 concluded:** DTAM and fixed migration land within ~1% of each other; neither is
consistently better; migration policy is a second-order factor.

**Review 2 finds** that the "no difference" conclusion averaged over two protocols that point in
opposite directions, and that the mechanism never operated as designed.

### 6.1 The direction depends on which budget is held fixed

- **Equal work** (same generations): DTAM **8.6% better**, 3/3 seeds.
- **Equal wall-clock** (same seconds): DTAM **8.4% worse** on clustered-600, 1/12 wins,
  **p = 0.001**.

DTAM's migration decision costs ~30% throughput (2.24 s vs 1.72 s for identical generations), so a
fixed time budget gives the per-generation advantage back with interest. Review 1 measured only one
direction at a time and so saw neither effect.

### 6.2 Diversity collapses; the trigger never discriminates

Diversity logged every 10 generations, 8 islands of 30, uniform-500:

| generation | 10 | 130 | 250 | 370 | 610 | 730 | 1090 | 1450 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| diversity | 0.224 | 0.032 | 0.039 | 0.012 | 0.010 | 0.006 | 0.005 | 0.004 |

Whole run: min 0.0029, max 0.2236, **mean 0.0181**. Islands collapse to near-clones within ~100
generations. The condition is `diversity < τ`, so **τ = 0.15 sits far above the metric's entire
operating range and fires on 99.7% of island-epochs**. The τ sweep confirms it: trigger rates of
100 / 100 / 99.97 / 99.89 / 99.73 / 99.59 / 99.06 / 97.2 / 93.94 / 90.62 / 78.55% for
τ = 0.9 down to 0.01. Only τ = 0 stops migration, and that is far worse (46382 vs ~31000).

### 6.3 The novelty was never actually exercised

New instrumentation counts how often DTAM finds a genuinely non-stagnating donor, versus falling
through to its "most distant island overall" fallback. Across the 10-seed factorial:

**Stock DTAM finds a healthy donor on 0.3–0.6% of migrations.** On more than 99% of migrations the
distant-source-pull mechanism — the project's actual contribution — is not exercised as designed,
because every island has collapsed simultaneously and there is no healthy donor to pull from.

### 6.4 Rescue attempts (E10) — equal 3 s budget, 10 seeds, vs fixed migration

uniform-500, no local search (fixed-migration reference 21537.8):

| config | median | vs fixed | vs stock DTAM | donor found | trigger rate | p vs fixed |
|---|--:|--:|--:|--:|--:|--:|
| stock | 23438.0 | +8.8% | — | 0.5% | 99.8% | 0.0039 |
| heterogeneous | 22791.4 | +5.8% | **−2.8%** | 1.7% | 99.6% | 0.0020 |
| immigrants | 23182.7 | +7.6% | −1.1% | 1.5% | 99.4% | 0.0059 |
| het + immigrants | 22767.5 | +5.7% | **−2.9%** | 4.1% | 99.0% | 0.0371 |
| rel-trigger | 27744.5 | +28.8% | +18.4% | 100.0% | 31.4% | 0.0020 |
| het + rel | 27100.6 | +25.8% | +15.6% | 100.0% | 26.3% | 0.0020 |

clustered-600, no local search (reference 7173.6): stock +19.8%, heterogeneous +13.9%
(−4.9% vs stock), rel-trigger +41.9%.

With 2-opt on, **every configuration lands within ±0.3% of fixed migration** and essentially none
of the differences are significant.

### 6.5 What this means

1. **Heterogeneous island parameters help** — the only mechanism that consistently improves on
   stock DTAM (−2.8% uniform, −4.9% clustered), and it roughly triples donor availability. It does
   not close the gap to fixed migration.
2. **The relative trigger works exactly as designed, and that is what makes it worse.** It restores
   discrimination (99.8% → ~31% firing, donor availability → 100%) and quality drops 18–20%,
   because it suppresses migration. Migration is the dominant source of genetic material once
   islands collapse: turning it off entirely costs 33%.
3. **Therefore DTAM's core premise — "migrate only when stagnating" — is wrong for this problem.**
   The right policy here is to migrate constantly. This is now demonstrated mechanistically rather
   than asserted, and it is a stronger, more specific result than Review 1's "no difference".
4. **No configuration was found in which DTAM meaningfully beats fixed migration.** One cell
   (het+rel, clustered-600 with 2-opt) shows −0.2% at p = 0.0273, but with 24 comparisons in the
   table a Bonferroni-corrected threshold is 0.002, so this is not significant and must not be
   reported as a win.

---

## 7. Novelty, restated honestly

Diversity-driven and adaptive migration for island GAs is established prior work; this project does
not originate it. What survives Review 2:

1. **A specific policy design.** The combination of a stagnation trigger with distant-source *pull*
   selection chosen at runtime is self-implemented. Incremental, and presented as such.
2. **An HPC-framed evaluation that changed the answer.** Reporting speedup, efficiency, Karp–Flatt
   and Amdahl alongside quality is what exposed two Review-1 headline numbers as measurement
   artefacts, and what located the real bottleneck. A quality-only evaluation would have found
   neither.
3. **A cost-versus-quality framing the literature does not contain.** A survey of the adaptive-
   migration literature found no published work that measures the *runtime cost* of an adaptive
   migration decision; that literature compares quality at fixed generation counts. The result
   "8.6% better per generation, 8.4% worse per second" is exactly the trade-off that framing hides,
   and it is the most defensible novelty claim in the project.
4. **A mechanistically diagnosed negative result.** Donor-availability instrumentation shows the
   proposed mechanism fires as designed on under 1% of migrations. That is a more useful finding
   than a null result, because it identifies *why*, and it points at premature convergence rather
   than at the policy.

---

## 8. Known limitations

- Euclidean TSP only, one machine, one GA operator set.
- 4 physical cores; results at 6 and 8 threads use SMT, so efficiency past 4 is expected to fall.
- E1 timing uses 3 seeds. This is sound for timing (with 2-opt off every seed performs identical
  work) but the equal-work DTAM comparison rests on 3 pairs, where p = 0.25 is the best a Wilcoxon
  test can return. The equal-wall-clock comparisons use 10–12 seeds.
- `uniform` and `clustered` instances have no exact optimum; quality claims needing an exact
  reference use the TSPLIB instances.
- τ was swept on one instance family.
- Heterogeneous island parameters were tested at one spread (mutation 0.10–0.45, tournament 2–6);
  the spread itself was not tuned.
