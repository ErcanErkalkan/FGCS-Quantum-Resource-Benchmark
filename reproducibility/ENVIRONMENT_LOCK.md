# U/W environment lock

Date: 2026-08-30
Target: canonical FGCS Max-Cut benchmark only.

The validated execution environment is pinned at Python 3.13.5. Direct project dependencies are pinned in `requirements.txt`; the complete benchmark/render/test dependency closure used in this environment is recorded in `requirements.lock`. The run-manifest environment checkpoint is Python 3.13.5, NumPy 2.3.5, and SciPy 1.17.0; the U/W lock additionally records Matplotlib 3.10.8 and pytest 9.0.2 because figure rendering and regression validation depend on them.

Recreate with a fresh virtual environment and install the lock file rather than unconstrained latest packages:

```bash
python3.13 -m venv .venv-fgcs
source .venv-fgcs/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.lock
python src/preflight.py --source-only
pytest -q
```

Before submission, run the full artifact check after all benchmark outputs are present:

```bash
python src/preflight.py --json-out results/preflight_report.json
```

The preflight fails on Python/package drift, stale SHA-256 values, duplicate canonical files, expected-row-count mismatches, unbalanced LaTeX environments, manifest claim-boundary violations, or missing canonical project files. It does not certify scientific validity or hardware performance; it certifies reproducibility/package consistency against the declared artifact contract.
