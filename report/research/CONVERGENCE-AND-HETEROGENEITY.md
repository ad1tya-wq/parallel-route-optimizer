# Convergence Collapse and Heterogeneity in Island-Model GAs for TSP — Literature Evidence Report

Prepared for the parallel-route-optimizer project. System under study: C++/OpenMP island-model GA,
Euclidean TSP (n = 500–800), 8 islands × 30 individuals (total 240), tournament k=4, OX crossover,
segment-inversion mutation p=0.25, elitism 1, bounded 2-opt on 20% of children. Comparing "fixed"
ring migration against "DTAM" (diversity-triggered, pull-based migration from the most different
non-stagnating island).

Measured ground truth: mean edge-distance-to-own-best diversity collapses from 0.22 (gen 10) to
the 0.003–0.05 band by gen 130 and stays there through gen 1500 (min 0.0029, max 0.2236 including
the initial transient, mean 0.0181). At tau=0.15 the stagnation trigger fires on 99.7% of
island-epochs; only tau≈0.01 discriminates at all (78.6% trigger rate). With migration disabled,
final tour length is 46382 vs. ~31000–32000 with migration enabled.

---

## Summary

- [strong evidence] Total population 240 for a 500–800 city permutation TSP is small relative to
  populations commonly reported in the island-GA-for-TSP literature, which more often uses
  populations in the several-hundred-to-low-thousands range, though direct "minimum viable size"
  guidance specific to permutation TSP is thin (Q1).
- [weak evidence] Classical GA population-sizing theory (Goldberg/Deb/Clark noise-based sizing;
  Harik–Cantú-Paz–Goldberg–Miller gambler's-ruin sizing) was derived for schema/building-block
  competition on bitstring problems, not permutation/edge-based representations — applying it
  quantitatively to OX/TSP is an extrapolation, but the qualitative message (population must scale
  with problem size and difficulty, and per-deme size in parallel GAs has a floor below which
  correct building-block decisions fail) is directly on point (Q1).
- [strong evidence] Homogeneous island models are documented to suffer from "homogenization" —
  islands converging to similar / identical solutions after enough generations, undermining the
  diversity benefit the island structure is supposed to provide (Q2).
- [strong evidence] Migration topology materially changes whether islands stay correlated: sparse,
  large-diameter topologies (ring, chain) slow propagation of a dominant genotype and preserve
  diversity longer than dense topologies (complete/hypercube), which accelerate homogenization
  (Q2).
- [strong evidence, but not TSP-specific] Heterogeneous-parameter island models (different
  mutation/crossover rates, different population sizes per island) are a published, named research
  direction with a positive result: randomly assigning heterogeneous control-parameter settings
  across islands performed competitively with per-problem hand-tuned homogeneous settings, at much
  lower tuning cost (Q2 — highest priority question).
- [strong evidence] Diversity-triggered / diversity-probability-gated migration for TSP has direct
  precedent and a reported quantitative advantage over interval-only migration, specifically on
  harder TSP instances, when the trigger is coupled to migration probability rather than to a hard
  on/off threshold on a saturating metric (Q4/Q5).
- [strong evidence] Random immigrants and other explicit diversity-injection mechanisms are
  documented, well-established, cheap countermeasures to the exact "population converges to
  near-clones" pathology measured here (Q3).
- [strong evidence] Deterministic crowding / fitness-sharing niching techniques are a documented,
  older but effective diversity-preservation family, with known interaction costs (extra pairwise
  comparisons; can antagonize elitism and local search by repeatedly replacing near-identical elites)
  (Q3).
- [strong evidence] Stagnation/restart criteria used in the literature are dominantly "no
  improvement in best fitness for W generations" and relative/ratio-based diversity or
  fitness-variance criteria, not raw absolute thresholds on a metric whose dynamic range is unknown
  a priori — which is exactly the failure mode diagnosed in this project's tau=0.15 setting (Q4).
- [weak evidence] Edge-frequency entropy and high-order (Markov-model) entropy measures for TSP
  permutation populations are documented as more discriminating diversity measures than a single
  mean-distance-to-best statistic, though no source found gives a head-to-head numeric comparison
  of "distance-to-own-best" vs. "distinct-individual count" vs. entropy on the same run (Q4).
- [unverified] No source found gives a controlled, TSP-specific, head-to-head experiment showing
  diversity-triggered pull migration beating fixed periodic migration under exactly this project's
  island count (8) and island size (30); the claimed mechanism (better donor selection when
  triggered rarely and correctly) is only demonstrated at larger island counts / different problem
  domains, so its benefit at n=8, size=30 is a plausible but untested extrapolation for this
  project (Q5).
- [strong evidence] The project's own measurement — 46382 (no migration) vs. ~31000–32000 (with
  migration) — is internally consistent with the general parallel-GA finding that once
  subpopulations collapse, migration is the dominant remaining source of genetic novelty; this is
  not something the literature searched here disputes, but the specific numbers are the project's
  own unverified-by-us empirical result, not a published citation.

---

## Q1 — Is 30 individuals per island simply too small?

### What island-GA-for-TSP papers actually use

Concrete, verifiable examples of population/island parameters found in the island-GA-for-TSP
literature:

- Gong & Fukunaga, "Distributed island-model genetic algorithms using heterogeneous parameter
  settings," CEC 2011 [2] — a heterogeneous-parameter distributed GA framework tested on standard
  GA benchmark functions and combinatorial problems using multiple islands with per-island
  population sizes on the order of tens to ~100 individuals, run on tens of processors; exact
  per-instance TSP sizes were not extractable from the accessible copies of this paper in this
  session (PDF text extraction failed; see Limitations). Cited here for the heterogeneous-parameter
  methodology (Q2), with population-size specifics marked unverified.
- Varadarajan et al., "A Parallel Ensemble Genetic Algorithm for the Traveling Salesman Problem,"
  GECCO 2021, pp. 636–643, DOI 10.1145/3449639.3459281 [3] — an ensemble of parallel GA solvers
  applied to TSP; this is a genuine, verifiable published island/ensemble-GA-for-TSP paper at
  GECCO, but this session could not extract the specific population-size / island-count numbers
  from the available PDF (text layer did not decode). Existence and venue are verified; internal
  parameter values are marked unverified.
