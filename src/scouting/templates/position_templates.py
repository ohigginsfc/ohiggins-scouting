"""Plantillas de atributos subjetivos por posición (criterios por bloque).

Estructura almacenada:
  POSITION_TEMPLATES[plantilla][bloque] -> lista de attribute_name
  attribute_name = "subcriterio · aspecto" (p. ej. "Pase de salida · Pase")

La UI de ficha usa posiciones finas (Lateral izquierdo, …); resolve_template_key_for_position
mapea a la plantilla (Lateral, Volante central, …).
"""

from __future__ import annotations

# --- Plantillas por rol (claves internas) ---

_PORTERO: dict[str, list[str]] = {
    "CONSTRUCCIÓN EN SALIDA": [
        "Salida propio arco · Pase",
        "Salida propio arco · Control",
        "Salida propio arco · Perfil",
        "Salida propio arco · Bajo presión",
        "Salida propio arco · Se ofrece como opción de pase",
        "Salida propio arco · Asume riesgos en la salida",
        "Salida propio arco · Salida larga",
        "Salida propio arco · Genera transiciones",
    ],
    "DEFENSIVO": [
        "Juego aéreo · Lateral",
        "Juego aéreo · Frontal",
        "Juego aéreo · Pelota detenida",
        "Lectura de juego · Rápido en salida",
        "Lectura de juego · Pierde referencia del arco",
        "Lectura de juego · Retarda / corta ataque",
        "Atajadas · Remate fuera del área",
        "Atajadas · Dentro del área y bajo el arco",
        "Atajadas · Envuelve o da rebote",
    ],
}

_CENTRAL: dict[str, list[str]] = {
    "CONSTRUCCIÓN EN SALIDA": [
        "Pase de salida · Pase",
        "Pase de salida · Control",
        "Pase de salida · Perfil",
        "Pase de salida · Conducción",
        "Pase de salida · Pérdida en salida",
        "Pase de salida · Asume riesgos en la salida",
        "Pase de salida · Encuentra línea de pases",
        "Pase de salida · Lectura de juego",
    ],
    "DEFENSIVO": [
        "Recuperación de balón – agresividad · Va a campo rival",
        "Recuperación de balón – agresividad · Comete faltas",
        "Recuperación de balón – agresividad · Regresos",
        "Recuperación de balón – agresividad · Velocidad",
        "Duelo defensivo · Aéreo",
        "Duelo defensivo · Ras de piso",
        "Coberturas · Cierres",
        "Coberturas · Cruces a los costados",
        "Coberturas · Envuelve o da rebote",
    ],
    "OFENSIVO": [
        "Juego aéreo · Gol",
        "Juego aéreo · Ocasión de gol",
        "Juego aéreo · Gana en área rival",
    ],
}

_LATERAL: dict[str, list[str]] = {
    "CONSTRUCCIÓN EN SALIDA": [
        "Pase de salida · Pase",
        "Pase de salida · Control",
        "Pase de salida · Perfil",
        "Pase de salida · Conducción",
        "Pase de salida · Pérdida en salida",
        "Pase de salida · Asume riesgos en la salida",
        "Pase de salida · Encuentra línea de pases",
        "Pase de salida · Lectura de juego",
    ],
    "DEFENSIVO": [
        "Recuperación de balón – agresividad · Va a campo rival",
        "Recuperación de balón – agresividad · Comete faltas",
        "Recuperación de balón – agresividad · Regresos",
        "Recuperación de balón – agresividad · Velocidad",
        "Duelo defensivo · Aéreo",
        "Duelo defensivo · Ras de piso",
        "Coberturas · Cierres",
        "Coberturas · Cruces a los costados",
        "Coberturas · Envuelve o da rebote",
    ],
    "OFENSIVO": [
        "Proyección en ataque · Ruptura interior",
        "Proyección en ataque · Pasada espalda extremo",
        "Proyección en ataque · Línea de fondo",
        "Proyección en ataque · 3/4 cancha",
        "Proyección en ataque · Llegada área rival",
        "Finalización · Centro",
        "Finalización · Pase profundo",
        "Finalización · Asistencia a tiro",
        "Finalización · Asistencia",
        "Finalización · Remate",
        "Finalización · Gol",
    ],
}

_VOLANTE_CENTRAL: dict[str, list[str]] = {
    "CONSTRUCCIÓN EN SALIDA": [
        "Pase de salida · Pase",
        "Pase de salida · Control",
        "Pase de salida · Perfil",
        "Pase de salida · Conducción",
        "Pase de salida · Pérdida en salida",
        "Pase de salida · Asume riesgos en la salida",
        "Pase de salida · Encuentra línea de pases",
        "Pase de salida · Lectura de juego",
        "Pase de salida · Desmarques",
    ],
    "DEFENSIVO": [
        "Recuperación de balón – agresividad · Va a campo rival",
        "Recuperación de balón – agresividad · Comete faltas",
        "Recuperación de balón – agresividad · Regresos",
        "Recuperación de balón – agresividad · Velocidad",
        "Duelo defensivo · Aéreo",
        "Duelo defensivo · Ras de piso",
        "Coberturas · Cierres",
        "Coberturas · Cruces a los costados",
        "Coberturas · Tercer central",
    ],
    "OFENSIVO": [
        "Juego ofensivo · Rupturas",
        "Juego ofensivo · Llegada",
        "Juego ofensivo · Gol",
        "Juego ofensivo · Asistencia",
        "Juego ofensivo · Asistencia a tiro",
    ],
}

