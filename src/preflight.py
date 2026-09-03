from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Check:
    name: str
    status: str  # PASS | WARN | FAIL
    detail: str


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def parse_lock(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            raise ValueError(f"unlocked requirement line: {line}")
        name, version = line.split("==", 1)
        out[name.strip().lower()] = version.strip()
    return out


def resolve_artifact(root: Path, name: str) -> tuple[Path | None, list[Path]]:
    candidates = [p for p in (root / "data" / name, root / "results" / name, root / "figures" / name, root / "reproducibility" / name) if p.exists()]
    if len(candidates) == 1:
        return candidates[0], candidates
    return None, candidates


def expected_count_checks(manifest: dict) -> dict[str, int]:
    suite = manifest.get("suite", {})
    qaoa = manifest.get("qaoa", {})
    checks: dict[str, int] = {}
    mapping = {
        "maxcut_ground_truth.csv": suite.get("exact_instances"),
        "operational_thresholds.csv": suite.get("operational_threshold_rows"),
        "classical_budgeted_runs.csv": suite.get("budgeted_classical_raw_rows"),
        "classical_budgeted_summary.csv": suite.get("budgeted_classical_summary_rows"),
        "classical_budget_curve_runs.csv": suite.get("classical_budget_curve_raw_rows"),
        "classical_budget_curve_summary.csv": suite.get("classical_budget_curve_summary_rows"),
        "classical_budget_curve_aggregate.csv": suite.get("classical_budget_curve_aggregate_rows"),
        "qaoa_runs.csv": qaoa.get("total_runs"),
        "qaoa_initialization_stability_runs.csv": suite.get("qaoa_stability_total_runs"),
        "qaoa_initialization_stability_instance_summary.csv": suite.get("qaoa_stability_instance_summary_rows"),
        "qaoa_initialization_stability_aggregate.csv": suite.get("qaoa_stability_aggregate_rows"),
        "qaoa_initialization_stability_inference.csv": suite.get("qaoa_stability_inference_rows"),
        "qaoa_initialization_stability_comparison.csv": suite.get("qaoa_stability_comparison_rows"),
        "qaoa_optimizer_budget_runs.csv": suite.get("qaoa_optimizer_budget_runs"),
        "qaoa_optimizer_budget_paired.csv": suite.get("qaoa_optimizer_paired_rows"),
        "qaoa_depth_inference.csv": suite.get("qaoa_depth_inference_rows"),
        "qaoa_optimizer_inference_instance_deltas.csv": suite.get("qaoa_optimizer_inference_instance_rows"),
        "qaoa_optimizer_inference.csv": suite.get("qaoa_optimizer_inference_rows"),
        "coverage_graphs.csv": suite.get("coverage_graph_edge_rows"),
        "coverage_ground_truth.csv": suite.get("coverage_exact_instances"),
        "coverage_operational_thresholds.csv": suite.get("coverage_operational_threshold_rows"),
        "coverage_hillclimb.csv": suite.get("coverage_hillclimb_rows"),
        "coverage_coupled_oracle.csv": suite.get("coverage_coupled_oracle_rows"),
        "coverage_summary.csv": suite.get("coverage_summary_rows"),
        "primary_graph_diagnostics.csv": suite.get("primary_graph_diagnostic_rows"),
        "coverage_graph_diagnostics.csv": suite.get("coverage_graph_diagnostic_rows"),
        "connected_validation_graphs.csv": suite.get("connected_validation_graph_edge_rows"),
        "connected_validation_graph_diagnostics.csv": suite.get("connected_validation_graph_diagnostic_rows"),
        "connected_validation_ground_truth.csv": suite.get("connected_validation_exact_instances"),
        "connected_validation_operational_thresholds.csv": suite.get("connected_validation_operational_threshold_rows"),
        "connected_validation_coupled_oracle.csv": suite.get("connected_validation_coupled_oracle_rows"),
        "connected_validation_fixed_overhead.csv": suite.get("connected_validation_fixed_overhead_rows"),
        "gw_sdp_primary.csv": suite.get("gw_primary_rows"),
        "gw_sdp_connected_validation.csv": suite.get("gw_connected_validation_rows"),
        "bbht_operational_primary.csv": suite.get("bbht_primary_rows"),
        "bbht_operational_connected_validation.csv": suite.get("bbht_connected_validation_rows"),
        "bbht_summary.csv": suite.get("bbht_summary_rows"),
        "resource_scalarization_primary.csv": suite.get("resource_scalarization_primary_rows"),
        "resource_scalarization_connected_validation.csv": suite.get("resource_scalarization_connected_validation_rows"),
        "dense_operational_lambda_primary.csv": suite.get("dense_operational_lambda_primary_rows"),
        "dense_operational_lambda_connected_validation.csv": suite.get("dense_operational_lambda_connected_validation_rows"),
        "dense_operational_lambda_summary.csv": suite.get("dense_operational_lambda_summary_rows"),
        "resource_scalarization_summary.csv": suite.get("resource_scalarization_summary_rows"),
        "oracle_resource_model.csv": suite.get("oracle_resource_model_rows"),
        "coupled_oracle_depth_sensitivity.csv": suite.get("coupled_oracle_depth_rows"),
        "fixed_overhead_sensitivity.csv": suite.get("fixed_overhead_sensitivity_rows"),
        "compiler_validation_qiskit.csv": suite.get("compiler_validation_rows"),
        "compiler_vs_analytic_oracle.csv": suite.get("compiler_vs_analytic_oracle_rows"),
        "compiler_native_aa_crosscheck.csv": suite.get("compiler_native_aa_crosscheck_rows"),
        "qaoa_threshold_training_budget_runs.csv": suite.get("qaoa_threshold_training_budget_runs_rows"),
        "qaoa_threshold_training_budget_paired.csv": suite.get("qaoa_threshold_training_budget_paired_rows"),
        "qaoa_threshold_training_budget_instance_summary.csv": suite.get("qaoa_threshold_training_budget_instance_rows"),
        "qaoa_threshold_training_budget_inference.csv": suite.get("qaoa_threshold_training_budget_inference_rows"),
    }
    for name, value in mapping.items():
        if value is not None:
            checks[name] = int(value)
    return checks


def source_location(root: Path, name: str) -> Path | None:
    fixed = {
        "benchmark.py": root / "src" / "benchmark.py",
        "render_tables.py": root / "src" / "render_tables.py",
        "render_figures.py": root / "src" / "render_figures.py",
        "render_p2_figures.py": root / "src" / "render_p2_figures.py",
        "finalize_manifest.py": root / "src" / "finalize_manifest.py",
        "compiler_validation_qiskit.py": root / "src" / "compiler_validation_qiskit.py",
        "compiler_native_aa_crosscheck.py": root / "src" / "compiler_native_aa_crosscheck.py",
        "qaoa_threshold_objective_audit.py": root / "src" / "qaoa_threshold_objective_audit.py",
        "preflight.py": root / "src" / "preflight.py",
        "test_core.py": root / "tests" / "test_core.py",
        "test_preflight.py": root / "tests" / "test_preflight.py",
        "test_finalize_manifest.py": root / "tests" / "test_finalize_manifest.py",
        "main.tex": root / "manuscript" / "main.tex",
        "references.bib": root / "manuscript" / "references.bib",
        "README.md": root / "README.md",
        "CLAIMS_REGISTER.md": root / "manuscript" / "CLAIMS_REGISTER.md",
        "requirements.txt": root / "requirements.txt",
        "requirements.lock": root / "requirements.lock",
        ".python-version": root / ".python-version",
    }
    p = fixed.get(name)
    if p is not None:
        return p
    matches = list(root.glob(f"**/{name}"))
    return matches[0] if len(matches) == 1 else None


def check_required_structure(root: Path) -> list[Check]:
    required = [
        "README.md",
        "requirements.txt",
        "requirements.lock",
        ".python-version",
        "src/benchmark.py",
        "src/render_tables.py",
        "src/render_figures.py",
        "src/render_p2_figures.py",
        "src/preflight.py",
        "src/finalize_manifest.py",
        "src/compiler_validation_qiskit.py",
        "src/compiler_native_aa_crosscheck.py",
        "src/qaoa_threshold_objective_audit.py",
        ".github/workflows/compiler-validation.yml",
        ".github/workflows/compiler-native-aa.yml",
        "tests/test_core.py",
        "tests/test_preflight.py",
        "tests/test_finalize_manifest.py",
        "manuscript/main.tex",
        "manuscript/references.bib",
        "manuscript/CLAIMS_REGISTER.md",
        "results/run_manifest.json",
        "results/gw_sdp_primary.csv",
        "results/gw_sdp_connected_validation.csv",
        "results/gw_sdp_summary.csv",
        "results/table_gw_sdp.tex",
        "results/bbht_operational_primary.csv",
        "results/bbht_operational_connected_validation.csv",
        "results/bbht_summary.csv",
        "results/resource_scalarization_primary.csv",
        "results/resource_scalarization_connected_validation.csv",
        "results/resource_scalarization_summary.csv",
        "results/classical_budget_curve_runs.csv",
        "results/classical_budget_curve_summary.csv",
        "results/classical_budget_curve_aggregate.csv",
        "results/dense_operational_lambda_primary.csv",
        "results/dense_operational_lambda_connected_validation.csv",
        "results/dense_operational_lambda_summary.csv",
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
        "reproducibility/compiler_environment.json",
        "reproducibility/compiler_environment_pip_freeze.txt",
        "reproducibility/P14_COMPILER_LOCKED_VALIDATION.md",
        "reproducibility/P16_COMPILER_NATIVE_AA_CROSSCHECK.md",
        "reproducibility/ENVIRONMENT_LOCK.md",
        "reproducibility/P3_STRUCTURAL_GRAPH_VALIDATION.md",
        "reproducibility/P4_GW_SDP_BASELINE.md",
        "reproducibility/P5_BBHT_UNKNOWN_RHO.md",
        "reproducibility/P6_RESOURCE_SCALARIZATION.md",
        "reproducibility/P7_CLASSICAL_BUDGET_CURVE.md",
        "reproducibility/P8_DENSE_OPERATIONAL_LAMBDA.md",
        "reproducibility/P9_QAOA_INITIALIZATION_STREAM.md",
        "reproducibility/P10_QAOA_20_START_STABILITY.md",
        "reproducibility/UW_PREFLIGHT.md",
    ]
    out = []
    for rel in required:
        p = root / rel
        out.append(Check(f"required:{rel}", "PASS" if p.exists() else "FAIL", "present" if p.exists() else "missing"))
    return out


def check_runtime_lock(root: Path) -> list[Check]:
    out: list[Check] = []
    py_file = root / ".python-version"
    lock_file = root / "requirements.lock"
    if not py_file.exists() or not lock_file.exists():
        return [Check("runtime-lock", "FAIL", "missing .python-version or requirements.lock")]
    expected_python = py_file.read_text(encoding="utf-8").strip()
    actual_python = ".".join(map(str, sys.version_info[:3]))
    out.append(Check("python-version", "PASS" if actual_python == expected_python else "FAIL", f"expected={expected_python}; actual={actual_python}"))
    try:
        lock = parse_lock(lock_file)
    except Exception as exc:
        return out + [Check("requirements-lock-parse", "FAIL", str(exc))]
    out.append(Check("requirements-lock-parse", "PASS", f"{len(lock)} exact pins"))
    for package, expected in sorted(lock.items()):
        try:
            actual = importlib.metadata.version(package)
            status = "PASS" if actual == expected else "FAIL"
            out.append(Check(f"package:{package}", status, f"expected={expected}; actual={actual}"))
        except importlib.metadata.PackageNotFoundError:
            out.append(Check(f"package:{package}", "FAIL", f"expected={expected}; package not installed"))
    return out


def check_manifest_hashes(root: Path, manifest: dict) -> list[Check]:
    out: list[Check] = []
    for name, expected in sorted(manifest.get("sha256", {}).items()):
        p, candidates = resolve_artifact(root, name)
        if p is None:
            detail = "missing" if not candidates else f"duplicate candidates={len(candidates)}"
            out.append(Check(f"artifact-hash:{name}", "FAIL", detail))
            continue
        actual = sha256(p)
        out.append(Check(f"artifact-hash:{name}", "PASS" if actual == expected else "FAIL", f"expected={expected}; actual={actual}"))
    for name, expected in sorted(manifest.get("source_sha256", {}).items()):
        p = source_location(root, name)
        if p is None or not p.exists():
            out.append(Check(f"source-hash:{name}", "FAIL", "missing or ambiguous"))
            continue
        actual = sha256(p)
        out.append(Check(f"source-hash:{name}", "PASS" if actual == expected else "FAIL", f"expected={expected}; actual={actual}"))
    for rel, expected in sorted(manifest.get("manuscript_dependency_sha256", {}).items()):
        p = root / rel
        if not p.exists():
            out.append(Check(f"manuscript-dependency-hash:{rel}", "FAIL", "missing"))
            continue
        actual = sha256(p)
        out.append(Check(f"manuscript-dependency-hash:{rel}", "PASS" if actual == expected else "FAIL", f"expected={expected}; actual={actual}"))
    return out


def check_row_counts(root: Path, manifest: dict) -> list[Check]:
    out: list[Check] = []
    for name, expected in sorted(expected_count_checks(manifest).items()):
        p, candidates = resolve_artifact(root, name)
        if p is None:
            out.append(Check(f"row-count:{name}", "FAIL", "missing" if not candidates else "duplicate artifact"))
            continue
        actual = csv_row_count(p)
        out.append(Check(f"row-count:{name}", "PASS" if actual == expected else "FAIL", f"expected={expected}; actual={actual}"))
    return out


def check_tex_balance(text: str) -> list[Check]:
    out = []
    envs = re.findall(r"\\begin\{([^}]+)\}", text)
    ends = re.findall(r"\\end\{([^}]+)\}", text)
    for env in sorted(set(envs) | set(ends)):
        a, b = envs.count(env), ends.count(env)
        out.append(Check(f"tex-env:{env}", "PASS" if a == b else "FAIL", f"begin={a}; end={b}"))
    return out


def find_affirmative_risky_claims(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?;])\s+", text)
    risk = re.compile(
        r"\b(?:achiev(?:e|es|ed)|demonstrat(?:e|es|ed)|establish(?:es|ed)?|prove(?:s|d)?|show(?:s|ed)?)\b.{0,50}\b(?:quantum|hardware)\b.{0,25}\b(?:advantage|speedup|superiority)\b",
        re.IGNORECASE,
    )
    neg = re.compile(r"\b(?:no|not|without|neither|cannot|does not|do not|is not|are not|not a|rather than)\b", re.IGNORECASE)
    out = []
    for s in sentences:
        if risk.search(s) and not neg.search(s):
            out.append(" ".join(s.split())[:240])
    return out


