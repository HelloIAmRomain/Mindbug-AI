import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.models import Card, CardEffect
from mindbug_engine.core.consts import Phase, EffectType, Trigger


@pytest.fixture
def game():
    # Setup manuel d'un jeu vide
    g = MindbugGame(verbose=False)
    g.state.player1.hand = []
    g.state.player2.hand = []
    g.state.player1.board = []
    g.state.player2.board = []
    g.state.deck = []
    return g


def test_integration_on_play_trigger(game):
    p1 = game.state.player1
    p1.hp = 1

    # Carte Soin (V2)
    effect = CardEffect(EffectType.MODIFY_STAT,
                        target={"group": "OWNER"},
                        params={"stat": "HP", "amount": 3, "operation": "ADD"})

    healer = Card("h1", "Doc", 1, trigger=Trigger.ON_PLAY, effects=[effect])
    p1.hand.append(healer)

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # 1. P1 joue
    game.step("PLAY", 0)
    # 2. P2 passe (Refus Mindbug)
    game.step("PASS")

    # L'effet s'applique après la résolution
    assert p1.hp == 4
    assert healer in p1.board


def test_integration_mindbug_steals_effect(game):
    p1 = game.state.player1
    p2 = game.state.player2
    p2.hp = 1

    effect = CardEffect(EffectType.MODIFY_STAT,
                        target={"group": "OWNER"},
                        params={"stat": "HP", "amount": 3, "operation": "ADD"})

    healer = Card("h1", "Doc", 1, trigger=Trigger.ON_PLAY, effects=[effect])
    p1.hand.append(healer)

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    game.step("PLAY", 0)
    game.step("MINDBUG")  # P2 vole

    # La carte arrive chez P2, l'effet s'applique à P2 (OWNER)
    assert healer in p2.board
    assert p2.hp == 4
    assert p1.hp == 3  # P1 inchangé


def test_integration_on_death_trigger_with_selection(game):
    p1 = game.state.player1
    p2 = game.state.player2

    # Crapaud Bombe : Détruit une créature ennemie à sa mort
    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ENEMIES", "zone": "BOARD", "count": 1, "select": "CHOICE_USER"})

    bomb = Card("b1", "Bomb", 1, trigger=Trigger.ON_DEATH, effects=[effect])
    p1.board.append(bomb)

    killer = Card("k1", "Killer", 10)
    victim = Card("v1", "Victim", 2)
    p2.board = [killer, victim]

    # C'est le tour de P2
    game.state.active_player_idx = 1
    game.state.phase = Phase.P2_MAIN

    game.step("ATTACK", 0)  # Killer attaque
    game.step("BLOCK", 0)  # Bomb bloque

    # Bomb meurt
    assert bomb in p1.discard
    assert game.state.phase == Phase.RESOLUTION_CHOICE

    # Cible = Victim (sur le plateau de P2).
    # Relation = Adversaire.
    # Commande = SELECT_OPP_BOARD.
    game.step("SELECT_OPP_BOARD", 1)

    assert victim in p2.discard
    # On vérifie que le tour n'a pas changé incorrectement
    assert game.state.active_player == p2


def test_integration_dracompost_sequence(game):
    p1 = game.state.player1
    dead = Card("d1", "Dead", 5)
    p1.discard = [dead]

    # Dracompost : Joue une carte de sa défausse
    effect = CardEffect(EffectType.PLAY,
                        target={"group": "OWNER", "zone": "DISCARD", "count": 1, "select": "CHOICE_USER"})

    draco = Card("dc", "Draco", 3, trigger=Trigger.ON_PLAY, effects=[effect])
    p1.hand = [draco]

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    game.step("PLAY", 0)
    game.step("PASS")  # Mindbug refusé, Draco arrive en jeu, trigger ON_PLAY

    assert game.state.phase == Phase.RESOLUTION_CHOICE

    # P1 est actif. Il cible sa propre défausse.
    game.step("SELECT_DISCARD", 0)

    assert dead in p1.board
    assert len(p1.discard) == 0