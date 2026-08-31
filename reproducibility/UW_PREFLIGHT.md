# U/W — Environment lock and automated preflight

Date: 2026-08-31
Target: canonical Future Generation Computer Systems manuscript only.

## Environment lock
- Python: 3.13.5 via `.python-version`.
- Direct runtime/test dependencies are exactly pinned in `requirements.txt`.
- The validated transitive dependency closure is exactly pinned in `requirements.lock`.
- The lock includes NumPy 2.3.5, SciPy 1.17.0, Matplotlib 3.10.8, pytest 9.0.2, and the installed transitive dependencies used by the workflow.

## Finalization and full preflight
`src/finalize_manifest.py` is run after tables and figures are rendered. It hashes the executable/source set and every LaTeX table and PDF figure actually included by `manuscript/main.tex`. It also refreshes declared scientific-artifact hashes without changing scientific results.

`src/preflight.py` is fail-closed. Full mode checks required canonical files, locked runtime versions, scientific-artifact SHA-256 values, manuscript-dependency SHA-256 values, declared CSV row counts, duplicate canonical files, LaTeX environment balance, and evidence/claim fences.

## Final validation result
- Regression/scientific tests: **68/68 PASS**.
- Full preflight: **PASS**.
- Full preflight checks: **158 PASS, 0 WARN, 0 FAIL**.
- Runtime checked: yes.
- Scientific artifacts checked: yes.
- Rendered manuscript dependencies checked: yes.
- Final LaTeX compilation: **PASS**, 15 pages in `5p,times` double-column format.
- Final log: 0 overfull boxes, 0 undefined references/citations, 0 LaTeX warnings.
- Visual QA: all 15 pages were rendered; wide tables, the updated 18-instance QAOA figures, and the fixed-overhead phase-boundary figure remain inside the two-column text blocks with no clipping or overlap.
- P0-1 regression: random graph streams are deterministic per `(n,density,seed)` configuration and regression tests prohibit the former cross-density prefix nesting.
- P0-2 regression: zero fixed-overhead behavior is preserved exactly, while an 8,085-row fixed-overhead boundary sweep is hash- and row-count checked.

## Evidence boundary
A preflight PASS means the package is internally synchronized with its declared evidence and environment. It does not convert analytical/logical-model results into compiler or hardware evidence and does not support a quantum-advantage claim.
