# Viva / Defence Preparation

Six documents. Read them in this order the first time; use the table afterwards to jump.

| # | File | Read it for |
|---|---|---|
| 1 | `01-architecture-and-dataflow.md` | The system diagram, module dependencies, the per-epoch parallel data flow, and which file to open for which concern. |
| 2 | `02-how-it-works.md` | A top-down walkthrough: one run traced end to end, then each of the nine subsystems expanded, plus a 30-term glossary. |
| 3 | `03-novelty-and-defence.md` | **The most important file.** The novelty claim ladder, the hardest question and how to answer it, category-by-category model answers, traps to avoid, and 30 rehearsal questions. |
| 4 | `04-theory-explained.md` | Every theoretical concept in plain terms, then formally, then what it does here and its measured impact. Includes a formula sheet. |
| 5 | `05-plots-and-metrics.md` | Every figure and every metric: what is plotted, how to read it, what to infer, likely questions, and honest caveats. |
| 6 | `06-what-else-matters.md` | Organised by risk: what will trip you up, the self-corrections on record, limitations to volunteer, and what to do if the demo goes wrong. |

## The single source of truth

Every number in these documents comes from **`../../results/FINDINGS.md`**, which in turn is derived
from the raw `results/study_E*.csv`. If a number here disagrees with FINDINGS.md, FINDINGS.md wins
and the discrepancy is a bug worth reporting.

## If you only have twenty minutes

1. `06-what-else-matters.md` section 1 — the five sentences to memorise.
2. `03-novelty-and-defence.md` Part 2 — the hardest question, answered in four beats.
3. `03-novelty-and-defence.md` Part 9 — the thirty-second summary.
4. `06-what-else-matters.md` section 3 — the distinction between migration mattering and the
   migration *policy* mattering. This is the one a panel is most likely to blur.

## Three things to be ready to concede

Volunteering these costs nothing and buys credibility. Defending them after being caught costs a lot.

- **The proposed policy does not work.** No configuration was found where DTAM beats fixed
  migration. What the project contributes is the diagnosis: it finds a valid donor on 0.3-0.6% of
  migrations, so the mechanism never ran.
- **Two Review-1 headline numbers were measurement artefacts**, not properties of the algorithm.
- **The machine drifted during the timing experiments** (+45.1% canary drift across E1). The
  protocol converts drift into noise rather than bias, but the honest rule is that timing
  differences under about 5% on this machine are not meaningful.
