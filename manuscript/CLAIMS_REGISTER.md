# Claims register — canonical FGCS manuscript

## Supported by the current canonical artifacts
- The project contains only the canonical FGCS weighted Max-Cut study.
- The operational threshold is constructed without the unknown exact optimum `C*` or an optimum-state list.
- Operational construction uses `mu_rnd = 0.5*sum(weights)` and `U_spec = min(sum(weights), n*lambda_max(L)/4)`, then `tau_lambda = ceil(mu_rnd + lambda*(U_spec-mu_rnd))`.
- Operational levels are `lambda={0.25,0.40,0.55}` and produce 54 exact-tier threshold-validation rows.
- Exact enumeration is used only after operational threshold construction to label feasibility, exact marked fraction, and retrospective `tau/C*`.
- Exact feasibility counts are 18/18, 18/18, and 15/18 at lambda 0.25, 0.40, and 0.55.
- Among feasible cases, retrospective median `tau/C*` values are 0.790, 0.865, and 0.933 at those levels.
- `operational_target_metric_summary.csv` contains 432 common-target rows after QAOA is evaluated on all 18 primary instances. The AA entries are explicitly oracle-informed Tier-I validation references because their stopping depth uses exact post-construction `rho_tau`.
- A separate benchmark-normalized calibration axis uses `q={0.90,0.95,1.00}` and `tau_q=ceil(q*C*)`; it is not described as operational target construction.
- The dense calibration robustness grid contains 11,934 conditions: 18 exact instances × 3 q targets × 13 attenuation levels × 17 normalized oracle-cost levels.
- The coarse calibration AA study contains 864 deterministic conditions.
- Exact ground truth is available for 18 weighted Max-Cut instances with `n={8,10,12}`.
- Each primary and random-coverage `(n,density,seed)` configuration uses its own versioned deterministic random stream, preventing density levels sharing a seed from becoming nested prefixes of one shuffled edge list.
- QAOA uses all 18 primary instances, `p={1,2,3}`, five optimizer seeds per depth, and 270 total ideal-statevector L-BFGS-B optimization runs.
- 269/270 QAOA runs return the optimizer success flag.
- Median-of-instance-median QAOA approximation ratios are 0.655, 0.697, and 0.700 for `p=1,2,3`.
- The best single QAOA run remains a diagnostic and is not treated as representative.
- The simple hill-climbing reference remains a sanity baseline. Two stronger reproducible heuristic references, simulated annealing and tabu search, use 64 runs per instance and a shared cap of 4096 classical objective evaluations per run.
- Host-side simulation scaling through `n=20` is labeled as classical reference-host cost only.
- The analytical threshold-event tier through `n_model=24` is explicitly not Max-Cut ground truth.

## P3-A completed: operational threshold construction
- The threshold definition itself no longer requires `C*`.
- An operational threshold may be infeasible. Exact Tier-I validation records this rather than silently clipping the target to `C*`.
- The spectral/trivial upper bound is a construction anchor, not a claim that the interpolated target is always attainable.

## Still prohibited without a new evidence layer
- quantum speedup or quantum advantage;
- hardware advantage;
- empirical device calibration;
- measured post-transpilation depth, two-qubit-gate count, duration, or energy;
- scalable Max-Cut performance claims beyond the exact micro-instance suite;
- claims that QAOA quality increases monotonically with depth;
- claims that normalized oracle-cost units correspond to a physical backend;
- claims that the operational AA stopping depth is deployable at scale, because exact `rho_tau` is still used in the current Tier-I validation reference;
- claims that a threshold oracle has negligible reversible arithmetic/comparator cost;
- direct runtime/resource superiority from `P_tau` alone without matched physical resource accounting.

