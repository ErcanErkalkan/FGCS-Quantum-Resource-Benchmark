import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from benchmark import (
    grover_probability,
    effective_probability,
    select_k_resource_efficiency,
    build_maxcut_instance,
    build_exact_suite,
    qaoa_metrics,
    qaoa_initial_params,
    QAOA_INIT_STREAM_VERSION,
    QAOA_STABILITY_STARTS,
    wilson_interval,
    local_hillclimb,
    threshold_spec,
    target_probability,
    TARGET_RATIOS,
    OPERATIONAL_LEVELS,
    operational_threshold_spec,
    random_cut_expectation,
    spectral_maxcut_upper_bound,
    RHO_ESTIMATE_FACTORS,
    select_k_with_rho_estimate,
    rho_estimation_robustness,
    maxcut_threshold_oracle_resource_model,
    select_k_architecture_coupled,
    oracle_resource_rows,
    coupled_oracle_depth_sensitivity,
    ORACLE_ATTENUATION_LEVELS,
    FIXED_OVERHEAD_ORACLE_RATIOS,
    architecture_fixed_overhead_break_even_ratio,
    fixed_overhead_sensitivity_rows,
    simulated_annealing_run,
    tabu_search_run,
    run_budgeted_classical_suite,
    CLASSICAL_EVAL_BUDGET,
    CLASSICAL_BUDGETED_RUNS,
    CLASSICAL_BUDGET_CURVE,
    run_classical_budget_curve,
    run_qaoa_budgeted_one,
    run_qaoa_optimizer_budget_suite,
    summarize_qaoa_optimizer_budget,
    qaoa_optimizer_paired_deltas,
    QAOA_OPTIMIZER_EVAL_BUDGET,
    QAOA_OPTIMIZER_METHODS,
    holm_adjust,
    paired_rank_biserial,
    bootstrap_median_ci,
    qaoa_depth_inference,
    qaoa_optimizer_inference,
    J_BOOTSTRAP_RESAMPLES,
    build_expanded_random_suite,
    build_structured_suite,
    build_coverage_suite,
    coverage_graph_rows,
    coverage_ground_truth_rows,
    coverage_operational_threshold_rows,
    coverage_coupled_oracle_rows,
    EXPANDED_RANDOM_SEEDS,
    STRUCTURED_FAMILIES,
    graph_structure_metrics,
    graph_diagnostics_rows,
    build_connected_validation_instance,
    build_connected_validation_suite,
    connected_validation_ground_truth_rows,
    connected_validation_operational_threshold_rows,
    connected_validation_coupled_oracle_rows,
    CONNECTED_VALIDATION_NS,
    CONNECTED_VALIDATION_DENSITIES,
    CONNECTED_VALIDATION_SEEDS,
    gw_sdp_relaxation,
    gw_hyperplane_rounding,
    gw_sdp_rows,
    gw_sdp_summary_rows,
    bbht_stage_widths,
    bbht_expected_architecture_cost,
    bbht_operational_rows,
    bbht_summary_rows,
    BBHT_LAMBDA,
    reweight_resource_model,
    resource_scalarization_sensitivity_rows,
    resource_scalarization_summary_rows,
    RESOURCE_TOFFOLI_WEIGHTS,
    DENSE_OPERATIONAL_LEVELS,
    dense_operational_lambda_rows,
    dense_operational_lambda_summary_rows,
)


def test_grover_k0_matches_marked_fraction():
    for rho in (0.01, 0.1, 0.25, 0.5):
        assert abs(grover_probability(rho, 0) - rho) < 1e-12


def test_attenuation_never_increases_probability():
    rho = 0.02
    for k in (0, 1, 5, 10):
        p0 = effective_probability(rho, k, 0.0, 30, 30)
        p1 = effective_probability(rho, k, 0.002, 30, 30)
        assert p1 <= p0 + 1e-15


def test_resource_selector_returns_feasible_k():
    r = select_k_resource_efficiency(2/1024, 0.001, 30, 30, 1, 4, 1, 50)
    assert 0 <= r['k'] <= 50
    assert r['score'] >= 0


def test_exact_suite_shape_and_uniqueness():
    suite = build_exact_suite()
    assert len(suite) == 18
    assert len({x.instance_id for x in suite}) == 18
    assert {x.n for x in suite} == {8, 10, 12}


def test_ground_truth_is_exact_small_instance():
    inst = build_maxcut_instance(8, 0.5, 42)
    assert inst.optimum == int(inst.cut_values.max())
    assert len(inst.optimum_states) >= 1
    assert all(inst.cut_values[x] == inst.optimum for x in inst.optimum_states)


def test_qaoa_state_is_normalized_and_bounded():
    inst = build_maxcut_instance(8, 0.5, 42)
    p = 2
    x = np.array([0.1, 0.2, 0.3, 0.4])
    expected, popt, probs = qaoa_metrics(x, p, inst)
    assert abs(probs.sum() - 1) < 1e-10
    assert 0 <= popt <= 1
    assert 0 <= expected <= inst.optimum


def test_wilson_bounds():
    phat, lo, hi = wilson_interval(5, 10)
    assert 0 <= lo <= phat <= hi <= 1


def test_hillclimb_reference_is_bounded():
    inst = build_maxcut_instance(8, 0.25, 17)
    r = local_hillclimb(inst, starts=32, seed=1)
    assert 0 <= r['median_ratio'] <= 1
    assert 0 <= r['best_ratio'] <= 1
    assert 0 <= r['optimum_hit_fraction'] <= 1


