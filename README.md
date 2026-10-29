# RQMC

## Software versions

- Windows 11 x64
- Python 3.12.13
- QMCPy 2.4; QMCToolsCL 1.2.4
- NumPy 2.5.4; SciPy 1.18.1; pandas 2.3.3; matplotlib 3.11.2; psutil 7.2.2

## Python packages

- Exact environment: requirements-lock.txt
- High-precision validation: bundled mpmath 1.3.0 wheel in validation_dependencies/
- Tests: pytest 9.1.1

## Reproduction

From the repository root, set up the environment and run:

    py -3.12 -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements-lock.txt
    .venv\Scripts\python.exe scripts/run_rescue.py --phase confirmation --workers 16 --methods controls A01 A02 PLUGIN_STAGE
    .venv\Scripts\python.exe scripts/analyze_rescue.py --phase confirmation
    .venv\Scripts\python.exe scripts/start_reproduction_clock.py
    .venv\Scripts\python.exe scripts/run_s1_replay.py --workers 16
    .venv\Scripts\python.exe scripts/run_supplement_v2.py --mode profile --workers 16
    .venv\Scripts\python.exe scripts/run_supplement_v2.py --mode confirmation --workers 16 --freeze
    .venv\Scripts\python.exe scripts/run_supplement_v2.py --mode sensitivity --workers 16
    .venv\Scripts\python.exe scripts/analyze_supplement_v2.py --kind s1
    .venv\Scripts\python.exe scripts/analyze_supplement_v2.py --kind s2
    .venv\Scripts\python.exe scripts/analyze_supplement_v2.py --kind s3
