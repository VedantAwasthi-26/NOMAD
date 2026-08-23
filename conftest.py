# Empty on purpose. Its only job is to exist at the repo root so pytest's
# rootdir-detection puts this directory on sys.path before collecting any
# tests -- without it, `pytest ai_engine/tests/test_scoring.py` inserts
# ai_engine/tests/ (not the repo root) onto sys.path, since neither `app/`
# nor `ai_engine/tests/` has an __init__.py (app is an implicit namespace
# package). That's what caused `ModuleNotFoundError: No module named 'app'`
# when the test file tried `from app.engine.scoring import ...`.
#
# Run pytest from the repo root (NOMAD\NOMAD, the folder this file lives
# in) and it'll be picked up automatically -- no extra flags needed.