def test_p2_dense_robustness_grid_shape():
    from benchmark import build_exact_suite, dense_resource_robustness
    rows = dense_resource_robustness(build_exact_suite())
    assert len(rows) == 18 * 3 * 13 * 17
    assert all(0 <= r['k_star'] <= 80 for r in rows)
    assert all(0 < r['eta_res'] <= 1 + 1e-12 for r in rows)
    assert {r['target_ratio'] for r in rows} == {0.90, 0.95, 1.00}
    assert all('rho_tau' in r and 'p_target_eff' in r for r in rows)


def test_p2_large_tier_is_analytical_and_monotone_state_counts():
    from benchmark import large_searchspace_tier
    rows = large_searchspace_tier()
    assert len(rows) == 4 * 3 * 13 * 17
    assert {r['model_n'] for r in rows} == {12,16,20,24}
    assert all('not Max-Cut ground truth' in r['evidence_label'] for r in rows)
    assert {r['target_event_count'] for r in rows} == {1, 4, 16}
    assert all('threshold-event' in r['evidence_label'] for r in rows)


def test_p2_simulator_scaling_labels_host_only():
    from benchmark import simulator_scaling_tier
    rows = simulator_scaling_tier(n_values=(8,10))
    assert [r['n'] for r in rows] == [8,10]
    assert all(r['evidence_label'] == 'host simulation scaling only' for r in rows)


def test_threshold_q100_matches_exact_optimum_set():
    inst = build_maxcut_instance(10, 0.5, 42)
    spec = threshold_spec(inst, 1.0)
    assert spec['threshold'] == inst.optimum
    assert abs(spec['rho_tau'] - inst.marked_fraction) < 1e-15
    assert spec['marked_count'] == len(inst.optimum_states)


def test_threshold_marked_fraction_is_monotone_with_quality():
    inst = build_maxcut_instance(10, 0.5, 42)
    rhos = [threshold_spec(inst, q)['rho_tau'] for q in TARGET_RATIOS]
    assert rhos[0] >= rhos[1] >= rhos[2] > 0


def test_target_probability_q100_equals_popt():
    inst = build_maxcut_instance(8, 0.5, 42)
    x = np.array([0.1, 0.2, 0.3, 0.4])
    _, popt, probs = qaoa_metrics(x, 2, inst)
    spec = threshold_spec(inst, 1.0)
    assert abs(target_probability(probs, inst, spec['threshold']) - popt) < 1e-12


def test_hillclimb_emits_common_target_metrics():
    inst = build_maxcut_instance(8, 0.25, 17)
    r = local_hillclimb(inst, starts=32, seed=2)
    for q in TARGET_RATIOS:
        key=f'target_q{int(round(100*q)):03d}_hit_fraction'
        assert key in r
        assert 0 <= r[key] <= 1


def test_threshold_aa_selector_uses_threshold_fraction_not_optimum_fraction():
    inst = build_maxcut_instance(10, 0.5, 42)
    spec = threshold_spec(inst, 0.90)
    assert spec['rho_tau'] >= inst.marked_fraction
    out = select_k_resource_efficiency(spec['rho_tau'], 0.0, 30, 30, 1, 1, 1, 50)
    assert 0 <= out['k'] <= 50


def test_operational_threshold_is_optimum_invariant_in_construction():
    from dataclasses import replace
    inst = build_maxcut_instance(10, 0.5, 42)
    a = operational_threshold_spec(inst, 0.40)
    altered = replace(inst, optimum=inst.optimum + 1000, optimum_states=tuple())
    b = operational_threshold_spec(altered, 0.40)
    assert a['threshold'] == b['threshold']
    assert abs(a['random_expectation_anchor'] - b['random_expectation_anchor']) < 1e-12
    assert abs(a['spectral_upper_bound'] - b['spectral_upper_bound']) < 1e-12
    assert a['construction_uses_C_star'] is False
    assert b['construction_uses_C_star'] is False


def test_operational_threshold_levels_are_monotone():
    inst = build_maxcut_instance(12, 0.75, 17)
    specs = [operational_threshold_spec(inst, level) for level in OPERATIONAL_LEVELS]
    thresholds = [s['threshold'] for s in specs]
    assert thresholds == sorted(thresholds)
    assert random_cut_expectation(inst) <= spectral_maxcut_upper_bound(inst) + 1e-10


def test_operational_threshold_feasibility_is_explicit():
    suite = build_exact_suite()
    rows = [operational_threshold_spec(inst, level) for inst in suite for level in OPERATIONAL_LEVELS]
    assert len(rows) == 18 * 3
    assert all(isinstance(r['feasible_exact_validation'], bool) for r in rows)
    assert all(0 <= r['rho_tau_exact_validation'] <= 1 for r in rows)
    # The construction is allowed to request a threshold that exact validation later finds infeasible.
    assert any(not r['feasible_exact_validation'] for r in rows)


def test_operational_threshold_level_zero_starts_from_random_expectation_anchor():
    inst = build_maxcut_instance(8, 0.25, 17)
    spec = operational_threshold_spec(inst, 0.0)
    assert spec['threshold'] == int(np.ceil(random_cut_expectation(inst) - 1e-12))


