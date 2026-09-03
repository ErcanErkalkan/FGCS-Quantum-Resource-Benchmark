# P5 — BBHT unknown-solution-count validation

## Purpose
The operational threshold is constructed without the exact optimum, but a fixed-depth Grover selector can still require the marked fraction `rho_tau`. P5 adds an executed control policy whose schedule does not consume `rho_tau`: the Boyer–Brassard–Høyer–Tapp (BBHT) unknown-solution-count search schedule.

## Schedule
- Initial growth variable: `m = 1`.
- Growth factor: `lambda = 6/5` (within the BBHT condition `1 < lambda < 4/3`).
- At each trial, choose an integer `j` uniformly from the non-negative integers strictly below `m`.
- Apply `j` Grover iterations, measure, and verify the threshold event.
- After failure, update `m <- min(lambda*m, sqrt(N))`.
- Once saturated, repeat the same randomized-depth stage until success.

The schedule depends on `N=2^n` but never receives the number or fraction of marked states.

## Expected-cost evaluation
Exact Tier-I `rho_tau` is used only retrospectively to evaluate success probabilities for each randomized `j`. Pre-saturation stages are summed using their exact survival probabilities. The saturated stage is evaluated with an exact geometric tail, avoiding Monte Carlo noise in the reported expected trials, Grover iterations, and logical gate-equivalent resource-to-success.

Each trial is charged the same architecture-informed preparation, iteration, attenuation, and optional fixed-overhead coordinates already used by the main resource model. No quantity is interpreted as measured backend time, energy, native-gate count, or control latency.

## Evidence grid
Primary exact tier:
- 51 feasible operational graph/threshold conditions;
- `eps_D={0,1e-4}`;
- `chi={0,0.25}`;
- 204 rows.

Connected non-bipartite validation tier:
- 126 feasible operational graph/threshold conditions;
- same attenuation and fixed-overhead coordinates;
- 504 rows.

## Results
At `eps_D=0, chi=0`, BBHT is not resource-preferred to repeated uniform sampling on any feasible condition. Median BBHT/uniform expected-resource ratios are 54.651 in the primary tier and 57.797 in connected validation.

At `eps_D=0, chi=0.25`, the medians fall to 0.769 and 0.643. BBHT is preferred to uniform repetition in 76.5% of primary and 90.5% of connected-validation conditions. Relative to the oracle-informed exact-rho selector, however, BBHT retains an information-uncertainty premium: median ratios are 1.170 and 1.247.

At `eps_D=1e-4, chi=0.25`, BBHT is preferred to uniform repetition in 47.1% of primary and 34.9% of connected-validation conditions.

## Claim boundary
P5 supports the statement that exact marked-fraction knowledge is not required by the implemented BBHT schedule. It also shows that unknown marked fraction narrows the fixed-overhead regime in which amplitude amplification is resource-preferred under the declared logical model. It does not provide quantum counting, fixed-point search, compiled adaptive-control measurements, hardware runtime, or a universal BBHT superiority claim.
