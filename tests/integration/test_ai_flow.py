import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.consts import Phase, Difficulty
from mindbug_ai.factory import AgentFactory


def test_ai_integration_decision_does_not_mutate_game(game):
    """Vérifie que la réflexion de l'IA ne modifie pas le vrai jeu."""
    agent = AgentFactory.create_agent(difficulty=Difficulty.HARD)

    # Setup : C'est à l'IA (P2) de jouer
    game.state.active_player_idx = 1
    game.state.phase = Phase.P2_MAIN

    hp_before = game.state.player2.hp

    action = agent.get_action(game)

    assert action is not None
    # Le vrai jeu ne doit pas avoir bougé
    assert game.state.player2.hp == hp_before


def test_ai_integration_mindbug_phase(game):
    """Vérifie que l'IA sait répondre à une demande de Mindbug."""
    agent = AgentFactory.create_agent(difficulty=Difficulty.MEDIUM)

    game.state.phase = Phase.MINDBUG_DECISION
    game.state.active_player_idx = 1

    from mindbug_engine.core.models import Card
    game.state.pending_card = Card("test", "TestUnit", 5)

    action = agent.get_action(game)
    assert action[0] in ["MINDBUG", "PASS"]


def test_ai_integration_no_crash_on_complex_simulation(game):
    """Vérifie que l'IA gère la simulation même avec des effets complexes."""
    agent = AgentFactory.create_agent(difficulty=Difficulty.EASY)

    game.state.active_player_idx = 1
    game.state.phase = Phase.P2_MAIN

    action = agent.get_action(game)
    assert action is not None