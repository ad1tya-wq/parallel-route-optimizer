# Novelty, and How to Defend It Under Questioning

Every number here is from `results/FINDINGS.md`. If a panel member asks where a figure comes from,
that file plus the raw `results/study_E*.csv` is the answer.

---

## Part 1 — The novelty, stated in the order you should say it

When asked "what is new here?", do **not** lead with DTAM. Lead with the evaluation. Here is the
claim ladder, strongest first.

### Claim 1 (strongest) — a cost-versus-quality framing the literature does not contain

The adaptive-migration literature compares migration policies on **solution quality at a fixed
generation count**. A survey conducted for this project found **no published work that measures the
runtime cost of the adaptive migration decision itself**.

That omission hides a real effect. Measured here:

| Protocol | Result |
|---|---|
| Equal work (same generations) | DTAM **8.6% better**, 3/3 seeds |
| Equal wall-clock (same seconds) | DTAM **8.4% worse**, 1/12 wins, **p = 0.001** |

The cause is measurable: DTAM's migration decision costs about **30% throughput** (2.24 s vs 1.72 s
for identical generations), so a fixed time budget gives the per-generation advantage back with
interest. **A quality-only evaluation cannot see this.** That is a methodological contribution, not
a hopeful one, and it is the thing to say first.

### Claim 2 — an HPC-framed evaluation that changed the answer

Reporting speedup, parallel efficiency, Karp–Flatt and Amdahl alongside tour quality is what
exposed **two Review-1 headline numbers as measurement artefacts** (Part 3 below), and what located
the real bottleneck. A quality-only evaluation would have found neither. This is a concrete
demonstration that the framing earns its keep, not an assertion that it does.

### Claim 3 — a mechanistically diagnosed negative result

New instrumentation counts how often a stagnating island finds a genuinely non-stagnating peer to
pull from, versus falling through to the "most distant island overall" fallback.

**Stock DTAM finds a healthy donor on 0.3–0.6% of migrations.** On more than 99% of migrations the
distant-source-pull mechanism — the actual contribution — is never exercised as designed, because
all eight islands collapse simultaneously.

That is a far more useful finding than "no significant difference", because it identifies *why*,
and it points at premature convergence rather than at the policy.

### Claim 4 (weakest, state it as incremental) — the policy design itself

DTAM couples a stagnation trigger computed from a concrete edge-set diversity metric with
**distant-source pull** selection chosen at runtime. Most prior schemes key the decision off the
target island's own diversity and/or a fixed topology. The combination is self-implemented.

**Say plainly: diversity-driven and adaptive migration for island GAs is established prior work and
this project does not claim to originate it.** Claiming otherwise is the single easiest way to lose
credibility, because the panel can find the prior work in thirty seconds.

---

## Part 2 — The hardest question, and the answer

> **"Your novelty doesn't work. You got a negative result. Why should this pass?"**

This is the question the whole viva turns on. Answer in four beats, in this order:

**Beat 1 — Concede immediately and precisely.**
"Correct. DTAM does not beat fixed migration in any configuration I tested. With local search
enabled every variant lands within ±0.3% of the baseline and none of it is significant."

**Beat 2 — Distinguish a null result from a diagnosed one.**
"Review 1 reported no difference and left it there. Review 2 shows the mechanism never actually
ran. The policy's defining step is 'pull migrants from the most different *non-stagnating* island'.
I instrumented that branch. It finds a non-stagnating donor on 0.3–0.6% of migrations. On 99%+ of
migrations every peer is also stagnant, so it falls through to a fallback that is not the proposed
policy at all. So this is not evidence that the idea is bad; it is evidence that the experiment
never tested the idea."

**Beat 3 — Show you then tested the fix.**
"I implemented three literature-backed mechanisms to break the synchronised collapse: heterogeneous
per-island parameters, a relative stagnation trigger, and random immigrants. Heterogeneity is the
only one that helps — 2.8% to 4.9% better than stock DTAM, and it roughly triples donor
availability — but it does not close the gap to fixed migration. The relative trigger works exactly
as designed, restoring discrimination from 99.8% firing down to 31%, and quality gets **18–20%
worse**, because it suppresses migration and migration is load-bearing here: turning migration off
entirely costs 33%."

**Beat 4 — State the conclusion the evidence actually supports.**
"So the finding is that DTAM's premise is wrong for this problem. 'Migrate only when stagnating' is
the wrong instinct on Euclidean TSP with these operators, because the islands are always stagnating
and migration is the only remaining source of genetic material. That is a specific, falsifiable,
mechanistically supported claim. It is a better outcome than a marginal win would have been,
because a marginal win at this sample size would not have been trustworthy."

