# What Else Matters: The Things That Are Easy to Miss

Everything else in this folder is organised by topic. This file is organised by **risk** — what is
most likely to trip you up, in rough order of how badly it would hurt.

All numbers trace to `results/FINDINGS.md`.

---

## 1. The five sentences to have memorised

If you remember nothing else:

1. **"Diversity collapses from 0.22 to 0.003 within about 100 generations, so τ = 0.15 fires on
   99.7% of island-epochs."** — the mechanism behind the whole DTAM result.
2. **"Stock DTAM finds a genuinely non-stagnating donor on 0.3–0.6% of migrations."** — the key
   diagnostic number.
3. **"3.93× at 8 SMT threads on 4 physical cores; efficiency 0.83 at 4 threads; Amdahl f = 0.155."**
   — the headline HPC result.
4. **"Karp–Flatt rises from 0.020 at p = 2 to 0.224 at p = 6, so the limit is overhead, not a serial
   section."** — the most important theoretical point.
5. **"At one thread, where there are no barriers at all, longer epochs still cut runtime from
   11.04 s to 3.63 s."** — the evidence that located the real bottleneck.

---

## 2. Three self-corrections that are in the record

These are documented in the repository. If you present the work as flawless and a panel member finds
one of them, it looks like concealment. Presented voluntarily, they look like rigour.

### 2.1 The diversity direction was initially stated backwards

During the audit the claim was made that islands stay *too diverse* for the trigger to discriminate.
The measured trace shows the opposite: islands are *permanently converged*. Recorded in
`report/research/_ERRATUM.md`, which also marks which literature conclusions that premise voided.

**If asked:** "One of my intermediate analyses had the direction wrong. I logged the diversity
trace directly, found it collapses rather than persists, corrected it, and recorded the error and
its consequences rather than quietly fixing it."

### 2.2 The 2-opt confound was initially over-estimated

An early inference put the equal-work confound at about 2×, from a single unrepeated pair of runs.
Repeated measurement showed it is **6–8%**. The 2× was thermal noise on a 15 W laptop part.

**If asked:** "That is exactly why the harness now uses repeats, round-robin scheduling and a
thermal canary. I made the mistake the harness was later built to prevent."

### 2.3 An optimisation was implemented, measured, and reverted

Removing the apparently redundant entry sort in `step_generation` looked like free speed. It is not:
`sort_population` orders by tour length only, so equal-length individuals are not totally ordered
and `std::sort` breaks those ties arbitrarily. Elitism and migration both create exact-duplicate
lengths, so sorting once instead of twice permutes the tied individuals differently, changing which
parents tournament selection picks. The engines diverged within about 15 generations.

`tests/test_equiv.cpp` caught it. The change was reverted and the reason documented in `ga.hpp`.

**Why this is worth volunteering:** it is a perfect example of an optimisation that is silently
*semantics-changing* rather than merely fast, which is a real hazard in stochastic search code. It
also demonstrates the differential tests are doing genuine work rather than decorating the repo.

---

## 3. The distinction the panel will most likely blur

**Migration matters enormously. The migration *policy* is second-order.** These are different
claims and conflating them is the easiest way to look like you have not understood your own result.

| Statement | Status | Evidence |
|---|---|---|
| Migration is important | **True and large** | Disabling it entirely: 46382 vs ~31000, roughly 33% worse |
| The island model beats serial | **True, but only without local search** | 68–74% better without 2-opt; **0.8–2.5%** with it |
| DTAM beats fixed migration | **False** | No configuration found; ±0.3% with local search, worse without |
| The trigger idea is untested | **True** | Donor availability 0.3–0.6% |

If someone says "so migration doesn't help", correct them: migration helps a great deal; choosing
*which peer* to migrate from is what does not.

---

## 4. The result most likely to be attacked as weak

**"The island model only beats serial by 0.8–2.5% once you enable local search."**

This is true and it is in the report. The full table, equal 4 s budget, 12 seeds:

| landscape | 2-opt | serial | island-fixed | island-dtam | parallel vs serial |
|---|--:|--:|--:|--:|--:|
| clustered-600 | off | 27297.2 | 7100.1 | 7695.7 | **−74.0%** |
| uniform-500 | off | 67353.2 | 21046.2 | 21274.7 | **−68.8%** |
| clustered-600 | on | 5361.5 | 5320.9 | 5331.8 | −0.8% |
| uniform-500 | on | 17714.9 | 17280.9 | 17205.6 | −2.5% |

Do not hide from it. The framing:

"With strong local search, 2-opt does most of the optimisation and keeps even the serial GA
competitive per generation, so the population-level search matters less. Without local search the
island engines are 68–74% better. That is a statement about where the parallel advantage comes from,
and it is exactly the kind of interaction a quality-only evaluation at one setting would miss. It
also means that if your goal is the best tour per second, the highest-value change is a better local
search — which is what candidate-list 2-opt delivered: 7.8–13.2× faster and enough to reach the
published optimum on all seven TSPLIB instances."

Turning the weak result into the motivation for the strongest one is the right move here.

---

## 5. What "1600+ configurations" actually means

Be able to break it down if challenged, because a vague large number invites scepticism.

| Experiment | Question | Scale |
|---|---|---|
| E1 | Strong scaling, islands fixed | 39 configs × 4 repeats |
| E2 | Original protocol, islands = threads | 75 configs × 4 repeats |
| E3 | Does 2-opt break equal work? | 60 configs × 3 repeats |
| E4 | τ sweep and trigger rate | 104 configs × 2 repeats |
| E5 | Equal wall-clock quality | 144 configs |
| E6 | TSPLIB with published optima | 252 configs |
| E7 | Synchronisation frequency | 48 configs × 3 repeats |
| E8 | Epoch length vs quality | 384 runs |
| E9 / E10 | Fast 2-opt; DTAM factorial | 620 runs |

