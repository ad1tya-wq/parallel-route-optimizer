# References

Review 1 shipped two disjoint bibliographies: a 10-entry literature-survey table in the submitted
PDF (authors/year, contribution, limitation, and relation to this project for each entry) and a
separate 9-entry numbered reference list in `report/report.md`. The two lists have almost no
overlap — only Reinelt's TSPLIB paper appears in both — because the PDF table covers GA and TSP
foundations while `report.md` focuses narrowly on the migration-policy literature DTAM is compared
against. This file merges both into a single de-duplicated, numbered list, organized thematically,
and is the reference list used by all Review-2 documents.

## Reference list

### Foundations: genetic algorithms and the TSP

1. D. E. Goldberg. *Genetic Algorithms in Search, Optimization and Machine Learning*. Addison-Wesley, 1989.
2. S. Lin and B. W. Kernighan. An Effective Heuristic Algorithm for the Traveling-Salesman Problem. *Operations Research*, 1973.
3. D. Applegate, R. Bixby, V. Chvátal, and W. Cook. *The Traveling Salesman Problem: A Computational Study*. Princeton University Press, 2006.
4. L. Davis. Applying Adaptive Algorithms to Epistatic Domains. IJCAI, 1985. (Order Crossover.)
5. G. A. Croes. A Method for Solving Traveling-Salesman Problems. *Operations Research*, 1958. (2-opt.)
6. J. Beardwood, J. H. Halton, and J. M. Hammersley. The Shortest Path Through Many Points. 1959.

### Parallel and island-model evolutionary algorithms

7. E. Cantú-Paz. *Efficient and Accurate Parallel Genetic Algorithms*. Kluwer Academic Publishers, 2000.
8. E. Alba and M. Tomassini. Parallelism and Evolutionary Algorithms. *IEEE Transactions on Evolutionary Computation*, 2002.
9. L. Scrucca. On Some Extensions to GA Package: Hybrid Optimisation, Parallelisation and Islands Evolution. 2017.
10. K. Varadarajan et al. A Parallel Ensemble Genetic Algorithm for the Traveling Salesman Problem. GECCO, 2021.
11. T. Harada, E. Alba, and G. Luque. A Fresh Approach to Evaluate Performance in Distributed Parallel Genetic Algorithms. 2021.

### Migration policy: fixed, adaptive, and diversity-driven

12. Z. Skolicki and K. De Jong. The Influence of Migration Sizes and Intervals on Island Models. 2005.
13. Subpopulation-diversity-based migrant selection for island GAs. arXiv:1701.01271.
14. Revisiting the Design of Adaptive Migration Schemes for Multipopulation Genetic Algorithms. (ResearchGate 261344192.)
15. DM-LIMGA: Dual Migration Localized Island Model Genetic Algorithm. *Evolutionary Intelligence*, 2020. doi:10.1007/s12065-019-00253-2.
16. A Dual Dynamic Migration Policy for Island Model Genetic Algorithm. (ResearchGate 321795727.)
17. Dynamic Island Model based on Spectral Clustering in Genetic Algorithm. arXiv:1801.01620.

### Benchmarks and evaluation methodology

18. G. Reinelt. TSPLIB — A Traveling Salesman Problem Library. *ORSA Journal on Computing*, 1991.

## Positioning