def test_rho_estimate_factor_one_matches_oracle_informed_selector():
    inst = build_maxcut_instance(10, 0.5, 42)
    spec = operational_threshold_spec(inst, 0.40)
    rho = spec['rho_tau_exact_validation']
    out = select_k_with_rho_estimate(rho, rho, 0.001, 30, 30, 1, 4, 1, 80)
    assert out['k_selected_from_rho_est'] == out['k_oracle_informed']
    assert abs(out['resource_score_retention'] - 1.0) < 1e-12


def test_rho_misspecification_retention_is_bounded():
    inst = build_maxcut_instance(12, 0.5, 42)
    spec = operational_threshold_spec(inst, 0.40)
    rho = spec['rho_tau_exact_validation']
    for factor in RHO_ESTIMATE_FACTORS:
        out = select_k_with_rho_estimate(rho, min(1.0, rho*factor), 0.0, 30, 30, 1, 1, 1, 80)
        assert 0 <= out['resource_score_retention'] <= 1 + 1e-12


def test_rho_robustness_row_count_and_labels():
    rows = rho_estimation_robustness(build_exact_suite())
    feasible_operational_thresholds = sum(
        operational_threshold_spec(inst, level)['feasible_exact_validation']
        for inst in build_exact_suite() for level in OPERATIONAL_LEVELS
    )
    assert len(rows) == feasible_operational_thresholds * 2 * 2 * len(RHO_ESTIMATE_FACTORS)
    assert all('retrospective regret' in r['evidence_label'] for r in rows)
    assert all(0 <= r['resource_score_retention'] <= 1 + 1e-12 for r in rows)


def test_oracle_resource_model_is_positive_and_explicit():
    inst = build_maxcut_instance(10, 0.5, 42)
    spec = operational_threshold_spec(inst, 0.40)
    r = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
    assert r['accumulator_bits'] >= 1
    assert r['total_logical_qubits_model'] > inst.n
    assert r['oracle_toffoli_model'] > 0
    assert r['oracle_cnot_model'] > 0
    assert r['oracle_logical_depth_model'] > 0
    assert r['oracle_gate_equivalent_model'] > r['diffusion_gate_equivalent_model']
    assert 'not compiled' in r['count_model_label']


def test_oracle_resource_model_scales_with_edges_on_fixed_n():
    sparse = build_maxcut_instance(10, 0.25, 42)
    dense = build_maxcut_instance(10, 0.75, 42)
    rs = maxcut_threshold_oracle_resource_model(sparse, 1)
    rd = maxcut_threshold_oracle_resource_model(dense, 1)
    assert dense.n_edges > sparse.n_edges
    assert rd['oracle_toffoli_model'] > rs['oracle_toffoli_model']
    assert rd['oracle_logical_depth_model'] > rs['oracle_logical_depth_model']


def test_architecture_coupled_selector_uses_model_cost_and_depth():
    inst = build_maxcut_instance(10, 0.5, 42)
    spec = operational_threshold_spec(inst, 0.40)
    rho = spec['rho_tau_exact_validation']
    rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
    out = select_k_architecture_coupled(rho, 1e-4, rm, 80)
    assert 0 <= out['k'] < 80
    assert out['gate_equivalent_cost'] >= rm['prep_gate_equivalent_model']
    assert out['logical_depth_model'] >= rm['prep_logical_depth_model']
    assert 0 < out['p_eff'] <= 1


def test_oracle_resource_and_coupled_row_counts():
    suite = build_exact_suite()
    rr = oracle_resource_rows(suite)
    assert len(rr) == 18 * len(OPERATIONAL_LEVELS)
    feasible = sum(operational_threshold_spec(inst, level)['feasible_exact_validation'] for inst in suite for level in OPERATIONAL_LEVELS)
    cc = coupled_oracle_depth_sensitivity(suite)
    assert len(cc) == feasible * len(ORACLE_ATTENUATION_LEVELS)
    assert all('not compiled' in x['evidence_label'] for x in cc)
    assert all(0 <= x['k_star'] < 80 for x in cc)


def test_fixed_overhead_zero_preserves_architecture_selector_contract():
    inst = build_maxcut_instance(10, 0.5, 42)
    spec = operational_threshold_spec(inst, 0.40)
    rho = spec['rho_tau_exact_validation']
    rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
    a = select_k_architecture_coupled(rho, 1e-4, rm, 80)
    b = select_k_architecture_coupled(rho, 1e-4, rm, 80, fixed_overhead_gate_equiv=0.0)
    assert a['k'] == b['k']
    assert abs(a['score'] - b['score']) < 1e-15
    assert abs(a['gate_equivalent_cost'] - b['gate_equivalent_cost']) < 1e-12


def test_fixed_overhead_sensitivity_exposes_nonzero_amplification_region():
    suite = build_exact_suite()
    rows = fixed_overhead_sensitivity_rows(suite, 'primary', eps_levels=(0.0,))
    feasible = sum(
        operational_threshold_spec(inst, level)['feasible_exact_validation']
        for inst in suite for level in OPERATIONAL_LEVELS
    )
    assert len(rows) == feasible * len(FIXED_OVERHEAD_ORACLE_RATIOS)
    zero = [r for r in rows if r['fixed_overhead_ratio_to_oracle'] == 0.0]
    half = [r for r in rows if r['fixed_overhead_ratio_to_oracle'] == 0.5]
    assert all(r['k_star'] == 0 for r in zero)
    assert all(r['k_star'] > 0 for r in half)
    be = [r['break_even_fixed_overhead_ratio_to_oracle'] for r in zero]
    assert all(0 <= x < 1 for x in be)
    assert 0.10 < float(np.median(be)) < 0.25
    assert all('not measured backend cost' in r['evidence_label'] for r in rows)


