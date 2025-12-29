import pytest
from mindbug_engine.core.consts import Difficulty
from mindbug_ai.factory import AgentFactory
from mindbug_ai.interface import AgentInterface
from mindbug_ai.mcts.agent import MCTSAgent


def test_factory_creates_mcts_agent():
    """Vérifie que la factory retourne bien un agent MCTS."""
    # On demande explicitement MCTS (ou c'est le défaut si vous avez retiré le if)
    agent = AgentFactory.create_agent(
        difficulty=Difficulty.HARD, strategy="MCTS")

    assert isinstance(agent, MCTSAgent)
    assert isinstance(agent, AgentInterface)
    # Vérification que le temps de réflexion est adapté à la difficulté (ex: 3.0s pour Hard)
    assert agent.simulation_time >= 1.0


def test_factory_fail_fast_on_unknown_strategy():
    """Vérifie que la factory plante sur une stratégie inconnue."""
    with pytest.raises(ValueError):
        AgentFactory.create_agent(
            difficulty=Difficulty.EASY, strategy="SKYNET_V1")

def test_factory_creates_extreme_agent():
    """Vérifie que le mode EXTREME alloue bien plus de temps."""
    agent = AgentFactory.create_agent(
        difficulty=Difficulty.EXTREME, strategy="MCTS")
    
    assert isinstance(agent, MCTSAgent)
    # On vérifie qu'il a au moins 5 secondes de réflexion
    assert agent.simulation_time >= 5.0