- Whitley, Rana & Heckendorn, "The Island Model Genetic Algorithm: On Separability, Population
  Size and Convergence," Journal of Computing and Information Technology (CIT), vol. 7, no. 1,
  1999, pp. 33–47 [1] — a theoretical (infinite-population-model) analysis, not an empirical
  parameter table, so it does not report concrete island sizes, but it is the foundational
  reference arguing that island models help preserve diversity because each island can follow a
  distinct search trajectory, and that this benefit interacts with problem separability and
  (implicitly) with deme size — a deme that is too small loses this benefit because a single
  trajectory dominates it almost immediately. This matches the measured collapse-by-generation-130
  behavior in this project directly.
- Holtschulte, "Optimal Population Size in Island Model Genetic Algorithms," UNM CS graduate
  symposium paper, 2012 [4] — empirically studies the relationship between total population size,
  island count, migration interval and migration size across benchmark problems, finding a point of
  diminishing returns beyond which added individuals do not improve results, and that moderate
  migration intervals with small migration size preserved diversity best. This session could not
  extract the exact numeric island sizes used per benchmark from the PDF (text extraction failed);
  the qualitative "diminishing returns" finding and its plausibility test size choice, however, are
  a valid published data point. Numbers marked unverified pending manual PDF read.

### Assessment

Is total population 240 for 500–800 cities unusually small? The literature searched in this
session does not converge on one canonical number, but several signals point toward "on the small
side, plausibly too small":

- The project's own measured pathology — diversity collapse to a 0.3–1% edge-distance band within
  ~100 generations, with the population becoming effectively a set of near-clones — is the textbook
  symptom of a deme that is too small to sustain multiple competing schemata/building blocks, which
  is precisely the phenomenon Goldberg/Deb/Clark's noise-based population-sizing model [5] and the
  Harik–Cantú-Paz–Goldberg–Miller gambler's-ruin population-sizing model [6][7] were built to
  predict for bitstring GAs: population size must scale with the number of building blocks, their
  fitness variance ("collateral noise"), and the desired probability of correctly resolving each
  building-block competition. Neither model was derived for order-based (OX/permutation)
  representations, so applying their formulas numerically to a 500–800-city TSP is an
  extrapolation, not a verified transfer — but the qualitative implication (30 individuals gives
  very little statistical power to resolve competition among the many partial-tour "building
  blocks" of a 500+ city instance) is consistent with both theory and the measured collapse.
- Cantú-Paz's parallel-GA extension of this theory [7][8] explicitly treats deme size in
  multi-population GAs as a free parameter trading off per-deme solution quality against
  parallelism/communication cost, and shows there is a deme-size floor below which per-deme
  convergence quality degrades faster than migration can repair — again consistent with, but not a
  numeric confirmation of, the collapse observed here at 30/deme.
- Practical island-GA-for-TSP papers found in this search generally do not report island sizes as
  small as 30 for instances in the 500–800 city range (where numbers were extractable), though this
  session was unable to pin down exact per-paper numbers for several of the most relevant hits due
  to PDF extraction failures (marked unverified above). This should be treated as directional, not
  conclusive.

**Verdict:** [weak evidence, leaning toward "too small"] — the diagnosis is consistent with
established population-sizing theory's mechanism (insufficient statistical resolving power per
deme) and with the project's own measured collapse timing, but no source in this search gives a
number that says "30 is provably insufficient for 500–800-city OX-TSP." This should be tested
directly and cheaply (see experiment plan).

---

## Q2 — Synchronised/correlated convergence across islands; heterogeneous island models (HIGHEST PRIORITY)

### Is synchronized convergence documented?

Yes. Multiple sources describe the phenomenon by name ("homogenization"): after enough generations,
different islands in a homogeneous island model retain similar, converged subpopulations, so
"while each island itself can have a diverse population, the lack of diversity between the islands
themselves results [in] the islands converging and potentially missing areas where the global
optima could reside" [9][10]. This is exactly what defeats the DTAM design in this project: because
all 8 islands collapse at roughly the same time (all running identical operators, identical rates,
identical selection pressure), the "most different non-stagnating island" donor almost never exists,
so the algorithm falls through to its fallback branch on nearly every trigger.

### What breaks the correlation

1. **Topology.** On the impact of migration topology: sparse, large-diameter topologies (ring,
   chain) slow the propagation of a dominant genotype and preserve diversity for longer; dense,
   small-diameter topologies (complete graph, hypercube) accelerate convergence but increase the
   risk of homogenization [10][11]. Frahnow & Kötzing, "Ring Migration Topology Helps Bypassing
   Local Optima," arXiv:1806.01128 [11], give a rigorous runtime-analysis result on a constructed
   two-optima benchmark (parametrized "FORK" function): a single (1+1) EA needs Θ(n^2r) evaluations,
   a complete-topology island model needs Θ(n^1.5r), and a ring-topology island model needs Θ̃(n^r) —
   matching black-box lower bounds. Their argument is explicitly that rare migration and large
   topological diameter (as in a ring) preserve inter-island diversity better than dense topologies.
   This project already uses a ring for the "fixed" policy, which is a defensible choice by this
   evidence, but the finding also implies that if all islands run identical parameters, ring
   topology alone delays but does not prevent eventual homogenization — it only slows the
   propagation of a single dominant genotype, it does not stop each island from independently
   collapsing to its own local optimum (which is the observed pathology: independent, near-
   simultaneous collapse, not one genotype spreading via migration).
