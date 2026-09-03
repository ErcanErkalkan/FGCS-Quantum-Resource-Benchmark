# FGCS Quantum Resource Benchmark v1.1.0 — reviewer-driven revision

Status: release candidate notes. Publish only after the exact v1.1.0 tree passes the final full regression/preflight/CI freeze.

## Scientific changes since v1.0.0
- Added explicit structural diagnostics for the primary and coverage graph suites.
- Added a 45-instance connected, non-bipartite exact validation tier through n=14.
- Added a numerically certified Goemans-Williamson SDP baseline with deterministic hyperplane rounding.
- Added a BBHT unknown-solution-count layer so the executed growth schedule does not receive exact marked fraction.
- Added Toffoli-weight resource scalarization and fixed-per-trial overhead break-even analyses.
- Added a six-point classical objective-evaluation budget curve and a 21-point operational-lambda sweep.
- Corrected QAOA initialization to deterministic instance-conditioned streams while preserving matched optimizer starts.
- Added a nested 20-start, 1,080-run QAOA initialization-stability audit.
- Added a paired QAOA threshold-objective sensitivity audit under a shared 128-evaluation L-BFGS-B cap.

## Compiler evidence
- Added compiler-locked Qiskit 2.4.2 validation with basis `rz/sx/x/cx`, optimization level 1, and `seed_transpiler=20260901`.
- P14 includes 54 line-routed QAOA circuits, 9 basis-decomposed threshold oracles, 3 sparse line-routed oracle controls, and an exhaustive 8/8 semantic threshold-oracle check.
- A 9-row analytical-vs-compiler ledger reports a median executable-oracle/analytical-template depth ratio of about 140.5x and a median qubit ratio of about 1.61x. Gate alphabets are not equated.
- P16 recompiles preparation, the executable oracle, and Grover diffusion on nine operational representatives. At zero fixed overhead, all 9/9 select `k*=0` under both compiled instruction-count and compiled-depth coordinates. Median compiler-native break-even coordinates are 0.147520 and 0.147723 times one compiler-native iteration cost.

## QAOA sensitivity
At operational `lambda=0.40`, direct threshold-hit training increases median target-hit probability relative to expectation-trained QAOA at p=1,2,3 under the same 128-evaluation cap, while median approximation ratio decreases slightly. This is reported as an objective-alignment trade-off, not universal optimizer superiority.

## Evidence boundaries
This release does **not** claim quantum advantage, hardware speedup, measured device performance, physical runtime superiority, device calibration, fidelity, energy, or fault-tolerant physical-resource estimates. Compiler counts are reproducible compiler/synthetic-topology evidence. Analytical `C_fixed/G_O` and compiler-native fixed-overhead/iteration coordinates use different denominators and are not metric-equivalent.

## Reproducibility state before release
- Current reviewer manuscript: 18 pages with no unresolved citations/references, LaTeX warnings, or overfull boxes; all pages visually checked after P16.
- P14/P15/P16 dedicated evidence checks: 11/11, 3/3, and 9/9 PASS.
- Historical full-project checkpoint before P14-P16: 93/93 regression tests; 244 PASS / 0 WARN / 0 FAIL full preflight.
- **Required before publishing v1.1.0:** rerun the complete regression suite and full preflight/CI on the exact frozen release-candidate commit.

## Preservation rule
The public `v1.0.0` tag remains immutable. Do not create or publish the `v1.1.0` tag/Zenodo DOI until the final full-project verification passes.
