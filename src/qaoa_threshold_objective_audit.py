from __future__ import annotations

import argparse
import csv
import json
import math
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.stats import wilcoxon

from benchmark import (
    build_exact_suite,
    build_maxcut_instance,
    holm_adjust,
    operational_threshold_spec,
    qaoa_initial_params,
    qaoa_metrics,
    target_probability,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
LEVEL = 0.40
DEPTHS = (1, 2, 3)
SEEDS = tuple(range(5))
EVAL_BUDGET = 128
BOOTSTRAP_RESAMPLES = 20_000
BOOTSTRAP_SEED = 20260902


class _EvaluationBudgetStop(RuntimeError):
    pass


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _threshold_run(task: tuple[int, float, int, int, int]) -> dict:
    n, density, graph_seed, p, optimizer_seed = task
    inst = build_maxcut_instance(n, density, graph_seed)
    spec = operational_threshold_spec(inst, LEVEL)
    threshold = int(spec["threshold"])
    x0 = qaoa_initial_params(inst, p, optimizer_seed)
    bounds = [(0.0, 2.0 * math.pi)] * p + [(0.0, math.pi)] * p
    nfev = 0
    best_target = -1.0
    best_x = np.asarray(x0, dtype=float).copy()

    def objective(x: np.ndarray) -> float:
        nonlocal nfev, best_target, best_x
        if nfev >= EVAL_BUDGET:
            raise _EvaluationBudgetStop
        nfev += 1
        _, _, probs = qaoa_metrics(np.asarray(x, dtype=float), p, inst)
        p_target = target_probability(probs, inst, threshold)
        if p_target > best_target:
            best_target = float(p_target)
            best_x = np.asarray(x, dtype=float).copy()
        return -p_target

    success = False
    termination = "optimizer_stopped"
    message = ""
    nit = -1
    try:
        res = minimize(
            objective,
            x0,
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 10000, "maxfun": EVAL_BUDGET, "ftol": 1e-12, "gtol": 1e-8},
        )
        success = bool(res.success)
        nit = int(getattr(res, "nit", -1))
        message = str(res.message)
        termination = "optimizer_converged" if success else (
            "evaluation_budget_exhausted" if nfev >= EVAL_BUDGET else "optimizer_stopped"
        )
    except _EvaluationBudgetStop:
        termination = "evaluation_budget_exhausted"
        message = f"strict objective-evaluation cap {EVAL_BUDGET} reached"

    expected, p_opt, probs = qaoa_metrics(best_x, p, inst)
    p_target = target_probability(probs, inst, threshold)
    return {
        "instance_id": inst.instance_id,
        "n": inst.n,
        "density_target": inst.density_target,
        "graph_seed": inst.seed,
        "p": p,
        "optimizer_seed": optimizer_seed,
        "operational_level": LEVEL,
        "threshold": threshold,
        "rho_uniform": float(spec["rho_tau_exact_validation"]),
        "objective": "threshold_hit_probability",
        "optimizer": "L-BFGS-B",
        "objective_eval_budget": EVAL_BUDGET,
        "objective_evaluations_used": nfev,
        "success": success,
        "termination": termination,
        "nit": nit,
        "p_target_exact": float(p_target),
        "expected_cut": float(expected),
        "approx_ratio": float(expected / inst.optimum),
        "p_opt_exact": float(p_opt),
        "initial_params": json.dumps([float(v) for v in x0]),
        "best_seen_params": json.dumps([float(v) for v in best_x]),
        "message": message,
        "evidence_label": "paired threshold-hit-trained ideal-statevector QAOA under 128-evaluation cap",
    }


def _read_standard_reference(path: Path) -> dict[tuple[str, int, int], dict]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for row in rows:
        if row["optimizer"] != "L-BFGS-B":
            continue
        key = (row["instance_id"], int(row["p"]), int(row["optimizer_seed"]))
        out[key] = row
    if len(out) != 270:
        raise RuntimeError(f"expected 270 L-BFGS-B reference rows, found {len(out)}")
    return out


def build_paired_rows(threshold_rows: list[dict], standard: dict[tuple[str, int, int], dict]) -> list[dict]:
    paired = []
    for row in threshold_rows:
        key = (row["instance_id"], int(row["p"]), int(row["optimizer_seed"]))
        ref = standard[key]
        same_x0 = ref["initial_params"] == row["initial_params"]
        paired.append({
            "instance_id": row["instance_id"],
            "p": int(row["p"]),
            "optimizer_seed": int(row["optimizer_seed"]),
            "expectation_p_target": float(ref["oper_p_target_exact_l040"]),
            "threshold_p_target": float(row["p_target_exact"]),
            "expectation_approx_ratio": float(ref["approx_ratio"]),
            "threshold_approx_ratio": float(row["approx_ratio"]),
            "expectation_p_opt": float(ref["p_opt_exact"]),
            "threshold_p_opt": float(row["p_opt_exact"]),
            "expectation_evals": int(ref["objective_evaluations_used"]),
            "threshold_evals": int(row["objective_evaluations_used"]),
            "initialization_identical": bool(same_x0),
            "delta_p_target": float(row["p_target_exact"]) - float(ref["oper_p_target_exact_l040"]),
            "delta_approx_ratio": float(row["approx_ratio"]) - float(ref["approx_ratio"]),
        })
    if not all(r["initialization_identical"] for r in paired):
        raise RuntimeError("paired initialization mismatch")
    return paired


