# FGCS Quantum Resource Benchmark — canonical project

**Only target:** Future Generation Computer Systems (Elsevier), intended for the active special collection **Advances in Quantum Computing: Methods, Algorithms, and Systems. Vol. IV**.

This repository is the single canonical project for the current FGCS manuscript. The computational scope is weighted Max-Cut, threshold-oriented resource-aware amplitude amplification, QAOA, and transparent classical references. No factoring-track material belongs in this project.

## Current paper
**Working title:** *Resource-Aware Amplitude Amplification for Hybrid Quantum–Classical Workflows: A Reproducible Max-Cut Benchmark with QAOA and Classical References*

The manuscript is deliberately neutral. It does not claim hardware speedup or quantum advantage.

## Threshold semantics
Two threshold layers are deliberately separated.

1. **Operational threshold construction (primary):** no optimum value is used to construct the threshold.
   - Random-cut anchor: `mu_rnd = 0.5 * sum(edge weights)`.
   - Graph upper bound: `U_spec = min(total edge weight, n*lambda_max(L)/4)`.
   - Operational threshold: `tau_lambda = ceil(mu_rnd + lambda*(U_spec-mu_rnd))`.
   - Declared levels: `lambda={0.25,0.40,0.55}`.
   - Exact enumeration is used only after construction to label feasibility, exact `rho_tau`, and retrospective `tau/C*` in Tier I.
   - Feasible exact instances: 18/18, 18/18, and 15/18 at the three levels.

2. **Benchmark-normalized calibration thresholds:** `tau_q=ceil(q*C*)`, with `q={0.90,0.95,1.00}`. These are retained only as an exact-tier calibration/sensitivity axis and are not presented as deployable threshold construction.

## Canonical evidence
- 18 primary exact weighted Max-Cut instances: `n={8,10,12}`, density `{0.25,0.50,0.75}`, seeds `{17,42}`.
- Each `(n,density,seed)` random instance uses its own versioned deterministic random stream; density levels sharing a seed are not nested prefixes of one shuffled edge list.
- K/L exact coverage tier: 45 random weighted instances using seeds `{17,42,73,101,211}` plus 18 structured weighted instances (`cycle`, `cubic_circulant`, `two_community`), for 63 exact coverage instances total.
- Coverage operational validation: 189 graph/threshold rows; feasibility is 63/63, 62/63, and 55/63 at `lambda={0.25,0.40,0.55}`.
- Coverage architecture-coupled diagnostic: 360 feasible conditions at `eps_D={0,0.001}`; all select `k*=0` under the declared logical resource objective when fixed per-trial overhead is zero.
- 54 operational-threshold validation rows.
- 432 operational common-target rows after adding fixed-budget simulated annealing and tabu search to uniform sampling, the AA reference, QAOA, and hill climbing.
- 1,428 marked-fraction misspecification conditions across feasible operational thresholds, seven rho-estimate factors, two attenuation levels, and two oracle-cost levels.
- 864 coarse benchmark-normalized AA calibration conditions.
- 11,934 dense threshold-aware resource-uncertainty conditions: 18 instances × 3 q levels × 13 attenuation levels × 17 oracle-cost levels.
- 8,085 fixed-overhead sensitivity rows across primary and coverage feasible thresholds, five attenuation levels, and `C_fixed/G_O={0,0.05,0.10,0.25,0.50,1,2}`.
- 270 primary ideal-statevector L-BFGS-B QAOA optimization runs over all 18 primary instances.
- 540 paired QAOA optimizer-budget runs: L-BFGS-B vs COBYLA, same initializations, 128 exact expectation-objective evaluations per run maximum.
- Instance-clustered QAOA inference: 18 fixed primary instances as paired units, Friedman depth test, Wilcoxon signed-rank contrasts with Holm correction, matched-pairs rank-biserial effect sizes, and 20,000-resample instance bootstrap intervals.
- Host-side simulation scaling diagnostic through `n=20`.
- Analytical threshold-event sensitivity through `n_model=24` (explicitly not Max-Cut ground truth).
- 256-start hill climbing on every exact instance.
- Simulated annealing and tabu search: 64 independent runs per instance and method, each capped at 4096 complete objective evaluations; 2,304 raw runs and 36 instance-method summaries.
- SHA-256-bearing run manifest.
- No hardware, compiler, empirical device-calibration, or quantum-advantage claims.

