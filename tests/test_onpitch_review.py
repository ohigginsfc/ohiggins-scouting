"""Boundary and invalid input cases for the reusable on-pitch calculation."""
import math

import pytest

from scouting.onpitch import FOR, OUTSIDE, Goal, on_pitch_result


def test_same_entry_exit_minute_outside_never_produces_negative_goals():
    result = on_pitch_result([Goal(60, FOR)], (1, 0), entered=(60, 0), left=(60, 0), same_minute=OUTSIDE)
    assert result.score_at_entry == result.score_at_exit == (1, 0)
    assert result.goals_for_while_on == result.goals_against_while_on == 0


@pytest.mark.parametrize('minute,added', [(math.nan, 0), (math.inf, 0), (30.5, 0), (True, 0), (30, math.nan), (30, 0.5)])
def test_goal_requires_known_integer_clock(minute, added):
    with pytest.raises(ValueError):
        Goal(minute, FOR, added)


@pytest.mark.parametrize('clock', [(math.nan, 0), (math.inf, 0), (30, 0.5), (True, 0)])
def test_stint_requires_known_integer_clock(clock):
    with pytest.raises(ValueError):
        on_pitch_result([], (0, 0), entered=clock)


@pytest.mark.parametrize('score', [(math.nan, 0), (False, 0), (0.0, 0), (-1, 0), (0, 0, 0)])
def test_final_score_requires_two_nonnegative_integer_values(score):
    with pytest.raises(ValueError):
        on_pitch_result([], score)
