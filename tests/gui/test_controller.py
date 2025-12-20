import pytest
from unittest.mock import Mock, MagicMock
from mindbug_engine.core.models import Card
from mindbug_engine.core.consts import Phase
from mindbug_gui.controller import InputHandler


@pytest.fixture
def mock_game():
    game = MagicMock()
    # Configuration de base
    p1 = Mock()
    p1.hand = []
    p1.board = []
    game.state.player1 = p1
    game.state.active_player = p1  # C'est le tour de P1
    game.get_legal_moves.return_value = []
    game.state.phase = Phase.P1_MAIN
    return game


def test_click_card_in_hand_returns_play(mock_game):
    """Si je clique sur une carte jouable de ma main, ça renvoie PLAY."""
    card = Card("c1", "Unit", 5)
    mock_game.state.player1.hand = [card]
    mock_game.get_legal_moves.return_value = [("PLAY", 0)]

    # ACTION
    result = InputHandler.handle_card_click(mock_game, card)

    # ASSERTION
    assert result == ("PLAY", 0)


def test_click_card_not_in_hand_returns_none(mock_game):
    """Si je clique sur une carte inconnue, ça renvoie None."""
    card_hand = Card("c1", "Unit", 5)
    card_other = Card("c2", "Other", 5)
    mock_game.state.player1.hand = [card_hand]

    result = InputHandler.handle_card_click(mock_game, card_other)
    assert result is None


def test_click_during_ai_turn_returns_none(mock_game):
    """On ne peut pas jouer pendant le tour de l'IA."""
    card = Card("c1", "Unit", 5)

    result = InputHandler.handle_card_click(mock_game, card, is_ai_turn=True)
    assert result is None


def test_button_mapping():
    """Vérifie le mapping des boutons."""
    assert InputHandler.handle_button_click("CMD_PASS") == ("PASS", -1)
    assert InputHandler.handle_button_click("CMD_MINDBUG") == ("MINDBUG", -1)
    assert InputHandler.handle_button_click("UNKNOWN") is None