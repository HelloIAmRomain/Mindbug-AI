from types import SimpleNamespace
import pickle

from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.models import Card
from mindbug_engine.core.consts import Phase, Trigger, EffectType


def make_config():
    cfg = SimpleNamespace()
    cfg.active_sets = ["FIRST_CONTACT"]
    cfg.debug_mode = False
    cfg.ai_difficulty = SimpleNamespace(value="MEDIUM")
    return cfg


def make_small_deck():
    # return a small deck list
    return [Card(f"d{i}", f"D{i}", power=1) for i in range(30)]


def test_start_game_sets_hands_and_players(monkeypatch):
    # patch DeckFactory.create_deck to return a small deck
    monkeypatch.setattr("mindbug_engine.infrastructure.deck_factory.DeckFactory.create_deck",
                        lambda self, **k: (make_small_deck(), [], ["FIRST_CONTACT"]))

    g = MindbugGame(make_config())
    g.start_game()

    # each player should have up to 5 cards
    assert len(g.state.player1.hand) == 5
    assert len(g.state.player2.hand) == 5
    assert g.state.turn_count == 1
    assert g.state.phase == Phase.P1_MAIN


def test_get_legal_moves_mindbug_and_frenzy(monkeypatch):
    monkeypatch.setattr("mindbug_engine.infrastructure.deck_factory.DeckFactory.create_deck",
                        lambda self, **k: (make_small_deck(), [], []))
    g = MindbugGame(make_config())

    # Setup for MINDBUG_DECISION
    g.state.phase = Phase.MINDBUG_DECISION
    g.state.active_player.mindbugs = 1
    moves = g.get_legal_moves()
    assert ("PASS", -1) in moves
    assert ("MINDBUG", -1) in moves

    # Setup frenzy candidate behavior
    card = Card("f", "F", power=2)
    g.state.active_player.board = [card]
    g.state.frenzy_candidate = card
    moves = g.get_legal_moves()
    assert moves == [("ATTACK", 0)]


def test_execute_mindbug_replay_calls_turn_manager(monkeypatch):
    monkeypatch.setattr("mindbug_engine.infrastructure.deck_factory.DeckFactory.create_deck",
                        lambda self, **k: (make_small_deck(), [], []))
    g = MindbugGame(make_config())

    calls = {"switched": False, "refilled": False}

    def fake_switch():
        calls["switched"] = True

    def fake_refill(p):
        calls["refilled"] = True

    g.turn_manager.switch_active_player = fake_switch
    g.turn_manager.refill_hand = fake_refill

    g.execute_mindbug_replay()
    assert calls["switched"] is True
    assert calls["refilled"] is True


def test_resolve_selection_effect_triggers_replay_and_pending_attacker(monkeypatch):
    monkeypatch.setattr("mindbug_engine.infrastructure.deck_factory.DeckFactory.create_deck",
                        lambda self, **k: (make_small_deck(), [], []))
    g = MindbugGame(make_config())

    # Case 1: mindbug_replay_pending
    g.state.phase = Phase.RESOLUTION_CHOICE
    g.state.mindbug_replay_pending = True
    g.query_manager.resolve_selection = lambda sel: True

    calls = {"replay": False}
    g.execute_mindbug_replay = lambda: calls.__setitem__("replay", True)

    g.resolve_selection_effect(object())
    assert calls["replay"] is True

    # Case 2: pending_attacker -> should move to BLOCK_DECISION and switch player
    g.state.phase = Phase.RESOLUTION_CHOICE
    g.state.mindbug_replay_pending = False
    g.state.pending_attacker = Card("a", "A", 1)
    g.query_manager.resolve_selection = lambda sel: True

    switched = {"v": False}
    g.turn_manager.switch_active_player = lambda: switched.__setitem__(
        "v", True)

    g.resolve_selection_effect(object())
    assert g.state.phase == Phase.BLOCK_DECISION
    assert switched["v"] is True


def test_put_card_on_board_triggers_or_suppresses_apply_effect(monkeypatch):
    monkeypatch.setattr("mindbug_engine.infrastructure.deck_factory.DeckFactory.create_deck",
                        lambda self, **k: (make_small_deck(), [], []))
    g = MindbugGame(make_config())

    p1 = g.state.player1
    p2 = g.state.player2

    # case: opponent has passive BAN TRIGGER_ON_PLAY -> silenced
    passive = Card("s", "S", 1)
    passive.trigger = Trigger.PASSIVE

    # build a proper effect-like object
    class Eff:
        def __init__(self):
            self.type = EffectType.BAN
            self.params = {"action": "TRIGGER_ON_PLAY"}
    passive.effects = [Eff()]

    p2.board = [passive]
    card = Card("c", "C", 1)

    called = {"applied": False}
    g.effect_manager.apply_effect = lambda card_obj, owner, opp: called.__setitem__(
        "applied", True)

    # putting card on p1 board should be silenced -> no apply_effect call
    g.put_card_on_board(p1, card)
    assert called["applied"] is False

    # Now ensure ON_PLAY triggers apply_effect when not silenced
    p2.board = []
    card.trigger = Trigger.ON_PLAY
    g.put_card_on_board(p1, card)
    assert called["applied"] is True


def test_clone_creates_independent_state(monkeypatch):
    monkeypatch.setattr("mindbug_engine.infrastructure.deck_factory.DeckFactory.create_deck",
                        lambda self, **k: (make_small_deck(), [], []))
    g = MindbugGame(make_config())
    g.state.player1.hp = 9

    clone = g.clone()
    # mutate clone state
    clone.state.player1.hp = 1
    # original unchanged
    assert g.state.player1.hp == 9
