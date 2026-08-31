from pathlib import Path
import csv
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / 'results'


def read_csv(name):
    with (R / name).open(encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write(name, lines):
    # FGCS final source uses the compact two-column 5p layout.  Generated
    # tabular fragments are therefore scaled to the active column width at
    # render time, rather than patched after generation.
    wrapped = [r'\resizebox{\columnwidth}{!}{%'] + list(lines)
    if wrapped[-1] == r'\end{tabular}':
        wrapped[-1] = r'\end{tabular}%'
    wrapped.append('}')
    (R / name).write_text('\n'.join(wrapped) + '\n', encoding='utf-8')

ROW_END = r'\\'

gt = read_csv('maxcut_ground_truth.csv')
by_n = []
for n in sorted({int(x['n']) for x in gt}):
    rr = [x for x in gt if int(x['n']) == n]
    rhos = np.array([float(x['rho_opt']) for x in rr])
    by_n.append((n, len(rr), min(int(x['n_edges']) for x in rr), max(int(x['n_edges']) for x in rr), float(np.median(rhos))))
lines = [r'\begin{tabular}{rrrrr}', r'\toprule', r'$n$ & instances & edge range & states & median $\rho_{opt}$ \\', r'\midrule']
for n, count, emin, emax, rho in by_n:
    lines.append(f'{n} & {count} & {emin}--{emax} & {1<<n} & {rho:.5f} {ROW_END}')
lines += [r'\bottomrule', r'\end{tabular}']
write('table_suite.tex', lines)


# Operational threshold construction independent of C*. Exact quantities below are retrospective validation only.
op = read_csv('operational_thresholds.csv')
lines = [r'\begin{tabular}{rrrrrr}', r'\toprule', r'$\lambda$ & feasible & median $\tau/C^*$ & range $\tau/C^*$ & median $\rho_\tau$ & construction \\', r'\midrule']
for level in (0.25, 0.40, 0.55):
    rr = [x for x in op if abs(float(x['operational_level'])-level)<1e-12 and x['feasible_exact_validation'].lower()=='true']
    q = np.array([float(x['realized_quality_ratio_exact_validation']) for x in rr])
    rho = np.array([float(x['rho_tau_exact_validation']) for x in rr])
    lines.append(f"{level:.2f} & {len(rr)}/18 & {np.median(q):.3f} & {q.min():.3f}--{q.max():.3f} & {np.median(rho):.4f} & no $C^*$ {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_operational_threshold.tex', lines)

# Operational common target metric on all 18 primary instances, summarized over thresholds
# found feasible by exact Tier-I validation. AA remains an oracle-informed rho reference.
otm = read_csv('operational_target_metric_summary.csv')
lines = [r'\begin{tabular}{rrrrrrrr}', r'\toprule', r'$\lambda$ & feas. & uniform & AA ref. & HC & QAOA $p=1$ & $p=2$ & $p=3$ \\', r'\midrule']
for level in (0.25, 0.40, 0.55):
    base = [x for x in otm if abs(float(x['operational_level'])-level)<1e-12 and x['feasible_exact_validation'].lower()=='true']
    feasible_ids = sorted({x['instance_id'] for x in base})
    def med(method, prefix=None):
        z=[float(x['p_target']) for x in base if x['method']==method and (prefix is None or x['configuration'].startswith(prefix))]
        return float(np.median(z))
    lines.append(f'{level:.2f} & {len(feasible_ids)}/18 & {med("uniform"):.4f} & {med("amplitude_amplification"):.4f} & {med("hillclimb"):.4f} & {med("qaoa","p=1;"):.4f} & {med("qaoa","p=2;"):.4f} & {med("qaoa","p=3;"):.4f} {ROW_END}')
lines += [r'\bottomrule', r'\end{tabular}']
write('table_operational_metric.tex', lines)

aa = read_csv('amplitude_amplification_sensitivity.csv')
# Main table uses the 95% quality-threshold reference; all three targets remain in raw CSV.
aa95 = [x for x in aa if abs(float(x['target_ratio']) - 0.95) < 1e-12]
keys = sorted({(float(x['eps_model']), float(x['oracle_cost_norm'])) for x in aa95})
lines = [r'\begin{tabular}{rrrrr}', r'\toprule', r'$\varepsilon_{model}$ & oracle cost & median $k^*$ & IQR $k^*$ & median $\eta_{res}$ \\', r'\midrule']
for eps, oc in keys:
    rr = [x for x in aa95 if float(x['eps_model']) == eps and float(x['oracle_cost_norm']) == oc]
    vals = np.array([int(x['k_star_resource_eff']) for x in rr])
    et = np.array([float(x['eta_res']) for x in rr])
    q1, med, q3 = np.quantile(vals, [0.25, 0.5, 0.75])
    lines.append(f'{eps:.4f} & {oc:.0f} & {med:.1f} & {q1:.1f}--{q3:.1f} & {np.median(et):.3f} {ROW_END}')
lines += [r'\bottomrule', r'\end{tabular}']
write('table_aa_aggregate.tex', lines)

# Common target-quality probability metric on all 18 primary instances.
tm = read_csv('target_metric_summary.csv')
lines = [r'\begin{tabular}{rrrrrrr}', r'\toprule', r'target & uniform & AA & hill climb & QAOA $p=1$ & $p=2$ & $p=3$ \\', r'\midrule']
for target in (0.90, 0.95, 1.00):
    rr = [x for x in tm if abs(float(x['target_ratio'])-target)<1e-12]
    def med(method, prefix=None):
        z=[float(x['p_target']) for x in rr if x['method']==method and (prefix is None or x['configuration'].startswith(prefix))]
        return float(np.median(z))
    lines.append(f'{target:.2f} & {med("uniform"):.4f} & {med("amplitude_amplification"):.4f} & {med("hillclimb"):.4f} & {med("qaoa","p=1;"):.4f} & {med("qaoa","p=2;"):.4f} & {med("qaoa","p=3;"):.4f} {ROW_END}')
lines += [r'\bottomrule', r'\end{tabular}']
write('table_target_metric.tex', lines)

q = read_csv('qaoa_aggregate_summary.csv')
lines = [r'\begin{tabular}{rrrrr}', r'\toprule', r'$p$ & instances & runs & median instance AR & median instance $P_{opt}$ \\', r'\midrule']
for x in q:
    lines.append(f"{x['p']} & {x['instances']} & {x['optimizer_runs']} & {float(x['instance_median_approx_ratio']):.3f} & {float(x['instance_median_p_opt']):.4f} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_qaoa_aggregate.tex', lines)


# H: paired QAOA optimizer robustness under an equal objective-evaluation cap.
qo = read_csv('qaoa_optimizer_budget_aggregate.csv')
lines = [r'\begin{tabular}{lrrrrr}', r'\toprule', r'optimizer & $p$ & runs & median inst. AR & median evals & budget-exhaust. \\', r'\midrule']
for x in qo:
    lines.append(f"{x['optimizer']} & {x['p']} & {x['runs']} & {float(x['median_instance_approx_ratio']):.3f} & {float(x['median_objective_evaluations_used']):.0f} & {float(x['budget_exhausted_fraction']):.3f} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_qaoa_optimizer_budget.tex', lines)

cl = read_csv('classical_hillclimb.csv')
gt_lookup = {x['instance_id']: x for x in gt}
lines = [r'\begin{tabular}{rrrr}', r'\toprule', r'$n$ & instances & median local-search ratio & median optimum-hit fraction \\', r'\midrule']
for n in sorted({int(gt_lookup[x['instance_id']]['n']) for x in cl}):
    rr = [x for x in cl if int(gt_lookup[x['instance_id']]['n']) == n]
    mr = np.median([float(x['median_ratio']) for x in rr])
    mh = np.median([float(x['optimum_hit_fraction']) for x in rr])
    lines.append(f'{n} & {len(rr)} & {mr:.3f} & {mh:.3f} {ROW_END}')
lines += [r'\bottomrule', r'\end{tabular}']
write('table_classical.tex', lines)

# G: stronger fixed-objective-evaluation-budget classical references.
cb = read_csv('classical_budgeted_summary.csv')
lines = [r'\begin{tabular}{lrrrrr}', r'\toprule', r'method & $n$ & inst. & eval. cap & median AR & opt.-hit frac. \\', r'\midrule']
for method, label in [('simulated_annealing','sim. annealing'), ('tabu_search','tabu search')]:
    for n in sorted({int(x['n']) for x in cb}):
        rr=[x for x in cb if x['method']==method and int(x['n'])==n]
        ratio=np.median([float(x['median_best_ratio']) for x in rr])
        hit=np.median([float(x['optimum_hit_fraction']) for x in rr])
        budget=int(float(rr[0]['eval_budget_per_run']))
        lines.append(f'{label} & {n} & {len(rr)} & {budget} & {ratio:.3f} & {hit:.3f} {ROW_END}')
lines += [r'\bottomrule', r'\end{tabular}']
write('table_classical_budgeted.tex', lines)

# P2: host-side simulation scaling boundary
sc = read_csv('simulator_scaling.csv')
lines = [r'\begin{tabular}{rrrrr}', r'\toprule', r'$n$ & states & exact-build (s) & $p=1$ eval. (s) & core memory (MiB) \\', r'\midrule']
for x in sc:
    mib = float(x['combined_core_bytes'])/(1024**2)
    lines.append(f"{x['n']} & {int(x['state_count']):,} & {float(x['exact_build_s']):.4f} & {float(x['p1_statevector_eval_s']):.4f} & {mib:.2f} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_simulator_scaling.tex', lines)

# P2: threshold-aware dense uncertainty grid.  Endpoint rows keep the table compact.
rg = read_csv('resource_robustness_grid.csv')
lines = [r'\begin{tabular}{rrrrr}', r'\toprule', r'target & $\varepsilon_{model}$ & median $k^*$ & IQR $k^*$ & median $\eta_{res}$ \\', r'\midrule']
for target in (0.90, 0.95, 1.00):
    for eps in (0.0, 0.003):
        rr = [x for x in rg if abs(float(x['target_ratio'])-target)<1e-12 and abs(float(x['eps_model'])-eps)<1e-15]
        kvals=np.array([int(x['k_star']) for x in rr])
        et=np.array([float(x['eta_res']) for x in rr])
        q1, med, q3=np.quantile(kvals,[.25,.5,.75])
        lines.append(f"{target:.2f} & {eps:.3f} & {med:.1f} & {q1:.1f}--{q3:.1f} & {np.median(et):.3f} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_robustness.tex', lines)

# P2: analytical threshold-event tier at the two attenuation endpoints.
lg = read_csv('large_searchspace_sensitivity.csv')
lines = [r'\begin{tabular}{rrrrr}', r'\toprule', r'$n_{model}$ & target-event states & $\varepsilon_{model}$ & median $k^*$ & IQR $k^*$ \\', r'\midrule']
for n in sorted({int(x['model_n']) for x in lg}):
    for m in sorted({int(x['target_event_count']) for x in lg}):
        for eps in (0.0,0.003):
            rr=[x for x in lg if int(x['model_n'])==n and int(x['target_event_count'])==m and abs(float(x['eps_model'])-eps)<1e-15]
            vals=np.array([int(x['k_star']) for x in rr])
            q1,med,q3=np.quantile(vals,[.25,.5,.75])
            lines.append(f"{n} & {m} & {eps:.3f} & {med:.1f} & {q1:.1f}--{q3:.1f} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_large_tier.tex', lines)

# P3-B: stopping-depth robustness to marked-fraction misspecification.
rh = read_csv('rho_estimation_robustness.csv')
lines = [r'\begin{tabular}{rrrrrr}', r'\toprule', r'$\hat\rho/\rho$ & med. $\Gamma_\rho$ & IQR $\Gamma_\rho$ & med. $|\Delta k|$ & exact-$k$ frac. & worst $\Gamma_\rho$ \\', r'\midrule']
for factor in (0.50,0.75,0.90,1.00,1.10,1.25,1.50):
    rr=[x for x in rh if abs(float(x['rho_estimate_factor'])-factor)<1e-12]
    ret=np.array([float(x['resource_score_retention']) for x in rr])
    dk=np.array([abs(int(x['delta_k'])) for x in rr])
    exact=np.mean(dk==0)
    q1,med,q3=np.quantile(ret,[.25,.5,.75])
    lines.append(f'{factor:.2f} & {med:.3f} & {q1:.3f}--{q3:.3f} & {np.median(dk):.1f} & {exact:.3f} & {ret.min():.3f} {ROW_END}')
lines += [r'\bottomrule', r'\end{tabular}']
write('table_rho_robustness.tex', lines)


# P4: architecture-informed reversible threshold-oracle resource template.
orr = read_csv('oracle_resource_model.csv')
# Resource counts do not depend on operational level in this template, so deduplicate by instance.
by_instance = {}
for x in orr:
    by_instance.setdefault(x['instance_id'], x)
oru = list(by_instance.values())
lines = [r'\begin{tabular}{rrrrrrr}', r'\toprule', r'$n$ & inst. & $m$ range & $b$ range & log. qubits & med. Toffoli$_O$ & med. $D_O$ \\', r'\midrule']
for n in sorted({int(x['n']) for x in oru}):
    rr=[x for x in oru if int(x['n'])==n]
    m=[int(x['n_edges']) for x in rr]; b=[int(x['accumulator_bits']) for x in rr]
    q=[int(x['total_logical_qubits_model']) for x in rr]
    t=[int(x['oracle_toffoli_model']) for x in rr]; d=[int(x['oracle_logical_depth_model']) for x in rr]
    lines.append(f"{n} & {len(rr)} & {min(m)}--{max(m)} & {min(b)}--{max(b)} & {min(q)}--{max(q)} & {np.median(t):.0f} & {np.median(d):.0f} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_oracle_resource.tex', lines)

# P4: coupled cost/depth selector at attenuation endpoints.
cc = read_csv('coupled_oracle_depth_sensitivity.csv')
lines = [r'\begin{tabular}{rrrrrr}', r'\toprule', r'$\lambda$ & feasible & $\varepsilon_D$ & median $k^*$ & zero-round frac. & median $\eta_{arch}$ \\', r'\midrule']
for level in (0.25,0.40,0.55):
    for eps in (0.0,5e-4):
        rr=[x for x in cc if abs(float(x['operational_level'])-level)<1e-12 and abs(float(x['eps_per_logical_depth_model'])-eps)<1e-15]
        kval=np.array([int(x['k_star']) for x in rr]); eta=np.array([float(x['eta_arch']) for x in rr])
        lines.append(f"{level:.2f} & {len(rr)} & {eps:.0e} & {np.median(kval):.1f} & {np.mean(kval==0):.3f} & {np.median(eta):.3f} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_coupled_oracle.tex', lines)

# J: instance-clustered inferential analysis for QAOA depth and optimizer family.
depth_inf = read_csv('qaoa_depth_inference.csv')
opt_inf = read_csv('qaoa_optimizer_inference.csv')
lines = [
    r'\begin{tabular}{lrrrrr}',
    r'\toprule',
    r'\multicolumn{6}{l}{\textit{Depth contrasts}} \\',
    r'contrast & median $\Delta$ & 95\% CI & $p_{\rm Holm}$ & $r_{\rm rb}$ & $n$ \\',
    r'\midrule',
]
for x in depth_inf:
    lines.append(f"{x['comparison']} & {float(x['median_delta']):+.4f} & [{float(x['bootstrap95_lo']):+.4f},{float(x['bootstrap95_hi']):+.4f}] & {float(x['p_holm']):.4f} & {float(x['rank_biserial']):+.3f} & {x['n_instances']} {ROW_END}")
lines += [r'\midrule', r'\multicolumn{6}{l}{\textit{Optimizer contrasts: COBYLA $-$ L-BFGS-B}} \\', r'$p$ & median $\Delta$ & 95\% CI & $p_{\rm Holm}$ & $r_{\rm rb}$ & $n$ \\', r'\midrule']
for x in opt_inf:
    lines.append(f"{x['p']} & {float(x['median_instance_delta']):+.4f} & [{float(x['bootstrap95_lo']):+.4f},{float(x['bootstrap95_hi']):+.4f}] & {float(x['p_holm']):.4f} & {float(x['rank_biserial']):+.3f} & {x['n_instances']} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_qaoa_inference.tex', lines)

# K/L: expanded exact seed/topology coverage alongside the 18-instance primary QAOA suite.
cv = read_csv('coverage_summary.csv')
family_label = {
    'random_fixed_density': 'random weighted',
    'cycle': 'cycle',
    'cubic_circulant': '3-regular circulant',
    'two_community': 'two-community',
}
lines = [r'\begin{tabular}{lrrrrr}', r'\toprule', r'family & $\lambda$ & feas. & med. $\tau/C^*$ & med. $\rho_\tau$ & med. HC AR \\', r'\midrule']
for fam in ('random_fixed_density','cycle','cubic_circulant','two_community'):
    for level in (0.25,0.40,0.55):
        rr=[x for x in cv if x['family']==fam and abs(float(x['operational_level'])-level)<1e-12][0]
        feas=f"{int(float(rr['feasible_count']))}/{int(float(rr['instances']))}"
        tq=float(rr['median_tau_over_Cstar_feasible'])
        rho=float(rr['median_rho_tau_feasible'])
        hc=float(rr['median_hillclimb_ratio'])
        lines.append(f"{family_label[fam]} & {level:.2f} & {feas} & {tq:.3f} & {rho:.4f} & {hc:.3f} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_coverage.tex', lines)


# P0-2: fixed per-trial overhead sensitivity of the architecture-informed selector.
fo = read_csv('fixed_overhead_sensitivity.csv')
lines = [
    r'\begin{tabular}{llrrrr}',
    r'\toprule',
    r'scope & $\varepsilon_D$ & med. $\chi_{BE}$ & IQR $\chi_{BE}$ & nonzero@0.25 & nonzero@0.50 \\',
    r'\midrule',
]
for scope in ('primary','coverage'):
    for eps in (0.0, 5e-4):
        base=[x for x in fo if x['scope']==scope and abs(float(x['eps_per_logical_depth_model'])-eps)<1e-15 and abs(float(x['fixed_overhead_ratio_to_oracle']))<1e-15]
        be=np.asarray([float(x['break_even_fixed_overhead_ratio_to_oracle']) for x in base],dtype=float)
        def nz(ratio):
            rr=[x for x in fo if x['scope']==scope and abs(float(x['eps_per_logical_depth_model'])-eps)<1e-15 and abs(float(x['fixed_overhead_ratio_to_oracle'])-ratio)<1e-12]
            return float(np.mean([int(float(x['k_star']))>0 for x in rr]))
        lines.append(f"{scope} & {eps:.0e} & {np.median(be):.3f} & {np.quantile(be,.25):.3f}--{np.quantile(be,.75):.3f} & {nz(.25):.3f} & {nz(.50):.3f} {ROW_END}")
lines += [r'\bottomrule', r'\end{tabular}']
write('table_fixed_overhead.tex', lines)
