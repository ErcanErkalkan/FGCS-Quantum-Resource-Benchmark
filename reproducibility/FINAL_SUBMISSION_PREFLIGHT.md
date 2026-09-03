# Final submission / preservation preflight

Date: 2026-09-02

Status: **v1.1.0 REVIEWER-DRIVEN REVISION — P16 SCIENTIFIC LAYERS COMPLETE; FINAL FULL CI/FREEZE PENDING**

The working manuscript, machine-readable results, source, compiler evidence, claim boundaries, and reviewer-driven validation layers are synchronized in the active `v1.1.0_WORKING` Drive workspace. The frozen public `v1.0.0` baseline remains unchanged.

## Current post-P16 validated state
- Manuscript: **18 pages**, `elsarticle` `5p,times`, double column.
- LaTeX: **0 unresolved citations/references; 0 warnings/overfull boxes** in the current P16 source.
- All **18 pages visually rendered and checked** after P16 integration.
- Bibliography: **27 cited references** in the current manuscript source.
- P14 compiler-specific evidence checks: **11/11 PASS**.
- P15 threshold-objective evidence checks: **3/3 PASS**.
- P16 compiler-native AA evidence checks: **9/9 PASS**.
- P16 GitHub Actions run `33596371482`: **SUCCESS**.
- Software license: **BSD-3-Clause** for repository software; manuscript/article text is not relicensed by the software license.
- Funding: **no specific grant funding** from public, commercial, or not-for-profit funding agencies.
- ORCID: **0000-0001-9259-7112**.

## Last complete project-wide checkpoint
The most recent *full-project* regression/preflight run predates P14-P16:
- Regression tests: **93/93 PASS**.
- Source-only preflight: **96 PASS / 0 WARN / 0 FAIL**.
- Full reproducibility preflight: **244 PASS / 0 WARN / 0 FAIL**.

These values remain historical evidence of the pre-P14-P16 working tree and are **not** represented as a final post-P16 full-suite result. A fresh full-project regression/preflight/CI run is mandatory after the reviewer-driven tree is frozen and before creating `v1.1.0` or a Zenodo DOI.

## Reviewer-driven scientific additions
- Structural graph diagnostics plus a 45-instance connected/non-bipartite exact control tier.
- Certified Goemans-Williamson SDP and seeded hyperplane-rounding reference.
- BBHT unknown-solution-count schedule evaluated without giving the executed schedule exact marked fraction.
- Logical Toffoli-weight scalarization sweep and fixed-overhead phase-boundary analysis.
- Six-point classical objective-evaluation budget curve and twenty-one-point operational-threshold sweep.
- Instance-conditioned QAOA initialization and nested 20-start / 1,080-run stability audit.
- P15 paired QAOA threshold-objective sensitivity: 270 threshold-trained runs under a matched 128-evaluation cap.
- P14 compiler-locked Qiskit 2.4.2 validation: 66 compiler rows, 54 routed QAOA circuits, 9 basis-decomposed threshold oracles, 3 sparse routed oracle controls, and an exhaustive 8/8 small-oracle semantic PASS.
- Matched analytical-vs-compiler oracle ledger: median depth ratio 140.5x and median qubit ratio 1.61x, without equating gate alphabets.
- P16 compiler-native AA cross-check: nine `lambda=0.40` representatives, with `k*=0` in 9/9 under both compiled instruction count and compiled depth at zero fixed overhead; median break-even coordinates 0.147520/0.147723 per compiler-native iteration cost.

## Remote/archive state
- Public GitHub repository exists and the frozen `v1.0.0` baseline is available at commit `04852bf6c87258c92f00c9a8fd67825aa7f9e7d6`.
- P14 compiler run: `33558640895`; artifact digest `sha256:7cac3634fa4ab81de905b4cbb04f7bb298b656038395e0e2138fe2dd35202c3b`.
- P16 compiler-native AA run: `33596371482`; artifact ID `9833538936`; digest `sha256:b97c18dc5fc2860719312eb14442d2b1e82f4f68d193b5e4a74e73093d965cc5`.
- The active `v1.1.0_WORKING` revision is **not yet a public archival release**.
- No Zenodo DOI is claimed for `v1.1.0` yet.

## Evidence boundary still enforced
No hardware speedup, quantum advantage, physical-runtime superiority, measured device calibration, physical-backend timing/fidelity/energy, or fault-tolerant physical-resource result is claimed. Compiler evidence is version-pinned and reproducible but remains compiler/synthetic-topology evidence. The analytical `C_fixed/G_O` coordinate and P16 compiler-native fixed-overhead/iteration coordinates have different denominators and are not treated as metric-equivalent.
