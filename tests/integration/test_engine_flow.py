import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card
from mindbug_engine.rules import Phase

@pytest.fixture
def game():
    return MindbugGame() # Charge le deck par défaut

def test_initial_setup(game):
    """Vérifie que la partie commence proprement."""
    assert game.turn_count == 1
    assert game.phase == Phase.P1_MAIN
    assert game.active_player.name == "P1"
    # Les joueurs doivent avoir 5 cartes (setup par défaut)
    assert len(game.player1.hand) == 5 
    assert len(game.player2.hand) == 5

def test_flow_play_card_transition(game):
    """P1 joue -> On doit passer en phase de décision Mindbug pour P2."""
    game.active_player_idx = 0 
    game.phase = Phase.P1_MAIN
    
    # Action
    game.step("PLAY", 0)
    
    # Vérifications
    assert game.phase == Phase.MINDBUG_DECISION
    assert game.active_player.name == "P2" # C'est à P2 de choisir
    assert game.pending_card is not None 

def test_flow_mindbug_refusal(game):
    """
    Scénario classique : P1 joue -> P2 refuse -> Carte chez P1 -> Tour P2.
    """
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    card_played = game.player1.hand[0]
    
    # 1. P1 joue
    game.step("PLAY", 0)
    
    # 2. P2 refuse
    game.step("PASS")
    
    # Vérifications
    assert card_played in game.player1.board 
    assert game.active_player.name == "P2"   # Le tour a changé
    assert game.phase == Phase.P2_MAIN       
    assert game.player2.mindbugs == 2        

def test_flow_mindbug_accepted(game):
    """
    Scénario Vol (Règle Replay) :
    P1 joue -> P2 Mindbug -> Carte chez P2 -> P1 rejoue son tour.
    """
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    card_played = game.player1.hand[0]
    
    # 1. P1 joue
    game.step("PLAY", 0)
    
    # 2. P2 Vole
    game.step("MINDBUG")
    
    # Vérifications
    assert card_played in game.player2.board # P2 a la carte
    assert game.player2.mindbugs == 1        # Coût payé
    
    # RÈGLE REPLAY : Le tour revient à P1
    assert game.active_player.name == "P1"   
    assert game.phase == Phase.P1_MAIN       

def test_win_condition_detection(game):
    """Vérifie que le jeu s'arrête si HP <= 0."""
    game.player1.hp = 1
    # P2 a un tueur
    killer = Card("Killer", "K", 5)
    game.player2.board = [killer]
    game.player1.board = [] # Pas de défense
    
    # P2 attaque P1
    game.active_player_idx = 1 # P2
    game.phase = Phase.P2_MAIN
    game.step("ATTACK", 0)
    
    # P1 ne peut pas bloquer (pas de board) -> Le jeu passe en BLOCK_DECISION mais sans bloqueur valide
    # P1 choisit de ne pas bloquer
    game.step("NO_BLOCK")
    
    # Vérif
    assert game.player1.hp == 0
    assert game.winner == game.player2