def test_architecture_attenuation_coupling_penalizes_survival():
    inst = build_maxcut_instance(12, 0.75, 42)
    spec = operational_threshold_spec(inst, 0.40)
    rho = spec['rho_tau_exact_validation']
    rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
    b = select_k_architecture_coupled(rho, 5e-4, rm, 80)
    assert b['survival_model'] <= 1.0
    assert b['logical_depth_model'] == rm['prep_logical_depth_model'] + b['k'] * rm['iteration_logical_depth_model']



def test_simulated_annealing_is_deterministic_and_budgeted():
    inst = build_maxcut_instance(8, 0.5, 42)
    a = simulated_annealing_run(inst, seed=12345, eval_budget=257)
    b = simulated_annealing_run(inst, seed=12345, eval_budget=257)
    assert a == b
    assert a['objective_evaluations'] == 257
    assert 0 <= a['best_cut'] <= inst.optimum


def test_tabu_search_is_deterministic_and_respects_budget():
    inst = build_maxcut_instance(10, 0.5, 42)
    a = tabu_search_run(inst, seed=9876, eval_budget=513)
    b = tabu_search_run(inst, seed=9876, eval_budget=513)
    assert a == b
    assert a['objective_evaluations'] <= 513
    assert a['objective_evaluations'] > 513 - inst.n - 1
    assert 0 <= a['best_cut'] <= inst.optimum


def test_budgeted_classical_search_does_not_use_stored_optimum_for_search():
    from dataclasses import replace
    inst = build_maxcut_instance(8, 0.25, 17)
    altered = replace(inst, optimum=inst.optimum + 999, optimum_states=tuple())
    sa_a = simulated_annealing_run(inst, seed=444, eval_budget=129)
    sa_b = simulated_annealing_run(altered, seed=444, eval_budget=129)
    tb_a = tabu_search_run(inst, seed=555, eval_budget=129)
    tb_b = tabu_search_run(altered, seed=555, eval_budget=129)
    assert sa_a == sa_b
    assert tb_a == tb_b


def test_budgeted_classical_suite_row_counts_and_labels():
    suite = build_exact_suite()
    raw, summary = run_budgeted_classical_suite(suite, runs=4, eval_budget=129, base_seed=77)
    assert len(raw) == 18 * 2 * 4
    assert len(summary) == 18 * 2
    assert {r['method'] for r in summary} == {'simulated_annealing', 'tabu_search'}
    assert all(0 <= float(r['median_best_ratio']) <= 1 for r in summary)
    assert all(0 <= float(r['optimum_hit_fraction']) <= 1 for r in summary)
    assert all('not a quantum-resource match' in r['evidence_label'] for r in summary)


def test_budgeted_classical_default_contract():
    assert CLASSICAL_EVAL_BUDGET == 4096
    assert CLASSICAL_BUDGETED_RUNS == 64



def test_qaoa_initialization_is_instance_conditioned_and_deterministic():
    a = build_maxcut_instance(8, 0.25, 42)
    b = build_maxcut_instance(8, 0.50, 42)
    xa1 = qaoa_initial_params(a, 2, 3)
    xa2 = qaoa_initial_params(a, 2, 3)
    xb = qaoa_initial_params(b, 2, 3)
    assert QAOA_INIT_STREAM_VERSION == 1
    assert np.array_equal(xa1, xa2)
    assert not np.array_equal(xa1, xb)


def test_qaoa_initialization_changes_with_depth_or_external_seed():
    inst = build_maxcut_instance(8, 0.50, 17)
    x11 = qaoa_initial_params(inst, 1, 1)
    x12 = qaoa_initial_params(inst, 1, 2)
    x21 = qaoa_initial_params(inst, 2, 1)
    assert not np.array_equal(x11, x12)
    assert len(x21) == 4
    assert not np.array_equal(x11, x21[:2])


def test_qaoa_budgeted_optimizer_is_deterministic_in_quality_fields():
    inst = build_maxcut_instance(8, 0.25, 42)
    a = run_qaoa_budgeted_one(inst, 1, 2, 'COBYLA', eval_budget=24)
    b = run_qaoa_budgeted_one(inst, 1, 2, 'COBYLA', eval_budget=24)
    assert a['initial_params'] == b['initial_params']
    assert a['best_seen_params'] == b['best_seen_params']
    assert abs(a['approx_ratio'] - b['approx_ratio']) < 1e-14
    assert a['objective_evaluations_used'] == b['objective_evaluations_used'] <= 24


def test_qaoa_optimizer_pair_uses_same_initialization_and_strict_cap():
    inst = build_maxcut_instance(8, 0.5, 42)
    a = run_qaoa_budgeted_one(inst, 2, 3, 'L-BFGS-B', eval_budget=32)
    b = run_qaoa_budgeted_one(inst, 2, 3, 'COBYLA', eval_budget=32)
    assert a['initial_params'] == b['initial_params']
    assert a['objective_evaluations_used'] <= 32
    assert b['objective_evaluations_used'] <= 32
    assert a['objective_eval_budget'] == b['objective_eval_budget'] == 32
    assert 'not hardware runtime' in a['evidence_label']
    assert 'not hardware runtime' in b['evidence_label']


