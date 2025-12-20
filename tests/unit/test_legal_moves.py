import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.models import Card, SelectionRequest
from mindbug_engine.core.consts import Phase


def test_legal_moves_main_phase(game):
    """Vérifie que PLAY et ATTACK sont dispos en Main Phase."""
    game.state.phase = Phase.P1_MAIN
    game.state.active_player_idx = 0

    from mindbug_engine.core.models import Card
    game.state.player1.board = [Card("b1", "Beast", 5)]

    moves = game.get_legal_moves()

    assert ("PLAY", 0) in moves
    assert ("ATTACK", 0) in moves


def test_legal_moves_selection(game):
    # Setup du plateau pour le test
    from mindbug_engine.core.models import Card
    target = Card("target", "Target", 5)
    game.state.player2.board = [target]

    game.state.phase = Phase.RESOLUTION_CHOICE
    game.state.active_player_idx = 0

    req = SelectionRequest(
        candidates=[target],  # Utilise la carte créée
        count=1,
        reason="Test",
        selector=game.state.player1,
        callback=lambda x: None
    )
    game.state.active_request = req

    moves = game.get_legal_moves()
    assert ("SELECT_OPP_BOARD", 0) in moves


def test_legal_moves_frenzy_constraint(game):
    """Vérifie que la Fureur force l'attaque."""
    p1 = game.state.player1
    frenzy_card = Card("f", "FrenzyCard", 6)
    other_card = Card("o", "Other", 4)
    p1.board = [frenzy_card, other_card]

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # La carte est marquée comme devant attaquer
    game.state.frenzy_candidate = frenzy_card

    moves = game.get_legal_moves()

    # Seule l'attaque avec la carte en fureur est légale
    assert len(moves) == 1
    assert moves[0] == ("ATTACK", 0)