## Current evidence boundary
The operational threshold itself no longer depends on `C*`. Marked-fraction sensitivity is quantified for estimate factors `{0.50,0.75,0.90,1.00,1.10,1.25,1.50}` using exact Tier-I `rho_tau` only as retrospective regret ground truth. The architecture-informed reversible oracle layer now couples logical oracle burden to iteration depth, and its 255 operational conditions all select `k*=0` under the declared gate-equivalent objective when fixed per-trial overhead is zero. A separate P0-2 stress test shows this is conditional: at zero attenuation the median break-even fixed-overhead ratios are 0.163 oracle-cost units in the primary tier and 0.168 in coverage. The strengthened classical layer shows that simulated annealing and tabu search are both highly effective on the exact micro-instances under an equal within-classical objective-evaluation cap. None of these statements is a physical runtime comparison. The paired QAOA optimizer layer now compares L-BFGS-B and COBYLA under the same 128-objective-evaluation cap and identical initializations. The instance-clustered inferential layer is now complete. On the fixed 18-instance primary suite the depth Friedman test gives p=0.00102; both p=2 versus p=1 and p=3 versus p=1 survive Holm correction (p_Holm=0.0101 for both), while p=3 versus p=2 does not. Under the finite 128-evaluation optimizer budget, COBYLA-minus-L-BFGS-B contrasts survive Holm correction at p=1 (0.0003) and p=3 (0.0013), but not at p=2 (0.7660). These tests condition on the fixed benchmark and are not population-level graph inference or physical-resource evidence. K/L now adds a separate 63-instance exact seed/topology coverage tier. It is descriptive stress testing only: the 18-instance primary QAOA inferential sample is not enlarged by the additional coverage tier, and no population-level graph-family claim is made.

## Reproduce
```bash
python src/benchmark.py
python src/render_tables.py
python src/render_figures.py
python src/render_p2_figures.py
python src/finalize_manifest.py
pytest -q
# Final package checkpoint after all generated artifacts are present:
python src/preflight.py --json-out results/preflight_full_report.json
```

The finalization step hashes every LaTeX table and PDF figure actually included by `manuscript/main.tex`, as well as the bibliography and executable source set. Full preflight therefore fails if a rendered manuscript dependency changes after manifest finalization.

## Canonical layout
- `manuscript/` — the only manuscript and reference database.
- `src/` — the only computational implementation.
- `data/` — exact graph definitions.
- `results/` — machine-generated results, tables, tests, and manifest.
- `figures/` — generated figures.
- `tests/` — consistency tests.
- `reproducibility/` — evidence/claim policy and phase records.
- `submission/` — FGCS-only submission files; not authoritative until final preflight.

## Architecture-informed oracle layer
- The weighted threshold oracle now has an explicit ripple-style logical resource template: edge parity, controlled weighted accumulation, threshold comparison/phase mark, and full uncomputation.
- The canonical ledger records modeled logical qubits, Toffoli, CNOT, logical depth, and a transparent gate-equivalent bookkeeping score. These are architecture-informed counts, not transpiled backend metrics.
- Oracle cost and attenuation are coupled through the same logical-depth model in 255 feasible operational-threshold conditions (51 feasible thresholds x 5 synthetic per-depth attenuation values).
- Under this declared logical resource objective with zero fixed per-trial overhead, all 255 coupled conditions select k*=0.
- P0-2 adds a fixed-overhead coordinate `chi=C_fixed/G_O`. At zero attenuation, median break-even `chi` is 0.163 (IQR 0.098--0.225) in the primary tier and 0.168 (0.103--0.239) in coverage. At `chi=0.25`, nonzero amplification is selected in 78.4% and 77.2% of primary/coverage conditions; at `chi=0.50`, all zero-attenuation conditions select `k*>0`.
- The fixed-overhead coordinate is synthetic logical bookkeeping, not measured control/readout/verification/handoff cost. The zero-round result is therefore retained as a boundary result, not a general statement that amplitude amplification is ineffective.

## Strengthened classical reference layer
- `classical_budgeted_runs.csv`: 2 methods x 18 instances x 64 runs = 2,304 raw runs.
- `classical_budgeted_summary.csv`: 36 instance-method summaries.
- Per-run cap: 4,096 complete Max-Cut objective evaluations for both simulated annealing and tabu search.
- Neither search algorithm queries `C*`; exact enumeration is used only for retrospective ratios and hit labels.
- Both methods have median run-best approximation ratio 1.000 and median optimum-hit fraction 1.000 at each tested `n`.
- Every exact instance is solved optimally by at least one run of each method.
- These budgets are comparable only within the classical layer and are not mapped to QAOA or amplitude-amplification resources.