def test_qaoa_optimizer_budget_suite_contract_small():
    suite = [build_maxcut_instance(8, 0.25, 42)]
    raw = run_qaoa_optimizer_budget_suite(suite, depths=(1,), optimizer_seeds=range(2), eval_budget=20)
    assert len(raw) == 1 * 1 * 2 * len(QAOA_OPTIMIZER_METHODS)
    assert {r['optimizer'] for r in raw} == set(QAOA_OPTIMIZER_METHODS)
    assert all(r['objective_evaluations_used'] <= 20 for r in raw)
    inst_rows, agg = summarize_qaoa_optimizer_budget(raw)
    assert len(inst_rows) == len(QAOA_OPTIMIZER_METHODS)
    assert len(agg) == len(QAOA_OPTIMIZER_METHODS)


def test_qaoa_optimizer_budget_default_contract():
    assert QAOA_OPTIMIZER_EVAL_BUDGET == 128
    assert QAOA_OPTIMIZER_METHODS == ('L-BFGS-B', 'COBYLA')



def test_qaoa_optimizer_paired_delta_contract():
    suite = [build_maxcut_instance(8, 0.25, 42)]
    raw = run_qaoa_optimizer_budget_suite(suite, depths=(1,), optimizer_seeds=range(3), eval_budget=20)
    paired = qaoa_optimizer_paired_deltas(raw)
    assert len(paired) == 3
    assert all('delta_cobyla_minus_lbfgsb' in r for r in paired)
    assert all('identical initialization' in r['evidence_label'] for r in paired)



def test_j_holm_adjustment_is_bounded_and_not_smaller_than_raw():
    raw = [0.01, 0.04, 0.2]
    adj = holm_adjust(raw)
    assert len(adj) == 3
    assert all(0 <= x <= 1 for x in adj)
    assert all(a + 1e-15 >= p for a, p in zip(adj, raw))


def test_j_rank_biserial_sign_and_bounds():
    assert abs(paired_rank_biserial([1, 2, 3]) - 1.0) < 1e-12
    assert abs(paired_rank_biserial([-1, -2, -3]) + 1.0) < 1e-12
    mixed = paired_rank_biserial([-2, 1, 3])
    assert -1 <= mixed <= 1


def test_j_bootstrap_median_ci_is_deterministic():
    d = [-0.1, 0.0, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08]
    a = bootstrap_median_ci(d, resamples=500, seed=123)
    b = bootstrap_median_ci(d, resamples=500, seed=123)
    assert a == b
    assert a[0] <= np.median(d) <= a[1]


def test_j_depth_inference_uses_instance_clustered_units():
    raw = []
    for i in range(4):
        iid = f'i{i}'
        for p in (1, 2, 3):
            for seed in range(3):
                raw.append({'instance_id': iid, 'p': p, 'optimizer_seed': seed, 'approx_ratio': 0.5 + 0.02*p + 0.001*seed + 0.002*i})
    rows = qaoa_depth_inference(raw, bootstrap_resamples=500, seed=99)
    assert len(rows) == 3
    assert all(r['n_instances'] == 4 for r in rows)
    assert all('not population generalization' in r['evidence_label'] for r in rows)
    assert all(0 <= r['p_holm'] <= 1 for r in rows)


def test_j_optimizer_inference_collapses_initializations_within_instance():
    paired = []
    for i in range(4):
        for p in (1, 2, 3):
            for seed in range(3):
                paired.append({'instance_id': f'i{i}', 'p': p, 'optimizer_seed': seed, 'delta_cobyla_minus_lbfgsb': 0.01*p + 0.001*seed - 0.002*i})
    inst, rows = qaoa_optimizer_inference(paired, bootstrap_resamples=500, seed=101)
    assert len(inst) == 4 * 3
    assert all(r['paired_initializations'] == 3 for r in inst)
    assert len(rows) == 3
    assert all(r['n_instances'] == 4 for r in rows)
    assert all(0 <= r['p_holm'] <= 1 for r in rows)


def test_j_default_bootstrap_contract():
    assert J_BOOTSTRAP_RESAMPLES == 20000


# K/L expanded exact coverage tests
def test_kl_expanded_random_suite_has_five_seeds_and_45_instances():
    suite = build_expanded_random_suite()
    assert len(suite) == 45
    assert {x.seed for x in suite} == set(EXPANDED_RANDOM_SEEDS)
    assert {x.n for x in suite} == {8, 10, 12}
    assert {round(x.density_target, 2) for x in suite} == {0.25, 0.50, 0.75}
    assert all(x.family == "random_fixed_density" for x in suite)


def test_random_fixed_density_generation_is_reproducible_per_configuration():
    a = build_maxcut_instance(10, 0.50, 42)
    b = build_maxcut_instance(10, 0.50, 42)
    assert a.edges == b.edges
    assert a.optimum == b.optimum
    assert a.optimum_states == b.optimum_states


def test_random_density_streams_are_not_nested_prefix_graphs():
    for n in (8, 10, 12):
        for seed in EXPANDED_RANDOM_SEEDS:
            instances = {d: build_maxcut_instance(n, d, seed) for d in (0.25, 0.50, 0.75)}
            edge_sets = {d: {(i, j, w) for i, j, w in inst.edges} for d, inst in instances.items()}
            assert not edge_sets[0.25].issubset(edge_sets[0.50])
            assert not edge_sets[0.50].issubset(edge_sets[0.75])


