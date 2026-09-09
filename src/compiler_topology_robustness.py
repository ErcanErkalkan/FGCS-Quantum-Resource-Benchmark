from __future__ import annotations

import argparse
import csv
import json
import platform
from collections import defaultdict
from pathlib import Path

import numpy as np
import qiskit
from qiskit.transpiler import CouplingMap

from compiler_validation_qiskit import (
    BASIS_GATES,
    OPTIMIZATION_LEVEL,
    SEED_TRANSPILER,
    compile_metrics,
    exact_suite,
    line_coupling,
    operational_threshold,
    qaoa_circuit,
    semantic_oracle_check,
    threshold_oracle_circuit,
)


def bidirectional(edges: list[tuple[int, int]]) -> CouplingMap:
    directed: list[list[int]] = []
    seen: set[tuple[int, int]] = set()
    for a, b in edges:
        if a == b:
            continue
        for u, v in ((a, b), (b, a)):
            if (u, v) not in seen:
                directed.append([u, v])
                seen.add((u, v))
    return CouplingMap(directed)


def ring_coupling(n: int) -> CouplingMap:
    edges = [(i, i + 1) for i in range(n - 1)]
    if n > 2:
        edges.append((n - 1, 0))
    return bidirectional(edges)


def ladder_coupling(n: int) -> CouplingMap:
    """Connected two-row ladder-like synthetic topology for arbitrary n >= 2."""
    split = (n + 1) // 2
    top = list(range(split))
    bottom = list(range(split, n))
    edges: list[tuple[int, int]] = []
    edges.extend((a, b) for a, b in zip(top, top[1:]))
    edges.extend((a, b) for a, b in zip(bottom, bottom[1:]))
    edges.extend((a, b) for a, b in zip(top, bottom))
    return bidirectional(edges)


