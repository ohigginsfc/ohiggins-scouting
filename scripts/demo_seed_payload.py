"""Datos embebidos para scripts/seed_demo_data.py."""

from __future__ import annotations

DEMO_SEED_PAYLOAD = {
  "competition": "Primera División Chile",
  "demo_players": [
    {
      "full_name": "Jason León",
      "birth_date": "2000-05-11",
      "nationality": "Chile",
      "position": "Lateral izquierdo",
      "current_team": "Palestino",
      "preferred_foot": "Izquierdo",
      "height_cm": 174,
      "image_path": "data/images/players/jason_leon.png",
      "external_id": "1017320",
      "report": {
        "source_type": "manual",
        "source_name": "Scouting manual",
        "scout_name": "Scouter externo",
        "report_date": "2026-05-22",
        "position_observed": "Lateral izquierdo",
        "alternative_positions": [
          "Carrilero izquierdo",
          "Defensa izquierdo"
        ],
        "video_url": "https://www.youtube.com/watch?v=2Dmsd2OXONY",
        "rating": 7.35,
        "recommendation": "Interesante / seguimiento",
        "summary": "Lateral izquierdo agresivo y dinámico, con buena intensidad defensiva y capacidad para recorrer metros con balón. Destaca por su persistencia en los duelos, sus incorporaciones ofensivas y la calidad de sus centros. Perfil de recorrido largo más que de interpretación posicional compleja.",
        "strengths": "- Agresividad y persistencia defensiva.\n- Buena cercanía con el atacante en duelos 1vs1.\n- Capacidad de recuperación tras ser superado.\n- Buen timing en deslizamientos defensivos.\n- Largos recorridos conduciendo balón.\n- Incorporaciones ofensivas agresivas.\n- Buenos centros en último tercio.\n- Intensidad competitiva alta.",
        "weaknesses": "- Juego aéreo limitado.\n- Puede mejorar perfiles defensivos iniciales.\n- A veces depende demasiado del deslizamiento.\n- Comprensión táctica limitada en secuencias intermedias.\n- Lectura colectiva del juego mejorable."
      },
      "attributes": [
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Pase",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Control",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Perfil",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Conducción",
          "rating": 3.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Pérdida en salida",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Asume riesgos en la salida",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Encuentra línea de pases",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Lectura de juego",
          "rating": 2.75,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Recuperación de balón – agresividad · Va a campo rival",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Recuperación de balón – agresividad · Comete faltas",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Recuperación de balón – agresividad · Regresos",
          "rating": 3.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Recuperación de balón – agresividad · Velocidad",
          "rating": 3.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Duelo defensivo · Aéreo",
          "rating": 2.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Duelo defensivo · Ras de piso",
          "rating": 3.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Coberturas · Cierres",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Coberturas · Cruces a los costados",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Coberturas · Envuelve o da rebote",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · Ruptura interior",
          "rating": 2.75,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · Pasada espalda extremo",
          "rating": 3.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · Línea de fondo",
          "rating": 3.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · 3/4 cancha",
          "rating": 3.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · Llegada área rival",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Centro",
          "rating": 3.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Pase profundo",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Asistencia a tiro",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Asistencia",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Remate",
          "rating": 2.75,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Gol",
          "rating": 2.25,
          "max_rating": 4.0
        }
      ],
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 13.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 618.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.91,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.15,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.15,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 45.4369,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 79.8,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 7.5728,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 3.932,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 1.8932,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.4757,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.0194,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 2.4757,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 6.1165,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.932,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 1.4563,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 6.1165,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 73.9806,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 1.3107,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.8738,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.1456,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 5.3883,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.8738,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 476.0,
                "M": 142.0
              }
            }
          }
        ],
        "2024": [
          {
            "metric_name": "matches_played",
            "metric_value": 28.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1793.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.99,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.05,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.05,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 51.6007,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 79.8,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 10.9426,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 5.6721,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 1.0541,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.309,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.6525,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 2.56,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 5.4713,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.5137,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.8533,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 6.0234,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 76.7485,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 1.0541,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 1.2549,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.1506,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 2.8109,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.7027,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Palestino",
              "team_id": "3157",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1793.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Marcelo Flores",
      "birth_date": "2001-12-10",
      "nationality": "Chile",
      "position": "Lateral izquierdo",
      "current_team": "Limache",
      "preferred_foot": "Izquierdo",
      "height_cm": 176,
      "image_path": "data/images/players/marcelo_flores.jpeg",
      "external_id": "1197239",
      "report": {
        "source_type": "manual",
        "source_name": "Carga manual inicial",
        "scout_name": "Scouter externo",
        "report_date": "2026-05-22",
        "position_observed": "Lateral izquierdo",
        "alternative_positions": [
          "Central izquierdo"
        ],
        "video_url": "https://youtube.com/watch?v=UpmWz988eNw",
        "rating": 7.25,
        "recommendation": "Segunda opción interesante / seguimiento",
        "summary": "Defensor lateral izquierdo con buenas aptitudes para la marca, seguro en duelos individuales y con criterio en sus incorporaciones ofensivas. Puede ser una buena segunda opción para la posición, con capacidad para participar como titular durante la temporada. Por sus características defensivas también podría actuar como central izquierdo o stopper por el mismo sector.",
        "strengths": "- Técnica defensiva en 1v1: buen perfil corporal, centro de gravedad bajo y distancia adecuada con el atacante.\n- Agresividad, concentración y seguridad en la marca.\n- Buena velocidad en recorridos largos, aunque el primer sprint no es especialmente destacado.\n- Criterio ofensivo: resuelve simple, se ofrece en salida y dirige bien los pases elevados por banda.\n- Potencia física útil en incorporaciones al espacio.\n- Centros de calidad aceptable y capacidad para finalizar jugadas.\n- Remate con potencia y dirección, aunque poco frecuente.\n- Puede aportar como lateral izquierdo, central izquierdo o stopper por izquierda.",
        "weaknesses": "- Debe mejorar las vigilancias a su espalda en jugadas de lado opuesto.\n- Primer sprint solo aceptable.\n- Duelos aéreos defensivos irregulares: compite con salto y agresividad, pero alterna aciertos y errores.\n- Remate no especialmente destacado ni habitual.\n- Conviene contrastar su estado físico con datos objetivos, especialmente por referencias visuales de su etapa anterior."
      },
      "attributes": [
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Pase",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Control",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Perfil",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Conducción",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Pérdida en salida",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Asume riesgos en la salida",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Encuentra línea de pases",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "CONSTRUCCIÓN EN SALIDA",
          "attribute_name": "Pase de salida · Lectura de juego",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Recuperación de balón – agresividad · Va a campo rival",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Recuperación de balón – agresividad · Comete faltas",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Recuperación de balón – agresividad · Regresos",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Recuperación de balón – agresividad · Velocidad",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Duelo defensivo · Aéreo",
          "rating": 2.75,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Duelo defensivo · Ras de piso",
          "rating": 3.5,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Coberturas · Cierres",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Coberturas · Cruces a los costados",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "DEFENSIVO",
          "attribute_name": "Coberturas · Envuelve o da rebote",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · Ruptura interior",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · Pasada espalda extremo",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · Línea de fondo",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · 3/4 cancha",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Proyección en ataque · Llegada área rival",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Centro",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Pase profundo",
          "rating": 3.25,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Asistencia a tiro",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Asistencia",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Remate",
          "rating": 3.0,
          "max_rating": 4.0
        },
        {
          "attribute_group": "OFENSIVO",
          "attribute_name": "Finalización · Gol",
          "rating": 2.5,
          "max_rating": 4.0
        }
      ],
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1037.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.67,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.09,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 30.7232,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 76.0,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 6.162,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 2.6037,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.3472,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 1.0415,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.6943,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 4.0791,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 3.298,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.0376,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.8679,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.3848,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 61.1861,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 1.1283,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.2604,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.0868,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 3.9055,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.3472,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 779.0,
                "M": 258.0
              }
            }
          }
        ]
      }
    }
  ],
  "cohort_players": [
    {
      "full_name": "Cohort LI 01",
      "position": "Lateral izquierdo",
      "nationality": "Chile",
      "current_team": "Equipo cohorte 1",
      "external_id": "819088",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 13.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1156.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.77,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.08,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 48.8149,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 87.9,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 5.9948,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 3.2699,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.0779,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 0.7007,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.7907,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 5.5277,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 4.5934,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 2.4913,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 2.9585,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.8149,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 61.5052,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.2336,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.7007,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.2336,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Universidad Católica",
              "team_id": "3151",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1156.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Cohort LI 02",
      "position": "Lateral izquierdo",
      "nationality": "Chile",
      "current_team": "Equipo cohorte 2",
      "external_id": "1177235",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 13.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1146.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.84,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 46.3351,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 84.9,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 7.9319,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 4.0838,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.3927,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 1.178,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.7853,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 4.8691,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 3.6911,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 2.6702,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 1.7277,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 4.8691,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 64.0052,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.1571,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.7068,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.2356,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 1.0995,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.3141,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1146.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Cohort LI 03",
      "position": "Lateral izquierdo",
      "nationality": "Chile",
      "current_team": "Equipo cohorte 3",
      "external_id": "819075",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1080.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.72,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 29.0833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 86.2,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 3.75,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.6667,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 0.75,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.5,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 5.8333,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 3.0833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 2.25,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 1.6667,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.3333,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 41.25,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.0833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.5833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Ñublense",
              "team_id": "7029",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Cohort LI 04",
      "position": "Lateral izquierdo",
      "nationality": "Chile",
      "current_team": "Equipo cohorte 4",
      "external_id": "36995",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1080.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.88,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 39.5,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 90.7,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 2.6667,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.75,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.1667,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 1.3333,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.5,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 6.5,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 5.8333,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 4.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 3.9167,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.5833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 53.5,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.5833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.1667,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Huachipato",
              "team_id": "3164",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Cohort LI 05",
      "position": "Lateral izquierdo",
      "nationality": "Argentina",
      "current_team": "Equipo cohorte 5",
      "external_id": "875564",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1080.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.68,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 44.1667,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 83.0,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 7.75,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 2.6667,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.25,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 0.8333,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.0833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 5.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 1.75,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 1.5,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.5,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.75,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 57.0833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.0833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.3333,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.0833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 0.4167,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.0833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes Limache",
              "team_id": "331131",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1080.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Cohort LI 06",
      "position": "Lateral izquierdo",
      "nationality": "Chile",
      "current_team": "Equipo cohorte 6",
      "external_id": "1014795",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1071.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.99,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 48.8235,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 88.1,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 3.7815,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.9328,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.4202,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 1.1765,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.3445,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 4.7899,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 4.5378,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 4.1176,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 2.1008,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.6134,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 64.0336,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.5042,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.7563,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.084,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 0.2521,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1071.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Cohort LI 07",
      "position": "Lateral izquierdo",
      "nationality": "Argentina",
      "current_team": "Equipo cohorte 7",
      "external_id": "889519",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1035.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.57,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 32.9565,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 83.9,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 5.7391,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 2.8696,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.4348,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.5652,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 6.2609,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 4.8696,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 4.2609,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 2.1739,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 2.7826,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 47.7391,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.087,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.1739,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.2609,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Cobresal",
              "team_id": "3167",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1035.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Cohort LI 08",
      "position": "Lateral izquierdo",
      "nationality": "Chile",
      "current_team": "Equipo cohorte 8",
      "external_id": "1002931",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 13.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1029.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.7,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 22.4781,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 76.3,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 3.6735,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.2245,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.5248,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.0991,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.8746,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 4.0233,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 4.8105,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 1.8367,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.7872,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 2.7114,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 46.0933,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.1749,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 1.7493,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.3499,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 0.6997,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.1749,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Deportes La Serena",
              "team_id": "5031",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1029.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Cohort LI 09",
      "position": "Lateral izquierdo",
      "nationality": "Argentina",
      "current_team": "Equipo cohorte 9",
      "external_id": "895340",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 13.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1023.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.62,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.09,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 51.0264,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 83.3,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 9.9413,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 4.8387,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.176,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 0.7918,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.0557,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 5.9824,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 1.6716,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 1.5836,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.5279,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.607,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 62.7273,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.2639,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.088,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.176,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 0.088,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Audax Italiano",
              "team_id": "3162",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1023.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Cohort LI 10",
      "position": "Lateral izquierdo",
      "nationality": "Uruguay",
      "current_team": "Equipo cohorte 10",
      "external_id": "1015274",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1005.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 7.0,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.09,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 58.6567,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 86.0,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 7.0746,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 3.403,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.2687,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.3284,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.3582,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 4.3881,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 6.2687,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 4.8358,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 2.7761,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 4.0299,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 77.194,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.3582,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.806,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.1791,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 1.0746,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.2687,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "Colo-Colo",
              "team_id": "3155",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1005.0
              }
            }
          }
        ]
      }
    }
  ],
  "ohiggins_season_players": [
    {
      "full_name": "Omar Carabalí",
      "position": "Portero",
      "nationality": "Ecuador",
      "current_team": "O'Higgins",
      "external_id": "831242",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 990.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.85,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 30.2727,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 73.6,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 13.6364,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 5.8182,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.1818,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 0.6364,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 0.4545,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.0909,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 9.5455,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 40.4545,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.3636,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.1818,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "goodHighClaim_per90",
            "metric_value": 0.3636,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          },
          {
            "metric_name": "saves_per90",
            "metric_value": 2.7273,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 990.0
              }
            }
          }
        ],
        "2024": [
          {
            "metric_name": "matches_played",
            "metric_value": 28.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 2515.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.88,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 30.3101,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 66.0,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 16.0676,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 5.833,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 0.0358,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 0.7515,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 0.8231,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 0.0716,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.2147,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 11.7018,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 41.7972,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.6083,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.1789,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "redCard_per90",
            "metric_value": 0.0358,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "goodHighClaim_per90",
            "metric_value": 0.7157,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          },
          {
            "metric_name": "saves_per90",
            "metric_value": 2.2903,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "G",
              "objective_position_group": "Portero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "G",
              "match_position_minutes": {
                "G": 2515.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Felipe Ogaz",
      "position": "Mediocentro",
      "nationality": "Chile",
      "current_team": "O'Higgins",
      "external_id": "1177211",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 958.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 7.16,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.09,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.09,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 53.643,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 86.5,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 4.2276,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 2.4426,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.7516,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 3.0063,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.785,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 1.785,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 5.261,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.8518,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.6576,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 6.1065,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 68.2985,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.1879,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 1.4092,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.2818,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 0.3758,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.0939,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 958.0
              }
            }
          }
        ],
        "2024": [
          {
            "metric_name": "matches_played",
            "metric_value": 18.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 752.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.82,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.12,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 43.8032,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 74.6,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 5.3856,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 2.3936,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 1.1968,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.0346,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.7181,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 1.0771,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 4.9069,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.8298,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 1.3165,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 4.9069,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 58.5239,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.2394,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 1.3165,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.4787,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 1.0771,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.2394,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 752.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Francisco González",
      "position": "Mediocentro",
      "nationality": "Argentina",
      "current_team": "O'Higgins",
      "external_id": "983528",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 883.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 7.42,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.31,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.41,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 31.8007,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 86.5,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 1.9366,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.325,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 2.752,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 0.7135,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.2039,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 0.5096,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 5.6059,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 4.5866,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 1.0193,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.5674,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 58.4032,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 1.427,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 2.4462,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 10.1925,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 3.4655,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 719.0,
                "F": 164.0
              }
            }
          }
        ],
        "2024": [
          {
            "metric_name": "matches_played",
            "metric_value": 14.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 805.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 7.24,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.45,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.11,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 25.9379,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 77.6,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 2.4596,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.677,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 2.1242,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 0.6708,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.2236,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 0.4472,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 5.7019,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 5.3665,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 1.2298,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 2.9068,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 52.7702,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 1.7888,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 2.0124,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.1118,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 8.6087,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 2.795,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "F": 138.0,
                "M": 667.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Felipe Faúndez",
      "position": "Lateral izquierdo",
      "nationality": "Chile",
      "current_team": "O'Higgins",
      "external_id": "1482408",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 11.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 823.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 7.01,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.11,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 30.5103,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 81.7,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 3.8275,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.8591,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 1.4216,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.6245,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.8748,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 3.4994,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 5.4678,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 4.2649,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.5468,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.4994,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 60.4739,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.8748,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 1.4216,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.2187,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 2.4058,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.5468,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 823.0
              }
            }
          }
        ],
        "2024": [
          {
            "metric_name": "matches_played",
            "metric_value": 24.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1604.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.77,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.06,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.06,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 30.7481,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 66.4,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 5.1621,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.5711,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.7855,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.02,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.8978,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 2.9177,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 5.0499,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 5.3865,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 1.8516,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.591,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 57.6808,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.2805,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.8978,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.3367,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "redCard_per90",
            "metric_value": 0.0561,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 3.7594,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.7855,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1012.0,
                "M": 592.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Juan Leiva",
      "position": "Mediocentro",
      "nationality": "Chile",
      "current_team": "O'Higgins",
      "external_id": "844183",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 11.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 819.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.81,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 50.6593,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 88.7,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 3.0769,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.5385,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.6593,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.0879,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.5495,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 0.3297,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 3.1868,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.1868,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.4396,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 5.3846,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 61.4286,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.4396,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.2198,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.1099,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 0.7692,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 819.0
              }
            }
          }
        ],
        "2024": [
          {
            "metric_name": "matches_played",
            "metric_value": 28.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 2232.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 7.05,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.12,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.04,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 48.3468,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 81.4,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 5.8065,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 3.0645,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 1.0081,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 2.621,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.8065,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 1.4113,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 5.5242,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.5887,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 0.9677,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 6.6129,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 62.3387,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.9274,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 1.0081,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.2016,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 0.4435,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.121,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "M",
              "objective_position_group": "Mediocampo",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "M",
              "match_position_minutes": {
                "M": 2232.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Arnaldo Castillo",
      "position": "Delantero",
      "nationality": "Paraguay",
      "current_team": "O'Higgins",
      "external_id": "849177",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 12.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 745.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.65,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.36,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 22.7114,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 64.9,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 0.3624,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 0.2416,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.604,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 0.3624,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.3624,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 0.9664,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 6.8859,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 7.6107,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 5.4362,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 1.3289,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 35.6376,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.604,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.4832,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.3624,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 0.1208,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 0.1208,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 745.0
              }
            }
          }
        ],
        "2024": [
          {
            "metric_name": "matches_played",
            "metric_value": 26.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 734.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.9,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.37,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.25,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 25.3815,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 54.6,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 0.6131,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 0.1226,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 1.2262,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 0.6131,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.1226,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 0.6131,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 9.6866,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 9.8093,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 7.6022,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 2.9428,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 43.0381,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.6131,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.9809,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.6131,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "redCard_per90",
            "metric_value": 0.1226,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 0.6131,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "F",
              "objective_position_group": "Delantero",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "F",
              "match_position_minutes": {
                "F": 734.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Nicolás Garrido",
      "position": "Lateral izquierdo",
      "nationality": "Chile",
      "current_team": "O'Higgins",
      "external_id": "1002945",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 11.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 720.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.88,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 46.875,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 83.2,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 9.25,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 4.375,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.125,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 1.625,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 9.25,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 5.625,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.375,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 3.625,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 2.875,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 63.25,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.25,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.125,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.375,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 720.0
              }
            }
          }
        ],
        "2024": [
          {
            "metric_name": "matches_played",
            "metric_value": 23.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 1491.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 7.0,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.06,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 45.9356,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 81.7,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 8.9336,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 3.5614,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 0.2414,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 1.7505,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.9658,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 8.994,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 6.0362,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.0785,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 4.1046,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 2.0523,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 62.173,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.2414,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.0604,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          },
          {
            "metric_name": "redCard_per90",
            "metric_value": 0.0604,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 1491.0
              }
            }
          }
        ]
      }
    },
    {
      "full_name": "Luis Pavez Munoz",
      "position": "Lateral izquierdo",
      "nationality": "Chile",
      "current_team": "O'Higgins",
      "external_id": "339699",
      "objective_metrics": {
        "2025": [
          {
            "metric_name": "matches_played",
            "metric_value": 9.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 660.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 6.68,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.0,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 41.8636,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 82.4,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 3.5455,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 1.6364,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 1.3636,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 1.0909,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 0.9545,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 3.1364,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 3.6818,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.5455,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 1.5,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 3.4091,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 67.2273,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.5455,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.5455,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.5455,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 4.6364,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 1.3636,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 660.0
              }
            }
          }
        ],
        "2024": [
          {
            "metric_name": "matches_played",
            "metric_value": 28.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "minutesPlayed",
            "metric_value": 2466.0,
            "metric_unit": "count",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "avg_rating",
            "metric_value": 7.34,
            "metric_unit": "rating",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "goals_per90",
            "metric_value": 0.07,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "assists_per90",
            "metric_value": 0.22,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "totalPass_per90",
            "metric_value": 40.9854,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "pass_accuracy_pct",
            "metric_value": 77.8,
            "metric_unit": "pct",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "totalLongBalls_per90",
            "metric_value": 5.2555,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "accurateLongBalls_per90",
            "metric_value": 2.4088,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "keyPass_per90",
            "metric_value": 1.6423,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "totalTackle_per90",
            "metric_value": 1.6423,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "interceptionWon_per90",
            "metric_value": 1.1314,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "totalClearance_per90",
            "metric_value": 3.9781,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "duelWon_per90",
            "metric_value": 4.927,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "duelLost_per90",
            "metric_value": 3.3212,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "aerialWon_per90",
            "metric_value": 2.1898,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "ballRecovery_per90",
            "metric_value": 4.3796,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "touches_per90",
            "metric_value": 68.7956,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "successfulDribble_per90",
            "metric_value": 0.4745,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "wasFouled_per90",
            "metric_value": 0.6204,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "yellowCard_per90",
            "metric_value": 0.219,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "totalCross_per90",
            "metric_value": 4.927,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          },
          {
            "metric_name": "accurateCross_per90",
            "metric_value": 1.6423,
            "metric_unit": "per90",
            "raw_payload": {
              "dominant_match_position": "D",
              "objective_position_group": "Defensa",
              "team_name": "O'Higgins",
              "team_id": "3163",
              "sofascore_position": "D",
              "match_position_minutes": {
                "D": 2376.0,
                "M": 90.0
              }
            }
          }
        ]
      }
    }
  ]
}
