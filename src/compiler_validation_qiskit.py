from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import DraperQFTAdder, IntegerComparator
from qiskit.quantum_info import Statevector
from qiskit.transpiler import CouplingMap

RANDOM_GRAPH_STREAM_VERSION = 2
BASIS_GATES = ["rz", "sx", "x", "cx"]
SEED_TRANSPILER = 20260901
OPTIMIZATION_LEVEL = 1
QAOA_GAMMAS = (0.731, 0.437, 0.219)
QAOA_BETAS = (0.413, 0.271, 0.157)


@dataclass(frozen=True)
class Instance:
    instance_id: str
    n: int
    density: float
    seed: int
    edges: tuple[tuple[int, int, int], ...]
    cut_values: np.ndarray
    optimum: int


def build_instance(n: int, density: float, seed: int) -> Instance:
    density_code = int(round(100 * density))
    stream = np.random.SeedSequence([RANDOM_GRAPH_STREAM_VERSION, seed, n, density_code])
    rng = np.random.default_rng(stream)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    rng.shuffle(pairs)
    m = max(1, int(round(density * len(pairs))))
    chosen = pairs[:m]
    edges = tuple((i, j, int(rng.integers(1, 10))) for i, j in chosen)
    states = np.arange(1 << n, dtype=np.uint64)
    vals = np.zeros(1 << n, dtype=float)
    for i, j, w in edges:
        vals += w * (((states >> np.uint64(i)) & 1) ^ ((states >> np.uint64(j)) & 1))
    iid = f"n{n}_d{int(round(100*density)):02d}_s{seed}"
    return Instance(iid, n, density, seed, edges, vals, int(vals.max()))


def exact_suite() -> list[Instance]:
    return [build_instance(n, d, s) for n in (8, 10, 12) for d in (0.25, 0.50, 0.75) for s in (17, 42)]


def random_cut_expectation(inst: Instance) -> float:
    return 0.5 * float(sum(w for _, _, w in inst.edges))


def spectral_upper_bound(inst: Instance) -> float:
    lap = np.zeros((inst.n, inst.n), dtype=float)
    total = 0.0
    for i, j, w in inst.edges:
        total += w
        lap[i, i] += w
        lap[j, j] += w
        lap[i, j] -= w
        lap[j, i] -= w
    return float(min(total, inst.n * float(np.linalg.eigvalsh(lap)[-1]) / 4.0))


def operational_threshold(inst: Instance, level: float = 0.40) -> int:
    lower = random_cut_expectation(inst)
    upper = spectral_upper_bound(inst)
    return int(math.ceil(lower + level * (upper - lower) - 1e-12))


def line_coupling(n: int) -> CouplingMap:
    edges = []
    for i in range(n - 1):
        edges.extend(([i, i + 1], [i + 1, i]))
    return CouplingMap(edges)


def qaoa_circuit(inst: Instance, p: int) -> QuantumCircuit:
    qc = QuantumCircuit(inst.n, name=f"qaoa_{inst.instance_id}_p{p}")
    qc.h(range(inst.n))
    for layer in range(p):
        gamma = QAOA_GAMMAS[layer]
        beta = QAOA_BETAS[layer]
        for i, j, w in inst.edges:
            qc.cx(i, j)
            qc.rz(gamma * float(w), j)
            qc.cx(i, j)
        for q in range(inst.n):
            qc.rx(2.0 * beta, q)
    return qc


