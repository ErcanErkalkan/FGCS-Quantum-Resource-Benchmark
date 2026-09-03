# Structural graph audit and connected validation

Status: WORKING v1.1.0 scientific revision layer.

## Motivation
A reviewer-facing audit found that deterministic fixed-density sampling did not guarantee connectivity. Because disconnected components and bipartite structure can inflate optimum-state degeneracy or make Max-Cut structurally easier, the original graph suites are now explicitly audited rather than assumed to be structurally homogeneous.

## Primary and expanded coverage audit
- Primary exact suite: 18 instances; 5 disconnected; 2 bipartite; 5 with at least one isolated vertex.
- Expanded exact coverage: 63 instances; 10 disconnected; 13 bipartite.
- These instances are retained unchanged to avoid post hoc replacement after inspecting their properties.

## Connected non-bipartite validation tier
A separate deterministic validation tier conditions fixed-density graph sampling on connectedness and non-bipartiteness:
- n = {10,12,14}
- target densities = {0.25,0.50,0.75}
- seeds = {17,42,73,101,211}
- 45 exact instances total
- integer weights sampled from {1,...,9}
- exact ground truth through 2^14 states

The conditioning is a structural-control device only; it is not claimed to prove computational hardness.

## Results
- Operational feasibility: 45/45, 45/45, 36/45 for lambda = 0.25, 0.40, 0.55.
- Median retrospective tau/C*: 0.794, 0.886, 0.946.
- Median exact rho_tau: 0.1400, 0.0337, 0.0067.
- 126 feasible graph/threshold combinations x 2 coupled attenuation values = 252 rows.
- All 252 select k*=0 under zero fixed per-trial overhead.
- At zero attenuation, overall median break-even chi_BE = 0.121 (IQR 0.065--0.190).
- At chi=0.25, 90.5% select nonzero amplification; at chi=0.50, 100% do.

## Validation state
- Regression suite after this change: 72/72 PASS.
- Manuscript compiles successfully in elsarticle 5p,times; working revision is 16 pages.
- Full benchmark regeneration is intentionally deferred until the remaining reviewer-driven scientific layers are implemented; the v1.0.0 archival release remains the frozen baseline.
