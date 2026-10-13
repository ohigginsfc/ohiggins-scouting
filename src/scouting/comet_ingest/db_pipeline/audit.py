"""Offline snapshot checks. Only aggregate counts leave this module.

Missing parents here mean absent from the supplied snapshot, not necessarily
absent from an existing database. This is not a remote-schema certification.
"""
from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class Relation:
    child: str
    columns: tuple[str, ...]
    parent: str
    parent_columns: tuple[str, ...]


RELATIONS = [
    Relation('competiciones', ('parentCompetitionId',), 'competiciones', ('id',)),
    Relation('competidores', ('id',), 'competiciones', ('id',)),
    Relation('competidores', ('clubId',), 'equipos', ('clubId',)),
    Relation('partidos', ('id',), 'competiciones', ('id',)),
    Relation('partidos', ('id', 'homeTeam'), 'competidores', ('id', 'clubId')),
    Relation('partidos', ('id', 'awayTeam'), 'competidores', ('id', 'clubId')),
    Relation('posiciones', ('id',), 'competiciones', ('id',)),
    Relation('posiciones', ('id', 'clubId'), 'competidores', ('id', 'clubId')),
    Relation('eventos_partido', ('personId',), 'jugadores', ('personId',)),
    Relation('eventos_partido', ('secondPersonId',), 'jugadores', ('personId',)),
    Relation('eventos_partido', ('id', 'teamId'), 'competidores', ('id', 'clubId')),
    Relation('partidos_cambios_estado', ('matchId',), 'partidos', ('matchId',)),
    Relation('partidos_cambios_estado_equipo', ('matchId',), 'partidos', ('matchId',)),
]
for table in ('partidos_fases', 'eventos_partido', 'actuaciones_jugadores', 'actuaciones_arqueros'):
    RELATIONS.extend([
        Relation(table, ('id',), 'competiciones', ('id',)),
        Relation(table, ('matchId',), 'partidos', ('matchId',)),
    ])
for table in ('actuaciones_jugadores', 'actuaciones_arqueros'):
    RELATIONS.extend([
        Relation(table, ('personId',), 'jugadores', ('personId',)),
        Relation(table, ('id', 'clubId'), 'competidores', ('id', 'clubId')),
    ])


def audit_relations(frames, relations=RELATIONS):
    checks = []
    for relation in relations:
        result = {'table': relation.child, 'columns': list(relation.columns),
                  'parent': relation.parent, 'parent_columns': list(relation.parent_columns)}
        child, parent = frames.get(relation.child), frames.get(relation.parent)
        if child is None or parent is None or not set(relation.columns).issubset(child.columns) or not set(relation.parent_columns).issubset(parent.columns):
            result.update(status='unavailable', missing_rows=None, missing_identities=None)
        else:
            # PostgreSQL MATCH SIMPLE: nullable foreign keys with any null are exempt.
            child_keys = child[list(relation.columns)].dropna()
            parent_keys = parent[list(relation.parent_columns)].dropna()
            known = set(parent_keys.itertuples(index=False, name=None))
            missing = [key for key in child_keys.itertuples(index=False, name=None) if key not in known]
            result.update(status='missing_parents' if missing else 'ok', checked_rows=len(child_keys),
                          null_reference_rows=len(child) - len(child_keys),
                          missing_rows=len(missing), missing_identities=len(set(missing)))
        checks.append(result)
    return checks


def audit_standings(raw, payload_columns):
    keys = ['id', 'season', 'clubId']
    if raw is None or not set(keys + ['type']).issubset(raw.columns):
        return {'status': 'unavailable', 'multiple_version_groups': None, 'conflicting_groups': None}
    multiple, conflicts = 0, 0
    metrics = [column for column in payload_columns if column in raw and column not in keys]
    for _, group in raw.groupby(keys, dropna=False):
        if len(group) < 2:
            continue
        if group['type'].nunique(dropna=False) > 1:
            multiple += 1
        if metrics and group[metrics].nunique(dropna=False).gt(1).any():
            conflicts += 1
    return {'status': 'review_required' if multiple or conflicts else 'ok',
            'multiple_version_groups': multiple, 'conflicting_groups': conflicts,
            'policy': 'No official/unofficial selection is inferred; source remains unchanged'}


def audit_snapshot(frames, raw_standings, standings_columns):
    relations = audit_relations(frames)
    standings = audit_standings(raw_standings, standings_columns)
    lineage = {name: frame.attrs.get('cleaning', {}) for name, frame in frames.items()}
    unavailable = any(item['status'] == 'unavailable' for item in relations) or standings['status'] == 'unavailable'
    issues = any(item['status'] == 'missing_parents' for item in relations) or standings['status'] == 'review_required'
    rejected = sum(item.get('invalid_required_rows', 0) for item in lineage.values())
    empty_core = [name for name in ('competiciones', 'equipos', 'competidores', 'partidos', 'jugadores')
                  if name in frames and frames[name].empty]
    status = 'incomplete' if unavailable else ('review_required' if issues or rejected or empty_core else 'ok')
    return {'status': status, 'relations': relations, 'standings': standings,
            'cleaning': lineage, 'invalid_required_rows': rejected, 'empty_core_tables': empty_core,
            'scope': 'Snapshot only; missing parents may exist in the database. No writes or remote validation.'}
