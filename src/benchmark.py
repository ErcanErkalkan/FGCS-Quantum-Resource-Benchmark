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


def run_qaoa_one(
    inst: MaxCutInstance,
    p: int,
    optimizer_seed: int,
    maxiter: int = 60,
    final_shots: int = 4096,
) -> dict:
    rng = np.random.default_rng(optimizer_seed)
    x0 = np.concatenate(
        [rng.uniform(0, 2 * math.pi, p), rng.uniform(0, math.pi, p)]
    )
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
    rng = np.random.default_rng(optimizer_seed)
    x0 = np.concatenate(
        [rng.uniform(0, 2 * math.pi, p), rng.uniform(0, math.pi, p)]
    )
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

    Five initialization runs are first collapsed to an instance-level median at
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
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
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

    qraw = run_qaoa_suite(suite)
    write_csv(RESULTS / "qaoa_runs.csv", qraw)
    qinst, qagg = summarize_qaoa(qraw)
    write_csv(RESULTS / "qaoa_instance_summary.csv", qinst)
    write_csv(RESULTS / "qaoa_aggregate_summary.csv", qagg)

    qopt_raw = run_qaoa_optimizer_budget_suite(suite)
    write_csv(RESULTS / "qaoa_optimizer_budget_runs.csv", qopt_raw)
    qopt_inst, qopt_agg = summarize_qaoa_optimizer_budget(qopt_raw)
    write_csv(RESULTS / "qaoa_optimizer_budget_instance_summary.csv", qopt_inst)
    write_csv(RESULTS / "qaoa_optimizer_budget_aggregate.csv", qopt_agg)
    qopt_pair = qaoa_optimizer_paired_deltas(qopt_raw)
    write_csv(RESULTS / "qaoa_optimizer_budget_paired.csv", qopt_pair)

    depth_inference_rows = qaoa_depth_inference(qraw)
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
        RESULTS / "maxcut_ground_truth.csv",
        RESULTS / "operational_thresholds.csv",
        RESULTS / "classical_hillclimb.csv",
        RESULTS / "classical_budgeted_runs.csv",
        RESULTS / "classical_budgeted_summary.csv",
        RESULTS / "amplitude_amplification_sensitivity.csv",
        RESULTS / "qaoa_runs.csv",
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
            "expanded exact graph-seed and structured-topology coverage alongside the 18-instance primary QAOA inference suite",
        ],
        "hardware_claims": False,
        "compiler_claims": False,
        "suite": {
            "n_values": [8, 10, 12],
            "density_targets": [0.25, 0.50, 0.75],
            "graph_seeds": [17, 42],
            "exact_instances": len(suite),
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
            "maxiter": 60,
            "optimization_shots": 0,
            "final_shots": 4096,
            "total_runs": len(qraw),
        },
        "qaoa_optimizer_robustness": {
            "optimizers": list(QAOA_OPTIMIZER_METHODS),
            "objective_eval_budget_per_run": QAOA_OPTIMIZER_EVAL_BUDGET,
            "paired_initializations": True,
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
