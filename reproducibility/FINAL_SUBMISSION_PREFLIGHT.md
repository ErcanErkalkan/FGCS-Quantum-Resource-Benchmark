# Final submission / preservation preflight

Date: 2026-08-31

Status: **P2 LOCAL RELEASE CANDIDATE PASS — GITHUB REMOTE / ZENODO ARCHIVE / DRIVE SUBMISSION SYNC PENDING**

The canonical manuscript, rendered tables/figures, bibliography, machine-readable results, executable source, environment lock, claim boundaries, and P2 repository-preservation metadata are synchronized locally. Numerical evidence is unchanged from the validated P1 scientific candidate.

## Validated scientific/package state
- 68/68 regression tests PASS.
- Full preflight: 158 PASS, 0 WARN, 0 FAIL.
- Final manuscript candidate: 15 pages using `elsarticle` 5p,times.
- 0 overfull boxes, 0 unresolved references/citations, 0 LaTeX warnings.
- `run_manifest.json` hashes the current canonical manuscript dependencies and source set.

## P2 repository/preservation additions
- Intended GitHub repository: `ErcanErkalkan/FGCS-Quantum-Resource-Benchmark`.
- `CITATION.cff` prepared for GitHub/Zenodo citation metadata.
- GitHub Actions reproducibility workflow prepared using `.python-version` and `requirements.lock`.
- `ZENODO_RELEASE_GUIDE.md`, `RELEASE_NOTES_v1.0.0.md`, and `RELEASE_CHECKLIST.md` added.
- Current manuscript PDF is included under `artifacts/` for archival convenience.

## Publication metadata intentionally unresolved
- software license/SPDX identifier: AUTHOR CONFIRMATION REQUIRED;
- funding/grant status: AUTHOR CONFIRMATION REQUIRED;
- ORCID: not inferred;
- journal article DOI: not yet available;
- Zenodo DOI: not yet available.

No DOI, grant, license, ORCID, hardware result, compiler result, or quantum-advantage claim is invented by this release-preparation phase.

## Remote state
The existing Google Drive submission package has not been overwritten in this phase. The GitHub repository does not yet exist remotely because the connected GitHub tool supports repository writes but not repository creation. Zenodo publication must occur only after a new public repository is created, the author confirms license/funding metadata, the repository is enabled in Zenodo, and a verified GitHub `v1.0.0` release is made.
