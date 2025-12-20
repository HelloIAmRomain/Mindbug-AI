import pytest
from mindbug_engine.core.models import Card
from mindbug_engine.core.consts import Phase


def test_initial_setup(game):
    # start_game() donne 5 cartes, mais notre fixture 'game' vide le deck ensuite.
    # Les mains, elles, sont déjà remplies.
    assert game.state.turn_count == 1
    assert game.state.phase == Phase.P1_MAIN
    assert len(game.state.player1.hand) == 5


def test_flow_play_card_transition(game):
    """P1 joue -> On doit passer en phase de décision Mindbug pour P2."""
    # ACTIVATION MINDBUG REQUISE
    game.state.player2.mindbugs = 2

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    game.step("PLAY", 0)

    assert game.state.phase == Phase.MINDBUG_DECISION
    assert game.state.active_player.name == "P2"
    assert game.state.pending_card is not None


def test_flow_mindbug_refusal(game):
    # ACTIVATION MINDBUG REQUISE
    game.state.player2.mindbugs = 2

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    vanilla_card = Card(id="test_soldat", name="Soldat Test", power=5)
    game.state.player1.hand[0] = vanilla_card

    # 1. P1 joue
    game.step("PLAY", 0)
    # 2. P2 refuse
    game.step("PASS")

    assert vanilla_card in game.state.player1.board
    assert game.state.active_player.name == "P2"


def test_flow_mindbug_accepted(game):
    # ACTIVATION MINDBUG REQUISE
    game.state.player2.mindbugs = 2

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    neutral_card = Card(id="n", name="NeutralUnit", power=5)
    game.state.player1.hand[0] = neutral_card

    # 1. P1 joue
    game.step("PLAY", 0)
    # 2. P2 Vole
    game.step("MINDBUG")

    assert neutral_card in game.state.player2.board
    assert game.state.player2.mindbugs == 1

    # Replay P1
    assert game.state.active_player.name == "P1"


def test_win_condition_detection(game):
    game.state.player1.hp = 1

    killer = Card(id="k", name="Killer", power=5)
    game.state.player2.board = [killer]
    game.state.player1.board = []

    game.state.active_player_idx = 1
    game.state.phase = Phase.P2_MAIN

    game.step("ATTACK", 0)
    game.step("NO_BLOCK")

    assert game.state.player1.hp == 0
    assert game.state.winner == game.state.player2