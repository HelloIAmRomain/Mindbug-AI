import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.models import Card
from mindbug_engine.core.consts import Phase


@pytest.fixture
def game():
    # --- FIX CRUCIAL : start_game() ---
    g = MindbugGame(verbose=False)
    g.start_game()
    return g


def test_initial_setup(game):
    """Vérifie que la partie commence proprement."""
    assert game.state.turn_count == 1
    assert game.state.phase == Phase.P1_MAIN
    assert game.state.active_player.name == "P1"
    # Les joueurs doivent avoir 5 cartes (setup par défaut)
    assert len(game.state.player1.hand) == 5
    assert len(game.state.player2.hand) == 5


def test_flow_play_card_transition(game):
    """P1 joue -> On doit passer en phase de décision Mindbug pour P2."""
    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # Action : P1 joue sa première carte
    game.step("PLAY", 0)

    # Vérifications
    assert game.state.phase == Phase.MINDBUG_DECISION
    assert game.state.active_player.name == "P2"
    assert game.state.pending_card is not None


def test_flow_mindbug_refusal(game):
    """
    Scénario : P1 joue -> P2 refuse -> Carte résolue chez P1 -> Tour P2.
    """
    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN
    game.state.player2.mindbugs = 2

    # Création carte neutre
    vanilla_card = Card(id="test_soldat", name="Soldat Test", power=5, keywords=[], trigger=None)

    # Injection forcée
    game.state.player1.hand[0] = vanilla_card

    # 1. P1 joue
    game.step("PLAY", 0)

    # 2. P2 refuse
    game.step("PASS")

    # VÉRIFICATIONS
    assert vanilla_card in game.state.player1.board
    assert game.state.active_player.name == "P2"
    assert game.state.phase == Phase.P2_MAIN
    assert game.state.player2.mindbugs == 2


def test_flow_mindbug_accepted(game):
    """
    Scénario Vol (Règle Replay).
    """
    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # Carte neutre
    neutral_card = Card(id="n", name="NeutralUnit", power=5, keywords=[], trigger=None)
    game.state.player1.hand[0] = neutral_card

    # 1. P1 joue
    game.step("PLAY", 0)

    # 2. P2 Vole
    game.step("MINDBUG")

    # Vérifications
    assert neutral_card in game.state.player2.board
    assert game.state.player2.mindbugs == 1

    # REPLAY : C'est encore à P1 de jouer
    assert game.state.active_player.name == "P1"
    assert game.state.phase == Phase.P1_MAIN


def test_win_condition_detection(game):
    """Vérifie que le jeu s'arrête si HP <= 0."""
    game.state.player1.hp = 1

    killer = Card(id="k", name="Killer", power=5, keywords=[], trigger=None)
    game.state.player2.board = [killer]
    game.state.player1.board = []  # Pas de défense

    game.state.active_player_idx = 1  # P2 attaque
    game.state.phase = Phase.P2_MAIN

    game.step("ATTACK", 0)
    game.step("NO_BLOCK")  # Pas de défenseur, dégâts directs

    assert game.state.player1.hp == 0
    assert game.state.winner == game.state.player2