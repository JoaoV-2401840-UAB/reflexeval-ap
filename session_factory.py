from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Protocol
from abc import ABC, abstractmethod

@dataclass
class PlanConfig:
    """
    Representa a configuração de um plano (planId) para o ReflexEval AP,
    construída a partir do PARAMS_SCHEMA definido no app.py.
    """
    plan_id: str
    sessions_number: int
    reflection_interval_days: int
    deadline_utc: str
    criteria_weights: Dict[str, float] = field(default_factory=dict)
    reflection_prompts: List[str] = field(default_factory=list)

    @classmethod
    def from_params_schema(cls, plan_id: str, params_schema: dict) -> "PlanConfig":
        """
        Constrói PlanConfig a partir do schema interno (params).
        NOTA: este schema vem do Adapter fields->params (PARAMS_SCHEMA_FOR_FACTORY).
        """
        params = {p["name"]: p for p in params_schema.get("params", [])}

        num_sessions = int(params.get("num_sessions", {}).get("default", 3))
        reflection_interval_days = int(params.get("reflection_interval_days", {}).get("default", 7))
        deadline_utc = params.get("deadline_utc", {}).get("default", "2099-12-31T23:59:00Z")

        # criteria: lista
        criteria = params.get("criteria", {}).get("default", []) or []

        # weights: dict criterion -> weight
        weights = params.get("weights", {}).get("default", {}) or {}

        # Se não houver weights definidos, distribuir pesos uniformes pelos critérios
        if (not isinstance(weights, dict) or not weights) and criteria:
            w = 1.0 / float(len(criteria))
            weights = {c: w for c in criteria}

        return cls(
            plan_id=plan_id,
            sessions_number=num_sessions,  # mantemos nome interno
            reflection_interval_days=reflection_interval_days,
            deadline_utc=deadline_utc,
            criteria_weights={k: float(v) for k, v in (weights or {}).items()},
            reflection_prompts=[],  # neste schema atual não tens prompts
        )

@dataclass
class ReflectionSessionViewModel:
    """
    ViewModel simples para expor uma sessão de reflexão (para um endpoint ou UI).
    """
    plan_id: str
    session_index: int
    session_type: str
    title: str
    intro: str
    questions: List[str]
    criteria_weights: Dict[str, float]


class ReflectionSession(ABC):
    """
    Classe base abstrata (Product do Factory Method).
    """

    def __init__(self, plan_config: PlanConfig, session_index: int) -> None:
        self.plan_config = plan_config
        self.session_index = session_index

    @abstractmethod
    def get_session_type(self) -> str:
        ...

    @abstractmethod
    def build_title(self) -> str:
        ...

    @abstractmethod
    def build_intro(self) -> str:
        ...

    def build_questions(self) -> List[str]:
        """
        Comportamento por omissão: reutiliza as perguntas globais de reflexão
        definidas em reflection_prompts.
        """
        return list(self.plan_config.reflection_prompts)

    def to_view_model(self) -> ReflectionSessionViewModel:
        return ReflectionSessionViewModel(
            plan_id=self.plan_config.plan_id,
            session_index=self.session_index,
            session_type=self.get_session_type(),
            title=self.build_title(),
            intro=self.build_intro(),
            questions=self.build_questions(),
            criteria_weights=self.plan_config.criteria_weights,
        )

class InitialReflectionSession(ReflectionSession):
    def get_session_type(self) -> str:
        return "initial"

    def build_title(self) -> str:
        return "Reflexão inicial"

    def build_intro(self) -> str:
        return (
            "Esta é a primeira sessão de reflexão. "
            "Regista expectativas, ponto de partida e objetivos pessoais."
        )

class IntermediateReflectionSession(ReflectionSession):
    def get_session_type(self) -> str:
        return "intermediate"

    def build_title(self) -> str:
        return f"Reflexão intermédia #{self.session_index}"

    def build_intro(self) -> str:
        return (
            "Sessão de reflexão intermédia. "
            "Foca-te nas dificuldades recentes e na evolução desde a última sessão."
        )

