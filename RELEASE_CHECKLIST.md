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
- [x] Final post-P16 regression suite: **94/94 PASS**
- [x] Final full reproducibility preflight: **302 PASS / 0 WARN / 0 FAIL**
- [x] Locked runtime verified at Python **3.13.5**

## Repository metadata
- [x] BSD-3-Clause software license and scope statement
- [x] Funding confirmed: no specific grant funding
- [x] ORCID recorded in title page and `CITATION.cff`
- [x] `CITATION.cff` finalized at version **1.1.0**
- [x] Frozen public `v1.0.0` baseline retained
- [x] Compiler evidence explicitly separated from physical-hardware evidence
- [x] P16 analytical-vs-compiler metric non-equivalence explicitly documented
- [x] Final release notes synchronized with the post-P16 verification state

## Final publication actions
- [x] Complete final reviewer-style A-Z audit of the frozen post-P16 tree
- [x] Freeze and commit the verified `v1.1.0` tree
- [x] Run final full regression/preflight/CI on the frozen release candidate
- [x] Prepare annotated `v1.1.0` tag on the verified release tree
- [x] Verify remote tag target before public release publication
- [ ] Enable/verify the repository in Zenodo before publishing the GitHub Release
- [ ] Publish GitHub Release `v1.1.0` from the final verified annotated tag
- [ ] Verify Zenodo ingestion and record version/concept DOI
- [ ] Add final DOI/version citation to README and manuscript Data and Code Availability
- [ ] Do not modify the archived `v1.1.0` tag after DOI creation

## Final verification policy
The public `v1.1.0` tag must target the exact metadata-final commit whose GitHub Actions run passes the locked regression suite and full preflight. If a pre-release metadata correction is made before GitHub Release/Zenodo publication, rerun CI and retarget the tag once before publication. After Zenodo DOI creation, the archived tag is immutable.
