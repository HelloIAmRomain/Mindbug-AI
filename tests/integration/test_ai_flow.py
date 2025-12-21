import pytest
from mindbug_engine.core.consts import Phase, Difficulty
from mindbug_ai.factory import AgentFactory


def test_mcts_integration_decision_does_not_crash(game):
    """Vérifie que l'agent MCTS peut prendre une décision sans erreur."""
    # On met un temps très court pour le test (0.1s)
    agent = AgentFactory.create_agent(
        difficulty=Difficulty.EASY, strategy="MCTS")
    agent.simulation_time = 0.1

    # Setup : C'est à l'IA (P2) de jouer
    game.state.active_player_idx = 1
    game.state.phase = Phase.P2_MAIN

    # On s'assure qu'il y a des coups légaux
    assert len(game.get_legal_moves()) > 0

    action = agent.get_action(game)

    assert action is not None
    assert action in game.get_legal_moves()


def test_mcts_integration_mindbug_phase(game):
    """Vérifie que l'IA sait répondre à une demande de Mindbug."""
    agent = AgentFactory.create_agent(
        difficulty=Difficulty.MEDIUM, strategy="MCTS")
    agent.simulation_time = 0.1

    game.state.phase = Phase.MINDBUG_DECISION
    game.state.active_player_idx = 1

    # On simule une carte jouée par P1
    from mindbug_engine.core.models import Card
    game.state.pending_card = Card("test", "TestUnit", 5)

    action = agent.get_action(game)
    assert action[0] in ["MINDBUG", "PASS"]
