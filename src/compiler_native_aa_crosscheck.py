from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile

from compiler_validation_qiskit import (
    BASIS_GATES,
    OPTIMIZATION_LEVEL,
    SEED_TRANSPILER,
    exact_suite,
    operational_threshold,
    threshold_oracle_circuit,
)

OPERATIONAL_LEVEL = 0.40
K_MAX = 64


def grover_probability(rho: float, k: int) -> float:
    theta = math.asin(math.sqrt(rho))
    return math.sin((2 * k + 1) * theta) ** 2


def basis_metrics(circuit: QuantumCircuit) -> dict:
    compiled = transpile(
        circuit,
        basis_gates=BASIS_GATES,
        coupling_map=None,
        optimization_level=OPTIMIZATION_LEVEL,
        seed_transpiler=SEED_TRANSPILER,
    )
    ops = compiled.count_ops()
    one_q = int(ops.get("rz", 0) + ops.get("sx", 0) + ops.get("x", 0))
    cx = int(ops.get("cx", 0))
    return {
        "compiled_qubits": int(compiled.num_qubits),
        "compiled_depth": int(compiled.depth()),
        "compiled_size": int(compiled.size()),
        "compiled_cx": cx,
        "compiled_1q": one_q,
    }


def preparation_circuit(total_qubits: int, n_data: int) -> QuantumCircuit:
    qc = QuantumCircuit(total_qubits, name=f"prep_n{n_data}")
    qc.h(range(n_data))
    return qc


def diffusion_circuit(total_qubits: int, n_data: int) -> QuantumCircuit:
    qc = QuantumCircuit(total_qubits, name=f"diff_n{n_data}")
    data = list(range(n_data))
    qc.h(data)
    qc.x(data)
    if n_data == 1:
        qc.z(data[0])
    else:
        target = data[-1]
        qc.h(target)
        qc.mcx(data[:-1], target)
        qc.h(target)
    qc.x(data)
    qc.h(data)
    return qc


def select_k(rho: float, prep_cost: float, iter_cost: float, *, k_max: int = K_MAX) -> dict:
    rows = []
    for k in range(k_max + 1):
        p = grover_probability(rho, k)
        cost = prep_cost + k * iter_cost
        score = p / cost
        rows.append((k, p, cost, score))
    best = max(rows, key=lambda t: (t[3], -t[0]))
    return {
        "k": int(best[0]),
        "p": float(best[1]),
        "cost": float(best[2]),
        "score": float(best[3]),
    }