def test_kl_original_18_are_unchanged_subset_of_expanded_random_suite():
    original = {x.instance_id: x for x in build_exact_suite()}
    expanded = {x.instance_id: x for x in build_expanded_random_suite()}
    assert set(original).issubset(expanded)
    for iid, a in original.items():
        b = expanded[iid]
        assert a.edges == b.edges
        assert a.optimum == b.optimum
        assert a.optimum_states == b.optimum_states


def test_kl_structured_suite_shape_families_and_simple_graphs():
    suite = build_structured_suite()
    assert len(suite) == 18
    assert {x.family for x in suite} == set(STRUCTURED_FAMILIES)
    assert {x.n for x in suite} == {8, 10, 12}
    assert {x.seed for x in suite} == {17, 42}
    for inst in suite:
        pairs = [(min(i,j), max(i,j)) for i,j,_ in inst.edges]
        assert len(pairs) == len(set(pairs))
        assert all(i != j for i,j in pairs)
        assert inst.optimum == int(inst.cut_values.max())


def test_kl_combined_coverage_is_63_unique_exact_instances():
    suite = build_coverage_suite()
    assert len(suite) == 63
    assert len({x.instance_id for x in suite}) == 63
    rows = coverage_ground_truth_rows(suite)
    assert len(rows) == 63
    assert {r["coverage_group"] for r in rows} == {"random_seed_expansion", "structured_family"}


def test_kl_operational_threshold_coverage_has_189_rows_and_no_cstar_in_construction():
    rows = coverage_operational_threshold_rows(build_coverage_suite())
    assert len(rows) == 63 * len(OPERATIONAL_LEVELS)
    assert all(r["construction_uses_C_star"] is False for r in rows)
    assert all("expanded coverage" in r["evidence_label"] for r in rows)


def test_kl_structured_thresholds_can_be_infeasible_without_clipping():
    rows = coverage_operational_threshold_rows(build_structured_suite())
    assert all(isinstance(r["feasible_exact_validation"], bool) for r in rows)
    # No assumption is made that all graph/level combinations must be feasible.
    assert len(rows) == 18 * len(OPERATIONAL_LEVELS)


def test_kl_architecture_coupled_coverage_is_bounded_and_labeled():
    rows = coverage_coupled_oracle_rows(build_structured_suite(), eps_levels=(0.0,))
    assert rows
    assert all(0 <= int(r["k_star"]) <= 80 for r in rows)
    assert all("not compiled or hardware measured" in r["evidence_label"] for r in rows)


def test_kl_coverage_graph_ledger_matches_edge_counts():
    suite = build_coverage_suite()
    rows = coverage_graph_rows(suite)
    assert len(rows) == sum(x.n_edges for x in suite)
    assert all(int(r["i"]) < int(r["j"]) for r in rows)


# Reviewer-audit connected/non-bipartite validation tier
def test_graph_structure_audit_exposes_primary_connectivity_and_bipartiteness():
    rows = graph_diagnostics_rows(build_exact_suite(), 'primary')
    assert len(rows) == 18
    assert sum(not bool(r['connected']) for r in rows) == 5
    assert sum(bool(r['bipartite']) for r in rows) == 2
    assert all(int(r['component_count']) >= 1 for r in rows)
    assert all(int(r['component_flip_symmetry_lower_bound']) >= 2 for r in rows)


def test_connected_validation_constructor_is_deterministic_and_structurally_filtered():
    a = build_connected_validation_instance(10, 0.25, 42)
    b = build_connected_validation_instance(10, 0.25, 42)
    assert a.edges == b.edges
    assert a.optimum == b.optimum
    m = graph_structure_metrics(a)
    assert m['connected'] is True
    assert m['bipartite'] is False
    assert m['isolated_vertices'] == 0
    assert m['cycle_rank'] >= 1


def test_connected_validation_suite_has_45_exact_connected_nonbipartite_instances():
    suite = build_connected_validation_suite()
    assert len(suite) == 45
    assert len({x.instance_id for x in suite}) == 45
    assert {x.n for x in suite} == set(CONNECTED_VALIDATION_NS)
    assert {round(x.density_target, 2) for x in suite} == set(CONNECTED_VALIDATION_DENSITIES)
    assert {x.seed for x in suite} == set(CONNECTED_VALIDATION_SEEDS)
    metrics = [graph_structure_metrics(x) for x in suite]
    assert all(m['connected'] and not m['bipartite'] for m in metrics)
    assert all(m['isolated_vertices'] == 0 for m in metrics)


def test_connected_validation_rows_preserve_exact_and_operational_claim_boundaries():
    suite = build_connected_validation_suite()
    gt = connected_validation_ground_truth_rows(suite)
    op = connected_validation_operational_threshold_rows(suite)
    cc = connected_validation_coupled_oracle_rows(suite, eps_levels=(0.0,))
    assert len(gt) == 45
    assert len(op) == 45 * len(OPERATIONAL_LEVELS)
    assert all(r['construction_uses_C_star'] is False for r in op)
    assert all(r['connected'] and not r['bipartite'] for r in gt)
    assert cc
    assert all('not compiled or hardware measured' in r['evidence_label'] for r in cc)


