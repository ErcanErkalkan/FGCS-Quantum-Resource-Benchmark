9 September 2026

Editors
Future Generation Computer Systems

Re: Submission to the special collection “Advances in Quantum Computing: Methods, Algorithms, and Systems. Vol. IV”

Dear Editors,

Please consider the manuscript entitled “Resource-Aware Amplitude Amplification for Hybrid Quantum-Classical Workflows: A Reproducible Max-Cut Benchmark with QAOA and Classical References” for publication in Future Generation Computer Systems.

The manuscript studies a systems-oriented configuration question that is easily obscured by query-complexity comparisons: how operational target construction, marked-fraction uncertainty, reversible-oracle burden, fixed per-trial work, variational optimization, compilation, and classical references change decisions in a finite hybrid quantum-classical workflow. Operational Max-Cut thresholds are constructed from graph-observable quantities without using the unknown optimum C*. Exact enumeration is reserved for retrospective validation.

The benchmark comprises an 18-instance primary tier, a 63-instance seed/topology coverage tier, and a separate 45-instance connected, non-bipartite exact validation tier through n=14. Its main systems contribution is not a new Grover or QAOA theorem, but an auditable configuration framework that links operational target construction, unknown-solution-count control, reversible-oracle burden, fixed-overhead break-even analysis, common target-hit semantics, and separately labeled compiler evidence. Under the declared logical resource model, all architecture-coupled conditions select no amplification when fixed per-trial overhead is zero; a dedicated overhead sweep identifies the break-even region where nonzero amplification becomes resource-preferred. An implemented BBHT layer evaluates unknown-solution-count search without giving the executed schedule the exact marked fraction.

QAOA uses deterministic instance-conditioned initialization. A nested 20-start audit comprising 1,080 L-BFGS-B runs preserves all three positive depth contrasts after Holm correction, while none of the COBYLA-minus-L-BFGS-B contrasts is significant after correction under an equal 128-evaluation cap. A separate paired objective-sensitivity audit shows that threshold-hit training raises the operational target probability at p=1,2,3 under the same 128-evaluation cap, with a small approximation-ratio trade-off. The classical reference layer includes a numerically certified Goemans-Williamson SDP; seeded hyperplane rounding reaches an exact optimum on 62 of 63 primary/connected-validation instances, and simulated annealing and tabu search expose the ease of the tested microinstances across a six-point evaluation-budget curve.

The systems evidence also includes a compiler-locked Qiskit 2.4.2 layer with fixed basis, optimization level, and transpiler seed. It produces 66 executable compiler rows, an exhaustive 8/8 semantic threshold-oracle check, and a separate compiler-native amplitude-amplification cross-check on nine operational representatives. At zero fixed overhead, all nine retain k*=0 under both compiled instruction-count and compiled-depth coordinates; the associated fixed-overhead break-even boundary is reported only in compiler-native iteration-cost units and is not equated with the analytical resource metric.

The paper is deliberately evidence-conditioned. It does not claim quantum advantage, hardware speedup, measured device calibration, physical runtime superiority, or physical-backend performance. Compiler outputs are explicitly labeled synthetic-topology or locked-basis evidence and are not interpreted as device timing, fidelity, energy, or fault-tolerant physical-resource measurements. The package includes machine-readable results, source code, environment locks, tests, SHA-256 manifests, and an automated fail-closed preflight.

The manuscript includes a declaration of generative-AI and AI-assisted technology use. All AI-assisted drafting, code support, literature-navigation support, and consistency checking were reviewed by the author; the computational workflow, reported outputs, and cited sources were independently checked, and the author retains full responsibility for the work.

The author declares no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper, and this research received no specific grant funding.

Thank you for your consideration.

Sincerely,

Ercan Erkalkan
Marmara University
Vocational School of Technical Sciences
Department of Electronics and Automation
Artificial Intelligence Operator Program
Istanbul, Turkey