_VOLANTE_MIXTO: dict[str, list[str]] = {
    "CONSTRUCCIÓN": [
        "Pase de salida · Pase",
        "Pase de salida · Control",
        "Pase de salida · Perfil",
        "Pase de salida · Conducción",
        "Pase de salida · Pérdida en salida",
        "Pase de salida · Asume riesgos en la salida",
        "Pase de salida · Encuentra línea de pases",
        "Pase de salida · Lectura de juego",
        "Pase de salida · Desmarques",
        "Pase de salida · Gana espalda rival",
        "Elaboración · Verticalidad",
        "Elaboración · Lateralización",
        "Elaboración · Pase profundo",
        "Elaboración · Pase gol",
    ],
    "DEFENSIVO": [
        "Recuperación de balón · Presión salida rival",
        "Recuperación de balón · Regreso",
        "Recuperación de balón · Agresividad",
        "Recuperación de balón · Cierres",
        "Recuperación de balón · Cruces a los costados",
    ],
    "OFENSIVO": [
        "Situación de gol · Gol",
        "Situación de gol · Remate",
        "Situación de gol · Llegada al área",
        "1 vs 1 en ataque · Gambeta",
        "1 vs 1 en ataque · Roce físico",
        "1 vs 1 en ataque · Velocidad",
    ],
}

_VOLANTE_OFENSIVO: dict[str, list[str]] = {
    "CONSTRUCCIÓN": list(_VOLANTE_MIXTO["CONSTRUCCIÓN"]),
    "DEFENSIVO": list(_VOLANTE_MIXTO["DEFENSIVO"]),
    "OFENSIVO": list(_VOLANTE_MIXTO["OFENSIVO"]),
}

_EXTREMO: dict[str, list[str]] = {
    "CONSTRUCCIÓN": [
        "Pase de salida · Pase",
        "Pase de salida · Control",
        "Pase de salida · Perfil",
        "Pase de salida · Hacia adentro / afuera",
        "Pase de salida · Encuentra líneas",
        "Pase de salida · Lectura de juego",
        "Pase de salida · Desmarques",
        "Pase de salida · Gana espalda rival",
        "Pase de salida · Inserción en circuito de juego",
        "Pase de salida · Pase filtrado",
    ],
    "DEFENSIVO": [
        "Regreso defensivo · Colabora con lateral",
        "Regreso defensivo · Recuperación balón alto/campo rival",
        "Regreso defensivo · Presión",
    ],
    "OFENSIVO": [
        "Finalización · Pase profundo",
        "Finalización · Asistencia a tiro",
        "Finalización · Asistencia",
        "Finalización · Llegada al área",
        "Finalización · Remate",
        "Finalización · Gol",
        "Duelo ofensivo · 1 vs 1",
        "Duelo ofensivo · Gambeta",
        "Duelo ofensivo · Línea o al espacio",
        "Duelo ofensivo · Rápido",
        "Duelo ofensivo · Mantiene amplitud",
        "Duelo ofensivo · Movilidad y desmarque",
    ],
}

_DELANTERO: dict[str, list[str]] = {
    "CONSTRUCCIÓN": [
        "Juego de espalda · Apoyo",
        "Juego de espalda · Descarga",
        "Juego de espalda · Fuerza",
        "Juego de espalda · Asociación",
        "Juego de espalda · Asistencia",
    ],
    "DEFENSIVO": [
        "Presión salida rival · Presión",
    ],
    "OFENSIVO": [
        "Finalización · En el área",
        "Finalización · Fuera del área",
        "Finalización · Juego aéreo",
        "Finalización · Referencia de área",
        "Finalización · Remate",
        "Finalización · Gol",
        "Movilidad · Diagonales",
        "Movilidad · Ataque primer palo",
        "Movilidad · Velocidad",
    ],
}

POSITION_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "Portero": _PORTERO,
    "Central": _CENTRAL,
    "Lateral": _LATERAL,
    "Volante central": _VOLANTE_CENTRAL,
    "Volante mixto": _VOLANTE_MIXTO,
    "Volante ofensivo": _VOLANTE_OFENSIVO,
    "Extremo": _EXTREMO,
    "Delantero": _DELANTERO,
}

# Posición de ficha (UI) o legacy → clave de plantilla
_POSITION_TO_TEMPLATE: dict[str, str] = {
    "portero": "Portero",
    "arquero": "Portero",
    "central": "Central",
    "central derecho": "Central",
    "central izquierdo": "Central",
    "lateral": "Lateral",
    "lateral derecho": "Lateral",
    "lateral izquierdo": "Lateral",
    "mediocentro defensivo": "Volante central",
    "mediocentro": "Volante mixto",
    "mediocentro ofensivo": "Volante ofensivo",
    "volante central": "Volante central",
    "volante mixto": "Volante mixto",
    "volante ofensivo": "Volante ofensivo",
    "extremo": "Extremo",
    "extremo derecho": "Extremo",
    "extremo izquierdo": "Extremo",
    "delantero": "Delantero",
}


def resolve_template_key_for_position(position: str | None) -> str:
    """
    Mapea posición de ficha (p. ej. Lateral izquierdo) a clave de plantilla (Lateral).
  """
    if position is None or not str(position).strip():
        raise KeyError("Posición vacía")
    key = str(position).strip().lower()
    if key in _POSITION_TO_TEMPLATE:
        return _POSITION_TO_TEMPLATE[key]
    # Coincidencia exacta con nombre de plantilla
    for template_key in POSITION_TEMPLATES:
        if key == template_key.lower():
            return template_key
    raise KeyError(f"Posición no soportada: {position}")


def attribute_count_for_template(template_key: str) -> int:
    template = POSITION_TEMPLATES[template_key]
    return sum(len(attrs) for attrs in template.values())
