import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card
from mindbug_engine.rules import Phase

@pytest.fixture
def game():
    return MindbugGame() # Charge le vrai deck par défaut

def test_initial_setup(game):
    """Vérifie que la partie commence proprement."""
    assert game.turn_count == 1
    assert game.phase == Phase.P1_MAIN
    assert game.active_player.name == "P1"
    # 5 en main (si mode compétitif activé dans config par défaut)
    assert len(game.player1.hand) == 5 
    assert len(game.player2.hand) == 5

def test_flow_play_card_transition(game):
    """P1 joue -> On doit passer en phase de décision Mindbug pour P2."""
    game.active_player_idx = 0 # Force P1
    game.phase = Phase.P1_MAIN
    
    # Action
    game.step("PLAY", 0)
    
    # Vérifications
    assert game.phase == Phase.MINDBUG_DECISION
    assert game.active_player.name == "P2" # C'est temporairement à P2 de choisir
    assert game.pending_card is not None # La carte est en "limbo"

def test_flow_mindbug_refusal(game):
    """
    Scénario classique :
    1. P1 joue
    2. P2 refuse le Mindbug
    3. La carte va chez P1
    4. C'est au tour de P2
    """
    # Étape 1 : P1 joue
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    card_played = game.player1.hand[0]
    game.step("PLAY", 0)
    
    # Étape 2 : P2 refuse
    game.step("PASS")
    
    # Vérifications
    assert card_played in game.player1.board # P1 a bien sa carte
    assert game.active_player.name == "P2"   # Le tour a changé
    assert game.phase == Phase.P2_MAIN       # C'est une phase principale
    assert game.player2.mindbugs == 2        # Pas de coût

def test_flow_mindbug_accepted(game):
    """
    Scénario Vol (CORRIGÉ) :
    1. P1 joue une carte.
    2. P2 utilise Mindbug.
    3. La carte va chez P2.
    4. C'est À NOUVEAU à P1 de jouer (P1 rejoue son tour).
    """
    # Setup : C'est à P1
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    card_played = game.player1.hand[0]
    
    # Action 1 : P1 joue
    game.step("PLAY", 0)
    
    # Vérif intermédiaire : C'est à P2 de décider
    assert game.phase == Phase.MINDBUG_DECISION
    assert game.active_player.name == "P2"
    
    # Action 2 : P2 Vole
    game.step("MINDBUG")
    
    # Vérifications Finales
    assert card_played in game.player2.board # P2 a bien la carte
    assert game.player2.mindbugs == 1        # P2 a payé
    
    # CORRECTION ICI : Le tour doit revenir à P1
    assert game.active_player.name == "P1"   # C'est redevenu P1
    assert game.phase == Phase.P1_MAIN       # Il doit rejouer (poser ou attaquer)

def test_win_condition_detection(game):
    """Vérifie que le jeu s'arrête si HP <= 0."""
    game.player1.hp = 1
    game.player2.board = [Card("Killer", "K", 5)]
    game.player1.board = [] # Pas de défense
    
    # P2 attaque P1
    game.active_player_idx = 1 # P2
    game.phase = Phase.P2_MAIN
    game.step("ATTACK", 0)
    
    # P1 ne peut pas bloquer (pas de board) -> NO_BLOCK auto ou manuel
    game.step("NO_BLOCK")
    
    # Vérif
    assert game.player1.hp == 0
    assert game.winner == game.player2
