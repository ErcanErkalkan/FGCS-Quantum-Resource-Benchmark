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
- QAOA initialization stream version 1 conditions the deterministic random start on graph identity, depth, and optimizer seed; equal external seeds therefore do not reuse the same `x0` across graph instances. The paired L-BFGS-B/COBYLA ablation still uses identical `x0` within each `(instance,p,seed)` pair.
- 269/270 QAOA runs return the optimizer success flag.
- Median-of-instance-median QAOA approximation ratios are 0.673, 0.689, and 0.716 for `p=1,2,3` under the instance-conditioned initialization stream.
- The best single QAOA run remains a diagnostic and is not treated as representative.
- The classical layer includes a numerically certified Goemans--Williamson SDP/rounding reference, plus hill climbing, simulated annealing, and tabu search. The two budgeted heuristics use 64 runs per instance and a shared cap of 4096 classical objective evaluations per run.
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
- physical-backend duration, fidelity, energy, calibration, or hardware-native performance claims;
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
- Exact `rho_tau` is retained only as a retrospective Tier-I regret reference for this misspecification layer. A separate BBHT layer now removes `rho_tau` from the executed growth schedule; fixed-point search and quantum counting remain unimplemented.

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

## P16-supported compiler-native AA cross-check
- GitHub Actions run `33596371482` completed successfully on branch `compiler-native-aa-v1.1` at head `8f9ef9294f393bc3aa0b6ceefde07472a0d2a74c`; artifact ID `9833538936`, digest `sha256:b97c18dc5fc2860719312eb14442d2b1e82f4f68d193b5e4a74e73093d965cc5`.
- Nine seed-17 representatives spanning `n={8,10,12}` and density `{0.25,0.50,0.75}` use the operational `lambda=0.40` threshold and exact Tier-I `rho_tau` only for retrospective configuration scoring.
- Uniform preparation, the executable weighted-threshold oracle, and Grover diffusion are compiled independently to the locked Qiskit `rz/sx/x/cx` basis with optimization level 1 and `seed_transpiler=20260901`; the P16 selector deliberately omits a coupling map so that synthesis cost is not conflated with the separate P14 routing stress test.
- Exhaustive `k=0..64` selection yields `k*=0` for all 9/9 representatives under both total compiled instruction count and compiled depth when fixed per-trial overhead is zero.
- Median fixed-overhead break-even coordinates are `0.147520` and `0.147723` times one compiler-native iteration cost for instruction-count and depth coordinates; observed ranges are approximately `0.0495--0.2455` and `0.0496--0.2460`.
- The compiler-native break-even coordinates and analytical `C_fixed/G_O` use different denominators and are not claimed to be metric-equivalent. No hardware timing, fidelity, energy, calibration, physical-resource, speedup, or quantum-advantage claim follows from P16.

## Still prohibited after P4
- calling the analytical Toffoli/CNOT/depth template itself a compiler output;
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
- any quantum speedup, hardware advantage, or physical resource-superiority statement.

## Reviewer-audit Goemans--Williamson SDP baseline
- `gw_sdp_primary.csv` contains 18 primary exact-tier rows and `gw_sdp_connected_validation.csv` contains 45 connected-validation rows.
- The primal relaxation is `max <L,X>/4` subject to `diag(X)=1` and `X >= 0`; the dual is `min sum(y)` subject to `Diag(y)-L/4 >= 0`.
- The implementation uses an `n`-dimensional Gram factor, 12 deterministic restarts, block-coordinate ascent, and a dual-feasible diagonal shift. A row is accepted only if the numerical primal--dual gap is at most `1e-6`.
- All 63 rows satisfy the numerical certificate. Maximum observed gaps are approximately `2.3e-7` in the primary tier and `4.4e-7` in the connected-validation tier.
- Median SDP upper-bound ratios `SDP/C*` are 1.015 primary and 1.017 connected validation. Exact `C*` is used only for retrospective scoring, not by the SDP solver.
- Each certified SDP factor is rounded with 4,096 deterministic-seed random hyperplanes. Median mean rounded-cut ratios are 0.967 primary and 0.961 connected validation.
- At least one rounded sample reaches the exact optimum on 18/18 primary instances and 44/45 connected-validation instances. These finite-sample optimum-hit counts are descriptive and are not the theoretical Goemans--Williamson guarantee.

## Still prohibited after the GW layer
- claiming symbolic/exact SDP certification; the certificate is floating-point numerical with a declared tolerance;
- treating 4,096 hyperplane samples as exhaustive rounding or as a scalable runtime benchmark;
- claiming that the observed exact-optimum hit fractions generalize to larger Max-Cut instances;
- equating SDP/rounding host cost with QAOA or amplitude-amplification physical resources.

