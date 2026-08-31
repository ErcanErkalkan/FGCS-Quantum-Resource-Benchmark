from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
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
    candidates = [p for p in (root / "data" / name, root / "results" / name, root / "figures" / name) if p.exists()]
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
        "qaoa_runs.csv": qaoa.get("total_runs"),
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
        "oracle_resource_model.csv": suite.get("oracle_resource_model_rows"),
        "coupled_oracle_depth_sensitivity.csv": suite.get("coupled_oracle_depth_rows"),
        "fixed_overhead_sensitivity.csv": suite.get("fixed_overhead_sensitivity_rows"),
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
        "tests/test_core.py",
        "tests/test_preflight.py",
        "tests/test_finalize_manifest.py",
        "manuscript/main.tex",
        "manuscript/references.bib",
        "manuscript/CLAIMS_REGISTER.md",
        "results/run_manifest.json",
        "reproducibility/ENVIRONMENT_LOCK.md",
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
    if manifest.get("compiler_claims") is not False:
        out.append(Check("manifest:compiler_claims", "FAIL", f"value={manifest.get('compiler_claims')}"))
    else:
        out.append(Check("manifest:compiler_claims", "PASS", "false"))

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
        "fixed-density-random-design": "fixed-edge-count/fixed-density random simple-graph design",
        "credit-statement": "CRediT authorship contribution statement",
        "ai-version-log": "GPT-5.6 Sol",
        "ai-history-limit": "not consistently logged at the exact model-version level",
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