def check_claim_fences(root: Path, manifest: dict) -> list[Check]:
    out: list[Check] = []
    if manifest.get("hardware_claims") is not False:
        out.append(Check("manifest:hardware_claims", "FAIL", f"value={manifest.get('hardware_claims')}"))
    else:
        out.append(Check("manifest:hardware_claims", "PASS", "false"))
    compiler_mode = manifest.get("compiler_claims")
    if compiler_mode != "locked_synthetic_topology":
        out.append(Check("manifest:compiler_claims", "FAIL", f"expected=locked_synthetic_topology; value={compiler_mode}"))
    else:
        out.append(Check("manifest:compiler_claims", "PASS", compiler_mode))

    for rel in ["manuscript/main.tex", "README.md"]:
        p = root / rel
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        risky = find_affirmative_risky_claims(text)
        if risky:
            out.append(Check(f"claim-fence:{rel}", "FAIL", " | ".join(risky)))
        else:
            out.append(Check(f"claim-fence:{rel}", "PASS", "no affirmative hardware/quantum-advantage claim pattern"))

    main = (root / "manuscript" / "main.tex").read_text(encoding="utf-8") if (root / "manuscript" / "main.tex").exists() else ""
    required_phrases = {
        "primary-suite-size": "18 primary",
        "coverage-suite-size": "63 coverage",
        "fixed-qaoa-inference-boundary": "18-instance QAOA",
        "no-physical-backend": "No physical-backend",
        "compiler-lock": "Qiskit 2.4.2",
        "fixed-density-random-design": "fixed-edge-count/fixed-density random simple-graph design",
        "credit-statement": "CRediT authorship contribution statement",
        "ai-version-log": "GPT-5.6 Sol",
        "ai-history-limit": "not consistently recorded",
    }
    for key, phrase in required_phrases.items():
        out.append(Check(f"manuscript-fence:{key}", "PASS" if phrase in main else "FAIL", f"required phrase={phrase!r}"))

    refs_path = root / "manuscript" / "references.bib"
    refs = refs_path.read_text(encoding="utf-8") if refs_path.exists() else ""
    for key in ("boyer1998", "li2023qasmbench", "tomesh2022supermarq", "lubinski2023application"):
        token = "{" + key + ","
        out.append(Check(f"bibliography-fence:{key}", "PASS" if token in refs else "FAIL", f"required BibTeX key={key}"))

    benchmark_path = root / "src" / "benchmark.py"
    benchmark = benchmark_path.read_text(encoding="utf-8") if benchmark_path.exists() else ""
    legacy = "erdos_renyi"
    out.append(Check(
        "random-family-label",
        "PASS" if "random_fixed_density" in benchmark and legacy not in benchmark else "FAIL",
        "requires random_fixed_density and forbids legacy erdos_renyi label",
    ))
    return out


