from types import SimpleNamespace

from mindbug_engine.managers.combat_manager import CombatManager
from mindbug_engine.core.models import Card, Player
from mindbug_engine.core.consts import Keyword, Trigger


def make_game_and_players():
    game = SimpleNamespace()
    state = SimpleNamespace()
    p1 = Player("P1")
    p2 = Player("P2")
    state.player1 = p1
    state.player2 = p2
    state.player1 = p1
    state.player2 = p2
    state.active_player = p1
    state.phase = None
    state.active_request = None
    game.state = state
    return game, p1, p2


def test_direct_attack_with_zero_power_does_no_damage():
    game, p1, p2 = make_game_and_players()
    attacker = Card(id="a", name="A", power=0)
    p1.board.append(attacker)

    cm = CombatManager(game, effect_manager=None)

    att_dead, blk_dead = cm.resolve_fight(attacker, None)
    assert att_dead is False and blk_dead is False
    assert p2.hp == 3


def test_direct_attack_with_positive_power_reduces_hp_by_one():
    game, p1, p2 = make_game_and_players()
    attacker = Card(id="a", name="A", power=5)
    p1.board.append(attacker)

    cm = CombatManager(game, effect_manager=None)
    cm.state = game.state

    att_dead, blk_dead = cm.resolve_fight(attacker, None)
    assert p2.hp == 2


def test_combat_power_comparison_kills_weaker():
    game, p1, p2 = make_game_and_players()
    attacker = Card(id="atk", name="Atk", power=4)
    blocker = Card(id="blk", name="Blk", power=1)
    p1.board.append(attacker)
    p2.board.append(blocker)

    called = {"apply_called": False}

    class FakeEffectManager:
        def apply_effect(self, *a, **k):
            called["apply_called"] = True

    cm = CombatManager(game, effect_manager=FakeEffectManager())

    att_die, blk_die = cm.resolve_fight(attacker, blocker)
    assert att_die is False
    assert blk_die is True
    # blocker moved to discard
    assert blocker not in p2.board
    assert blocker in p2.discard


def test_poison_overrides_power_and_kills_even_if_weaker():
    game, p1, p2 = make_game_and_players()
    attacker = Card(id="a", name="A", power=1, keywords=[Keyword.POISON])
    blocker = Card(id="b", name="B", power=5)
    p1.board.append(attacker)
    p2.board.append(blocker)

    cm = CombatManager(game, effect_manager=None)
    att_die, blk_die = cm.resolve_fight(attacker, blocker)
    assert blk_die is True


def test_tough_prevents_death_once():
    game, p1, p2 = make_game_and_players()
    attacker = Card(id="a", name="A", power=5)
    blocker = Card(id="b", name="B", power=1, keywords=[Keyword.TOUGH])
    p1.board.append(attacker)
    p2.board.append(blocker)

    cm = CombatManager(game, effect_manager=None)
    att_die, blk_die = cm.resolve_fight(attacker, blocker)

    # blocker should survive due to TOUGH and be marked damaged
    assert blk_die is False
    assert blocker.is_damaged is True
    assert blocker in p2.board


def test_on_blocked_trigger_can_remove_blocker_and_end_combat():
    game, p1, p2 = make_game_and_players()
    attacker = Card(id="a", name="A", power=1, trigger=Trigger.ON_BLOCKED)
    blocker = Card(id="b", name="B", power=1)
    p1.board.append(attacker)
    p2.board.append(blocker)

    class FakeEffectManager:
        def apply_effect(self, attacker_card, owner, opp):
            # simulate effect that destroys the blocker (remove from opponent board)
            if blocker in opp.board:
                opp.board.remove(blocker)

    cm = CombatManager(game, effect_manager=FakeEffectManager())

    att_die, blk_die = cm.resolve_fight(attacker, blocker)
    # attacker lives, blocker considered removed
    assert att_die is False
    assert blk_die is True


def test_apply_lethal_damage_calls_on_death_trigger():
    game, p1, p2 = make_game_and_players()
    card = Card(id="d", name="D", power=1, trigger=Trigger.ON_DEATH)
    p1.board.append(card)

    calls = {"applied": False}

    class FakeEffectManager:
        def apply_effect(self, card_obj, owner, opp):
            calls["applied"] = True

    cm = CombatManager(game, effect_manager=FakeEffectManager())
    cm.apply_lethal_damage(card, p1)

    assert card not in p1.board
    assert card in p1.discard
    assert calls["applied"] is True
