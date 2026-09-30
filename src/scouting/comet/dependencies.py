"""Datos que el pipeline de COMET (dataProject) debería aportar y hoy no están disponibles.

Este repositorio no modifica dataProject. Cada fila indica qué se hace mientras tanto, para que
ninguna cifra parezca más precisa de lo que permiten los datos.
"""
from __future__ import annotations

PIPELINE_DEPENDENCIES: tuple[dict, ...] = (
    dict(dato='Citación completa de cada partido, incluidos los suplentes que no ingresaron',
         para='Suplentes que no ingresaron y "solo citación"',
         hoy='Se usan las filas de actuaciones de jugadores marcadas como que no jugaron. Si COMET no las trae, '
             'esas cifras quedan vacías y el control de calidad lo avisa.'),
    dict(dato='Plantel oficial de cada categoría y temporada (quién pertenece a cada serie)',
         para='Jugadores no citados que no participaron; minutos posibles exactos',
         hoy='Referencial: quienes figuran en otra planilla de la misma competición.'),
    dict(dato='Minuto de cada gol, tarjeta y cambio',
         para='Resultado con el jugador en cancha entendido como el marcador mientras jugó',
         hoy='Resultado final del partido en que el jugador sumó al menos el mínimo de minutos configurado.'),
    dict(dato='Fecha de ingreso al club de cada jugador',
         para='Antigüedad real y promedio de antigüedad por categoría',
         hoy='Años desde el primer partido de O\'Higgins registrado en COMET (es un mínimo).'),
    dict(dato='Historial de categorías anterior al primer año disponible',
         para='Temporadas sin promoción de categoría',
         hoy='Se cuenta con las temporadas que hay en COMET; el aviso indica desde qué año.'),
    dict(dato='Duración reglamentaria por categoría y estado del partido (suspendido, W.O.)',
         para='Minutos posibles',
         hoy='Minuto más largo registrado en cada partido; sin minutos registrados, el partido no cuenta.'),
    dict(dato='Doble amarilla, expulsión por acumulación y suspensiones cumplidas',
         para='Ciclo de tarjetas',
         hoy='Solo tarjetas amarillas simples, sin descontar suspensiones.'),
    dict(dato='Ficha deportiva ampliada (posición, pie hábil, estatura, peso)',
         para='Perfil con datos deportivos',
         hoy='Se muestran nombre, nacimiento, nacionalidad, nivel y estado.'),
    dict(dato='Autogoles diferenciados de los goles',
         para='Goles por jugador frente al marcador',
         hoy='Se muestran los goles de la planilla; el control de calidad avisa si no suman el marcador.'),
)
