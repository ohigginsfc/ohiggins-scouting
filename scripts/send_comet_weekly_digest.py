"""Genera y, solo si se pide, envía el resumen semanal de COMET. Por defecto NO envía nada.

    python scripts/send_comet_weekly_digest.py                       # vista previa en la consola
    python scripts/send_comet_weekly_digest.py --week-of 2026-09-21 --html-out resumen.html
    python scripts/send_comet_weekly_digest.py --send                # envía; ver condiciones abajo

Envío (--send) solo si se cumplen las tres condiciones; si falta alguna, no se envía y sale con código 2:
  1. La regla "Destinatarios del resumen semanal" tiene correos y está marcada como confirmada por el club.
  2. Hay servicio de correo: COMET_DIGEST_SMTP_HOST, COMET_DIGEST_SMTP_FROM (y opcionalmente _PORT, _USER,
     _PASSWORD, _STARTTLS) en el entorno. La clave nunca se pasa por argumento ni se guarda en el repositorio.
  3. Se pasa --send de forma explícita.

Lee COMET con COMET_DATABASE_URL (rol de solo lectura) y la configuración con PORTAL_AUTH_DATABASE_URL
(solo lectura). Este script no está programado en ningún lado: programarlo es una decisión posterior a
que Pablo confirme destinatarios, día y hora.
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
from scouting.comet import config_store, mailer, metrics, queries
from scouting.comet.digest import build_weekly_digest, previous_week
from scouting.comet.facts import LOCAL_TZ, build_dataset
from scouting.comet.rules import Rules


def connect_read_only(env):
    """Conexión de solo lectura a COMET, con las mismas opciones que la pantalla del portal."""
    import psycopg
    dsn = env.get('COMET_DATABASE_URL', '').strip()
    if not dsn:
        raise SystemExit('Falta COMET_DATABASE_URL (conexión de solo lectura de COMET).')
    return psycopg.connect(dsn, connect_timeout=10, autocommit=True,
                           options='-c default_transaction_read_only=on -c search_path=public -c statement_timeout=30000')


def load_stored(env):
    """Reglas y configuración guardadas; si no están disponibles, valores por defecto (con aviso)."""
    if not env.get('PORTAL_AUTH_DATABASE_URL', '').strip():
        return {}, 'PORTAL_AUTH_DATABASE_URL no está definida'
    try:
        settings, _, _ = config_store.load_all_for_job()
        return settings, None
    except config_store.StoreUnavailable as exc:
        return {}, str(exc)


def run(argv=None, *, env=None, load_raw=None, stored=None, now=None, smtp_factory=None, out=print):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--week-of', help='una fecha dentro de la semana a resumir (AAAA-MM-DD); por defecto, la semana anterior')
    parser.add_argument('--html-out', help='guarda la versión HTML en este archivo')
    parser.add_argument('--send', action='store_true', help='envía el correo (ver condiciones en la ayuda)')
    args = parser.parse_args(argv)
    env = os.environ if env is None else env
    today = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz=LOCAL_TZ).tz_localize(None)

    if load_raw is None:
        conn = connect_read_only(env)
        load_raw = lambda: queries.fetch_raw(lambda sql, params: pd.read_sql_query(sql, conn, params=params))  # noqa: E731
    settings, warning = stored if stored is not None else load_stored(env)
    if warning:
        out(f'Aviso: se usan las reglas por defecto ({warning}).')
    rules = Rules({k: v for k, v in settings.items() if k != config_store.ALERT_CONFIG_KEY})
    raw = load_raw()
    ds = build_dataset(raw['sheet'], raw['matches'], raw['players'], raw['goalkeepers'], rules)
    if args.week_of:
        anchor = pd.Timestamp(args.week_of).date()
        week_start = anchor - timedelta(days=anchor.weekday())
    else:
        week_start = previous_week(today)[0]
    season = ds.current_season(pd.Timestamp(week_start + timedelta(days=6)))
    comp = metrics.add_percentages(metrics.player_competition_summary(ds))
    found = (alert_rules.evaluate_alerts(ds, metrics.category_summary(comp), season,
                                         (settings.get(config_store.ALERT_CONFIG_KEY) or {}).get('value'))
             if season else pd.DataFrame(columns=['alert_key']))
    digest = build_weekly_digest(ds, found, week_start, generated_on=today.date(), pending_rules=len(rules.pending()))
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
    kwargs = {'smtp_factory': smtp_factory} if smtp_factory else {}
    sent = mailer.send_digest(digest, recipients, smtp, **kwargs)
    out(f'Resumen enviado a {sent} destinatarios.')
    return 0


if __name__ == '__main__':
    sys.exit(run())
