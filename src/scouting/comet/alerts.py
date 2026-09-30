"""Alertas automáticas de seguimiento deportivo y su color de presentación."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Optional

import pandas as pd

from .facts import Dataset
from .metrics import principal_categories, seasons_without_promotion

# nombre -> (color de texto y borde, color de fondo). Siempre se acompaña de texto: el color no es el único aviso.
ALERT_COLORS: dict[str, tuple[str, str]] = {
    'Rojo': ('#B42318', '#FEE4E2'),
    'Naranja': ('#B54708', '#FEF0C7'),
    'Amarillo': ('#854D0E', '#FEF9C3'),
    'Verde': ('#1B6B34', '#DCFCE7'),
    'Azul': ('#1B537B', '#E0F0FC'),
    'Gris': ('#475569', '#EEF2F6'),
}


@dataclass(frozen=True)
class AlertDef:
    key: str
    default_color: str
    rule_key: Optional[str] = None


ALERT_DEFS: tuple[AlertDef, ...] = (
    AlertDef('yellow_cards', 'Naranja', 'yellow_threshold'),
    AlertDef('low_participation', 'Rojo', 'participation_threshold'),
    AlertDef('playing_up', 'Azul'),
    AlertDef('no_promotion', 'Amarillo', 'seasons_without_promotion'),
)
ALERTS_BY_KEY = {a.key: a for a in ALERT_DEFS}


def alert_label(key: str, rules) -> str:
    """Nombre legible de la alerta, con el umbral vigente."""
    if key == 'yellow_cards':
        return f'{rules.value("yellow_threshold")} o más tarjetas amarillas'
    if key == 'low_participation':
        return f'Menos del {rules.value("participation_threshold")} % de los minutos posibles'
    if key == 'playing_up':
        return 'Juega en una categoría superior'
    if key == 'no_promotion':
        return f'Más de {rules.value("seasons_without_promotion")} temporadas sin promoción de categoría'
    raise KeyError(key)


def default_config() -> dict[str, dict[str, Any]]:
    return {a.key: {'enabled': True, 'color': a.default_color} for a in ALERT_DEFS}


def resolve_config(stored: Optional[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Combina lo guardado con los valores por defecto; descarta colores o claves inválidos."""
    config = default_config()
    for key, entry in (stored or {}).items():
        if key in config and isinstance(entry, Mapping):
            if isinstance(entry.get('enabled'), bool):
                config[key]['enabled'] = entry['enabled']
            if entry.get('color') in ALERT_COLORS:
                config[key]['color'] = entry['color']
    return config


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=['alert_key', 'personid', 'displayname', 'category', 'value', 'detail'])


def _yellow_cards(ds: Dataset, season_year: int) -> pd.DataFrame:
    f = ds.facts[ds.facts['season_year'] == season_year]
    threshold = ds.rules.value('yellow_threshold')
    per_competition = ds.rules.value('card_cycle') == 'competicion'
    keys = ['personid', 'competition_id'] if per_competition else ['personid']
    grouped = f.groupby(keys, as_index=False).agg(
        displayname=('displayname', 'first'), category=('category', 'last'),
        competition=('competition', 'first'), value=('yellow_cards', lambda s: s.sum(min_count=1)),
        second=('second_yellows', lambda s: s.sum(min_count=1)))
    hit = grouped[grouped['value'] >= threshold].copy()
    if hit.empty:
        return _empty()
    scope = hit['competition'] if per_competition else f'temporada {season_year}'
    hit['detail'] = hit['value'].astype(int).astype(str) + ' amarillas en ' + scope
    seconds = hit['second'].fillna(0).astype(int)
    hit.loc[seconds > 0, 'detail'] += ' (+' + seconds.astype(str) + ' segunda amarilla, no sumada)'
    return hit[['personid', 'displayname', 'category', 'value', 'detail']].assign(alert_key='yellow_cards')


def _pct_text(value: float) -> str:
    """Porcentaje con 2 decimales, truncado: nunca se muestra «20,00 %» bajo un umbral de 20 %."""
    return f'{math.floor(value * 100) / 100:.2f} %'


