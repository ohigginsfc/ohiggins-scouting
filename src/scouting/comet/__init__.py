"""Cálculos deportivos de COMET (categorías, minutos, alertas, adelantados).

Este paquete es puro: recibe DataFrames y devuelve DataFrames. No abre conexiones,
no usa Streamlit y no decide permisos; el acceso a datos y la autorización viven en
`app/comet_followup.py` y `scouting.comet.config_store`.
"""
