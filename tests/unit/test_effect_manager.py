from types import SimpleNamespace
from mindbug_engine.managers.effect_manager import EffectManager
from mindbug_engine.core.models import Card, CardEffect, Player
from mindbug_engine.core.consts import EffectType, Trigger


def make_game_state():
    game = SimpleNamespace()
    state = SimpleNamespace()
    p1 = Player("P1")
    p2 = Player("P2")
    state.player1 = p1
    state.player2 = p2
    state.deck = []
    state.player1.board = []
    state.player2.board = []
    state.player1.hand = []
    state.player2.hand = []
    state.player1.discard = []
    state.player2.discard = []
    state.active_player = p1
    game.state = state
    game.turn_manager = SimpleNamespace()
    game.combat_manager = SimpleNamespace()
    return game, p1, p2


def test_check_global_conditions_and_get_zone_content_and_compare():
    game, p1, p2 = make_game_state()
    em = EffectManager(game)

    # MY_TURN
    cond = {"context": "MY_TURN"}
    assert em._check_global_conditions(cond, p1, p2) is True

    # IS_ALONE
    p1.board = [Card("a", "A", 1)]
    cond = {"context": "IS_ALONE"}
    assert em._check_global_conditions(cond, p1, p2) is True
    p1.board.append(Card("b", "B", 1))
    assert em._check_global_conditions(cond, p1, p2) is False

    # FEWER_ALLIES
    p1.board = [Card("a", "A", 1)]
    p2.board = [Card("x", "X", 1), Card("y", "Y", 1)]
    cond = {"context": "FEWER_ALLIES"}
    assert em._check_global_conditions(cond, p1, p2) is True

    # _get_zone_content
    assert em._get_zone_content(p1, "HAND") == p1.hand
    assert em._get_zone_content(p1, "DISCARD") == p1.discard
    assert em._get_zone_content(p1, "BOARD") == p1.board

    # _compare
    assert em._compare(3, "EQ", 3)
    assert em._compare(5, "GTE", 4)
    assert em._compare(2, "LT", 3)


def test_filter_targets_by_power_and_player_included():
    game, p1, p2 = make_game_state()
    em = EffectManager(game)

    c1 = Card("c1", "C1", power=1)
    c2 = Card("c2", "C2", power=5)
    p1.board = [c1, c2]

    candidates = p1.board.copy()
    cond = {"stat": "POWER", "operator": "GTE", "value": 3}
    filtered = em._filter_targets(candidates, cond)
    assert filtered == [c2]

    # Player in candidates should be returned as-is
    filtered = em._filter_targets([p1], cond)
    assert filtered == [p1]


def test_apply_effect_dispatches_actions_and_apply_passive_effects(monkeypatch):
    game, p1, p2 = make_game_state()
    em = EffectManager(game)

    # Replace actions mapping with a fake that records calls
    recorded = {"calls": []}

    class FakeAction:
        def execute(self, target, params, source, owner, opp):
            recorded["calls"].append((target, params, source, owner, opp))

    em._actions = {EffectType.MODIFY_STAT: FakeAction()}

    # Create a card with a single effect that targets OWNER board
    eff = CardEffect(effect_type=EffectType.MODIFY_STAT, target={
                     "group": "OWNER", "zone": "BOARD"}, condition={}, params={})
    card = Card(id="s", name="S", power=1, effects=[eff])
    # put a target on owner's board
    p1.board = [Card("t", "T", 1)]

    em.apply_effect(card, p1, p2)
    # Should have dispatched for that one target
    assert len(recorded["calls"]) == 1

    # Test passive effects: create a passive card with same effect
    recorded["calls"].clear()
    passive_card = Card(id="p", name="P", power=0,
                        trigger=Trigger.PASSIVE, effects=[eff])
    p1.board = [passive_card, Card("t2", "T2", 1)]
    em.apply_passive_effects()
    # passive should cause a dispatch for the other card as owner target
    assert len(recorded["calls"]) >= 1
