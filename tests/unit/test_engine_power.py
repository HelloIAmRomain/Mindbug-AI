# tests/unit/test_engine_power.py
import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card, CardAbility
from mindbug_engine.rules import Phase

@pytest.fixture
def game():
    return MindbugGame()

def test_power_boost_my_turn(game):
    """Test Goblin-Garou (Boost si mon tour)."""
    # Setup : P1 joue Goblin
    goblin = Card("g", "Gob", 2, trigger="PASSIVE", 
                  ability=CardAbility("BOOST_IF_MY_TURN", "SELF", 6))
    game.player1.board = [goblin]
    
    # Cas 1 : Tour de P1 (Attaque)
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    assert game.calculate_real_power(goblin) == 8 # (2 + 6)
    
    # Cas 2 : Tour de P2 (Défense)
    # Attention : active_player est P2, phase MAIN
    game.active_player_idx = 1 
    game.phase = Phase.P2_MAIN
    assert game.calculate_real_power(goblin) == 2  # (Base)

def test_power_debuff_enemies(game):
    """Test Oursin (Debuff ennemis PERMANENT)."""
    # P1 a un Oursin (-1 aux ennemis)
    oursin = Card("o", "Urchin", 5, trigger="PASSIVE",
                  ability=CardAbility("DEBUFF_ENEMIES", "OPP", -1))
    game.player1.board = [oursin]
    
    # P2 a une créature normale (3 de base)
    enemy = Card("e", "Enemy", 3)
    game.player2.board = [enemy]
    
    # Cas 1 : C'est le tour de P2 (La victime)
    game.active_player_idx = 1
    game.phase = Phase.P2_MAIN
    # 3 - 1 = 2
    assert game.calculate_real_power(enemy) == 2 
    
    # Cas 2 : C'est le tour de P1 (Le propriétaire de l'oursin)
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    # Le debuff doit AUSSI s'appliquer ! (3 - 1 = 2)
    assert game.calculate_real_power(enemy) == 2
