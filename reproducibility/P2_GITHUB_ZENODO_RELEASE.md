# P2 — GitHub/Zenodo release preparation

Status: **LOCAL RELEASE CANDIDATE PREPARED; REMOTE REPOSITORY / ZENODO PUBLICATION PENDING**

This phase adds preservation and citation infrastructure without changing numerical benchmark evidence.

## Added
- GitHub-ready `.gitignore`.
- `CITATION.cff` with creator, title, version, repository target, keywords, and evidence-bounded description.
- GitHub Actions reproducibility workflow using `.python-version` and `requirements.lock`.
- `ZENODO_RELEASE_GUIDE.md`, `RELEASE_NOTES_v1.0.0.md`, and `RELEASE_CHECKLIST.md`.
- Current manuscript PDF and checksum record under `artifacts/` for release convenience.

## Release metadata and still-unresolved identifiers
- software license: **BSD-3-Clause** (author-confirmed);
- funding/grant status: **no specific grant funding** (author-confirmed);
- ORCID: not inferred;
- article DOI: pending publication;
- Zenodo DOI: pending archival release.

DOI fields remain absent until the corresponding services create them.

## Preservation strategy
Use the public GitHub repository `ErcanErkalkan/FGCS-Quantum-Resource-Benchmark`, enable it in Zenodo, then create a verified `v1.0.0` GitHub release. Zenodo will preserve the release snapshot and assign the archival DOI. A DOI-only documentation update may then be made on the default branch without modifying the archived tag.