**Do not** say "but it's self-tuning so it removes a hyperparameter." That was Review 1's fallback
and it does not survive: the relative-trigger experiment shows the tuning question just moves to
`rel_drop` and `rel_window`.

---

## Part 3 — Defending the change from Review 1

> **"Your Review-1 report said 2.5× speedup and 60–67% better tours. Now you say something else.
> Which is right, and why should we believe the new one?"**

Answer: "Both were measured correctly; the earlier one was measured with a flawed protocol. Here
are the two specific flaws."

### Flaw 1 — "equal work" was not equal work

Review-1 speedup was measured with 2-opt **enabled**. 2-opt is a first-improvement local search: it
sweeps until it finds no improving move, so **its cost depends on how good the tour already is**.
Two runs performing the same number of fitness evaluations therefore do not perform the same amount
of work.

Evidence: correlation between tour length and wall-clock at fixed thread count is **+0.15 to
+0.31**, with 6–8% time spread. Fix: speedup is measured with 2-opt off, where per-generation work
is fixed; quality is measured separately under an equal wall-clock budget.

If pressed on magnitude, be honest: "the effect is real and in the predicted direction, but modest —
6–8%, not a factor. I initially over-estimated it from a single unrepeated pair of runs and
corrected that after repeating the measurement."

### Flaw 2 — speedup conflated parallelism with a cache effect

The original engine hard-wires one island per thread, so `island_pop = P/T`. Raising T does three
things at once: adds parallelism, changes the algorithm (8 small islands search differently from 1
big one), and shrinks the per-thread working set. At P = 240 and n = 500 the serial population is
about **480 KB**, which overflows this CPU's L2; one island of 30 is about **60 KB**, which fits.
Effect three alone makes parallel runs faster per unit work, and folding it into "speedup" is how a
4-core machine produces an apparently super-linear number.

Fix: `--islands` decouples decomposition from thread count. Because each island carries its own RNG
stream keyed by island id, **every thread count now produces a bit-identical search trajectory** —
verified, not assumed — so wall-clock is the only variable.

### The line to close on

"The corrected numbers are smaller and defensible. The original ones were larger and not. On the
platform this project actually targets, the corrected speedup is **3.93× at 8 SMT threads on 4
physical cores**, with efficiency 0.83 at 4 threads."

---

## Part 4 — Anticipated questions by category, with model answers

### A. Novelty and contribution

**"Isn't this just a textbook island-model GA?"**
The island model is the vehicle, not the contribution. The three engines share one GA core
precisely so any measured difference is attributable to parallel structure or migration policy and
not to the search operators. The contribution is the migration policy plus an HPC-grade evaluation
of it, and the evaluation is what produced the findings.

**"What did you actually build versus what already existed?"**
See Part 6 on provenance. Answer it straight.

**"Your contribution is negative. What is the scientific value?"**
A correctly diagnosed negative result rules out a plausible design and explains why, which is
publishable in its own right. The donor-availability instrumentation is reusable by anyone
evaluating a conditional migration policy.

**"Has nobody measured migration overhead before?"**
The literature survey found none. State it as "I did not find any, and I looked" rather than "none
exists" — that is both honest and unfalsifiable in the room.

### B. Parallel computing (expect the most questions here)

**"3.93× on 8 threads is poor. Explain."**
The machine has **4 physical cores**; threads 5–8 are SMT siblings sharing execution resources, so
8× was never available. At 4 threads efficiency is 0.83, which is reasonable. The Amdahl fit gives
a serial fraction of 0.155 and a ceiling of 6.47×.

**"Why is p = 6 slower than p = 4?"** *(a trap question — get this right)*
Load imbalance from integer division. Islands are distributed with `schedule(static)`, so an epoch
costs `ceil(I/p)` island-units. With I = 8, p = 6 gives `ceil(8/6) = 2` — the same as p = 4 — and
p = 6 additionally contends for the same 4 physical cores. So p = 6 does the same number of
sequential island-units as p = 4 with more contention. Measuring against a linear ideal would
misreport integer division as poor scaling, so the analysis reports efficiency against the
load-balance ceiling as well: at p = 3 that reads 0.93 rather than 0.83.

**"What is your Karp–Flatt metric telling you?"**
That the limit is **overhead, not an inherent serial section**. The experimentally determined serial
fraction rises from 0.020 at p = 2 to 0.224 at p = 6. If a fixed serial section were the constraint,
e would be roughly constant. A rising e means synchronisation and memory effects grow with thread
count, which is an engineering problem rather than a law. This is the single most important
theoretical point in the project.

