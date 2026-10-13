"""Resultado con el jugador en la cancha: casos de partido con el marcador comprobado a mano."""
import pytest

from scouting.onpitch import (AGAINST, DURING, FOR, LEADING, OUTSIDE, TIED, TRAILING, Goal, describe, final_result,
                              live_state, on_pitch_result)


def goals(*events):
    """goals((30, 'for'), (70, 'against'), (45, 'for', 2))"""
    return [Goal(*event) for event in events]


def test_starter_who_plays_everything_sees_no_change_when_the_game_ends_level():
    # 1-0 a los 30', 1-1 a los 70'. Estuvo todo el partido: entró con 0-0 y terminó con 1-1.
    result = on_pitch_result(goals((30, FOR), (70, AGAINST)), (1, 1))
    assert result.entered is None and result.left is None
    assert result.score_at_entry == (0, 0) and result.score_at_exit == (1, 1)
    assert (result.goals_for_while_on, result.goals_against_while_on) == (1, 1)
    assert result.state_at_entry == TIED and result.state_at_exit == TIED and not result.result_changed
    assert result.final_result == 'Empate'


def test_substitute_who_comes_on_level_and_leaves_the_team_ahead_changes_the_result():
    # Entra a los 60' con 0-0 y el equipo marca a los 65' y a los 80': termina 2-0.
    result = on_pitch_result(goals((65, FOR), (80, FOR)), (2, 0), entered=(60, 0))
    assert result.score_at_entry == (0, 0) and result.score_at_exit == (2, 0)
    assert result.state_at_entry == TIED and result.state_at_exit == LEADING and result.result_changed
    assert result.goals_for_while_on == 2 and result.goals_against_while_on == 0
    assert result.final_result == 'Victoria'


def test_starter_substituted_off_when_the_opponent_scored_while_he_was_on():
    # 0-0 al inicio; el rival marca a los 20' y el equipo empata a los 60', cuando él ya salió (a los 55').
    result = on_pitch_result(goals((20, AGAINST), (60, FOR)), (1, 1), left=(55, 0))
    assert result.score_at_entry == (0, 0) and result.score_at_exit == (0, 1)
    assert result.state_at_entry == TIED and result.state_at_exit == TRAILING and result.result_changed
    assert result.final_score == (1, 1) and result.final_result == 'Empate', 'el final no dice lo que pasó con él'


def test_entry_and_exit_in_the_middle_of_the_game():
    # 1-0 (10'), 1-1 (40'), 2-1 (50'), 2-2 (75'). Jugó entre el 45' y el 70'.
    timeline = goals((10, FOR), (40, AGAINST), (50, FOR), (75, AGAINST))
    result = on_pitch_result(timeline, (2, 2), entered=(45, 0), left=(70, 0))
    assert result.score_at_entry == (1, 1) and result.score_at_exit == (2, 1)
    assert result.state_at_entry == TIED and result.state_at_exit == LEADING and result.result_changed
    assert (result.goals_for_while_on, result.goals_against_while_on) == (1, 0)


def test_a_goal_scored_while_ahead_does_not_change_the_result():
    result = on_pitch_result(goals((10, FOR), (50, FOR)), (2, 0), entered=(30, 0))
    assert result.state_at_entry == LEADING and result.state_at_exit == LEADING and not result.result_changed
    assert result.goals_for_while_on == 1, 'el marcador cambió pero el resultado no'


def test_goal_in_the_same_minute_as_the_substitution_follows_the_rule_and_the_rule_is_visible():
    timeline = goals((60, FOR))
    during = on_pitch_result(timeline, (1, 0), entered=(60, 0), same_minute=DURING)
    outside = on_pitch_result(timeline, (1, 0), entered=(60, 0), same_minute=OUTSIDE)
    assert during.score_at_entry == (0, 0) and during.goals_for_while_on == 1
    assert outside.score_at_entry == (1, 0) and outside.goals_for_while_on == 0
    # Lo mismo en la salida.
    left_during = on_pitch_result(timeline, (1, 0), left=(60, 0), same_minute=DURING)
    left_outside = on_pitch_result(timeline, (1, 0), left=(60, 0), same_minute=OUTSIDE)
    assert left_during.score_at_exit == (1, 0) and left_outside.score_at_exit == (0, 0)
    with pytest.raises(ValueError):
        on_pitch_result(timeline, (1, 0), same_minute='quizás')


def test_stoppage_time_is_ordered_inside_the_half():
    # Salió a los 45+1': el gol de los 45' cuenta, el de 45+2' no.
    timeline = goals((45, FOR), (45, AGAINST, 2))
    result = on_pitch_result(timeline, (1, 1), left=(45, 1))
    assert result.score_at_exit == (1, 0)
    assert on_pitch_result(timeline, (1, 1), left=(45, 2)).score_at_exit == (1, 1)
    assert on_pitch_result(timeline, (1, 1), entered=(45, 1)).score_at_entry == (1, 0)


def test_incomplete_or_contradictory_timeline_is_unknown_not_guessed():
    assert on_pitch_result(goals((10, FOR)), (2, 0)) is None, 'falta un gol: no se sabe cuándo llegó el segundo'
    assert on_pitch_result(goals((10, FOR), (20, FOR)), (1, 0)) is None, 'sobra un gol'
    assert on_pitch_result(goals((10, FOR)), None) is None, 'sin marcador final no se puede comprobar'
    assert on_pitch_result([], (0, 0)).result_changed is False, 'un 0-0 sin goles sí es una cronología completa'


def test_invalid_stints_and_goals_are_rejected():
    with pytest.raises(ValueError):
        on_pitch_result([], (0, 0), entered=(70, 0), left=(60, 0))
    with pytest.raises(ValueError):
        on_pitch_result([], (0, 0), entered=(-1, 0))
    with pytest.raises(ValueError):
        Goal(10, 'neutral')
    with pytest.raises(ValueError):
        Goal(-5, FOR)


def test_states_and_final_result_labels():
    assert [live_state(s) for s in ((1, 0), (0, 0), (0, 2))] == [LEADING, TIED, TRAILING]
    assert [final_result(s) for s in ((1, 0), (2, 2), (0, 3))] == ['Victoria', 'Empate', 'Derrota']


def test_sentence_for_the_screens():
    result = on_pitch_result(goals((65, FOR), (80, FOR)), (2, 0), entered=(60, 0))
    assert describe(result) == ("Entró a los 60' con 0-0 (empatando); terminó el partido con 2-0 (ganando): "
                                'el resultado cambió mientras estuvo en la cancha')
    starter = on_pitch_result(goals((10, AGAINST), (45, FOR, 2)), (1, 1), left=(45, 1))
    assert describe(starter) == ("Fue titular con 0-0 (empatando); salió a los 45+1' con 0-1 (perdiendo): "
                                 'el resultado cambió mientras estuvo en la cancha')
    steady = on_pitch_result([], (0, 0), entered=(30, 0), left=(60, 0))
    assert describe(steady).endswith('el resultado no cambió')
    assert describe(None) == 'Sin dato: la cronología del partido no está completa'
