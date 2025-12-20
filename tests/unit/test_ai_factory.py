import pytest
from mindbug_engine.core.consts import Difficulty
from mindbug_ai.factory import AgentFactory
from mindbug_ai.interface import AgentInterface
from mindbug_ai.agent import HeuristicAgent


def test_factory_creates_heuristic_agent():
    """Vérifie que la factory retourne bien un agent configuré."""
    # FIX : Argument 'difficulty' et Enum
    agent = AgentFactory.create_agent(difficulty=Difficulty.HARD, strategy="HEURISTIC")

    assert isinstance(agent, HeuristicAgent)
    assert isinstance(agent, AgentInterface)
    assert agent.difficulty == Difficulty.HARD


def test_factory_accepts_string_difficulty():
    """Vérifie que la factory sait convertir 'HARD' en Difficulty.HARD."""
    agent = AgentFactory.create_agent(difficulty="HARD")
    assert agent.difficulty == Difficulty.HARD


def test_factory_fail_fast_on_unknown_strategy():
    """Vérifie que la factory plante sur une stratégie inconnue."""
    with pytest.raises(ValueError):
        AgentFactory.create_agent(difficulty=Difficulty.EASY, strategy="SKYNET_V1")


def test_factory_fail_fast_on_bad_difficulty_string():
    """Vérifie que la factory plante si la string de difficulté est invalide."""
    with pytest.raises(ValueError):
        AgentFactory.create_agent(difficulty="EXTREME_GOD_MODE")