2. **Heterogeneous parameters across islands — the direct fix.** This is a distinct, named research
   thread:
   - Gong & Fukunaga, "Distributed island-model genetic algorithms using heterogeneous parameter
     settings," IEEE CEC 2011 [2]. Core idea: rather than tuning one set of GA control parameters
     (mutation rate, crossover rate, population size) for the whole system, statically assign
     *randomly different* parameter values to each island/processor. Reported finding: this simple
     randomized heterogeneous-parameter strategy achieves results competitive with a homogeneous
     distributed GA that had its parameters hand-tuned specifically for each benchmark, while
     removing the tuning cost. This is a real, verifiable, citable positive result for
     parameter-heterogeneous islands, though this session could not extract the exact numeric
     parameter ranges or per-benchmark performance deltas from the accessible PDF/RG pages (PDF
     text extraction failed, RG page returned 403); the existence, authorship, venue and headline
     finding are corroborated by two independent search-result summaries and should be treated as
     established, with numeric details marked unverified pending direct access. A closely related
     follow-up, "Evaluation of a Randomized Parameter Setting Strategy for..." (metahack.org,
     CEC2013-RHIM.pdf) [12], appears to extend this line of work; not independently verified in this
     session.
   - Luo et al., "A Dual Heterogeneous Island Genetic Algorithm for Solving Large Size Flexible Flow
     Shop Scheduling Problems on Hybrid Multicore CPU and GPU Platforms," Mathematical Problems in
     Engineering, 2019, arXiv:1903.10722 [13]. Not TSP, but a directly relevant, verifiable
     heterogeneous-island design: islands are heterogeneous both in *where* they run (CPU vs GPU,
     giving different effective operator costs/behavior) and in *configuration*. Rationale stated by
     the authors: pure selection + elitism decreases within-island diversity over generations, and
     while migration injects new material, its effect is limited if every island's operators behave
     identically — i.e., migration between islands that will independently reconverge to the same
     kind of solution has limited value, which is precisely the mechanism failing in this project's
     DTAM.
   - A related but distinct GPU multi-population TSP paper (Wang et al., 2020, "Multipopulation
     Genetic Algorithm Based on GPU for Solving TSP Problem," Mathematical Problems in Engineering)
     [14] is reported in search summaries as using *different mutation rates per subpopulation* to
     "simulate different living environments and increase species richness" specifically for TSP —
     this is the most directly on-point heterogeneous-island-for-TSP data point found, though this
     session was not able to independently fetch and verify its full text; treat the specific
     mutation-rate values as unverified until the paper itself is read.

### Concrete parameter axes to make heterogeneous (synthesized guidance, not a single citation)

Based on the above sources collectively, the published heterogeneous-island design space covers:
different mutation rates per island, different crossover rates, different island (sub)population
sizes, different selection pressure (tournament size), and different hardware/operator variants
(e.g., some islands with 2-opt local search enabled, some without). All are cited above as having
been tried in at least one published heterogeneous-island system; only the Gong & Fukunaga
randomized-heterogeneous-parameter result and the CPU/GPU dual-heterogeneous scheduling paper give
an explicit reported gain over a homogeneous baseline verifiable from the search summaries in this
session.

**Verdict:** [strong evidence for the mechanism, weak/unverified for exact numbers applicable to
this project] Heterogeneous islands are a real, multi-paper research direction whose stated
rationale — homogeneous islands independently converge to similar solutions, limiting the value of
migration between them — matches this project's measured pathology exactly. This is the
single most literature-supported, directly actionable fix among the five questions.

---

## Q3 — Diversity maintenance mechanisms for permutation GAs

Ranked by (a) expected impact on *this* pathology (near-instant collapse to <1% edge-distance
clones within ~100 generations) and (b) implementation cost, given C++/OpenMP island GA with
elitism=1 and 2-opt on 20% of children.

1. **Random immigrants** — replace a fraction of the worst individuals each generation (or each
   epoch) with freshly-generated random tours. Documented as a standard, simple technique
   specifically for maintaining diversity by continually reinjecting genetic material [15][16]; a
   self-organizing variant replaces the worst individual and near-worst-ranked individuals with
   random immigrants each generation and is shown to induce a self-regulating diversity level [16].
   *Impact:* high — directly counteracts the measured "population becomes near-clones" symptom by
   construction, since it guarantees a floor on diversity independent of selection/mutation
   dynamics. *Cost:* very low (a few lines; O(1) extra tour generations per generation).
   *Interaction:* can partially defeat elitism's benefit if the immigrant fraction is too high
   relative to island size (30 individuals is small, so even a 10% immigrant fraction is 3
   individuals/generation — proportionally large); interacts fine with 2-opt (2-opt is applied only
   to 20% of children, immigrants can simply be excluded from local search to keep them "raw" and
   diversity-preserving).

2. **Diversity-based / relative stagnation triggers** replacing the current absolute-threshold
   trigger — not a diversity-maintenance mechanism per se, but directly fixes the DTAM inertness
   described in the prompt (cross-reference Q4). *Impact:* high for restoring DTAM's intended
   selectivity. *Cost:* very low (change one comparison).

3. **Self-adaptive / stagnation-triggered hypermutation.** Documented pattern: increase mutation
   rate when stagnation is detected for W generations (one concrete example found: mutation rate
   raised from 0.02 to 0.05 after 50 stagnant generations) [17]; self-adaptation of mutation
   operator *and* probability for permutation representations specifically is documented to match
   or beat well-tuned static operators on benchmark TSPs [18][19]. Known pathology: naive
   self-adaptive schemes can suffer "vanishing mutation rate," where the adaptive rate decays toward
   zero and the very collapse this project measures is reproduced by the adaptation mechanism itself
   [20] — so a stagnation-*triggered* (not continuously self-adaptive) hypermutation is the safer
   design, consistent with Doerr & Rajabi, "Stagnation Detection Meets Fast Mutation," arXiv:
   2201.12158 [21], who formally analyze coupling stagnation detection to heavy-tailed/fast mutation
   and show runtime benefits on standard benchmarks (not TSP-specific, theoretical analysis).
   *Impact:* medium-high. *Cost:* low. *Interaction:* directly antagonizes elitism if the elite
   individual is preserved at rate 1 while everything else hypermutates — likely fine here since
   elitism=1 is very small; largely orthogonal to 2-opt.

4. **Duplicate elimination / no-duplicates policy.** Not separately documented with strong TSP
   citations in this search, but is a standard, cheap technique (reject or resample offspring
   identical to an existing population member) directly targeted at a "near-clone population"
   symptom. *Impact:* medium (prevents exact duplication, but the measured problem is *near*-clones
   at 0.3–1% edge distance, not exact duplicates, so this mechanism alone likely would not resolve
   the measured pathology). *Cost:* low but O(pop) comparisons per insertion.

5. **Deterministic crowding.** Offspring compete against the most similar parent rather than the
   population's worst; De Jong's original crowding and the deterministic-crowding
   refinement/generalization are documented, established niching mechanisms for preserving multiple
   subpopulations within a single population [22][23][24]. *Impact:* medium — directly targeted at
   preventing genotypic clustering, well-matched to a permutation edge-distance diversity metric.
   *Cost:* medium (requires a distance metric between individuals — edge-distance is already
   computed for this project's diversity metric, so reuse is cheap; requires restructuring the
   replacement step). *Interaction:* documented to interact awkwardly with strong elitism (elitism
   already privileges one region of the search; crowding then fights to keep diversity around a
   preserved elite) and can add non-trivial overhead when combined with an expensive local search
   like 2-opt on top, since each 2-opt'd child must still be crowd-compared.

6. **Fitness sharing.** Shares fitness among similar individuals to discourage crowding into one
   region; classic, well-documented [24]. *Impact:* medium, similar rationale to crowding but
   historically more sensitive to the sharing-radius parameter and more expensive (pairwise distance
   over the whole population each generation). *Cost:* higher than crowding for equivalent effect on
   small islands (30 individuals → 435 pairwise edge-distance computations per island per
   generation — likely acceptable at this scale, but non-trivial vs. immigrants/hypermutation).
   *Interaction:* known to be sensitive to (and can conflict with) elitism if the shared fitness of
   the incumbent elite is depressed by its own similarity to itself/near-clones.

7. **Incest prevention / mating restriction.** Restrict crossover to sufficiently distant parents
   (used explicitly inside CHC-style algorithms, which pair "vigorous crossover only between
   sufficiently distant individuals" with soft restarts, and are reported to "virtually eliminate
   genetic drift") [25][26]. *Impact:* medium — directly slows the mechanism (selection pulling
   similar parents together) that produces the measured collapse. *Cost:* low-medium (needs a
   distance check before mating; may need a fallback when the island has already collapsed and no
   distant pairs exist — which, given the measured 0.3–1% edge-distance band, would be *most of the
   run*, so incest prevention alone is unlikely to help once collapse has already occurred; it is
   better as a preventative measure than a cure).

8. **Reduced selection pressure (tournament k=2 vs 4 vs 7).** General principle, well documented:
   larger k increases selection pressure and convergence rate but raises premature-convergence risk;
   smaller k slows convergence and preserves diversity longer [27][28][29]. No source in this search
   gives a controlled numeric comparison of k=2/4/7 specifically on TSP with quantified diversity or
   final-tour-length deltas — the direction of the effect is well established, magnitude is not.
   *Impact:* medium, *Cost:* trivial (change one integer). *Interaction:* directly composes with
   elitism (elitism is itself a maximal selection-pressure operator on 1 individual regardless of k,
   so k mainly affects the other 29 slots); does not interact badly with 2-opt.

**Overall ranking by (impact / cost) for this specific pathology:** (1) random immigrants,
(2) fix the stagnation trigger to be relative (Q4), (3) reduce tournament k, (4) stagnation-triggered
hypermutation, (5) deterministic crowding (reusing the existing edge-distance metric), (6) incest
prevention (weak once already collapsed), (7) duplicate elimination (addresses a narrower symptom
than measured), (8) fitness sharing (highest overhead for comparable effect to crowding).

---

## Q4 — Relative vs. absolute stagnation triggers

### What the literature uses

- **No-improvement-for-W-generations** is the dominant, simplest stagnation criterion reported
  across sources found in this search [30][31][32] — track best fitness, declare stagnation if it
  has not improved for W consecutive generations. This is scale-free by construction (it never
  depends on the absolute numeric range of a metric), which is exactly the property the project's
  current absolute diversity threshold lacks.
- **Dual/relative criteria.** One documented pattern combines a population-compression check (e.g.,
  a near-tail percentile individual's fitness within some small percentage of the best) with a
  *relative* improvement-over-a-window test (window w=5, tolerance δ=10⁻⁴ in one reported
  implementation) [32] — i.e., stagnation is declared only when the population has both converged
  *and* stopped improving, evaluated relative to a moving reference rather than an absolute cutoff.
- **Proportion-of-stagnated-individuals threshold** (e.g., SProp = 50%, meaning the stagnation
  response activates only once at least half the population is individually stagnated) is another
  documented relative/normalized formulation [32].
- **Entropy-based termination/stagnation criteria** for evolutionary optimization are documented
  (e.g., "Entropy based Termination Criterion for Multiobjective Evolutionary Optimisation" [33]),
  using population entropy trend rather than a fixed absolute diversity value.
- **TSP-specific, permutation-aware diversity measures**: Sudholt/collaborators' or others' work
  aside, the most directly relevant citable source is Nagata & colleagues / or the MIT Press paper
  "High-Order Entropy-Based Population Diversity Measures in the Traveling Salesman Problem,"
  Evolutionary Computation, MIT Press, vol. 28, no. 4, 2020, pp. 595–620 [34]. This paper explicitly
  argues that commonly used permutation-diversity measures do not capture higher-order dependencies
  between tour positions, and proposes edge-frequency entropy and higher-order (Markov-model)
  entropy measures as more discriminating alternatives. It is directly on point for this project's
  question of whether "distance to the island's own best individual" is a poorly-conditioned metric:
  edge-frequency entropy is a *population-relative* statistic (built from how often each edge
  appears across the whole population) rather than a *distance-to-a-single-reference-individual*
  statistic, and by construction it responds to structure the mean-distance-to-best metric can miss
  (e.g., a population that is diverse in aggregate edge usage but where every individual happens to
  be similarly far from the specific best tour, or conversely a population clustered near a
  non-representative "best"). This session was not able to fetch the full text (403 on the direct
  MIT Press page) to extract a quantitative robustness comparison; the paper's existence, venue, and
  general thrust are corroborated by multiple independent search hits and should be treated as
  established, with the "is it more scale-robust than distance-to-best" comparison marked
  **unverified pending full-text access**.

### Is distance-to-own-best worse-conditioned than the alternatives?

[weak evidence, reasoned from first principles + the paper above, not from a direct quantitative
citation]: Measuring diversity as mean edge-distance to a *single* reference individual (the
island's current best) has two structural weaknesses documented indirectly by the sources above:
(1) it collapses toward zero as soon as the population clusters around *any* single point,
including a point that is not necessarily representative of the population's actual spread
(pairwise inter-individual distance, by contrast, only collapses when *all pairs* are close, which
is a stricter and arguably more informative condition); (2) it is a single scalar whose "healthy"
range depends on n (tour length) and on how OX/mutation interact with edge sets, so an absolute
threshold tuned by intuition (tau=0.15) can be badly miscalibrated for a given n — exactly the
measured failure. Simply **counting distinct individuals** in the population (a trivial, O(pop
log pop) with hashing, metric) is a conceptually different but very cheap alternative that is scale-
naturally-bounded (0 to population size) and does not require deciding on an edge-distance
threshold at all; no citation found in this search specifically compares it to edge-distance, so
this is marked as a plausible, cheap, easily-testable candidate rather than an established
literature recommendation.

**Verdict:** [strong evidence for relative-over-absolute triggers in general; weak/unverified for
the specific comparison of distance-to-best vs. pairwise vs. entropy vs. distinct-count on this
project's exact setup] — the clearest, most defensible fix directly supported by the literature is
to replace the fixed tau with a *relative* trigger: e.g., diversity below X% of the island's own
diversity at epoch start, or diversity below a moving-average fraction, or a no-improvement-for-W
window on best fitness — all of which are standard patterns [30][31][32] and none of which suffer
the saturation problem diagnosed in the prompt.

---

## Q5 — Where diversity-driven migration should demonstrably help

Being honest about the state of evidence: **no source found in this session gives a controlled,
TSP-specific, head-to-head experiment showing diversity-triggered/adaptive migration beating fixed
periodic migration under conditions matching this project (8 islands, 30/island, ring-adjacent
topology, n≈500–800).** The closest direct precedent is:

- Li & Wu, "Subpopulation Diversity Based Selecting Migration Moment in Distributed Evolutionary
  Algorithms," arXiv:1701.01271 [35]. This is a genuine, directly relevant precedent: migration
  still occurs at fixed intervals, but the *probability* that immigrants are accepted into the
  target subpopulation is a function of that subpopulation's diversity (higher diversity → migrants
  less likely to be accepted / needed; lower diversity → migrants more likely accepted), evaluated
  on the TSP with eight benchmark instances. Reported result (from abstract-level summary; full
  quantitative tables not independently extracted in this session): the diversity-gated scheme shows
  "a significant advantage on solutions especially for high difficulty instances" versus
  (implicitly) non-diversity-gated migration. This supports candidate #1 below (harder/more
  multimodal instances favor diversity-aware migration) but the paper uses a *probability-gated*
  design, not this project's *pull from most-different-non-stagnating-donor* design, and does not
  report island count/island size — so it is suggestive, not a direct validation of DTAM's specific
  mechanism.

For each candidate regime, the mechanism by which diversity-triggered migration *should* help, and
the evidentiary status:

1. **Highly multimodal / clustered instances.** Mechanism: with more distinct local optima basins,
   different islands are more likely to genuinely diverge to different basins before collapsing, so
   a diversity-triggered "pull from the most different island" has real, distinguishable donors to
   choose among, and the payoff of picking the right donor is larger (escaping a worse basin).
   Evidence: Li & Wu's reported "significant advantage... especially for high difficulty instances"
   [35] is a real, if not fully quantified-in-this-session, data point in this exact direction, on
   TSP. **[weak-to-moderate evidence]**

2. **Larger island counts (16/32/64) giving more donor choice.** Mechanism: with only 8 islands,
   and all 8 collapsing together (as measured), the "most different non-stagnating" search space is
   tiny and mostly empty; with more islands, at any given epoch a larger fraction are statistically
   likely to still be mid-collapse or to have re-diversified via their own local mutation/immigrant
   noise, giving DTAM real donor diversity to exploit and reducing how often it falls to the
   fallback branch. No source found runs this exact ablation for a diversity-triggered *pull*
   migration scheme; general island-model literature does discuss that island count/topology jointly
   determine time-to-homogenization [9][10][11], which is consistent with, but does not directly
   confirm, this candidate. **[weak evidence — plausible extrapolation, untested]**

3. **Larger islands that do not collapse.** Mechanism: directly follows from Q1/Q3 — if per-island
   population size is raised past whatever the true collapse threshold is (unknown, but plausibly
   above 30 given the measured near-instant collapse and consistent with population-sizing theory's
   qualitative prediction [5][6][7]), islands retain enough internal diversity that the "not
   stagnating" donor condition is not vacuously false almost everywhere, and DTAM's donor-selection
   logic becomes meaningful rather than inert. **[weak evidence, but mechanistically the most
   directly implied fix given the measured pathology]**

4. **Longer epochs between migration.** Mechanism: ties to the ring-topology finding that *rare*
   migration is part of why sparse topologies preserve diversity better than dense/frequent
   migration [11] — if islands are allowed more generations to independently drift before any
   migration event (fixed or triggered), they have more chance to genuinely diverge from each other
   first, making a later triggered migration more informative. Evidence for this specific claim
   comes from Holtschulte's reported finding that "moderately large migration intervals and small
   migration size were found to be optimal" for maintaining diversity in island GAs generally
   [4] (numeric interval values not independently verified in this session — PDF extraction
   failed). **[weak evidence, general island-GA finding, not TSP- or DTAM-specific]**

5. **Weaker or absent local search.** Mechanism: 2-opt applied to 20% of children is itself a strong
   convergence accelerant (it locally optimizes and likely increases similarity among optimized
   children, compounding the GA's own selection pressure toward collapse); removing or reducing it
   should slow collapse and preserve more of a window in which any migration policy — but especially
   a diversity-*triggered* one — can distinguish real islands from collapsed ones. No source found
   in this search directly quantifies local-search-driven diversity loss magnitude for island-GA
   TSP; this is a mechanistic inference from general memetic-algorithm literature on the
   exploration/exploitation tradeoff of local search intensity (e.g., "Memetic Algorithms:
   Parametrization and Balancing Local and Global Search," arXiv:1109.6441 [36], which generally
   discusses how local-search intensity trades off against global exploration, without giving
   island-model-specific numbers). **[weak evidence, generic memetic-algorithm principle,
   not directly measured for this scenario]**

6. **Heterogeneous islands (per Q2).** Mechanism: this is the strongest, most literature-grounded
   candidate. If islands run different mutation rates / selection pressures / operators, they will
   *not* collapse in lock-step (per Q2's central finding), which directly restores the precondition
   DTAM's "most-different non-stagnating island" clause needs to be non-vacuous. This is the same
   mechanism cited by Luo et al. [13] as the motivation for heterogeneous islands in the first place
   (homogeneous operators limit the value of migration because everything converges the same way).
   **[strong evidence for the mechanism generally; still no TSP-specific, DTAM-specific numeric
   confirmation]**

**Honest bottom line:** the literature supports, with real citations, the *mechanisms* by which
diversity-triggered migration should outperform fixed migration (harder instances give real donor
diversity; more islands give more donor choice; non-collapsing islands make the trigger meaningful;
heterogeneous islands prevent lock-step collapse). It does **not** provide a controlled experiment
demonstrating the gain in this project's specific configuration. The recommended path is to test
candidates #3 and #6 first (see experiment plan), since they attack the measured root cause most
directly and are cheap to test in isolation.

---

## Ranked experiment plan for this project

Ordered by (expected information gain) / (compute cost); each assumed to cost minutes of CPU on a
laptop, changing one axis at a time from the current baseline (8×30, tau=0.15, k=4, mut=0.25,
20% 2-opt).

1. **Replace the absolute diversity threshold with a relative/no-improvement trigger.**
   Change: stagnation = (diversity < 0.5 × island's own diversity at epoch start) OR (best fitness
   unchanged for W=5 epochs), instead of `diversity < 0.15`.
   Hypothesis: this restores discrimination in the trigger (currently saturated at 99.7% firing) so
   DTAM's donor-selection logic is exercised meaningfully rather than degenerating to "always
   migrate from most distant island."
   Predicted direction: trigger rate drops well below 99.7%, and DTAM's final tour length either
   improves relative to its own current (broken) behavior, or at minimum starts to diverge in
   behavior from "fixed."
   Confirm/refute: log trigger-rate over the run (should no longer be ~99.7%/78.6% bimodal); compare
   final tour length DTAM-relative vs fixed before/after.
   Citation motivating: [30][31][32] (relative/windowed stagnation criteria are the documented norm).

2. **Raise island size while holding total population fixed (redistribute islands), e.g., 4×60 and
   2×120, vs. current 8×30.**
   Change: island count/size only; keep total population 240 constant to isolate the per-island-size
   effect from a total-compute-budget effect.
   Hypothesis: per-island collapse is driven by insufficient per-deme statistical resolving power
   (population-sizing theory mechanism [5][6][7]); larger demes should collapse later and to a
   higher floor.
   Predicted direction: gen-of-collapse (diversity first below e.g. 0.02) pushed later, and
   collapsed-floor diversity higher, monotonically with island size.
   Confirm/refute: re-run the same diversity-logging-every-10-generations protocol at each island
   size; compare collapse timing/floor.
   Citation motivating: [1][5][6][7].

3. **Make islands heterogeneous in mutation rate and tournament k (cheapest heterogeneity axis).**
   Change: assign each of the 8 islands a different (mutation_rate, k) pair, e.g. mutation ∈
   {0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45}, k ∈ {2,3,3,4,4,5,5,6} (or simplest: randomize
   once at startup, static for the whole run, per Gong & Fukunaga's design [2]).
   Hypothesis: heterogeneous islands desynchronize collapse timing across islands, so at any given
   epoch some islands remain non-stagnating — restoring DTAM's donor-availability precondition.
   Predicted direction: fraction of DTAM trigger-epochs that fall through to the "no non-stagnating
   donor" fallback branch drops substantially versus the homogeneous baseline; DTAM final tour
   length improves relative to fixed-migration under otherwise identical settings.
   Confirm/refute: log, per DTAM trigger event, whether a genuine non-stagnating donor was found vs.
   fallback used; compare that rate homogeneous vs heterogeneous.
   Citation motivating: [2][9][10][13] (highest-priority question, Q2).

4. **Add random immigrants (cheap, orthogonal diversity injection).**
   Change: each generation, replace the worst 1–3 individuals per island (≈3–10% of 30) with fresh
   random tours (excluded from 2-opt to keep them "raw").
   Hypothesis: sets a diversity floor that prevents the population from ever reaching the measured
   0.003–0.01 near-clone band.
   Predicted direction: mean/min diversity over the run rise substantially above the measured
   0.0181 mean / 0.0029 min baseline; final tour length improves or is at worst unchanged (small
   risk of quality regression if immigrant fraction is too high for 30-individual islands).
   Confirm/refute: same diversity-logging protocol; compare distribution of diversity values and
   final tour length against baseline.
   Citation motivating: [15][16].

5. **Reduce tournament size to k=2 (single-line change, cheapest test in the whole plan).**
   Change: k=4 → k=2.
   Hypothesis: lower selection pressure slows the rate at which the population converges toward a
   few genotypes.
   Predicted direction: diversity collapse (time-to-<0.02) delayed; possibly mild final-quality
   change (small risk of slower convergence hurting solution quality within the fixed generation
   budget — worth checking both diversity *and* final tour length).
   Confirm/refute: diversity-vs-generation curve, generation-to-collapse metric, final tour length.
   Citation motivating: [27][28][29] (general, direction well-established, magnitude for this
   system unknown — this is why it's cheap and decisive to just run it).

6. **Widen epoch length E (longer independent-evolution windows between migration checks).**
   Change: double or quadruple E.
   Hypothesis: islands get more time to independently drift before any migration event, increasing
   the chance that a triggered migration finds genuinely different islands rather than
   already-homogenized ones.
   Predicted direction: DTAM's fallback-branch rate (from experiment 3's logging) drops as E grows,
   even without heterogeneity; possible interaction where longer E alone already substantially fixes
   DTAM without needing heterogeneous parameters.
   Confirm/refute: same fallback-rate logging as experiment 3, swept over E.
   Citation motivating: [4][11] (rare/interval migration preserving diversity — general island-GA
   finding, not TSP-specific numeric confirmation).

7. **Reduce/remove 2-opt local search fraction (0.20 → 0.05 or 0.0) as a diversity-preservation
   lever, holding everything else fixed.**
   Change: fraction of children receiving bounded 2-opt.
   Hypothesis: local search compounds selection pressure toward convergence; reducing it should slow
   collapse, at a plausible cost to final-tour-length within a fixed generation budget (this is the
   key tradeoff to quantify, not assume).
   Predicted direction: diversity collapse delayed; final tour length may or may not degrade —
   this experiment's main value is establishing whether local-search intensity is a first-order or
   second-order contributor to the measured collapse relative to population size/selection pressure.
   Confirm/refute: diversity-vs-generation curve and final tour length at 2-opt fractions
   {0, 0.05, 0.20 (baseline), 0.5}.
   Citation motivating: [36] (general memetic-algorithm exploration/exploitation principle, not a
   quantified citation for this exact tradeoff — treat as a mechanistic hypothesis test, not a
   literature-confirmed prediction).

8. **Switch the diversity metric from mean-distance-to-own-best to (a) pairwise mean edge-distance
   and (b) distinct-individual count, logged in parallel with the existing metric, no algorithm
   change.**
   Change: measurement only — add two more logged diversity statistics alongside the current one.
   Hypothesis: the current metric is more poorly conditioned (saturates faster / has a narrower
   dynamic range) than pairwise distance or distinct-count, per the edge-entropy literature's
   critique of single-reference-point diversity measures [34].
   Predicted direction: pairwise and distinct-count metrics should show a wider dynamic range over
   the run than distance-to-best, and/or diverge in their trajectory shape, revealing information
   distance-to-best is currently discarding.
   Confirm/refute: log all three metrics over the same 1500-generation run; compare dynamic range,
   variance, and correlation with final quality.
   Citation motivating: [34] (High-Order Entropy-Based Population Diversity Measures in TSP,
   MIT Press Evolutionary Computation 2020) — note the paper's own proposed entropy measures were
   not independently re-derived here; this experiment tests the simpler, cheaper pairwise/distinct-
   count alternatives first, consistent with the "cheap decisive test" mandate.

---

## References

1. Whitley, D., Rana, S., & Heckendorn, R. B. (1999). The Island Model Genetic Algorithm: On
   Separability, Population Size and Convergence. *Journal of Computing and Information
   Technology (CIT)*, 7(1), 33–47. http://cit.fer.hr/index.php/CIT/article/view/2919 —
   full text: http://cit.fer.hr/index.php/CIT/article/download/2919/1783

2. Gong, Y., & Fukunaga, A. (2011). Distributed island-model genetic algorithms using heterogeneous
   parameter settings. *2011 IEEE Congress of Evolutionary Computation (CEC)*.
   https://ieeexplore.ieee.org/document/5949703/ ; PDF:
   https://www.metahack.org/gong-fukunaga-island-model-cec2011.pdf
   [Numeric parameter values and per-benchmark results marked unverified in this report — PDF text
   extraction failed and the ResearchGate page returned HTTP 403 in this session; venue/authorship
   corroborated via independent web search summaries.]

3. Varadarajan, et al. (2021). A Parallel Ensemble Genetic Algorithm for the Traveling Salesman
   Problem. *Proceedings of the Genetic and Evolutionary Computation Conference (GECCO '21)*,
   636–643. DOI: 10.1145/3449639.3459281. https://dl.acm.org/doi/10.1145/3449639.3459281
   [Internal parameters (population/island sizes) marked unverified — PDF text extraction failed
   in this session; existence/venue/DOI verified via ACM DL and search.]

4. Holtschulte, N. (2012). Optimal Population Size in Island Model Genetic Algorithms. University
   of New Mexico CS Graduate Symposium paper.
   https://www.cs.unm.edu/~csgsa/archive/2011-2012/papers/2012/NealHoltschulte.pdf
   [Qualitative "diminishing returns" and "moderate migration interval / small migration size
   optimal" findings corroborated by search summary; exact numeric benchmark/parameter values
   marked unverified — PDF text extraction failed in this session.]

5. Goldberg, D. E., Deb, K., & Clark, J. H. (1992). Genetic Algorithms, Noise, and the Sizing of
   Populations. *Complex Systems*, 6(4), 333–362.
   https://www.complex-systems.com/abstracts/v06_i04_a03/ ; full text:
   https://content.wolfram.com/sites/13/2018/02/06-4-3.pdf

6. Harik, G., Cantú-Paz, E., Goldberg, D. E., & Miller, B. L. (1999). The Gambler's Ruin Problem,
   Genetic Algorithms, and the Sizing of Populations. *Evolutionary Computation*, 7(3), 231–253.
   https://pubmed.ncbi.nlm.nih.gov/10491464/

7. Cantú-Paz, E. (2001). The Gambler's Ruin Problem and Population Sizing. In *Efficient and
   Accurate Parallel Genetic Algorithms* (Genetic Algorithms and Evolutionary Computation, vol 1),
   Ch. 2. Springer. https://link.springer.com/chapter/10.1007/978-1-4615-4369-5_2

8. Cantú-Paz, E. (1998). A Survey of Parallel Genetic Algorithms. IlliGAL Report.
   https://neo.lcc.uma.es/cEA-web/documents/cant98.pdf

9. Island-Based Genetic Algorithm (topic overview; homogenization / islands converging to similar
   clusters of local optima). https://www.emergentmind.com/topics/island-based-genetic-algorithm
   [Aggregator/overview source, not a primary peer-reviewed citation — used only to corroborate a
   claim also supported by primary sources 10 and 11; treat as supplementary.]

10. Cohoon et al. and subsequent authors; summarized in "On the Impact of the Migration Topology on
    the Island Model," *Parallel Computing*, 2010 (and arXiv preprint 1004.4541).
    https://dl.acm.org/doi/10.1016/j.parco.2010.04.002 ;
    https://arxiv.org/pdf/1004.4541 ; ResearchGate:
    https://www.researchgate.net/publication/222676877_On_the_Impact_of_the_Migration_Topology_on_the_Island_Model
    [Sparse vs. dense topology effect on diversity/homogenization corroborated by search summary;
    full-text quantitative details not independently re-verified in this session.]

11. Frahnow, C., & Kötzing, T. (2018). Ring Migration Topology Helps Bypassing Local Optima.
    arXiv:1806.01128 [cs.NE]. https://arxiv.org/abs/1806.01128 ; PDF:
    https://arxiv.org/pdf/1806.01128

12. Evaluation of a Randomized Parameter Setting Strategy for [Heterogeneous Island Models],
    CEC 2013 (metahack.org). https://metahack.org/CEC2013-RHIM.pdf
    [unverified — title truncated in search results, full title/authors not independently
    confirmed in this session; listed for completeness/follow-up only.]

13. Luo, S., et al. (2019). A Dual Heterogeneous Island Genetic Algorithm for Solving Large Size
    Flexible Flow Shop Scheduling Problems on Hybrid Multicore CPU and GPU Platforms.
    *Mathematical Problems in Engineering*, 2019. arXiv:1903.10722.
    https://onlinelibrary.wiley.com/doi/10.1155/2019/1713636 ;
    https://arxiv.org/pdf/1903.10722

14. Wang, et al. (2020). Multipopulation Genetic Algorithm Based on GPU for Solving TSP Problem.
    *Mathematical Problems in Engineering*, 2020, Article 1398595.
    https://onlinelibrary.wiley.com/doi/10.1155/2020/1398595
    [Reported "different mutation rates per subpopulation for TSP" claim is from a search-engine
    summary of this paper, not independently confirmed against the full text in this session —
    marked unverified.]

15. Grefenstette, J. J. (as generally cited for random immigrants in dynamic/diversity-preserving
    GAs); summarized secondary description via search. Specific primary citation not independently
    re-verified in this session — the *concept* of random immigrants as a diversity-maintenance
    technique is well established in the EA literature generally.
    [unverified primary citation — concept corroborated by source 16 below, which is a verifiable
    peer-reviewed paper using the technique.]

16. Self-organizing random immigrants genetic algorithm for dynamic optimization problems.
    *Genetic Programming and Evolvable Machines*, Springer.
    https://link.springer.com/article/10.1007/s10710-007-9024-z ;
    https://www.academia.edu/974253/A_self-organizing_random_immigrants_genetic_algorithm_for_dynamic_optimization_problems

17. Adaptive mutation rate example (increase from 0.02 to 0.05 after 50 stagnant generations) —
    reported via aggregated search summary; specific primary paper not independently identified/
    verified in this session. [unverified]

18. Self-Adaptation of Mutation Operator and Probability for Permutation Representations in Genetic
    Algorithms. https://www.researchgate.net/publication/220375133 ; PubMed:
    https://pubmed.ncbi.nlm.nih.gov/20560757/

19. (Same study as 18; corroborating PubMed indexing.)

20. "Vanishing mutation rate problem" in self-adaptive mutation schemes — reported via aggregated
    search summary discussing pathologies of self-adaptive mutation; primary source not
    independently pinned down in this session. [unverified]

21. Doerr, B., & Rajabi, A. (2022). Stagnation Detection Meets Fast Mutation. arXiv:2201.12158
    [cs.NE]. https://arxiv.org/pdf/2201.12158 ; also published as: Doerr, B., Rajabi, A. (2022).
    Stagnation Detection Meets Fast Mutation. In: Evolutionary Computation in Combinatorial
    Optimization (EvoCOP 2022), LNCS. [Theoretical runtime-analysis paper, not TSP-specific;
    general benchmark functions.]

22. De Jong, K. A. (1975). *An Analysis of the Behavior of a Class of Genetic Adaptive Systems*
    (PhD dissertation) — origin of crowding. Cited via secondary sources in this search; primary
    dissertation not independently fetched in this session. [unverified primary, well-established
    in secondary literature]

23. Mahfoud, S. W. — deterministic crowding, cited via: "The crowding approach to niching in
    genetic algorithms," *Evolutionary Computation*, 16(3), 315–338 (2008 retrospective/analysis).
    https://dl.acm.org/doi/10.1162/evco.2008.16.3.315

24. "Generalized crowding for genetic algorithms," *Proceedings of GECCO 2010*.
    https://dl.acm.org/doi/10.1145/1830483.1830620

25. Eshelman, L. J. (1991). The CHC Adaptive Search Algorithm: How to Have Safe Search When
    Engaging in Nontraditional Genetic Recombination. In *Foundations of Genetic Algorithms 1*.
    [Cited via secondary description of CHC's incest-prevention + soft-restart design found in
    this search's summaries; primary source not independently re-fetched in this session.]
    [unverified primary, well-established in secondary GA literature]

26. Preventing Premature Convergence in Genetic Algorithms by Preventing Incest.
    https://www.researchgate.net/publication/201976019
    [Title/topic corroborated via search; full text and authors not independently confirmed in
    this session — unverified.]

27. Tournament selection and selection pressure — general description.
    https://www.geeksforgeeks.org/dsa/tournament-selection-ga/
    [Tutorial/aggregator source, used only for the well-established qualitative k↔selection-pressure
    relationship; not a peer-reviewed citation.]

28. Genetic algorithm with a new round-robin based tournament selection: Statistical properties
    analysis. *PLOS ONE*, 2022. https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0274456

29. Analysis Effect of Tournament Selection on Genetic Algorithm Performance.
    *Journal of Physics: Conference Series*, 1566, 012131 (2020).
    https://iopscience.iop.org/article/10.1088/1742-6596/1566/1/012131/pdf

30. Extended Evolutionary Algorithms with Stagnation-Based Extinction Protocol.
    *Applied Sciences*, MDPI, 11(8), 3461 (2021). https://www.mdpi.com/2076-3417/11/8/3461

31. Most effective stagnation detection for a multi-objective evolutionary algorithm? (discussion
    thread aggregating no-improvement-window criteria).
    https://www.researchgate.net/post/Most_effective_stagnation_detection_for_a_multi-objective_evolutionary_algorithm
    [Discussion/Q&A source, not peer-reviewed — used only as corroborating evidence that
    no-improvement-window criteria are the community-standard default; treat as weak evidence.]

32. UDE-III: An Enhanced Unified Differential Evolution Algorithm for Constrained Optimization
    Problems (window w=5, tolerance δ=10⁻⁴ relative-improvement stagnation criterion; SProp
    proportion-of-stagnated-individuals criterion). arXiv:2410.03992.
    https://arxiv.org/pdf/2410.03992

33. Entropy based Termination Criterion for Multiobjective Evolutionary Optimisation.
    https://www.researchgate.net/publication/283949115

34. High-Order Entropy-Based Population Diversity Measures in the Traveling Salesman Problem.
    *Evolutionary Computation*, MIT Press, 28(4), 595–620 (2020).
    https://direct.mit.edu/evco/article/28/4/595/94998 ; ResearchGate:
    https://www.researchgate.net/publication/339244541
    [Existence, venue, and general thrust (edge-frequency and higher-order Markov-model entropy as
    diversity measures for TSP permutation populations) corroborated by multiple independent search
    summaries; full-text quantitative robustness comparison vs. distance-to-best not independently
    verified in this session — MIT Press page returned HTTP 403.]

35. Li, C., & Wu, J. (2017). Subpopulation Diversity Based Selecting Migration Moment in Distributed
    Evolutionary Algorithms. arXiv:1701.01271 [cs.NE]. https://arxiv.org/abs/1701.01271 ; PDF:
    https://arxiv.org/pdf/1701.01271
    [Abstract-level summary extracted; quantitative result tables (exact numbers for the "significant
    advantage... especially for high difficulty instances" claim) not independently extracted from
    full text in this session due to PDF parsing limitations — headline qualitative claim marked as
    weak/moderate evidence, not fully verified.]

36. Memetic Algorithms: Parametrization and Balancing Local and Global Search. arXiv:1109.6441.
    https://arxiv.org/pdf/1109.6441

### Notes on verification limitations

Several PDFs in this session could not be parsed to extractable text by the available fetch tooling
(binary/FlateDecode-compressed streams), and a small number of pages returned HTTP 403. In every
such case this report explicitly marks the specific numeric claim as "unverified" rather than
inferring or inventing values, while still citing the source's existence, venue, and headline
finding where that much was corroborated by independent search-engine summaries. Where a claim is
load-bearing for the ranked experiment plan (Q1 population-size guidance, Q2 heterogeneous-parameter
gains, Q5 diversity-triggered migration's TSP evidence), readers should treat this report as
identifying *where* to look and *what mechanism* is claimed, not as a substitute for reading the
primary sources directly before citing specific numbers in the project's own write-up.
