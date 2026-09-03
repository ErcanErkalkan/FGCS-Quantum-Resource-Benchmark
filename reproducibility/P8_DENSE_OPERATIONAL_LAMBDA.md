# P8 — Dense operational-lambda audit

## Reviewer risk addressed
The manuscript originally emphasized lambda={0.25,0.40,0.55}. A reviewer could ask whether those operating points were cherry-picked or whether feasibility/resource behavior changes immediately outside them.

## Design
The exact same C*-independent threshold construction is evaluated at lambda=0,0.05,...,1.00. The primary 18-instance suite gives 378 rows and the 45-instance connected non-bipartite validation tier gives 945 rows. Exact C*, tau/C*, rho_tau, and resource decisions are recorded only retrospectively after the threshold has been fixed.

## Representative results
Primary feasibility counts at lambda 0, .25, .40, .55, .75, 1.00 are 18, 18, 18, 15, 5, and 2 out of 18. Connected-validation counts are 45, 45, 45, 36, 12, and 0 out of 45.

Across every feasible dense-sweep condition in both tiers, the architecture-informed selector returns k*=0 when fixed per-trial overhead and attenuation are both zero. The break-even fixed-overhead ratio decreases as the target event becomes rarer, consistent with the existing fixed-overhead phase-boundary analysis.

## Interpretation boundary
This audit reduces dependence on three displayed lambda values; it does not identify a universally optimal application threshold. The rows are repeated settings on fixed exact graph suites, not independent graph samples, and all resource quantities remain logical/synthetic rather than compiled or hardware measured.
