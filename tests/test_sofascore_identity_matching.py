from scouting.services import matching_service


def test_source_qualified_identity_can_be_reviewed_as_an_exact_name_candidate(monkeypatch):
    repo = matching_service.matching_repository
    monkeypatch.setattr(repo, 'get_player_row', lambda *a: dict(id=1, full_name='Synthetic Player', normalized_name='synthetic player'))
    monkeypatch.setattr(repo, 'get_sofascore_candidate_pool', lambda *a, **k: [
        dict(candidate_player_id=2, full_name='Synthetic Player', normalized_name='synthetic player | sofascore:200')])
    monkeypatch.setattr(repo, 'get_candidate_metric_extras', lambda *a: dict(competitions=['Primera B Chile'], minutes_played=90, avg_rating=None))
    candidates = matching_service.find_sofascore_candidates_for_player(None, 1)
    assert candidates[0]['candidate_player_id'] == 2
    assert candidates[0]['match_reason'] == 'normalized_name'
    assert candidates[0]['normalized_name'].endswith(' | sofascore:200')
