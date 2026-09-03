# v1.1.0 reviewer-driven release checklist

## Scientific revision lock
- [x] Structural audit of primary/coverage graph tiers
- [x] 45-instance connected, non-bipartite exact validation tier
- [x] Certified Goemans-Williamson SDP/rounding reference
- [x] BBHT unknown-solution-count evidence layer
- [x] Logical resource-scalarization sensitivity and fixed-overhead boundary
- [x] Classical objective-evaluation budget curve
- [x] Dense operational-threshold sweep
- [x] Instance-conditioned QAOA initialization stream
- [x] 20-start QAOA initialization-stability audit
- [x] P15 threshold-objective QAOA sensitivity under matched 128-evaluation cap
- [x] P14 compiler-locked Qiskit validation and semantic oracle check
- [x] P16 compiler-native AA configuration cross-check
- [x] Literature expansion and FGCS positioning review
- [x] Current manuscript compressed to **18 pages** without font/spacing hacks
- [x] Current P16 LaTeX: no unresolved citations/references, warnings, or overfull boxes
- [x] Current P16 manuscript: all 18 pages visually checked
- [x] P14/P15/P16 dedicated evidence checks: **11/11 + 3/3 + 9/9 PASS**
- [ ] **Run final post-P16 full regression suite and full reproducibility preflight** using root script `FINALIZE_V1_1_LOCAL.ps1`

> Historical full-project checkpoint before P14-P16: 93/93 regression tests and 244 PASS / 0 WARN / 0 FAIL full preflight. Do not label these as the final post-P16 result.

## Repository metadata
- [x] BSD-3-Clause software license and scope statement
- [x] Funding confirmed: no specific grant funding
- [x] ORCID recorded in title page and `CITATION.cff`
- [x] Frozen public `v1.0.0` baseline retained
- [x] Active scientific work isolated in `v1.1.0_WORKING`
- [x] Compiler evidence explicitly separated from physical-hardware evidence
- [x] P16 analytical-vs-compiler metric non-equivalence explicitly documented

## Final publication actions
- [ ] Complete final reviewer-style A-Z audit of the frozen post-P16 tree
- [ ] Freeze and commit the verified `v1.1.0` tree
- [ ] Run final full regression/preflight/CI on that exact commit
- [ ] Tag the verified commit as `v1.1.0`
- [ ] Push `v1.1.0` to the public GitHub repository
- [ ] Enable/verify the repository in Zenodo before publishing the release
- [ ] Create GitHub release `v1.1.0` from the verified tag
- [ ] Verify Zenodo ingestion and record version/concept DOI
- [ ] Add final DOI/version citation to README and manuscript Data and Code Availability
- [ ] Do not modify the archived `v1.1.0` tag after DOI creation
