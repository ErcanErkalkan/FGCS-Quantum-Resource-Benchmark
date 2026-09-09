# Current manuscript state

Last audited: 2026-09-09

## Immutable reproducibility release
- Archived software/reproducibility release: `v1.1.0`
- Archived tag commit: `923ffe7570dd2d8fb6235ae6eab63a5cf1c50b8d`
- Zenodo version DOI: `10.5281/zenodo.22272778`
- The archived tag and Zenodo record remain unchanged.

## Canonical manuscript build
Canonical manuscript filename:
`FGCS_manuscript_v1.1.0_FINAL_NEUTRAL_COLOR_FIGURES.pdf`

Canonical manuscript SHA-256:
`aa1d889d80e8923173437616834f151f7267f39122fa8e72f70866b4f6a24117`

Canonical LaTeX source-package SHA-256:
`ec97d8bb6fb43724772e55c936d6f6ad1890e89b4b4063053b8498b28d325ac8`

Canonical full manuscript-package SHA-256:
`49a66843893dbb9dae6cf1c58e29346ce1706db4685e1467caf06e69023d6768`

The canonical active files are the `FINAL_NEUTRAL_COLOR_FIGURES` files in the Drive `/submission` layer. Repository paths `manuscript/main.tex` and `manuscript/references.bib` remain release-era provenance and are not the authoritative current manuscript source. The hash-identified Drive source ZIP is authoritative for the active manuscript build.

## Language and presentation lock
- neutral academic prose
- zero authorial first-person pronouns
- no editorial-history or revision-process language in the manuscript
- no target-journal, special-issue, or journal-name positioning in the manuscript body/source
- no journal-name field in the manuscript source
- generic AI-assisted tools disclosure
- no figure or visual generated or modified by generative AI

## Compiler-topology robustness evidence
Repository `main` contains a compiler-only robustness layer under the locked Qiskit 2.4.2 compiler settings. Matched routed circuits are evaluated on synthetic bidirectional line, ring, and ladder-like coupling maps.

- workflow run: `34365030258`
- workflow artifact: `10109484982`
- artifact SHA-256: `540bc30840c1917e18b69b1d1ab68a54ea69b332eeb00b4ff0254ad1e3c1d0ac`
- locked line baseline: 57/57 rows reproduced, 0 metric mismatches
- QAOA ring/line median depth ratio: 0.9363; median CX ratio: 0.8971
- QAOA ladder/line median depth ratio: 0.7847; median CX ratio: 0.6218
- sparse-oracle ring/line median depth/CX ratios: 1.0015/1.0039
- sparse-oracle ladder/line median depth/CX ratios: 0.9271/0.9000

The compiler-topology layer is synthetic compiler-routing sensitivity evidence only. No backend calibration, duration, fidelity, energy, queue-time, or hardware-speedup claim is introduced.

## Evidence boundary
The active manuscript build does not create a new software release and does not move or rewrite the archived `v1.1.0` tag. Reproducibility claims about the archived computational evidence remain anchored to the immutable tag and DOI.