## H-supported paired QAOA optimizer-budget layer
- `qaoa_optimizer_budget_runs.csv` contains 540 ideal-statevector runs: 18 instances x 3 depths x 5 paired initialization seeds x 2 optimizers.
- L-BFGS-B and COBYLA receive the identical initial parameter vector at fixed `(instance,p,seed)` and the same strict cap of 128 exact expectation-objective evaluations.
- `qaoa_optimizer_budget_paired.csv` contains 270 paired optimizer deltas.
- Median-of-instance-median approximation ratios at p=1,2,3 are 0.673, 0.702, 0.696 for L-BFGS-B and 0.691, 0.712, 0.718 for COBYLA.
- COBYLA has the larger paired approximation ratio in 50/90, 47/90, and 52/90 pairs at p=1,2,3; these are descriptive counts only.
- Budget-exhaustion fractions are 0.011/0.344/0.789 for L-BFGS-B and 0.522/0.978/1.000 for COBYLA at p=1/2/3.
- Because the cap binds many deeper runs, H supports a finite-budget optimizer-sensitivity statement, not a general convergence or optimizer-superiority statement.

## J-supported instance-clustered inferential layer
- Primary QAOA depth inference first collapses five L-BFGS-B starts to one median approximation ratio per instance and depth; all 18 fixed primary instances are the paired units.
- The Friedman depth test is chi-square_F=20.333 with p=0.00004.
- Holm-adjusted signed-rank contrasts are: p2-p1 median delta +0.0234, p_Holm=0.0080; p3-p1 +0.0379, p_Holm=0.0002; p3-p2 +0.0307, p_Holm=0.0080.
- The p3-p1 instance-bootstrap 95% interval is [0.0179,0.1369] and its paired rank-biserial effect size is 0.942; p2-p1 has interval [0.0045,0.0648] and rank-biserial 0.731; p3-p2 has interval [0.0045,0.0428] and rank-biserial 0.743.
- Optimizer inference collapses the five seed-level COBYLA-minus-L-BFGS-B pairs to one median difference per instance and depth before testing.
- Optimizer Holm-adjusted p values are 0.0911, 0.0911, and 0.0911 for p=1,2,3. All three bootstrap intervals include zero (the p=1 lower endpoint is numerically indistinguishable from zero).
- Therefore J supports fixed-suite attained-quality differences for all three ordered depth contrasts under the instance-conditioned initialization protocol. Under the finite 128-evaluation cap it does not support a Holm-significant COBYLA-minus-L-BFGS-B difference at any tested depth; this is not a general optimizer-convergence ranking.

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
- any hardware, quantum-advantage, or scalable Max-Cut performance claim not separately evidenced.

## U/W-supported reproducibility lock and preflight
- `.python-version` pins Python 3.13.5 for the canonical validated environment.
- `requirements.txt` pins direct dependencies and `requirements.lock` pins the validated dependency closure, including NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8, and pytest 9.0.2.
- `src/preflight.py` checks canonical file presence, runtime/package drift, SHA-256 consistency against `run_manifest.json`, declared CSV row counts, duplicate canonical files, LaTeX environment balance, and the hardware/compiler claim fences.
- `--source-only` is an editing checkpoint; only full preflight is eligible for final submission synchronization.
- A preflight PASS is an internal reproducibility/package-consistency statement only; compiler evidence is supplied separately by the locked Qiskit artifact, and a PASS does not add hardware, device-calibration, runtime, or advantage evidence.
- The active reviewer-revision regression suite contains 89 tests after adding structural validation, certified GW, BBHT, resource-scalarization, and classical-budget-curve checks. The frozen v1.0.0 release remains separately archived with its earlier 68-test validation state.

## Still prohibited after U/W
- treating environment reproducibility as hardware reproducibility;
- treating a passing hash/preflight check as scientific validation beyond the tested contract;
- bypassing full artifact verification when constructing the authoritative submission package;
- any positive hardware, quantum-advantage, or physical-resource superiority claim without a new evidence layer.

## Next planned evidence layer
P0-1 scientific synchronization is complete in the working copy; regenerate final hashes, compile the manuscript, run full preflight, and only then rebuild the authoritative submission package.


