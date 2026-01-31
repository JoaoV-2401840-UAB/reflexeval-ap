from __future__ import annotations

from typing import Any, Dict


# ====== JSON de configuração (params) ======

PARAMS_SCHEMA: Dict[str, Any] = {
    "schema_version": "1.0",
    "activity_type": "reflexeval_ap",
    "ui": {
        "title": "ReflexEval — Activity Provider",
        "description": "Configuração da atividade de reflexão e autoavaliação."
    },
    "fields": [
        {
            "name": "course_name",
            "type": "string",
            "label": "Nome da unidade curricular",
            "default": "APS"
        },
        {
            "name": "num_sessions",
            "type": "integer",
            "label": "Número de sessões de reflexão",
            "default": 3,
            "min": 1,
            "max": 10
        },
        {
            "name": "reflection_interval_days",
            "type": "integer",
            "label": "Intervalo entre sessões (dias)",
            "default": 7,
            "min": 1,
            "max": 30
        },
        {
            "name": "deadline_utc",
            "type": "datetime",
            "label": "Data limite (UTC)",
            "default": "2026-01-31T23:59:59Z"
        },
        {
            "name": "criteria",
            "type": "array<string>",
            "label": "Critérios de avaliação (lista)",
            "default": ["Clareza", "Profundidade", "Consistência", "Evidência"]
        },
        {
            "name": "weights",
            "type": "object<string,number>",
            "label": "Pesos por critério",
            "default": {
                "Clareza": 0.25,
                "Profundidade": 0.25,
                "Consistência": 0.25,
                "Evidência": 0.25
            }
        }
    ]
}


def fields_to_params_schema(params_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter interno: converte PARAMS_SCHEMA(fields=...) para o formato interno esperado
    pelo módulo de sessões (params=[...]).
    """
    return {
        "params": [
            {
                "name": f["name"],
                "type": f["type"],
                "default": f.get("default"),
            }
            for f in params_schema.get("fields", [])
        ]
    }


PARAMS_SCHEMA_FOR_FACTORY = fields_to_params_schema(PARAMS_SCHEMA)


# ====== JSON de analytics list ======

ANALYTICS_SCHEMA: Dict[str, Any] = {
    "schema_version": "1.0",
    "activity_type": "reflexeval_ap",
    "quantitative": [
        {
            "name": "time_spent_seconds",
            "type": "integer",
            "label": "Tempo total gasto (segundos)",
            "unit": "s"
        },
        {
            "name": "confidence_level",
            "type": "integer",
            "label": "Nível de confiança auto-reportado",
            "min": 1,
            "max": 5
        },
        {
            "name": "consistency_gap",
            "type": "number",
            "label": "Gap de consistência (autoavaliação vs. rubrica)",
            "unit": "points"
        }
    ],
    "qualitative": [
        {
            "name": "reflection_notes",
            "type": "string",
            "label": "Notas de reflexão"
        },
        {
            "name": "evidence_links",
            "type": "array<string>",
            "label": "Links de evidências"
        }
    ],
    "events": [
        {
            "name": "session_started",
            "type": "event",
            "label": "Sessão iniciada"
        },
        {
            "name": "session_submitted",
            "type": "event",
            "label": "Sessão submetida"
        }
    ]
}
