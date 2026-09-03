from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import json
import math
import platform
import sys
import time
from typing import Iterable

import numpy as np
from scipy.optimize import minimize
from scipy.stats import friedmanchisquare, rankdata, wilcoxon

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DATA = ROOT / "data"
RESULTS.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

# Versioned random-graph stream: density participates in the RNG stream so
# fixed-density instances sharing an external seed are reproducible but not
# nested prefixes of one shuffled edge list.
RANDOM_GRAPH_STREAM_VERSION = 2


def grover_probability(rho: float, k: int) -> float:
    """Ideal amplitude-amplification hit probability for marked fraction rho."""
    if not (0.0 < rho <= 1.0):
        raise ValueError("rho must lie in (0,1].")
    if k < 0:
        raise ValueError("k must be non-negative.")
    theta = math.asin(math.sqrt(rho))
    return math.sin((2 * k + 1) * theta) ** 2


def effective_probability(
    rho: float,
    k: int,
    eps_model: float,
    d_prep: float,
    d_iter: float,
) -> float:
    """Synthetic attenuation model; eps_model is never interpreted as a device estimate."""
    if eps_model < 0:
        raise ValueError("eps_model must be non-negative.")
    depth_model = d_prep + k * d_iter
    return math.exp(-eps_model * depth_model) * grover_probability(rho, k)


def select_k_resource_efficiency(
    rho: float,
    eps_model: float,
    d_prep: float,
    d_iter: float,
    prep_cost: float,
    oracle_cost: float,
    diffusion_cost: float,
    k_max: int,
) -> dict:
    """Exhaustively select k by normalized hit-probability per declared resource unit."""
    if min(prep_cost, oracle_cost, diffusion_cost) <= 0:
        raise ValueError("normalized costs must be positive")
    rows = []
    for k in range(k_max + 1):
        p_eff = effective_probability(rho, k, eps_model, d_prep, d_iter)
        cost = prep_cost + k * (oracle_cost + diffusion_cost)
        score = p_eff / cost
        rows.append((k, p_eff, score, cost, d_prep + k * d_iter))
    best = max(rows, key=lambda x: (x[2], -x[0]))
    return {
        "k": int(best[0]),
        "p_eff": float(best[1]),
        "score": float(best[2]),
        "normalized_cost": float(best[3]),
        "depth_model": float(best[4]),
        "rows": rows,
    }


@dataclass(frozen=True)
class MaxCutInstance:
    instance_id: str
    n: int
    n_edges: int
    density_target: float
    seed: int
    edges: tuple[tuple[int, int, int], ...]
    cut_values: np.ndarray
    optimum: int
    optimum_states: tuple[int, ...]
    family: str = "random_fixed_density"

    @property
    def state_count(self) -> int:
        return 1 << self.n

    @property
    def marked_fraction(self) -> float:
        return len(self.optimum_states) / self.state_count


def build_maxcut_instance(
    n: int,
    density_target: float,
    seed: int,
    weight_low: int = 1,
    weight_high: int = 9,
) -> MaxCutInstance:
    if not (0 < density_target <= 1):
        raise ValueError("density_target must be in (0,1]")
    density_code = int(round(100 * density_target))
    stream = np.random.SeedSequence([RANDOM_GRAPH_STREAM_VERSION, int(seed), int(n), density_code])
    rng = np.random.default_rng(stream)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    rng.shuffle(pairs)
    n_edges = max(1, int(round(density_target * len(pairs))))
    chosen = pairs[:n_edges]
    edges = tuple(
        (i, j, int(rng.integers(weight_low, weight_high + 1))) for i, j in chosen
    )
    states = np.arange(1 << n, dtype=np.uint64)
    vals = np.zeros(1 << n, dtype=float)
    for i, j, w in edges:
        vals += w * (((states >> np.uint64(i)) & 1) ^ ((states >> np.uint64(j)) & 1))
    optimum = int(vals.max())
    opt_states = tuple(int(x) for x in np.flatnonzero(vals == optimum))
    iid = f"n{n}_d{int(round(100*density_target)):02d}_s{seed}"
    return MaxCutInstance(
        instance_id=iid,
        n=n,
        n_edges=n_edges,
        density_target=float(density_target),
        seed=int(seed),
        edges=edges,
        cut_values=vals,
        optimum=optimum,
        optimum_states=opt_states,
        family="random_fixed_density",
    )


def build_exact_suite() -> list[MaxCutInstance]:
    out = []
    for n in (8, 10, 12):
        for density in (0.25, 0.50, 0.75):
            for seed in (17, 42):
                out.append(build_maxcut_instance(n, density, seed))
    return out


def graph_structure_metrics(inst: MaxCutInstance) -> dict:
    """Return exact structural diagnostics used to audit graph degeneracy.

    Connectivity and bipartiteness are graph properties only; they do not use C* to
    construct any benchmark target.  Exact optimum information is reported only as a
    retrospective difficulty/degeneracy descriptor in the exact tiers.
    """
    adjacency = [set() for _ in range(inst.n)]
    for i, j, _ in inst.edges:
        adjacency[i].add(j)
        adjacency[j].add(i)

    seen: set[int] = set()
    components = 0
    for start in range(inst.n):
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            u = stack.pop()
            for v in adjacency[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)

    colors: dict[int, int] = {}
    bipartite = True
    for start in range(inst.n):
        if start in colors:
            continue
        colors[start] = 0
        stack = [start]
        while stack:
            u = stack.pop()
            for v in adjacency[u]:
                if v not in colors:
                    colors[v] = 1 - colors[u]
                    stack.append(v)
                elif colors[v] == colors[u]:
                    bipartite = False

    isolated = sum(1 for nbrs in adjacency if not nbrs)
    cycle_rank = inst.n_edges - inst.n + components
    total_weight = int(sum(w for _, _, w in inst.edges))
    return {
        "component_count": int(components),
        "connected": bool(components == 1),
        "isolated_vertices": int(isolated),
        "bipartite": bool(bipartite),
        "cycle_rank": int(cycle_rank),
        "total_edge_weight": total_weight,
        "Cstar_over_total_weight": float(inst.optimum / total_weight) if total_weight else math.nan,
        "M_opt": int(len(inst.optimum_states)),
        "component_flip_symmetry_lower_bound": int(1 << components),
    }


def graph_diagnostics_rows(suite: Iterable[MaxCutInstance], tier: str) -> list[dict]:
    rows = []
    for inst in suite:
        rows.append({
            "tier": tier,
            "instance_id": inst.instance_id,
            "family": inst.family,
            "n": inst.n,
            "n_edges": inst.n_edges,
            "density_actual": inst.n_edges / (inst.n * (inst.n - 1) / 2),
            "seed": inst.seed,
            **graph_structure_metrics(inst),
            "rho_opt": inst.marked_fraction,
            "evidence_label": "exact structural audit; connectivity/bipartiteness are graph properties, C* descriptors are retrospective",
        })
    return rows


CONNECTED_VALIDATION_STREAM_VERSION = 1
CONNECTED_VALIDATION_NS = (10, 12, 14)
CONNECTED_VALIDATION_DENSITIES = (0.25, 0.50, 0.75)
CONNECTED_VALIDATION_SEEDS = (17, 42, 73, 101, 211)


