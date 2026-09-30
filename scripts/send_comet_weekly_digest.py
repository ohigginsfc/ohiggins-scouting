"""Genera y, solo si se pide, envía el resumen semanal de COMET. Por defecto NO envía nada.

    python scripts/send_comet_weekly_digest.py                       # vista previa en la consola
    python scripts/send_comet_weekly_digest.py --week-of 2026-09-21 --html-out resumen.html
    python scripts/send_comet_weekly_digest.py --send                # envía; ver condiciones abajo

Envío (--send) solo si se cumplen las cuatro condiciones; si falta alguna, no se envía y sale con código 2:
  1. La regla "Destinatarios del resumen semanal" tiene correos y está marcada como confirmada por el club.
  2. Hay servicio de correo: COMET_DIGEST_SMTP_HOST y COMET_DIGEST_SMTP_FROM (y opcionalmente _PORT, _USER,
     _PASSWORD, _STARTTLS) en el entorno. La clave nunca se pasa por argumento ni se guarda en el repositorio.
  3. Hay registro de entregas: PORTAL_AUTH_DATABASE_URL con la migración 003 aplicada (tabla
     portal.comet_digest_deliveries). Sin registro no se puede garantizar que un correo no salga dos veces.
  4. Se pasa --send de forma explícita.

Como mucho una entrega por semana y destinatario: cada correo se reserva en el registro antes de enviarse, así que
dos ejecuciones de la misma semana no lo repiten. Un envío que falla se reintenta en la próxima ejecución (hasta
--max-attempts); una reserva que quedó sin cerrar (el proceso murió a medias) se informa y NO se repite sola, porque
el correo pudo haber salido. Código de salida 1 si algo quedó fallido, agotado o en duda.

El cálculo es el mismo de las pantallas (reglas, períodos de selección y alertas guardados en Supabase), así que el
correo y la pantalla no pueden mostrar cifras distintas para la misma semana.

Lee COMET con COMET_DATABASE_URL (rol de solo lectura). Este script no está programado en ningún lado: programarlo
es una decisión posterior a que Pablo confirme destinatarios, día y hora.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import pandas as pd

from scouting.comet import alerts as alert_rules
from scouting.comet import config_store, mailer, queries
from scouting.comet.digest import build_weekly_digest, previous_week
from scouting.comet.facts import LOCAL_TZ
from scouting.comet.ledger import DEFAULT_MAX_ATTEMPTS, PostgresLedger
from scouting.comet.pipeline import compute_all

NO_PERIODS = pd.DataFrame(columns=['id', 'personid', 'kind', 'starts_on', 'ends_on', 'note', 'active', 'start', 'end'])


def connect_read_only(env):
    """Conexión de solo lectura a COMET, con las mismas opciones que la pantalla del portal."""
    import psycopg
    dsn = env.get('COMET_DATABASE_URL', '').strip()
    if not dsn:
        raise SystemExit('Falta COMET_DATABASE_URL (conexión de solo lectura de COMET).')
    return psycopg.connect(dsn, connect_timeout=10, autocommit=True,
                           options='-c default_transaction_read_only=on -c search_path=public -c statement_timeout=30000')


def load_stored(env):
    """(reglas guardadas, períodos, aviso). Sin configuración disponible: valores por defecto y un aviso."""
    if not env.get('PORTAL_AUTH_DATABASE_URL', '').strip():
        return {}, NO_PERIODS, 'PORTAL_AUTH_DATABASE_URL no está definida'
    try:
        settings, _, periods = config_store.load_all_for_job()
        return settings, periods, None
    except config_store.StoreUnavailable as exc:
        return {}, NO_PERIODS, str(exc)


def run(argv=None, *, env=None, load_raw=None, stored=None, now=None, smtp_factory=None, ledger=None, out=print):
    """`stored` = (reglas, períodos, aviso); `ledger` = registro de entregas (por defecto, el de Supabase)."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--week-of', help='una fecha dentro de la semana a resumir (AAAA-MM-DD); por defecto, la semana anterior')
    parser.add_argument('--html-out', help='guarda la versión HTML en este archivo')
    parser.add_argument('--send', action='store_true', help='envía el correo (ver condiciones en la ayuda)')
    parser.add_argument('--max-attempts', type=int, default=DEFAULT_MAX_ATTEMPTS,
                        help='intentos de envío por semana y destinatario (por defecto %(default)s)')
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    today = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz=LOCAL_TZ).tz_localize(None)

    if load_raw is None:
        conn = connect_read_only(env)
        load_raw = lambda: queries.fetch_raw(lambda sql, params: pd.read_sql_query(sql, conn, params=params))  # noqa: E731
    settings, periods, warning = stored if stored is not None else load_stored(env)
    if warning:
        out(f'Aviso: se usan las reglas por defecto y sin períodos de selección ({warning}).')
    alert_key = config_store.ALERT_CONFIG_KEY
    computed = compute_all(load_raw(), {k: v for k, v in settings.items() if k != alert_key}, periods)
    ds, rules = computed.ds, computed.ds.rules
    if args.week_of:
        anchor = pd.Timestamp(args.week_of).date()
        week_start = anchor - timedelta(days=anchor.weekday())
    else:
        week_start = previous_week(today)[0]
    season = ds.current_season(pd.Timestamp(week_start + timedelta(days=6)))
    found = (alert_rules.evaluate_alerts(ds, computed.cat, season, (settings.get(alert_key) or {}).get('value'))
             if season else pd.DataFrame(columns=['alert_key']))
    digest = build_weekly_digest(ds, found, week_start, generated_on=today.date(), pending_rules=len(rules.pending()),
                                 blocked=len(ds.blocked_players(season)) if season else 0)
    if args.html_out:
        Path(args.html_out).write_text(digest.html, encoding='utf8')
        out(f'HTML guardado en {args.html_out}')
    if not args.send:
        out(digest.text)
        out('\n(Vista previa: no se envió nada. Usa --send cuando el club haya confirmado destinatarios y correo.)')
        return 0

    recipients = rules.value('digest_recipients')
    if not recipients or not rules.confirmed('digest_recipients'):
        out('No se envía: los destinatarios no están definidos o no han sido confirmados por el club.')
        return 2
    smtp = mailer.smtp_config_from_env(env)
    if smtp is None:
        out('No se envía: falta configurar COMET_DIGEST_SMTP_HOST y COMET_DIGEST_SMTP_FROM.')
        return 2
    if ledger is None:
        if not env.get('PORTAL_AUTH_DATABASE_URL', '').strip():
            out('No se envía: falta PORTAL_AUTH_DATABASE_URL para el registro de entregas (evita correos repetidos).')
            return 2
        ledger = PostgresLedger()
    kwargs = {'smtp_factory': smtp_factory} if smtp_factory else {}
    try:
        report = mailer.send_digest_once(digest, recipients, smtp, ledger, max_attempts=args.max_attempts, **kwargs)
    except config_store.StoreUnavailable as exc:
        out(f'No se envía: el registro de entregas no está disponible ({exc}).')
        return 2
    out(f'Enviados ahora: {len(report.sent)} · ya enviados antes (omitidos): {len(report.already_sent)}.')
    if report.failed:
        out(f'Fallaron {len(report.failed)}: se reintentan en la próxima ejecución (hasta {args.max_attempts} intentos).')
    if report.exhausted:
        out(f'Sin más intentos: {len(report.exhausted)} destinatario(s). Revisar el servicio de correo.')
    if report.in_doubt or report.unrecorded:
        out(f'En duda: {len(report.in_doubt) + len(report.unrecorded)} destinatario(s) con una reserva sin cerrar. '
            'No se reenvían solos (el correo pudo haber salido): confirmar a mano.')
    return 0 if report.clean else 1


if __name__ == '__main__':
    sys.exit(run())