def topology_map(name: str, n: int) -> CouplingMap:
    if name == "line":
        return line_coupling(n)
    if name == "ring":
        return ring_coupling(n)
    if name == "ladder":
        return ladder_coupling(n)
    raise ValueError(name)


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_baseline(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def baseline_guard(rows: list[dict], baseline_path: Path) -> dict:
    baseline = load_baseline(baseline_path)
    base_index: dict[tuple, dict[str, str]] = {}
    for r in baseline:
        profile = r["compiler_profile"]
        if profile == "qaoa_line_routed":
            key = ("qaoa", r["instance_id"], int(r["p"]))
        elif profile == "oracle_line_routed_sparse":
            key = ("threshold_oracle", r["instance_id"], 0)
        else:
            continue
        base_index[key] = r

    new_line: dict[tuple, dict] = {}
    for r in rows:
        if r["topology"] != "line":
            continue
        key = (r["circuit_family"], r["instance_id"], int(r.get("p") or 0))
        new_line[key] = r

    fields = [
        "logical_qubits",
        "logical_depth",
        "logical_size",
        "compiled_qubits",
        "compiled_depth",
        "compiled_size",
        "compiled_cx",
        "compiled_rz",
        "compiled_sx",
        "compiled_x",
    ]
    mismatches: list[dict] = []
    missing = sorted(set(base_index) - set(new_line))
    extra = sorted(set(new_line) - set(base_index))
    for key in sorted(set(base_index) & set(new_line)):
        old = base_index[key]
        new = new_line[key]
        for field in fields:
            if int(float(old[field])) != int(new[field]):
                mismatches.append(
                    {
                        "key": list(key),
                        "field": field,
                        "baseline": int(float(old[field])),
                        "rerun": int(new[field]),
                    }
                )
    return {
        "baseline_rows_expected": len(base_index),
        "line_rows_rerun": len(new_line),
        "missing_keys": [list(x) for x in missing],
        "extra_keys": [list(x) for x in extra],
        "metric_mismatches": mismatches,
        "passed": not missing and not extra and not mismatches,
    }


def matched_ratios(rows: list[dict], family: str) -> list[dict]:
    grouped: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        if r["circuit_family"] != family:
            continue
        key = (r["instance_id"], int(r.get("p") or 0))
        grouped[key][r["topology"]] = r

    out: list[dict] = []
    for key, by_top in sorted(grouped.items()):
        line = by_top["line"]
        for top in ("ring", "ladder"):
            r = by_top[top]
            out.append(
                {
                    "circuit_family": family,
                    "instance_id": key[0],
                    "p": key[1] if family == "qaoa" else "",
                    "topology": top,
                    "depth_ratio_to_line": float(r["compiled_depth"]) / float(line["compiled_depth"]),
                    "cx_ratio_to_line": float(r["compiled_cx"]) / float(line["compiled_cx"]),
                    "depth_delta_to_line": int(r["compiled_depth"]) - int(line["compiled_depth"]),
                    "cx_delta_to_line": int(r["compiled_cx"]) - int(line["compiled_cx"]),
                }
            )
    return out


def summarize_ratios(ratios: list[dict]) -> dict:
    result: dict[str, dict] = {}
    for top in ("ring", "ladder"):
        subset = [r for r in ratios if r["topology"] == top]
        depth = np.asarray([r["depth_ratio_to_line"] for r in subset], dtype=float)
        cx = np.asarray([r["cx_ratio_to_line"] for r in subset], dtype=float)
        result[top] = {
            "n": len(subset),
            "median_depth_ratio_to_line": float(np.median(depth)),
            "iqr_depth_ratio_to_line": [float(np.quantile(depth, 0.25)), float(np.quantile(depth, 0.75))],
            "min_depth_ratio_to_line": float(np.min(depth)),
            "max_depth_ratio_to_line": float(np.max(depth)),
            "median_cx_ratio_to_line": float(np.median(cx)),
            "iqr_cx_ratio_to_line": [float(np.quantile(cx, 0.25)), float(np.quantile(cx, 0.75))],
            "min_cx_ratio_to_line": float(np.min(cx)),
            "max_cx_ratio_to_line": float(np.max(cx)),
            "fraction_depth_not_worse_than_line": float(np.mean(depth <= 1.0)),
            "fraction_cx_not_worse_than_line": float(np.mean(cx <= 1.0)),
        }
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="compiler_topology_robustness_artifact")
    ap.add_argument("--baseline", default="results/compiler_validation_qiskit.csv")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    semantic = semantic_oracle_check()
    if not semantic["passed"]:
        raise RuntimeError(f"semantic threshold-oracle check failed: {semantic['failures']}")

    suite = exact_suite()
    rows: list[dict] = []

    # Matched QAOA audit: all 18 primary graphs x p=1,2,3 x three synthetic topologies.
    for inst in suite:
        for p in (1, 2, 3):
            qc = qaoa_circuit(inst, p)
            for top in ("line", "ring", "ladder"):
                metrics = compile_metrics(
                    qc,
                    profile=f"qaoa_{top}_routed",
                    coupling_map=topology_map(top, qc.num_qubits),
                )
                rows.append(
                    {
                        "circuit_family": "qaoa",
                        "instance_id": inst.instance_id,
                        "n": inst.n,
                        "density": inst.density,
                        "graph_seed": inst.seed,
                        "n_edges": len(inst.edges),
                        "p": p,
                        "operational_level": "",
                        "threshold": "",
                        "topology": top,
                        **metrics,
                    }
                )

    # Matched sparse-oracle routing audit: one sparse seed-17 representative per n.
    for n in (8, 10, 12):
        inst = next(i for i in suite if i.n == n and abs(i.density - 0.25) < 1e-12 and i.seed == 17)
        tau = operational_threshold(inst, 0.40)
        qc = threshold_oracle_circuit(inst, tau)
        for top in ("line", "ring", "ladder"):
            metrics = compile_metrics(
                qc,
                profile=f"oracle_{top}_routed_sparse",
                coupling_map=topology_map(top, qc.num_qubits),
            )
            rows.append(
                {
                    "circuit_family": "threshold_oracle",
                    "instance_id": inst.instance_id,
                    "n": inst.n,
                    "density": inst.density,
                    "graph_seed": inst.seed,
                    "n_edges": len(inst.edges),
                    "p": "",
                    "operational_level": 0.40,
                    "threshold": tau,
                    "topology": top,
                    **metrics,
                }
            )

    rows_path = out / "compiler_topology_robustness.csv"
    write_csv(rows_path, rows)

    guard = baseline_guard(rows, Path(args.baseline))
    if not guard["passed"]:
        (out / "baseline_guard_failure.json").write_text(
            json.dumps(guard, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        raise RuntimeError("line-topology rerun does not reproduce the locked baseline")

    qaoa_ratios = matched_ratios(rows, "qaoa")
    oracle_ratios = matched_ratios(rows, "threshold_oracle")
    write_csv(out / "compiler_topology_qaoa_matched_ratios.csv", qaoa_ratios)
    write_csv(out / "compiler_topology_oracle_matched_ratios.csv", oracle_ratios)

    qaoa_by_p = {}
    for p in (1, 2, 3):
        qaoa_by_p[str(p)] = summarize_ratios([r for r in qaoa_ratios if int(r["p"]) == p])

    summary = {
        "evidence_label": "compiler-level synthetic-topology robustness; not physical hardware execution or timing evidence",
        "qiskit_version": qiskit.__version__,
        "python_version": platform.python_version(),
        "basis_gates": BASIS_GATES,
        "seed_transpiler": SEED_TRANSPILER,
        "optimization_level": OPTIMIZATION_LEVEL,
        "topologies": {
            "line": "bidirectional path",
            "ring": "bidirectional cycle",
            "ladder": "bidirectional two-row ladder-like graph",
        },
        "semantic_oracle_check": semantic,
        "baseline_guard": guard,
        "row_count": len(rows),
        "qaoa_rows": sum(r["circuit_family"] == "qaoa" for r in rows),
        "oracle_rows": sum(r["circuit_family"] == "threshold_oracle" for r in rows),
        "qaoa_matched_ratio_summary": summarize_ratios(qaoa_ratios),
        "qaoa_matched_ratio_summary_by_p": qaoa_by_p,
        "oracle_sparse_matched_ratio_summary": summarize_ratios(oracle_ratios),
        "claim_boundary": [
            "Topology changes are synthetic compiler-routing stress tests only.",
            "No backend calibration, duration, fidelity, queue-time, energy, or hardware-speedup claim is made.",
            "The line rerun must reproduce the pre-existing Qiskit 2.4.2 locked baseline before alternate-topology results are accepted.",
        ],
    }
    (out / "compiler_topology_robustness_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