## P3-B completed: marked-fraction misspecification robustness
- `rho_estimation_robustness.csv` contains 1,428 conditions over 51 feasible operational thresholds, seven multiplicative marked-fraction estimate factors, two attenuation levels, and two normalized oracle costs.
- The selector receives `rho_hat=f*rho_true` with `f={0.50,0.75,0.90,1.00,1.10,1.25,1.50}` and the selected depth is evaluated retrospectively under the exact Tier-I `rho_true`.
- The primary retention statistic is `Gamma_rho=J_true(k(rho_hat))/J_true(k(rho_true))`; it is a within-model regret/retention quantity, not a speedup.
- At `f=0.90` and `f=1.10`, median retention is 1.000; worst observed retention is 0.954 and 0.960, respectively.
- A factor-two underestimate (`f=0.50`) is materially more damaging: median retention 0.857, IQR 0.797--0.935, worst 0.505.
- Exact `rho_tau` is retained only as a retrospective Tier-I regret reference. The study still does not claim to implement BBHT, fixed-point search, quantum counting, or another estimator-free unknown-solution-count protocol.

## P4-supported architecture-informed oracle layer
- The operational weighted-Max-Cut threshold oracle is represented by a reproducible ripple-style logical template: reusable edge parity, controlled constant accumulation, reversible comparator/phase flag, and full uncomputation.
- The resource ledger contains 54 threshold rows (18 instances x 3 operational levels); resource counts are threshold-independent within an instance under this logical template.
- For n=8,10,12, median modeled oracle Toffoli counts are 420, 644, and 1,088; median modeled oracle logical depths are 533, 821, and 1,353.
- Modeled total logical-qubit ranges are 17--18, 19--21, and 22--23 for n=8,10,12.
- A coupled architecture-informed sweep contains 255 conditions: 51 feasible operational thresholds x 5 synthetic per-logical-depth attenuation values.
- All 255 coupled conditions select k*=0 under the declared gate-equivalent probability-per-resource objective when fixed per-trial overhead is zero, including the zero-attenuation slice.
- This negative result is a configuration conclusion under the stated logical template; it is not a hardware result or a general impossibility claim for amplitude amplification.

## P0-2-supported fixed-overhead boundary layer
- `fixed_overhead_sensitivity.csv` contains 8,085 rows: 1,785 primary and 6,300 coverage conditions over `chi=C_fixed/G_O={0,0.05,0.10,0.25,0.50,1,2}` and five synthetic attenuation levels.
- At zero attenuation, the exact median break-even overhead ratio is `chi_BE=0.163` (IQR 0.098--0.225) for the 51 primary feasible thresholds and 0.168 (0.103--0.239) for the 180 feasible coverage thresholds.
- At `chi=0.25` and zero attenuation, 78.4% of primary and 77.2% of coverage conditions select `k*>0`; at `chi=0.50`, 100% of both tiers select nonzero amplification.
- At `eps_D=5e-4`, median break-even ratios rise to 0.306 primary and 0.301 coverage; at `chi=0.50`, nonzero fractions are 86.3% and 84.4%.
- `C_fixed` is a synthetic per-trial bookkeeping stress coordinate. It is not an estimate of measurement, control, verification, communication, queue, or quantum--classical handoff cost on any backend.
- P0-2 therefore supports a configuration-boundary statement: `k*=0` is robust at the declared zero-overhead point but is not universal once fixed per-trial work is admitted.

## Still prohibited after P4
- calling the logical Toffoli/CNOT/depth template a compiled circuit result;
- mapping gate-equivalent units or epsilon_D to wall-clock time, native gate counts, energy, or a particular processor;
- extrapolating the zero-fixed-overhead k*=0 micro-instance result to arbitrary oracle constructions, fixed-overhead regimes, or large Max-Cut instances;
- claiming physical superiority of classical, QAOA, or AA from these logical bookkeeping quantities.


## G-supported strengthened classical layer
- `classical_budgeted_runs.csv` contains 2,304 raw heuristic runs: 18 instances x 2 methods x 64 independent runs.
- `classical_budgeted_summary.csv` contains 36 instance-method summaries.
- Simulated annealing and tabu search each receive at most 4,096 complete Max-Cut objective evaluations per run.
- Their search logic does not query the exact optimum `C*` or optimum-state identities; exact enumeration is used only for retrospective scoring and target-hit labels.
- For both methods, the median of instance-level median run-best approximation ratios is 1.000 at n=8,10,12, and the median optimum-hit fraction is 1.000 at each size.
- Every one of the 18 instances is solved exactly by at least one of the 64 runs of each method.
- The lowest instance-level optimum-hit fraction is 1.000 for simulated annealing and 0.359375 for tabu search.
- Across all 18 primary instances, both fixed-budget methods have median target-hit fraction 1.000 at q=0.90,0.95,1.00 and at each feasible operational level.

