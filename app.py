import os
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, DefaultDict
from collections import defaultdict

from flask import Flask, jsonify, request, render_template_string

from session_factory import (
    InMemoryConfigProvider,
    StandardSessionFactory,
    SessionService,
)

# =============================================================================
# Padrão Comportamental: Observer (Publish–Subscribe)
# =============================================================================

@dataclass(frozen=True)
class DomainEvent:
    name: str
    payload: Dict[str, Any]


class Observer(Protocol):
    def update(self, event: DomainEvent) -> None: ...


class EventBus:
    """Subject do padrão Observer."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[Observer]] = defaultdict(list)

    def subscribe(self, event_name: str, observer: Observer) -> None:
        self._subscribers[event_name].append(observer)

    def publish(self, event: DomainEvent) -> None:
        for obs in self._subscribers.get(event.name, []):
            obs.update(event)


class InMemoryAnalyticsRepository:
    """Repo simples para suportar /analytics/get (eventos)."""

    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []

    def add(self, event: DomainEvent) -> None:
        self._events.append({"event": event.name, **event.payload})

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self._events)


class AnalyticsStoreObserver:
    """Observer que persiste eventos."""

    def __init__(self, repo: InMemoryAnalyticsRepository) -> None:
        self._repo = repo

    def update(self, event: DomainEvent) -> None:
        self._repo.add(event)


class MetricsObserver:
    """Observer que mantém métricas simples (contagens por evento)."""

    def __init__(self) -> None:
        self.counts: Dict[str, int] = {}

    def update(self, event: DomainEvent) -> None:
        self.counts[event.name] = self.counts.get(event.name, 0) + 1


# =============================================================================
# App
# =============================================================================

app = Flask(__name__)

# ====== Observer setup ======
event_bus = EventBus()
analytics_repo = InMemoryAnalyticsRepository()
analytics_observer = AnalyticsStoreObserver(analytics_repo)
metrics_observer = MetricsObserver()

for ev in ["activity_deployed", "session_started", "session_submitted"]:
    event_bus.subscribe(ev, analytics_observer)
    event_bus.subscribe(ev, metrics_observer)

# =============================================================================
# Schemas (Inven!RA)
# =============================================================================

PARAMS_SCHEMA = {
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
            "default": [
                "Clareza",
                "Profundidade",
                "Consistência",
                "Evidência"
            ]
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

# Adapter interno: converte "fields" (Inven!RA) para "params" (session_factory)
PARAMS_SCHEMA_FOR_FACTORY = {
    "params": [
        {
            "name": f["name"],
            "type": f["type"],
            "default": f.get("default"),
        }
        for f in PARAMS_SCHEMA.get("fields", [])
    ]
}

ANALYTICS_SCHEMA = {
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

# =============================================================================
# UI HTML (para corrigir o feedback: página de configuração em HTML)
# =============================================================================

CONFIG_UI_HTML = """
<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ReflexEval — Configuração</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 40px; max-width: 980px; }
    h1 { margin: 0 0 8px; }
    .muted { color: #555; margin: 0 0 18px; }
    .links { margin: 12px 0 18px; }
    .links a { margin-right: 12px; }
    label { display:block; font-weight:600; margin-top: 14px; }
    input, textarea { width: 100%; padding: 10px; margin-top: 6px; box-sizing: border-box; }
    .row { display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    button { margin-top: 18px; padding: 10px 14px; cursor:pointer; }
    pre { background:#f6f6f6; padding:12px; overflow:auto; }
    .card { border: 1px solid #e5e5e5; border-radius: 12px; padding: 14px; margin-top: 14px; }
  </style>
</head>
<body>
  <h1>ReflexEval — Página de Configuração</h1>
  <div class="muted">
    Página HTML para configurar a atividade e gerar o JSON esperado pelo serviço <b>/config/create</b>.
  </div>

  <div class="links">
    <a href="/" target="_blank">/</a>
    <a href="/params/get" target="_blank">/params/get</a>
    <a href="/analytics/list" target="_blank">/analytics/list</a>
    <a href="/deploy" target="_blank">/deploy (GET)</a>
    <a href="/analytics/get" target="_blank">/analytics/get</a>
    <a href="/debug/session" target="_blank">/debug/session</a>
  </div>

  <form method="post" action="/config/ui">
    <label>plan_id</label>
    <input name="plan_id" value="{{ defaults.plan_id }}" />

    <div class="row">
      <div>
        <label>course_name</label>
        <input name="course_name" value="{{ defaults.course_name }}" />
      </div>
      <div>
        <label>num_sessions</label>
        <input name="num_sessions" type="number" min="1" max="10" value="{{ defaults.num_sessions }}" />
      </div>
    </div>

    <div class="row">
      <div>
        <label>reflection_interval_days</label>
        <input name="reflection_interval_days" type="number" min="1" max="30" value="{{ defaults.reflection_interval_days }}" />
      </div>
      <div>
        <label>deadline_utc</label>
        <input name="deadline_utc" value="{{ defaults.deadline_utc }}" />
      </div>
    </div>

    <label>criteria (uma por linha)</label>
    <textarea name="criteria" rows="4">{{ defaults.criteria_text }}</textarea>

    <label>weights (JSON)</label>
    <textarea name="weights" rows="4">{{ defaults.weights_json }}</textarea>

    <button type="submit">Gerar JSON e simular /config/create</button>
  </form>

  {% if payload %}
    <div class="card">
      <h2>Payload gerado</h2>
      <pre>{{ payload }}</pre>
    </div>

    <div class="card">
      <h2>Resposta simulada do /config/create</h2>
      <pre>{{ response }}</pre>
    </div>
  {% endif %}
</body>
</html>
"""

# =============================================================================
# Serviços (Inven!RA)
# =============================================================================

@app.route("/")
def index():
    return jsonify({
        "name": "ReflexEval Activity Provider",
        "status": "ok",
        "endpoints": [
            "/params/get",
            "/config/create",
            "/config/ui (GET/POST)  [HTML]",
            "/deploy (GET/POST)",
            "/analytics/list",
            "/analytics/get",
            "/debug/session",
        ]
    })


@app.get("/params/get")
def params_get():
    """Equivalente a json_params_url."""
    return jsonify(PARAMS_SCHEMA)


@app.post("/config/create")
def config_create():
    """Equivalente a config_create_url (demonstração simples)."""
    data = request.json or {}
    plan_id = data.get("plan_id", "demo-plan")
    config = data.get("config", {})

    # Numa versão real guardaríamos em BD. Para demo, apenas devolve.
    return jsonify({
        "plan_id": plan_id,
        "stored_config": config,
        "status": "created"
    })


@app.get("/config/ui")
def config_ui_get():
    # Defaults a partir do schema (se quiseres, podes ir buscar sempre ao PARAMS_SCHEMA)
    defaults = {
        "plan_id": "demo-plan",
        "course_name": "APS",
        "num_sessions": 3,
        "reflection_interval_days": 7,
        "deadline_utc": "2026-01-31T23:59:59Z",
        "criteria_text": "Clareza\nProfundidade\nConsistência\nEvidência",
        "weights_json": '{"Clareza":0.25,"Profundidade":0.25,"Consistência":0.25,"Evidência":0.25}',
    }
    return render_template_string(CONFIG_UI_HTML, defaults=defaults)


@app.post("/config/ui")
def config_ui_post():
    plan_id = request.form.get("plan_id", "demo-plan")
    course_name = request.form.get("course_name", "APS")

    try:
        num_sessions = int(request.form.get("num_sessions", "3"))
    except ValueError:
        num_sessions = 3

    try:
        reflection_interval_days = int(request.form.get("reflection_interval_days", "7"))
    except ValueError:
        reflection_interval_days = 7

    deadline_utc = request.form.get("deadline_utc", "2026-01-31T23:59:59Z")

    criteria = [
        c.strip()
        for c in (request.form.get("criteria", "") or "").splitlines()
        if c.strip()
    ]

    weights_raw = request.form.get("weights", "{}") or "{}"
    try:
        weights = json.loads(weights_raw)
    except json.JSONDecodeError:
        weights = {}

    payload_obj = {
        "plan_id": plan_id,
        "config": {
            "course_name": course_name,
            "num_sessions": num_sessions,
            "reflection_interval_days": reflection_interval_days,
            "deadline_utc": deadline_utc,
            "criteria": criteria,
            "weights": weights,
        }
    }

    # Simula resposta do /config/create (não faz HTTP interno)
    response_obj = {
        "plan_id": plan_id,
        "stored_config": payload_obj["config"],
        "status": "created"
    }

    defaults = {
        "plan_id": plan_id,
        "course_name": course_name,
        "num_sessions": num_sessions,
        "reflection_interval_days": reflection_interval_days,
        "deadline_utc": deadline_utc,
        "criteria_text": "\n".join(criteria) if criteria else "",
        "weights_json": json.dumps(weights, ensure_ascii=False),
    }

    return render_template_string(
        CONFIG_UI_HTML,
        defaults=defaults,
        payload=json.dumps(payload_obj, indent=2, ensure_ascii=False),
        response=json.dumps(response_obj, indent=2, ensure_ascii=False),
    )


@app.route("/deploy", methods=["GET", "POST"])
def deploy():
    """Equivalente a json_deploy_url."""
    if request.method == "GET":
        return jsonify({
            "message": "Use POST com JSON para fazer deploy da atividade.",
            "example": {
                "method": "POST",
                "url": "/deploy",
                "body": {"user_id": "u1", "plan_id": "p1"}
            }
        })

    data = request.json or {}
    user_id = data.get("user_id", "demo-user")
    plan_id = data.get("plan_id", "demo-plan")
    instance_id = f"instance-{plan_id}-{user_id}"

    response = {
        "instance_id": instance_id,
        "activity_url": f"https://reflexeval.example/{instance_id}",
        "initial_state": "ready",
    }

    # Evento interno (Observer)
    event_bus.publish(DomainEvent(
        name="activity_deployed",
        payload={"plan_id": plan_id, "user_id": user_id, "instance_id": instance_id}
    ))

    return jsonify(response)


@app.get("/analytics/list")
def analytics_list():
    """Equivalente a analytics_list_url."""
    return jsonify(ANALYTICS_SCHEMA)


@app.get("/analytics/get")
def analytics_get():
    """Equivalente a analytics_get_url (devolve eventos reais do AP)."""
    instance_id = request.args.get("instance_id", "instance-demo")
    return jsonify({
        "instance_id": instance_id,
        "events": analytics_repo.list_all(),
        "metrics": metrics_observer.counts
    })


# =============================================================================
# Factory Method — Session Service
# =============================================================================

config_provider = InMemoryConfigProvider(PARAMS_SCHEMA_FOR_FACTORY)
factory = StandardSessionFactory()
session_service = SessionService(factory=factory, config_provider=config_provider)


@app.get("/debug/session")
def debug_session():
    """
    Endpoint de teste para demonstrar o padrão Factory Method em ação.
    Exemplo: /debug/session?planId=demo-plan&sessionIndex=1
    """
    plan_id = request.args.get("planId", "demo-plan")
    try:
        session_index = int(request.args.get("sessionIndex", "1"))
    except ValueError:
        session_index = 1

    vm = session_service.start_session(plan_id=plan_id, session_index=session_index)

    # Evento interno (Observer)
    event_bus.publish(DomainEvent(
        name="session_started",
        payload={
            "plan_id": vm.plan_id,
            "session_index": vm.session_index,
            "session_type": vm.session_type
        }
    ))

    return jsonify({
        "plan_id": vm.plan_id,
        "session_index": vm.session_index,
        "session_type": vm.session_type,
        "title": vm.title,
        "intro": vm.intro,
        "questions": vm.questions,
        "criteria_weights": vm.criteria_weights,
    })


if __name__ == "__main__":
    # Para desenvolvimento local (Render define PORT)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