**"Where is the actual bottleneck?"**
Per-epoch serial bookkeeping, principally the diversity metric and the publish copies. The evidence
is the epoch-length experiment: at **one thread, where there are no barriers at all**, wall-clock
still falls from 11.04 s to 3.63 s as epoch length goes from 1 to 250, for identical total work.
Synchronisation shows up separately in the scaling — efficiency at 8 threads rises from 0.31 to
0.50 over the same range.

**"Did you eliminate false sharing?"**
Yes, and it made no difference: 0.92–0.99×. The same for eliminating per-generation heap allocation
and for moving the RNG to thread-local storage. All three are textbook optimisations and all three
did nothing here, because their theoretical cost is negligible against roughly 15,000 operations of
useful work per shared write. What did work was found by measurement, not by pattern-matching: a
bitset diversity metric (~6×, 1.11–1.16× end-to-end) and candidate-list 2-opt (7.8–13.2×).

**"Why OpenMP and not MPI or CUDA?"**
Migration exchanges a few tours per island per epoch — kilobytes. On shared memory that is a pointer
copy behind a barrier. The interesting cost here is synchronisation and cache behaviour, which is
what the study measures; MPI would add serialisation and network latency that would dominate and
obscure the effect being studied. For GPU: the inner operations are branch-heavy and irregular — OX
walks a permutation with a membership test, 2-opt does data-dependent segment reversals with early
exit, tournament selection is a random gather. That is a poor fit for SIMT because of warp
divergence. A GPU version would be a different algorithm (fine-grained or cellular GA), not a port.

**"Is your code race-free? Prove it."**
During an epoch each thread touches only its own island's data. Publication happens before an
implicit barrier; migration reads peers' published slots and writes only its own island; the
bookkeeping block is `omp single`. The `omp for` implicit exit barriers order publish-before-read
and migrate-before-next-epoch. Independent evidence: the engine is **bit-identical across thread
counts and across repeated runs**, which a data race would break.

**"A laptop is not HPC hardware."**
Agreed, and it is stated as a limitation. The project's stated target platform is a 4-core mobile
i5, and the contribution is methodological rather than a scalability record. The thermal-drift
canary, repeat scheduling and min-over-samples estimator exist specifically because the platform is
noisy.

**Be honest about the magnitude if pressed.** The canary recorded **+45.1% drift across the E1
timing run** and +41.0% on E7. That is large and should not be waved away. What bounds its effect:
repeats are scheduled round-robin across the whole configuration list rather than back to back, so
drift acts as noise rather than as a bias between the configurations being compared; and the
estimator is the minimum over all samples, because throttling noise is one-directional and only
ever makes a run slower. The residual spread is a **7.06% median coefficient of variation** in E1.
The rule that follows is that **timing differences under about 5% on this machine are not
meaningful**. The 3.93x scaling result and the 7.8-13.2x local-search result are far outside that
band; the 1.11-1.16x engine-rewrite result is close to it, which is exactly why it was re-confirmed
separately with nine tightly alternated repeats rather than trusted from the main sweep. The two
experiments carrying the quality conclusions, E5 and E6, recorded **0.0% drift** because they are
time-budgeted by construction.

### C. Algorithm and correctness

**"How do you know the solver is correct?"**
Three independent checks. (1) The `circle` instance has a closed-form optimum `n·2R·sin(π/n)`,
reached at 0.00% gap, and this runs as a build gate. (2) **All seven TSPLIB instances reach their
published optimum exactly** — berlin52 7542, eil51 426, st70 675, kroA100 21282, ch150 6528,
kroA200 29368, a280 2579. These are externally verifiable. (3) `--validate` checks every returned
tour is a genuine permutation and that its reported length matches an independent recomputation;
all 1600+ measured configurations passed.

**"Population 240 across 8 islands is only 30 per island. Isn't that too small?"**
Probably yes, and it is listed as a limitation. It is also the direct cause of the observed
pathology: islands of 30 collapse to near-clones within about 100 generations. The parameters were
inherited from Review 1 and held fixed so that Review 2 measures the same system; changing them
would have confounded the comparison. Redistributing the same total population into fewer, larger
islands is named as future work.

**"Why τ = 0.15?"**
It was inherited from Review 1 and it is badly chosen — that is a finding. Diversity collapses into
the 0.003–0.05 band, so τ = 0.15 sits above the metric's entire operating range and fires on 99.7%
of island-epochs. The sweep from 0.9 down to 0.01 gives trigger rates of 100% down to only 78.55%.
An absolute threshold is the wrong instrument; a relative one was implemented and tested.