def check_compiler_evidence(root: Path, manifest: dict) -> list[Check]:
    out: list[Check] = []
    summary_path = root / "results" / "compiler_validation_summary.json"
    if not summary_path.exists():
        return [Check("compiler-evidence:summary", "FAIL", "results/compiler_validation_summary.json missing")]
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [Check("compiler-evidence:summary", "FAIL", f"unreadable: {exc}")]
    expected = {
        "qiskit_version": "2.4.2",
        "seed_transpiler": 20260901,
        "optimization_level": 1,
        "row_count": 66,
        "qaoa_routed_rows": 54,
        "oracle_basis_rows": 9,
        "oracle_sparse_routed_rows": 3,
    }
    for key, value in expected.items():
        actual = summary.get(key)
        out.append(Check(f"compiler-evidence:{key}", "PASS" if actual == value else "FAIL", f"expected={value}; actual={actual}"))
    basis = summary.get("basis_gates")
    out.append(Check("compiler-evidence:basis", "PASS" if basis == ["rz", "sx", "x", "cx"] else "FAIL", f"actual={basis}"))
    semantic = summary.get("semantic_oracle_check", {})
    semantic_ok = semantic.get("passed") is True and semantic.get("tested_basis_states") == 8 and not semantic.get("failures")
    out.append(Check("compiler-evidence:oracle-semantic", "PASS" if semantic_ok else "FAIL", f"{semantic}"))
    depths = summary.get("qaoa_median_compiled_depth_by_p", {})
    try:
        monotone = float(depths["1"]) < float(depths["2"]) < float(depths["3"])
    except Exception:
        monotone = False
    out.append(Check("compiler-evidence:qaoa-depth-order", "PASS" if monotone else "FAIL", f"depths={depths}"))

    gap_path = root / "results" / "compiler_vs_analytic_oracle.csv"
    if not gap_path.exists():
        out.append(Check("compiler-evidence:abstraction-gap", "FAIL", "results/compiler_vs_analytic_oracle.csv missing"))
    else:
        try:
            import csv as _csv
            with gap_path.open("r", encoding="utf-8", newline="") as fh:
                gap_rows = list(_csv.DictReader(fh))
            depth_ratios = [float(r["compiler_to_analytic_depth_ratio"]) for r in gap_rows]
            qubit_ratios = [float(r["compiler_to_analytic_qubit_ratio"]) for r in gap_rows]
            gap_ok = len(gap_rows) == 9 and min(depth_ratios) > 1.0 and all(1.0 <= q <= 2.0 for q in qubit_ratios)
            out.append(Check(
                "compiler-evidence:abstraction-gap",
                "PASS" if gap_ok else "FAIL",
                f"rows={len(gap_rows)}; depth_ratio_range=({min(depth_ratios):.3f},{max(depth_ratios):.3f}); qubit_ratio_range=({min(qubit_ratios):.3f},{max(qubit_ratios):.3f})",
            ))
        except Exception as exc:
            out.append(Check("compiler-evidence:abstraction-gap", "FAIL", f"unreadable: {exc}"))
    return out



