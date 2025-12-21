from types import SimpleNamespace
import pytest

from mindbug_engine.managers.effects.actions.modify_stat import ModifyStatAction
from mindbug_engine.managers.effects.actions.play import PlayAction
from mindbug_engine.managers.effects.actions.steal import StealAction
from mindbug_engine.managers.effects.base import EffectAction
from mindbug_engine.core.models import Card


def test_effectaction_is_abstract():
    with pytest.raises(TypeError):
        EffectAction()


def test_modify_stat_hp_and_power_and_copy():
    action = ModifyStatAction()

    player = SimpleNamespace(name="P", hp=5)
    # ADD
    action.execute(
        player, {"stat": "HP", "operation": "ADD", "amount": 3}, None, None, None)
    assert player.hp == 8

    # SUB doesn't go negative
    action.execute(
        player, {"stat": "HP", "operation": "SUB", "amount": 10}, None, None, None)
    assert player.hp == 0

    # POWER on card
    card = Card("c", "C", power=2)
    action.execute(
        card, {"stat": "POWER", "operation": "ADD", "amount": 3}, None, None, None)
    assert card.power == 5

    # COPY from opponent HP -> set target hp
    owner = SimpleNamespace(name="O", hp=1)
    opponent = SimpleNamespace(name="X", hp=7)
    target = owner
    action.execute(target, {"stat": "HP", "operation": "COPY",
                   "source": "OPPONENT"}, None, owner, opponent)
    assert target.hp == 7


def test_modify_stat_ignores_non_applicable_target():
    action = ModifyStatAction()

    class NotApplicable:
        pass
    # Should not raise
    action.execute(NotApplicable(), {
                   "stat": "HP", "operation": "ADD", "amount": 1}, None, None, None)


def test_play_action_moves_from_discard_and_calls_put_on_board():
    # Setup fake game and effect_manager
    game = SimpleNamespace()
    effect_manager = SimpleNamespace()
    # _get_owner should return card_owner

    def _get_owner(target):
        return card_owner
    effect_manager._get_owner = _get_owner
    game.effect_manager = effect_manager

    called = {}

    def put_card_on_board(owner, target):
        called['owner'] = owner
        called['target'] = target
        # simulate placing on board
        owner.board.append(target)

    game.put_card_on_board = put_card_on_board

    action = PlayAction(game)

    card_owner = SimpleNamespace(name="Owner", board=[], discard=[], hand=[])
    target_card = Card("t", "T", power=1)
    card_owner.discard.append(target_card)

    # Execute
    action.execute(target_card, {}, None, card_owner, None)

    assert target_card in card_owner.board
    assert called['owner'] == card_owner
    assert called['target'] == target_card


def test_steal_action_from_board_and_hand(monkeypatch):
    # Prepare effect manager with turn_manager
    recorded = {"refilled": False}

    class FakeTurnManager:
        def refill_hand(self, player):
            recorded["refilled"] = True

    em = SimpleNamespace()
    em.turn_manager = FakeTurnManager()

    # _get_owner will determine victim based on target location
    def _get_owner(target):
        if target in victim.board or target in victim.hand:
            return victim
        return None

    em._get_owner = _get_owner

    action = StealAction(em)

    thief = SimpleNamespace(name="Thief", board=[], hand=[])
    victim = SimpleNamespace(name="Victim", board=[],
                             hand=[], discard=[])  # ensure attributes exist

    # Board steal
    card_b = Card("b", "B", 1)
    victim.board.append(card_b)
    action.execute(card_b, {}, None, thief, victim)
    assert card_b in thief.board
    assert card_b not in victim.board

    # Hand steal
    card_h = Card("h", "H", 1)
    victim.hand.append(card_h)
    action.execute(card_h, {}, None, thief, victim)
    assert card_h in thief.hand
    assert recorded["refilled"] is True


def test_play_action_when_target_not_in_discard_still_puts_on_board():
    game = SimpleNamespace()
    effect_manager = SimpleNamespace()

    def _get_owner(target):
        return card_owner

    effect_manager._get_owner = _get_owner
    game.effect_manager = effect_manager

    called = {}

    def put_card_on_board(owner, target):
        called['owner'] = owner
        called['target'] = target
        owner.board.append(target)

    game.put_card_on_board = put_card_on_board

    action = PlayAction(game)

    card_owner = SimpleNamespace(name="Owner2", board=[], discard=[], hand=[])
    target_card = Card("t2", "T2", power=1)
    # target not in discard

    action.execute(target_card, {}, None, card_owner, None)
    assert target_card in card_owner.board


def test_steal_action_no_victim_or_self(monkeypatch):
    # effect manager whose _get_owner returns None
    em = SimpleNamespace()
    em.turn_manager = SimpleNamespace()
    em._get_owner = lambda target: None

    action = StealAction(em)
    thief = SimpleNamespace(name="Thief2", board=[], hand=[])
    target = Card("z", "Z", 1)

    # No victim -> should be no-op
    action.execute(target, {}, None, thief, None)

    # Now emulate victim == thief
    em._get_owner = lambda t: thief
    # put target in thief.board
    thief.board.append(target)
    # Should be ignored because thief == victim
    action.execute(target, {}, None, thief, None)
    # target should remain in thief.board
    assert target in thief.board
