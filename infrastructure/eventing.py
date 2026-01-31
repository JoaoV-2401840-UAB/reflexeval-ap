from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, DefaultDict
from collections import defaultdict


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


# ====== Analytics infrastructure ======

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


def build_default_event_bus() -> tuple[EventBus, InMemoryAnalyticsRepository, MetricsObserver]:
    """
    Helper para criar EventBus + observers default para o AP.
    Retorna: (bus, analytics_repo, metrics_observer)
    """
    bus = EventBus()
    repo = InMemoryAnalyticsRepository()
    metrics = MetricsObserver()
    analytics_observer = AnalyticsStoreObserver(repo)

    for ev in ["activity_deployed", "session_started", "session_submitted"]:
        bus.subscribe(ev, analytics_observer)
        bus.subscribe(ev, metrics)

    return bus, repo, metrics
