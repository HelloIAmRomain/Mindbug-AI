import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.models import Card, SelectionRequest
from mindbug_engine.core.consts import Phase


@pytest.fixture
def game():
    g = MindbugGame(verbose=False)
    # Setup basique pour éviter les erreurs d'index
    g.state.player1.hand = [Card("c1", "C1", 1)]
    g.state.player1.board = [Card("b1", "B1", 1)]
    g.state.player2.hand = []
    g.state.player2.board = [Card("b2", "B2", 1)]
    return g


def test_legal_moves_main_phase(game):
    """Vérifie que PLAY et ATTACK sont dispos en Main Phase."""
    game.state.phase = Phase.P1_MAIN
    game.state.active_player_idx = 0

    moves = game.get_legal_moves()

    assert ("PLAY", 0) in moves
    assert ("ATTACK", 0) in moves


def test_legal_moves_selection(game):
    """Vérifie la génération des coups de sélection."""
    game.state.phase = Phase.RESOLUTION_CHOICE
    game.state.active_player_idx = 0  # P1 Actif

    # On simule une demande : P1 doit choisir une carte sur le plateau adverse (P2)
    req = SelectionRequest(
        candidates=[game.state.player2.board[0]],
        count=1,
        reason="Test",
        selector=game.state.player1,  # V3 utilise 'selector'
        callback=lambda x: None
    )
    game.state.active_request = req

    moves = game.get_legal_moves()

    # Du point de vue de P1, le plateau de P2 est OPP_BOARD
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