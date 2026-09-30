"""Datos de COMET que el seguimiento usa, a medias o todavía no puede usar, y qué se hace mientras tanto.

Este repositorio no modifica dataProject ni concede permisos. La columna `estado` distingue lo que ya existe
en COMET y se usa de lo que hay que confirmar, obtener o inspeccionar con autorización. Ninguna fila dice
que un dato «falta» sin haberlo comprobado.
"""
from __future__ import annotations

IN_USE = 'Existe en COMET: en uso'
TO_CONFIRM = 'Existe: significado por confirmar'
NO_ACCESS = 'Sin acceso del lector del portal'
MISSING = 'No disponible en los datos leídos'

PIPELINE_DEPENDENCIES: tuple[dict, ...] = (
    dict(estado=MISSING,
         dato='Citación completa de cada partido, incluidos los suplentes que no ingresaron',
         para='Suplentes que no ingresaron y "solo citación"',
         hoy='Se usan las filas de actuaciones marcadas como que no jugaron. Si COMET no las trae, esas cifras quedan '
             'vacías y el control de calidad lo avisa.'),
    dict(estado=MISSING,
         dato='Plantel oficial de cada categoría y temporada (quién pertenece a cada serie)',
         para='Jugadores no citados que no participaron; minutos posibles exactos',
         hoy='Referencial: quienes figuran en otra planilla de la misma competición.'),
    dict(estado=NO_ACCESS,
         dato='Cronología del partido (minuto de goles, tarjetas y cambios): tabla eventos_partido',
         para='Resultado con el jugador en cancha entendido como el marcador mientras jugó',
         hoy='La tabla existe, pero el lector del portal no tiene SELECT sobre ella y no se comprobó su contenido. '
             'No se concedieron permisos: falta una inspección autorizada de su calidad y cobertura. Mientras tanto, '
             'resultado final del partido en que el jugador sumó el mínimo de minutos.'),
    dict(estado=TO_CONFIRM,
         dato='Fecha «datefrom» de la ficha del jugador',
         para='Antigüedad en el club',
         hoy='La mayoría de las fichas la trae, pero su significado no está confirmado. Por defecto la antigüedad cuenta '
             'desde el primer partido registrado; la regla permite usar «datefrom» (sin dato si falta, sin sustituirla).'),
    dict(estado=MISSING,
         dato='Historial de categorías anterior al primer año leído',
         para='Temporadas sin promoción de categoría',
         hoy='Se cuenta con las temporadas leídas; el aviso indica desde qué año. La alerta no puede certificarse con un '
             'horizonte de una o dos temporadas.'),
    dict(estado=TO_CONFIRM,
         dato='Duración nominal de la competición (matchlength) y estado del partido (matchstatus)',
         para='Minutos posibles',
         hoy='Ambos existen y se leen. La duración registrada y la nominal difieren en algunos partidos y ninguna es «la '
             'correcta» por sí sola: la regla elige cuál usar y puede excluir estados (suspendido, etc.). Falta contrastar '
             'duración reglamentaria, descuentos y estado con el club.'),
    dict(estado=IN_USE,
         dato='Segunda amarilla (secondyellow)',
         para='Ciclo de tarjetas',
         hoy='Se muestra en planillas, historial y alerta, pero no se suma a las amarillas. Falta definir cómo cuenta y qué '
             'ocurre con las suspensiones cumplidas (no hay dato de suspensiones).'),
    dict(estado=IN_USE,
         dato='Autogoles (owngoals)',
         para='Goles por jugador frente al marcador',
         hoy='Se muestran aparte y no cuentan como goles a favor. Las filas son solo de O\'Higgins: los autogoles del rival '
             'no figuran en ellas.'),
    dict(estado=IN_USE,
         dato='Estatura y peso del jugador',
         para='Perfil con datos deportivos',
         hoy='Cobertura parcial: se muestran con «—» cuando faltan y tal como los entrega COMET, sin convertir unidades. '
             'Posición y pie hábil no figuran en las columnas leídas.'),
)