## Still prohibited after G
- treating a classical objective evaluation as physically equivalent to a QAOA circuit evaluation or an amplitude-amplification oracle call;
- claiming classical runtime superiority from the common target-hit probabilities alone;
- describing simulated annealing or tabu search as best-known Max-Cut solvers;
- claiming that a Goemans--Williamson SDP baseline has been implemented;
- any quantum speedup, hardware advantage, or physical resource-superiority statement.

## H-supported paired QAOA optimizer-budget layer
- `qaoa_optimizer_budget_runs.csv` contains 540 ideal-statevector runs: 18 instances x 3 depths x 5 paired initialization seeds x 2 optimizers.
- L-BFGS-B and COBYLA receive the identical initial parameter vector at fixed `(instance,p,seed)` and the same strict cap of 128 exact expectation-objective evaluations.
- `qaoa_optimizer_budget_paired.csv` contains 270 paired optimizer deltas.
- Median-of-instance-median approximation ratios at p=1,2,3 are 0.655, 0.698, 0.697 for L-BFGS-B and 0.691, 0.700, 0.722 for COBYLA.
- COBYLA has the larger paired approximation ratio in 62/90, 47/90, and 59/90 pairs at p=1,2,3; these are descriptive counts only.
- Budget-exhaustion fractions are 0.000/0.378/0.744 for L-BFGS-B and 0.489/0.989/0.989 for COBYLA at p=1/2/3.
- Because the cap binds many deeper runs, H supports a finite-budget optimizer-sensitivity statement, not a general convergence or optimizer-superiority statement.

## J-supported instance-clustered inferential layer
- Primary QAOA depth inference first collapses five L-BFGS-B starts to one median approximation ratio per instance and depth; all 18 fixed primary instances are the paired units.
- The Friedman depth test is chi-square_F=13.768 with p=0.00102.
- Holm-adjusted signed-rank contrasts are: p2-p1 median delta +0.0162, p_Holm=0.0101; p3-p1 +0.0084, p_Holm=0.0101; p3-p2 +0.0067, p_Holm=0.7337.
- The p3-p1 instance-bootstrap 95% interval is [0.0014,0.0333] and its paired rank-biserial effect size is 0.833; p2-p1 has interval [0.0065,0.0612] and rank-biserial 0.754.
- Optimizer inference collapses the five seed-level COBYLA-minus-L-BFGS-B pairs to one median difference per instance and depth before testing.
- Optimizer Holm-adjusted p values are 0.0003, 0.7660, and 0.0013 for p=1,2,3. The p=1 and p=3 bootstrap intervals exclude zero; the p=2 interval includes zero.
- Therefore J supports fixed-suite depth improvements for p=2 and p=3 relative to p=1, but not p=3 relative to p=2. Under the finite 128-evaluation cap it also supports attained-quality COBYLA-minus-L-BFGS-B differences at p=1 and p=3, not a general optimizer-convergence ranking.

## Still prohibited after J
- generalizing the fixed-suite p values to a population of random or structured graphs;
- claiming monotone QAOA improvement with depth;
- claiming COBYLA is generally superior to L-BFGS-B;
- interpreting statistical significance as quantum advantage, runtime advantage, or physical resource superiority;
- treating the 18 deterministic primary benchmark instances as a probability sample from an external graph population.

