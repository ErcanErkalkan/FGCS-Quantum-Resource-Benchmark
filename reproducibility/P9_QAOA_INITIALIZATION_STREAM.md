# P9 — QAOA instance-conditioned initialization audit

Status: COMPLETE

The reviewer audit identified that the previous QAOA implementation seeded initial parameters only with the external optimizer seed. Consequently, equal `(p, seed)` values reused the same `x0` across distinct graph instances. P9 replaces that design with a versioned deterministic stream conditioned on graph identity, depth, and optimizer seed.

## Contract
- `QAOA_INIT_STREAM_VERSION = 1`.
- Distinct graph instances receive distinct initial parameter vectors even when `p` and external optimizer seed are equal.
- L-BFGS-B and COBYLA still receive exactly the same `x0` within every `(instance,p,seed)` paired optimizer comparison.
- The QAOA Hamiltonian, graph suite, optimizer settings, 128-evaluation cap, and instance-clustered inference procedure are unchanged.

## Regenerated evidence
- Main QAOA runs: 270; successful optimizer flags: 269/270.
- Every `(p, optimizer_seed)` group contains 18 distinct initial vectors across the 18 primary graph instances.
- All 270 paired optimizer keys preserve one identical `x0` across the two optimizer families.
- Median-of-instance-median approximation ratios at p=1/2/3: 0.673317, 0.689377, 0.715751.
- Friedman statistic: 20.333333, p=0.00003843.
- Holm-adjusted depth p values: p2-p1=0.00801086, p3-p1=0.00022888, p3-p2=0.00801086.
- Optimizer Holm-adjusted p values: p1=0.09109497, p2=0.09109497, p3=0.09109497; none is below 0.05.

## Interpretation change
The corrected initialization design materially changes the inferential summary: all three fixed-suite depth contrasts now survive Holm correction, whereas none of the finite-budget optimizer-family contrasts does. The manuscript, README, claims register, tables, figures, and manifest must therefore use the regenerated P9 outputs rather than the v1.0.0 QAOA statistics. This remains fixed-suite inference and does not imply population-level monotone QAOA behavior.
