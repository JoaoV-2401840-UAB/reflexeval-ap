import os
from flask import Flask, jsonify, request

from session_factory import (
    InMemoryConfigProvider,
    StandardSessionFactory,
    SessionService,
)

app = Flask(__name__)

# ====== JSON de configuração (params) ======

PARAMS_SCHEMA = {
    "schema_version": "1.0",
    "activity_type": "reflexeval_ap",
    "name": "ReflexEval AP – Autoavaliação e Reflexão Final",
    "params": [
        {
            "name": "criteria",
            "type": "list",
            "label": "Critérios de autoavaliação",
            "description": "Conjunto de critérios usados pelo aluno para se autoavaliar.",
            "items": [
                {
                    "name": "empenho",
                    "type": "ordinal",
                    "label": "Empenho",
                    "weight": 0.33,
                    "levels": ["Insuficiente", "Suficiente", "Bom", "Excelente"]
                },
                {
                    "name": "dominio",
                    "type": "ordinal",
                    "label": "Domínio dos conteúdos",
                    "weight": 0.34,
                    "levels": ["Insuficiente", "Suficiente", "Bom", "Excelente"]
                },
                {
                    "name": "autonomia",
                    "type": "ordinal",
                    "label": "Autonomia",
                    "weight": 0.33,
                    "levels": ["Insuficiente", "Suficiente", "Bom", "Excelente"]
                }
            ]
        },
        {
            "name": "sessions_number",
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
            "label": "Data limite para conclusão",
            "default": "2025-12-20T23:59:00Z"
        },
        {
            "name": "allow_revisions",
            "type": "boolean",
            "label": "Permitir revisões de respostas anteriores",
            "default": True
        },
        {
            "name": "reflection_prompts",
            "type": "list",
            "label": "Perguntas de reflexão",
            "item_type": "string",
            "default": [
                "O que aprendi desde a última sessão?",
                "Quais foram as maiores dificuldades?",
                "Que evidências mostram a minha evolução?"
            ]
        },
        {
            "name": "comment_enabled",
            "type": "boolean",
            "label": "Permitir comentários livres",
            "default": True
        },
        {
            "name": "consent_qualitative_analysis",
            "type": "boolean",
            "label": "Consentimento para análise qualitativa das respostas",
            "default": True
        },
        {
            "name": "locale",
            "type": "string",
            "label": "Locale",
            "default": "pt-PT"
        }
    ]
}

ANALYTICS_SCHEMA = {
    "schema_version": "1.0",
    "events": [
        {
            "name": "session_started",
            "type": "qualitative",
            "label": "Sessão iniciada",
            "payload_schema": {
                "instance_id": "string",
                "session_index": "integer",
                "user_id": "string",
                "started_at": "datetime"
            }
        },
        {
            "name": "session_submitted",
            "type": "mixed",
            "label": "Sessão submetida",
            "payload_schema": {
                "instance_id": "string",
                "session_index": "integer",
                "user_id": "string",
                "submitted_at": "datetime",
                "time_spent_seconds": "integer",
                "criteria_scores": {
                    "*criterion_id": "integer"
                },
                "confidence_level": "integer",
                "reflection_text": "string"
            }
        },
        {
            "name": "final_synthesis_published",
            "type": "mixed",
            "label": "Síntese final publicada",
            "payload_schema": {
                "instance_id": "string",
                "user_id": "string",
                "published_at": "datetime",
                "evolution_delta": "float",
                "consistency_gap": "float",
                "completion_rate": "float"
            }
        }
    ],
    "kpis": {
        "quantitative": [
            {
                "name": "avg_time_per_session",
                "type": "quantitative",
                "label": "Tempo médio por sessão (s)",
                "unit": "seconds",
                "source_event": "session_submitted",
                "formula": "AVG(time_spent_seconds)"
            },
            {
                "name": "confidence_trend",
                "type": "quantitative",
                "label": "Tendência de confiança (Δ médio)",
                "unit": "points",
                "source_event": "session_submitted",
                "formula": "AVG(delta(confidence_level))"
            },
            {
                "name": "consistency_gap_mean",
                "type": "quantitative",
                "label": "Média de consistência (gap)",
                "unit": "points",
                "source_event": "final_synthesis_published",
                "formula": "AVG(consistency_gap)"
            },
            {
                "name": "completion_rate",
                "type": "quantitative",
                "label": "Taxa de conclusão (%)",
                "unit": "percent",
                "source_event": "final_synthesis_published",
                "formula": "AVG(completion_rate)"
            }
        ],
        "qualitative": [
            {
                "name": "reflection_text_samples",
                "type": "qualitative",
                "label": "Amostras de textos de reflexão",
                "source_event": "session_submitted",
                "field": "reflection_text"
            }
        ]
    }
}

# ====== Endpoints ======

@app.route("/")
def home():
    return jsonify({
        "autor": [
            "João Valadares - UAb - 2401840",
        ],
        "message": "ReflexEval AP – AP operacional",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "params": "/params",
            "config": "/config",
            "deploy": "/deploy (POST)",
            "analyticsList": "/analytics/list",
            "analyticsGet": "/analytics/get"
        }
    })



@app.get("/params")
def get_params():
    """Equivalente a json_params_url."""
    return jsonify(PARAMS_SCHEMA)


@app.get("/config")
def get_config():
    """Equivalente a json_config_url."""
    plan_id = request.args.get("planId", "demo-plan")
    config = {
        "plan_id": plan_id,
        "params": PARAMS_SCHEMA
    }
    return jsonify(config)


@app.route("/deploy", methods=["GET", "POST"])
def deploy():
    """Equivalente a json_deploy_url."""
    if request.method == "GET":
        # Resposta amigável para quem acede pelo browser
        return jsonify({
            "message": "Use POST com JSON para fazer deploy da atividade.",
            "example": {
                "method": "POST",
                "url": "/deploy",
                "body": {
                    "user_id": "u1",
                    "plan_id": "p1"
                }
            }
        })

    # Se for POST, faz o comportamento normal
    data = request.json or {}
    user_id = data.get("user_id", "demo-user")
    plan_id = data.get("plan_id", "demo-plan")
    instance_id = f"instance-{plan_id}-{user_id}"
    response = {
        "instance_id": instance_id,
        "activity_url": f"https://reflexeval.example/{instance_id}",
        "initial_state": "ready"
    }
    return jsonify(response)



@app.get("/analytics/list")
def analytics_list():
    """Equivalente a analytics_list_url."""
    return jsonify(ANALYTICS_SCHEMA)


@app.get("/analytics/get")
def analytics_get():
    """Equivalente a analytics_get_url (dados dummy)."""
    instance_id = request.args.get("instance_id", "instance-demo")

    data = {
        "instance_id": instance_id,
        "metrics": {
            "avg_time_per_session": 420,
            "confidence_trend": 1.2,
            "consistency_gap_mean": 0.8,
            "completion_rate": 0.95
        },
        "events_sample": [
            {
                "event": "session_submitted",
                "session_index": 1,
                "time_spent_seconds": 380,
                "confidence_level": 3
            },
            {
                "event": "session_submitted",
                "session_index": 2,
                "time_spent_seconds": 450,
                "confidence_level": 4
            }
        ]
    }
    return jsonify(data)


if __name__ == "__main__":
    # Para desenvolvimento local (Render usa gunicorn)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
