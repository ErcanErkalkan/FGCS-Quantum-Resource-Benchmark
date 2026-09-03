# Reviewer revision P4 — Goemans–Williamson SDP baseline

Date: 2026-09-01
Status: WORKING REVISION COMPLETE

## Reviewer risk addressed
A Max-Cut benchmark without the canonical Goemans–Williamson semidefinite-programming reference leaves the classical comparison vulnerable, especially when the study uses exact micro-instances and later seeks larger validation tiers.

## Implementation
- No new optimization dependency was introduced: CVXPY/SCS/CVXOPT were not present in the locked environment.
- The weighted Max-Cut SDP is represented by an n-dimensional Gram factor, which is sufficient to represent every feasible n x n SDP Gram matrix.
- Twelve deterministic restarts use unit-vector block-coordinate ascent.
- Every restart also constructs a dual candidate for `min sum(y)` subject to `Diag(y)-L/4 >= 0`.
- A uniform diagonal shift makes the dual slack numerically PSD.
- A result is accepted only when the best primal value and best dual-feasible upper bound close within `1e-6`.
- The accepted primal factor is rounded with 4,096 deterministic-seed random hyperplanes.
- Exact `C*` is never used by the SDP solver or rounding; it is used only for retrospective exact-tier scoring.

## Generated evidence
- `results/gw_sdp_primary.csv`: 18 rows.
- `results/gw_sdp_connected_validation.csv`: 45 rows.
- `results/gw_sdp_summary.csv`: tier/n summaries.
- `results/table_gw_sdp.tex`: manuscript table.

## Key results
- Numerical SDP certificate: 18/18 primary and 45/45 connected-validation rows pass.
- Maximum primal–dual gap: approximately 2.3e-7 primary and 4.4e-7 connected validation.
- Median SDP upper-bound ratio `SDP/C*`: 1.015 primary; 1.017 connected validation.
- Median mean hyperplane-rounded cut ratio: 0.967 primary; 0.961 connected validation.
- At least one of 4,096 rounded samples reaches exact `C*` on 18/18 primary and 44/45 connected-validation instances.

## Claim boundary
The SDP certificate is numerical floating-point evidence with an explicit tolerance, not symbolic exact arithmetic. The finite hyperplane sample is not exhaustive and its observed optimum-hit rate is not the theoretical Goemans–Williamson approximation guarantee. No host runtime, physical-resource, hardware, or large-instance competitiveness claim is made from this layer.