def check_compiler_native_aa_evidence(root: Path, manifest: dict) -> list[Check]:
    summary_path = root / "results" / "compiler_native_aa_summary.json"
    csv_path = root / "results" / "compiler_native_aa_crosscheck.csv"
    if not summary_path.exists():
        return [Check("compiler-native-aa:summary", "FAIL", "results/compiler_native_aa_summary.json missing")]
    if not csv_path.exists():
        return [Check("compiler-native-aa:csv", "FAIL", "results/compiler_native_aa_crosscheck.csv missing")]
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception as exc:
        return [Check("compiler-native-aa:parse", "FAIL", str(exc))]

    checks: list[Check] = []
    checks.append(Check("compiler-native-aa:qiskit", "PASS" if summary.get("qiskit_version") == "2.4.2" else "FAIL", f"qiskit={summary.get('qiskit_version')}"))
    checks.append(Check("compiler-native-aa:basis", "PASS" if summary.get("basis_gates") == ["rz", "sx", "x", "cx"] else "FAIL", f"basis={summary.get('basis_gates')}"))
    checks.append(Check("compiler-native-aa:seed", "PASS" if int(summary.get("seed_transpiler", -1)) == 20260901 else "FAIL", f"seed={summary.get('seed_transpiler')}"))
    checks.append(Check("compiler-native-aa:rows", "PASS" if len(rows) == 9 and int(summary.get("row_count", -1)) == 9 else "FAIL", f"csv={len(rows)}, summary={summary.get('row_count')}"))
    size_k0 = bool(summary.get("all_k0_compiled_size")) and all(int(float(r["k_star_compiled_size"])) == 0 for r in rows)
    depth_k0 = bool(summary.get("all_k0_compiled_depth")) and all(int(float(r["k_star_compiled_depth"])) == 0 for r in rows)
    checks.append(Check("compiler-native-aa:k0-size", "PASS" if size_k0 else "FAIL", "9/9 expected k*=0"))
    checks.append(Check("compiler-native-aa:k0-depth", "PASS" if depth_k0 else "FAIL", "9/9 expected k*=0"))
    valid_rows = all(0.0 < float(r["rho"]) <= 1.0 and float(r["iteration_compiled_size"]) > 0 and float(r["iteration_compiled_depth"]) > 0 for r in rows)
    checks.append(Check("compiler-native-aa:positive-coordinates", "PASS" if valid_rows else "FAIL", "rho in (0,1], iteration coordinates positive"))
    be_size = float(summary.get("median_break_even_fixed_over_iter_size", float("nan")))
    be_depth = float(summary.get("median_break_even_fixed_over_iter_depth", float("nan")))
    be_ok = math.isfinite(be_size) and math.isfinite(be_depth) and 0.0 < be_size < 1.0 and 0.0 < be_depth < 1.0
    checks.append(Check("compiler-native-aa:break-even", "PASS" if be_ok else "FAIL", f"size={be_size:.6f}, depth={be_depth:.6f}"))
    expected = int(manifest.get("suite", {}).get("compiler_native_aa_crosscheck_rows", 9))
    checks.append(Check("compiler-native-aa:manifest-count", "PASS" if expected == len(rows) else "FAIL", f"manifest={expected}, csv={len(rows)}"))
    return checks

