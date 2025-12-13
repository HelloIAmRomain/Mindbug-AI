import pytest
from mindbug_engine.models import Card, CardAbility
from mindbug_engine.rules import Phase

def test_power_boost_my_turn(game):
    goblin = Card("g", "Gob", 2, trigger="PASSIVE", 
                  ability=CardAbility("BOOST_IF_MY_TURN", "SELF", 6))
    game.player1.board = [goblin]
    
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    assert game.calculate_real_power(goblin) == 8
    
    game.active_player_idx = 1 
    game.phase = Phase.P2_MAIN
    assert game.calculate_real_power(goblin) == 2

def test_power_debuff_enemies(game):
    oursin = Card("o", "Urchin", 5, trigger="PASSIVE",
                  ability=CardAbility("DEBUFF_ENEMIES", "OPP", -1))
    game.player1.board = [oursin]
    
    enemy = Card("e", "Enemy", 3)
    game.player2.board = [enemy]
    
    game.active_player_idx = 1
    game.phase = Phase.P2_MAIN
    assert game.calculate_real_power(enemy) == 2 
    
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    assert game.calculate_real_power(enemy) == 2