**"Why 8 islands?"**
To match the 8 hardware threads, and then held fixed while sweeping threads so the two effects
could be separated. The `ceil(I/p)` load-imbalance result is a direct consequence and is reported
rather than hidden.

**"Is the 2-opt improvement really yours, or standard?"**
Standard, and cited: neighbour lists and don't-look bits are Bentley (1992), used in essentially all
high-quality TSP codes. The contribution is applying and measuring it here: 7.8–13.2× faster **and**
2.4–3.9% better tours at equal wall-clock, p = 0.0020, which moved three TSPLIB instances from
near-optimal to exactly optimal. Claiming the technique as novel would be false.

### D. Statistics and method

**"How many seeds, and is that enough?"**
Timing uses 3 seeds with 4 repeats, which is sound because with 2-opt off every seed performs
**identical work** — they are repeated measurements of one workload, so the estimator is the minimum
over all samples. Quality comparisons use 10–12 seeds with paired Wilcoxon signed-rank tests. The
equal-work DTAM comparison rests on only 3 pairs, where p = 0.25 is the best the test can return; I
report that as directional, not significant.

**"You have a p = 0.0273 result. Is that not significant?"**
No. There are 24 comparisons in that table, so the Bonferroni-corrected threshold is 0.05/24 =
0.002. That cell is a −0.2% difference and I explicitly decline to report it as a win. Volunteering
this before being asked is worth more than defending it.

**"Why Wilcoxon rather than a t-test?"**
Paired because both policies see the same seed, so the pairing removes seed-to-seed variance;
non-parametric because tour lengths are not normally distributed and the sample is small. Note that
p = 0.0020 is the **floor** for n = 10 paired samples, so several results are at the strongest value
the test can express.

**"Why the minimum rather than the mean of repeated timings?"**
Timing noise on a thermally throttled laptop is essentially additive — interrupts, scheduler
migrations, frequency dips only ever make a run slower. The fastest observed run is therefore the
closest estimate of true throughput. A mean would fold in the noise; the median would partially.
The coefficient of variation is reported alongside so the spread is visible.

**"How do you know thermal throttling did not corrupt your results?"**
A fixed canary configuration is timed at the start of every round, and repeats are scheduled
round-robin across the whole configuration list rather than back-to-back, so drift spreads evenly
instead of concentrating in whichever configuration ran during a hot patch. Drift is reported per
experiment: +3.4% on the headline scaling run and 0.0% on both quality runs.

---

## Part 5 — Questions you should hope for

These let you show depth. Have the answers ready.

1. "What surprised you most?" — That the textbook optimisations did nothing while a 30-line change
   to the diversity metric gave 6×. It taught me to locate bottlenecks by measurement rather than
   by pattern-matching.
2. "What would you do differently with more time?" — Larger islands (the collapse is a
   population-sizing problem), a proper Or-opt or Lin–Kernighan local search, and a distributed-memory
   version where migration cost is real and DTAM's reduced migration frequency might finally pay.
3. "What is the weakest part of this project?" — The sample size on the equal-work DTAM comparison,
   and that the heterogeneity spread was never itself tuned. Naming your own weakest point before
   the panel does is the strongest move available.
4. "If you had to defend one number, which?" — 3.93× speedup, because it is reproducible from
   `results/study_E1.csv` with one command, was measured with a protocol whose confounds are
   documented, and every run behind it passed tour validation.
5. "What does the epoch-length pair of experiments teach?" — That a speed number without a quality
   number is not a result. E7 alone would have justified raising the default epoch length for a 3×
   gain; E8 shows quality degrades by up to 42% because epoch length is also the migration period.
   The default was left unchanged.

---

## Part 6 — The provenance question, handled honestly

You will likely be asked some version of **"did you write this?"**, especially since the repository
is a fork.

Be straightforward. The defensible and accurate position is:

- The Review-1 implementation was produced with AI assistance, and the repository was originally
  created under a collaborator's account; this fork is yours and the GitHub fork banner shows the
  upstream, so nothing is concealed.
- The Review-2 work — the methodology audit, the two flaw findings, the corrected measurement
  protocol, the instrumentation, the candidate-list 2-opt and bitset-diversity integration, and the
  full experimental study — is what you are being examined on, and it is documented commit by commit
  with the raw data to back it.

