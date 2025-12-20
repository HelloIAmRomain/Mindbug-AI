import pytest
from mindbug_engine.core.models import Card, CardEffect
from mindbug_engine.core.consts import Phase, Trigger, EffectType


def test_integration_on_play_trigger(game):
    p1 = game.state.player1
    p1.hp = 1

    # Nettoyage pour garantir l'index 0
    p1.hand = []

    # Pour tester le PASS manuel, il faut que P2 ait un mindbug
    game.state.player2.mindbugs = 1

    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OWNER"},
                        params={"stat": "HP", "amount": 3, "operation": "ADD"})
    healer = Card("h1", "Doc", 1, trigger=Trigger.ON_PLAY, effects=[effect])

    p1.hand.append(healer)  # Index 0

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # CORRECTION : Index 0 au lieu de -1
    game.step("PLAY", 0)
    game.step("PASS")  # P2 refuse

    assert p1.hp == 4
    assert healer in p1.board


def test_integration_mindbug_steals_effect(game):
    p1 = game.state.player1
    p2 = game.state.player2
    p2.hp = 1

    # Nettoyage
    p1.hand = []

    # Activation Mindbug
    p2.mindbugs = 1

    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OWNER"},
                        params={"stat": "HP", "amount": 3, "operation": "ADD"})
    healer = Card("h1", "Doc", 1, trigger=Trigger.ON_PLAY, effects=[effect])

    p1.hand.append(healer)  # Index 0

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # CORRECTION : Index 0 au lieu de -1
    game.step("PLAY", 0)
    game.step("MINDBUG")

    assert healer in p2.board
    assert p2.hp == 4
    assert p1.hp == 3


def test_integration_on_death_trigger_with_selection(game):
    p1 = game.state.player1
    p2 = game.state.player2
    # ... (copier le reste depuis votre fichier original) ...
    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ENEMIES", "zone": "BOARD", "count": 1, "select": "CHOICE_USER"})
    bomb = Card("b1", "Bomb", 1, trigger=Trigger.ON_DEATH, effects=[effect])
    p1.board.append(bomb)
    killer = Card("k1", "Killer", 10)
    victim = Card("v1", "Victim", 2)
    p2.board = [killer, victim]
    game.state.active_player_idx = 1
    game.state.phase = Phase.P2_MAIN
    game.step("ATTACK", 0)
    game.step("BLOCK", 0)
    assert bomb in p1.discard
    assert game.state.phase == Phase.RESOLUTION_CHOICE
    game.step("SELECT_OPP_BOARD", 1)
    assert victim in p2.discard
    assert game.state.active_player == p2


def test_integration_dracompost_sequence(game):
    p1 = game.state.player1
    dead = Card("d1", "Dead", 5)
    p1.discard = [dead]
    effect = CardEffect(EffectType.PLAY,
                        target={"group": "OWNER", "zone": "DISCARD", "count": 1, "select": "CHOICE_USER"})
    draco = Card("dc", "Draco", 3, trigger=Trigger.ON_PLAY, effects=[effect])
    p1.hand = [draco]
    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN
    game.step("PLAY", 0)
    game.step("PASS")
    assert game.state.phase == Phase.RESOLUTION_CHOICE
    game.step("SELECT_DISCARD", 0)
    assert dead in p1.board
    assert len(p1.discard) == 0