# Reviewer-audit canonical Goemans--Williamson SDP baseline
def test_gw_sdp_primal_dual_certificate_brackets_exact_maxcut():
    inst = build_maxcut_instance(8, 0.25, 17)
    solved = gw_sdp_relaxation(inst, starts=4, max_sweeps=1200)
    assert solved['certified'] is True
    assert solved['primal_value'] <= solved['dual_upper_bound'] + 1e-8
    assert solved['dual_upper_bound'] + 1e-7 >= inst.optimum
    assert solved['primal_dual_gap'] <= 1e-6
    # This particular tree instance has an integral SDP relaxation.
    assert abs(solved['dual_upper_bound'] - inst.optimum) < 1e-5


def test_gw_rounding_is_seeded_feasible_and_never_exceeds_exact_optimum():
    inst = build_maxcut_instance(8, 0.50, 17)
    solved = gw_sdp_relaxation(inst, starts=4, max_sweeps=1200)
    a = gw_hyperplane_rounding(inst, solved['vectors'], samples=512)
    b = gw_hyperplane_rounding(inst, solved['vectors'], samples=512)
    assert a == b
    assert 0 <= a['rounding_best_cut'] <= inst.optimum
    assert 0.0 <= a['rounding_optimum_hit_fraction'] <= 1.0
    assert a['rounding_best_ratio_to_Cstar'] <= 1.0 + 1e-12


def test_gw_rows_are_certified_and_summary_preserves_tier_counts():
    suite = build_exact_suite()[:3]
    rows = gw_sdp_rows(suite, 'test_primary')
    assert len(rows) == 3
    assert all(r['sdp_numerically_certified'] for r in rows)
    assert all(float(r['sdp_dual_upper_bound']) + 1e-6 >= float(r['C_star']) for r in rows)
    summary = gw_sdp_summary_rows(rows)
    overall = [r for r in summary if r['n'] == 'all'][0]
    assert overall['instances'] == 3
    assert overall['certified_instances'] == 3


def test_bbht_schedule_is_rho_independent_and_saturates_at_sqrt_n():
    widths = bbht_stage_widths(256)
    assert widths[0] == 1
    assert widths[-1] == 16
    assert all(a <= b for a, b in zip(widths, widths[1:]))
    assert 1.0 < BBHT_LAMBDA < 4.0 / 3.0


def test_bbht_expected_cost_is_finite_and_respects_classical_bbht_bound():
    inst = build_maxcut_instance(10, 0.50, 17)
    spec = operational_threshold_spec(inst, 0.55)
    rho = float(spec['rho_tau_exact_validation'])
    assert 0 < rho <= 0.75
    rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
    out = bbht_expected_architecture_cost(rho, inst.state_count, rm)
    assert out['eventual_success_probability'] == 1.0
    assert out['expected_trials_to_success'] > 0
    assert out['expected_gate_equivalent_to_success'] > 0
    # Boyer et al. give a 4.5*sqrt(N/M) worst-case Grover-iteration envelope for lambda=6/5.
    assert out['expected_grover_iterations_to_success'] <= 4.5 / np.sqrt(rho) + 1e-12


def test_bbht_operational_rows_cover_primary_and_connected_validation_without_rho_input():
    primary = bbht_operational_rows(build_exact_suite(), 'primary', eps_levels=(0.0,), fixed_overhead_ratios=(0.0,))
    connected = bbht_operational_rows(build_connected_validation_suite(), 'connected_validation', eps_levels=(0.0,), fixed_overhead_ratios=(0.0,))
    assert len(primary) == 51
    assert len(connected) == 126
    assert all(r['bbht_schedule_uses_rho'] is False for r in primary + connected)
    assert all(r['bbht_expected_resource_per_target_hit_model'] > 0 for r in primary + connected)
    assert all(r['uniform_expected_resource_per_target_hit_model'] > 0 for r in primary + connected)
    assert all(r['oracle_informed_expected_resource_per_target_hit_model'] > 0 for r in primary + connected)


def test_bbht_summary_has_expected_scope_rows():
    rows = bbht_operational_rows(build_exact_suite(), 'primary', eps_levels=(0.0,), fixed_overhead_ratios=(0.0, 0.25))
    summary = bbht_summary_rows(rows)
    assert len(summary) == 2
    assert {r['fixed_overhead_ratio_to_oracle'] for r in summary} == {0.0, 0.25}
    assert all(r['feasible_threshold_conditions'] == 51 for r in summary)


def test_resource_reweight_alpha6_reproduces_canonical_gate_equivalent_counts():
    inst = build_maxcut_instance(10, 0.50, 17)
    spec = operational_threshold_spec(inst, 0.40)
    rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
    r6 = reweight_resource_model(rm, 6.0)
    assert r6['oracle_gate_equivalent_model'] == rm['oracle_gate_equivalent_model']
    assert r6['diffusion_gate_equivalent_model'] == rm['diffusion_gate_equivalent_model']
    assert r6['iteration_gate_equivalent_model'] == rm['iteration_gate_equivalent_model']
    assert r6['oracle_toffoli_model'] == rm['oracle_toffoli_model']
    assert r6['oracle_logical_depth_model'] == rm['oracle_logical_depth_model']


