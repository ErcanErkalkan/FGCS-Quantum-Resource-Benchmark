# P7 — Classical objective-evaluation budget curve

## Reviewer risk addressed
The earlier strengthened classical reference used a single 4096-objective-evaluation cap. Because the exact state spaces contain only 256, 1024, and 4096 assignments at n=8,10,12, a reviewer could reasonably ask whether the strong classical result is an artifact of this one high budget.

## Design
- Methods: simulated annealing and one-flip tabu search.
- Primary exact suite: 18 instances.
- Independent runs: 64 per instance, method, and budget.
- Budgets: 64, 128, 256, 512, 1024, 4096 complete objective evaluations per run.
- Search logic never queries C* or optimum-state identities.
- Exact enumeration is used only for retrospective approximation ratios and optimum-hit labels.
- Each budget is run as a complete budget-specific trajectory. For simulated annealing, the geometric temperature schedule is rescaled to that budget; the small-budget rows are not truncated checkpoints of a 4096-evaluation run.
- The 4096 endpoint uses the same seed mapping and semantics as the previous fixed-budget layer.

## Results
At 64 evaluations per run, the median-of-instance-median approximation ratio is 1.000 for both methods. Median instance optimum-hit fractions are 0.5546875 for simulated annealing and 0.7890625 for tabu search. Across 64 runs, every one of the 18 instances is solved optimally at least once by both methods.

Tabu search reaches a median instance optimum-hit fraction of 1.000 at budget 128. Simulated annealing increases from 0.6875 at budget 128 to 0.859375 at 256, 0.9609375 at 512, and 1.000 at 1024. Both methods remain at 1.000 at the 4096 endpoint.

## Interpretation boundary
The result strengthens the claim that the exact microinstances are classically easy: this conclusion is already visible well below the previous 4096-evaluation endpoint. Objective evaluations may revisit states, so budget/state-count ratios are bookkeeping descriptors rather than unique-search-space coverage. The budget curve is comparable only within the classical layer and is not mapped to QAOA objective calls, quantum circuit executions, amplitude-amplification oracle calls, wall-clock time, or physical resource use.
