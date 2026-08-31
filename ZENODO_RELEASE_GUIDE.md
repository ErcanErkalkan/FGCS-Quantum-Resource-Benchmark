# GitHub → Zenodo archival release guide

## Intended repository
`ErcanErkalkan/FGCS-Quantum-Resource-Benchmark`

## Release gate
Do **not** create the final public release until both items below are confirmed by the author:
1. software license/SPDX identifier;
2. funding status and, if applicable, grant metadata.

The scientific package itself is already reproducibility-validated. These two items are publication metadata/legal declarations, not numerical-analysis gaps.

## Recommended first release
- Git tag/release: `v1.0.0`
- Release title: `FGCS Quantum Resource Benchmark v1.0.0`
- GitHub repository visibility: public, if open Zenodo preservation is intended.
- Release source: exact commit passing the locked test/preflight checks.

## Zenodo workflow
1. Connect the same GitHub account to Zenodo.
2. In Zenodo → GitHub, choose **Sync now**.
3. Find `FGCS-Quantum-Resource-Benchmark` and enable the repository toggle.
4. Confirm the repository contains `CITATION.cff` before the first release.
5. Verify `BSD-3-Clause` is represented in `LICENSE` and `CITATION.cff` before release.
6. Create GitHub release `v1.0.0` from the verified commit.
7. Zenodo should ingest the release and create an archived software record with a version DOI.
8. Record both the **version DOI** and the **concept DOI** returned by Zenodo.
9. Add the DOI badge and citation to `README.md` and, where appropriate, the manuscript Data and Code Availability statement.
10. Commit the DOI-only metadata update as a post-archive documentation commit; do not alter the archived v1.0.0 files retroactively.

## Important DOI rule
Zenodo's GitHub integration does not provide a DOI that can be reserved before the GitHub release. If a DOI must appear inside the exact v1.0.0 manuscript/files before archival, use a manual Zenodo deposit instead and reserve a DOI there first.

## Metadata behavior
Zenodo supports `CITATION.cff` for GitHub releases. If a root `.zenodo.json` is later added, Zenodo will use `.zenodo.json` instead of `CITATION.cff` for GitHub-release metadata. Do not add `.zenodo.json` casually; use it only if Zenodo-specific metadata such as grants, communities, access settings, or related identifiers is needed.

## Current package facts
- 18 primary exact weighted Max-Cut instances.
- 63-instance exact coverage tier.
- 270 primary QAOA runs.
- 540 paired optimizer-budget QAOA runs.
- 8,085 fixed-overhead sensitivity conditions.
- 68/68 regression tests PASS.
- Full preflight: 158 PASS, 0 WARN, 0 FAIL before repository-metadata additions.
- Current compiled manuscript candidate: 15 pages.

## Files to cite
The archival GitHub/Zenodo release should be the primary reproducibility citation. The associated journal article should be added as a related work after it receives its DOI.
