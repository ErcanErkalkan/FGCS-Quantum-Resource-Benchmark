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
