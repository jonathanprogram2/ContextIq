import importlib.util
from pathlib import Path


def test_retrieval_metrics():
    script = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_retrieval.py"
    spec = importlib.util.spec_from_file_location("evaluate_retrieval", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    metrics = module.score_case([7, 9, 2, 3], {9, 3}, 4)
    assert metrics["recall_at_k"] == 1
    assert metrics["precision_at_k"] == 0.5
    assert metrics["reciprocal_rank"] == 0.5