## P1-supported literature/declaration cleanup
- The random graph family is labeled `random_fixed_density`; each `(n,density,seed)` tuple has an independent deterministic RNG stream and an exact edge count. No Erdős–Rényi `G(n,p)` claim is made.
- BBHT is implemented as a separate unknown-solution-count control policy with `lambda=6/5`; its schedule never consumes exact `rho_tau`. Quantum counting and fixed-point search remain unimplemented.
- SupermarQ, QASMBench, and application-oriented quantum benchmarking are cited to position the manuscript as a problem-specific exact-ground-truth microbenchmark rather than a general-purpose hardware benchmark suite.
- The manuscript includes a single-author CRediT statement based on the documented project workflow.
- The final P1 revision records ChatGPT/GPT-5.6 Sol use on 31 August 2026 while explicitly stating that exact historical model IDs for earlier sessions were not consistently recorded.
- Funding remains a manual author-confirmation item; no funding source or no-funding assertion is inferred without evidence.

## Reviewer-audit structural validation layer
- `primary_graph_diagnostics.csv` records exact structural metadata for all 18 primary instances: 5 are disconnected, 2 are bipartite, and 5 contain at least one isolated vertex.
- `coverage_graph_diagnostics.csv` records the same audit for all 63 expanded-coverage instances: 10 are disconnected and 13 are bipartite.
- The original primary and coverage instances are retained unchanged; no post hoc graph replacement is performed after observing these properties.
- A separate connected, non-bipartite exact validation tier contains 45 deterministic fixed-density weighted instances over `n={10,12,14}`, densities `{0.25,0.50,0.75}`, and seeds `{17,42,73,101,211}`.
- All 45 validation graphs are connected, non-bipartite, and contain no isolated vertices by an explicit deterministic rejection-sampling contract.
- Operational feasibility in the connected validation tier is 45/45, 45/45, and 36/45 at `lambda={0.25,0.40,0.55}`.
- Across 126 feasible graph/threshold combinations and `eps_D={0,0.001}`, all 252 architecture-coupled zero-fixed-overhead conditions select `k*=0`.
- At zero attenuation, the connected-validation median fixed-overhead break-even ratio is 0.121 (IQR 0.065--0.190) across all feasible operational thresholds; at `chi=0.25`, 90.5% select nonzero amplification and at `chi=0.50` all do.
- Conditioning on connectedness and non-bipartiteness is a structural confounder control, not a proof that the resulting instances are computationally hard or population-representative.

## Still prohibited after structural validation
- claiming that connected/non-bipartite conditioning proves Max-Cut hardness;
- treating the 45 validation instances as a probability sample from a graph population;
- extending QAOA inferential claims to the connected validation tier, because QAOA has not yet been rerun there;
- converting the persistence of `k*=0` into a hardware or large-scale impossibility claim;
- removing or hiding the original disconnected/bipartite benchmark rows after inspection.


## P5-supported BBHT unknown-solution-count layer
- `bbht_operational_primary.csv` contains 204 rows: 51 feasible primary operational thresholds x `eps_D={0,1e-4}` x `chi={0,0.25}`.
- `bbht_operational_connected_validation.csv` contains 504 rows: 126 feasible connected-validation thresholds over the same two attenuation and two fixed-overhead coordinates.
- The BBHT schedule uses `m=1`, `lambda=6/5`, uniformly randomized Grover depth over the non-negative integers below `m`, and `m <- min(lambda*m,sqrt(N))` after failure. It does not receive `rho_tau`.
- Exact Tier-I `rho_tau` is used only to evaluate the schedule's expected trials, Grover iterations, and logical gate-equivalent resource-to-success; the saturated stage is evaluated with an exact geometric tail rather than Monte Carlo.
- At `eps_D=0, chi=0`, BBHT is never resource-preferred to repeated uniform sampling in either exact tier; median BBHT/uniform resource ratios are 54.651 primary and 57.797 connected validation.
- At `eps_D=0, chi=0.25`, median BBHT/uniform resource ratios fall to 0.769 and 0.643, with BBHT preferred to uniform in 76.5% and 90.5% of feasible primary/connected-validation threshold conditions.
- Under that same coordinate, BBHT remains more expensive than the oracle-informed exact-rho selector, with median BBHT/oracle ratios 1.170 primary and 1.247 connected validation.
- At `eps_D=1e-4, chi=0.25`, BBHT is preferred to uniform in 47.1% of primary and 34.9% of connected-validation conditions.
- P5 therefore supports an operational statement: unknown marked fraction narrows, but does not eliminate, the fixed-overhead region in which amplification can be resource-preferred under the declared logical model.

