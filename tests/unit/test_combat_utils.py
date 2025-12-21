from mindbug_engine.utils.combat_utils import CombatUtils
from mindbug_engine.core.models import Card, CardEffect
from mindbug_engine.core.consts import Keyword


def test_simulate_combat_basic_outcomes():
    a = Card("a", "A", power=3)
    b = Card("b", "B", power=1)
    assert CombatUtils.simulate_combat(a, b) == (False, True)

    # reverse
    assert CombatUtils.simulate_combat(b, a) == (True, False)

    # tie
    c1 = Card("c1", "C1", power=2)
    c2 = Card("c2", "C2", power=2)
    assert CombatUtils.simulate_combat(c1, c2) == (True, True)

    # overrides
    assert CombatUtils.simulate_combat(
        c1, c2, override_att_power=5) == (False, True)
    assert CombatUtils.simulate_combat(
        c1, c2, override_blk_power=6) == (True, False)


def test_can_block_sneaky_keyword():
    attacker = Card("s", "Sneak", power=1)
    blocker = Card("n", "Normal", power=1)

    # attacker sneaky as string in keywords
    attacker.keywords = [Keyword.SNEAKY.value]
    blocker.keywords = []
    assert CombatUtils.can_block(attacker, blocker) is False

    # blocker with sneaky can block
    blocker.keywords = [Keyword.SNEAKY.value]
    assert CombatUtils.can_block(attacker, blocker) is True


def test_can_block_ban_action_with_conditions():
    attacker = Card("atk", "ATK", power=1)
    blocker = Card("blk", "BLK", power=3)

    # effect banning blockers with POWER LTE 2
    eff = CardEffect(effect_type="BAN", params={"action": "BLOCK"}, condition={
                     "stat": "POWER", "operator": "LTE", "value": 2})
    attacker.effects = [eff]

    # blocker power 3 -> not banned
    assert CombatUtils.can_block(attacker, blocker) is True

    # lower power blocker
    weak = Card("w", "Weak", power=2)
    assert CombatUtils.can_block(attacker, weak) is False


def test_check_ban_condition_various_ops():
    card = Card("x", "X", power=5)
    cond = {"stat": "POWER", "operator": "GT", "value": 3}
    assert CombatUtils._check_ban_condition(card, cond) is True

    cond = {"stat": "POWER", "operator": "LT", "value": 10}
    assert CombatUtils._check_ban_condition(card, cond) is True

    cond = {"stat": "POWER", "operator": "EQ", "value": 5}
    assert CombatUtils._check_ban_condition(card, cond) is True

    cond = {"stat": "POWER", "operator": "GTE", "value": 6}
    assert CombatUtils._check_ban_condition(card, cond) is False
