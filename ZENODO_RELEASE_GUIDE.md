# GitHub -> Zenodo archival procedure for v1.1.0

The public repository is:
`https://github.com/ErcanErkalkan/FGCS-Quantum-Resource-Benchmark`

The existing `v1.0.0` tag is a frozen baseline and must not be changed. The reviewer-driven revision will be archived as `v1.1.0` only after final validation.

## Before creating the release
1. Confirm the active revision has 0 failing tests/preflight checks.
2. Confirm `CITATION.cff` contains the final version, author ORCID, license, and repository URL.
3. Confirm manuscript Data and Code Availability does not claim a DOI that does not yet exist.
4. Enable or verify the repository in the Zenodo GitHub integration.
5. Create and push the verified annotated tag `v1.1.0`.

## Archive sequence
1. On GitHub, create a release from the existing `v1.1.0` tag; do not create a different tag from the web form.
2. Suggested release title: `FGCS Quantum Resource Benchmark v1.1.0`.
3. Publish the release only after Zenodo integration is enabled/verified.
4. Verify that Zenodo ingests the GitHub release and assigns both a version DOI and a concept DOI.
5. Record both DOI values in the release audit notes.
6. Add the version DOI/citation to README and manuscript Data and Code Availability in a post-archive documentation commit.
7. Never rewrite or move the archived `v1.1.0` tag after DOI creation.

## Evidence rule
Zenodo archival proves preservation of a software/reproducibility snapshot; it does not upgrade analytical or simulated results into compiler, device, runtime, or quantum-advantage evidence.
