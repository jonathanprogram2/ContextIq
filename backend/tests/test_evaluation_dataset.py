"""CPU-only benchmark annotation and scoring checks."""

import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "scripts" / "prepare_evaluation.py"
spec = importlib.util.spec_from_file_location("prepare_evaluation", MODULE)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
match_ids = module.match_ids
normalize = module.normalize
prepare = module.prepare


def test_whitespace_normalization():
    assert normalize("  Vacation\n requests   take 14 days  ") == "vacation requests take 14 days"


def test_verified_evidence_mapping():
    rows = [{"id": 42, "filename": "sample.pdf", "page_number": 3, "text_content": "Vacation requests take 14 days."}]
    annotations = [{"question": "When?", "filename": "sample.pdf", "page_number": 3, "evidence_anchor": "requests take 14 days"}]
    assert match_ids(rows, "sample.pdf", 3, "requests take 14 days") == [42]
    assert prepare(annotations, rows) == [{"question": "When?", "relevant_chunk_ids": [42]}]


def test_missing_evidence_fails_closed():
    try:
        prepare([{"question": "When?", "filename": "missing.pdf", "page_number": 1, "evidence_anchor": "not here"}], [])
    except ValueError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("Missing source must cause a failure")
