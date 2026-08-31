# FGCS Quantum Resource Benchmark v1.0.0

Initial archival reproducibility release for the manuscript:

**Resource-Aware Amplitude Amplification for Hybrid Quantum–Classical Workflows: A Reproducible Max-Cut Benchmark with QAOA and Classical References**

## Included evidence
- exact weighted Max-Cut ground truth for 18 primary instances;
- independent deterministic fixed-density random graph streams;
- 63-instance seed/topology coverage tier;
- operational thresholds constructed without using the unknown exact optimum;
- architecture-informed logical oracle/resource model;
- fixed-overhead phase-boundary sensitivity layer;
- 270 primary ideal-statevector QAOA runs;
- 540 paired L-BFGS-B/COBYLA finite-budget runs;
- fixed-instance clustered inference with multiplicity correction;
- simulated annealing, tabu search, and hill-climbing reference layers;
- machine-readable CSV results, generated LaTeX tables/PDF figures, tests, and preflight hashes.

## Evidence boundary
This release does not claim quantum advantage, hardware speedup, measured device calibration, compiled backend resource counts, or physical energy/runtime superiority.

## Reproduction
See `README.md`. The canonical final package check is:

```bash
pytest -q
python src/preflight.py --json-out results/preflight_full_report.json
```

## Release metadata
- Software license: **BSD-3-Clause**.
- Funding: **no specific grant funding** from public, commercial, or not-for-profit funding agencies.
- Manuscript/article files remain subject to the final publication license rather than the repository software license.
