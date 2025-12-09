import pytest
from mindbug_engine.models import Card
from mindbug_engine.rules import CombatUtils, Keyword

# --- FIXTURES ---

@pytest.fixture
def card_weak():
    return Card(id="t1", name="Weakling", power=2, keywords=[])

@pytest.fixture
def card_strong():
    return Card(id="t2", name="Strongman", power=8, keywords=[])

@pytest.fixture
def card_poison():
    return Card(id="t3", name="Snake", power=1, keywords=["POISON"])

@pytest.fixture
def card_tough():
    return Card(id="t4", name="Shield Bug", power=4, keywords=["TOUGH"])

@pytest.fixture
def card_sneaky():
    return Card(id="t5", name="Ninja", power=3, keywords=["SNEAKY"])

@pytest.fixture
def card_hunter():
    return Card(id="t6", name="Hunter Bee", power=5, keywords=["HUNTER"])

# --- TESTS : LOGIQUE DE COMBAT ---

def test_combat_power_win(card_strong, card_weak):
    att_dead, blk_dead = CombatUtils.simulate_combat(card_strong, card_weak)
    assert att_dead is False
    assert blk_dead is True

def test_combat_power_loss(card_weak, card_strong):
    att_dead, blk_dead = CombatUtils.simulate_combat(card_weak, card_strong)
    assert att_dead is True
    assert blk_dead is False

def test_combat_equality():
    c1 = Card(id="e1", name="Twin A", power=5)
    c2 = Card(id="e2", name="Twin B", power=5)
    att_dead, blk_dead = CombatUtils.simulate_combat(c1, c2)
    assert att_dead is True
    assert blk_dead is True

def test_combat_poison_vs_strong(card_poison, card_strong):
    att_dead, blk_dead = CombatUtils.simulate_combat(card_poison, card_strong)
    assert blk_dead is True
    assert att_dead is True

def test_combat_poison_vs_poison(card_poison):
    c2_poison = Card(id="p2", name="Other Snake", power=1, keywords=["POISON"])
    att_dead, blk_dead = CombatUtils.simulate_combat(card_poison, c2_poison)
    assert att_dead is True
    assert blk_dead is True

def test_combat_tough_mechanic(card_strong, card_tough):
    att_dead, blk_dead = CombatUtils.simulate_combat(card_strong, card_tough)
    assert blk_dead is True 
    assert att_dead is False

def test_combat_poison_vs_tough(card_poison, card_tough):
    att_dead, blk_dead = CombatUtils.simulate_combat(card_poison, card_tough)
    assert blk_dead is True 
    assert att_dead is True 

# --- TESTS : LÉGALITÉ DU BLOCAGE (CORRIGÉS) ---

def test_block_normal(card_strong, card_weak):
    # Correction : On passe les arguments sans les nommer
    assert CombatUtils.can_block(card_strong, card_weak) is True

def test_block_sneaky_illegal(card_sneaky, card_strong):
    assert CombatUtils.can_block(card_sneaky, card_strong) is False

def test_block_sneaky_legal(card_sneaky):
    other_sneaky = Card(id="s2", name="Spy", power=2, keywords=["SNEAKY"])
    assert CombatUtils.can_block(card_sneaky, other_sneaky) is True

def test_block_sneaky_defensive(card_strong, card_sneaky):
    assert CombatUtils.can_block(card_strong, card_sneaky) is True
