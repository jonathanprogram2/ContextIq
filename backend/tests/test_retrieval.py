from app.retrieval import reciprocal_rank_fusion


def test_fusion_rewards_items_in_both_rankings():
    scores = reciprocal_rank_fusion([[1, 2, 3], [2, 3, 4]])
    assert scores[2] > scores[1]
    assert scores[2] > scores[4]


def test_fusion_deduplicates_within_ranking():
    assert reciprocal_rank_fusion([[9, 9]])[9] == 1 / 61
