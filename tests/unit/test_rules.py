import pytest
from mindbug_engine.models import Card, CardAbility
from mindbug_engine.rules import CombatUtils

# --- FIXTURES LÉGÈRES (Pas d'Engine ici) ---
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
    # Poison tue Tough (2 blessures = mort)
    att_dead, blk_dead = CombatUtils.simulate_combat(card_poison, card_tough)
    assert att_dead and blk_dead

# --- TESTS LOGIQUE BLOCAGE ---

def test_can_block_sneaky(card_sneaky, card_strong):
    assert CombatUtils.can_block(card_sneaky, card_strong) is False
    other_sneaky = Card("s2", "Spy", 2, keywords=["SNEAKY"])
    assert CombatUtils.can_block(card_sneaky, other_sneaky) is True

def test_block_ban_conditions():
    """Teste la logique statique des conditions de blocage."""
    attacker_max = Card("a1", "Bear", 8, ability=CardAbility("BLOCK_BAN", "OPP", 0, "MAX_POWER", 6))
    blocker_weak = Card("b1", "Weak", 6)
    blocker_strong = Card("b2", "Strong", 7)
    
    assert CombatUtils.can_block(attacker_max, blocker_weak) is False
    assert CombatUtils.can_block(attacker_max, blocker_strong) is True

def test_can_block_block_ban_edge_cases():
    """Teste les interactions complexes de BLOCK_BAN."""
    # Cas 1 : Attaquant avec BLOCK_BAN (MAX_POWER 5) vs Bloqueur (5) -> Doit être FAUX (car <= 5)
    attacker = Card("a", "Ban", 8, ability=CardAbility("BLOCK_BAN", "OPP", 0, "MAX_POWER", 5))
    blocker_edge = Card("b", "Edge", 5)
    assert CombatUtils.can_block(attacker, blocker_edge) is False

    # Cas 2 : Attaquant avec BLOCK_BAN (MIN_POWER 5) vs Bloqueur (5) -> Doit être FAUX (car >= 5)
    attacker_min = Card("a2", "BanMin", 2, ability=CardAbility("BLOCK_BAN", "OPP", 0, "MIN_POWER", 5))
    assert CombatUtils.can_block(attacker_min, blocker_edge) is False

    # Cas 3 : Furtif vs Furtif (Prioritaire sur Block Ban ? Non, Block Ban est une restriction supplémentaire)
    # Si une carte est Furtive ET Block Ban, le bloqueur doit être Furtif ET respecter la condition.
    attacker_combo = Card("a3", "Combo", 5, keywords=["SNEAKY"], 
                          ability=CardAbility("BLOCK_BAN", "OPP", 0, "MAX_POWER", 3))
    
    blocker_sneaky_weak = Card("b2", "S_Weak", 3, keywords=["SNEAKY"]) # Furtif OK, mais Puissance <= 3 -> NON
    blocker_sneaky_strong = Card("b3", "S_Strong", 4, keywords=["SNEAKY"]) # Furtif OK, Puissance > 3 -> OUI
    
    assert CombatUtils.can_block(attacker_combo, blocker_sneaky_weak) is False
    assert CombatUtils.can_block(attacker_combo, blocker_sneaky_strong) is True