## K/L-supported expanded exact seed/topology coverage
- `coverage_graphs.csv` contains 1,326 machine-readable weighted edge rows for the 63-instance coverage suite.
- The random coverage component contains 45 exact instances over `n={8,10,12}`, density targets `{0.25,0.50,0.75}`, and seeds `{17,42,73,101,211}`; the original 18 primary instances are an exact subset and remain unchanged.
- The structured coverage component contains 18 exact instances from `cycle`, `cubic_circulant`, and `two_community` families at `n={8,10,12}` with independent weight seeds `{17,42}`.
- `coverage_operational_thresholds.csv` contains 189 exact post-construction validation rows. Operational feasibility is 63/63 at lambda 0.25, 62/63 at lambda 0.40, and 55/63 at lambda 0.55.
- At lambda 0.55, feasibility is 39/45 for random weighted, 6/6 for cycles, 6/6 for 3-regular circulants, and 4/6 for two-community graphs.
- `coverage_coupled_oracle.csv` contains 360 feasible architecture-coupled rows across `eps_D={0,0.001}`; all 360 select `k*=0` under the declared logical probability-per-resource objective at zero fixed per-trial overhead.
- `coverage_hillclimb.csv` is a 64-start descriptive sanity diagnostic. Family-level median ratios are approximately 1.000 random weighted, 0.958 cycle, 1.000 cubic circulant, and 0.977 two-community.
- K/L does not enlarge QAOA inference beyond the 18 primary instances; the additional coverage rows remain descriptive stress testing.

## Still prohibited after K/L
- treating the 63 exact coverage instances as a probability sample from a graph population;
- claiming graph-family-general QAOA behavior because QAOA was not rerun as an inferential study on the K/L coverage suite;
- extrapolating the all-`k*=0` coverage result beyond `n<=12`, the declared structured families, or the stated reversible logical template;
- converting coverage hill-climb outcomes into matched-runtime superiority;
- any hardware, compiler, quantum-advantage, or scalable Max-Cut performance claim not separately evidenced.

## U/W-supported reproducibility lock and preflight
- `.python-version` pins Python 3.13.5 for the canonical validated environment.
- `requirements.txt` pins direct dependencies and `requirements.lock` pins the validated dependency closure, including NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8, and pytest 9.0.2.
- `src/preflight.py` checks canonical file presence, runtime/package drift, SHA-256 consistency against `run_manifest.json`, declared CSV row counts, duplicate canonical files, LaTeX environment balance, and the hardware/compiler claim fences.
- `--source-only` is an editing checkpoint; only full preflight is eligible for final submission synchronization.
- A preflight PASS is an internal reproducibility/package-consistency statement only and does not add hardware, compiler, device-calibration, runtime, or advantage evidence.
- The current regression suite contains 68 tests; P0-1 adds two graph-stream independence tests and P0-2 adds two fixed-overhead selector/boundary tests to the previously synchronized suite.

## Still prohibited after U/W
- treating environment reproducibility as hardware reproducibility;
- treating a passing hash/preflight check as scientific validation beyond the tested contract;
- bypassing full artifact verification when constructing the authoritative submission package;
- any positive hardware, compiler, quantum-advantage, or physical-resource superiority claim without a new evidence layer.

## Next planned evidence layer
P0-1 scientific synchronization is complete in the working copy; regenerate final hashes, compile the manuscript, run full preflight, and only then rebuild the authoritative submission package.


## P1-supported literature/declaration cleanup
- The random graph family is labeled `random_fixed_density`; each `(n,density,seed)` tuple has an independent deterministic RNG stream and an exact edge count. No Erdős–Rényi `G(n,p)` claim is made.
- BBHT is cited only as prior work addressing unknown solution counts; the benchmark still does not claim to implement BBHT, quantum counting, or fixed-point search.
- SupermarQ, QASMBench, and application-oriented quantum benchmarking are cited to position the manuscript as a problem-specific exact-ground-truth microbenchmark rather than a general-purpose hardware benchmark suite.
- The manuscript includes a single-author CRediT statement based on the documented project workflow.
- The final P1 revision records ChatGPT/GPT-5.6 Sol use on 31 August 2026 while explicitly stating that exact historical model IDs for earlier sessions were not consistently recorded.
- Funding remains a manual author-confirmation item; no funding source or no-funding assertion is inferred without evidence.
