from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from infrastructure.eventing import DomainEvent, EventBus, InMemoryAnalyticsRepository, MetricsObserver


@dataclass(frozen=True)
class DeployResult:
    instance_id: str
    activity_url: str
    initial_state: str


class ActivityDeployService:
    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus

    def deploy(self, user_id: str, plan_id: str) -> DeployResult:
        instance_id = f"instance-{plan_id}-{user_id}"
        result = DeployResult(
            instance_id=instance_id,
            activity_url=f"https://reflexeval.example/{instance_id}",
            initial_state="ready",
        )

        self._bus.publish(DomainEvent(
            name="activity_deployed",
            payload={"plan_id": plan_id, "user_id": user_id, "instance_id": instance_id}
        ))

        return result


class AnalyticsQueryService:
    def __init__(self, repo: InMemoryAnalyticsRepository, metrics: MetricsObserver) -> None:
        self._repo = repo
        self._metrics = metrics

    def get_analytics(self, instance_id: str) -> Dict[str, Any]:
        return {
            "instance_id": instance_id,
            "events": self._repo.list_all(),
            "metrics": self._metrics.counts
        }


class SessionApplicationService:
    """
    Serviço de aplicação que coordena o subsistema de sessões e publica eventos.
    """
    def __init__(self, session_service: Any, event_bus: EventBus) -> None:
        self._session_service = session_service
        self._bus = event_bus

    def start_session(self, plan_id: str, session_index: int) -> Dict[str, Any]:
        vm = self._session_service.start_session(plan_id=plan_id, session_index=session_index)

        self._bus.publish(DomainEvent(
            name="session_started",
            payload={
                "plan_id": vm.plan_id,
                "session_index": vm.session_index,
                "session_type": vm.session_type
            }
        ))

        return {
            "plan_id": vm.plan_id,
            "session_index": vm.session_index,
            "session_type": vm.session_type,
            "title": vm.title,
            "intro": vm.intro,
            "questions": vm.questions,
            "criteria_weights": vm.criteria_weights,
        }
