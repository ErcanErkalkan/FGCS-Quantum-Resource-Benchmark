from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE_PATHS = {
    "benchmark.py": "src/benchmark.py",
    "render_tables.py": "src/render_tables.py",
    "render_figures.py": "src/render_figures.py",
    "render_p2_figures.py": "src/render_p2_figures.py",
    "preflight.py": "src/preflight.py",
    "finalize_manifest.py": "src/finalize_manifest.py",
    "compiler_validation_qiskit.py": "src/compiler_validation_qiskit.py",
    "compiler_native_aa_crosscheck.py": "src/compiler_native_aa_crosscheck.py",
    "qaoa_threshold_objective_audit.py": "src/qaoa_threshold_objective_audit.py",
    "compiler-validation.yml": ".github/workflows/compiler-validation.yml",
    "compiler-native-aa.yml": ".github/workflows/compiler-native-aa.yml",
    "test_core.py": "tests/test_core.py",
    "test_preflight.py": "tests/test_preflight.py",
    "test_finalize_manifest.py": "tests/test_finalize_manifest.py",
    "main.tex": "manuscript/main.tex",
    "references.bib": "manuscript/references.bib",
    "README.md": "README.md",
    "CLAIMS_REGISTER.md": "manuscript/CLAIMS_REGISTER.md",
    "requirements.txt": "requirements.txt",
    "requirements.lock": "requirements.lock",
    ".python-version": ".python-version",
}

MANUSCRIPT_DEPENDENCIES = [
    "results/table_suite.tex",
    "results/table_operational_threshold.tex",
    "results/table_operational_metric.tex",
    "results/table_coverage.tex",
    "results/table_graph_structure_audit.tex",
    "results/table_connected_validation.tex",
    "results/table_oracle_resource.tex",
    "results/table_coupled_oracle.tex",
    "results/table_fixed_overhead.tex",
    "results/table_bbht_summary.tex",
    "results/table_aa_aggregate.tex",
    "results/table_target_metric.tex",
    "results/table_qaoa_aggregate.tex",
    "results/table_qaoa_stability.tex",
    "results/table_qaoa_optimizer_budget.tex",
    "results/table_qaoa_inference.tex",
    "results/table_gw_sdp.tex",
    "figures/fig_fixed_overhead_phase.pdf",
    "figures/fig_aa_sensitivity.pdf",
    "figures/fig_threshold_common_metric.pdf",
    "figures/fig_qaoa_depth.pdf",
    "figures/fig_qaoa_vs_local.pdf",
]

