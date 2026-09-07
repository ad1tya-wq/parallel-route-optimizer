# Erratum applying to MIGRATION-POLICY-EVIDENCE.md

That report was commissioned with an incorrect premise. It was told that island
diversity "never falls low enough for a threshold trigger to be selective", and
several of its conclusions restate that as "diversity never collapses".

**That premise is wrong.** Measured directly (diversity logged every 10
generations, 1500 generations, 8 islands of 30, uniform-500):

| generation | 10 | 130 | 250 | 370 | 610 | 730 | 1090 | 1450 |
|---|---|---|---|---|---|---|---|---|
| diversity | 0.224 | 0.032 | 0.039 | 0.012 | 0.010 | 0.006 | 0.005 | 0.004 |

Whole run: min 0.0029, max 0.2236, **mean 0.0181**. Diversity *collapses* within
about 100 generations and stays pinned near 0.003-0.01. The stagnation condition
is `diversity < tau`, so tau = 0.15 is true 99.7% of the time because the islands
are permanently converged, not because they stay diverse.

Treat every sentence in that report asserting sustained high diversity as void.
Its verified literature findings remain valid and, read against the corrected
measurement, several of them explain the collapse rather than contradicting it:

1. **A segment inversion changes exactly two edges of a tour**, regardless of the
   reversed segment's length. At n = 500 one mutation perturbs 0.4% of the edge
   set. Mutation is therefore a very weak source of edge diversity and cannot
   offset selection pressure. This *supports* rapid collapse.

2. **Skolicki & De Jong (GECCO 2005): migration interval is the dominant lever,
   and frequent migration homogenises islands.** This project migrates every
   epoch (interval = 1), the most aggressive end of that spectrum. That is a
   citable mechanism for why all eight islands collapse *together*, which in turn
   is why DTAM's "pull from the most different NON-STAGNATING island" clause
   almost never finds a healthy donor.

3. **Nagata (Evolutionary Computation, 2020): single-reference diversity measures
   are weaker signals than population-wide pairwise or edge-frequency-entropy
   measures.** The project's metric is distance to the island's own best tour, a
   single reference point, and it saturates in the 0.003-0.05 band where an
   absolute threshold is badly conditioned.

4. **No published work was found that measures the runtime cost of an adaptive
   migration decision**; the adaptive-migration literature compares quality at
   fixed generation counts and does not report wall-clock cost of the trigger.
   This is a genuine gap and is where this project's cost-versus-quality framing
   contributes something the literature does not already contain.

Points 1 and 2 together predict the observed pathology, and point 2 predicts that
*increasing* the migration interval (equivalently, raising epoch length) should
slow the collapse. Experiment E8 tests exactly that.