class FinalReflectionSession(ReflectionSession):
    def get_session_type(self) -> str:
        return "final"

    def build_title(self) -> str:
        return "Reflexão final e autoavaliação"

    def build_intro(self) -> str:
        return (
            "Última sessão de reflexão. "
            "Sintetiza o teu percurso, evidências de aprendizagem e autoavaliação final."
        )

    def build_questions(self) -> List[str]:
        base = super().build_questions()
        extra = [
            "Que evidências concretas mostram a tua evolução ao longo da unidade curricular?",
            "Se repetisses a unidade curricular, o que farias de forma diferente?",
        ]
        return base + extra

class SessionFactory(ABC):
    """
    Creator abstrato do Factory Method.
    """

    @abstractmethod
    def create_session(self, plan_config: PlanConfig, session_index: int) -> ReflectionSession:
        ...


class StandardSessionFactory(SessionFactory):
    """
    Implementação concreta do Factory Method:
    decide que tipo de sessão criar (inicial, intermédia ou final)
    com base no índice da sessão e na configuração do plano.
    """

    def create_session(self, plan_config: PlanConfig, session_index: int) -> ReflectionSession:
        if session_index <= 1:
            return InitialReflectionSession(plan_config, session_index)
        elif session_index < plan_config.sessions_number:
            return IntermediateReflectionSession(plan_config, session_index)
        else:
            return FinalReflectionSession(plan_config, session_index)

class IConfigProvider(Protocol):
    """
    Porto abstrato para obter PlanConfig (permite trocar origem da config).
    """

    def get_plan_config(self, plan_id: str) -> PlanConfig:
        ...


class InMemoryConfigProvider:
    """
    Integra schema (defaults) + config guardada por plano (overrides).
    """
    def __init__(self, params_schema: dict, plan_config_repo=None) -> None:
        self._params_schema = params_schema
        self._repo = plan_config_repo  # pode ser None

    def get_plan_config(self, plan_id: str) -> PlanConfig:
        base = PlanConfig.from_params_schema(plan_id, self._params_schema)

        if not self._repo:
            return base

        overrides = self._repo.get(plan_id) or {}
        if not isinstance(overrides, dict) or not overrides:
            return base

        # aplicar overrides no objeto base (apenas os campos que existem)
        if "num_sessions" in overrides:
            base.sessions_number = int(overrides["num_sessions"])
        if "reflection_interval_days" in overrides:
            base.reflection_interval_days = int(overrides["reflection_interval_days"])
        if "deadline_utc" in overrides:
            base.deadline_utc = str(overrides["deadline_utc"])

        criteria = overrides.get("criteria")
        weights = overrides.get("weights")

        if isinstance(criteria, list):
            # se critérios vierem, e weights não, gera uniformes
            if not isinstance(weights, dict) or not weights:
                w = 1.0 / float(len(criteria)) if criteria else 1.0
                base.criteria_weights = {c: w for c in criteria}
            else:
                base.criteria_weights = {k: float(v) for k, v in weights.items()}
        elif isinstance(weights, dict) and weights:
            base.criteria_weights = {k: float(v) for k, v in weights.items()}

        return base

class SessionService:
    """
    Serviço de aplicação que usa o Factory Method para criar sessões de reflexão.
    Este é o ponto de entrada do resto do sistema para o padrão de criação.
    """

    def __init__(self, config_provider: IConfigProvider, factory: SessionFactory) -> None:
        self._config_provider = config_provider
        self._factory = factory

    def start_session(self, plan_id: str, session_index: int) -> ReflectionSessionViewModel:
        plan_config = self._config_provider.get_plan_config(plan_id)
        session = self._factory.create_session(plan_config, session_index)
        return session.to_view_model()
