"""Small synthetic SQL fixtures only; production is never a test database."""
import json
import pytest
from psycopg.types.json import Jsonb
from tests.test_atomic_sofascore_import import db
from scouting.repositories import metrics_repository as metrics


@pytest.mark.parametrize('payload', [
    None, [], {}, {'sofascore_position': 'D', 'original_position': 'M'},
    {'sofascore_position': ' ', 'original_position': 'M'},
    {'raw_row': {'position': '\tF\n', 'unneeded': 'x' * 5000}},
    {'sofascore_position': False, 'original_position': 'M'},
    {'sofascore_position': {'invalid': None}, 'original_position': 'F'},
    {'sofascore_position': [], 'raw_row': {'position': 'D'}},
    {'sofascore_position': 'M', 'objective_team': {'nested': None}, 'team_name': 'Fallback'},
    {'sofascore_position': 'G', 'objective_team': 0, 'team': 'Synthetic Team'},
])
def test_sql_projection_keeps_position_precedence_and_team_labels(db, payload):
    with db() as conn:
        compact = conn.execute('SELECT ' + metrics._objective_payload_sql(with_team=True)
            + ' FROM (SELECT %s::jsonb AS raw_payload) om', (Jsonb(payload),)).fetchone()[0]
    original, projected = {'raw_payload': payload}, {'raw_payload': compact}
    assert metrics._objective_position_from_row(projected, source_name='Sofascore') == metrics._objective_position_from_row(original, source_name='Sofascore')
    assert metrics._team_from_objective_row(projected) == metrics._team_from_objective_row(original)


def seed(conn):
    for player, position in [(1, 'D'), (2, 'D'), (3, 'D'), (4, 'M'), (5, 'G'), (6, None)]:
        conn.execute('INSERT INTO players(id,full_name,normalized_name,position) VALUES (%s,%s,%s,%s)',
                     (player, f'Synthetic {player}', f'synthetic-{player}', 'Portero'))
        for season in ('2025', '2026'):
            for index, name in enumerate(('goals', 'yellowCards', 'minutesPlayed')):
                payload = {'sofascore_position': position, 'objective_team': f'Synthetic team {player}',
                           'raw_row': {'position': position, 'unused': 'x' * 5000}, 'metric_debug': name}
                conn.execute('INSERT INTO objective_metrics(player_id,source_name,source_type,season,competition,metric_name,metric_value,metric_unit,raw_payload) '
                             'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                             (player, 'Sofascore', 'sofascore', season, 'Synthetic League', name,
                              player * 10 + index + int(season[-1]), 'count', Jsonb(payload)))


def legacy_projection(*, with_team=False):
    return 'om.raw_payload'


def test_counts_averages_percentiles_and_peer_labels_match_full_payload(db, monkeypatch):
    with db() as conn:
        seed(conn)
        args = (conn, 1, '2026', 'Synthetic League', 'Defensa')
        names = ['goals', 'yellowCards', 'minutesPlayed']
        def calculate():
            return (
                metrics.count_objective_comparison_cohort(*args, 'same_competition'),
                metrics.get_player_vs_position_average(*args, names, 'same_competition'),
                metrics.get_player_vs_position_percentiles(*args, names),
                metrics.get_player_vs_position_percentiles(*args, names, cohort_seasons=['2025', '2026']),
                metrics.get_position_group_percentile_averages(*args, names),
            )
        optimized = calculate()
        monkeypatch.setattr(metrics, '_objective_payload_sql', legacy_projection)
        original = calculate()
        assert optimized == original
        assert optimized[0] == 2
        assert optimized[2][0] and optimized[2][0][0]['players_count'] == 2


def test_count_projection_collapses_metric_copies_and_reduces_transfer(db):
    with db() as conn:
        seed(conn)
        sizes = []
        for projection in ('om.raw_payload', metrics._objective_payload_sql()):
            query = f'SELECT count(*), sum(octet_length(row_to_json(t)::text)) FROM (SELECT DISTINCT player_id, {projection} AS raw_payload FROM objective_metrics om) t'
            sizes.append(conn.execute(query).fetchone())
        assert sizes[1][0] == 6 and sizes[0][0] == 18
        assert sizes[1][1] < sizes[0][1] / 20