EXTRA_SCIENCE_ARTIFACTS = [
    "results/oracle_resource_model.csv",
    "results/coupled_oracle_depth_sensitivity.csv",
    "results/fixed_overhead_sensitivity.csv",
    "results/qaoa_initialization_stability_runs.csv",
    "results/qaoa_initialization_stability_instance_summary.csv",
    "results/qaoa_initialization_stability_aggregate.csv",
    "results/qaoa_initialization_stability_inference.csv",
    "results/qaoa_initialization_stability_comparison.csv",
    "results/compiler_validation_qiskit.csv",
    "results/compiler_validation_summary.json",
    "results/compiler_vs_analytic_oracle.csv",
    "results/compiler_native_aa_crosscheck.csv",
    "results/compiler_native_aa_summary.json",
    "results/qaoa_threshold_training_budget_runs.csv",
    "results/qaoa_threshold_training_budget_paired.csv",
    "results/qaoa_threshold_training_budget_instance_summary.csv",
    "results/qaoa_threshold_training_budget_inference.csv",
    "reproducibility/P15_QAOA_THRESHOLD_OBJECTIVE.md",
    "reproducibility/compiler_environment.json",
    "reproducibility/compiler_environment_pip_freeze.txt",
    "reproducibility/P14_COMPILER_LOCKED_VALIDATION.md",
    "reproducibility/P16_COMPILER_NATIVE_AA_CROSSCHECK.md",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def finalize(root: Path) -> dict:
    manifest_path = root / "results" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    missing = []
    source_hashes = {}
    for name, rel in SOURCE_PATHS.items():
        p = root / rel
        if not p.exists():
            missing.append(rel)
        else:
            source_hashes[name] = sha256(p)

    dep_hashes = {}
    for rel in MANUSCRIPT_DEPENDENCIES:
        p = root / rel
        if not p.exists():
            missing.append(rel)
        else:
            dep_hashes[rel] = sha256(p)

    if missing:
        raise FileNotFoundError("missing final-manifest dependencies: " + ", ".join(sorted(missing)))

    # Refresh every already-declared scientific artifact hash after deterministic
    # render steps, and add the architecture-informed ledgers that became canonical
    # after P4. Artifact names remain basename keys for backward compatibility.
    refreshed_artifacts = {}
    for name in manifest.get("sha256", {}):
        matches = [p for p in (root / "data" / name, root / "results" / name, root / "figures" / name, root / "reproducibility" / name) if p.exists()]
        if len(matches) != 1:
            raise FileNotFoundError(f"cannot uniquely resolve declared artifact {name}: {matches}")
        refreshed_artifacts[name] = sha256(matches[0])
    for rel in EXTRA_SCIENCE_ARTIFACTS:
        p = root / rel
        if not p.exists():
            raise FileNotFoundError(f"missing canonical scientific artifact: {rel}")
        refreshed_artifacts[p.name] = sha256(p)
    manifest["sha256"] = refreshed_artifacts
    suite = manifest.setdefault("suite", {})
    oracle_path = root / "results" / "oracle_resource_model.csv"
    coupled_path = root / "results" / "coupled_oracle_depth_sensitivity.csv"
    fixed_overhead_path = root / "results" / "fixed_overhead_sensitivity.csv"
    if oracle_path.exists():
        suite["oracle_resource_model_rows"] = max(0, len(oracle_path.read_text(encoding="utf-8").splitlines()) - 1)
    if coupled_path.exists():
        suite["coupled_oracle_depth_rows"] = max(0, len(coupled_path.read_text(encoding="utf-8").splitlines()) - 1)
    if fixed_overhead_path.exists():
        suite["fixed_overhead_sensitivity_rows"] = max(0, len(fixed_overhead_path.read_text(encoding="utf-8").splitlines()) - 1)
    compiler_csv = root / "results" / "compiler_validation_qiskit.csv"
    if compiler_csv.exists():
        suite["compiler_validation_rows"] = max(0, len(compiler_csv.read_text(encoding="utf-8").splitlines()) - 1)
    compiler_gap_csv = root / "results" / "compiler_vs_analytic_oracle.csv"
    if compiler_gap_csv.exists():
        suite["compiler_vs_analytic_oracle_rows"] = max(0, len(compiler_gap_csv.read_text(encoding="utf-8").splitlines()) - 1)
    compiler_native_csv = root / "results" / "compiler_native_aa_crosscheck.csv"
    if compiler_native_csv.exists():
        suite["compiler_native_aa_crosscheck_rows"] = max(0, len(compiler_native_csv.read_text(encoding="utf-8").splitlines()) - 1)
    threshold_files = {
        "qaoa_threshold_training_budget_runs_rows": root / "results" / "qaoa_threshold_training_budget_runs.csv",
        "qaoa_threshold_training_budget_paired_rows": root / "results" / "qaoa_threshold_training_budget_paired.csv",
        "qaoa_threshold_training_budget_instance_rows": root / "results" / "qaoa_threshold_training_budget_instance_summary.csv",
        "qaoa_threshold_training_budget_inference_rows": root / "results" / "qaoa_threshold_training_budget_inference.csv",
    }
    for key, path in threshold_files.items():
        if path.exists():
            suite[key] = max(0, len(path.read_text(encoding="utf-8").splitlines()) - 1)

    manifest["source_sha256"] = source_hashes
    manifest["manuscript_dependency_sha256"] = dep_hashes
    manifest["finalization"] = {
        "script": "src/finalize_manifest.py",
        "manuscript_dependency_count": len(dep_hashes),
        "source_dependency_count": len(source_hashes),
        "note": "Hashes synchronize the rendered manuscript inputs; they do not add a new scientific evidence layer.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize canonical FGCS manifest after tables/figures are rendered")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    manifest = finalize(args.root)
    print(json.dumps(manifest["finalization"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
