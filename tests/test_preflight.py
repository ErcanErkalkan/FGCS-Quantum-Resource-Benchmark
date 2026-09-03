import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preflight import (
    Check,
    check_claim_fences,
    check_compiler_evidence,
    check_manifest_hashes,
    check_row_counts,
    check_tex_balance,
    csv_row_count,
    find_affirmative_risky_claims,
    parse_lock,
    resolve_artifact,
    sha256,
)


def test_uw_sha256_is_deterministic(tmp_path):
    p = tmp_path / 'x.txt'
    p.write_text('abc', encoding='utf-8')
    assert sha256(p) == sha256(p)
    assert len(sha256(p)) == 64


def test_uw_parse_lock_requires_exact_pins(tmp_path):
    p = tmp_path / 'requirements.lock'
    p.write_text('# lock\nnumpy==2.3.5\nscipy==1.17.0\n', encoding='utf-8')
    assert parse_lock(p) == {'numpy': '2.3.5', 'scipy': '1.17.0'}
    p.write_text('numpy>=2\n', encoding='utf-8')
    try:
        parse_lock(p)
        assert False, 'expected ValueError'
    except ValueError:
        pass


def test_uw_resolve_artifact_rejects_duplicate(tmp_path):
    (tmp_path / 'data').mkdir(); (tmp_path / 'results').mkdir()
    (tmp_path / 'data' / 'a.csv').write_text('x\n1\n', encoding='utf-8')
    p, candidates = resolve_artifact(tmp_path, 'a.csv')
    assert p == tmp_path / 'data' / 'a.csv' and len(candidates) == 1
    (tmp_path / 'results' / 'a.csv').write_text('x\n1\n', encoding='utf-8')
    p, candidates = resolve_artifact(tmp_path, 'a.csv')
    assert p is None and len(candidates) == 2


def test_uw_row_count_uses_data_rows_not_header(tmp_path):
    p = tmp_path / 'x.csv'
    p.write_text('a,b\n1,2\n3,4\n', encoding='utf-8')
    assert csv_row_count(p) == 2


def _mini_project(tmp_path):
    for d in ('data','results','src','tests','manuscript','reproducibility'):
        (tmp_path / d).mkdir(exist_ok=True)
    (tmp_path / 'data' / 'maxcut_suite_graphs.csv').write_text('x\n1\n', encoding='utf-8')
    (tmp_path / 'results' / 'maxcut_ground_truth.csv').write_text('x\n1\n', encoding='utf-8')
    (tmp_path / 'src' / 'benchmark.py').write_text('family = \"random_fixed_density\"\n', encoding='utf-8')
    return tmp_path


def test_uw_manifest_hash_check_detects_mismatch(tmp_path):
    root = _mini_project(tmp_path)
    p = root / 'results' / 'maxcut_ground_truth.csv'
    manifest = {'sha256': {'maxcut_ground_truth.csv': sha256(p)}, 'source_sha256': {}}
    checks = check_manifest_hashes(root, manifest)
    assert all(c.status == 'PASS' for c in checks)
    p.write_text('x\n2\n', encoding='utf-8')
    checks = check_manifest_hashes(root, manifest)
    assert any(c.status == 'FAIL' for c in checks)


def test_uw_manifest_row_count_detects_mismatch(tmp_path):
    root = _mini_project(tmp_path)
    manifest = {'suite': {'exact_instances': 1}, 'qaoa': {}}
    assert all(c.status == 'PASS' for c in check_row_counts(root, manifest))
    manifest['suite']['exact_instances'] = 2
    assert any(c.status == 'FAIL' for c in check_row_counts(root, manifest))


def test_uw_tex_balance_detects_unbalanced_environment():
    good = r'\begin{document}x\end{document}'
    bad = r'\begin{document}x'
    assert all(c.status == 'PASS' for c in check_tex_balance(good))
    assert any(c.status == 'FAIL' for c in check_tex_balance(bad))