def _low_participation(cat_summary: pd.DataFrame, season_year: int, threshold: int) -> pd.DataFrame:
    season = cat_summary[cat_summary['season_year'] == season_year]
    principal = principal_categories(season) if len(season) else season
    hit = principal[principal['possible_minutes'].fillna(0) > 0]
    # Comparación exacta (minutos × 100 frente a umbral × posibles): nada se redondea antes de comparar.
    hit = hit[hit['counted_minutes'].notna() & (hit['counted_minutes'] * 100 < threshold * hit['possible_minutes'])].copy()
    if hit.empty:
        return _empty()
    hit['value'] = hit['counted_minutes'] / hit['possible_minutes'] * 100
    hit['detail'] = (hit['value'].map(_pct_text) + ' · '
                     + hit['counted_minutes'].astype(int).astype(str) + ' de '
                     + hit['possible_minutes'].astype(int).astype(str) + ' min posibles en ' + hit['category'])
    return hit[['personid', 'displayname', 'category', 'value', 'detail']].assign(alert_key='low_participation')


def _playing_up(ds: Dataset, season_year: int) -> pd.DataFrame:
    f = ds.facts[(ds.facts['season_year'] == season_year) & (ds.facts['steps_ahead'] > 0) & ds.facts['participated']]
    if f.empty:
        return _empty()
    per_category = f.groupby(['personid', 'category'], as_index=False).agg(
        displayname=('displayname', 'first'), age=('age', 'first'), age_category=('age_category', 'first'),
        steps=('steps_ahead', 'max'), minutes=('minutes', lambda s: s.sum(min_count=1)))
    total = per_category.groupby('personid')['minutes'].sum(min_count=1)
    top = per_category.sort_values(['minutes', 'steps'], ascending=False).groupby('personid', as_index=False).head(1)
    top = top.assign(value=top['personid'].map(total))
    top['detail'] = ('Le corresponde ' + top['age_category'] + ' por edad (' + top['age'].astype(int).astype(str)
                     + ' años) · juega en ' + top['category'] + ' (+' + top['steps'].astype(int).astype(str)
                     + ') · ' + top['value'].fillna(0).astype(int).astype(str) + ' min')
    return top[['personid', 'displayname', 'category', 'value', 'detail']].assign(alert_key='playing_up')


def _no_promotion(principal: pd.DataFrame, season_year: int, threshold: int) -> pd.DataFrame:
    streak = seasons_without_promotion(principal, season_year)
    if streak.empty:
        return _empty()
    hit = streak[(streak['seasons_in_category'] > threshold) & streak['category_rank'].notna()
                 & (streak['category_rank'] < 1000)].copy()  # Primer Equipo no tiene categoría superior
    if hit.empty:
        return _empty()
    hit['detail'] = (hit['seasons_in_category'].astype(str) + ' temporadas seguidas en ' + hit['category']
                     + ' (desde ' + hit['since_season'].astype(str) + '; historial disponible desde '
                     + hit['history_start'].astype(str) + ')')
    return hit.rename(columns={'seasons_in_category': 'value'})[
        ['personid', 'displayname', 'category', 'value', 'detail']].assign(alert_key='no_promotion')


def evaluate_alerts(ds: Dataset, cat_summary: pd.DataFrame, season_year: int,
                    config: Optional[Mapping[str, Any]] = None) -> pd.DataFrame:
    """Alertas vigentes de una temporada. Cada fila es un jugador y una alerta."""
    config = resolve_config(config)
    rules = ds.rules
    parts = []
    if config['yellow_cards']['enabled']:
        parts.append(_yellow_cards(ds, season_year))
    if config['low_participation']['enabled']:
        parts.append(_low_participation(cat_summary, season_year, rules.value('participation_threshold')))
    if config['playing_up']['enabled']:
        parts.append(_playing_up(ds, season_year))
    if config['no_promotion']['enabled']:
        principal = principal_categories(cat_summary)
        parts.append(_no_promotion(principal, season_year, rules.value('seasons_without_promotion')))
    parts = [p for p in parts if not p.empty]
    if not parts:
        return _empty().assign(alert='', color='')
    out = pd.concat(parts, ignore_index=True)
    # Jugadores con planillas contradictorias: sus cifras están incompletas, no se evalúan (se avisan aparte).
    out = out[~out['personid'].isin(ds.blocked_players(season_year)['personid'])]
    if out.empty:
        return _empty().assign(alert='', color='')
    out['alert'] = out['alert_key'].map(lambda k: alert_label(k, rules))
    out['color'] = out['alert_key'].map(lambda k: config[k]['color'])
    order = {a.key: i for i, a in enumerate(ALERT_DEFS)}
    return (out.assign(_order=out['alert_key'].map(order))
            .sort_values(['_order', 'displayname']).drop(columns='_order').reset_index(drop=True))
