"""Preparar todo antes de escribir reportes por categoría y las tres alertas existentes."""
import os
from datetime import datetime, timezone
import pandas as pd
from . import category, alerts
from .source import ReportSource
from .sheets import ReportSheets

DEFAULT_SHEET_ID = '15R7y6NqN6ZEkcVc_TB8UMT2AQjGvavKQmiyblI1okYk'

ALERT_COLUMNS = {
    'Alertas Amarillas': {'competition_name': 'Competición', 'category_name': 'Categoría',
        'displayname': 'Jugador', 'total_accumulated': 'Amarillas Acumuladas', 'next_threshold': 'Límite Suspensión',
        'status': 'Estado', 'suspension_served': 'Suspensión liberada', 'last_sanction_date': 'Fecha Sanción',
        'last_team_match_date': 'Último Partido Equipo'},
    'Jugadores Poco Utilizados': {'competition_name': 'Competición', 'category_name': 'Categoría',
        'displayname': 'Jugador', 'total_minutes': 'Minutos Jugados', 'possible_minutes': 'Minutos Posibles',
        'percentage': '% Jugado'},
    'Jugadores en Categoría Superior': {'competition_name': 'Competición', 'competition_category': 'Categoría',
        'displayname': 'Jugador', 'age': 'Edad', 'category_age_limit': 'Edad Categoría',
        'age_difference': 'Diferencia Edad', 'total_minutes': 'Minutos Jugados'},
}


def prepare(source, *, season, club="O'Higgins"):
    club_id = category.get_club_id(source, club)
    if club_id is None:
        raise RuntimeError('No se pudo resolver el club para los reportes')
    data = category.load_base_data(source, club_id=club_id, season=season)
    master = category.compute_master_category_data(data)
    if not master:
        raise RuntimeError('No hay datos de partidos jugados para publicar; comprobar club y temporada')
    frames = {}
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    for name, frame in master.items():
        title = str(name).replace('/', '-').replace('\\', '-')[:50]
        if not title or title in frames or title in ALERT_COLUMNS:
            raise ValueError('Pestañas de categorías ambiguas')
        frames[title] = frame.assign(**{'Last Updated': now})
    findings = [alerts.get_yellow_card_alerts(source, season),
                alerts.get_low_minutes_alerts(source, threshold_percentage=20, season=season),
                alerts.get_higher_category_alerts(source, season)]
    for (title, columns), frame in zip(ALERT_COLUMNS.items(), findings):
        frame = frame.copy()
        if 'status' in frame:
            frame['status'] = frame['status'].replace({'WARNING_ONE_AWAY': 'PELIGRO', 'SUSPENDED_NEXT_MATCH': 'SUSPENDIDO'})
        if 'suspension_served' in frame:
            frame['suspension_served'] = frame['suspension_served'].map({True: 'SI', False: 'NO'})
        for key in ('last_sanction_date', 'last_team_match_date'):
            if key in frame:
                frame[key] = pd.to_datetime(frame[key], errors='coerce').dt.strftime('%d-%m-%Y')
        frame = frame.reindex(columns=list(columns)).rename(columns=columns)
        frames[title] = frame.assign(**{'Última Actualización': now})
    return frames


def run_reports(*, publish=False, source=None, sheets=None, season=None):
    season = str(season or os.environ.get('COMET_REPORT_SEASON', datetime.now().year))
    source = source or ReportSource.from_env()
    frames = prepare(source, season=season, club=os.environ.get('COMET_REPORT_CLUB', "O'Higgins"))
    summary = {'mode': 'publish' if publish else 'dry-run', 'season': season, 'complete': False,
               'tabs': {name: {'prepared': len(frame), 'published': 0} for name, frame in frames.items()}}
    if publish:
        sheets = sheets or ReportSheets(os.environ.get('COMET_REPORT_SHEET_ID', DEFAULT_SHEET_ID))
        for name, frame in frames.items():
            sheets.replace(name, frame)
            summary['tabs'][name]['published'] = len(frame)
    summary['complete'] = True
    return summary
