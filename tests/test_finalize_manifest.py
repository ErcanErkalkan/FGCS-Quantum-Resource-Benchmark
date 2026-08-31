import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import finalize_manifest as fm


def test_finalizer_hashes_declared_sources_and_dependencies(tmp_path, monkeypatch):
    (tmp_path / 'results').mkdir()
    (tmp_path / 'src').mkdir()
    (tmp_path / 'manuscript').mkdir()
    (tmp_path / 'results' / 'run_manifest.json').write_text('{"study":"x"}\n', encoding='utf-8')
    (tmp_path / 'src' / 'a.py').write_text('x=1\n', encoding='utf-8')
    (tmp_path / 'manuscript' / 'a.tex').write_text('x\n', encoding='utf-8')
    monkeypatch.setattr(fm, 'SOURCE_PATHS', {'a.py': 'src/a.py'})
    monkeypatch.setattr(fm, 'MANUSCRIPT_DEPENDENCIES', ['manuscript/a.tex'])
    monkeypatch.setattr(fm, 'EXTRA_SCIENCE_ARTIFACTS', [])
    out = fm.finalize(tmp_path)
    assert out['source_sha256']['a.py'] == fm.sha256(tmp_path / 'src' / 'a.py')
    assert out['manuscript_dependency_sha256']['manuscript/a.tex'] == fm.sha256(tmp_path / 'manuscript' / 'a.tex')
    saved = json.loads((tmp_path / 'results' / 'run_manifest.json').read_text())
    assert saved['finalization']['manuscript_dependency_count'] == 1


def test_finalizer_fails_closed_on_missing_dependency(tmp_path, monkeypatch):
    (tmp_path / 'results').mkdir()
    (tmp_path / 'results' / 'run_manifest.json').write_text('{"study":"x"}\n', encoding='utf-8')
    monkeypatch.setattr(fm, 'SOURCE_PATHS', {})
    monkeypatch.setattr(fm, 'MANUSCRIPT_DEPENDENCIES', ['figures/missing.pdf'])
    monkeypatch.setattr(fm, 'EXTRA_SCIENCE_ARTIFACTS', [])
    try:
        fm.finalize(tmp_path)
        assert False, 'expected FileNotFoundError'
    except FileNotFoundError:
        pass
