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
        Constrói um PlanConfig a partir do PARAMS_SCHEMA do app.py.
        Usa apenas os campos relevantes para o padrão de criação.
        """
        params = {p["name"]: p for p in params_schema.get("params", [])}

        sessions_number = int(params.get("sessions_number", {}).get("default", 3))
        reflection_interval_days = int(params.get("reflection_interval_days", {}).get("default", 7))
        deadline_utc = params.get("deadline_utc", {}).get("default", "2099-12-31T23:59:00Z")

        # pesos dos critérios
        criteria_param = params.get("criteria", {})
        items = criteria_param.get("items", [])
        weights = {item["name"]: float(item.get("weight", 1.0)) for item in items}

        # perguntas de reflexão definidas no schema
        reflection_prompts = params.get("reflection_prompts", {}).get("default", [])

        return cls(
            plan_id=plan_id,
            sessions_number=sessions_number,
            reflection_interval_days=reflection_interval_days,
            deadline_utc=deadline_utc,
            criteria_weights=weights,
            reflection_prompts=reflection_prompts,
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
    Implementação simples de IConfigProvider, usada para integrar com o PARAMS_SCHEMA
    do app.py sem base de dados.
    """

    def __init__(self, params_schema: dict) -> None:
        self._params_schema = params_schema

    def get_plan_config(self, plan_id: str) -> PlanConfig:
        return PlanConfig.from_params_schema(plan_id, self._params_schema)


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
