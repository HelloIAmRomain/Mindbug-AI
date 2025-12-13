import pytest
from mindbug_engine.models import Card, CardAbility
from mindbug_engine.engine import MindbugGame
from mindbug_engine.rules import Phase

# Note: On n'importe plus EffectManager directement, on l'utilise via game.effect_manager

def test_dracompost_play_discard(game):
    p1 = game.player1
    dead_card = Card("d1", "BigGuy", 10)
    p1.discard = [dead_card]
    
    dracompost = Card("dc", "Draco", 3, trigger="ON_PLAY", 
                      ability=CardAbility("PLAY_FROM_MY_DISCARD", "SELF", 1))
    p1.hand = [dracompost]
    
    game.step("PLAY", 0)
    game.step("PASS")
    
    assert game.phase == Phase.RESOLUTION_CHOICE
    game.step("SELECT_DISCARD_P1", 0)
    assert dead_card in p1.board

def test_reclaim_all_discard(game):
    p1 = game.player1
    c1 = Card("1", "A", 1)
    p1.discard = [c1]
    
    giraffodile = Card("g", "Gira", 7, trigger="ON_PLAY", 
                       ability=CardAbility("RECLAIM_ALL_DISCARD", "SELF", 0))
    p1.hand = [giraffodile]
    
    game.step("PLAY", 0)
    game.step("PASS")
    
    assert len(p1.discard) == 0
    assert c1 in p1.hand

def test_neuromouche_steal_condition(game):
    p1 = game.player1
    p2 = game.player2
    weak = Card("w", "Weak", 3)
    strong = Card("s", "Strong", 7)
    p2.board = [weak, strong]
    
    neuro = Card("n", "Fly", 4, trigger="ON_PLAY",
                 ability=CardAbility("STEAL_CREATURE", "OPP", 1, "MIN_POWER", 6))
    p1.hand = [neuro]
    
    game.step("PLAY", 0)
    game.step("PASS")
    
    assert game.phase == Phase.RESOLUTION_CHOICE
    
    candidates = game.selection_context["candidates"]
    assert strong in candidates
    assert weak not in candidates
    
    # Strong est à l'index 1 du board P2
    game.step("SELECT_BOARD_P2", 1)
    
    assert strong in p1.board

def test_effect_destroy_all_enemies(game):
    p1 = game.player1
    p2 = game.player2
    
    w1 = Card("w1", "Weak1", 3)
    w2 = Card("w2", "Weak2", 3)
    s1 = Card("s1", "Strong", 8)
    p2.board = [w1, w2, s1]
    
    kanga = Card("k", "Kanga", 7, trigger="ON_PLAY",
                 ability=CardAbility("DESTROY_ALL_ENEMIES", "OPP", 0, "MAX_POWER", 4))
    p1.hand = [kanga]
    
    game.step("PLAY", 0)
    game.step("PASS")
    
    assert w1 in p2.discard
    assert w2 in p2.discard
    assert s1 in p2.board

def test_effect_discard_random(game):
    p2 = game.player2
    c1 = Card("c1", "C1", 1)
    c2 = Card("c2", "C2", 1)
    p2.hand = [c1, c2]
    # On vide le deck pour éviter le refill automatique qui fausserait le compte
    p2.deck = [] 
    
    furet = Card("f", "Furet", 2, trigger="ON_PLAY",
                 ability=CardAbility("DISCARD_RANDOM", "OPP", 1))
    game.player1.hand = [furet]
    
    game.step("PLAY", 0)
    game.step("PASS")
    
    # 2 cartes - 1 défaussée = 1 restante (car deck vide)
    assert len(p2.hand) == 1
    assert len(p2.discard) == 1

def test_effect_steal_hand(game):
    """Test Baril (Voler main)."""
    p1 = game.player1
    p2 = game.player2
    target_card = Card("t", "Target", 5)
    p2.hand = [target_card]
    
    thief = Card("t", "Thief", 1, trigger="ON_DEATH",
                 ability=CardAbility("STEAL_CARD_HAND", "OPP", 1))
    
    # --- CORRECTION ICI : Utilisation de l'instance via game.effect_manager ---
    game.effect_manager.apply_effect(game, thief, p1, p2)
    
    assert target_card in p1.hand
    assert target_card not in p2.hand

def test_effect_play_opp_discard(game):
    p1 = game.player1
    p2 = game.player2
    dead = Card("d", "Dead", 5)
    p2.discard = [dead]
    
    pilleur = Card("p", "Pilleur", 1, trigger="ON_PLAY",
                   ability=CardAbility("PLAY_FROM_OPP_DISCARD", "SELF", 1))
    p1.hand = [pilleur]
    
    game.step("PLAY", 0)
    game.step("PASS")
    
    assert game.phase == Phase.RESOLUTION_CHOICE
    game.step("SELECT_DISCARD_P2", 0)
    
    assert dead in p1.board

def test_effect_sacrifice(game):
    p1 = game.player1
    p2 = game.player2
    
    victim = Card("v", "Vic", 5)
    p2.board = [victim]
    
    kanga = Card("k", "Kanga", 5, trigger="ON_PLAY",
                 ability=CardAbility("OPPONENT_SACRIFICE", "OPP", 1))
    p1.hand = [kanga]
    
    game.active_player_idx = 0
    game.step("PLAY", 0)
    game.step("PASS")
    
    assert len(p2.board) == 0
    assert victim in p2.discard

def test_effect_reclaim_discard_simple(game):
    p1 = game.player1
    dead = Card("d", "Dead", 1)
    p1.discard = [dead]
    
    necro = Card("n", "Necro", 3, trigger="ON_PLAY",
                 ability=CardAbility("RECLAIM_DISCARD", "SELF", 1))
    p1.hand = [necro]
    
    game.active_player_idx = 0
    game.step("PLAY", 0)
    game.step("PASS")
    
    assert game.phase == Phase.RESOLUTION_CHOICE
    game.step("SELECT_DISCARD_P1", 0)
    
    assert dead in p1.hand
    assert dead not in p1.board
