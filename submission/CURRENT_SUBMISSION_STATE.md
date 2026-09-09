# Current FGCS submission presentation state

Last audited: 2026-09-09

## Immutable reproducibility release
- Archived software/reproducibility release: `v1.1.0`
- Archived tag commit: `923ffe7570dd2d8fb6235ae6eab63a5cf1c50b8d`
- Zenodo version DOI: `10.5281/zenodo.22272778`
- The archived tag and Zenodo record are not rewritten by later journal-presentation edits.

## Current journal presentation layer
The active FGCS submission manuscript retains the core benchmark numerical evidence, equations, original experiment outputs, tables, and figure data of the reproducibility evidence line while incorporating later journal-presentation refinements. These include clearer systems-positioning language, explicit explanation of attenuation-grid roles, aligned AI-use disclosure, publication-quality color-figure presentation, close-prior-work/corrigendum literature positioning, an explicit interpretation of the probability-per-resource objective, and a post-release compiler-topology robustness audit.

Canonical active manuscript filename:
`FGCS_manuscript_v1.1.0_FINAL_NEUTRAL_COLOR_FIGURES.pdf`

Canonical active manuscript SHA-256:
`81a7e89510e37c1a797a4be375604cbfcb88adc96cbe8ff155e3989a2ed61e71`

Canonical active LaTeX source-package SHA-256:
`91073fe9a13ddcad7bd9f548b74834f602e1b60cb5684d340973040b17f76447`

Canonical active full-submission-package SHA-256:
`1300694470ddb979c74bb1254980aee485ea358da754daa244fd539717332b51`

The canonical active files are the `FINAL_NEUTRAL_COLOR_FIGURES` files in the Drive `/submission` layer. The repository `manuscript/main.tex` and `manuscript/references.bib` paths are retained as release-era provenance and are **not** the authoritative current journal-presentation source. They must not be mistaken for the canonical active submission. The canonical LaTeX source is the hash-identified source ZIP above.

## Post-release compiler-topology robustness audit
Current `main` adds a compiler-only robustness layer under the same locked Qiskit 2.4.2 compiler settings. The same routed circuits are evaluated on synthetic bidirectional line, ring, and ladder-like coupling maps.

- workflow run: `34365030258`
- workflow artifact: `10109484982`
- artifact SHA-256: `540bc30840c1917e18b69b1d1ab68a54ea69b332eeb00b4ff0254ad1e3c1d0ac`
- locked line baseline: 57/57 rows reproduced, 0 metric mismatches
- QAOA ring/line median depth ratio: 0.9363; median CX ratio: 0.8971
- QAOA ladder/line median depth ratio: 0.7847; median CX ratio: 0.6218
- sparse-oracle ring/line median depth/CX ratios: 1.0015/1.0039
- sparse-oracle ladder/line median depth/CX ratios: 0.9271/0.9000

This is synthetic compiler-routing sensitivity evidence only. It does not add backend calibration, duration, fidelity, energy, queue-time, or hardware-speedup claims.

## Evidence boundary
The current journal presentation layer does not create a new software release and must not be used to move or rewrite the archived `v1.1.0` tag. Reproducibility claims about the archived computational evidence remain anchored to the immutable tag/DOI. Later prose, disclosure, literature-positioning, objective-clarification, publication-presentation, and compiler-topology robustness changes are journal-submission refinements rather than retrospective rewriting of the archived release.