import pytest
from mindbug_engine.core.models import Card, CardEffect
from mindbug_engine.utils.combat_utils import CombatUtils


# --- FIXTURES LÉGÈRES ---
@pytest.fixture
def card_weak(): return Card("t1", "Weak", 2)


@pytest.fixture
def card_strong(): return Card("t2", "Strong", 8)


@pytest.fixture
def card_poison(): return Card("t3", "Snake", 1, keywords=["POISON"])


@pytest.fixture
def card_tough(): return Card("t4", "Shield", 4, keywords=["TOUGH"])


@pytest.fixture
def card_sneaky(): return Card("t5", "Ninja", 3, keywords=["SNEAKY"])


# --- TESTS LOGIQUE COMBAT ---

def test_combat_power_win(card_strong, card_weak):
    att_dead, blk_dead = CombatUtils.simulate_combat(card_strong, card_weak)
    assert not att_dead and blk_dead


def test_combat_poison_vs_tough(card_poison, card_tough):
    # Note: simulate_combat ne gère pas Poison/Tough (c'est le CombatManager),
    # mais il gère la comparaison de puissance brute.
    # Ici Poison(1) perd contre Tough(4) en puissance pure.
    att_dead, blk_dead = CombatUtils.simulate_combat(card_poison, card_tough)
    assert att_dead and not blk_dead


# --- TESTS LOGIQUE BLOCAGE ---

def test_can_block_sneaky(card_sneaky, card_strong):
    assert CombatUtils.can_block(card_sneaky, card_strong) is False
    other_sneaky = Card("s2", "Spy", 2, keywords=["SNEAKY"])
    assert CombatUtils.can_block(card_sneaky, other_sneaky) is True


def test_block_ban_conditions():
    """Teste la logique statique des conditions de blocage (V2)."""
    # Effet : BAN BLOCK si Power <= 6 (Oursabeille)
    ban_effect = CardEffect(
        "BAN",
        target={"group": "ENEMIES"},
        condition={"stat": "POWER", "operator": "LTE", "value": 6},
        params={"action": "BLOCK"}
    )
    attacker_max = Card("a1", "Bear", 8, effects=[ban_effect])

    blocker_weak = Card("b1", "Weak", 6)  # <= 6 -> Interdit
    blocker_strong = Card("b2", "Strong", 7)  # > 6 -> Autorisé

    assert CombatUtils.can_block(attacker_max, blocker_weak) is False
    assert CombatUtils.can_block(attacker_max, blocker_strong) is True


def test_can_block_block_ban_edge_cases():
    """Teste les interactions complexes de BAN."""
    # Cas 1 : Interdit si Power <= 5
    ban_eff = CardEffect(
        "BAN", target={"group": "ENEMIES"},
        condition={"stat": "POWER", "operator": "LTE", "value": 5},
        params={"action": "BLOCK"}
    )
    attacker = Card("a", "Ban", 8, effects=[ban_eff])
    blocker_edge = Card("b", "Edge", 5)  # 5 <= 5 -> Interdit

    assert CombatUtils.can_block(attacker, blocker_edge) is False

    # Cas 2 : Interdit si Power >= 5
    ban_min = CardEffect(
        "BAN", target={"group": "ENEMIES"},
        condition={"stat": "POWER", "operator": "GTE", "value": 5},
        params={"action": "BLOCK"}
    )
    attacker_min = Card("a2", "BanMin", 2, effects=[ban_min])

    assert CombatUtils.can_block(attacker_min, blocker_edge) is False  # 5 >= 5 -> Interdit

    # Cas 3 : Sneaky ET Ban
    attacker_combo = Card("a3", "Combo", 5, keywords=["SNEAKY"], effects=[
        CardEffect("BAN", target={"group": "ENEMIES"},
                   condition={"stat": "POWER", "operator": "LTE", "value": 3},
                   params={"action": "BLOCK"})
    ])

    # Furtif (OK) mais Power 3 (<=3 -> BAN)
    blocker_sneaky_weak = Card("b2", "S_Weak", 3, keywords=["SNEAKY"])
    # Furtif (OK) et Power 4 (>3 -> OK)
    blocker_sneaky_strong = Card("b3", "S_Strong", 4, keywords=["SNEAKY"])

    assert CombatUtils.can_block(attacker_combo, blocker_sneaky_weak) is False
    assert CombatUtils.can_block(attacker_combo, blocker_sneaky_strong) is True