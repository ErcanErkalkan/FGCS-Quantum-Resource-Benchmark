# P10 — QAOA 20-start initialization-stability audit

## Purpose
The primary QAOA analysis uses five deterministic instance-conditioned L-BFGS-B initializations per instance and depth. This phase tests whether the fixed-suite depth conclusion depends materially on that small initialization sample.

## Design
- Primary exact suite: 18 instances.
- QAOA depths: p = 1, 2, 3.
- Initialization seeds: 0..19 (20 starts per instance-depth).
- Total runs: 18 x 3 x 20 = 1,080.
- Seeds 0..4 are the exact canonical five-start subset; no alternate initialization rule is introduced.
- Optimization remains ideal-statevector L-BFGS-B with maxiter=60.
- The optimizer-family ablation is not expanded here; its paired five-start/128-evaluation design remains a separate finite-budget experiment.

## Results
Median of the 18 instance-level 20-start median approximation ratios:
- p=1: 0.6605866
- p=2: 0.6914892
- p=3: 0.7070602

Instance-clustered depth inference after collapsing 20 starts within each instance:
- Friedman statistic = 26.7778, p = 1.53e-6.
- p2-p1: median delta +0.01262, bootstrap 95% CI [0.00463, 0.03045], Holm p=0.000328.
- p3-p1: median delta +0.03336, bootstrap 95% CI [0.02170, 0.06526], Holm p=2.29e-5.
- p3-p2: median delta +0.01686, bootstrap 95% CI [0.00617, 0.03374], Holm p=0.000107.

## Interpretation boundary
The 20-start audit strengthens initialization robustness within the fixed 18-instance benchmark. It does not convert the deterministic benchmark into a probability sample, establish population-level monotonicity in QAOA depth, or provide hardware/runtime evidence.