def break_even_fixed_ratio(rho: float, prep_cost: float, iter_cost: float, *, k_max: int = K_MAX) -> float | None:
    candidates = []
    for k in range(1, k_max + 1):
        p = grover_probability(rho, k)
        if p <= rho + 1e-15:
            continue
        c = rho * k * iter_cost / (p - rho) - prep_cost
        candidates.append(max(0.0, c / iter_cost))
    return float(min(candidates)) if candidates else None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="compiler_native_aa_artifact")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    reps = [inst for inst in exact_suite() if inst.seed == 17]
    rows: list[dict] = []

    cache: dict[tuple[int, int], tuple[dict, dict]] = {}
    for inst in reps:
        tau = operational_threshold(inst, OPERATIONAL_LEVEL)
        marked = int(np.count_nonzero(inst.cut_values >= tau))
        rho = marked / float(1 << inst.n)
        if not (0.0 < rho <= 1.0):
            raise RuntimeError(f"invalid marked fraction for {inst.instance_id}: {rho}")

        oracle = threshold_oracle_circuit(inst, tau)
        oracle_m = basis_metrics(oracle)
        cache_key = (oracle.num_qubits, inst.n)
        if cache_key not in cache:
            prep_m = basis_metrics(preparation_circuit(oracle.num_qubits, inst.n))
            diff_m = basis_metrics(diffusion_circuit(oracle.num_qubits, inst.n))
            cache[cache_key] = prep_m, diff_m
        prep_m, diff_m = cache[cache_key]

        size_iter = float(oracle_m["compiled_size"] + diff_m["compiled_size"])
        depth_iter = float(oracle_m["compiled_depth"] + diff_m["compiled_depth"])
        size_sel = select_k(rho, float(prep_m["compiled_size"]), size_iter)
        depth_sel = select_k(rho, float(prep_m["compiled_depth"]), depth_iter)

        rows.append({
            "instance_id": inst.instance_id,
            "n": inst.n,
            "density": inst.density,
            "graph_seed": inst.seed,
            "n_edges": len(inst.edges),
            "operational_level": OPERATIONAL_LEVEL,
            "threshold": tau,
            "marked_states": marked,
            "state_count": 1 << inst.n,
            "rho": rho,
            "oracle_qubits": oracle.num_qubits,
            "prep_compiled_size": prep_m["compiled_size"],
            "prep_compiled_depth": prep_m["compiled_depth"],
            "oracle_compiled_size": oracle_m["compiled_size"],
            "oracle_compiled_depth": oracle_m["compiled_depth"],
            "oracle_compiled_cx": oracle_m["compiled_cx"],
            "oracle_compiled_1q": oracle_m["compiled_1q"],
            "diffusion_compiled_size": diff_m["compiled_size"],
            "diffusion_compiled_depth": diff_m["compiled_depth"],
            "diffusion_compiled_cx": diff_m["compiled_cx"],
            "diffusion_compiled_1q": diff_m["compiled_1q"],
            "iteration_compiled_size": size_iter,
            "iteration_compiled_depth": depth_iter,
            "k_star_compiled_size": size_sel["k"],
            "k_star_compiled_depth": depth_sel["k"],
            "score_compiled_size": size_sel["score"],
            "score_compiled_depth": depth_sel["score"],
            "break_even_fixed_over_iter_size": break_even_fixed_ratio(rho, float(prep_m["compiled_size"]), size_iter),
            "break_even_fixed_over_iter_depth": break_even_fixed_ratio(rho, float(prep_m["compiled_depth"]), depth_iter),
        })

    csv_path = out / "compiler_native_aa_crosscheck.csv"
    write_csv(csv_path, rows)

    summary = {
        "evidence_label": "compiler-native amplitude-amplification cross-check in locked Qiskit basis; no physical hardware claim",
        "qiskit_version": qiskit.__version__,
        "python_version": platform.python_version(),
        "basis_gates": BASIS_GATES,
        "seed_transpiler": SEED_TRANSPILER,
        "optimization_level": OPTIMIZATION_LEVEL,
        "operational_level": OPERATIONAL_LEVEL,
        "k_max": K_MAX,
        "row_count": len(rows),
        "all_k0_compiled_size": all(int(r["k_star_compiled_size"]) == 0 for r in rows),
        "all_k0_compiled_depth": all(int(r["k_star_compiled_depth"]) == 0 for r in rows),
        "median_break_even_fixed_over_iter_size": float(np.median([r["break_even_fixed_over_iter_size"] for r in rows])),
        "median_break_even_fixed_over_iter_depth": float(np.median([r["break_even_fixed_over_iter_depth"] for r in rows])),
        "median_iteration_compiled_size": float(np.median([r["iteration_compiled_size"] for r in rows])),
        "median_iteration_compiled_depth": float(np.median([r["iteration_compiled_depth"] for r in rows])),
        "median_oracle_to_diffusion_size_ratio": float(np.median([r["oracle_compiled_size"] / max(1.0, r["diffusion_compiled_size"]) for r in rows])),
        "median_oracle_to_diffusion_depth_ratio": float(np.median([r["oracle_compiled_depth"] / max(1.0, r["diffusion_compiled_depth"]) for r in rows])),
    }
    summary_path = out / "compiler_native_aa_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    checksums = {csv_path.name: sha256(csv_path), summary_path.name: sha256(summary_path)}
    (out / "SHA256SUMS.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