def check_qaoa_threshold_objective_evidence(root: Path, manifest: dict) -> list[Check]:
    import csv as _csv
    out: list[Check] = []
    paths = {
        "runs": root / "results" / "qaoa_threshold_training_budget_runs.csv",
        "paired": root / "results" / "qaoa_threshold_training_budget_paired.csv",
        "instance": root / "results" / "qaoa_threshold_training_budget_instance_summary.csv",
        "inference": root / "results" / "qaoa_threshold_training_budget_inference.csv",
    }
    if any(not p.exists() for p in paths.values()):
        missing = [k for k,p in paths.items() if not p.exists()]
        return [Check("qaoa-threshold-objective:files", "FAIL", f"missing={missing}")]
    try:
        with paths["paired"].open("r", encoding="utf-8", newline="") as fh:
            paired = list(_csv.DictReader(fh))
        with paths["inference"].open("r", encoding="utf-8", newline="") as fh:
            inf = list(_csv.DictReader(fh))
        exact_pair = len(paired) == 270 and all(str(r.get("initialization_identical", "")).lower() in {"true", "1"} for r in paired)
        out.append(Check("qaoa-threshold-objective:pairing", "PASS" if exact_pair else "FAIL", f"paired_rows={len(paired)}"))
        inf_ok = len(inf) == 3 and all(float(r["median_delta_p_target"]) > 0 and float(r["bootstrap_ci_lo"]) > 0 and float(r["p_holm"]) < 0.05 for r in inf)
        out.append(Check("qaoa-threshold-objective:inference", "PASS" if inf_ok else "FAIL", f"rows={[(r.get('p'), r.get('median_delta_p_target'), r.get('p_holm')) for r in inf]}"))
        tradeoff = len(inf) == 3 and all(float(r["median_delta_approx_ratio"]) < 0 for r in inf)
        out.append(Check("qaoa-threshold-objective:tradeoff", "PASS" if tradeoff else "FAIL", f"delta_AR={[r.get('median_delta_approx_ratio') for r in inf]}"))
    except Exception as exc:
        out.append(Check("qaoa-threshold-objective:parse", "FAIL", f"unreadable: {exc}"))
    return out