def threshold_oracle_circuit(inst: Instance, threshold: int) -> QuantumCircuit:
    total_weight = int(sum(w for _, _, w in inst.edges))
    b = max(1, int(math.ceil(math.log2(total_weight + 1))))
    adder = DraperQFTAdder(b, kind="fixed").to_gate(label=f"add_{b}")
    cadd = adder.control(1)
    cmp_gate = IntegerComparator(b, threshold, geq=True).to_gate(label=f"ge_{threshold}")
    cmp_anc_count = cmp_gate.num_qubits - b - 1
    if cmp_anc_count < 0:
        raise RuntimeError("unexpected comparator qubit layout")

    data = list(range(inst.n))
    parity = inst.n
    const = list(range(parity + 1, parity + 1 + b))
    accum = list(range(const[-1] + 1, const[-1] + 1 + b))
    flag = accum[-1] + 1
    cmp_anc = list(range(flag + 1, flag + 1 + cmp_anc_count))
    qc = QuantumCircuit(flag + 1 + cmp_anc_count, name=f"oracle_{inst.instance_id}_tau{threshold}")

    def load_constant(weight: int) -> None:
        for bit in range(b):
            if (weight >> bit) & 1:
                qc.x(const[bit])

    def edge_add(i: int, j: int, w: int, inverse: bool = False) -> None:
        qc.cx(data[i], parity)
        qc.cx(data[j], parity)
        load_constant(w)
        qc.append(cadd.inverse() if inverse else cadd, [parity] + const + accum)
        load_constant(w)
        qc.cx(data[j], parity)
        qc.cx(data[i], parity)

    for i, j, w in inst.edges:
        edge_add(i, j, w)

    cmp_qargs = accum + [flag] + cmp_anc
    qc.append(cmp_gate, cmp_qargs)
    qc.z(flag)
    qc.append(cmp_gate.inverse(), cmp_qargs)

    for i, j, w in reversed(inst.edges):
        edge_add(i, j, w, inverse=True)
    return qc


def cut_value(x: int, edges: tuple[tuple[int, int, int], ...]) -> int:
    return int(sum(w for i, j, w in edges if ((x >> i) & 1) != ((x >> j) & 1)))


def semantic_oracle_check() -> dict:
    edges = ((0, 1, 2), (1, 2, 3), (0, 2, 4))
    n = 3
    vals = np.asarray([cut_value(x, edges) for x in range(1 << n)], dtype=float)
    inst = Instance("semantic_triangle", n, 1.0, 0, edges, vals, int(vals.max()))
    threshold = 5
    oracle = threshold_oracle_circuit(inst, threshold)
    failures = []
    for x in range(1 << n):
        prep = QuantumCircuit(oracle.num_qubits)
        for q in range(n):
            if (x >> q) & 1:
                prep.x(q)
        prep.compose(oracle, inplace=True)
        sv = Statevector.from_instruction(prep)
        amp = complex(sv.data[x])
        leakage = float(1.0 - abs(amp) ** 2)
        expected_phase = -1.0 if cut_value(x, edges) >= threshold else 1.0
        if leakage > 1e-8 or abs(amp - expected_phase) >= 1e-8:
            failures.append({"x": x, "cut": cut_value(x, edges), "amp_real": amp.real, "amp_imag": amp.imag, "leakage": leakage, "expected_phase": expected_phase})
    return {"passed": not failures, "tested_basis_states": 1 << n, "threshold": threshold, "failures": failures, "oracle_qubits": oracle.num_qubits}


