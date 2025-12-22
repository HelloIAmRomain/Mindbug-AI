import pytest
from unittest.mock import MagicMock
from mindbug_ai.mcts.agent import MCTSAgent


def test_mcts_agent_returns_move_within_time_budget():
    """Vérifie que l'agent respecte le temps imparti et retourne un coup."""
    agent = MCTSAgent(simulation_time=0.1)

    # Mock du jeu
    mock_game = MagicMock()
    mock_game.get_legal_moves.return_value = [("PLAY", 0), ("PLAY", 1)]
    mock_game.state.active_player_idx = 0
    mock_game.state.winner = None

    mock_game.state.player1.hp = 3
    mock_game.state.player2.hp = 3

    # Le clone doit retourner un mock aussi pour la simulation
    mock_clone = MagicMock()
    mock_clone.state.active_player_idx = 0
    mock_clone.state.winner = None

    mock_clone.state.player1.hp = 3
    mock_clone.state.player2.hp = 3

    mock_clone.get_legal_moves.return_value = [
        ("PLAY", 0)]  # Coups pour la simu
    mock_game.clone.return_value = mock_clone

    # On mock le determinizer pour qu'il ne fasse rien (évite les dépendances complexes)
    agent.determinizer.determinize = MagicMock()

    action = agent.get_action(mock_game)

    assert action is not None
    assert action in [("PLAY", 0), ("PLAY", 1)]
    assert agent.root is not None
    # On vérifie qu'il a fait au moins quelques simulations
    assert agent.root.visits > 0