## Still prohibited after P5
- claiming that the BBHT expected-cost rows are hardware runtime measurements or executed adaptive quantum-control experiments;
- claiming that exact `rho_tau` is required by the BBHT schedule itself; it is used only for retrospective exact-tier scoring;
- treating `chi` or `eps_D` as calibrated backend quantities;
- claiming BBHT is universally superior to uniform repetition or to an oracle-informed selector;
- claiming implementation of quantum counting or fixed-point search.


## P6-supported logical resource scalarization sensitivity
- The canonical mixed bookkeeping score remains `G_eq=N1+N_CNOT+6*N_T`, but P6 recomputes the selector for `alpha_T={1,4,6,10}` without changing raw Toffoli, CNOT, single-qubit, ancilla, or logical-depth counts.
- Fixed overhead is anchored to the canonical `alpha_T=6` oracle cost (`chi_6`) so changing the Toffoli weight does not silently rescale the external fixed-work coordinate.
- `resource_scalarization_primary.csv` contains 1,632 rows: 51 feasible primary thresholds x 4 Toffoli weights x 2 attenuation levels x 4 canonical fixed-overhead ratios.
- `resource_scalarization_connected_validation.csv` contains 4,032 rows over 126 feasible connected-validation thresholds on the same grid.
- At `eps_D=0, chi_6=0`, all primary and connected-validation conditions select `k*=0` for every `alpha_T` in `{1,4,6,10}`.
- Primary median break-even ratios in canonical-alpha6 oracle units are 0.064, 0.124, 0.163, and 0.243 for `alpha_T=1,4,6,10`; connected-validation medians are 0.047, 0.091, 0.121, and 0.180.
- At `eps_D=0, chi_6=0.25`, primary nonzero-amplification fractions are 1.000, 0.961, 0.784, and 0.549 across increasing alpha; connected-validation fractions are 1.000, 0.976, 0.905, and 0.667.
- P6 therefore supports robustness of the zero-fixed-overhead boundary to the tested Toffoli weighting range, while showing that the fixed-overhead transition location is scalarization-dependent.

## Still prohibited after P6
- treating `alpha_T=6` or any tested weight as a backend-native or fault-tolerant physical equivalence;
- interpreting cross-alpha gate-equivalent magnitudes as measured runtime or energy;
- claiming the fixed-overhead transition is invariant to resource scalarization;
- extrapolating the compiler-locked counts beyond the declared Qiskit version, basis, seed, synthesis settings, and synthetic topology.


## P7-supported classical objective-evaluation budget curve
- `CLASSICAL_BUDGET_CURVE={64,128,256,512,1024,4096}` replaces reliance on a single 4096-evaluation endpoint for classical interpretation.
- `classical_budget_curve_runs.csv` contains 13,824 rows: 18 instances x 2 methods x 64 runs x 6 budgets.
- `classical_budget_curve_summary.csv` contains 216 instance-method-budget summaries; `classical_budget_curve_aggregate.csv` contains 12 method-budget aggregates.
- At 64 objective evaluations per run, both simulated annealing and tabu search have median-of-instance-median approximation ratio 1.000; median instance optimum-hit fractions are 0.555 and 0.789, respectively.
- At every tested budget, all 18 primary instances are solved optimally at least once across the 64 runs of each method.
- Tabu search reaches median instance optimum-hit fraction 1.000 at budget 128; simulated annealing reaches 1.000 at budget 1024.
- The 4096 endpoint therefore does not create the conclusion that these micro-instances are classically easy; the conclusion is already visible at substantially smaller objective-evaluation budgets.

## Still prohibited after P7
- treating an objective evaluation as a unique-state visit or an exhaustive-search fraction;
- equating classical objective-evaluation budgets to QAOA circuit evaluations, shots, wall-clock time, or amplitude-amplification oracle resources;
- generalizing micro-instance classical ease to large Max-Cut instances or industrial solvers;
- claiming classical runtime superiority or quantum disadvantage from this within-classical budget curve.


## P8-supported dense operational-lambda audit
- `DENSE_OPERATIONAL_LEVELS` spans `lambda=0,0.05,...,1.00`; the three declared levels 0.25, 0.40, and 0.55 are embedded in this 21-point grid.
- `dense_operational_lambda_primary.csv` contains 378 rows (18 x 21); `dense_operational_lambda_connected_validation.csv` contains 945 rows (45 x 21); the summary contains 42 tier-level rows.
- Primary feasibility at lambda 0/.25/.40/.55/.75/1.00 is 18/18, 18/18, 18/18, 15/18, 5/18, and 2/18.
- Connected-validation feasibility at the same levels is 45/45, 45/45, 45/45, 36/45, 12/45, and 0/45.
- Every feasible dense-sweep condition selects `k*=0` at zero fixed overhead and zero attenuation under the declared logical resource model.
- P8 therefore shows that the reported operational levels lie on a broader strictness/feasibility curve rather than being the only inspected threshold settings.