def summarize_instances(paired: list[dict]) -> list[dict]:
    keys = sorted({(r["instance_id"], int(r["p"])) for r in paired})
    rows = []
    for iid, p in keys:
        rr = [r for r in paired if r["instance_id"] == iid and int(r["p"]) == p]
        exp_target = np.asarray([r["expectation_p_target"] for r in rr], dtype=float)
        thr_target = np.asarray([r["threshold_p_target"] for r in rr], dtype=float)
        exp_ar = np.asarray([r["expectation_approx_ratio"] for r in rr], dtype=float)
        thr_ar = np.asarray([r["threshold_approx_ratio"] for r in rr], dtype=float)
        rows.append({
            "instance_id": iid,
            "p": p,
            "paired_starts": len(rr),
            "expectation_p_target_median": float(np.median(exp_target)),
            "threshold_p_target_median": float(np.median(thr_target)),
            "delta_p_target_median": float(np.median(thr_target - exp_target)),
            "expectation_approx_ratio_median": float(np.median(exp_ar)),
            "threshold_approx_ratio_median": float(np.median(thr_ar)),
            "delta_approx_ratio_median": float(np.median(thr_ar - exp_ar)),
        })
    return rows


def infer(instance_rows: list[dict]) -> list[dict]:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    rows = []
    raw_p = []
    for p in DEPTHS:
        rr = [r for r in instance_rows if int(r["p"]) == p]
        d = np.asarray([r["threshold_p_target_median"] - r["expectation_p_target_median"] for r in rr], dtype=float)
        d_ar = np.asarray([r["threshold_approx_ratio_median"] - r["expectation_approx_ratio_median"] for r in rr], dtype=float)
        try:
            p_raw = float(wilcoxon(d, zero_method="wilcox", method="auto").pvalue)
        except ValueError:
            p_raw = 1.0
        boot = np.median(d[rng.integers(0, len(d), size=(BOOTSTRAP_RESAMPLES, len(d)))], axis=1)
        lo, hi = np.quantile(boot, [0.025, 0.975])
        rows.append({
            "p": p,
            "instances": len(rr),
            "paired_starts_per_instance": 5,
            "objective_eval_budget": EVAL_BUDGET,
            "median_expectation_p_target": float(np.median([r["expectation_p_target_median"] for r in rr])),
            "median_threshold_p_target": float(np.median([r["threshold_p_target_median"] for r in rr])),
            "median_delta_p_target": float(np.median(d)),
            "bootstrap_ci_lo": float(lo),
            "bootstrap_ci_hi": float(hi),
            "p_raw": p_raw,
            "p_holm": math.nan,
            "improved_instance_fraction": float(np.mean(d > 1e-12)),
            "median_delta_approx_ratio": float(np.median(d_ar)),
            "evidence_label": "instance-clustered paired objective-training sensitivity under equal 128-evaluation cap",
        })
        raw_p.append(p_raw)
    for row, adj in zip(rows, holm_adjust(raw_p)):
        row["p_holm"] = float(adj)
    return rows


def run(workers: int = 12) -> None:
    suite = build_exact_suite()
    tasks = [(inst.n, inst.density_target, inst.seed, p, seed) for inst in suite for p in DEPTHS for seed in SEEDS]
    threshold_rows = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_threshold_run, task) for task in tasks]
        for future in as_completed(futures):
            threshold_rows.append(future.result())
    threshold_rows.sort(key=lambda r: (r["instance_id"], int(r["p"]), int(r["optimizer_seed"])))
    standard = _read_standard_reference(RESULTS / "qaoa_optimizer_budget_runs.csv")
    paired = build_paired_rows(threshold_rows, standard)
    instance_rows = summarize_instances(paired)
    inference = infer(instance_rows)
    _write_csv(RESULTS / "qaoa_threshold_training_budget_runs.csv", threshold_rows)
    _write_csv(RESULTS / "qaoa_threshold_training_budget_paired.csv", paired)
    _write_csv(RESULTS / "qaoa_threshold_training_budget_instance_summary.csv", instance_rows)
    _write_csv(RESULTS / "qaoa_threshold_training_budget_inference.csv", inference)
    print(json.dumps(inference, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Paired QAOA expected-cut vs threshold-hit objective audit")
    parser.add_argument("--workers", type=int, default=12)
    args = parser.parse_args()
    run(workers=max(1, args.workers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