| Ref | Contribution | Gap it leaves | How this project relates |
|---|---|---|---|
| 1 | Established the classical GA framework: population initialization, selection, crossover, mutation, elitism. | Serial only; no parallel execution or migration. | Forms the GA core shared by all three engines. |
| 2 | Lin-Kernighan local search heuristic for TSP. | Local search alone cannot explore globally. | Motivates the optional 2-opt local search used alongside the GA. |
| 3 | Exact algorithms and benchmark methodology for TSP. | Exact methods are expensive at scale. | Justifies using heuristics such as GAs instead of exact solvers. |
| 4 | Introduced Order Crossover (OX) for permutation problems. | Domain-specific to epistatic/permutation representations. | Used directly as the crossover operator (§3.1). |
| 5 | 2-opt local search for TSP. | Purely local; needs to be combined with a global search method. | Used as the optional bounded first-improvement local search (§3.1). |
| 6 | Estimate for the expected optimal tour length on random Euclidean instances. | Asymptotic estimate, not an exact optimum. | Used as the reference length for `uniform` instances (§4). |
| 7 | Foundational theory of parallel GAs: population sizing, migration frequency, topology, speedup. | Theoretical models rather than adaptive migration policies. | Theoretical basis for the island-model parallelization used here. |
| 8 | Survey of master-slave, fine-grained, and island-model evolutionary algorithms and their scalability. | Broad survey; no specific migration strategy proposed. | Motivates the island model chosen for multicore execution. |
| 9 | Hybrid local search combined with master-slave and island-model parallel GA (software framework). | Describes a software framework, not a migration-mechanism evaluation. | Supports the design choice of combining GA with optional local search. |
| 10 | Scalable parallel island GA for TSP with advanced crossover and multiple topologies. | Emphasizes crossover and topology; migration itself remains conventional. | Contemporary point of comparison for a parallel island GA on TSP. |
| 11 | Quantitative evaluation of parallel GAs using runtime, scalability, migration effects, and speedup rather than solution quality alone. | General distributed PGA evaluation, not TSP-specific or adaptive-migration-specific. | Aligns with this project's emphasis on reporting HPC metrics alongside optimization quality. |
| 12 | Systematic study of how migration interval and migration size affect convergence and diversity in island models. | Studies fixed migration schedules; no adaptive triggers. | Directly motivates investigating an alternative, adaptive migration policy (DTAM). |
| 13 | Diversity-based migrant selection and diversity-conditioned immigration. | Keys migration decisions off the target island's own diversity, and evaluates primarily on final solution quality. | DTAM instead couples a stagnation trigger with distant-source PULL selection chosen at runtime; this project's evaluation adds parallel-computing metrics (speedup, efficiency, Karp-Flatt) alongside quality. |
| 14 | Design and analysis of adaptive (fitness- and diversity-based) migration schemes. | Keys migration decisions off the target island's own diversity and/or a fixed topology, and evaluates primarily on final solution quality. | DTAM instead couples a stagnation trigger with distant-source PULL selection chosen at runtime; this project's evaluation adds parallel-computing metrics (speedup, efficiency, Karp-Flatt) alongside quality. |
| 15 | Dual migration policy (DM-LIMGA) that preserves population diversity in a localized island model. | Keys migration decisions off the target island's own diversity and/or a fixed topology, and evaluates primarily on final solution quality. | DTAM instead couples a stagnation trigger with distant-source PULL selection chosen at runtime; this project's evaluation adds parallel-computing metrics (speedup, efficiency, Karp-Flatt) alongside quality. |
| 16 | Dual dynamic migration policy for island model GAs. | Keys migration decisions off the target island's own diversity and/or a fixed topology, and evaluates primarily on final solution quality. | DTAM instead couples a stagnation trigger with distant-source PULL selection chosen at runtime; this project's evaluation adds parallel-computing metrics (speedup, efficiency, Karp-Flatt) alongside quality. |
| 17 | Dynamic island topology via spectral clustering. | Keys migration decisions off the target island's own diversity and/or a fixed topology, and evaluates primarily on final solution quality. | DTAM instead couples a stagnation trigger with distant-source PULL selection chosen at runtime; this project's evaluation adds parallel-computing metrics (speedup, efficiency, Karp-Flatt) alongside quality. |
| 18 | Standard benchmark instance library for TSP. | Provides problem instances, not algorithms. | Standardizes evaluation of tour quality; supports `EUC_2D` instances in the harness (§4). |

### Honest positioning

Diversity-driven and adaptive migration for island-model genetic algorithms is established prior
work (refs 12-17), and this project does not claim to originate the idea of adapting migration to
population diversity or topology. What this project contributes is narrower: (a) a specific,
self-implemented policy combination — a stagnation trigger paired with distant-source pull
selection chosen at runtime (DTAM) — rather than a new general migration theory, and (b) an
HPC-framed evaluation that reports speedup, efficiency, and related parallel-computing metrics
alongside solution quality, which most of the cited migration-policy papers do not emphasize. The
Review-1 PDF's novelty section overstated DTAM's originality relative to this prior work; the
Review-1 slide deck was more careful on this point. This inconsistency between the two Review-1
deliverables is corrected here: Review 2 states plainly that the migration-policy idea is not new,
and confines the claimed contribution to the specific combination implemented and the way it is
evaluated.
