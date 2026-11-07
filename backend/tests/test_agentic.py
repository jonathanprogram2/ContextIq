from app.agentic import choose_path


def test_graph_answers_with_sufficient_evidence():
    assert choose_path({"sufficient": True, "attempts": 1}) == "answer"


def test_graph_rewrites_only_once():
    assert choose_path({"sufficient": False, "attempts": 1}) == "rewrite"
    assert choose_path({"sufficient": False, "attempts": 2}) == "abstain"
