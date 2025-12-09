import pytest
from mindbug_engine.models import Card, CardAbility, Player
from mindbug_engine.effects import EffectManager
from mindbug_engine.engine import MindbugGame

# --- FIXTURES ---

@pytest.fixture
def game():
    return MindbugGame() # On a besoin d'une instance basique

@pytest.fixture
def p1(game):
    return game.player1

@pytest.fixture
def p2(game):
    return game.player2

@pytest.fixture
def card_dummy():
    return Card("d1", "Dummy", 1)

# --- TESTS ---

def test_effect_heal(p1, card_dummy):
    """Test le code HEAL avec une valeur précise."""
    # Setup : P1 a 1 PV
    p1.hp = 1
    
    # Action : On applique une carte qui soigne de 2
    card_heal = Card("h1", "Axolotl", 4, ability=CardAbility(code="HEAL", target="SELF", value=2))
    EffectManager.apply_effect(None, card_heal, owner=p1, opponent=None)
    
    # Vérification : 1 + 2 = 3
    assert p1.hp == 3

def test_effect_heal_overflow(p1, card_dummy):
    """Test que le soin peut dépasser les PV de départ (pas de max)."""
    # Setup : P1 a déjà 3 PV (full)
    p1.hp = 3
    
    # Action : Soin de 2
    card_heal = Card("h1", "Axolotl", 4, ability=CardAbility(code="HEAL", target="SELF", value=2))
    EffectManager.apply_effect(None, card_heal, owner=p1, opponent=None)
    
    # Vérification : 3 + 2 = 5
    assert p1.hp == 5

def test_effect_damage(p2, card_dummy):
    """Test le code DAMAGE"""
    p2.hp = 3
    card_dmg = Card("dmg1", "Bee", 1, ability=CardAbility(code="DAMAGE", target="OPP", value=1))
    
    EffectManager.apply_effect(None, card_dmg, owner=None, opponent=p2)
    
    assert p2.hp == 2

def test_effect_steal_creature(game, p1, p2, card_dummy):
    """Test le code STEAL_CREATURE"""
    # Setup : P2 a une créature, P1 n'en a pas
    target_card = Card("t1", "Target", 5)
    p2.board = [target_card]
    p1.board = []
    
    card_steal = Card("s1", "Thief", 1, ability=CardAbility(code="STEAL_CREATURE", target="OPP", value=1))
    
    # Action
    EffectManager.apply_effect(game, card_steal, owner=p1, opponent=p2)
    
    # Assert
    assert len(p2.board) == 0
    assert len(p1.board) == 1
    assert p1.board[0] == target_card

def test_effect_conditional_destroy(game, p1, p2):
    """Test le code DESTROY_CREATURE avec condition POWER_GE_6"""
    # Setup : P2 a un Rat (2) et un Tigre (8)
    rat = Card("r1", "Rat", 2)
    tiger = Card("t1", "Tiger", 8)
    p2.board = [rat, tiger]
    
    # Carte qui détruit les monstres >= 6
    card_dest = Card("k1", "Killer", 1, ability=CardAbility(code="DESTROY_CREATURE", target="OPP", condition="POWER_GE_6", value=1))
    
    # Action
    EffectManager.apply_effect(game, card_dest, owner=p1, opponent=p2)
    
    # Assert : Le Tigre doit être détruit (défausse), le Rat doit rester
    assert tiger in p2.discard
    assert tiger not in p2.board
    assert rat in p2.board

def test_effect_reclaim_discard(p1):
    """Test le code RECLAIM_DISCARD"""
    # Setup : Une carte dans la défausse
    lost_card = Card("l1", "Lost", 5)
    p1.discard = [lost_card]
    p1.hand = []
    
    card_reclaim = Card("r1", "Necro", 1, ability=CardAbility(code="RECLAIM_DISCARD", target="SELF", value=1))
    
    EffectManager.apply_effect(None, card_reclaim, owner=p1, opponent=None)
    
    assert len(p1.discard) == 0
    assert len(p1.hand) == 1
    assert p1.hand[0] == lost_card