def compile_metrics(circuit: QuantumCircuit, profile: str, coupling_map: CouplingMap | None) -> dict:
    t0 = time.perf_counter()
    compiled = transpile(circuit, basis_gates=BASIS_GATES, coupling_map=coupling_map, optimization_level=OPTIMIZATION_LEVEL, seed_transpiler=SEED_TRANSPILER)
    elapsed = time.perf_counter() - t0
    ops = compiled.count_ops()
    return {
        "compiler_profile": profile,
        "logical_qubits": circuit.num_qubits,
        "logical_depth": circuit.depth(),
        "logical_size": circuit.size(),
        "compiled_qubits": compiled.num_qubits,
        "compiled_depth": compiled.depth(),
        "compiled_size": compiled.size(),
        "compiled_cx": int(ops.get("cx", 0)),
        "compiled_rz": int(ops.get("rz", 0)),
        "compiled_sx": int(ops.get("sx", 0)),
        "compiled_x": int(ops.get("x", 0)),
        "compile_time_s": elapsed,
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = sorted({k for row in rows for k in row})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="compiler_validation_artifact")
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    semantic = semantic_oracle_check()
    if not semantic["passed"]:
        raise RuntimeError(f"semantic threshold-oracle check failed: {semantic['failures']}")

    suite = exact_suite()
    rows = []
    for inst in suite:
        for p in (1, 2, 3):
            metrics = compile_metrics(qaoa_circuit(inst, p), "qaoa_line_routed", line_coupling(inst.n))
            rows.append({"circuit_family": "qaoa", "instance_id": inst.instance_id, "n": inst.n, "density": inst.density, "graph_seed": inst.seed, "n_edges": len(inst.edges), "p": p, "operational_level": "", "threshold": "", **metrics})

    oracle_reps = [inst for inst in suite if inst.seed == 17]
    for inst in oracle_reps:
        tau = operational_threshold(inst, 0.40)
        qc = threshold_oracle_circuit(inst, tau)
        metrics = compile_metrics(qc, "oracle_basis_decomposition", None)
        rows.append({"circuit_family": "threshold_oracle", "instance_id": inst.instance_id, "n": inst.n, "density": inst.density, "graph_seed": inst.seed, "n_edges": len(inst.edges), "p": "", "operational_level": 0.40, "threshold": tau, **metrics})

    for n in (8, 10, 12):
        inst = next(x for x in suite if x.n == n and abs(x.density - 0.25) < 1e-12 and x.seed == 17)
        tau = operational_threshold(inst, 0.40)
        qc = threshold_oracle_circuit(inst, tau)
        metrics = compile_metrics(qc, "oracle_line_routed_sparse", line_coupling(qc.num_qubits))
        rows.append({"circuit_family": "threshold_oracle", "instance_id": inst.instance_id, "n": inst.n, "density": inst.density, "graph_seed": inst.seed, "n_edges": len(inst.edges), "p": "", "operational_level": 0.40, "threshold": tau, **metrics})

    csv_path = out / "compiler_validation_qiskit.csv"
    write_csv(csv_path, rows)
    qaoa_rows = [r for r in rows if r["compiler_profile"] == "qaoa_line_routed"]
    oracle_basis = [r for r in rows if r["compiler_profile"] == "oracle_basis_decomposition"]
    oracle_routed = [r for r in rows if r["compiler_profile"] == "oracle_line_routed_sparse"]
    summary = {
        "evidence_label": "compiler-locked Qiskit transpilation evidence; synthetic topology, not physical hardware execution",
        "qiskit_version": qiskit.__version__,
        "python_version": platform.python_version(),
        "basis_gates": BASIS_GATES,
        "seed_transpiler": SEED_TRANSPILER,
        "optimization_level": OPTIMIZATION_LEVEL,
        "semantic_oracle_check": semantic,
        "row_count": len(rows),
        "qaoa_routed_rows": len(qaoa_rows),
        "oracle_basis_rows": len(oracle_basis),
        "oracle_sparse_routed_rows": len(oracle_routed),
        "qaoa_median_compiled_depth_by_p": {str(p): float(np.median([r["compiled_depth"] for r in qaoa_rows if int(r["p"]) == p])) for p in (1, 2, 3)},
        "qaoa_median_compiled_cx_by_p": {str(p): float(np.median([r["compiled_cx"] for r in qaoa_rows if int(r["p"]) == p])) for p in (1, 2, 3)},
        "oracle_basis_median_compiled_depth": float(np.median([r["compiled_depth"] for r in oracle_basis])),
        "oracle_basis_median_compiled_cx": float(np.median([r["compiled_cx"] for r in oracle_basis])),
        "oracle_sparse_routed_depths": {r["instance_id"]: int(r["compiled_depth"]) for r in oracle_routed},
        "oracle_sparse_routed_cx": {r["instance_id"]: int(r["compiled_cx"]) for r in oracle_routed},
    }
    summary_path = out / "compiler_validation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    env = {
        "qiskit_version": qiskit.__version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "basis_gates": BASIS_GATES,
        "seed_transpiler": SEED_TRANSPILER,
        "optimization_level": OPTIMIZATION_LEVEL,
        "command": "python src/compiler_validation_qiskit.py --out-dir compiler_validation_artifact",
    }
    env_path = out / "compiler_environment.json"
    env_path.write_text(json.dumps(env, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksums = {csv_path.name: sha256(csv_path), summary_path.name: sha256(summary_path), env_path.name: sha256(env_path)}
    (out / "SHA256SUMS.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