**Every one validated. Zero validation failures.** That last sentence is worth saying.

---

## 6. Reproducibility — the thing that makes all of it defensible

If a panel doubts a number, the answer is a command, not an argument.

```powershell
.\build.ps1                                # builds, then self-tests against a closed-form optimum
python bench\run_study.py                  # E1-E7
python bench\exp_epoch_quality.py          # E8
python bench\exp_review2_extensions.py     # E9, E10
python bench\analyze_study.py              # derived tables and figures
python bench\plot_review2.py               # figures for E7-E10
```

Three properties worth stating explicitly:

1. **Bit-identical across thread counts.** Because each island owns an RNG stream keyed by island
   id, a given seed produces the same tours at 1, 2, 4 or 8 threads. Only wall-clock varies. This is
   what makes the speedup study a controlled experiment rather than a comparison of different
   searches.
2. **Bit-identical between engines.** `--engine opt` reproduces the frozen `--engine baseline`
   exactly, asserted by two differential tests. So any timing difference is engineering, not a
   different algorithm.
3. **The binary is statically linked.** It runs on a machine with no MSYS2 installed, so a
   demonstration cannot fail on a missing DLL.

**Practical advice:** if you demo live, run the TSPLIB check. It takes three seconds per instance
and produces `gap=0.00%` against an externally published optimum, which is the single most
convincing thing you can show.

---

## 7. Limitations to volunteer before you are asked

Naming your own limitations first is worth more than defending them later.

- **One machine, one architecture.** A 15 W 4-core mobile part. No claim about scalability beyond it.
- **The machine drifted during the timing experiments.** The canary recorded +45.1% across E1 and
  +41.0% across E7. Round-robin scheduling and a min-over-samples estimator convert that into noise
  rather than bias, and the residual coefficient of variation is 7.06% (median, E1) — but the
  practical consequence is that **timing differences under about 5% on this machine are not
  meaningful**. E5 and E6, which carry the quality conclusions, recorded 0.0% drift because they
  are time-budgeted.
- **Time-to-target produced no data.** The 5% gap target was reached by 0 of 39 configurations in
  E1 and 0 of 75 in E2, so the metric is reported as unusable rather than as a result.
- **Small populations.** 240 total, 30 per island. This is likely undersized for a 500-city instance
  and is the direct cause of the collapse. Inherited from Review 1 and held fixed deliberately so
  the comparison stayed controlled.
- **Euclidean TSP only**, with one operator set (tournament / OX / inversion / bounded 2-opt).
- **Sample sizes vary by experiment.** Timing uses 3 seeds (defensible: identical work per seed);
  quality uses 10–12. The equal-work DTAM comparison rests on 3 pairs and is reported as
  directional, not significant.
- **The heterogeneity spread was never tuned.** Mutation 0.10–0.45 and tournament 2–6 were chosen
  once, not optimised.
- **τ was swept on one instance family.**
- **`uniform` and `clustered` have no exact optimum.** The uniform reference is the
  Beardwood–Halton–Hammersley asymptotic estimate, so a "gap" against it is approximate and can be
  negative. Claims needing an exact reference use TSPLIB.

---

## 8. If the demo goes wrong

- **Numbers differ from the report.** Expected on a laptop: thermal state, background processes and
  turbo behaviour all move wall-clock. The *quality* numbers are deterministic per seed and will
  match exactly. Say so before running, not after.
- **Something fails to build.** `build.ps1` locates the compiler itself and links statically;
  `make test` runs all four suites. If the toolchain is missing entirely, the committed
  `results/study_E*.csv` files are the evidence and predate the demo.
- **Asked to change a parameter live.** Safe and fast: `--islands`, `--threads`, `--tau`,
  `--epoch-len`, `--twoopt-fast`, `--heterogeneous`, `--rel-trigger`. Use `--validate` every time so
  the output carries its own correctness proof.
- **Asked for something not measured.** Say it was not measured. Inventing a number in the room is
  unrecoverable; "I did not test that, and here is what I would run" is fine.

---

## 9. The one-line answers to the five most likely opening questions

| Question | Answer |
|---|---|
| "What is this project?" | A parallel island-model GA for TSP, evaluated as an HPC problem — speedup, efficiency, Karp–Flatt and Amdahl alongside tour quality. |
| "What is new?" | A cost-versus-quality framing the migration literature does not contain, and an HPC evaluation that exposed two of the earlier report's headline numbers as measurement artefacts. |
| "What is your main result?" | 3.93× at 8 SMT threads on 4 physical cores, and a mechanistically diagnosed negative result for the proposed migration policy. |
| "Did your idea work?" | No, and I instrumented exactly why: it finds a valid donor on under 1% of migrations, so the mechanism never actually ran. |
| "What did you learn?" | That bottlenecks must be located by measurement. Three textbook optimisations gave nothing; the two that worked were found by an experiment that isolated per-epoch cost. |

---

## 10. Framing the whole thing

The strongest available framing of this project is **not** "I designed a new migration policy."
It is:

> "I took a system that reported a set of performance claims, audited how those claims were
> measured, found that two of them were artefacts of the measurement protocol rather than properties
> of the algorithm, corrected the protocol, re-measured on the hardware the system actually targets,
> and in the process found that the system's own novel mechanism was never being exercised. Then I
> made the solver an order of magnitude faster using a technique from the literature, and verified
> the result against externally published optima."

That is a description of engineering maturity rather than of a lucky result, and it is what the
evidence in this repository actually supports.
