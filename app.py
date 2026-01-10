import os
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, DefaultDict
from collections import defaultdict

from flask import Flask, jsonify, request

from session_factory import (
    InMemoryConfigProvider,
    StandardSessionFactory,
    SessionService,
)


# ====== Padrão Comportamental: Observer (Publish–Subscribe) ======

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
    """Repo simples para suportar /analytics/get."""

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


app = Flask(__name__)

# ====== Observer setup ======
event_bus = EventBus()
analytics_repo = InMemoryAnalyticsRepository()
analytics_observer = AnalyticsStoreObserver(analytics_repo)
metrics_observer = MetricsObserver()

for ev in ["activity_deployed", "session_started", "session_submitted"]:
    event_bus.subscribe(ev, analytics_observer)
    event_bus.subscribe(ev, metrics_observer)

# ====== JSON de configuração (params) ======

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

# ====== JSON de analytics list ======

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

# ====== Serviços (Inven!RA) ======

@app.route("/")
def index():
    return jsonify({
        "name": "ReflexEval Activity Provider",
        "status": "ok",
        "endpoints": [
            "/params/get",
            "/config/create",
            "/deploy (GET/POST)",
            "/analytics/list",
            "/analytics/get",
            "/debug/session"
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

    # Aqui numa versão real guardaríamos em BD. Para demo, só devolve.
    return jsonify({
        "plan_id": plan_id,
        "stored_config": config,
        "status": "created"
    })


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
    """Equivalente a analytics_get_url (agora devolve eventos reais do AP)."""
    instance_id = request.args.get("instance_id", "instance-demo")

    # Dados reais (eventos publicados pelos endpoints do AP)
    return jsonify({
        "instance_id": instance_id,
        "events": analytics_repo.list_all(),
        "metrics": metrics_observer.counts
    })


# ====== Factory Method (Semana 4) — Session Service ======

config_provider = InMemoryConfigProvider()
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