def test_uw_claim_fence_flags_affirmative_advantage_language():
    bad = 'Our method demonstrates quantum advantage over all baselines.'
    good = 'The study does not demonstrate quantum advantage and makes no hardware speedup claim.'
    assert find_affirmative_risky_claims(bad)
    assert not find_affirmative_risky_claims(good)


def test_uw_claim_fence_requires_locked_compiler_mode_and_no_hardware_claim(tmp_path):
    root = _mini_project(tmp_path)
    (root / 'README.md').write_text('neutral benchmark', encoding='utf-8')
    (root / 'manuscript' / 'main.tex').write_text(
        '18 primary; 63 coverage; 18-instance QAOA; No physical-backend; '
        'fixed-edge-count/fixed-density random simple-graph design; '
        'CRediT authorship contribution statement; GPT-5.6 Sol; '
        'not consistently recorded; Qiskit 2.4.2',
        encoding='utf-8',
    )
    (root / 'manuscript' / 'references.bib').write_text(
        '@article{boyer1998,}\n@article{li2023qasmbench,}\n'
        '@inproceedings{tomesh2022supermarq,}\n@article{lubinski2023application,}\n',
        encoding='utf-8',
    )
    ok = {'hardware_claims': False, 'compiler_claims': 'locked_synthetic_topology'}
    assert all(c.status == 'PASS' for c in check_claim_fences(root, ok))
    bad = {'hardware_claims': True, 'compiler_claims': 'locked_synthetic_topology'}
    assert any(c.status == 'FAIL' for c in check_claim_fences(root, bad))


def test_p1_preflight_rejects_legacy_random_family_label(tmp_path):
    root = _mini_project(tmp_path)
    (root / 'README.md').write_text('neutral benchmark', encoding='utf-8')
    (root / 'manuscript' / 'main.tex').write_text(
        '18 primary; 63 coverage; 18-instance QAOA; No physical-backend; '
        'fixed-edge-count/fixed-density random simple-graph design; '
        'CRediT authorship contribution statement; GPT-5.6 Sol; '
        'not consistently recorded; Qiskit 2.4.2',
        encoding='utf-8',
    )
    (root / 'manuscript' / 'references.bib').write_text(
        '@article{boyer1998,}\n@article{li2023qasmbench,}\n'
        '@inproceedings{tomesh2022supermarq,}\n@article{lubinski2023application,}\n',
        encoding='utf-8',
    )
    (root / 'src' / 'benchmark.py').write_text('family = "erdos_renyi"\n', encoding='utf-8')
    checks = check_claim_fences(root, {'hardware_claims': False, 'compiler_claims': 'locked_synthetic_topology'})
    assert any(c.name == 'random-family-label' and c.status == 'FAIL' for c in checks)


def test_compiler_evidence_accepts_locked_summary(tmp_path):
    root = _mini_project(tmp_path)
    summary = {
        'qiskit_version': '2.4.2',
        'seed_transpiler': 20260901,
        'optimization_level': 1,
        'row_count': 66,
        'qaoa_routed_rows': 54,
        'oracle_basis_rows': 9,
        'oracle_sparse_routed_rows': 3,
        'basis_gates': ['rz','sx','x','cx'],
        'semantic_oracle_check': {'passed': True, 'tested_basis_states': 8, 'failures': []},
        'qaoa_median_compiled_depth_by_p': {'1':78.0,'2':180.5,'3':260.5},
    }
    (root/'results'/'compiler_validation_summary.json').write_text(json.dumps(summary), encoding='utf-8')
    gap_csv = 'compiler_to_analytic_depth_ratio,compiler_to_analytic_qubit_ratio\n' + ''.join('2.0,1.5\n' for _ in range(9))
    (root/'results'/'compiler_vs_analytic_oracle.csv').write_text(gap_csv, encoding='utf-8')
    checks = check_compiler_evidence(root, {'compiler_claims':'locked_synthetic_topology'})
    assert checks and all(c.status == 'PASS' for c in checks)
    summary['semantic_oracle_check']['passed'] = False
    (root/'results'/'compiler_validation_summary.json').write_text(json.dumps(summary), encoding='utf-8')
    assert any(c.status == 'FAIL' for c in check_compiler_evidence(root, {}))
