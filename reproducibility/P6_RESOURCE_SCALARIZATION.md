# P6 — Logical resource scalarization sensitivity

## Purpose
The architecture-informed layer preserves raw logical Toffoli, CNOT, single-qubit, ancilla, and depth counts, but the selector uses a scalar bookkeeping projection. The canonical projection assigns six units to one logical Toffoli. P6 tests whether the scientific conclusion is an artifact of that single weight.

## Protocol
Recompute the mixed score as

`G_alpha = N1 + N_CNOT + alpha_T * N_T`

for `alpha_T={1,4,6,10}`. No raw count or logical depth is changed. The external fixed-overhead amount is anchored to the canonical `alpha_T=6` oracle cost so that varying the scalarization does not simultaneously redefine the fixed-work assumption.

Evidence grid:
- primary: 51 feasible operational thresholds;
- connected validation: 126 feasible operational thresholds;
- `alpha_T={1,4,6,10}`;
- `eps_D={0,1e-4}`;
- canonical fixed-overhead ratios `chi_6={0,0.10,0.25,0.50}`.

This produces 1,632 primary and 4,032 connected-validation rows.

## Results
At `eps_D=0, chi_6=0`, all conditions in both tiers select `k*=0` for every tested Toffoli weight.

Median break-even fixed-overhead ratios expressed in canonical-alpha6 oracle units:
- primary: 0.064, 0.124, 0.163, 0.243 for alpha 1, 4, 6, 10;
- connected validation: 0.047, 0.091, 0.121, 0.180.

At `eps_D=0, chi_6=0.25`, the nonzero-amplification fractions are:
- primary: 1.000, 0.961, 0.784, 0.549;
- connected validation: 1.000, 0.976, 0.905, 0.667.

## Claim boundary
P6 shows that the zero-fixed-overhead no-amplification conclusion is robust to a broad tested range of Toffoli scalarization weights, while the fixed-overhead phase boundary is quantitatively scalarization-dependent. No alpha value is interpreted as a native backend, runtime, energy, or fault-tolerant cost equivalence.
