# Reviewer revision P17 — compiler-topology robustness

Date: 2026-09-09  
Status: POST-RELEASE JOURNAL-PRESENTATION ROBUSTNESS AUDIT COMPLETE

## Reviewer risk addressed
The compiler-locked layer originally used a bidirectional line coupling map for routed QAOA circuits and three sparse routed threshold-oracle representatives. A systems reviewer could therefore ask whether the concrete transpilation counts are artifacts of one synthetic connectivity graph.

## Locked comparison protocol
The audit preserves the original compiler settings:

- Qiskit 2.4.2;
- Python 3.12.14;
- basis `rz/sx/x/cx`;
- optimization level 1;
- `seed_transpiler = 20260901`;
- identical primary weighted-Max-Cut instances and circuit constructors.

Only the synthetic coupling graph changes. Three bidirectional topology classes are compared:

1. line/path (the locked baseline);
2. ring/cycle;
3. two-row ladder-like connectivity.

The matched QAOA audit covers all 18 primary graphs at p=1,2,3 under all three maps (162 routed QAOA rows). The sparse-oracle audit uses the n=8,10,12, density-0.25, seed-17 representatives under all three maps (9 routed oracle rows), for 171 rows overall.

## Fail-closed baseline guard
Before alternate-topology results are accepted, the line rerun is compared against the pre-existing `results/compiler_validation_qiskit.csv` locked baseline for logical qubits/depth/size and compiled qubits/depth/size/CX/RZ/SX/X counts.

Result:

- expected locked line rows: 57;
- line rows rerun: 57;
- missing rows: 0;
- extra rows: 0;
- metric mismatches: 0;
- baseline guard: PASS.

Thus the topology audit extends rather than silently redefining the existing Qiskit compiler evidence.

## QAOA matched results
Across the 54 matched QAOA circuits, relative to line routing:

- ring median compiled-depth ratio: 0.9363 (about 6.4% lower);
- ring median CX ratio: 0.8971 (about 10.3% lower);
- ring is no worse than line in depth on 85.2% of circuits and in CX on 90.7%;
- ladder median compiled-depth ratio: 0.7847 (about 21.5% lower);
- ladder median CX ratio: 0.6218 (about 37.8% lower);
- ladder is no worse than line in depth on 98.1% of circuits and in CX on 100%.

The per-depth summaries show the same qualitative pattern for p=1,2,3; no single QAOA depth creates the aggregate result.

## Sparse threshold-oracle matched results
For the three sparse routed threshold-oracle representatives:

- ring median compiled-depth ratio: 1.0015 and median CX ratio: 1.0039, i.e. essentially unchanged from line;
- ladder median compiled-depth ratio: 0.9271 and median CX ratio: 0.9000, i.e. lower than line on all three representatives for both metrics.

## Interpretation
The experiment does not establish a hardware topology advantage and does not privilege any synthetic coupling graph. It shows two narrower points relevant to the manuscript claim boundary:

1. concrete routed depth/CX values materially depend on connectivity, reinforcing the manuscript warning that compiler counts are not physical-resource constants; and
2. the original line-routing evidence is not a uniquely favorable connectivity choice whose removal destroys the compiler-level interpretation. Ring routing is typically similar to or cheaper than line for QAOA, while ladder routing is generally cheaper for both QAOA and the sparse oracle representatives.

No backend calibration, duration, fidelity, queue time, control/readout latency, energy, or hardware-speedup conclusion is drawn.

## Reproducibility evidence
- script: `src/compiler_topology_robustness.py`;
- workflow: `.github/workflows/compiler-topology-robustness.yml`;
- persisted compact summary: `results/compiler_topology_robustness_summary.json`;
- successful workflow run: 34365030258;
- workflow artifact: 10109484982;
- artifact SHA-256: `540bc30840c1917e18b69b1d1ab68a54ea69b332eeb00b4ff0254ad1e3c1d0ac`.

The archived Git/Zenodo v1.1.0 release remains immutable; this is a post-release journal-presentation robustness layer on current `main`.
