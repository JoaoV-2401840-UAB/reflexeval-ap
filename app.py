import os
from flask import Flask, jsonify, request

from session_factory import (
    InMemoryConfigProvider,
    StandardSessionFactory,
    SessionService,
)

from infrastructure.eventing import build_default_event_bus
from infrastructure.schemas import PARAMS_SCHEMA, PARAMS_SCHEMA_FOR_FACTORY, ANALYTICS_SCHEMA
from application.services import ActivityDeployService, AnalyticsQueryService, SessionApplicationService
from ui.pages import render_landing_page


def create_app() -> Flask:
    app = Flask(__name__)

    # ====== Eventing (Observer) wiring ======
    event_bus, analytics_repo, metrics_observer = build_default_event_bus()

    # ====== Factory Method wiring (sessões) ======
    config_provider = InMemoryConfigProvider(PARAMS_SCHEMA_FOR_FACTORY)
    factory = StandardSessionFactory()
    session_service = SessionService(factory=factory, config_provider=config_provider)

    # ====== Application services ======
    deploy_service = ActivityDeployService(event_bus)
    analytics_service = AnalyticsQueryService(analytics_repo, metrics_observer)
    session_app_service = SessionApplicationService(session_service, event_bus)

    # ====== Rotas (fina camada de entrada) ======

    @app.get("/")
def index():
    # Se o pedido vier de um browser, mostrar HTML; senão manter JSON
    if request.accept_mimetypes.accept_html and not request.accept_mimetypes.accept_json:
        return render_landing_page()

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
            "/debug/session"
        ]
    })

    @app.get("/home")
    def home():
        return render_landing_page()

    
    @app.get("/params/get")
    def params_get():
        return jsonify(PARAMS_SCHEMA)

    @app.post("/config/create")
    def config_create():
        data = request.json or {}
        plan_id = data.get("plan_id", "demo-plan")
        config = data.get("config", {})
        return jsonify({
            "plan_id": plan_id,
            "stored_config": config,
            "status": "created"
        })

    @app.route("/config/ui", methods=["GET", "POST"])
    def config_ui():
        return render_config_ui(PARAMS_SCHEMA)

    @app.route("/deploy", methods=["GET", "POST"])
    def deploy():
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

        result = deploy_service.deploy(user_id=user_id, plan_id=plan_id)
        return jsonify({
            "instance_id": result.instance_id,
            "activity_url": result.activity_url,
            "initial_state": result.initial_state
        })

    @app.get("/analytics/list")
    def analytics_list():
        return jsonify(ANALYTICS_SCHEMA)

    @app.get("/analytics/get")
    def analytics_get():
        instance_id = request.args.get("instance_id", "instance-demo")
        return jsonify(analytics_service.get_analytics(instance_id))

    @app.get("/debug/session")
    def debug_session():
        plan_id = request.args.get("planId", "demo-plan")
        try:
            session_index = int(request.args.get("sessionIndex", "1"))
        except ValueError:
            session_index = 1

        return jsonify(session_app_service.start_session(plan_id=plan_id, session_index=session_index))

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
