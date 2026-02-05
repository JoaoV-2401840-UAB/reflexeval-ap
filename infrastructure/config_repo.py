from __future__ import annotations
from typing import Dict, Any, Optional


class InMemoryPlanConfigRepository:
    """
    Repo in-memory: guarda config por plan_id.
    Suficiente para demonstração (sem BD), mas prova 'config por plano'.
    """
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def save(self, plan_id: str, config: Dict[str, Any]) -> None:
        self._store[plan_id] = dict(config or {})

    def get(self, plan_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(plan_id)
