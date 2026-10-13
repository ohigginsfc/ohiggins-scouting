"""Reportes, publicación y correos: sin red, datos privados ni efectos reales."""
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock
import sys
import pandas as pd
import pytest
from scouting.comet_reports import category, job, notify, sheets
from scouting.comet_reports.source import ReportSource
from scouting.comet_ingest.db_pipeline.specs import SPECS
from scouting.comet import mailer


def row(table, **values):
    base = {column.lower(): None for column in SPECS[table].cols}
    return {**base, **values}


def fixture_source(status='JUGADO'):
    source = ReportSource('https://example.supabase.co', 'synthetic')
    source.cache = {
        'equipos': [row('equipos', clubid=1, club="O'Higgins", clublongname="O'Higgins")],
        'competiciones': [row('competiciones', id=10, name='Torneo', category='U-18', season='2026', matchlength=90, playermaxage=18)],
        'jugadores': [row('jugadores', personid=1, displayname='Jugador sintético', firstname='Jugador', lastname='Sintético',
                         dateofbirth='2012-01-01', datefrom='2024-01-01')],
        'partidos': [row('partidos', matchid=20, id=10, hometeam=1, awayteam=2, matchdate='2026-03-02', matchstatus=status)],
        'actuaciones_jugadores': [row('actuaciones_jugadores', personid=1, id=10, matchid=20, clubid=1,
            minutesplayed=10, played=True, startinglineup=False, singleyellow=False, secondyellow=False,
            redcards=False, result='GANADO', goals=1, home=True)],
        'actuaciones_arqueros': [],
    }
    return source


def test_prepare_preserves_category_columns_and_alerts():
    frames = job.prepare(fixture_source(), season='2026')
    assert set(frames) == {'U-18', *job.ALERT_COLUMNS}
    report = frames['U-18'].iloc[0]
    assert report['Minutos'] == 10 and report['Suplente_entra'] == 1
    assert report['Goles'] == 1 and report['Partidos_Jugados'] == 1
    assert list(frames['Alertas Amarillas'].columns) == [*job.ALERT_COLUMNS['Alertas Amarillas'].values(), 'Última Actualización']
    assert frames['Alertas Amarillas'].empty
    assert len(frames['Jugadores Poco Utilizados']) == 1


def test_dry_run_never_constructs_sheets(monkeypatch):
    factory = Mock(side_effect=AssertionError('must not publish'))
    monkeypatch.setattr(job, 'ReportSheets', factory)
    receipt = job.run_reports(source=fixture_source(), season='2026')
    assert receipt['complete'] and receipt['mode'] == 'dry-run'
    assert all(tab['published'] == 0 for tab in receipt['tabs'].values())
    factory.assert_not_called()


def test_empty_or_unplayed_season_never_clears_existing_reports():
    for status in ('PROGRAMADO', 'SUSPENDIDO'):
        publisher = Mock()
        with pytest.raises(RuntimeError, match='No hay datos'):
            job.run_reports(publish=True, source=fixture_source(status), sheets=publisher, season='2026')
        publisher.replace.assert_not_called()


def test_all_calculations_finish_before_first_write(monkeypatch):
    publisher = Mock()
    monkeypatch.setattr(job.alerts, 'get_higher_category_alerts', Mock(side_effect=RuntimeError('calculation failed')))
    with pytest.raises(RuntimeError):
        job.run_reports(publish=True, source=fixture_source(), sheets=publisher, season='2026')
    publisher.replace.assert_not_called()


def test_publication_failure_is_not_a_complete_receipt():
    publisher = Mock()
    publisher.replace.side_effect = [None, RuntimeError('publication failed')]
    with pytest.raises(RuntimeError):
        job.run_reports(publish=True, source=fixture_source(), sheets=publisher, season='2026')
    assert publisher.replace.call_count == 2


def test_empty_alerts_are_explicitly_published_with_headers():
    publisher = Mock()
    result = job.run_reports(publish=True, source=fixture_source(), sheets=publisher, season='2026')
    assert result['complete'] and publisher.replace.call_count == 4
    empty = [call.args[1] for call in publisher.replace.call_args_list if call.args[0] == 'Alertas Amarillas'][0]
    assert empty.empty and 'Jugador' in empty


def test_pagination_order_and_complete_cache(monkeypatch):
    get = Mock(side_effect=[SimpleNamespace(status_code=206, headers={'Content-Range': '0-999/1001'}, json=lambda: [dict(personid=i) for i in range(1000)]),
                           SimpleNamespace(status_code=200, headers={'Content-Range': '1000-1000/1001'}, json=lambda: [dict(personid=1000)])])
    monkeypatch.setattr('scouting.comet_reports.source.requests.get', get)
    source = ReportSource('https://example.supabase.co', 'synthetic')
    assert len(source.rows('jugadores')) == 1001
    assert get.call_args_list[0].kwargs['params']['order'] == 'personid.asc'
    assert get.call_args_list[1].kwargs['params']['offset'] == 1000
    assert len(source.rows('jugadores')) == 1001 and get.call_count == 2


def test_server_page_cap_cannot_silently_truncate_report(monkeypatch):
    get = Mock(side_effect=[SimpleNamespace(status_code=206, headers={'Content-Range': '0-1/3'}, json=lambda: [{'personid': 1}, {'personid': 2}]),
                           SimpleNamespace(status_code=200, headers={'Content-Range': '2-2/3'}, json=lambda: [{'personid': 3}])])
    monkeypatch.setattr('scouting.comet_reports.source.requests.get', get)
    source = ReportSource('https://example.supabase.co', 'synthetic')
    assert len(source.rows('jugadores')) == 3
    assert get.call_args_list[1].kwargs['params']['offset'] == 2