## Paired QAOA optimizer-budget layer
- `qaoa_optimizer_budget_runs.csv`: 18 instances x 3 depths x 5 seeds x 2 optimizers = 540 runs.
- `qaoa_optimizer_budget_paired.csv`: 270 paired L-BFGS-B/COBYLA deltas at identical instance, depth, and initialization seed.
- Per-run cap: 128 exact statevector expectation-objective evaluations; early convergence is allowed.
- Median instance-level approximation ratios at p=1/2/3: L-BFGS-B = 0.655/0.698/0.697; COBYLA = 0.691/0.700/0.722.
- COBYLA has the larger paired approximation ratio in 62/90, 47/90, and 59/90 comparisons at p=1,2,3. These are descriptive counts, not inferential or physical-runtime claims.
- Evaluation-cap exhaustion is substantial for deeper settings, so this is a finite-budget robustness study rather than a fully converged optimizer ranking.


## Instance-clustered inferential layer
- Repeated optimizer starts are not treated as independent graph replicates. Five starts are first collapsed within each instance.
- Primary depth omnibus: Friedman statistic 13.768, p=0.00102 across the 18 matched instance medians.
- Holm-adjusted depth contrasts: p2-p1 median delta +0.0162, p_Holm=0.0101; p3-p1 +0.0084, p_Holm=0.0101; p3-p2 p_Holm=0.7337.
- Finite-budget optimizer contrasts use instance-median COBYLA-minus-L-BFGS-B deltas. Holm-adjusted p values are 0.0003, 0.7660, and 0.0013 at p=1,2,3; p=1 and p=3 pass the 0.05 multiplicity-corrected threshold under the fixed 128-evaluation budget.
- Confidence intervals are 20,000-resample percentile bootstraps over the 18 instances. Rank-biserial correlations are reported as paired effect sizes.
- These tests describe consistency within the fixed deterministic suite and do not justify population generalization, hardware performance claims, or physical resource equivalence.

## K/L expanded exact seed/topology coverage
- Random seed expansion: 45 exact fixed-density random weighted instances across `n={8,10,12}`, densities `{0.25,0.50,0.75}`, and five seeds `{17,42,73,101,211}`. The original 18 primary instances are an exact subset. Each `(n,density,seed)` tuple uses its own deterministic RNG stream and exactly the declared edge count; the family label is `random_fixed_density`, not Erdős–Rényi `G(n,p)`.
- Structured topology expansion: 18 exact weighted instances from `cycle`, `cubic_circulant`, and `two_community` families at `n={8,10,12}` with weight seeds `{17,42}`.
- Combined K/L coverage: 63 exact instances, 1,326 edge-ledger rows, 189 operational-threshold validation rows, 63 coverage hill-climb diagnostics, and 360 feasible architecture-coupled rows at `eps_D={0,0.001}`.
- Operational feasibility across the 63 instances is 63/63 at `lambda=0.25`, 62/63 at `lambda=0.40`, and 55/63 at `lambda=0.55`.
- All 360 architecture-coupled coverage rows select `k*=0` at zero fixed per-trial overhead; the P0-2 boundary sweep shows that this conclusion changes as synthetic fixed overhead rises. It remains a logical-model result, not a hardware or large-scale claim.
- The 18-instance primary QAOA inference remains separate from the added coverage rows and is not reinterpreted as population inference after the coverage expansion.



## U/W environment lock and preflight
- Python is pinned to `3.13.5` in `.python-version`.
- Direct dependencies are exactly pinned in `requirements.txt`; the validated transitive closure is pinned in `requirements.lock`.
- `src/preflight.py` is the canonical fail-closed package validator. Full mode verifies runtime/package versions, manifest SHA-256 values, manifest-declared CSV row counts, duplicate canonical files, LaTeX environment balance, and claim fences.
- `--source-only` is permitted during editing, but it deliberately skips result-artifact hash/count validation and is not the final submission check.
- A preflight PASS certifies internal package synchronization only; it is not compiler, hardware, or performance evidence.
- The current regression suite contains 68 tests; P0-1 adds two graph-stream independence checks and P0-2 adds two fixed-overhead boundary/zero-overhead compatibility checks.


## Repository citation and preservation
- Intended public repository: `https://github.com/ErcanErkalkan/FGCS-Quantum-Resource-Benchmark`.
- `CITATION.cff` provides GitHub/Zenodo citation metadata.
- The first archival release is planned as `v1.0.0` after the repository is enabled in Zenodo.
- Software is released under the **BSD 3-Clause License (`BSD-3-Clause`)**; see `LICENSE` and `LICENSE_SCOPE.md`.
- Funding status is author-confirmed: **no specific grant funding** from public, commercial, or not-for-profit funding agencies.
- Manuscript/article files are publication materials and are not relicensed by the repository software license.
- `ZENODO_RELEASE_GUIDE.md` records the exact publication sequence and DOI back-link procedure.

## Submission formatting
- Final FGCS manuscript uses `\documentclass[5p,times]{elsarticle}`.
- The compiled manuscript is kept within the 18-page FGCS special-issue limit.
- Final compiled manuscript: **15 pages**, double-column, with no overfull boxes or unresolved citations/references.