def _topology_connected_nonbipartite(n: int, pairs: Iterable[tuple[int, int]]) -> tuple[bool, bool]:
    adjacency = [set() for _ in range(n)]
    for i, j in pairs:
        adjacency[i].add(j)
        adjacency[j].add(i)
    seen = {0}
    stack = [0]
    while stack:
        u = stack.pop()
        for v in adjacency[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    connected = len(seen) == n

    colors: dict[int, int] = {}
    bipartite = True
    for start in range(n):
        if start in colors:
            continue
        colors[start] = 0
        q = [start]
        while q:
            u = q.pop()
            for v in adjacency[u]:
                if v not in colors:
                    colors[v] = 1 - colors[u]
                    q.append(v)
                elif colors[v] == colors[u]:
                    bipartite = False
    return connected, (not bipartite)


def build_connected_validation_instance(
    n: int,
    density_target: float,
    seed: int,
    weight_low: int = 1,
    weight_high: int = 9,
    max_attempts: int = 10_000,
) -> MaxCutInstance:
    """Condition fixed-density sampling on connected, non-bipartite topology.

    This tier is a reviewer-facing structural stress test.  The original primary suite
    remains unchanged; conditioning is explicit and deterministic rather than silently
    discarding inconvenient primary instances.
    """
    if not (0 < density_target <= 1):
        raise ValueError("density_target must be in (0,1]")
    pairs_all = [(i, j) for i in range(n) for j in range(i + 1, n)]
    n_edges = max(1, int(round(density_target * len(pairs_all))))
    if n_edges < n:
        # A connected non-bipartite simple graph needs at least n edges: n-1 for
        # connectivity plus one edge to create an odd cycle somewhere.
        raise ValueError("density too low for guaranteed connected non-bipartite validation")
    density_code = int(round(100 * density_target))
    chosen = None
    accepted_attempt = None
    accepted_rng = None
    for attempt in range(max_attempts):
        stream = np.random.SeedSequence([
            CONNECTED_VALIDATION_STREAM_VERSION, int(seed), int(n), density_code, int(attempt)
        ])
        rng = np.random.default_rng(stream)
        pairs = list(pairs_all)
        rng.shuffle(pairs)
        candidate = pairs[:n_edges]
        connected, nonbipartite = _topology_connected_nonbipartite(n, candidate)
        if connected and nonbipartite:
            chosen = candidate
            accepted_attempt = attempt
            accepted_rng = rng
            break
    if chosen is None or accepted_rng is None or accepted_attempt is None:
        raise RuntimeError("unable to sample connected non-bipartite fixed-density graph")

    edges = tuple(
        (i, j, int(accepted_rng.integers(weight_low, weight_high + 1)))
        for i, j in chosen
    )
    states = np.arange(1 << n, dtype=np.uint64)
    vals = np.zeros(1 << n, dtype=float)
    for i, j, w in edges:
        vals += w * (((states >> np.uint64(i)) & 1) ^ ((states >> np.uint64(j)) & 1))
    optimum = int(vals.max())
    opt_states = tuple(int(x) for x in np.flatnonzero(vals == optimum))
    iid = f"cv_n{n}_d{density_code:02d}_s{seed}"
    inst = MaxCutInstance(
        instance_id=iid,
        n=n,
        n_edges=n_edges,
        density_target=float(density_target),
        seed=int(seed),
        edges=edges,
        cut_values=vals,
        optimum=optimum,
        optimum_states=opt_states,
        family="connected_nonbipartite_fixed_density",
    )
    metrics = graph_structure_metrics(inst)
    if not metrics["connected"] or metrics["bipartite"]:
        raise RuntimeError("connected validation constructor violated its structural contract")
    return inst


def build_connected_validation_suite() -> list[MaxCutInstance]:
    return [
        build_connected_validation_instance(n, density, seed)
        for n in CONNECTED_VALIDATION_NS
        for density in CONNECTED_VALIDATION_DENSITIES
        for seed in CONNECTED_VALIDATION_SEEDS
    ]


def connected_validation_graph_rows(suite: Iterable[MaxCutInstance]) -> list[dict]:
    rows = []
    for inst in suite:
        for i, j, w in inst.edges:
            rows.append({
                "instance_id": inst.instance_id, "family": inst.family,
                "n": inst.n, "density_target": inst.density_target, "seed": inst.seed,
                "i": i, "j": j, "w": w,
            })
    return rows


def connected_validation_ground_truth_rows(suite: Iterable[MaxCutInstance]) -> list[dict]:
    rows = []
    for inst in suite:
        rows.append({
            "instance_id": inst.instance_id, "family": inst.family,
            "n": inst.n, "n_edges": inst.n_edges, "density_target": inst.density_target,
            "seed": inst.seed, "C_star": inst.optimum, "rho_opt": inst.marked_fraction,
            **graph_structure_metrics(inst),
            "evidence_label": "exact connected non-bipartite validation tier; structural stress test, not population inference",
        })
    return rows


def connected_validation_operational_threshold_rows(suite: Iterable[MaxCutInstance]) -> list[dict]:
    rows = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            rows.append({
                "instance_id": inst.instance_id, "family": inst.family,
                "n": inst.n, "density_target": inst.density_target, "seed": inst.seed,
                **operational_threshold_spec(inst, level),
                "evidence_label": "exact post-construction validation on connected non-bipartite tier",
            })
    return rows


def connected_validation_coupled_oracle_rows(
    suite: Iterable[MaxCutInstance], eps_levels: tuple[float, ...] = (0.0, 0.001)
) -> list[dict]:
    rows = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            rho = float(spec["rho_tau_exact_validation"])
            if rho <= 0:
                continue
            rm = maxcut_threshold_oracle_resource_model(inst, spec["threshold"])
            for eps in eps_levels:
                out = select_k_architecture_coupled(rho, float(eps), rm, k_max=80)
                rows.append({
                    "instance_id": inst.instance_id, "family": inst.family, "n": inst.n,
                    "density_target": inst.density_target, "seed": inst.seed,
                    "operational_level": level, "threshold": spec["threshold"],
                    "rho_tau_exact_validation": rho, "eps_per_logical_depth_model": float(eps),
                    "k_star": out["k"], "p_target_eff": out["p_eff"],
                    "oracle_logical_depth_model": rm["oracle_logical_depth_model"],
                    "oracle_gate_equivalent_model": rm["oracle_gate_equivalent_model"],
                    "evidence_label": "connected non-bipartite exact validation under logical model; not compiled or hardware measured",
                })
    return rows


EXPANDED_RANDOM_SEEDS = (17, 42, 73, 101, 211)
STRUCTURED_WEIGHT_SEEDS = (17, 42)
STRUCTURED_FAMILIES = ("cycle", "cubic_circulant", "two_community")


def _build_instance_from_edge_pairs(
    n: int,
    edge_pairs: Iterable[tuple[int, int]],
    weight_seed: int,
    family: str,
    instance_id: str,
    weight_low: int = 1,
    weight_high: int = 9,
) -> MaxCutInstance:
    """Build an exact weighted Max-Cut instance from a deterministic simple graph."""
    pairs = []
    seen = set()
    for i, j in edge_pairs:
        i, j = int(i), int(j)
        if i == j:
            raise ValueError("self-loops are not allowed")
        if not (0 <= i < n and 0 <= j < n):
            raise ValueError("edge endpoint out of range")
        a, b = (i, j) if i < j else (j, i)
        if (a, b) in seen:
            continue
        seen.add((a, b))
        pairs.append((a, b))
    if not pairs:
        raise ValueError("structured graph must contain at least one edge")
    rng = np.random.default_rng(int(weight_seed))
    edges = tuple((i, j, int(rng.integers(weight_low, weight_high + 1))) for i, j in sorted(pairs))
    states = np.arange(1 << n, dtype=np.uint64)
    vals = np.zeros(1 << n, dtype=float)
    for i, j, w in edges:
        vals += w * (((states >> np.uint64(i)) & 1) ^ ((states >> np.uint64(j)) & 1))
    optimum = int(vals.max())
    opt_states = tuple(int(x) for x in np.flatnonzero(vals == optimum))
    density = len(edges) / (n * (n - 1) / 2)
    return MaxCutInstance(
        instance_id=instance_id,
        n=int(n),
        n_edges=len(edges),
        density_target=float(density),
        seed=int(weight_seed),
        edges=edges,
        cut_values=vals,
        optimum=optimum,
        optimum_states=opt_states,
        family=str(family),
    )


def build_expanded_random_suite() -> list[MaxCutInstance]:
    """K-tier random exact coverage: 45 instances using five graph seeds."""
    return [
        build_maxcut_instance(n, density, seed)
        for n in (8, 10, 12)
        for density in (0.25, 0.50, 0.75)
        for seed in EXPANDED_RANDOM_SEEDS
    ]


def _structured_edge_pairs(n: int, family: str) -> list[tuple[int, int]]:
    if n % 2 != 0:
        raise ValueError("structured suite currently requires even n")
    if family == "cycle":
        return [(i, (i + 1) % n) for i in range(n)]
    if family == "cubic_circulant":
        # Cycle plus opposite-vertex perfect matching: 3-regular for even n.
        return [(i, (i + 1) % n) for i in range(n)] + [(i, i + n // 2) for i in range(n // 2)]
    if family == "two_community":
        # Two dense equal-size communities with two cross-community bridges.
        h = n // 2
        pairs = []
        for offset in (0, h):
            nodes = range(offset, offset + h)
            pairs.extend((i, j) for i in nodes for j in nodes if i < j)
        pairs.extend([(0, h), (h - 1, n - 1)])
        return pairs
    raise ValueError(f"unsupported structured family: {family}")


def build_structured_instance(n: int, family: str, weight_seed: int) -> MaxCutInstance:
    iid = f"{family}_n{n}_s{weight_seed}"
    return _build_instance_from_edge_pairs(
        n=n,
        edge_pairs=_structured_edge_pairs(n, family),
        weight_seed=weight_seed,
        family=family,
        instance_id=iid,
    )


def build_structured_suite() -> list[MaxCutInstance]:
    """L-tier exact topology coverage: 18 structured weighted instances."""
    return [
        build_structured_instance(n, family, seed)
        for n in (8, 10, 12)
        for family in STRUCTURED_FAMILIES
        for seed in STRUCTURED_WEIGHT_SEEDS
    ]


def build_coverage_suite() -> list[MaxCutInstance]:
    """Combined K/L exact coverage; the original 18-instance suite remains unchanged."""
    return build_expanded_random_suite() + build_structured_suite()


def coverage_graph_rows(suite: Iterable[MaxCutInstance]) -> list[dict]:
    rows = []
    for inst in suite:
        for i, j, w in inst.edges:
            rows.append({
                "instance_id": inst.instance_id,
                "coverage_group": "random_seed_expansion" if inst.family == "random_fixed_density" else "structured_family",
                "family": inst.family,
                "n": inst.n,
                "seed": inst.seed,
                "i": i,
                "j": j,
                "w": w,
            })
    return rows


def coverage_ground_truth_rows(suite: Iterable[MaxCutInstance]) -> list[dict]:
    rows = []
    for inst in suite:
        rows.append({
            "instance_id": inst.instance_id,
            "coverage_group": "random_seed_expansion" if inst.family == "random_fixed_density" else "structured_family",
            "family": inst.family,
            "n": inst.n,
            "n_edges": inst.n_edges,
            "density_actual": inst.density_target,
            "seed": inst.seed,
            "C_star": inst.optimum,
            "M_opt": len(inst.optimum_states),
            "state_count": inst.state_count,
            "rho_opt": inst.marked_fraction,
            "evidence_label": "exact enumeration coverage tier; not QAOA population inference",
        })
    return rows


def coverage_operational_threshold_rows(suite: Iterable[MaxCutInstance]) -> list[dict]:
    rows = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            rows.append({
                "instance_id": inst.instance_id,
                "coverage_group": "random_seed_expansion" if inst.family == "random_fixed_density" else "structured_family",
                "family": inst.family,
                "n": inst.n,
                "seed": inst.seed,
                "operational_level": level,
                **spec,
                "evidence_label": "exact post-construction threshold validation on expanded coverage suite",
            })
    return rows


def coverage_hillclimb_rows(suite: Iterable[MaxCutInstance], starts: int = 64) -> list[dict]:
    rows = []
    for inst in suite:
        r = local_hillclimb(inst, starts=starts, seed=404)
        r.update({
            "coverage_group": "random_seed_expansion" if inst.family == "random_fixed_density" else "structured_family",
            "family": inst.family,
            "n": inst.n,
            "seed": inst.seed,
            "evidence_label": "coverage-only classical sanity diagnostic; not a matched-resource comparison",
        })
        rows.append(r)
    return rows


def coverage_coupled_oracle_rows(
    suite: Iterable[MaxCutInstance],
    eps_levels: tuple[float, ...] = (0.0, 0.001),
) -> list[dict]:
    rows = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            rho = float(spec["rho_tau_exact_validation"])
            if rho <= 0:
                continue
            rm = maxcut_threshold_oracle_resource_model(inst, spec["threshold"])
            for eps in eps_levels:
                out = select_k_architecture_coupled(rho, float(eps), rm, k_max=80)
                rows.append({
                    "instance_id": inst.instance_id,
                    "coverage_group": "random_seed_expansion" if inst.family == "random_fixed_density" else "structured_family",
                    "family": inst.family,
                    "n": inst.n,
                    "seed": inst.seed,
                    "operational_level": level,
                    "threshold": spec["threshold"],
                    "rho_tau_exact_validation": rho,
                    "eps_per_logical_depth_model": float(eps),
                    "k_star": out["k"],
                    "p_target_eff": out["p_eff"],
                    "oracle_logical_depth_model": rm["oracle_logical_depth_model"],
                    "iteration_logical_depth_model": rm["iteration_logical_depth_model"],
                    "oracle_gate_equivalent_model": rm["oracle_gate_equivalent_model"],
                    "total_logical_qubits_model": rm["total_logical_qubits_model"],
                    "evidence_label": "expanded exact coverage under architecture-informed logical model; not compiled or hardware measured",
                })
    return rows


def coverage_summary_rows(
    gt_rows: list[dict],
    threshold_rows: list[dict],
    hill_rows: list[dict],
    coupled_rows: list[dict],
) -> list[dict]:
    rows = []
    families = sorted({str(r["family"]) for r in gt_rows})
    for family in families:
        g = [r for r in gt_rows if r["family"] == family]
        h = [r for r in hill_rows if r["family"] == family]
        for level in OPERATIONAL_LEVELS:
            t = [r for r in threshold_rows if r["family"] == family and abs(float(r["operational_level"])-level) < 1e-12]
            feas = [r for r in t if bool(r["feasible_exact_validation"])]
            c0 = [r for r in coupled_rows if r["family"] == family and abs(float(r["operational_level"])-level) < 1e-12 and abs(float(r["eps_per_logical_depth_model"])) < 1e-15]
            rows.append({
                "family": family,
                "operational_level": level,
                "instances": len(g),
                "feasible_count": len(feas),
                "feasible_fraction": len(feas) / len(t) if t else math.nan,
                "median_tau_over_Cstar_feasible": float(np.median([r["realized_quality_ratio_exact_validation"] for r in feas])) if feas else math.nan,
                "median_rho_tau_feasible": float(np.median([r["rho_tau_exact_validation"] for r in feas])) if feas else math.nan,
                "median_hillclimb_ratio": float(np.median([r["median_ratio"] for r in h])) if h else math.nan,
                "architecture_zero_attenuation_nonzero_k_fraction": float(np.mean([int(r["k_star"]) > 0 for r in c0])) if c0 else math.nan,
                "evidence_label": "family-level exact coverage summary; descriptive, not population inference",
            })
    return rows



TARGET_RATIOS = (0.90, 0.95, 1.00)
OPERATIONAL_LEVELS = (0.25, 0.40, 0.55)
DENSE_OPERATIONAL_LEVELS = tuple(round(i * 0.05, 2) for i in range(21))
RHO_ESTIMATE_FACTORS = (0.50, 0.75, 0.90, 1.00, 1.10, 1.25, 1.50)


def random_cut_expectation(inst: MaxCutInstance) -> float:
    """Expected weighted cut value under independent uniform random bits."""
    return 0.5 * float(sum(w for _, _, w in inst.edges))


def spectral_maxcut_upper_bound(inst: MaxCutInstance) -> float:
    """A graph-derived Max-Cut upper bound independent of the unknown optimum.

    For spin vector s in {+1,-1}^n, C(s)=s^T L s / 4.  Therefore
    C(s) <= n*lambda_max(L)/4.  We also intersect this with the trivial
    total-edge-weight upper bound.
    """
    L = np.zeros((inst.n, inst.n), dtype=float)
    total_weight = 0.0
    for i, j, w in inst.edges:
        wf = float(w)
        total_weight += wf
        L[i, i] += wf
        L[j, j] += wf
        L[i, j] -= wf
        L[j, i] -= wf
    lam_max = float(np.linalg.eigvalsh(L)[-1])
    spectral = inst.n * lam_max / 4.0
    return float(min(total_weight, spectral))


def operational_threshold_spec(inst: MaxCutInstance, level: float) -> dict:
    """Construct a threshold without using C* or an optimum-state list.

    level interpolates between the uniform-random expected cut and a valid
    spectral/trivial graph upper bound. Exact enumeration is consulted only
    after construction to label feasibility and marked fraction in Tier I.
    """
    if not (0.0 <= level <= 1.0):
        raise ValueError("operational level must lie in [0,1]")
    lower = random_cut_expectation(inst)
    upper = spectral_maxcut_upper_bound(inst)
    if upper + 1e-10 < lower:
        raise RuntimeError("upper bound fell below random-cut expectation")
    tau = int(math.ceil(lower + level * (upper - lower) - 1e-12))
    mask = inst.cut_values >= tau
    count = int(np.count_nonzero(mask))
    feasible = count > 0
    return {
        "operational_level": float(level),
        "threshold": tau,
        "random_expectation_anchor": float(lower),
        "spectral_upper_bound": float(upper),
        "target_event_count_exact_validation": count,
        "rho_tau_exact_validation": float(count / inst.state_count),
        "feasible_exact_validation": bool(feasible),
        "realized_quality_ratio_exact_validation": float(tau / inst.optimum),
        "construction_uses_C_star": False,
    }


def threshold_spec(inst: MaxCutInstance, target_ratio: float) -> dict:
    """Return a numeric Max-Cut quality threshold and its exact marked fraction.

    The oracle semantics are threshold based: mark x iff C(x) >= tau.  Exact
    enumeration is used only in the small benchmark tier to characterize rho_tau;
    the oracle is not given a pre-enumerated list of optimal states.
    """
    if not (0.0 < target_ratio <= 1.0):
        raise ValueError("target_ratio must lie in (0,1]")
    tau = int(math.ceil(target_ratio * inst.optimum - 1e-12))
    mask = inst.cut_values >= tau
    count = int(np.count_nonzero(mask))
    if count <= 0:
        raise RuntimeError("quality threshold produced an empty marked set")
    return {
        "target_ratio": float(target_ratio),
        "threshold": tau,
        "marked_count": count,
        "rho_tau": float(count / inst.state_count),
    }


def target_probability(probs: np.ndarray, inst: MaxCutInstance, threshold: int) -> float:
    """Probability that a distribution over bit strings reaches C(x) >= threshold."""
    if len(probs) != inst.state_count:
        raise ValueError("probability vector length does not match instance state count")
    return float(probs[inst.cut_values >= threshold].sum())


def cut_value(x: int, inst: MaxCutInstance) -> int:
    return int(inst.cut_values[x])


GW_SDP_STARTS = 12
GW_SDP_MAX_SWEEPS = 2500
GW_SDP_CERT_GAP_TOL = 1e-6
GW_SDP_DUAL_FEAS_EPS = 1e-10
GW_ROUNDING_SAMPLES = 4096
GW_RANDOM_STREAM_VERSION = 1


def _stable_u32_token(text: str) -> int:
    """Stable 32-bit token for deterministic RNG stream construction."""
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:4], "little")


def _weighted_laplacian(inst: MaxCutInstance) -> np.ndarray:
    L = np.zeros((inst.n, inst.n), dtype=float)
    for i, j, w in inst.edges:
        wf = float(w)
        L[i, i] += wf
        L[j, j] += wf
        L[i, j] -= wf
        L[j, i] -= wf
    return L


def _gw_sdp_objective(inst: MaxCutInstance, vectors: np.ndarray) -> float:
    """Max-Cut SDP objective 1/2 sum_e w_e(1-v_i^T v_j)."""
    if vectors.shape != (inst.n, inst.n):
        raise ValueError("GW vector factor must have shape (n,n)")
    return float(
        0.5
        * sum(
            float(w) * (1.0 - float(vectors[i] @ vectors[j]))
            for i, j, w in inst.edges
        )
    )


def gw_sdp_relaxation(
    inst: MaxCutInstance,
    starts: int = GW_SDP_STARTS,
    max_sweeps: int = GW_SDP_MAX_SWEEPS,
    convergence_tol: float = 1e-11,
    dual_feas_eps: float = GW_SDP_DUAL_FEAS_EPS,
) -> dict:
    """Solve the Goemans--Williamson SDP factorization with a numerical dual certificate.

    The primal factor has rank n, so it can represent every feasible n-by-n SDP
    Gram matrix.  Block-coordinate ascent optimizes unit vectors.  Crucially, the
    reported SDP value is not accepted on primal optimization alone: each restart
    also constructs a dual candidate for

        min sum_i y_i  subject to Diag(y) - L/4 >= 0.

    A uniform diagonal shift makes the candidate numerically PSD.  The smallest
    dual upper bound across restarts and the largest primal value form an explicit
    primal--dual gap.  ``certified`` therefore means numerically bracketed to the
    declared tolerance; it is not a claim of symbolic exact arithmetic.
    """
    if starts <= 0 or max_sweeps <= 0:
        raise ValueError("starts and max_sweeps must be positive")
    if dual_feas_eps <= 0:
        raise ValueError("dual_feas_eps must be positive")

    n = inst.n
    L = _weighted_laplacian(inst)
    adjacency: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for i, j, w in inst.edges:
        adjacency[i].append((j, float(w)))
        adjacency[j].append((i, float(w)))

    token = _stable_u32_token(inst.instance_id)
    best_primal = -math.inf
    best_vectors: np.ndarray | None = None
    best_primal_start = -1
    best_primal_sweeps = -1
    best_dual = math.inf
    best_dual_min_eig = -math.inf
    best_dual_start = -1
    best_dual_shift = math.nan

    for start in range(starts):
        rng = np.random.default_rng(
            np.random.SeedSequence(
                [GW_RANDOM_STREAM_VERSION, 20260901, token, int(start)]
            )
        )
        vectors = rng.normal(size=(n, n))
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        previous = -math.inf

        for sweep in range(max_sweeps):
            max_change = 0.0
            for i in rng.permutation(n):
                field = np.zeros(n, dtype=float)
                for j, w in adjacency[i]:
                    field += w * vectors[j]
                norm = float(np.linalg.norm(field))
                if norm > 1e-15:
                    updated = -field / norm
                    max_change = max(
                        max_change, float(np.linalg.norm(updated - vectors[i]))
                    )
                    vectors[i] = updated
            primal = _gw_sdp_objective(inst, vectors)
            if (
                math.isfinite(previous)
                and abs(primal - previous) < convergence_tol
                and max_change < 3e-8
            ):
                break
            previous = primal

        primal = _gw_sdp_objective(inst, vectors)
        if primal > best_primal:
            best_primal = primal
            best_vectors = vectors.copy()
            best_primal_start = start
            best_primal_sweeps = sweep + 1

        # KKT-derived dual candidate.  Shift all y_i equally until the slack
        # matrix is safely PSD in floating-point arithmetic.
        LV = L @ vectors
        y = np.einsum("ij,ij->i", vectors, LV) / 4.0
        slack = np.diag(y) - L / 4.0
        min_eig_before = float(np.linalg.eigvalsh(slack)[0])
        shift = max(0.0, -min_eig_before + dual_feas_eps)
        y_feasible = y + shift
        slack_feasible = np.diag(y_feasible) - L / 4.0
        min_eig_after = float(np.linalg.eigvalsh(slack_feasible)[0])
        dual = float(y_feasible.sum())
        if dual < best_dual:
            best_dual = dual
            best_dual_min_eig = min_eig_after
            best_dual_start = start
            best_dual_shift = shift

    if best_vectors is None:
        raise RuntimeError("GW SDP solver produced no primal factor")

    gap = float(best_dual - best_primal)
    certified = bool(
        best_dual_min_eig >= -1e-9
        and gap >= -GW_SDP_CERT_GAP_TOL
        and gap <= GW_SDP_CERT_GAP_TOL
    )
    return {
        "primal_value": float(best_primal),
        "dual_upper_bound": float(best_dual),
        "primal_dual_gap": gap,
        "dual_min_eigenvalue": float(best_dual_min_eig),
        "dual_diagonal_shift": float(best_dual_shift),
        "certified": certified,
        "certificate_tolerance": float(GW_SDP_CERT_GAP_TOL),
        "starts": int(starts),
        "max_sweeps": int(max_sweeps),
        "best_primal_start": int(best_primal_start),
        "best_primal_sweeps": int(best_primal_sweeps),
        "best_dual_start": int(best_dual_start),
        "vectors": best_vectors,
    }


def gw_hyperplane_rounding(
    inst: MaxCutInstance,
    vectors: np.ndarray,
    samples: int = GW_ROUNDING_SAMPLES,
) -> dict:
    """Deterministic-seed Goemans--Williamson random-hyperplane rounding."""
    if samples <= 0:
        raise ValueError("samples must be positive")
    if vectors.shape != (inst.n, inst.n):
        raise ValueError("GW vector factor must have shape (n,n)")
    token = _stable_u32_token(inst.instance_id + "|gw-rounding")
    rng = np.random.default_rng(
        np.random.SeedSequence(
            [GW_RANDOM_STREAM_VERSION, 20260901, token, int(samples)]
        )
    )
    hyperplanes = rng.normal(size=(inst.n, samples))
    bits = (vectors @ hyperplanes) >= 0.0
    values = np.zeros(samples, dtype=float)
    for i, j, w in inst.edges:
        values += float(w) * (bits[i] != bits[j])

    out = {
        "rounding_samples": int(samples),
        "rounding_mean_cut": float(np.mean(values)),
        "rounding_median_cut": float(np.median(values)),
        "rounding_q1_cut": float(np.quantile(values, 0.25)),
        "rounding_q3_cut": float(np.quantile(values, 0.75)),
        "rounding_best_cut": int(np.max(values)),
        "rounding_mean_ratio_to_Cstar": float(np.mean(values) / inst.optimum),
        "rounding_median_ratio_to_Cstar": float(np.median(values) / inst.optimum),
        "rounding_best_ratio_to_Cstar": float(np.max(values) / inst.optimum),
        "rounding_optimum_hit_fraction": float(np.mean(values >= inst.optimum)),
    }
    for target_ratio in TARGET_RATIOS:
        spec = threshold_spec(inst, target_ratio)
        suffix = f"q{int(round(100 * target_ratio)):03d}"
        out[f"rounding_target_{suffix}_hit_fraction"] = float(
            np.mean(values >= spec["threshold"])
        )
    for level in OPERATIONAL_LEVELS:
        spec = operational_threshold_spec(inst, level)
        suffix = f"l{int(round(100 * level)):03d}"
        out[f"rounding_oper_{suffix}_hit_fraction"] = float(
            np.mean(values >= spec["threshold"])
        )
    return out


def gw_sdp_rows(suite: Iterable[MaxCutInstance], tier: str) -> list[dict]:
    """Certified numerical SDP + seeded GW rounding rows for an exact suite."""
    rows: list[dict] = []
    for inst in suite:
        solved = gw_sdp_relaxation(inst)
        if not solved["certified"]:
            raise RuntimeError(
                f"GW SDP numerical certificate failed for {inst.instance_id}: "
                f"gap={solved['primal_dual_gap']:.3e}"
            )
        rounded = gw_hyperplane_rounding(inst, solved["vectors"])
        spectral = spectral_maxcut_upper_bound(inst)
        row = {
            "tier": str(tier),
            "instance_id": inst.instance_id,
            "family": inst.family,
            "n": inst.n,
            "n_edges": inst.n_edges,
            "density_target": inst.density_target,
            "seed": inst.seed,
            "C_star": inst.optimum,
            "spectral_upper_bound": spectral,
            "sdp_primal_value": solved["primal_value"],
            "sdp_dual_upper_bound": solved["dual_upper_bound"],
            "sdp_primal_dual_gap": solved["primal_dual_gap"],
            "sdp_dual_min_eigenvalue": solved["dual_min_eigenvalue"],
            "sdp_dual_diagonal_shift": solved["dual_diagonal_shift"],
            "sdp_numerically_certified": solved["certified"],
            "sdp_certificate_tolerance": solved["certificate_tolerance"],
            "sdp_starts": solved["starts"],
            "sdp_max_sweeps": solved["max_sweeps"],
            "sdp_upper_bound_over_Cstar": solved["dual_upper_bound"] / inst.optimum,
            "sdp_tightening_vs_spectral": spectral - solved["dual_upper_bound"],
            **rounded,
            "evidence_label": (
                "Goemans-Williamson SDP relaxation with numerical primal-dual "
                "certificate and seeded random-hyperplane rounding; exact C* used "
                "only for retrospective scoring"
            ),
        }
        rows.append(row)
    return rows


def gw_sdp_summary_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    tiers = sorted({str(r["tier"]) for r in rows})
    for tier in tiers:
        group = [r for r in rows if r["tier"] == tier]
        for n_value in [None] + sorted({int(r["n"]) for r in group}):
            g = group if n_value is None else [r for r in group if int(r["n"]) == n_value]
            out.append({
                "tier": tier,
                "n": "all" if n_value is None else int(n_value),
                "instances": len(g),
                "certified_instances": sum(bool(r["sdp_numerically_certified"]) for r in g),
                "max_primal_dual_gap": max(float(r["sdp_primal_dual_gap"]) for r in g),
                "median_sdp_upper_bound_over_Cstar": float(np.median([float(r["sdp_upper_bound_over_Cstar"]) for r in g])),
                "median_rounding_mean_ratio_to_Cstar": float(np.median([float(r["rounding_mean_ratio_to_Cstar"]) for r in g])),
                "median_rounding_best_ratio_to_Cstar": float(np.median([float(r["rounding_best_ratio_to_Cstar"]) for r in g])),
                "instances_with_optimum_in_rounding": sum(float(r["rounding_best_ratio_to_Cstar"]) >= 1.0 - 1e-12 for r in g),
                "median_sdp_tightening_vs_spectral": float(np.median([float(r["sdp_tightening_vs_spectral"]) for r in g])),
                "evidence_label": "descriptive GW/SDP summary on exact validation tiers",
            })
    return out


def local_hillclimb(inst: MaxCutInstance, starts: int = 256, seed: int = 2026) -> dict:
    """Simple classical reference, not claimed as a best-known Max-Cut solver."""
    rng = np.random.default_rng(seed + inst.seed + inst.n * 1000 + inst.n_edges)
    finals: list[int] = []
    hit_opt = 0
    for _ in range(starts):
        x = int(rng.integers(0, 1 << inst.n))
        current = cut_value(x, inst)
        while True:
            best_x = x
            best_val = current
            for q in range(inst.n):
                y = x ^ (1 << q)
                v = cut_value(y, inst)
                if v > best_val:
                    best_x, best_val = y, v
            if best_val <= current:
                break
            x, current = best_x, best_val
        finals.append(current)
        if current == inst.optimum:
            hit_opt += 1
    arr = np.asarray(finals, dtype=float) / inst.optimum
    result = {
        "instance_id": inst.instance_id,
        "starts": starts,
        "best_ratio": float(arr.max()),
        "median_ratio": float(np.median(arr)),
        "q1_ratio": float(np.quantile(arr, 0.25)),
        "q3_ratio": float(np.quantile(arr, 0.75)),
        "optimum_hit_fraction": float(hit_opt / starts),
    }
    finals_arr = np.asarray(finals, dtype=float)
    for target_ratio in TARGET_RATIOS:
        spec = threshold_spec(inst, target_ratio)
        key = f"target_q{int(round(100*target_ratio)):03d}_hit_fraction"
        result[key] = float(np.mean(finals_arr >= spec["threshold"]))
    for level in OPERATIONAL_LEVELS:
        spec = operational_threshold_spec(inst, level)
        key = f"oper_l{int(round(100*level)):03d}_hit_fraction"
        result[key] = float(np.mean(finals_arr >= spec["threshold"]))
    return result



CLASSICAL_EVAL_BUDGET = 4096
CLASSICAL_BUDGETED_RUNS = 64
CLASSICAL_BUDGET_CURVE = (64, 128, 256, 512, 1024, 4096)


def _weighted_degree_scale(inst: MaxCutInstance) -> float:
    """Instance-derived energy scale; does not use C* or optimum-state identities."""
    deg = np.zeros(inst.n, dtype=float)
    for i, j, w in inst.edges:
        deg[i] += w
        deg[j] += w
    return float(max(1.0, np.max(deg)))


def simulated_annealing_run(
    inst: MaxCutInstance,
    seed: int,
    eval_budget: int = CLASSICAL_EVAL_BUDGET,
) -> dict:
    """One deterministic-budget simulated-annealing run.

    The search itself never queries the exact optimum.  ``eval_budget`` counts objective
    evaluations of complete bit strings, including the initial state.
    """
    if eval_budget < 2:
        raise ValueError("eval_budget must be at least 2")
    rng = np.random.default_rng(seed)
    x = int(rng.integers(0, 1 << inst.n))
    current = cut_value(x, inst)
    best = current
    best_x = x
    evaluations = 1

    energy_scale = _weighted_degree_scale(inst)
    t_start = energy_scale
    t_end = max(1e-3, energy_scale * 1e-3)
    proposals = eval_budget - 1
    for step in range(proposals):
        frac = step / max(1, proposals - 1)
        temperature = t_start * ((t_end / t_start) ** frac)
        q = int(rng.integers(0, inst.n))
        y = x ^ (1 << q)
        candidate = cut_value(y, inst)
        evaluations += 1
        delta = candidate - current
        if delta >= 0 or rng.random() < math.exp(delta / max(temperature, 1e-12)):
            x, current = y, candidate
        if current > best:
            best, best_x = current, x

    return {
        "best_cut": int(best),
        "best_state": int(best_x),
        "objective_evaluations": int(evaluations),
        "t_start": float(t_start),
        "t_end": float(t_end),
    }


def tabu_search_run(
    inst: MaxCutInstance,
    seed: int,
    eval_budget: int = CLASSICAL_EVAL_BUDGET,
    tenure: int | None = None,
) -> dict:
    """One fixed-objective-evaluation-budget one-flip tabu-search run.

    All one-bit neighbours are evaluated at each iteration. Aspiration permits a tabu
    move only when it improves the best value found within the run.  Exact C* is not used
    by the search logic.
    """
    if eval_budget < inst.n + 1:
        raise ValueError("eval_budget is too small for one tabu neighbourhood scan")
    if tenure is None:
        tenure = max(3, int(round(math.sqrt(inst.n))))
    if tenure <= 0:
        raise ValueError("tenure must be positive")

    rng = np.random.default_rng(seed)
    x = int(rng.integers(0, 1 << inst.n))
    current = cut_value(x, inst)
    best = current
    best_x = x
    evaluations = 1
    tabu_until = np.zeros(inst.n, dtype=int)
    iteration = 0

    while evaluations + inst.n <= eval_budget:
        candidates: list[tuple[int, int, int]] = []
        for q in range(inst.n):
            y = x ^ (1 << q)
            value = cut_value(y, inst)
            evaluations += 1
            allowed = iteration >= int(tabu_until[q]) or value > best
            if allowed:
                candidates.append((value, -q, y))
        if not candidates:
            # This is extremely unlikely with the short tenure, but keeping an explicit
            # fallback avoids a hidden early termination if every move is tabu.
            q = int(rng.integers(0, inst.n))
            y = x ^ (1 << q)
            value = cut_value(y, inst)
            candidates.append((value, -q, y))
        value, neg_q, y = max(candidates)
        q = -neg_q
        x, current = int(y), int(value)
        tabu_until[q] = iteration + tenure + 1
        if current > best:
            best, best_x = current, x
        iteration += 1

    return {
        "best_cut": int(best),
        "best_state": int(best_x),
        "objective_evaluations": int(evaluations),
        "iterations": int(iteration),
        "tenure": int(tenure),
    }


def run_budgeted_classical_suite(
    suite: Iterable[MaxCutInstance],
    runs: int = CLASSICAL_BUDGETED_RUNS,
    eval_budget: int = CLASSICAL_EVAL_BUDGET,
    base_seed: int = 700_001,
) -> tuple[list[dict], list[dict]]:
    """Run reproducible SA and tabu references under the same per-run objective budget."""
    if runs <= 0:
        raise ValueError("runs must be positive")
    raw: list[dict] = []
    summary: list[dict] = []
    methods = (
        ("simulated_annealing", simulated_annealing_run, 0),
        ("tabu_search", tabu_search_run, 10_000_000),
    )
    for inst in suite:
        for method_name, method, method_offset in methods:
            method_rows: list[dict] = []
            for run_index in range(runs):
                run_seed = (
                    base_seed + method_offset + 100_000 * inst.n
                    + 1_000 * inst.n_edges + 10 * inst.seed + run_index
                )
                out = method(inst, seed=run_seed, eval_budget=eval_budget)
                row = {
                    "instance_id": inst.instance_id,
                    "n": inst.n,
                    "density_target": inst.density_target,
                    "seed": inst.seed,
                    "method": method_name,
                    "run_index": run_index,
                    "run_seed": run_seed,
                    "eval_budget": eval_budget,
                    "objective_evaluations": out["objective_evaluations"],
                    "best_cut": out["best_cut"],
                    "best_ratio": out["best_cut"] / inst.optimum,
                    "optimum_hit": int(out["best_cut"] == inst.optimum),
                    "evidence_label": "fixed-objective-evaluation-budget classical heuristic; exact optimum used only for retrospective scoring",
                }
                for target_ratio in TARGET_RATIOS:
                    spec = threshold_spec(inst, target_ratio)
                    row[f"target_q{int(round(100*target_ratio)):03d}_hit"] = int(out["best_cut"] >= spec["threshold"])
                for level in OPERATIONAL_LEVELS:
                    spec = operational_threshold_spec(inst, level)
                    row[f"oper_l{int(round(100*level)):03d}_hit"] = int(out["best_cut"] >= spec["threshold"])
                raw.append(row)
                method_rows.append(row)

            ratios = np.asarray([float(r["best_ratio"]) for r in method_rows], dtype=float)
            evals = np.asarray([int(r["objective_evaluations"]) for r in method_rows], dtype=int)
            q1, med, q3 = np.quantile(ratios, [0.25, 0.50, 0.75])
            sr = {
                "instance_id": inst.instance_id,
                "n": inst.n,
                "density_target": inst.density_target,
                "seed": inst.seed,
                "method": method_name,
                "runs": runs,
                "eval_budget_per_run": eval_budget,
                "median_objective_evaluations": float(np.median(evals)),
                "best_ratio": float(ratios.max()),
                "median_best_ratio": float(med),
                "q1_best_ratio": float(q1),
                "q3_best_ratio": float(q3),
                "optimum_hit_fraction": float(np.mean([int(r["optimum_hit"]) for r in method_rows])),
                "evidence_label": "fixed-objective-evaluation-budget classical heuristic; not a quantum-resource match",
            }
            for target_ratio in TARGET_RATIOS:
                suffix = f"q{int(round(100*target_ratio)):03d}"
                sr[f"target_{suffix}_hit_fraction"] = float(np.mean([int(r[f"target_{suffix}_hit"]) for r in method_rows]))
            for level in OPERATIONAL_LEVELS:
                suffix = f"l{int(round(100*level)):03d}"
                sr[f"oper_{suffix}_hit_fraction"] = float(np.mean([int(r[f"oper_{suffix}_hit"]) for r in method_rows]))
            summary.append(sr)
    return raw, summary


def run_classical_budget_curve(
    suite: Iterable[MaxCutInstance],
    budgets: tuple[int, ...] = CLASSICAL_BUDGET_CURVE,
    runs: int = CLASSICAL_BUDGETED_RUNS,
    base_seed: int = 700_001,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Evaluate SA/tabu across a declared objective-evaluation budget curve.

    Each budget is a complete deterministic-budget experiment using the same seed
    mapping. Simulated annealing rescales its temperature schedule to the declared
    budget, so these are budget-specific runs rather than prefix checkpoints.
    """
    if not budgets or any(int(b) < 2 for b in budgets):
        raise ValueError('budgets must contain evaluation caps >=2')
    suite_list = list(suite)
    raw_all: list[dict] = []
    summary_all: list[dict] = []
    inst_lookup = {x.instance_id: x for x in suite_list}
    for budget in budgets:
        raw, summary = run_budgeted_classical_suite(
            suite_list, runs=runs, eval_budget=int(budget), base_seed=base_seed
        )
        for r in raw:
            r['curve_budget'] = int(budget)
            raw_all.append(r)
        for r in summary:
            r['curve_budget'] = int(budget)
            inst = inst_lookup[r['instance_id']]
            r['state_count'] = inst.state_count
            r['budget_over_state_count'] = float(int(budget) / inst.state_count)
            summary_all.append(r)

    aggregate: list[dict] = []
    for method in ('simulated_annealing', 'tabu_search'):
        for budget in budgets:
            rr = [r for r in summary_all if r['method'] == method and int(r['curve_budget']) == int(budget)]
            vals = np.asarray([float(r['median_best_ratio']) for r in rr], dtype=float)
            aggregate.append({
                'method': method,
                'eval_budget_per_run': int(budget),
                'instances': len(rr),
                'runs_per_instance': int(runs),
                'median_of_instance_median_best_ratio': float(np.median(vals)),
                'q1_of_instance_median_best_ratio': float(np.quantile(vals, 0.25)),
                'q3_of_instance_median_best_ratio': float(np.quantile(vals, 0.75)),
                'median_instance_optimum_hit_fraction': float(np.median([float(r['optimum_hit_fraction']) for r in rr])),
                'instances_with_at_least_one_optimum_hit': int(sum(float(r['optimum_hit_fraction']) > 0 for r in rr)),
                'median_budget_over_state_count': float(np.median([float(r['budget_over_state_count']) for r in rr])),
                'evidence_label': 'within-classical objective-evaluation budget curve; not matched to quantum resources',
            })
    return raw_all, summary_all, aggregate


def _apply_rx_all(state: np.ndarray, beta: float, n: int) -> np.ndarray:
    c = math.cos(beta)
    s = -1j * math.sin(beta)
    out = state.copy()
    idx = np.arange(len(out))
    for q in range(n):
        mask = 1 << q
        i0 = idx[(idx & mask) == 0]
        i1 = i0 | mask
        a = out[i0].copy()
        b = out[i1].copy()
        out[i0] = c * a + s * b
        out[i1] = s * a + c * b
    return out


def qaoa_state(params: np.ndarray, p: int, inst: MaxCutInstance) -> np.ndarray:
    if len(params) != 2 * p:
        raise ValueError("parameter length must be 2p")
    gammas = params[:p]
    betas = params[p:]
    state = np.ones(inst.state_count, dtype=np.complex128) / math.sqrt(inst.state_count)
    for layer in range(p):
        state *= np.exp(-1j * gammas[layer] * inst.cut_values)
        state = _apply_rx_all(state, betas[layer], inst.n)
    return state


def qaoa_metrics(params: np.ndarray, p: int, inst: MaxCutInstance) -> tuple[float, float, np.ndarray]:
    state = qaoa_state(params, p, inst)
    probs = np.abs(state) ** 2
    expected = float(np.dot(probs, inst.cut_values))
    p_opt = float(probs[list(inst.optimum_states)].sum())
    return expected, p_opt, probs


def wilson_interval(hits: int, shots: int, z: float = 1.959963984540054) -> tuple[float, float, float]:
    if shots <= 0 or not (0 <= hits <= shots):
        raise ValueError("invalid binomial counts")
    phat = hits / shots
    denom = 1 + z * z / shots
    centre = (phat + z * z / (2 * shots)) / denom
    half = z * math.sqrt(phat * (1 - phat) / shots + z * z / (4 * shots * shots)) / denom
    return phat, max(0.0, centre - half), min(1.0, centre + half)



QAOA_INIT_STREAM_VERSION = 1
QAOA_STABILITY_STARTS = 20


def qaoa_initial_params(inst: MaxCutInstance, p: int, optimizer_seed: int) -> np.ndarray:
    """Deterministic instance-conditioned QAOA initialization.

    The graph identity participates in the random stream so equal external optimizer
    seeds do not reuse the same parameter vector across distinct graph instances.
    Optimizer families still call this same helper at fixed (instance,p,seed), which
    preserves the paired-initialization contract for the L-BFGS-B/COBYLA ablation.
    """
    if p <= 0:
        raise ValueError("p must be positive")
    payload = inst.instance_id + "|" + ";".join(f"{i},{j},{w}" for i, j, w in inst.edges)
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    words = [int.from_bytes(digest[i:i+4], "big") for i in range(0, 16, 4)]
    stream = np.random.SeedSequence([
        QAOA_INIT_STREAM_VERSION, int(inst.n), int(p), int(optimizer_seed), *words
    ])
    rng = np.random.default_rng(stream)
    return np.concatenate([
        rng.uniform(0, 2 * math.pi, p),
        rng.uniform(0, math.pi, p),
    ])

def run_qaoa_one(
    inst: MaxCutInstance,
    p: int,
    optimizer_seed: int,
    maxiter: int = 60,
    final_shots: int = 4096,
) -> dict:
    x0 = qaoa_initial_params(inst, p, optimizer_seed)
    bounds = [(0, 2 * math.pi)] * p + [(0, math.pi)] * p

    def obj(x: np.ndarray) -> float:
        expected, _, _ = qaoa_metrics(x, p, inst)
        return -expected

    t0 = time.perf_counter()
    res = minimize(
        obj,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": maxiter, "ftol": 1e-12},
    )
    elapsed = time.perf_counter() - t0
    expected, p_opt, probs = qaoa_metrics(res.x, p, inst)
    sample_rng = np.random.default_rng(
        1_000_000 + 10_000 * inst.n + 100 * inst.seed + 10 * p + optimizer_seed
    )
    draws = sample_rng.choice(len(probs), size=final_shots, p=probs)
    hits = int(np.isin(draws, np.asarray(inst.optimum_states)).sum())
    phat, lo, hi = wilson_interval(hits, final_shots)
    target_metrics = {}
    for target_ratio in TARGET_RATIOS:
        spec = threshold_spec(inst, target_ratio)
        suffix = f"q{int(round(100*target_ratio)):03d}"
        p_target = target_probability(probs, inst, spec["threshold"])
        target_metrics[f"threshold_{suffix}"] = spec["threshold"]
        target_metrics[f"rho_uniform_{suffix}"] = spec["rho_tau"]
        target_metrics[f"p_target_exact_{suffix}"] = p_target
        target_metrics[f"expected_repetitions_{suffix}"] = (1.0 / p_target) if p_target > 0 else math.inf
    for level in OPERATIONAL_LEVELS:
        spec = operational_threshold_spec(inst, level)
        suffix = f"l{int(round(100*level)):03d}"
        p_target = target_probability(probs, inst, spec["threshold"])
        target_metrics[f"oper_threshold_{suffix}"] = spec["threshold"]
        target_metrics[f"oper_rho_uniform_{suffix}"] = spec["rho_tau_exact_validation"]
        target_metrics[f"oper_feasible_{suffix}"] = spec["feasible_exact_validation"]
        target_metrics[f"oper_p_target_exact_{suffix}"] = p_target
        target_metrics[f"oper_expected_repetitions_{suffix}"] = (1.0 / p_target) if p_target > 0 else math.inf
    return {
        "instance_id": inst.instance_id,
        "n": inst.n,
        "density_target": inst.density_target,
        "graph_seed": inst.seed,
        "p": p,
        "optimizer_seed": optimizer_seed,
        "success": bool(res.success),
        "nit": int(getattr(res, "nit", -1)),
        "nfev": int(getattr(res, "nfev", -1)),
        "optimizer": "L-BFGS-B",
        "maxiter": maxiter,
        "T_opt_s": elapsed,
        "expected_cut": expected,
        "approx_ratio": expected / inst.optimum,
        "p_opt_exact": p_opt,
        "final_shots": final_shots,
        "hits_opt": hits,
        "p_opt_sample": phat,
        "p_opt_ci_lo": lo,
        "p_opt_ci_hi": hi,
        "initial_params": json.dumps([float(v) for v in x0]),
        "final_params": json.dumps([float(v) for v in res.x]),
        "message": str(res.message),
        **target_metrics,
    }




class _QAOAEvaluationBudgetStop(RuntimeError):
    pass


QAOA_OPTIMIZER_EVAL_BUDGET = 128
QAOA_OPTIMIZER_METHODS = ("L-BFGS-B", "COBYLA")


def run_qaoa_budgeted_one(
    inst: MaxCutInstance,
    p: int,
    optimizer_seed: int,
    optimizer: str,
    eval_budget: int = QAOA_OPTIMIZER_EVAL_BUDGET,
) -> dict:
    """Optimize one ideal-statevector QAOA run under a strict objective-evaluation cap.

    The same x0 is used for all optimizer families at fixed (instance,p,seed). The
    cap counts calls to the exact statevector expectation objective only. Final
    diagnostic metrics are evaluated after optimization and are not charged to
    the optimization budget. This is an optimizer-robustness comparison, not a
    physical quantum-runtime comparison.
    """
    if optimizer not in QAOA_OPTIMIZER_METHODS:
        raise ValueError(f"unsupported optimizer: {optimizer}")
    if eval_budget < 4:
        raise ValueError("eval_budget must be at least 4")
    x0 = qaoa_initial_params(inst, p, optimizer_seed)
    bounds = [(0, 2 * math.pi)] * p + [(0, math.pi)] * p
    nfev = 0
    best_expected = -math.inf
    best_x = np.asarray(x0, dtype=float).copy()

    def obj(x: np.ndarray) -> float:
        nonlocal nfev, best_expected, best_x
        if nfev >= eval_budget:
            raise _QAOAEvaluationBudgetStop
        nfev += 1
        expected, _, _ = qaoa_metrics(np.asarray(x, dtype=float), p, inst)
        if expected > best_expected:
            best_expected = float(expected)
            best_x = np.asarray(x, dtype=float).copy()
        return -expected

    t0 = time.perf_counter()
    success = False
    termination = "optimizer_stopped"
    message = ""
    nit = -1
    try:
        if optimizer == "L-BFGS-B":
            res = minimize(
                obj,
                x0,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 10000, "maxfun": eval_budget, "ftol": 1e-12, "gtol": 1e-8},
            )
        else:
            res = minimize(
                obj,
                x0,
                method="COBYLA",
                bounds=bounds,
                options={"maxiter": eval_budget, "rhobeg": 0.5, "tol": 1e-6, "catol": 1e-6},
            )
        success = bool(res.success)
        termination = "optimizer_converged" if success else "optimizer_stopped"
        if (not success) and nfev >= eval_budget:
            termination = "evaluation_budget_exhausted"
        message = str(res.message)
        nit = int(getattr(res, "nit", -1))
        # Preserve the best point actually observed under the counted budget rather
        # than assuming res.x is always the best objective value visited.
    except _QAOAEvaluationBudgetStop:
        termination = "evaluation_budget_exhausted"
        message = f"strict objective-evaluation cap {eval_budget} reached"
    elapsed = time.perf_counter() - t0

    expected, p_opt, probs = qaoa_metrics(best_x, p, inst)
    row = {
        "instance_id": inst.instance_id,
        "n": inst.n,
        "density_target": inst.density_target,
        "graph_seed": inst.seed,
        "p": p,
        "optimizer_seed": optimizer_seed,
        "optimizer": optimizer,
        "objective_eval_budget": int(eval_budget),
        "objective_evaluations_used": int(nfev),
        "budget_fraction_used": float(nfev / eval_budget),
        "success": bool(success),
        "termination": termination,
        "nit": nit,
        "T_opt_s_host_diagnostic": float(elapsed),
        "expected_cut": float(expected),
        "approx_ratio": float(expected / inst.optimum),
        "p_opt_exact": float(p_opt),
        "initial_params": json.dumps([float(v) for v in x0]),
        "best_seen_params": json.dumps([float(v) for v in best_x]),
        "message": message,
        "evidence_label": "ideal-statevector optimizer robustness under equal objective-evaluation cap; not hardware runtime",
    }
    for target_ratio in TARGET_RATIOS:
        spec = threshold_spec(inst, target_ratio)
        suffix = f"q{int(round(100*target_ratio)):03d}"
        row[f"p_target_exact_{suffix}"] = target_probability(probs, inst, spec["threshold"])
    for level in OPERATIONAL_LEVELS:
        spec = operational_threshold_spec(inst, level)
        suffix = f"l{int(round(100*level)):03d}"
        row[f"oper_feasible_{suffix}"] = spec["feasible_exact_validation"]
        row[f"oper_p_target_exact_{suffix}"] = target_probability(probs, inst, spec["threshold"])
    return row


def run_qaoa_optimizer_budget_suite(
    suite: Iterable[MaxCutInstance],
    depths=(1, 2, 3),
    optimizer_seeds=range(5),
    optimizers=QAOA_OPTIMIZER_METHODS,
    eval_budget: int = QAOA_OPTIMIZER_EVAL_BUDGET,
) -> list[dict]:
    """Paired optimizer comparison on all primary instances and identical x0 seeds."""
    raw: list[dict] = []
    for inst in suite:
        for p in depths:
            for seed in optimizer_seeds:
                for optimizer in optimizers:
                    raw.append(run_qaoa_budgeted_one(inst, p, int(seed), str(optimizer), eval_budget))
    return raw




def qaoa_optimizer_paired_deltas(raw: list[dict]) -> list[dict]:
    """Pair optimizer outcomes at identical instance, depth, and initialization seed."""
    rows: list[dict] = []
    keys = sorted({(r["instance_id"], int(r["p"]), int(r["optimizer_seed"])) for r in raw})
    for iid, p, seed in keys:
        rr = {r["optimizer"]: r for r in raw if r["instance_id"] == iid and int(r["p"]) == p and int(r["optimizer_seed"]) == seed}
        if set(rr) != set(QAOA_OPTIMIZER_METHODS):
            raise RuntimeError("paired optimizer ledger is incomplete")
        a = rr["L-BFGS-B"]
        c = rr["COBYLA"]
        rows.append({
            "instance_id": iid,
            "p": p,
            "optimizer_seed": seed,
            "lbfgsb_approx_ratio": float(a["approx_ratio"]),
            "cobyla_approx_ratio": float(c["approx_ratio"]),
            "delta_cobyla_minus_lbfgsb": float(c["approx_ratio"]) - float(a["approx_ratio"]),
            "lbfgsb_objective_evaluations": int(a["objective_evaluations_used"]),
            "cobyla_objective_evaluations": int(c["objective_evaluations_used"]),
            "evidence_label": "paired ideal-statevector optimizer delta under identical initialization and equal evaluation cap",
        })
    return rows

def summarize_qaoa_optimizer_budget(raw: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return per-instance and aggregate optimizer/depth summaries."""
    instance_rows: list[dict] = []
    keys = sorted({(r["instance_id"], int(r["p"]), r["optimizer"]) for r in raw})
    for iid, p, optimizer in keys:
        rr = [r for r in raw if r["instance_id"] == iid and int(r["p"]) == p and r["optimizer"] == optimizer]
        ar = np.asarray([float(r["approx_ratio"]) for r in rr], dtype=float)
        po = np.asarray([float(r["p_opt_exact"]) for r in rr], dtype=float)
        ev = np.asarray([int(r["objective_evaluations_used"]) for r in rr], dtype=float)
        instance_rows.append({
            "instance_id": iid,
            "p": p,
            "optimizer": optimizer,
            "runs": len(rr),
            "approx_ratio_median": float(np.median(ar)),
            "approx_ratio_q1": float(np.quantile(ar, 0.25)),
            "approx_ratio_q3": float(np.quantile(ar, 0.75)),
            "p_opt_exact_median": float(np.median(po)),
            "objective_evaluations_median": float(np.median(ev)),
            "budget_exhausted_fraction": float(np.mean([r["termination"] == "evaluation_budget_exhausted" for r in rr])),
        })

    aggregate: list[dict] = []
    for optimizer in QAOA_OPTIMIZER_METHODS:
        for p in sorted({int(r["p"]) for r in raw}):
            rr = [r for r in instance_rows if r["optimizer"] == optimizer and int(r["p"]) == p]
            ar = np.asarray([float(r["approx_ratio_median"]) for r in rr], dtype=float)
            po = np.asarray([float(r["p_opt_exact_median"]) for r in rr], dtype=float)
            raw_rr = [r for r in raw if r["optimizer"] == optimizer and int(r["p"]) == p]
            aggregate.append({
                "optimizer": optimizer,
                "p": p,
                "instances": len(rr),
                "runs": len(raw_rr),
                "objective_eval_budget_per_run": int(raw_rr[0]["objective_eval_budget"]) if raw_rr else 0,
                "median_instance_approx_ratio": float(np.median(ar)),
                "q1_instance_approx_ratio": float(np.quantile(ar, 0.25)),
                "q3_instance_approx_ratio": float(np.quantile(ar, 0.75)),
                "median_instance_p_opt": float(np.median(po)),
                "median_objective_evaluations_used": float(np.median([r["objective_evaluations_used"] for r in raw_rr])),
                "budget_exhausted_fraction": float(np.mean([r["termination"] == "evaluation_budget_exhausted" for r in raw_rr])),
                "optimizer_success_fraction": float(np.mean([bool(r["success"]) for r in raw_rr])),
                "evidence_label": "paired ideal-statevector optimizer comparison under equal objective-evaluation cap",
            })
    return instance_rows, aggregate



J_BOOTSTRAP_RESAMPLES = 20000
J_BOOTSTRAP_SEED = 20260830


def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm family-wise adjustment, returned in the original order."""
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1 or len(p) == 0:
        raise ValueError("p_values must be a non-empty one-dimensional sequence")
    order = np.argsort(p)
    adjusted = np.empty(len(p), dtype=float)
    running = 0.0
    m = len(p)
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * float(p[idx]))
        running = max(running, value)
        adjusted[idx] = running
    return [float(x) for x in adjusted]


def paired_rank_biserial(differences: Iterable[float], zero_tol: float = 1e-15) -> float:
    """Matched-pairs rank-biserial correlation; positive follows the difference sign."""
    d = np.asarray(list(differences), dtype=float)
    d = d[np.abs(d) > zero_tol]
    if len(d) == 0:
        return 0.0
    ranks = rankdata(np.abs(d), method="average")
    w_plus = float(ranks[d > 0].sum())
    w_minus = float(ranks[d < 0].sum())
    denom = w_plus + w_minus
    return 0.0 if denom == 0 else float((w_plus - w_minus) / denom)


def bootstrap_median_ci(
    differences: Iterable[float],
    resamples: int = J_BOOTSTRAP_RESAMPLES,
    seed: int = J_BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Percentile bootstrap CI for a paired median, resampling benchmark instances."""
    d = np.asarray(list(differences), dtype=float)
    if len(d) == 0 or resamples < 100:
        raise ValueError("need non-empty differences and at least 100 bootstrap resamples")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(int(resamples), len(d)))
    medians = np.median(d[idx], axis=1)
    lo, hi = np.quantile(medians, [0.025, 0.975])
    return float(lo), float(hi)


def qaoa_depth_inference(
    qaoa_raw: list[dict],
    bootstrap_resamples: int = J_BOOTSTRAP_RESAMPLES,
    seed: int = J_BOOTSTRAP_SEED,
) -> list[dict]:
    """Instance-clustered inference for the primary L-BFGS-B depth study.

    Repeated initialization runs are first collapsed to an instance-level median at
    each depth. The 18 deterministic primary benchmark instances are then the paired
    units. Inference is conditional on this fixed suite; it is not population
    generalization over random graphs.
    """
    by_key: dict[tuple[str, int], list[float]] = {}
    for r in qaoa_raw:
        key = (str(r["instance_id"]), int(r["p"]))
        by_key.setdefault(key, []).append(float(r["approx_ratio"]))
    instance_ids = sorted({k[0] for k in by_key})
    depths = (1, 2, 3)
    if any((iid, p) not in by_key for iid in instance_ids for p in depths):
        raise RuntimeError("primary QAOA depth ledger is incomplete")
    med = {
        (iid, p): float(np.median(by_key[(iid, p)]))
        for iid in instance_ids for p in depths
    }
    vectors = [np.asarray([med[(iid, p)] for iid in instance_ids], dtype=float) for p in depths]
    fried = friedmanchisquare(*vectors)
    comparisons = ((1, 2), (1, 3), (2, 3))
    rows: list[dict] = []
    p_raw: list[float] = []
    for j, (a, b) in enumerate(comparisons):
        diff = np.asarray([med[(iid, b)] - med[(iid, a)] for iid in instance_ids], dtype=float)
        test = wilcoxon(diff, zero_method="wilcox", alternative="two-sided", method="auto")
        lo, hi = bootstrap_median_ci(diff, bootstrap_resamples, seed + 100 + j)
        p_raw.append(float(test.pvalue))
        rows.append({
            "analysis": "qaoa_depth_instance_clustered",
            "comparison": f"p{b}-p{a}",
            "n_instances": len(instance_ids),
            "median_delta": float(np.median(diff)),
            "bootstrap95_lo": lo,
            "bootstrap95_hi": hi,
            "wilcoxon_statistic": float(test.statistic),
            "p_raw": float(test.pvalue),
            "p_holm": math.nan,
            "rank_biserial": paired_rank_biserial(diff),
            "friedman_statistic": float(fried.statistic),
            "friedman_p": float(fried.pvalue),
            "evidence_label": "instance-clustered paired inference on 18 fixed primary benchmark instances; not population generalization",
        })
    for row, adj in zip(rows, holm_adjust(p_raw)):
        row["p_holm"] = adj
    return rows


def qaoa_optimizer_inference(
    paired_rows: list[dict],
    bootstrap_resamples: int = J_BOOTSTRAP_RESAMPLES,
    seed: int = J_BOOTSTRAP_SEED,
) -> tuple[list[dict], list[dict]]:
    """Instance-clustered optimizer inference after collapsing the five seed pairs.

    The paired outcome is COBYLA minus L-BFGS-B under the H-phase 128-exact-
    objective-evaluation cap. Seed-level pairs are descriptive repetitions;
    primary inference uses one median difference per benchmark instance and depth.
    """
    by_key: dict[tuple[str, int], list[float]] = {}
    for r in paired_rows:
        key = (str(r["instance_id"]), int(r["p"]))
        by_key.setdefault(key, []).append(float(r["delta_cobyla_minus_lbfgsb"]))
    instance_rows: list[dict] = []
    for (iid, p), values in sorted(by_key.items()):
        instance_rows.append({
            "instance_id": iid,
            "p": p,
            "paired_initializations": len(values),
            "instance_median_delta_cobyla_minus_lbfgsb": float(np.median(values)),
            "evidence_label": "instance-level median of paired optimizer deltas under the finite 128-evaluation cap",
        })
    depths = sorted({int(r["p"]) for r in instance_rows})
    rows: list[dict] = []
    p_raw: list[float] = []
    for j, p in enumerate(depths):
        rr = [r for r in instance_rows if int(r["p"]) == p]
        diff = np.asarray([float(r["instance_median_delta_cobyla_minus_lbfgsb"]) for r in rr], dtype=float)
        test = wilcoxon(diff, zero_method="wilcox", alternative="two-sided", method="auto")
        lo, hi = bootstrap_median_ci(diff, bootstrap_resamples, seed + 200 + j)
        p_raw.append(float(test.pvalue))
        rows.append({
            "analysis": "optimizer_COBYLA_minus_LBFGSB_instance_clustered",
            "p": p,
            "n_instances": len(rr),
            "median_instance_delta": float(np.median(diff)),
            "bootstrap95_lo": lo,
            "bootstrap95_hi": hi,
            "wilcoxon_statistic": float(test.statistic),
            "p_raw": float(test.pvalue),
            "p_holm": math.nan,
            "rank_biserial": paired_rank_biserial(diff),
            "evidence_label": "instance-clustered paired optimizer inference; five paired starts collapsed within instance; finite 128-evaluation cap",
        })
    for row, adj in zip(rows, holm_adjust(p_raw)):
        row["p_holm"] = adj
    return instance_rows, rows

def run_qaoa_suite(
    suite: Iterable[MaxCutInstance],
    depths=(1, 2, 3),
    optimizer_seeds=range(5),
    maxiter: int = 60,
    final_shots: int = 4096,
) -> list[dict]:
    raw: list[dict] = []
    # QAOA primary suite: all 18 independently streamed fixed-density instances.
    for inst in suite:
        for p in depths:
            for s in optimizer_seeds:
                raw.append(run_qaoa_one(inst, p, int(s), maxiter=maxiter, final_shots=final_shots))
    return raw


def summarize_qaoa(raw: list[dict]) -> tuple[list[dict], list[dict]]:
    by_instance: list[dict] = []
    keys = sorted({(r["instance_id"], int(r["p"])) for r in raw})
    for iid, p in keys:
        rr = [r for r in raw if r["instance_id"] == iid and int(r["p"]) == p]
        ratio = np.asarray([r["approx_ratio"] for r in rr])
        popt = np.asarray([r["p_opt_exact"] for r in rr])
        by_instance.append(
            {
                "instance_id": iid,
                "p": p,
                "runs": len(rr),
                "converged": sum(bool(r["success"]) for r in rr),
                "approx_ratio_median": float(np.median(ratio)),
                "approx_ratio_q1": float(np.quantile(ratio, 0.25)),
                "approx_ratio_q3": float(np.quantile(ratio, 0.75)),
                "p_opt_exact_median": float(np.median(popt)),
                "p_opt_exact_q1": float(np.quantile(popt, 0.25)),
                "p_opt_exact_q3": float(np.quantile(popt, 0.75)),
            }
        )

    aggregate: list[dict] = []
    for p in sorted({int(r["p"]) for r in by_instance}):
        rr = [r for r in by_instance if int(r["p"]) == p]
        ar = np.asarray([r["approx_ratio_median"] for r in rr])
        po = np.asarray([r["p_opt_exact_median"] for r in rr])
        aggregate.append(
            {
                "p": p,
                "instances": len(rr),
                "optimizer_runs": sum(int(r["runs"]) for r in rr),
                "instance_median_approx_ratio": float(np.median(ar)),
                "instance_q1_approx_ratio": float(np.quantile(ar, 0.25)),
                "instance_q3_approx_ratio": float(np.quantile(ar, 0.75)),
                "instance_median_p_opt": float(np.median(po)),
                "instance_q1_p_opt": float(np.quantile(po, 0.25)),
                "instance_q3_p_opt": float(np.quantile(po, 0.75)),
            }
        )
    return by_instance, aggregate



def simulator_scaling_tier(n_values=(8, 10, 12, 14, 16, 18, 20), density_target: float = 0.5, seed: int = 42) -> list[dict]:
    """Host-side exact-enumeration/statevector scaling diagnostic.

    The timings characterize this Python/Numpy reference implementation only. They are
    evidence boundaries for classical simulation cost, not quantum-runtime measurements.
    """
    rows: list[dict] = []
    for n in n_values:
        t0 = time.perf_counter()
        inst = build_maxcut_instance(n, density_target, seed)
        build_s = time.perf_counter() - t0
        params = np.array([0.2, 0.3], dtype=float)
        t1 = time.perf_counter()
        expected, p_opt, probs = qaoa_metrics(params, 1, inst)
        eval_s = time.perf_counter() - t1
        state_bytes = int(probs.nbytes)
        cut_bytes = int(inst.cut_values.nbytes)
        rows.append({
            "n": n,
            "state_count": inst.state_count,
            "density_target": density_target,
            "seed": seed,
            "exact_build_s": build_s,
            "p1_statevector_eval_s": eval_s,
            "cut_values_bytes": cut_bytes,
            "probability_vector_bytes": state_bytes,
            "combined_core_bytes": cut_bytes + state_bytes,
            "expected_cut_fixed_params": expected,
            "p_opt_fixed_params": p_opt,
            "evidence_label": "host simulation scaling only",
        })
    return rows


def dense_resource_robustness(suite: Iterable[MaxCutInstance]) -> list[dict]:
    """Dense threshold-aware uncertainty grid over attenuation and oracle cost.

    All three target-quality events are retained.  Grid coordinates are dimensionless
    model variables and are deliberately not mapped to a physical backend.
    """
    eps_grid = np.linspace(0.0, 0.003, 13)
    oracle_grid = np.geomspace(0.5, 16.0, 17)
    rows: list[dict] = []
    for inst in suite:
        for target_ratio in TARGET_RATIOS:
            spec = threshold_spec(inst, target_ratio)
            for eps in eps_grid:
                for oracle_cost in oracle_grid:
                    sel = select_k_resource_efficiency(
                        spec["rho_tau"], float(eps), 30.0, 30.0, 1.0,
                        float(oracle_cost), 1.0, 80
                    )
                    p0 = effective_probability(spec["rho_tau"], 0, float(eps), 30.0, 30.0)
                    baseline_resource_per_hit = 1.0 / p0
                    selected_resource_per_hit = sel["normalized_cost"] / sel["p_eff"]
                    rows.append({
                        "instance_id": inst.instance_id,
                        "n": inst.n,
                        "target_ratio": spec["target_ratio"],
                        "threshold": spec["threshold"],
                        "marked_count": spec["marked_count"],
                        "rho_tau": spec["rho_tau"],
                        "eps_model": float(eps),
                        "oracle_cost_norm": float(oracle_cost),
                        "k_star": sel["k"],
                        "p_target_eff": sel["p_eff"],
                        "normalized_cost": sel["normalized_cost"],
                        "normalized_resource_per_target_hit": selected_resource_per_hit,
                        "eta_res": selected_resource_per_hit / baseline_resource_per_hit,
                    })
    return rows


def select_k_with_rho_estimate(
    rho_true: float,
    rho_est: float,
    eps_model: float,
    d_prep: float,
    d_iter: float,
    prep_cost: float,
    oracle_cost: float,
    diffusion_cost: float,
    k_max: int,
) -> dict:
    """Choose k with rho_est, then score that choice under rho_true.

    This separates stopping-depth information error from threshold construction.
    The exact-rho optimum is retained only as a retrospective regret reference.
    """
    if not (0.0 < rho_true <= 1.0 and 0.0 < rho_est <= 1.0):
        raise ValueError("rho_true and rho_est must lie in (0,1]")
    est_sel = select_k_resource_efficiency(
        rho_est, eps_model, d_prep, d_iter, prep_cost, oracle_cost, diffusion_cost, k_max
    )
    oracle_sel = select_k_resource_efficiency(
        rho_true, eps_model, d_prep, d_iter, prep_cost, oracle_cost, diffusion_cost, k_max
    )
    k = int(est_sel["k"])
    actual_p = effective_probability(rho_true, k, eps_model, d_prep, d_iter)
    actual_cost = prep_cost + k * (oracle_cost + diffusion_cost)
    actual_score = actual_p / actual_cost
    retention = actual_score / oracle_sel["score"] if oracle_sel["score"] > 0 else 1.0
    return {
        "k_selected_from_rho_est": k,
        "k_oracle_informed": int(oracle_sel["k"]),
        "delta_k": k - int(oracle_sel["k"]),
        "p_target_eff_actual": float(actual_p),
        "normalized_cost_actual": float(actual_cost),
        "resource_score_actual": float(actual_score),
        "resource_score_oracle_informed": float(oracle_sel["score"]),
        "resource_score_retention": float(retention),
    }


def rho_estimation_robustness(suite: Iterable[MaxCutInstance]) -> list[dict]:
    """Stopping-depth sensitivity to multiplicative marked-fraction error.

    Thresholds are operational (C*-independent). Exact rho is used only to generate
    retrospective ground truth and regret. The selector receives rho_est.
    """
    rows: list[dict] = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            rho_true = float(spec["rho_tau_exact_validation"])
            if rho_true <= 0:
                continue
            for eps in (0.0, 0.001):
                for oracle_cost in (1.0, 4.0):
                    for factor in RHO_ESTIMATE_FACTORS:
                        rho_est = min(1.0, max(1e-15, rho_true * factor))
                        out = select_k_with_rho_estimate(
                            rho_true, rho_est, eps, 30.0, 30.0, 1.0, oracle_cost, 1.0, 80
                        )
                        rows.append({
                            "instance_id": inst.instance_id,
                            "n": inst.n,
                            "operational_level": level,
                            "threshold": spec["threshold"],
                            "rho_true_exact_validation": rho_true,
                            "rho_estimate_factor": factor,
                            "rho_estimate_used": rho_est,
                            "eps_model": eps,
                            "oracle_cost_norm": oracle_cost,
                            **out,
                            "evidence_label": "estimated-rho stopping robustness; exact rho used only for retrospective regret",
                        })
    return rows



ORACLE_ATTENUATION_LEVELS = (0.0, 1e-5, 5e-5, 1e-4, 5e-4)
FIXED_OVERHEAD_ORACLE_RATIOS = (0.0, 0.05, 0.10, 0.25, 0.50, 1.0, 2.0)
BBHT_LAMBDA = 6.0 / 5.0
BBHT_EPS_LEVELS = (0.0, 1e-4)
BBHT_FIXED_OVERHEAD_RATIOS = (0.0, 0.25)
RESOURCE_TOFFOLI_WEIGHTS = (1.0, 4.0, 6.0, 10.0)
RESOURCE_SCALARIZATION_EPS_LEVELS = (0.0, 1e-4)
RESOURCE_SCALARIZATION_CANONICAL_FIXED_RATIOS = (0.0, 0.10, 0.25, 0.50)


def maxcut_threshold_oracle_resource_model(inst: MaxCutInstance, threshold: int) -> dict:
    """Architecture-informed logical resource model for a reversible threshold oracle.

    Template: reusable edge-parity ancilla -> controlled constant accumulation ->
    threshold comparison/phase flag -> complete uncomputation.  Counts are logical
    bookkeeping estimates for a ripple-style construction, not transpiled backend metrics.

    A b-bit controlled constant adder is modeled with 2b Toffoli, 4b CNOT, and
    logical depth 2b.  The comparator uses the same order per compute/uncompute pass.
    Each Toffoli contributes six units to ``gate_equivalent`` only as a transparent
    decomposition-weight convention; this is not a native-gate or timing claim.
    """
    if threshold < 0:
        raise ValueError('threshold must be non-negative')
    m = inst.n_edges
    total_weight = int(sum(w for _, _, w in inst.edges))
    b = max(1, int(math.ceil(math.log2(total_weight + 1))))

    # Accumulation + uncomputation: two passes over all m edges.
    toffoli_edges = 4 * m * b
    cnot_edges = 8 * m * b + 8 * m
    depth_edges = 4 * m * b + 8 * m

    # Comparator compute + uncompute around a phase mark.
    toffoli_cmp = 4 * b
    cnot_cmp = 8 * b
    depth_cmp = 4 * b

    oracle_toffoli = toffoli_edges + toffoli_cmp
    oracle_cnot = cnot_edges + cnot_cmp
    oracle_single = 1  # phase mark; arithmetic one-qubit gates are not expanded here
    oracle_depth = depth_edges + depth_cmp + 1

    # Standard n-qubit diffusion logical template.  This remains architecture-level.
    diffusion_toffoli = max(0, 2 * inst.n - 4)
    diffusion_cnot = 4 * inst.n
    diffusion_single = 4 * inst.n + 1
    diffusion_depth = max(1, 2 * inst.n - 3) + 4

    # Transparent mixed logical-gate bookkeeping metric, not a compiled count.
    oracle_gate_equiv = oracle_single + oracle_cnot + 6 * oracle_toffoli
    diffusion_gate_equiv = diffusion_single + diffusion_cnot + 6 * diffusion_toffoli
    prep_gate_equiv = inst.n  # H on every data qubit
    prep_depth = 1

    ancilla = b + 3  # accumulator plus reusable parity/carry/flag work qubits
    return {
        'threshold': int(threshold),
        'n_edges': int(m),
        'total_edge_weight': total_weight,
        'accumulator_bits': b,
        'data_qubits': inst.n,
        'ancilla_qubits_model': ancilla,
        'total_logical_qubits_model': inst.n + ancilla,
        'oracle_toffoli_model': int(oracle_toffoli),
        'oracle_cnot_model': int(oracle_cnot),
        'oracle_single_qubit_model': int(oracle_single),
        'oracle_logical_depth_model': int(oracle_depth),
        'oracle_gate_equivalent_model': float(oracle_gate_equiv),
        'diffusion_toffoli_model': int(diffusion_toffoli),
        'diffusion_cnot_model': int(diffusion_cnot),
        'diffusion_single_qubit_model': int(diffusion_single),
        'diffusion_logical_depth_model': int(diffusion_depth),
        'diffusion_gate_equivalent_model': float(diffusion_gate_equiv),
        'prep_gate_equivalent_model': float(prep_gate_equiv),
        'prep_logical_depth_model': int(prep_depth),
        'iteration_logical_depth_model': int(oracle_depth + diffusion_depth),
        'iteration_gate_equivalent_model': float(oracle_gate_equiv + diffusion_gate_equiv),
        'count_model_label': 'ripple-style logical template; architecture-informed, not compiled',
    }


def select_k_architecture_coupled(
    rho: float,
    eps_per_logical_depth: float,
    resource_model: dict,
    k_max: int = 80,
    fixed_overhead_gate_equiv: float = 0.0,
) -> dict:
    """Select k with logical resource, attenuation, and optional fixed per-trial overhead.

    ``fixed_overhead_gate_equiv`` is a synthetic sensitivity coordinate shared by all
    k choices for one trial.  It may represent control/readout/verification/handoff
    work only as a bookkeeping stress test; it is not a measured backend cost.
    """
    if eps_per_logical_depth < 0:
        raise ValueError('eps_per_logical_depth must be non-negative')
    if fixed_overhead_gate_equiv < 0:
        raise ValueError('fixed_overhead_gate_equiv must be non-negative')
    if not (0.0 < rho <= 1.0):
        raise ValueError('rho must lie in (0,1]')
    prep_cost = float(resource_model['prep_gate_equivalent_model'])
    iter_cost = float(resource_model['iteration_gate_equivalent_model'])
    prep_depth = float(resource_model['prep_logical_depth_model'])
    iter_depth = float(resource_model['iteration_logical_depth_model'])
    rows = []
    for k in range(k_max + 1):
        ideal = grover_probability(rho, k)
        depth = prep_depth + k * iter_depth
        survival = math.exp(-eps_per_logical_depth * depth)
        p_eff = ideal * survival
        cost = fixed_overhead_gate_equiv + prep_cost + k * iter_cost
        score = p_eff / cost
        rows.append((k, ideal, survival, p_eff, cost, depth, score))
    best = max(rows, key=lambda x: (x[6], -x[0]))
    return {
        'k': int(best[0]),
        'p_ideal': float(best[1]),
        'survival_model': float(best[2]),
        'p_eff': float(best[3]),
        'gate_equivalent_cost': float(best[4]),
        'logical_depth_model': float(best[5]),
        'score': float(best[6]),
        'fixed_overhead_gate_equiv': float(fixed_overhead_gate_equiv),
        'rows': rows,
    }



def bbht_stage_widths(state_count: int, growth: float = BBHT_LAMBDA) -> list[int]:
    """Return the finite BBHT growth schedule through the saturated stage.

    The schedule follows Boyer--Brassard--Hoyer--Tapp: m starts at one, an
    integer j is drawn uniformly from the non-negative integers strictly below
    m, and after a failed trial m <- min(growth*m, sqrt(N)).  The final returned
    width is the saturated stage, which is then repeated until success.
    """
    if state_count <= 0:
        raise ValueError('state_count must be positive')
    if not (1.0 < growth < 4.0 / 3.0):
        raise ValueError('BBHT growth must lie strictly between 1 and 4/3')
    cap = math.sqrt(float(state_count))
    m = 1.0
    widths: list[int] = []
    while True:
        width = max(1, int(math.ceil(m - 1e-12)))
        widths.append(width)
        if m >= cap - 1e-12:
            break
        m = min(growth * m, cap)
    return widths


def bbht_expected_architecture_cost(
    rho: float,
    state_count: int,
    resource_model: dict,
    eps_per_logical_depth: float = 0.0,
    fixed_overhead_gate_equiv: float = 0.0,
    growth: float = BBHT_LAMBDA,
) -> dict:
    """Exact expectation of the BBHT unknown-solution-count schedule.

    The schedule itself never receives ``rho``; exact rho is supplied only here
    to evaluate the expected success/resource cost retrospectively on Tier-I
    ground truth.  Before saturation, one trial is taken at each growth stage.
    At the saturated stage the same randomized-j trial is repeated until success,
    allowing an exact geometric-tail expectation rather than Monte Carlo noise.
    """
    if not (0.0 < rho <= 1.0):
        raise ValueError('rho must lie in (0,1]')
    if eps_per_logical_depth < 0 or fixed_overhead_gate_equiv < 0:
        raise ValueError('attenuation and fixed overhead must be non-negative')
    prep_cost = float(resource_model['prep_gate_equivalent_model'])
    iter_cost = float(resource_model['iteration_gate_equivalent_model'])
    prep_depth = float(resource_model['prep_logical_depth_model'])
    iter_depth = float(resource_model['iteration_logical_depth_model'])
    widths = bbht_stage_widths(state_count, growth=growth)

    expected_cost = 0.0
    expected_trials = 0.0
    expected_iterations = 0.0
    survival = 1.0
    stage_rows: list[dict] = []

    for stage_index, width in enumerate(widths):
        js = np.arange(width, dtype=int)
        probs = np.asarray([
            grover_probability(rho, int(j))
            * math.exp(-eps_per_logical_depth * (prep_depth + int(j) * iter_depth))
            for j in js
        ], dtype=float)
        costs = np.asarray([
            fixed_overhead_gate_equiv + prep_cost + int(j) * iter_cost
            for j in js
        ], dtype=float)
        p_bar = float(np.mean(probs))
        avg_cost = float(np.mean(costs))
        avg_j = float(np.mean(js))
        if p_bar <= 0.0:
            raise RuntimeError('BBHT saturated-stage success probability is zero')
        saturated = stage_index == len(widths) - 1
        if saturated:
            expected_cost += survival * avg_cost / p_bar
            expected_trials += survival / p_bar
            expected_iterations += survival * avg_j / p_bar
            stage_rows.append({
                'stage': stage_index, 'width': width, 'saturated': True,
                'survival_before': survival, 'mean_success_probability': p_bar,
                'mean_trial_cost': avg_cost, 'mean_grover_iterations': avg_j,
            })
            survival = 0.0
            break
        expected_cost += survival * avg_cost
        expected_trials += survival
        expected_iterations += survival * avg_j
        stage_rows.append({
            'stage': stage_index, 'width': width, 'saturated': False,
            'survival_before': survival, 'mean_success_probability': p_bar,
            'mean_trial_cost': avg_cost, 'mean_grover_iterations': avg_j,
        })
        survival *= (1.0 - p_bar)

    return {
        'growth_lambda': float(growth),
        'growth_stages_including_saturation': len(widths),
        'saturated_width': int(widths[-1]),
        'expected_trials_to_success': float(expected_trials),
        'expected_grover_iterations_to_success': float(expected_iterations),
        'expected_gate_equivalent_to_success': float(expected_cost),
        'eventual_success_probability': 1.0,
        'stage_rows': stage_rows,
    }


def bbht_operational_rows(
    suite: Iterable[MaxCutInstance],
    scope: str,
    eps_levels: tuple[float, ...] = BBHT_EPS_LEVELS,
    fixed_overhead_ratios: tuple[float, ...] = BBHT_FIXED_OVERHEAD_RATIOS,
) -> list[dict]:
    """Compare BBHT, uniform repetition, and oracle-informed exact-rho selection."""
    rows: list[dict] = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            rho = float(spec['rho_tau_exact_validation'])
            if rho <= 0.0:
                continue
            rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
            for eps in eps_levels:
                for ratio in fixed_overhead_ratios:
                    fixed = float(ratio) * float(rm['oracle_gate_equivalent_model'])
                    bbht = bbht_expected_architecture_cost(
                        rho, inst.state_count, rm, eps_per_logical_depth=float(eps),
                        fixed_overhead_gate_equiv=fixed, growth=BBHT_LAMBDA,
                    )
                    p_uniform = rho * math.exp(-float(eps) * float(rm['prep_logical_depth_model']))
                    uniform_resource = (fixed + float(rm['prep_gate_equivalent_model'])) / p_uniform
                    oracle = select_k_architecture_coupled(
                        rho, float(eps), rm, k_max=80, fixed_overhead_gate_equiv=fixed
                    )
                    oracle_resource = float(oracle['gate_equivalent_cost']) / float(oracle['p_eff'])
                    rows.append({
                        'scope': str(scope),
                        'instance_id': inst.instance_id,
                        'n': inst.n,
                        'family': inst.family,
                        'operational_level': level,
                        'threshold': spec['threshold'],
                        'rho_tau_exact_validation': rho,
                        'bbht_schedule_uses_rho': False,
                        'bbht_lambda': BBHT_LAMBDA,
                        'eps_per_logical_depth_model': float(eps),
                        'fixed_overhead_ratio_to_oracle': float(ratio),
                        'expected_bbht_trials_to_success': bbht['expected_trials_to_success'],
                        'expected_bbht_grover_iterations_to_success': bbht['expected_grover_iterations_to_success'],
                        'bbht_expected_resource_per_target_hit_model': bbht['expected_gate_equivalent_to_success'],
                        'uniform_expected_resource_per_target_hit_model': uniform_resource,
                        'oracle_informed_k_star': int(oracle['k']),
                        'oracle_informed_expected_resource_per_target_hit_model': oracle_resource,
                        'bbht_over_uniform_resource_ratio': bbht['expected_gate_equivalent_to_success'] / uniform_resource,
                        'bbht_over_oracle_informed_resource_ratio': bbht['expected_gate_equivalent_to_success'] / oracle_resource,
                        'evidence_label': 'BBHT schedule does not consume rho; exact rho used only for retrospective expected-cost evaluation under the logical model',
                    })
    return rows

def bbht_summary_rows(rows: list[dict]) -> list[dict]:
    """Compact descriptive summary of the BBHT resource comparison."""
    out: list[dict] = []
    scopes = sorted({str(r['scope']) for r in rows})
    eps_values = sorted({float(r['eps_per_logical_depth_model']) for r in rows})
    fixed_values = sorted({float(r['fixed_overhead_ratio_to_oracle']) for r in rows})
    for scope in scopes:
        for eps in eps_values:
            for fixed in fixed_values:
                rr = [
                    r for r in rows
                    if str(r['scope']) == scope
                    and abs(float(r['eps_per_logical_depth_model']) - eps) < 1e-15
                    and abs(float(r['fixed_overhead_ratio_to_oracle']) - fixed) < 1e-15
                ]
                if not rr:
                    continue
                b_u = np.asarray([float(r['bbht_over_uniform_resource_ratio']) for r in rr])
                b_o = np.asarray([float(r['bbht_over_oracle_informed_resource_ratio']) for r in rr])
                it = np.asarray([float(r['expected_bbht_grover_iterations_to_success']) for r in rr])
                out.append({
                    'scope': scope,
                    'eps_per_logical_depth_model': eps,
                    'fixed_overhead_ratio_to_oracle': fixed,
                    'feasible_threshold_conditions': len(rr),
                    'median_bbht_over_uniform_resource_ratio': float(np.median(b_u)),
                    'q1_bbht_over_uniform_resource_ratio': float(np.quantile(b_u, 0.25)),
                    'q3_bbht_over_uniform_resource_ratio': float(np.quantile(b_u, 0.75)),
                    'bbht_better_than_uniform_fraction': float(np.mean(b_u < 1.0)),
                    'median_bbht_over_oracle_informed_resource_ratio': float(np.median(b_o)),
                    'median_expected_bbht_grover_iterations': float(np.median(it)),
                    'evidence_label': 'descriptive BBHT unknown-rho comparison; exact rho used only for retrospective expected-cost evaluation',
                })
    return out




def reweight_resource_model(resource_model: dict, toffoli_weight: float) -> dict:
    """Recompute the mixed logical gate-equivalent score with a new Toffoli weight.

    Raw logical Toffoli/CNOT/single-qubit counts and logical depths are unchanged.
    Only the scalar bookkeeping projection is changed, allowing direct sensitivity
    analysis of the canonical factor-six convention.
    """
    if toffoli_weight <= 0:
        raise ValueError('toffoli_weight must be positive')
    out = dict(resource_model)
    oracle = (
        float(resource_model['oracle_single_qubit_model'])
        + float(resource_model['oracle_cnot_model'])
        + float(toffoli_weight) * float(resource_model['oracle_toffoli_model'])
    )
    diffusion = (
        float(resource_model['diffusion_single_qubit_model'])
        + float(resource_model['diffusion_cnot_model'])
        + float(toffoli_weight) * float(resource_model['diffusion_toffoli_model'])
    )
    out['oracle_gate_equivalent_model'] = float(oracle)
    out['diffusion_gate_equivalent_model'] = float(diffusion)
    out['iteration_gate_equivalent_model'] = float(oracle + diffusion)
    out['toffoli_weight_convention'] = float(toffoli_weight)
    return out


def resource_scalarization_sensitivity_rows(
    suite: Iterable[MaxCutInstance],
    scope: str,
    toffoli_weights: tuple[float, ...] = RESOURCE_TOFFOLI_WEIGHTS,
    eps_levels: tuple[float, ...] = RESOURCE_SCALARIZATION_EPS_LEVELS,
    canonical_fixed_ratios: tuple[float, ...] = RESOURCE_SCALARIZATION_CANONICAL_FIXED_RATIOS,
) -> list[dict]:
    """Sensitivity of architecture selection to the Toffoli scalarization weight.

    Fixed overhead is anchored to the canonical alpha=6 oracle cost so that changing
    alpha does not silently rescale the external fixed-work assumption itself.
    """
    rows: list[dict] = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            rho = float(spec['rho_tau_exact_validation'])
            if rho <= 0.0:
                continue
            canonical = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
            canonical_oracle = float(canonical['oracle_gate_equivalent_model'])
            for alpha in toffoli_weights:
                rm = reweight_resource_model(canonical, float(alpha))
                be_reweighted = architecture_fixed_overhead_break_even_ratio(
                    rho, 0.0, rm, k_max=80
                )
                be_canonical = (
                    be_reweighted * float(rm['oracle_gate_equivalent_model']) / canonical_oracle
                    if math.isfinite(be_reweighted) else math.inf
                )
                for eps in eps_levels:
                    # recompute the attenuation-specific break-even boundary
                    be_eps = architecture_fixed_overhead_break_even_ratio(rho, float(eps), rm, k_max=80)
                    be_eps_canonical = (
                        be_eps * float(rm['oracle_gate_equivalent_model']) / canonical_oracle
                        if math.isfinite(be_eps) else math.inf
                    )
                    for chi6 in canonical_fixed_ratios:
                        fixed = float(chi6) * canonical_oracle
                        out = select_k_architecture_coupled(
                            rho, float(eps), rm, k_max=80, fixed_overhead_gate_equiv=fixed
                        )
                        rows.append({
                            'scope': str(scope),
                            'instance_id': inst.instance_id,
                            'n': inst.n,
                            'family': inst.family,
                            'operational_level': level,
                            'threshold': spec['threshold'],
                            'rho_tau_exact_validation': rho,
                            'toffoli_weight_alpha': float(alpha),
                            'eps_per_logical_depth_model': float(eps),
                            'fixed_overhead_ratio_to_canonical_alpha6_oracle': float(chi6),
                            'fixed_overhead_gate_equivalent_model': fixed,
                            'effective_fixed_overhead_ratio_to_reweighted_oracle': fixed / float(rm['oracle_gate_equivalent_model']),
                            'break_even_fixed_overhead_ratio_to_canonical_alpha6_oracle': be_eps_canonical,
                            'k_star': int(out['k']),
                            'p_target_eff': float(out['p_eff']),
                            'gate_equivalent_cost_at_k': float(out['gate_equivalent_cost']),
                            'oracle_gate_equivalent_reweighted': float(rm['oracle_gate_equivalent_model']),
                            'iteration_gate_equivalent_reweighted': float(rm['iteration_gate_equivalent_model']),
                            'canonical_alpha6_oracle_gate_equivalent': canonical_oracle,
                            'evidence_label': 'Toffoli-weight scalarization sensitivity; raw logical counts/depth unchanged; not a native-gate claim',
                        })
    return rows


def resource_scalarization_summary_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    scopes = sorted({str(r['scope']) for r in rows})
    alphas = sorted({float(r['toffoli_weight_alpha']) for r in rows})
    eps_values = sorted({float(r['eps_per_logical_depth_model']) for r in rows})
    fixed_values = sorted({float(r['fixed_overhead_ratio_to_canonical_alpha6_oracle']) for r in rows})
    for scope in scopes:
        for eps in eps_values:
            for alpha in alphas:
                # Break-even is independent of the enumerated fixed-overhead coordinate.
                base = [r for r in rows if str(r['scope']) == scope and abs(float(r['eps_per_logical_depth_model'])-eps)<1e-15 and abs(float(r['toffoli_weight_alpha'])-alpha)<1e-15]
                bevals = np.asarray([float(r['break_even_fixed_overhead_ratio_to_canonical_alpha6_oracle']) for r in base[::len(fixed_values)]]) if base else np.asarray([])
                for fixed in fixed_values:
                    rr = [r for r in base if abs(float(r['fixed_overhead_ratio_to_canonical_alpha6_oracle'])-fixed)<1e-15]
                    if not rr:
                        continue
                    ks = np.asarray([int(r['k_star']) for r in rr])
                    out.append({
                        'scope': scope,
                        'eps_per_logical_depth_model': eps,
                        'toffoli_weight_alpha': alpha,
                        'fixed_overhead_ratio_to_canonical_alpha6_oracle': fixed,
                        'feasible_threshold_conditions': len(rr),
                        'nonzero_k_fraction': float(np.mean(ks > 0)),
                        'median_k_star': float(np.median(ks)),
                        'median_break_even_ratio_to_canonical_alpha6_oracle': float(np.median([float(r['break_even_fixed_overhead_ratio_to_canonical_alpha6_oracle']) for r in rr])),
                        'evidence_label': 'descriptive scalarization robustness summary; alpha changes bookkeeping only',
                    })
    return out

def oracle_resource_rows(suite: Iterable[MaxCutInstance]) -> list[dict]:
    """Logical oracle-resource ledger for every operational threshold."""
    rows = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
            rows.append({
                'instance_id': inst.instance_id,
                'n': inst.n,
                'density_target': inst.density_target,
                'operational_level': level,
                'feasible_exact_validation': spec['feasible_exact_validation'],
                'rho_tau_exact_validation': spec['rho_tau_exact_validation'],
                **rm,
            })
    return rows


def coupled_oracle_depth_sensitivity(suite: Iterable[MaxCutInstance]) -> list[dict]:
    """Coupled architecture-informed oracle cost/depth sensitivity on feasible targets."""
    rows = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            rho = float(spec['rho_tau_exact_validation'])
            if rho <= 0:
                continue
            rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
            for eps in ORACLE_ATTENUATION_LEVELS:
                out = select_k_architecture_coupled(rho, eps, rm, k_max=80)
                p0 = grover_probability(rho, 0) * math.exp(-eps * rm['prep_logical_depth_model'])
                base_resource_per_hit = rm['prep_gate_equivalent_model'] / p0
                selected_resource_per_hit = out['gate_equivalent_cost'] / out['p_eff']
                rows.append({
                    'instance_id': inst.instance_id,
                    'n': inst.n,
                    'density_target': inst.density_target,
                    'operational_level': level,
                    'threshold': spec['threshold'],
                    'rho_tau_exact_validation': rho,
                    'eps_per_logical_depth_model': eps,
                    'k_star': out['k'],
                    'p_target_eff': out['p_eff'],
                    'survival_model_at_k': out['survival_model'],
                    'logical_depth_model_at_k': out['logical_depth_model'],
                    'gate_equivalent_cost_at_k': out['gate_equivalent_cost'],
                    'resource_per_target_hit_model': selected_resource_per_hit,
                    'eta_arch': selected_resource_per_hit / base_resource_per_hit,
                    'oracle_logical_depth_model': rm['oracle_logical_depth_model'],
                    'diffusion_logical_depth_model': rm['diffusion_logical_depth_model'],
                    'iteration_logical_depth_model': rm['iteration_logical_depth_model'],
                    'oracle_gate_equivalent_model': rm['oracle_gate_equivalent_model'],
                    'diffusion_gate_equivalent_model': rm['diffusion_gate_equivalent_model'],
                    'total_logical_qubits_model': rm['total_logical_qubits_model'],
                    'evidence_label': 'architecture-informed logical resource model; not compiled or hardware measured',
                })
    return rows

def architecture_fixed_overhead_break_even_ratio(
    rho: float,
    eps_per_logical_depth: float,
    resource_model: dict,
    k_max: int = 80,
) -> float:
    """Exact fixed-overhead/oracle-cost ratio where some k>0 first beats k=0.

    This follows algebraically from comparing the probability-per-resource score of
    k>0 with k=0 under the same fixed per-trial overhead.  ``inf`` means no tested
    k can improve the effective hit probability enough to cross the baseline.
    """
    if eps_per_logical_depth < 0:
        raise ValueError('eps_per_logical_depth must be non-negative')
    if not (0.0 < rho <= 1.0):
        raise ValueError('rho must lie in (0,1]')
    prep = float(resource_model['prep_gate_equivalent_model'])
    iter_cost = float(resource_model['iteration_gate_equivalent_model'])
    oracle_cost = float(resource_model['oracle_gate_equivalent_model'])
    d0 = float(resource_model['prep_logical_depth_model'])
    di = float(resource_model['iteration_logical_depth_model'])
    p0 = grover_probability(rho, 0) * math.exp(-eps_per_logical_depth * d0)
    candidates = []
    for k in range(1, k_max + 1):
        pk = grover_probability(rho, k) * math.exp(-eps_per_logical_depth * (d0 + k * di))
        if pk <= p0 + 1e-15:
            continue
        required = p0 * k * iter_cost / (pk - p0) - prep
        candidates.append(max(0.0, required) / oracle_cost)
    return float(min(candidates)) if candidates else math.inf



def dense_operational_lambda_rows(
    suite: Iterable[MaxCutInstance],
    tier: str,
    levels: tuple[float, ...] = DENSE_OPERATIONAL_LEVELS,
) -> list[dict]:
    """Dense operational-threshold sweep used to audit the three declared levels.

    The sweep uses the same C*-independent construction at every lambda. Exact C*,
    rho_tau, and resource quantities are retrospective exact-tier diagnostics only.
    """
    rows: list[dict] = []
    for inst in suite:
        for level in levels:
            spec = operational_threshold_spec(inst, float(level))
            row = {
                "tier": tier,
                "instance_id": inst.instance_id,
                "n": inst.n,
                "density_target": inst.density_target,
                "seed": inst.seed,
                "operational_level": float(level),
                **spec,
                "declared_level": any(abs(float(level) - x) < 1e-12 for x in OPERATIONAL_LEVELS),
            }
            rho = float(spec["rho_tau_exact_validation"])
            if rho > 0:
                rm = maxcut_threshold_oracle_resource_model(inst, int(spec["threshold"]))
                out0 = select_k_architecture_coupled(rho, 0.0, rm, k_max=80)
                row.update({
                    "k_star_zero_fixed_zero_attenuation": int(out0["k"]),
                    "break_even_fixed_overhead_ratio_to_oracle_zero_attenuation": architecture_fixed_overhead_break_even_ratio(rho, 0.0, rm, k_max=80),
                })
            else:
                row.update({
                    "k_star_zero_fixed_zero_attenuation": "",
                    "break_even_fixed_overhead_ratio_to_oracle_zero_attenuation": "",
                })
            row["evidence_label"] = "dense operational-lambda audit; exact retrospective validation, not population inference"
            rows.append(row)
    return rows


def dense_operational_lambda_summary_rows(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    tiers = sorted({str(r["tier"]) for r in rows})
    levels = sorted({float(r["operational_level"]) for r in rows})
    for tier in tiers:
        for level in levels:
            rr = [r for r in rows if str(r["tier"]) == tier and abs(float(r["operational_level"]) - level) < 1e-12]
            feas = [r for r in rr if bool(r["feasible_exact_validation"])]
            be = [float(r["break_even_fixed_overhead_ratio_to_oracle_zero_attenuation"]) for r in feas if r["break_even_fixed_overhead_ratio_to_oracle_zero_attenuation"] != "" and math.isfinite(float(r["break_even_fixed_overhead_ratio_to_oracle_zero_attenuation"]))]
            out.append({
                "tier": tier,
                "operational_level": level,
                "declared_level": any(abs(level - x) < 1e-12 for x in OPERATIONAL_LEVELS),
                "instances": len(rr),
                "feasible_count": len(feas),
                "feasible_fraction": len(feas) / len(rr) if rr else math.nan,
                "median_tau_over_Cstar_feasible": float(np.median([float(r["realized_quality_ratio_exact_validation"]) for r in feas])) if feas else math.nan,
                "median_rho_tau_feasible": float(np.median([float(r["rho_tau_exact_validation"]) for r in feas])) if feas else math.nan,
                "zero_fixed_zero_attenuation_nonzero_k_fraction": float(np.mean([int(r["k_star_zero_fixed_zero_attenuation"]) > 0 for r in feas])) if feas else math.nan,
                "median_break_even_fixed_overhead_ratio_to_oracle": float(np.median(be)) if be else math.nan,
                "evidence_label": "dense lambda summary; descriptive exact-tier sensitivity",
            })
    return out


def fixed_overhead_sensitivity_rows(
    suite: Iterable[MaxCutInstance],
    scope: str,
    overhead_ratios: tuple[float, ...] = FIXED_OVERHEAD_ORACLE_RATIOS,
    eps_levels: tuple[float, ...] = ORACLE_ATTENUATION_LEVELS,
) -> list[dict]:
    """Stress-test the architecture selector against fixed per-trial overhead."""
    rows: list[dict] = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            rho = float(spec['rho_tau_exact_validation'])
            if rho <= 0:
                continue
            rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
            for eps in eps_levels:
                be_ratio = architecture_fixed_overhead_break_even_ratio(rho, eps, rm, k_max=80)
                for ratio in overhead_ratios:
                    fixed = float(ratio) * float(rm['oracle_gate_equivalent_model'])
                    out = select_k_architecture_coupled(
                        rho, eps, rm, k_max=80, fixed_overhead_gate_equiv=fixed
                    )
                    p0 = grover_probability(rho, 0) * math.exp(-eps * rm['prep_logical_depth_model'])
                    base_resource_per_hit = (fixed + rm['prep_gate_equivalent_model']) / p0
                    selected_resource_per_hit = out['gate_equivalent_cost'] / out['p_eff']
                    rows.append({
                        'scope': str(scope),
                        'instance_id': inst.instance_id,
                        'n': inst.n,
                        'family': inst.family,
                        'operational_level': level,
                        'threshold': spec['threshold'],
                        'rho_tau_exact_validation': rho,
                        'eps_per_logical_depth_model': float(eps),
                        'fixed_overhead_ratio_to_oracle': float(ratio),
                        'fixed_overhead_gate_equivalent_model': fixed,
                        'break_even_fixed_overhead_ratio_to_oracle': be_ratio,
                        'k_star': out['k'],
                        'p_target_eff': out['p_eff'],
                        'gate_equivalent_cost_at_k': out['gate_equivalent_cost'],
                        'resource_per_target_hit_model': selected_resource_per_hit,
                        'eta_arch_fixed': selected_resource_per_hit / base_resource_per_hit,
                        'oracle_gate_equivalent_model': rm['oracle_gate_equivalent_model'],
                        'iteration_gate_equivalent_model': rm['iteration_gate_equivalent_model'],
                        'evidence_label': 'synthetic fixed-overhead sensitivity on architecture-informed logical model; not measured backend cost',
                    })
    return rows


def large_searchspace_tier() -> list[dict]:
    """Analytical-only threshold-event scaling tier.

    ``target_event_count`` is the multiplicity of states satisfying an abstract quality
    threshold in a 2**n search space.  These rows are not Max-Cut ground truth and do not
    assume knowledge of optimum bitstrings; they isolate selector behavior as a target
    event becomes rarer.
    """
    rows: list[dict] = []
    for n in (12, 16, 20, 24):
        for target_event_count in (1, 4, 16):
            rho = target_event_count / float(1 << n)
            if rho > 1.0:
                continue
            theta = math.asin(math.sqrt(rho))
            first_peak = math.pi / (4.0 * theta) - 0.5
            k_max = max(50, int(math.ceil(1.20 * first_peak)))
            for eps in np.linspace(0.0, 0.003, 13):
                for oracle_cost in np.geomspace(0.5, 16.0, 17):
                    sel = select_k_resource_efficiency(
                        rho, float(eps), 30.0, 30.0, 1.0, float(oracle_cost), 1.0, k_max
                    )
                    rows.append({
                        "model_n": n,
                        "state_count": 1 << n,
                        "target_event_count": target_event_count,
                        "rho_target_model": rho,
                        "first_peak_continuous": first_peak,
                        "eps_model": float(eps),
                        "oracle_cost_norm": float(oracle_cost),
                        "k_star": sel["k"],
                        "p_eff": sel["p_eff"],
                        "normalized_cost": sel["normalized_cost"],
                        "evidence_label": "analytical threshold-event sensitivity; not Max-Cut ground truth",
                    })
    return rows

def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path.name}")
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    suite = build_exact_suite()
    coverage_suite = build_coverage_suite()
    connected_validation_suite = build_connected_validation_suite()

    primary_graph_diagnostics = graph_diagnostics_rows(suite, "primary")
    coverage_graph_diagnostics = graph_diagnostics_rows(coverage_suite, "coverage")
    connected_graph_diagnostics = graph_diagnostics_rows(connected_validation_suite, "connected_validation")
    write_csv(RESULTS / "primary_graph_diagnostics.csv", primary_graph_diagnostics)
    write_csv(RESULTS / "coverage_graph_diagnostics.csv", coverage_graph_diagnostics)
    write_csv(RESULTS / "connected_validation_graph_diagnostics.csv", connected_graph_diagnostics)

    connected_graphs = connected_validation_graph_rows(connected_validation_suite)
    connected_gt = connected_validation_ground_truth_rows(connected_validation_suite)
    connected_thresholds = connected_validation_operational_threshold_rows(connected_validation_suite)
    connected_coupled = connected_validation_coupled_oracle_rows(connected_validation_suite)
    write_csv(DATA / "connected_validation_graphs.csv", connected_graphs)
    write_csv(RESULTS / "connected_validation_ground_truth.csv", connected_gt)
    write_csv(RESULTS / "connected_validation_operational_thresholds.csv", connected_thresholds)
    write_csv(RESULTS / "connected_validation_coupled_oracle.csv", connected_coupled)

    # Canonical Max-Cut classical reference: numerically certified GW SDP relaxation
    # plus deterministic-seed random-hyperplane rounding.  Exact C* is used only
    # retrospectively for scoring the exact tiers.
    gw_primary_rows = gw_sdp_rows(suite, "primary")
    gw_connected_rows = gw_sdp_rows(connected_validation_suite, "connected_validation")
    gw_summary = gw_sdp_summary_rows(gw_primary_rows + gw_connected_rows)
    write_csv(RESULTS / "gw_sdp_primary.csv", gw_primary_rows)
    write_csv(RESULTS / "gw_sdp_connected_validation.csv", gw_connected_rows)
    write_csv(RESULTS / "gw_sdp_summary.csv", gw_summary)

    # Unknown-solution-count search: BBHT schedule never receives rho; exact Tier-I rho
    # is used only to evaluate expected resource-to-success retrospectively.
    bbht_primary_rows = bbht_operational_rows(suite, "primary")
    bbht_connected_rows = bbht_operational_rows(connected_validation_suite, "connected_validation")
    bbht_summary = bbht_summary_rows(bbht_primary_rows + bbht_connected_rows)
    write_csv(RESULTS / "bbht_operational_primary.csv", bbht_primary_rows)
    write_csv(RESULTS / "bbht_operational_connected_validation.csv", bbht_connected_rows)
    write_csv(RESULTS / "bbht_summary.csv", bbht_summary)

    scalar_primary_rows = resource_scalarization_sensitivity_rows(suite, "primary")
    scalar_connected_rows = resource_scalarization_sensitivity_rows(connected_validation_suite, "connected_validation")
    scalar_summary = resource_scalarization_summary_rows(scalar_primary_rows + scalar_connected_rows)
    write_csv(RESULTS / "resource_scalarization_primary.csv", scalar_primary_rows)
    write_csv(RESULTS / "resource_scalarization_connected_validation.csv", scalar_connected_rows)
    write_csv(RESULTS / "resource_scalarization_summary.csv", scalar_summary)

    dense_lambda_primary = dense_operational_lambda_rows(suite, "primary")
    dense_lambda_connected = dense_operational_lambda_rows(connected_validation_suite, "connected_validation")
    dense_lambda_summary = dense_operational_lambda_summary_rows(dense_lambda_primary + dense_lambda_connected)
    write_csv(RESULTS / "dense_operational_lambda_primary.csv", dense_lambda_primary)
    write_csv(RESULTS / "dense_operational_lambda_connected_validation.csv", dense_lambda_connected)
    write_csv(RESULTS / "dense_operational_lambda_summary.csv", dense_lambda_summary)

    coverage_graphs = coverage_graph_rows(coverage_suite)
    coverage_gt = coverage_ground_truth_rows(coverage_suite)
    coverage_thresholds = coverage_operational_threshold_rows(coverage_suite)
    coverage_hill = coverage_hillclimb_rows(coverage_suite)
    coverage_coupled = coverage_coupled_oracle_rows(coverage_suite)
    coverage_summary = coverage_summary_rows(coverage_gt, coverage_thresholds, coverage_hill, coverage_coupled)
    write_csv(DATA / "coverage_graphs.csv", coverage_graphs)
    write_csv(RESULTS / "coverage_ground_truth.csv", coverage_gt)
    write_csv(RESULTS / "coverage_operational_thresholds.csv", coverage_thresholds)
    write_csv(RESULTS / "coverage_hillclimb.csv", coverage_hill)
    write_csv(RESULTS / "coverage_coupled_oracle.csv", coverage_coupled)
    write_csv(RESULTS / "coverage_summary.csv", coverage_summary)

    graph_rows: list[dict] = []
    gt_rows: list[dict] = []
    for inst in suite:
        for i, j, w in inst.edges:
            graph_rows.append(
                {
                    "instance_id": inst.instance_id,
                    "n": inst.n,
                    "density_target": inst.density_target,
                    "seed": inst.seed,
                    "i": i,
                    "j": j,
                    "w": w,
                }
            )
        gt_rows.append(
            {
                "instance_id": inst.instance_id,
                "n": inst.n,
                "n_edges": inst.n_edges,
                "density_target": inst.density_target,
                "seed": inst.seed,
                "C_star": inst.optimum,
                "M_opt": len(inst.optimum_states),
                "state_count": inst.state_count,
                "rho_opt": inst.marked_fraction,
                "optimum_states": json.dumps(list(inst.optimum_states)),
            }
        )
    write_csv(DATA / "maxcut_suite_graphs.csv", graph_rows)
    write_csv(RESULTS / "maxcut_ground_truth.csv", gt_rows)

    operational_threshold_rows: list[dict] = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            operational_threshold_rows.append({
                "instance_id": inst.instance_id,
                "n": inst.n,
                "density_target": inst.density_target,
                "seed": inst.seed,
                **spec,
            })
    write_csv(RESULTS / "operational_thresholds.csv", operational_threshold_rows)

    hill = [local_hillclimb(inst) for inst in suite]
    write_csv(RESULTS / "classical_hillclimb.csv", hill)

    classical_budgeted_raw, classical_budgeted_summary = run_budgeted_classical_suite(suite)
    write_csv(RESULTS / "classical_budgeted_runs.csv", classical_budgeted_raw)
    write_csv(RESULTS / "classical_budgeted_summary.csv", classical_budgeted_summary)

    classical_curve_raw, classical_curve_summary, classical_curve_aggregate = run_classical_budget_curve(suite)
    write_csv(RESULTS / "classical_budget_curve_runs.csv", classical_curve_raw)
    write_csv(RESULTS / "classical_budget_curve_summary.csv", classical_curve_summary)
    write_csv(RESULTS / "classical_budget_curve_aggregate.csv", classical_curve_aggregate)

    scaling_rows = simulator_scaling_tier()
    write_csv(RESULTS / "simulator_scaling.csv", scaling_rows)

    robustness_rows = dense_resource_robustness(suite)
    write_csv(RESULTS / "resource_robustness_grid.csv", robustness_rows)

    rho_robustness_rows = rho_estimation_robustness(suite)
    write_csv(RESULTS / "rho_estimation_robustness.csv", rho_robustness_rows)

    oracle_rows = oracle_resource_rows(suite)
    write_csv(RESULTS / "oracle_resource_model.csv", oracle_rows)

    coupled_rows = coupled_oracle_depth_sensitivity(suite)
    write_csv(RESULTS / "coupled_oracle_depth_sensitivity.csv", coupled_rows)

    fixed_overhead_rows = (
        fixed_overhead_sensitivity_rows(suite, "primary")
        + fixed_overhead_sensitivity_rows(coverage_suite, "coverage")
    )
    write_csv(RESULTS / "fixed_overhead_sensitivity.csv", fixed_overhead_rows)
    connected_fixed_overhead_rows = fixed_overhead_sensitivity_rows(
        connected_validation_suite, "connected_validation"
    )
    write_csv(RESULTS / "connected_validation_fixed_overhead.csv", connected_fixed_overhead_rows)

    large_rows = large_searchspace_tier()
    write_csv(RESULTS / "large_searchspace_sensitivity.csv", large_rows)

    aa_rows: list[dict] = []
    for inst in suite:
        for target_ratio in TARGET_RATIOS:
            spec = threshold_spec(inst, target_ratio)
            for eps in (0.0, 5e-4, 1e-3, 2e-3):
                for oracle_cost in (1.0, 2.0, 4.0, 8.0):
                    sel = select_k_resource_efficiency(
                        spec["rho_tau"],
                        eps_model=eps,
                        d_prep=30.0,
                        d_iter=30.0,
                        prep_cost=1.0,
                        oracle_cost=oracle_cost,
                        diffusion_cost=1.0,
                        k_max=50,
                    )
                    p0 = effective_probability(spec["rho_tau"], 0, eps, 30.0, 30.0)
                    eta_res = (sel["normalized_cost"] / sel["p_eff"]) / (1.0 / p0)
                    aa_rows.append(
                        {
                            "instance_id": inst.instance_id,
                            "n": inst.n,
                            "density_target": inst.density_target,
                            "seed": inst.seed,
                            "target_ratio": spec["target_ratio"],
                            "threshold": spec["threshold"],
                            "marked_count": spec["marked_count"],
                            "rho_tau": spec["rho_tau"],
                            "eps_model": eps,
                            "oracle_cost_norm": oracle_cost,
                            "diffusion_cost_norm": 1.0,
                            "prep_cost_norm": 1.0,
                            "k_star_resource_eff": sel["k"],
                            "p_target_eff": sel["p_eff"],
                            "expected_repetitions": 1.0 / sel["p_eff"],
                            "score": sel["score"],
                            "normalized_cost": sel["normalized_cost"],
                            "normalized_resource_per_target_hit": sel["normalized_cost"] / sel["p_eff"],
                            "depth_model": sel["depth_model"],
                            "eta_res": eta_res,
                        }
                    )
    write_csv(RESULTS / "amplitude_amplification_sensitivity.csv", aa_rows)

    # QAOA initialization-stability audit: twenty deterministic instance-conditioned
    # starts per (instance, depth). The canonical five-start primary ledger is the exact
    # seed-0..4 subset so the original analysis and the expanded audit are nested.
    qstable = run_qaoa_suite(suite, optimizer_seeds=range(QAOA_STABILITY_STARTS))
    write_csv(RESULTS / "qaoa_initialization_stability_runs.csv", qstable)
    qstable_inst, qstable_agg = summarize_qaoa(qstable)
    write_csv(RESULTS / "qaoa_initialization_stability_instance_summary.csv", qstable_inst)
    write_csv(RESULTS / "qaoa_initialization_stability_aggregate.csv", qstable_agg)
    qstable_inf = qaoa_depth_inference(qstable)
    write_csv(RESULTS / "qaoa_initialization_stability_inference.csv", qstable_inf)

    qraw = [r for r in qstable if int(r["optimizer_seed"]) < 5]
    write_csv(RESULTS / "qaoa_runs.csv", qraw)
    qinst, qagg = summarize_qaoa(qraw)
    write_csv(RESULTS / "qaoa_instance_summary.csv", qinst)
    write_csv(RESULTS / "qaoa_aggregate_summary.csv", qagg)

    stability_comparison: list[dict] = []
    for a20 in qstable_agg:
        pdepth = int(a20["p"])
        a5 = next(x for x in qagg if int(x["p"]) == pdepth)
        stability_comparison.append({
            "metric": "aggregate",
            "p": pdepth,
            "comparison": "",
            "five_start_value": float(a5["instance_median_approx_ratio"]),
            "twenty_start_value": float(a20["instance_median_approx_ratio"]),
            "twenty_start_ci_lo": math.nan,
            "twenty_start_ci_hi": math.nan,
            "five_start_p_holm": math.nan,
            "twenty_start_p_holm": math.nan,
        })
    depth_inference_rows = qaoa_depth_inference(qraw)
    for r20 in qstable_inf:
        r5 = next(x for x in depth_inference_rows if x["comparison"] == r20["comparison"])
        stability_comparison.append({
            "metric": "inference",
            "p": "",
            "comparison": r20["comparison"],
            "five_start_value": float(r5["median_delta"]),
            "twenty_start_value": float(r20["median_delta"]),
            "twenty_start_ci_lo": float(r20["bootstrap95_lo"]),
            "twenty_start_ci_hi": float(r20["bootstrap95_hi"]),
            "five_start_p_holm": float(r5["p_holm"]),
            "twenty_start_p_holm": float(r20["p_holm"]),
        })
    write_csv(RESULTS / "qaoa_initialization_stability_comparison.csv", stability_comparison)

    qopt_raw = run_qaoa_optimizer_budget_suite(suite)
    write_csv(RESULTS / "qaoa_optimizer_budget_runs.csv", qopt_raw)
    qopt_inst, qopt_agg = summarize_qaoa_optimizer_budget(qopt_raw)
    write_csv(RESULTS / "qaoa_optimizer_budget_instance_summary.csv", qopt_inst)
    write_csv(RESULTS / "qaoa_optimizer_budget_aggregate.csv", qopt_agg)
    qopt_pair = qaoa_optimizer_paired_deltas(qopt_raw)
    write_csv(RESULTS / "qaoa_optimizer_budget_paired.csv", qopt_pair)

    write_csv(RESULTS / "qaoa_depth_inference.csv", depth_inference_rows)
    qopt_inf_inst, qopt_inf_rows = qaoa_optimizer_inference(qopt_pair)
    write_csv(RESULTS / "qaoa_optimizer_inference_instance_deltas.csv", qopt_inf_inst)
    write_csv(RESULTS / "qaoa_optimizer_inference.csv", qopt_inf_rows)

    # Common target-quality metric across methods.  P_tau is always the probability/fraction
    # of producing C(x) >= tau.  Resource units are not compared across method families here.
    target_rows: list[dict] = []
    hill_lookup = {r["instance_id"]: r for r in hill}
    budgeted_lookup = {(r["instance_id"], r["method"]): r for r in classical_budgeted_summary}
    for inst in suite:
        for target_ratio in TARGET_RATIOS:
            spec = threshold_spec(inst, target_ratio)
            suffix = f"q{int(round(100*target_ratio)):03d}"
            target_rows.append({
                "instance_id": inst.instance_id, "n": inst.n,
                "target_ratio": target_ratio, "threshold": spec["threshold"],
                "method": "uniform", "configuration": "uniform sample",
                "p_target": spec["rho_tau"],
                "expected_independent_repetitions": 1.0/spec["rho_tau"],
                "resource_metric_scope": "none/common probability metric only",
            })
            hprob = float(hill_lookup[inst.instance_id][f"target_{suffix}_hit_fraction"])
            target_rows.append({
                "instance_id": inst.instance_id, "n": inst.n,
                "target_ratio": target_ratio, "threshold": spec["threshold"],
                "method": "hillclimb", "configuration": "256 starts",
                "p_target": hprob,
                "expected_independent_repetitions": (1.0/hprob) if hprob > 0 else math.inf,
                "resource_metric_scope": "none/common probability metric only",
            })
            for classical_method in ("simulated_annealing", "tabu_search"):
                cr = budgeted_lookup[(inst.instance_id, classical_method)]
                cprob = float(cr[f"target_{suffix}_hit_fraction"])
                target_rows.append({
                    "instance_id": inst.instance_id, "n": inst.n,
                    "target_ratio": target_ratio, "threshold": spec["threshold"],
                    "method": classical_method,
                    "configuration": f"{CLASSICAL_BUDGETED_RUNS} runs; <= {CLASSICAL_EVAL_BUDGET} objective evaluations/run",
                    "p_target": cprob,
                    "expected_independent_repetitions": (1.0/cprob) if cprob > 0 else math.inf,
                    "resource_metric_scope": "classical objective-evaluation budget only; not matched to quantum resources",
                })
            # Reference AA operating point: no attenuation, unit oracle cost.
            aa_ref = select_k_resource_efficiency(spec["rho_tau"], 0.0, 30.0, 30.0, 1.0, 1.0, 1.0, 50)
            target_rows.append({
                "instance_id": inst.instance_id, "n": inst.n,
                "target_ratio": target_ratio, "threshold": spec["threshold"],
                "method": "amplitude_amplification", "configuration": f"k={aa_ref['k']}; eps=0; oracle_cost=1",
                "p_target": aa_ref["p_eff"],
                "expected_independent_repetitions": 1.0/aa_ref["p_eff"],
                "resource_metric_scope": f"within-AA normalized_resource_per_hit={aa_ref['normalized_cost']/aa_ref['p_eff']:.12g}",
            })
            for pdepth in (1, 2, 3):
                rr = [r for r in qraw if r["instance_id"] == inst.instance_id and int(r["p"]) == pdepth]
                vals = np.asarray([float(r[f"p_target_exact_{suffix}"]) for r in rr], dtype=float)
                pmed = float(np.median(vals))
                target_rows.append({
                    "instance_id": inst.instance_id, "n": inst.n,
                    "target_ratio": target_ratio, "threshold": spec["threshold"],
                    "method": "qaoa", "configuration": f"p={pdepth}; median over 5 L-BFGS-B starts",
                    "p_target": pmed,
                    "expected_independent_repetitions": (1.0/pmed) if pmed > 0 else math.inf,
                    "resource_metric_scope": "none/common probability metric only",
                })
    write_csv(RESULTS / "target_metric_summary.csv", target_rows)

    # Operational thresholds are constructed without C*.  Exact Tier-I enumeration is
    # used only after construction to evaluate feasibility/rho and to form an
    # oracle-informed AA reference.  Robustness to unknown rho is a separate layer.
    operational_target_rows: list[dict] = []
    for inst in suite:
        for level in OPERATIONAL_LEVELS:
            spec = operational_threshold_spec(inst, level)
            suffix = f"l{int(round(100*level)):03d}"
            p_uniform = spec["rho_tau_exact_validation"]
            operational_target_rows.append({
                "instance_id": inst.instance_id, "n": inst.n,
                "operational_level": level, "threshold": spec["threshold"],
                "feasible_exact_validation": spec["feasible_exact_validation"],
                "realized_quality_ratio_exact_validation": spec["realized_quality_ratio_exact_validation"],
                "method": "uniform", "configuration": "uniform sample",
                "p_target": p_uniform,
                "expected_independent_repetitions": (1.0/p_uniform) if p_uniform > 0 else math.inf,
                "resource_metric_scope": "common probability only; threshold construction independent of C*",
            })
            hprob = float(hill_lookup[inst.instance_id][f"oper_{suffix}_hit_fraction"])
            operational_target_rows.append({
                "instance_id": inst.instance_id, "n": inst.n,
                "operational_level": level, "threshold": spec["threshold"],
                "feasible_exact_validation": spec["feasible_exact_validation"],
                "realized_quality_ratio_exact_validation": spec["realized_quality_ratio_exact_validation"],
                "method": "hillclimb", "configuration": "256 starts",
                "p_target": hprob,
                "expected_independent_repetitions": (1.0/hprob) if hprob > 0 else math.inf,
                "resource_metric_scope": "common probability only; threshold construction independent of C*",
            })
            for classical_method in ("simulated_annealing", "tabu_search"):
                cr = budgeted_lookup[(inst.instance_id, classical_method)]
                cprob = float(cr[f"oper_{suffix}_hit_fraction"])
                operational_target_rows.append({
                    "instance_id": inst.instance_id, "n": inst.n,
                    "operational_level": level, "threshold": spec["threshold"],
                    "feasible_exact_validation": spec["feasible_exact_validation"],
                    "realized_quality_ratio_exact_validation": spec["realized_quality_ratio_exact_validation"],
                    "method": classical_method,
                    "configuration": f"{CLASSICAL_BUDGETED_RUNS} runs; <= {CLASSICAL_EVAL_BUDGET} objective evaluations/run",
                    "p_target": cprob,
                    "expected_independent_repetitions": (1.0/cprob) if cprob > 0 else math.inf,
                    "resource_metric_scope": "classical objective-evaluation budget only; threshold construction independent of C*; not matched to quantum resources",
                })
            if p_uniform > 0:
                aa_ref = select_k_resource_efficiency(p_uniform, 0.0, 30.0, 30.0, 1.0, 1.0, 1.0, 50)
                aa_prob = aa_ref["p_eff"]
                aa_cfg = f"k={aa_ref['k']}; exact-rho validation; eps=0; oracle_cost=1"
                aa_scope = f"oracle-informed validation reference; normalized_resource_per_hit={aa_ref['normalized_cost']/aa_prob:.12g}"
            else:
                aa_prob = 0.0
                aa_cfg = "infeasible threshold under exact Tier-I validation"
                aa_scope = "no AA selector run because the validated target event is empty"
            operational_target_rows.append({
                "instance_id": inst.instance_id, "n": inst.n,
                "operational_level": level, "threshold": spec["threshold"],
                "feasible_exact_validation": spec["feasible_exact_validation"],
                "realized_quality_ratio_exact_validation": spec["realized_quality_ratio_exact_validation"],
                "method": "amplitude_amplification", "configuration": aa_cfg,
                "p_target": aa_prob,
                "expected_independent_repetitions": (1.0/aa_prob) if aa_prob > 0 else math.inf,
                "resource_metric_scope": aa_scope,
            })
            for pdepth in (1, 2, 3):
                rr = [r for r in qraw if r["instance_id"] == inst.instance_id and int(r["p"]) == pdepth]
                vals = np.asarray([float(r[f"oper_p_target_exact_{suffix}"]) for r in rr], dtype=float)
                pmed = float(np.median(vals))
                operational_target_rows.append({
                    "instance_id": inst.instance_id, "n": inst.n,
                    "operational_level": level, "threshold": spec["threshold"],
                    "feasible_exact_validation": spec["feasible_exact_validation"],
                    "realized_quality_ratio_exact_validation": spec["realized_quality_ratio_exact_validation"],
                    "method": "qaoa", "configuration": f"p={pdepth}; median over 5 L-BFGS-B starts",
                    "p_target": pmed,
                    "expected_independent_repetitions": (1.0/pmed) if pmed > 0 else math.inf,
                    "resource_metric_scope": "common probability only; threshold construction independent of C*",
                })
    write_csv(RESULTS / "operational_target_metric_summary.csv", operational_target_rows)

    files_for_hash = [
        DATA / "maxcut_suite_graphs.csv",
        DATA / "coverage_graphs.csv",
        DATA / "connected_validation_graphs.csv",
        RESULTS / "primary_graph_diagnostics.csv",
        RESULTS / "coverage_graph_diagnostics.csv",
        RESULTS / "connected_validation_graph_diagnostics.csv",
        RESULTS / "connected_validation_ground_truth.csv",
        RESULTS / "connected_validation_operational_thresholds.csv",
        RESULTS / "connected_validation_coupled_oracle.csv",
        RESULTS / "connected_validation_fixed_overhead.csv",
        RESULTS / "gw_sdp_primary.csv",
        RESULTS / "gw_sdp_connected_validation.csv",
        RESULTS / "gw_sdp_summary.csv",
        RESULTS / "bbht_operational_primary.csv",
        RESULTS / "bbht_operational_connected_validation.csv",
        RESULTS / "bbht_summary.csv",
        RESULTS / "resource_scalarization_primary.csv",
        RESULTS / "resource_scalarization_connected_validation.csv",
        RESULTS / "resource_scalarization_summary.csv",
        RESULTS / "dense_operational_lambda_primary.csv",
        RESULTS / "dense_operational_lambda_connected_validation.csv",
        RESULTS / "dense_operational_lambda_summary.csv",
        RESULTS / "maxcut_ground_truth.csv",
        RESULTS / "operational_thresholds.csv",
        RESULTS / "classical_hillclimb.csv",
        RESULTS / "classical_budgeted_runs.csv",
        RESULTS / "classical_budgeted_summary.csv",
        RESULTS / "classical_budget_curve_runs.csv",
        RESULTS / "classical_budget_curve_summary.csv",
        RESULTS / "classical_budget_curve_aggregate.csv",
        RESULTS / "amplitude_amplification_sensitivity.csv",
        RESULTS / "qaoa_runs.csv",
        RESULTS / "qaoa_initialization_stability_runs.csv",
        RESULTS / "qaoa_initialization_stability_instance_summary.csv",
        RESULTS / "qaoa_initialization_stability_aggregate.csv",
        RESULTS / "qaoa_initialization_stability_inference.csv",
        RESULTS / "qaoa_initialization_stability_comparison.csv",
        RESULTS / "qaoa_instance_summary.csv",
        RESULTS / "qaoa_aggregate_summary.csv",
        RESULTS / "qaoa_optimizer_budget_runs.csv",
        RESULTS / "qaoa_optimizer_budget_instance_summary.csv",
        RESULTS / "qaoa_optimizer_budget_aggregate.csv",
        RESULTS / "qaoa_optimizer_budget_paired.csv",
        RESULTS / "qaoa_depth_inference.csv",
        RESULTS / "qaoa_optimizer_inference_instance_deltas.csv",
        RESULTS / "qaoa_optimizer_inference.csv",
        RESULTS / "simulator_scaling.csv",
        RESULTS / "resource_robustness_grid.csv",
        RESULTS / "rho_estimation_robustness.csv",
        RESULTS / "oracle_resource_model.csv",
        RESULTS / "coupled_oracle_depth_sensitivity.csv",
        RESULTS / "fixed_overhead_sensitivity.csv",
        RESULTS / "large_searchspace_sensitivity.csv",
        RESULTS / "coverage_ground_truth.csv",
        RESULTS / "coverage_operational_thresholds.csv",
        RESULTS / "coverage_hillclimb.csv",
        RESULTS / "coverage_coupled_oracle.csv",
        RESULTS / "coverage_summary.csv",
        RESULTS / "target_metric_summary.csv",
        RESULTS / "operational_target_metric_summary.csv",
    ]
    best = max(qraw, key=lambda r: r["approx_ratio"])
    manifest = {
        "study": "FGCS canonical Max-Cut resource benchmark",
        "evidence_mode": [
            "threshold-oracle analytical amplitude-amplification calculation",
            "exact classical enumeration",
            "ideal-statevector QAOA simulation",
            "synthetic attenuation/resource-cost sensitivity",
            "simple classical local-search reference",
            "fixed-objective-evaluation-budget simulated-annealing and tabu-search references",
            "multi-budget classical objective-evaluation curve for simulated annealing and tabu search",
            "host-side simulator scaling diagnostic",
            "dense normalized resource-uncertainty analysis across 90%, 95%, and 100% quality thresholds",
            "common target-quality probability metric across AA, QAOA, uniform sampling, hill climbing, simulated annealing, and tabu search",
            "operational threshold construction from random-cut expectation and spectral upper bound without C*",
            "exact Tier-I feasibility/rho validation of operational thresholds",
            "architecture-informed reversible weighted-Max-Cut threshold-oracle logical resource model",
            "coupled oracle-cost/logical-depth attenuation sensitivity",
            "fixed per-trial overhead sensitivity and break-even analysis under the logical resource model",
            "estimated-rho stopping-depth robustness with exact-rho retrospective regret",
            "analytical large-search-space sensitivity",
            "instance-clustered paired QAOA depth and optimizer inference with Holm correction and bootstrap intervals",
            "twenty-start QAOA initialization-stability audit nested around the canonical five-start primary analysis",
            "expanded exact graph-seed and structured-topology coverage alongside the 18-instance primary QAOA inference suite",
            "connected non-bipartite fixed-density exact validation tier through n=14 with explicit structural diagnostics",
            "BBHT unknown-solution-count search schedule evaluated retrospectively under the same logical resource model",
            "Toffoli-weight scalarization sensitivity with fixed overhead anchored to the canonical alpha=6 oracle cost",
            "dense operational-lambda sensitivity from 0 to 1 in increments of 0.05",
        ],
        "hardware_claims": False,
        "compiler_claims": False,
        "suite": {
            "n_values": [8, 10, 12],
            "density_targets": [0.25, 0.50, 0.75],
            "graph_seeds": [17, 42],
            "exact_instances": len(suite),
            "primary_graph_diagnostic_rows": len(primary_graph_diagnostics),
            "primary_disconnected_instances": sum(not bool(r["connected"]) for r in primary_graph_diagnostics),
            "primary_bipartite_instances": sum(bool(r["bipartite"]) for r in primary_graph_diagnostics),
            "coverage_graph_diagnostic_rows": len(coverage_graph_diagnostics),
            "coverage_disconnected_instances": sum(not bool(r["connected"]) for r in coverage_graph_diagnostics),
            "coverage_bipartite_instances": sum(bool(r["bipartite"]) for r in coverage_graph_diagnostics),
            "connected_validation_stream_version": CONNECTED_VALIDATION_STREAM_VERSION,
            "connected_validation_n_values": list(CONNECTED_VALIDATION_NS),
            "connected_validation_density_targets": list(CONNECTED_VALIDATION_DENSITIES),
            "connected_validation_seeds": list(CONNECTED_VALIDATION_SEEDS),
            "connected_validation_exact_instances": len(connected_validation_suite),
            "connected_validation_graph_edge_rows": len(connected_graphs),
            "connected_validation_graph_diagnostic_rows": len(connected_graph_diagnostics),
            "connected_validation_operational_threshold_rows": len(connected_thresholds),
            "connected_validation_coupled_oracle_rows": len(connected_coupled),
            "connected_validation_fixed_overhead_rows": len(connected_fixed_overhead_rows),
            "gw_sdp_starts": GW_SDP_STARTS,
            "gw_sdp_max_sweeps": GW_SDP_MAX_SWEEPS,
            "gw_sdp_certificate_gap_tolerance": GW_SDP_CERT_GAP_TOL,
            "gw_rounding_samples_per_instance": GW_ROUNDING_SAMPLES,
            "gw_primary_rows": len(gw_primary_rows),
            "gw_connected_validation_rows": len(gw_connected_rows),
            "bbht_lambda": BBHT_LAMBDA,
            "bbht_eps_levels": list(BBHT_EPS_LEVELS),
            "bbht_fixed_overhead_ratios": list(BBHT_FIXED_OVERHEAD_RATIOS),
            "bbht_primary_rows": len(bbht_primary_rows),
            "bbht_connected_validation_rows": len(bbht_connected_rows),
            "bbht_summary_rows": len(bbht_summary),
            "resource_toffoli_weights": list(RESOURCE_TOFFOLI_WEIGHTS),
            "resource_scalarization_eps_levels": list(RESOURCE_SCALARIZATION_EPS_LEVELS),
            "resource_scalarization_canonical_fixed_ratios": list(RESOURCE_SCALARIZATION_CANONICAL_FIXED_RATIOS),
            "resource_scalarization_primary_rows": len(scalar_primary_rows),
            "resource_scalarization_connected_validation_rows": len(scalar_connected_rows),
            "resource_scalarization_summary_rows": len(scalar_summary),
            "dense_operational_levels": list(DENSE_OPERATIONAL_LEVELS),
            "dense_operational_lambda_primary_rows": len(dense_lambda_primary),
            "dense_operational_lambda_connected_validation_rows": len(dense_lambda_connected),
            "dense_operational_lambda_summary_rows": len(dense_lambda_summary),
            "expanded_random_exact_instances": len(build_expanded_random_suite()),
            "structured_exact_instances": len(build_structured_suite()),
            "coverage_exact_instances": len(coverage_suite),
            "coverage_graph_edge_rows": len(coverage_graphs),
            "expanded_random_seeds": list(EXPANDED_RANDOM_SEEDS),
            "structured_families": list(STRUCTURED_FAMILIES),
            "structured_weight_seeds": list(STRUCTURED_WEIGHT_SEEDS),
            "coverage_operational_threshold_rows": len(coverage_thresholds),
            "coverage_coupled_oracle_rows": len(coverage_coupled),
            "coverage_summary_rows": len(coverage_summary),
            "qaoa_instances": len(suite),
            "qaoa_initialization_stream_version": QAOA_INIT_STREAM_VERSION,
            "qaoa_initialization_conditioning": "instance+p+optimizer_seed",
            "qaoa_stability_starts_per_instance_depth": QAOA_STABILITY_STARTS,
            "qaoa_stability_total_runs": len(qstable),
            "qaoa_stability_inference_rows": len(qstable_inf),
            "random_graph_stream_version": RANDOM_GRAPH_STREAM_VERSION,
            "simulator_scaling_n_values": [8, 10, 12, 14, 16, 18, 20],
            "large_analytical_n_values": [12, 16, 20, 24],
            "dense_robustness_conditions": len(robustness_rows),
            "large_analytical_conditions": len(large_rows),
            "target_quality_ratios": list(TARGET_RATIOS),
            "operational_levels": list(OPERATIONAL_LEVELS),
            "operational_threshold_rows": len(operational_threshold_rows),
            "operational_target_metric_rows": len(operational_target_rows),
            "budgeted_classical_raw_rows": len(classical_budgeted_raw),
            "budgeted_classical_summary_rows": len(classical_budgeted_summary),
            "classical_budget_curve_budgets": list(CLASSICAL_BUDGET_CURVE),
            "classical_budget_curve_raw_rows": len(classical_curve_raw),
            "classical_budget_curve_summary_rows": len(classical_curve_summary),
            "classical_budget_curve_aggregate_rows": len(classical_curve_aggregate),
            "budgeted_classical_methods": ["simulated_annealing", "tabu_search"],
            "budgeted_classical_runs_per_instance_method": CLASSICAL_BUDGETED_RUNS,
            "budgeted_classical_eval_budget_per_run": CLASSICAL_EVAL_BUDGET,
            "rho_estimate_factors": list(RHO_ESTIMATE_FACTORS),
            "rho_estimation_robustness_rows": len(rho_robustness_rows),
            "oracle_resource_model_rows": len(oracle_rows),
            "coupled_oracle_depth_rows": len(coupled_rows),
            "fixed_overhead_sensitivity_rows": len(fixed_overhead_rows),
            "fixed_overhead_oracle_ratios": list(FIXED_OVERHEAD_ORACLE_RATIOS),
            "oracle_attenuation_levels": list(ORACLE_ATTENUATION_LEVELS),
            "coarse_threshold_aa_conditions": len(aa_rows),
            "qaoa_depth_inference_rows": len(depth_inference_rows),
            "qaoa_optimizer_inference_instance_rows": len(qopt_inf_inst),
            "qaoa_optimizer_inference_rows": len(qopt_inf_rows),
        },
        "qaoa": {
            "depths": [1, 2, 3],
            "optimizer_seeds": [0, 1, 2, 3, 4],
            "optimizer": "L-BFGS-B",
            "initialization": "deterministic instance-conditioned stream; independent across graph instances",
            "initialization_stream_version": QAOA_INIT_STREAM_VERSION,
            "maxiter": 60,
            "optimization_shots": 0,
            "final_shots": 4096,
            "total_runs": len(qraw),
        },
        "qaoa_initialization_stability": {
            "depths": [1, 2, 3],
            "optimizer_seeds": list(range(QAOA_STABILITY_STARTS)),
            "starts_per_instance_depth": QAOA_STABILITY_STARTS,
            "optimizer": "L-BFGS-B",
            "total_runs": len(qstable),
            "canonical_five_start_subset": [0, 1, 2, 3, 4],
            "inference_rows": len(qstable_inf),
            "population_generalization_claim": False,
        },
        "qaoa_optimizer_robustness": {
            "optimizers": list(QAOA_OPTIMIZER_METHODS),
            "objective_eval_budget_per_run": QAOA_OPTIMIZER_EVAL_BUDGET,
            "paired_initializations": True,
            "paired_initialization_scope": "identical x0 within each (instance,p,seed) optimizer pair; independent streams across graph instances",
            "initialization_stream_version": QAOA_INIT_STREAM_VERSION,
            "total_runs": len(qopt_raw),
            "evidence_label": "ideal-statevector optimizer robustness under equal objective-evaluation cap",
        },
        "statistical_inference": {
            "paired_unit": "benchmark instance after collapsing repeated optimizer starts",
            "fixed_qaoa_instances": len(suite),
            "bootstrap_resamples": J_BOOTSTRAP_RESAMPLES,
            "multiple_comparison_correction": "Holm within depth family and optimizer family separately",
            "population_generalization_claim": False,
        },
        "best_qaoa_single_run": {
            "instance_id": best["instance_id"],
            "p": int(best["p"]),
            "optimizer_seed": int(best["optimizer_seed"]),
            "approx_ratio": float(best["approx_ratio"]),
            "p_opt_exact": float(best["p_opt_exact"]),
        },
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
        },
        "environment_lock": {
            "python_version_file": ".python-version",
            "python_expected": (ROOT / ".python-version").read_text(encoding="utf-8").strip() if (ROOT / ".python-version").exists() else None,
            "requirements_file": "requirements.txt",
            "requirements_lock_file": "requirements.lock",
            "requirements_lock_sha256": sha256(ROOT / "requirements.lock") if (ROOT / "requirements.lock").exists() else None,
            "preflight": "src/preflight.py",
        },
        "sha256": {p.name: sha256(p) for p in files_for_hash},
        "source_sha256": {
            "benchmark.py": sha256(Path(__file__)),
            "render_tables.py": sha256(ROOT / "src" / "render_tables.py") if (ROOT / "src" / "render_tables.py").exists() else None,
            "preflight.py": sha256(ROOT / "src" / "preflight.py") if (ROOT / "src" / "preflight.py").exists() else None,
            "test_core.py": sha256(ROOT / "tests" / "test_core.py") if (ROOT / "tests" / "test_core.py").exists() else None,
            "test_preflight.py": sha256(ROOT / "tests" / "test_preflight.py") if (ROOT / "tests" / "test_preflight.py").exists() else None,
            "main.tex": sha256(ROOT / "manuscript" / "main.tex") if (ROOT / "manuscript" / "main.tex").exists() else None,
            "README.md": sha256(ROOT / "README.md") if (ROOT / "README.md").exists() else None,
            "CLAIMS_REGISTER.md": sha256(ROOT / "manuscript" / "CLAIMS_REGISTER.md") if (ROOT / "manuscript" / "CLAIMS_REGISTER.md").exists() else None,
            "requirements.txt": sha256(ROOT / "requirements.txt") if (ROOT / "requirements.txt").exists() else None,
            "requirements.lock": sha256(ROOT / "requirements.lock") if (ROOT / "requirements.lock").exists() else None,
            ".python-version": sha256(ROOT / ".python-version") if (ROOT / ".python-version").exists() else None,
        },
    }
    (RESULTS / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