def test_missing_exact_count_cannot_be_certified_as_complete(monkeypatch):
    get = Mock(return_value=SimpleNamespace(status_code=200, headers={'Content-Range': '0-0/*'}, json=lambda: [{'personid': 1}]))
    monkeypatch.setattr('scouting.comet_reports.source.requests.get', get)
    source = ReportSource('https://example.supabase.co', 'synthetic')
    with pytest.raises(RuntimeError, match='total de filas'):
        source.rows('jugadores')
    assert 'jugadores' not in source.cache


def test_read_failure_does_not_log_body_or_become_empty(monkeypatch):
    get = Mock(return_value=SimpleNamespace(status_code=403, text='PRIVATE TOKEN AND PLAYER'))
    monkeypatch.setattr('scouting.comet_reports.source.requests.get', get)
    source = ReportSource('https://example.supabase.co', 'synthetic')
    with pytest.raises(RuntimeError, match='HTTP 403') as error:
        source.rows('jugadores')
    assert 'PRIVATE' not in str(error.value) and 'jugadores' not in source.cache
    assert get.call_count == 1


def test_source_rejects_non_comet_tables_and_unknown_columns():
    source = fixture_source()
    with pytest.raises(ValueError):
        source.table('portal.accounts')
    with pytest.raises(ValueError):
        source.table('jugadores').select('password')


def test_sheet_empty_replace_atomic_raw_and_no_clear(monkeypatch):
    monkeypatch.setitem(sys.modules, 'gspread', SimpleNamespace(WorksheetNotFound=KeyError, APIError=ValueError))
    worksheet = Mock(id=1, row_count=100, col_count=10)
    publisher = sheets.ReportSheets.__new__(sheets.ReportSheets)
    publisher.document = Mock()
    publisher.document.worksheet.return_value = worksheet
    publisher.replace('Alertas', pd.DataFrame(columns=['Jugador']))
    body = publisher.document.batch_update.call_args.args[0]
    update = body['requests'][0]['updateCells']
    assert update['range']['endRowIndex'] == 100
    assert update['fields'] == 'userEnteredValue'
    assert len(update['rows']) == 1
    worksheet.clear.assert_not_called()
    publisher.replace('Alertas', pd.DataFrame({'Jugador': ['=UNTRUSTED()']}))
    values = publisher.document.batch_update.call_args.args[0]['requests'][0]['updateCells']['rows'][1]['values']
    assert values == [{'userEnteredValue': {'stringValue': '=UNTRUSTED()'}}]


def test_permission_error_does_not_create_duplicate_tab(monkeypatch):
    class APIError(Exception):
        pass
    monkeypatch.setitem(sys.modules, 'gspread', SimpleNamespace(WorksheetNotFound=KeyError, APIError=APIError))
    publisher = sheets.ReportSheets.__new__(sheets.ReportSheets)
    publisher.document = Mock()
    publisher.document.worksheet.side_effect = APIError('private remote error')
    with pytest.raises(RuntimeError) as error:
        publisher.replace('Alertas', pd.DataFrame({'Jugador': ['sintético']}))
    assert 'private remote' not in str(error.value)
    publisher.document.add_worksheet.assert_not_called()


def test_port_465_uses_ssl_without_starttls(monkeypatch):
    server = Mock()
    factory = Mock(return_value=server)
    monkeypatch.setattr(mailer.smtplib, 'SMTP_SSL', factory)
    config = mailer.smtp_config_from_env({'COMET_DIGEST_SMTP_HOST': 'smtp.example.test',
        'COMET_DIGEST_SMTP_FROM': 'a@example.test', 'COMET_DIGEST_SMTP_PORT': '465'})
    assert config.implicit_tls
    assert mailer.smtp_session(config, mailer.smtplib.SMTP) is server
    factory.assert_called_once()


def test_technical_email_has_only_status_and_run_link():
    session = MagicMock()
    factory = Mock(return_value=session)
    server = session.__enter__.return_value
    count = notify.send_status('failure', env={'COMET_REPORT_SMTP_USER': 'sender@example.test',
        'COMET_REPORT_SMTP_PASSWORD': 'synthetic-private', 'COMET_REPORT_NOTIFICATION_TO': 'a@example.test,a@example.test',
        'GITHUB_REPOSITORY': 'ohigginsfc/ohiggins-scouting', 'GITHUB_RUN_ID': '123'}, smtp_factory=factory)
    assert count == 1
    message = server.send_message.call_args.args[0]
    assert 'actions/runs/123' in message.get_content()
    assert 'synthetic-private' not in message.as_string()
    server.starttls.assert_not_called()


def test_missing_mail_configuration_cannot_pass():
    with pytest.raises(ValueError):
        notify.send_status('success', env={})


def test_smtp_validation_does_not_send_email():
    session = MagicMock()
    factory = Mock(return_value=session)
    notify.check_smtp(env={'COMET_REPORT_SMTP_USER': 'a@example.test', 'COMET_REPORT_SMTP_PASSWORD': 'synthetic'}, smtp_factory=factory)
    session.__enter__.return_value.login.assert_called_once()
    session.__enter__.return_value.send_message.assert_not_called()


def test_cli_masks_uncontrolled_errors_and_explains_controlled_errors(monkeypatch, capsys):
    from scripts import publish_comet_reports as cli
    from scouting.comet_reports.errors import ReportError
    monkeypatch.setattr(cli, 'run_reports', Mock(side_effect=RuntimeError('PRIVATE TOKEN')))
    assert cli.main([]) == 1 and 'PRIVATE TOKEN' not in capsys.readouterr().err
    monkeypatch.setattr(cli, 'run_reports', Mock(side_effect=ReportError('Lectura COMET jugadores: HTTP 403')))
    assert cli.main([]) == 1 and 'HTTP 403' in capsys.readouterr().err
