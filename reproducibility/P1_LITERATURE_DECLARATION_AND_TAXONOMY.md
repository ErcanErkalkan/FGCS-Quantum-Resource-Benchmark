# P1 — literature positioning, declaration, and graph-taxonomy lock

Date: 2026-08-31
Status: PASS (local candidate; Drive synchronization pending)

## Scope
P1 does not change the numerical benchmark evidence. It strengthens literature positioning, corrects the random-graph family label, and makes author/AI declarations auditable.

## Literature additions
- Boyer, Brassard, Høyer, and Tapp (1998), *Tight Bounds on Quantum Searching*, DOI `10.1002/(SICI)1521-3978(199806)46:4/5<493::AID-PROP493>3.0.CO;2-P`. Used only to position unknown-solution-count quantum search (BBHT).
- Li et al. (2023), *QASMBench*, DOI `10.1145/3550488`. Used to position low-level device/compiler/simulator benchmarking.
- Tomesh et al. (2022), *SupermarQ*, DOI `10.1109/HPCA53966.2022.00050`. Used to position scalable hardware-agnostic application-level suite construction.
- Lubinski et al. (2023), *Application-Oriented Performance Benchmarks for Quantum Computing*, DOI `10.1109/TQE.2023.3253761`. Used to position end-user/application-oriented benchmarking and execution-pipeline metrics.

## Taxonomy correction
The random suite samples an exact edge count after a configuration-specific deterministic shuffle. The canonical family label is therefore `random_fixed_density`. The code, tests, machine-readable CSVs, README, and claims register no longer use the legacy `erdos_renyi` family label. The manuscript explicitly states that the design is not an Erdős–Rényi `G(n,p)` draw.

## AI disclosure
Elsevier's current journal policy requires research-process AI use such as AI-assisted code development to be described in Methods, and manuscript-preparation use to be declared before the references. Both locations are present. The final P1 audit records OpenAI ChatGPT / GPT-5.6 Sol on 31 August 2026. Earlier exact model identifiers were not consistently logged and are not reconstructed retrospectively.

## CRediT
A single-author CRediT statement is included for the documented roles: Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data curation, Visualization, Writing — original draft, Writing — review and editing, Project administration.

## Funding
Funding status remains a manual author confirmation. No grant and no no-funding declaration is inferred from silence or from unrelated projects.

## Validation
- pytest: 68/68 PASS
- full preflight: 158 PASS, 0 WARN, 0 FAIL
- PDF: 15 pages, 0 overfull boxes, 0 undefined references/citations, 0 LaTeX warnings
- visual QA: 15/15 pages rendered without clipping or overlap