def check_duplicate_canonical_files(root: Path) -> list[Check]:
    out: list[Check] = []
    expected = {
        "main.tex": root / "manuscript" / "main.tex",
        "references.bib": root / "manuscript" / "references.bib",
        "CLAIMS_REGISTER.md": root / "manuscript" / "CLAIMS_REGISTER.md",
        "run_manifest.json": root / "results" / "run_manifest.json",
    }
    for name, canonical in expected.items():
        matches = [p for p in root.rglob(name) if p.is_file()]
        extras = [p for p in matches if p.resolve() != canonical.resolve()]
        out.append(Check(f"duplicate:{name}", "PASS" if not extras else "FAIL", "none" if not extras else ", ".join(str(p.relative_to(root)) for p in extras)))
    return out


def run_preflight(root: Path, *, runtime: bool = True, artifacts: bool = True) -> dict:
    manifest_path = root / "results" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    checks: list[Check] = []
    checks.extend(check_required_structure(root))
    if runtime:
        checks.extend(check_runtime_lock(root))
    if manifest:
        checks.extend(check_claim_fences(root, manifest))
        checks.extend(check_compiler_evidence(root, manifest))
        checks.extend(check_compiler_native_aa_evidence(root, manifest))
        checks.extend(check_qaoa_threshold_objective_evidence(root, manifest))
    else:
        checks.append(Check("run-manifest", "FAIL", "results/run_manifest.json missing or unreadable"))
    if (root / "manuscript" / "main.tex").exists():
        checks.extend(check_tex_balance((root / "manuscript" / "main.tex").read_text(encoding="utf-8")))
    checks.extend(check_duplicate_canonical_files(root))
    if artifacts and manifest:
        if not manifest.get("manuscript_dependency_sha256"):
            checks.append(Check("manifest:manuscript-dependencies", "FAIL", "missing final manuscript dependency hashes; run src/finalize_manifest.py"))
        checks.extend(check_manifest_hashes(root, manifest))
        checks.extend(check_row_counts(root, manifest))

    failures = sum(c.status == "FAIL" for c in checks)
    warnings = sum(c.status == "WARN" for c in checks)
    report = {
        "status": "PASS" if failures == 0 else "FAIL",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root.resolve()),
        "runtime_checked": runtime,
        "artifacts_checked": artifacts,
        "summary": {"pass": sum(c.status == "PASS" for c in checks), "warn": warnings, "fail": failures},
        "checks": [asdict(c) for c in checks],
    }
    return report


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Canonical FGCS reproducibility/submission preflight")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--no-runtime", action="store_true", help="skip installed-version checks")
    parser.add_argument("--source-only", action="store_true", help="skip result-table hashes and row counts")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = run_preflight(args.root, runtime=not args.no_runtime, artifacts=not args.source_only)
    text = json.dumps(report, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
