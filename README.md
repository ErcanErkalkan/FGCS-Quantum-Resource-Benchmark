# FGCS Quantum Resource Benchmark — canonical project

## Archived release
Version **1.1.0** is archived on Zenodo with version DOI **[10.5281/zenodo.22272778](https://doi.org/10.5281/zenodo.22272778)**.
The corresponding GitHub release is **[v1.1.0](https://github.com/ErcanErkalkan/FGCS-Quantum-Resource-Benchmark/releases/tag/v1.1.0)**.
This DOI identifies the archived v1.1.0 snapshot; subsequent commits on main do not alter that archived release.

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
- Expanded exact coverage tier: 45 random weighted instances using seeds `{17,42,73,101,211}` plus 18 structured weighted instances (`cycle`, `cubic_circulant`, `two_community`), for 63 exact coverage instances total.
- Coverage operational validation: 189 graph/threshold rows; feasibility is 63/63, 62/63, and 55/63 at `lambda={0.25,0.40,0.55}`.
- Coverage architecture-coupled diagnostic: 360 feasible conditions at `eps_D={0,0.001}`; all select `k*=0` under the declared logical resource objective when fixed per-trial overhead is zero.
- 54 operational-threshold validation rows.
- 432 operational common-target rows after adding fixed-budget simulated annealing and tabu search to uniform sampling, the AA reference, QAOA, and hill climbing.
- 1,428 marked-fraction misspecification conditions across feasible operational thresholds, seven rho-estimate factors, two attenuation levels, and two oracle-cost levels.
- BBHT unknown-solution-count validation: 204 primary and 504 connected-validation expected-cost rows over `eps_D={0,1e-4}` and `chi={0,0.25}`; the BBHT schedule never consumes exact `rho_tau`.
- Logical resource scalarization sensitivity: 1,632 primary and 4,032 connected-validation rows over Toffoli weights `alpha_T={1,4,6,10}`, two attenuation levels, and four fixed-overhead coordinates anchored to the canonical alpha-6 oracle cost.
- Dense operational-threshold audit: 21 levels `lambda=0,0.05,...,1.0`, producing 378 primary rows, 945 connected-validation rows, and 42 tier-level summaries. The three declared operating points are embedded in this full-grid sensitivity.
- 864 coarse benchmark-normalized AA calibration conditions.
- 11,934 dense threshold-aware resource-uncertainty conditions: 18 instances × 3 q levels × 13 attenuation levels × 17 oracle-cost levels.
- 8,085 fixed-overhead sensitivity rows across primary and coverage feasible thresholds, five attenuation levels, and `C_fixed/G_O={0,0.05,0.10,0.25,0.50,1,2}`.
- 270 primary ideal-statevector L-BFGS-B QAOA optimization runs over all 18 primary instances, using versioned instance-conditioned initialization streams so equal external seeds do not reuse the same x0 across graphs.
- QAOA initialization stream version 1 conditions on graph identity, depth, and external optimizer seed; all 18 graphs have distinct `x0` at fixed `(p,seed)`, while L-BFGS-B/COBYLA pairs retain identical `x0` within each `(instance,p,seed)`.
- 540 paired QAOA optimizer-budget runs: L-BFGS-B vs COBYLA, same initializations, 128 exact expectation-objective evaluations per run maximum.
- Instance-clustered QAOA inference: 18 fixed primary instances as paired units, Friedman depth test, Wilcoxon signed-rank contrasts with Holm correction, matched-pairs rank-biserial effect sizes, and 20,000-resample instance bootstrap intervals.
- Host-side simulation scaling diagnostic through `n=20`.
- Analytical threshold-event sensitivity through `n_model=24` (explicitly not Max-Cut ground truth).
- 256-start hill climbing on every exact instance.
- Simulated annealing and tabu search: 64 independent runs per instance and method across objective-evaluation budgets `{64,128,256,512,1024,4096}`; 13,824 budget-curve raw runs, 216 instance-method-budget summaries, and 12 aggregate rows. The 4096 setting is retained as a high-budget endpoint, not the sole classical evidence.
- Goemans--Williamson SDP: 18 primary + 45 connected-validation exact rows, each numerically bracketed by a primal/dual certificate with gap <= 1e-6; 4,096 deterministic-seed hyperplane rounds per instance.
- SHA-256-bearing run manifest.
- Compiler-locked Qiskit 2.4.2 validation: 66 transpilation rows under fixed `rz/sx/x/cx`, optimization level 1, `seed_transpiler=20260901`, with an exhaustive 8/8 small-oracle semantic check. No physical-hardware, empirical device-calibration, or quantum-advantage claims.

## Current evidence boundary
The compiler evidence is now an explicit fourth implementation layer: 54 primary QAOA circuits routed on a bidirectional line topology have median compiled depths `78.0/180.5/260.5` and median CX counts `97.0/234.5/348.0` at `p=1/2/3`; nine independently executable weighted-threshold oracles have median basis-decomposed depth `110317` and CX count `53794`, while sparse `n=8/10/12` line-routed oracle representatives have depths `41539/65177/130085`. These are reproducible Qiskit compiler counts on a synthetic topology, not hardware timing/fidelity/energy evidence. A nine-row matched abstraction-gap ledger reports a median compiler-to-analytical oracle-depth ratio of 140.5x (IQR 138.0-168.0x) and median qubit ratio of 1.61x; gate alphabets are deliberately not equated. The compiler oracle is therefore kept separate from the analytical ripple-style count model.

**Compiler-native AA cross-check (P16).** On nine seed-17 representatives at operational `lambda=0.40`, the locked Qiskit basis is also used to compile uniform preparation and Grover diffusion alongside the executable threshold oracle. Exhaustive `k=0..64` selection retains `k*=0` in 9/9 cases under both total compiled instruction count and compiled depth. Median fixed-per-trial break-even coordinates are `0.1475` and `0.1477` times one compiler-native iteration cost, respectively. These are synthesis coordinates with a different denominator from analytical `C_fixed/G_O`; they are not hardware measurements or numerically interchangeable with the analytical metric.

The operational threshold itself no longer depends on `C*`. Marked-fraction sensitivity is quantified for estimate factors `{0.50,0.75,0.90,1.00,1.10,1.25,1.50}` using exact Tier-I `rho_tau` only as retrospective regret ground truth. A separate BBHT layer removes exact `rho_tau` from the executed growth schedule; exact `rho_tau` is used only to score expected resource-to-success retrospectively. At zero attenuation and `chi=0.25`, median BBHT/uniform resource ratios are 0.769 primary and 0.643 connected validation. A separate Toffoli-weight sweep shows that the zero-fixed-overhead `k*=0` result is unchanged for `alpha_T=1,4,6,10`, while the median break-even coordinate shifts materially, so the scalarization dependence is explicit. The architecture-informed reversible oracle layer now couples logical oracle burden to iteration depth, and its 255 operational conditions all select `k*=0` under the declared gate-equivalent objective when fixed per-trial overhead is zero. A separate fixed-overhead stress test shows this is conditional: at zero attenuation the median break-even fixed-overhead ratios are 0.163 oracle-cost units in the primary tier and 0.168 in coverage. The strengthened classical layer shows that simulated annealing and tabu search are highly effective across a six-point within-classical objective-evaluation budget curve: even at 64 evaluations per run, both methods solve all 18 primary instances at least once across 64 runs and have a median-of-instance-median approximation ratio of 1.000. None of these statements is a physical runtime comparison. The paired QAOA optimizer layer now compares L-BFGS-B and COBYLA under the same 128-objective-evaluation cap and identical initializations. The instance-clustered inferential layer is now complete. On the fixed 18-instance primary suite the depth Friedman test gives p=0.00004; all three pairwise depth contrasts survive Holm correction (p2-p1=0.0080, p3-p1=0.0002, p3-p2=0.0080). Under the finite 128-evaluation optimizer budget, none of the COBYLA-minus-L-BFGS-B contrasts survives Holm correction (all p_Holm=0.0911 after adjustment in this run). These tests condition on the fixed benchmark and are not population-level graph inference or physical-resource evidence. The expanded validation design also adds a separate 63-instance exact seed/topology coverage tier. It is descriptive stress testing only: the 18-instance primary QAOA inferential sample is not enlarged by the additional coverage tier, and no population-level graph-family claim is made.

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
- The fixed-overhead analysis adds a coordinate `chi=C_fixed/G_O`. At zero attenuation, median break-even `chi` is 0.163 (IQR 0.098--0.225) in the primary tier and 0.168 (0.103--0.239) in coverage. At `chi=0.25`, nonzero amplification is selected in 78.4% and 77.2% of primary/coverage conditions; at `chi=0.50`, all zero-attenuation conditions select `k*>0`.
- The fixed-overhead coordinate is synthetic logical bookkeeping, not measured control/readout/verification/handoff cost. The zero-round result is therefore retained as a boundary result, not a general statement that amplitude amplification is ineffective.

## Goemans--Williamson SDP reference
- `gw_sdp_primary.csv`: 18 certified primary rows.
- `gw_sdp_connected_validation.csv`: 45 certified connected-validation rows.
- The rank-n Gram factor can represent every feasible n-by-n SDP matrix; 12 deterministic block-coordinate restarts are paired with a dual-feasible certificate.
- Maximum observed primal--dual gaps: about `2.3e-7` primary and `4.4e-7` connected validation, below the declared `1e-6` acceptance tolerance.
- Median `SDP/C*`: 1.015 primary and 1.017 connected validation. `C*` is retrospective only.
- 4,096 seeded random-hyperplane rounds per graph have median mean-cut ratios 0.967 and 0.961; at least one rounded cut reaches `C*` on 18/18 and 44/45 instances.
- These are exact-tier quality diagnostics, not physical runtime or large-instance competitiveness claims.

## Strengthened classical reference layer
- `classical_budgeted_runs.csv`: 2 methods x 18 instances x 64 runs = 2,304 raw runs.
- `classical_budgeted_summary.csv`: 36 instance-method summaries.
- Per-run cap: 4,096 complete Max-Cut objective evaluations for both simulated annealing and tabu search.
- Neither search algorithm queries `C*`; exact enumeration is used only for retrospective ratios and hit labels.
- Both methods have median run-best approximation ratio 1.000 and median optimum-hit fraction 1.000 at each tested `n`.
- Every exact instance is solved optimally by at least one run of each method.
- These budgets are comparable only within the classical layer and are not mapped to QAOA or amplitude-amplification resources.

## Dense operational-threshold audit
- Full grid: `lambda=0,0.05,...,1.00`; threshold construction remains independent of `C*` at every point.
- Primary feasibility at representative lambda values 0/.25/.40/.55/.75/1.00: `18/18, 18/18, 18/18, 15/18, 5/18, 2/18`.
- Connected-validation feasibility at the same values: `45/45, 45/45, 45/45, 36/45, 12/45, 0/45`.
- Every feasible condition in the dense sweep selects `k*=0` at zero fixed overhead and zero attenuation under the declared logical resource objective.
- This is a sensitivity audit, not a claim that any lambda is universally optimal.

## Classical objective-evaluation budget curve
- Budgets: `64,128,256,512,1024,4096` complete objective evaluations per run; 64 runs per instance and method.
- At budget 64, median-of-instance-median approximation ratio is `1.000` for both simulated annealing and tabu search; median instance optimum-hit fractions are `0.555` and `0.789`.
- All 18 primary instances are solved optimally at least once by both methods at every tested budget.
- Tabu reaches median instance optimum-hit fraction `1.000` at budget 128; simulated annealing reaches `1.000` at budget 1024.
- Objective evaluations may revisit states. These budgets are comparable only within the classical layer and are not mapped to QAOA or amplitude-amplification resources.

## Paired QAOA optimizer-budget layer
- `qaoa_optimizer_budget_runs.csv`: 18 instances x 3 depths x 5 seeds x 2 optimizers = 540 runs.
- `qaoa_optimizer_budget_paired.csv`: 270 paired L-BFGS-B/COBYLA deltas at identical instance, depth, and initialization seed.
- Per-run cap: 128 exact statevector expectation-objective evaluations; early convergence is allowed.
- Median instance-level approximation ratios at p=1/2/3: L-BFGS-B = 0.673/0.702/0.696; COBYLA = 0.691/0.712/0.718.
- COBYLA has the larger paired approximation ratio in 50/90, 47/90, and 52/90 comparisons at p=1,2,3. These are descriptive counts, not inferential or physical-runtime claims.
- Evaluation-cap exhaustion is substantial for deeper settings, so this is a finite-budget robustness study rather than a fully converged optimizer ranking.


## Instance-clustered inferential layer
- Repeated optimizer starts are not treated as independent graph replicates. Five starts are first collapsed within each instance.
- Primary depth omnibus: Friedman statistic 20.333, p=0.00004 across the 18 matched instance medians.
- Holm-adjusted depth contrasts: p2-p1 median delta +0.0234, p_Holm=0.0080; p3-p1 +0.0379, p_Holm=0.0002; p3-p2 +0.0307, p_Holm=0.0080.
- Finite-budget optimizer contrasts use instance-median COBYLA-minus-L-BFGS-B deltas. Holm-adjusted p values are 0.0911, 0.0911, and 0.0911 at p=1,2,3; none passes the 0.05 multiplicity-corrected threshold under the fixed 128-evaluation budget.
- Confidence intervals are 20,000-resample percentile bootstraps over the 18 instances. Rank-biserial correlations are reported as paired effect sizes.
- These tests describe consistency within the fixed deterministic suite and do not justify population generalization, hardware performance claims, or physical resource equivalence.

## Expanded exact seed/topology coverage
- Random seed expansion: 45 exact fixed-density random weighted instances across `n={8,10,12}`, densities `{0.25,0.50,0.75}`, and five seeds `{17,42,73,101,211}`. The original 18 primary instances are an exact subset. Each `(n,density,seed)` tuple uses its own deterministic RNG stream and exactly the declared edge count; the family label is `random_fixed_density`, not Erdős–Rényi `G(n,p)`.
- Structured topology expansion: 18 exact weighted instances from `cycle`, `cubic_circulant`, and `two_community` families at `n={8,10,12}` with weight seeds `{17,42}`.
- Combined expanded coverage: 63 exact instances, 1,326 edge-ledger rows, 189 operational-threshold validation rows, 63 coverage hill-climb diagnostics, and 360 feasible architecture-coupled rows at `eps_D={0,0.001}`.
- Operational feasibility across the 63 instances is 63/63 at `lambda=0.25`, 62/63 at `lambda=0.40`, and 55/63 at `lambda=0.55`.
- All 360 architecture-coupled coverage rows select `k*=0` at zero fixed per-trial overhead; the fixed-overhead boundary sweep shows that this conclusion changes as synthetic fixed overhead rises. It remains a logical-model result, not a hardware or large-scale claim.
- The 18-instance primary QAOA inference remains separate from the added coverage rows and is not reinterpreted as population inference after the coverage expansion.



## Environment lock and preflight
- Python is pinned to `3.13.5` in `.python-version`.
- Direct dependencies are exactly pinned in `requirements.txt`; the validated transitive closure is pinned in `requirements.lock`.
- `src/preflight.py` is the canonical fail-closed package validator. Full mode verifies runtime/package versions, manifest SHA-256 values, manifest-declared CSV row counts, duplicate canonical files, LaTeX environment balance, and claim fences.
- `--source-only` is permitted during editing, but it deliberately skips result-artifact hash/count validation and is not the final submission check.
- A preflight PASS certifies internal package synchronization only; the compiler evidence comes from the separately locked Qiskit workflow/artifact, and neither constitutes hardware or performance evidence.
- The current regression suite contains 93 tests, including graph-stream independence, structural-validation, certified-SDP, BBHT, scalarization, budget-curve, dense-threshold, QAOA initialization-stream, and 20-start stability checks.


## Repository citation and preservation
- Public repository: `https://github.com/ErcanErkalkan/FGCS-Quantum-Resource-Benchmark`.
- `CITATION.cff` provides GitHub/Zenodo citation metadata.
- Frozen public baseline: `v1.0.0` at commit `04852bf6c87258c92f00c9a8fd67825aa7f9e7d6`.
- The reviewer-driven scientific revision is developed as `v1.1.0_WORKING`; its final `v1.1.0` tag and Zenodo DOI will be created only after final validation.
- Software is released under the **BSD 3-Clause License (`BSD-3-Clause`)**; see `LICENSE` and `LICENSE_SCOPE.md`.
- Funding status is author-confirmed: **no specific grant funding** from public, commercial, or not-for-profit funding agencies.
- Manuscript/article files are publication materials and are not relicensed by the repository software license.
- `ZENODO_RELEASE_GUIDE.md` records the exact publication sequence and DOI back-link procedure.

## Submission formatting
- Final FGCS manuscript uses `\documentclass[5p,times]{elsarticle}`.
- The current submission constraint is **18 pages** in `elsarticle` `5p,times` double-column format.
- Current compiled manuscript: **18 pages**, with no overfull boxes or unresolved citations/references.

## Reviewer-audit structural validation (working v1.1.0 layer)
- The original 18 primary graphs remain unchanged for traceability; exact structural diagnostics show 5 disconnected and 2 bipartite instances.
- The 63-instance expanded coverage tier contains 10 disconnected and 13 bipartite graphs; these rows are retained and labeled rather than silently filtered.
- A separate 45-instance `connected_nonbipartite_fixed_density` validation tier uses `n={10,12,14}`, densities `{0.25,0.50,0.75}`, and five deterministic seeds.
- All 45 validation graphs are connected, non-bipartite, and exact-enumerated through `2^14=16,384` states.
- Operational feasibility is 45/45, 45/45, and 36/45 at `lambda={0.25,0.40,0.55}`.
- All 252 feasible architecture-coupled rows at `eps_D={0,0.001}` retain `k*=0` when fixed per-trial overhead is zero; at zero attenuation, the overall median break-even fixed-overhead ratio is 0.121 oracle-cost units.
- This layer removes identifiable connectivity/bipartiteness confounding but is not described as a hardness proof or population-level graph evidence.


## Twenty-start QAOA initialization-stability audit
The five-start primary L-BFGS-B analysis is nested inside a 20-start audit on the same 18 instances and three depths (1,080 runs total). Median instance-level approximation ratios are 0.661/0.691/0.707 for p=1/2/3. All three instance-clustered depth contrasts remain positive after Holm correction, with 95% bootstrap intervals above zero. This is a fixed-suite initialization-robustness check, not a population or hardware claim.

### Threshold-aligned QAOA objective audit

A paired 270-run sensitivity audit uses the same 18 primary instances, depths `p={1,2,3}`, five instance-conditioned starts, L-BFGS-B, and a strict 128-objective-evaluation cap for both objectives. Replacing expected-cut training by direct optimization of the operational `lambda=0.40` hit probability increases the median instance-level event probability from `0.0683/0.1187/0.1007` to `0.0874/0.1618/0.1868` at `p=1/2/3`. Median paired gains are `+0.0159/+0.0173/+0.0174`; all three survive Holm correction (`0.0039/0.0020/0.0385`), while median approximation-ratio changes are slightly negative (`-0.0012/-0.0045/-0.0140`). This is reported as an objective trade-off, not universal superiority of threshold training.