## Still prohibited after P8
- claiming that the dense sweep identifies a universally optimal lambda;
- using retrospective feasibility or C* ratios as inputs to threshold construction;
- treating the 21 lambda values as independent graph replicates;
- interpreting the dense-sweep logical resource result as compiler or hardware evidence.


## P10-supported 20-start QAOA initialization stability
- The canonical five-start QAOA analysis is nested inside a 20-start L-BFGS-B audit using the same instance-conditioned initialization stream (seeds 0--19).
- The audit contains 1,080 runs: 18 instances x 3 depths x 20 starts.
- Median-of-instance-median approximation ratios are 0.661, 0.691, and 0.707 for p=1,2,3.
- The 20-start Friedman statistic is 26.778 (p=1.53e-6).
- Holm-adjusted depth contrasts remain positive and significant: p2-p1 median delta +0.0126 (p_Holm=0.000328), p3-p1 +0.0334 (p_Holm=2.29e-5), p3-p2 +0.0169 (p_Holm=0.000107); all three instance-bootstrap 95% intervals exclude zero.
- This strengthens initialization robustness within the fixed 18-instance benchmark only; it does not support population-level graph or hardware generalization.


## Compiler-locked Qiskit validation evidence
- A separate GitHub Actions run (`33558640895`) executed Qiskit 2.4.2 on Python 3.12.14 with basis `rz/sx/x/cx`, optimization level 1, and `seed_transpiler=20260901`; the workflow completed successfully and uploaded artifact `compiler-validation-qiskit-2.4.2`.
- The compiler ledger contains 66 rows: 54 line-routed QAOA circuits (18 instances x p=1,2,3), 9 basis-decomposed operational threshold oracles, and 3 sparse line-routed oracle representatives.
- QAOA median compiled depth is 78.0/180.5/260.5 and median CX count is 97.0/234.5/348.0 at p=1/2/3.
- The independent reversible threshold-oracle implementation passes an exhaustive 8/8 computational-basis semantic test on a small weighted triangle. Across nine basis-decomposed representative operational oracles, median compiled depth is 110,317 and median CX count is 53,794.
- Sparse n=8/10/12 oracle representatives routed on a bidirectional line have compiled depths 41,539/65,177/130,085 and CX counts 30,655/48,636/97,268.
- A matched nine-row abstraction-gap audit gives a median compiler-basis-depth / analytical-oracle-depth ratio of 140.5x (IQR 138.0--168.0x) and a median compiler-qubit / analytical-logical-qubit ratio of 1.61x. These ratios compare depth and qubit coordinates only; CX is not identified with analytical CNOT/Toffoli bookkeeping.
- These counts are compiler-locked synthetic-topology evidence. They are not device execution, calibration, duration, fidelity, energy, or quantum-advantage evidence. The executable oracle realization is deliberately separate from the analytical ripple-style resource template; no exact count agreement is claimed.

## Still prohibited after compiler validation
- treating line-topology transpilation as a specific hardware backend result;
- using the compiled CX/depth numbers as elapsed time, error probability, energy, or fault-tolerant physical resource counts;
- claiming that the compiler realization validates the exact analytical gate-count formulas;
- generalizing the compiler counts to other Qiskit versions, synthesis plugins, optimization levels, compiler seeds, coupling maps, or hardware architectures.

## Threshold-aligned QAOA objective sensitivity

- Canonical evidence: `results/qaoa_threshold_training_budget_runs.csv` (270 runs), `results/qaoa_threshold_training_budget_paired.csv` (270 matched rows), `results/qaoa_threshold_training_budget_instance_summary.csv` (54 instance-depth rows), and `results/qaoa_threshold_training_budget_inference.csv` (3 depth-level inference rows).
- Pairing is exact at `(instance,p,optimizer_seed)`: expectation-trained and threshold-trained L-BFGS-B runs use identical initial parameter vectors and the same strict 128-objective-evaluation cap.
- At `p=1/2/3`, median instance-level operational `lambda=0.40` hit probability changes from `0.0683/0.1187/0.1007` to `0.0874/0.1618/0.1868`; median paired gains are `+0.0159/+0.0173/+0.0174`, with Holm-adjusted p-values `0.0039/0.0020/0.0385`.
- Median approximation-ratio changes are `-0.0012/-0.0045/-0.0140`; therefore the allowed claim is an **objective trade-off**. Do not claim threshold-trained QAOA is universally superior.