Do not claim sole unaided authorship of the original implementation. It is easy to check, the fork
relationship is visible in the repository, and being caught overstating it would damage you far more
than the admission costs. The honest framing is also the stronger one: *auditing a system, finding
that two of its headline numbers were measurement artefacts, and correcting them* is a more mature
piece of engineering work than having typed the original code.

If asked what you personally understand, the answer is demonstrated by the fact that you can explain
why p = 6 is slower than p = 4, why Karp–Flatt rising matters, and why the donor-availability
counter is the key diagnostic. Those are the things that show comprehension.

---

## Part 7 — Traps to avoid

| Trap | Why it hurts | Say instead |
|---|---|---|
| "DTAM is better, it just needs tuning" | The τ sweep and the E10 factorial both refute it | "DTAM's premise is wrong for this problem, and here is the mechanism" |
| "We got 5.9× speedup on 4 cores" | Super-linear on 4 cores invites an immediate attack; it was a cache artefact | "3.93× at 8 SMT threads, 0.83 efficiency at 4" |
| "Diversity stays high so the trigger never fires" | Backwards, and the trace disproves it | "Diversity collapses to 0.003–0.01, so the trigger is always on" |
| "The migration policy doesn't matter" | Overreach: migration matters enormously (33%); the *policy* is what is second-order | "Migration is load-bearing; the policy choice is second-order" |
| "It's novel because it's adaptive" | Adaptive migration is well-established prior work | "The novelty is the cost-versus-quality framing and the diagnosis" |
| Quoting Review-1 numbers from memory | They are superseded and inconsistent with the new report | Quote from `results/FINDINGS.md` |
| Claiming statistical significance loosely | The p = 0.0273 cell fails Bonferroni | "Not significant after correcting for 24 comparisons" |

---

## Part 8 — Thirty sample questions for rehearsal

Rapid-fire. Aim to answer each in under 45 seconds.

**Conceptual**
1. Define the island model and say why it parallelises well.
2. What is an epoch, and what two independent things does epoch length control here?
3. What is premature convergence and how did you detect it?
4. Why must TSP crossover be permutation-safe? What breaks with one-point crossover?
5. How many undirected edges does a segment-inversion mutation change, and why does that matter?
6. What is a memetic algorithm?
7. Define parallel efficiency and state yours at 4 threads.
8. State Amdahl's law and your fitted serial fraction.
9. What does the Karp–Flatt metric measure, and what does a *rising* value mean?
10. Distinguish strong scaling from weak scaling. Which did you measure?

**Design**
11. Why is the RNG keyed to the island rather than the thread?
12. Why keep `island.hpp` frozen instead of just editing it?
13. Why does `--islands` exist?
14. Why is `IslandSlot` declared `alignas(64)`?
15. Why did you *revert* the "remove the redundant sort" optimisation?
16. Why are there two separate fairness protocols?
17. Why is 2-opt gated by a probability rather than applied to every child?
18. What does `--validate` check, and why is checking the length not enough on its own?

**Results**
19. Why is p = 6 slower than p = 4?
20. Which optimisations produced no gain, and why do you think that is?
21. What is donor availability and what is its measured value?
22. Why did the relative trigger make quality worse?
23. Why did you not raise the default epoch length after E7?
24. Which is better, DTAM or fixed migration? Under which protocol?
25. What changed when you enabled candidate-list 2-opt on the TSPLIB set?

**Method and critique**
26. Why the minimum of repeated timings rather than the mean?
27. How did you control for thermal throttling?
28. Why is p = 0.0020 appearing repeatedly rather than smaller values?
29. Why is one p = 0.0273 result not evidence of an improvement?
30. What is the weakest claim in your report, and how would you strengthen it?

---

## Part 9 — The thirty-second summary, memorised

> "I re-measured an island-model genetic algorithm for TSP on the Intel i5 the original report named
> as its target but never used. Two of its headline numbers turned out to be measurement artefacts:
> speedup had been measured with a local search whose cost depends on solution quality, and with
> island count tied to thread count so a cache effect was being counted as parallel speedup. After
> correcting both, the speedup is 3.93× at 8 SMT threads on 4 physical cores, with efficiency 0.83
> at 4 threads and a Karp–Flatt trend showing the limit is overhead rather than a serial section.
> The proposed migration policy does not beat the baseline, and I instrumented why: it finds a valid
> donor on under 1% of migrations because all islands collapse together, so the mechanism never
> actually runs. Along the way, candidate-list 2-opt made the solver 7.8–13.2× faster and good
> enough to hit the published optimum on all seven TSPLIB instances tested."
