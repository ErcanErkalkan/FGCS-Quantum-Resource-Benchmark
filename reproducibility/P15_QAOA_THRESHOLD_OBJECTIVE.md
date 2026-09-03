# P15 - QAOA threshold-objective sensitivity

## Question
Does optimizing standard expected Max-Cut value bias a comparison whose common operational outcome is the event `C(x) >= tau_lambda`?

## Locked paired design
- 18 primary exact instances
- p = 1,2,3
- 5 instance-conditioned starts per instance/depth
- same initial parameter vector for both objectives
- L-BFGS-B
- strict 128 exact-statevector objective evaluations per run
- operational lambda = 0.40
- expectation-trained reference is the existing L-BFGS-B subset of `qaoa_optimizer_budget_runs.csv`
- threshold-trained side contributes 270 new runs

## Result
| p | expectation-trained median P_tau | threshold-trained median P_tau | median paired delta | 95% bootstrap CI | Holm p | positive-instance fraction | median delta approximation ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.0683 | 0.0874 | +0.0159 | [0.0052, 0.0368] | 0.0039 | 0.944 | -0.0012 |
| 2 | 0.1187 | 0.1618 | +0.0173 | [0.0082, 0.0632] | 0.0020 | 0.833 | -0.0045 |
| 3 | 0.1007 | 0.1868 | +0.0174 | [0.0018, 0.0442] | 0.0385 | 0.722 | -0.0140 |

All three event-probability gains survive Holm correction on the fixed suite, but expected-cut approximation ratio decreases slightly. The evidence therefore supports an objective-alignment trade-off, not universal superiority of threshold training.

## Canonical files
- `results/qaoa_threshold_training_budget_runs.csv`
- `results/qaoa_threshold_training_budget_paired.csv`
- `results/qaoa_threshold_training_budget_instance_summary.csv`
- `results/qaoa_threshold_training_budget_inference.csv`