def test_resource_reweight_changes_only_scalar_projection_not_raw_counts():
    inst = build_maxcut_instance(8, 0.75, 42)
    spec = operational_threshold_spec(inst, 0.25)
    rm = maxcut_threshold_oracle_resource_model(inst, spec['threshold'])
    r1 = reweight_resource_model(rm, 1.0)
    r10 = reweight_resource_model(rm, 10.0)
    assert r1['oracle_gate_equivalent_model'] < r10['oracle_gate_equivalent_model']
    for key in ('oracle_toffoli_model','oracle_cnot_model','oracle_single_qubit_model','oracle_logical_depth_model','total_logical_qubits_model'):
        assert r1[key] == r10[key] == rm[key]


def test_resource_scalarization_rows_cover_declared_grid_and_zero_overhead_boundary():
    rows = resource_scalarization_sensitivity_rows(build_exact_suite(), 'primary')
    assert len(rows) == 51 * len(RESOURCE_TOFFOLI_WEIGHTS) * 2 * 4
    zero = [r for r in rows if abs(r['eps_per_logical_depth_model']) < 1e-15 and abs(r['fixed_overhead_ratio_to_canonical_alpha6_oracle']) < 1e-15]
    assert len(zero) == 51 * len(RESOURCE_TOFFOLI_WEIGHTS)
    assert all(r['k_star'] == 0 for r in zero)


def test_resource_scalarization_summary_reports_all_alpha_scope_coordinates():
    p = resource_scalarization_sensitivity_rows(build_exact_suite(), 'primary', eps_levels=(0.0,), canonical_fixed_ratios=(0.0,0.25))
    c = resource_scalarization_sensitivity_rows(build_connected_validation_suite(), 'connected_validation', eps_levels=(0.0,), canonical_fixed_ratios=(0.0,0.25))
    summary = resource_scalarization_summary_rows(p+c)
    assert len(summary) == 2 * len(RESOURCE_TOFFOLI_WEIGHTS) * 2
    assert {r['scope'] for r in summary} == {'primary','connected_validation'}


def test_classical_budget_curve_small_grid_has_expected_rows_and_metadata():
    suite = build_exact_suite()[:2]
    raw, summary, agg = run_classical_budget_curve(suite, budgets=(64,128), runs=3)
    assert len(raw) == 2 * 2 * 2 * 3
    assert len(summary) == 2 * 2 * 2
    assert len(agg) == 2 * 2
    assert {r['curve_budget'] for r in raw} == {64,128}
    assert all(float(r['budget_over_state_count']) > 0 for r in summary)


def test_classical_budget_curve_4096_endpoint_matches_single_budget_runner():
    suite = build_exact_suite()[:1]
    raw0, summary0 = run_budgeted_classical_suite(suite, runs=4, eval_budget=4096)
    raw, summary, agg = run_classical_budget_curve(suite, budgets=(4096,), runs=4)
    key=lambda r:(r['method'],r['run_index'])
    assert [(r['best_cut'],r['objective_evaluations']) for r in sorted(raw0,key=key)] == [(r['best_cut'],r['objective_evaluations']) for r in sorted(raw,key=key)]
    assert len(agg) == 2


def test_declared_classical_budget_curve_spans_sub_state_space_to_full_n12_space():
    assert CLASSICAL_BUDGET_CURVE == (64,128,256,512,1024,4096)
    assert CLASSICAL_BUDGET_CURVE[-1] == 2**12


def test_dense_operational_levels_cover_full_unit_interval():
    assert DENSE_OPERATIONAL_LEVELS == tuple(round(i * 0.05, 2) for i in range(21))
    assert set(OPERATIONAL_LEVELS).issubset(set(DENSE_OPERATIONAL_LEVELS))


def test_dense_lambda_rows_are_complete_and_do_not_use_cstar_for_construction():
    suite = build_exact_suite()[:2]
    levels = (0.0, 0.25, 0.4, 0.55, 1.0)
    rows = dense_operational_lambda_rows(suite, "test", levels=levels)
    assert len(rows) == len(suite) * len(levels)
    assert all(r["construction_uses_C_star"] is False for r in rows)
    assert all(r["tier"] == "test" for r in rows)


def test_dense_lambda_summary_matches_declared_operational_points():
    suite = build_exact_suite()
    rows = dense_operational_lambda_rows(suite, "primary", levels=OPERATIONAL_LEVELS)
    summary = dense_operational_lambda_summary_rows(rows)
    by_level = {round(float(r["operational_level"]), 2): r for r in summary}
    assert int(by_level[0.25]["feasible_count"]) == 18
    assert int(by_level[0.40]["feasible_count"]) == 18
    assert int(by_level[0.55]["feasible_count"]) == 15
    assert all(float(r["zero_fixed_zero_attenuation_nonzero_k_fraction"]) == 0.0 for r in summary if int(r["feasible_count"]) > 0)


def test_qaoa_stability_declares_twenty_nested_starts():
    assert QAOA_STABILITY_STARTS == 20
    inst = build_exact_suite()[0]
    first_five = [qaoa_initial_params(inst, 2, s) for s in range(5)]
    first_twenty = [qaoa_initial_params(inst, 2, s) for s in range(QAOA_STABILITY_STARTS)]
    assert all(np.array_equal(a, b) for a, b in zip(first_five, first_twenty[:5]))
    assert len({tuple(np.round(x, 14)) for x in first_twenty}) == 20

def test_qaoa_stability_streams_remain_instance_conditioned():
    a, b = build_exact_suite()[:2]
    for s in (0, 5, 19):
        assert not np.array_equal(qaoa_initial_params(a, 3, s), qaoa_initial_params(b, 3, s))
