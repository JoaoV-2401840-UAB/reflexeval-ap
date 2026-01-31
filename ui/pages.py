from __future__ import annotations

from typing import Any, Dict
from flask import render_template_string, request


CONFIG_UI_TEMPLATE = """
<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>ReflexEval — Config UI</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
    .box { max-width: 900px; margin: 0 auto; }
    textarea, input { width: 100%; padding: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    button { padding: 10px 14px; cursor: pointer; }
    .muted { color: #555; font-size: 0.95rem; }
    pre { background: #f6f6f6; padding: 12px; overflow: auto; }
  </style>
</head>
<body>
<div class="box">
  <h1>ReflexEval — Configuração</h1>
  <p class="muted">
    Esta página gera um payload para <code>POST /config/create</code>.
  </p>

  <form method="post">
    <div class="row">
      <div>
        <label>plan_id</label>
        <input name="plan_id" value="{{ plan_id }}"/>
      </div>
      <div>
        <label>user_id (opcional)</label>
        <input name="user_id" value="{{ user_id }}"/>
      </div>
    </div>

    <p class="muted">Config (JSON)</p>
    <textarea name="config_json" rows="14">{{ config_json }}</textarea>
    <p>
      <button type="submit">Gerar payload</button>
    </p>
  </form>

  {% if payload %}
    <h2>Payload gerado</h2>
    <pre>{{ payload }}</pre>
  {% endif %}

  <h2>Schema disponível</h2>
  <p class="muted">GET /params/get devolve o schema completo de configuração.</p>
</div>
</body>
</html>
"""


def render_config_ui(params_schema: Dict[str, Any]) -> str:
    plan_id = request.form.get("plan_id", "demo-plan") if request.method == "POST" else "demo-plan"
    user_id = request.form.get("user_id", "") if request.method == "POST" else ""

    default_config = {f["name"]: f.get("default") for f in params_schema.get("fields", [])}
    config_json = request.form.get("config_json") if request.method == "POST" else _pretty_json(default_config)

    payload = None
    if request.method == "POST":
        payload = _pretty_json({"plan_id": plan_id, "config": _safe_parse_json(config_json)})

    return render_template_string(
        CONFIG_UI_TEMPLATE,
        plan_id=plan_id,
        user_id=user_id,
        config_json=config_json,
        payload=payload,
    )


def _safe_parse_json(txt: str):
    import json
    try:
        return json.loads(txt)
    except Exception:
        return {"_error": "JSON inválido", "_raw": txt}


def _pretty_json(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, indent=2)

def render_landing_page() -> str:
    return render_template_string("""
<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>ReflexEval — Activity Provider</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 40px; max-width: 920px; }
    h1 { margin: 0 0 6px; }
    .muted { color: #555; margin: 0 0 18px; }
    ul { line-height: 1.9; }
    a { text-decoration: none; }
    code { background: #f6f6f6; padding: 2px 6px; border-radius: 6px; }
  </style>
</head>
<body>
  <h1>ReflexEval — Activity Provider</h1>
  <p class="muted">
    Página de navegação rápida para testes e validação manual dos serviços.
  </p>

  <h2>Configuração</h2>
  <ul>
    <li><a href="/params/get"><code>/params/get</code></a> — schema de configuração</li>
    <li><a href="/config/ui"><code>/config/ui</code></a> — UI HTML de configuração</li>
    <li><code>POST /config/create</code> — criar/guardar configuração (JSON)</li>
  </ul>

  <h2>Deploy e Analytics</h2>
  <ul>
    <li><a href="/deploy"><code>/deploy</code></a> — GET com exemplo; POST faz deploy</li>
    <li><a href="/analytics/list"><code>/analytics/list</code></a> — schema de analytics</li>
    <li><a href="/analytics/get"><code>/analytics/get</code></a> — eventos e métricas recolhidas</li>
  </ul>

  <h2>Demonstração</h2>
  <ul>
    <li><a href="/debug/session"><code>/debug/session</code></a> — Factory Method (sessões)</li>
  </ul>

  <hr/>
  <p class="muted">
    Nota: para clientes API, <code>/</code> continua a devolver JSON (Accept: application/json).
  </p>
</body>
</html>
""")
