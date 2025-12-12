import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card, CardAbility
from mindbug_engine.rules import Phase

@pytest.fixture
def game():
    g = MindbugGame()
    # On vide tout pour maîtriser le test
    g.player1.hand = []
    g.player2.hand = []
    g.player1.board = []
    g.player2.board = []
    return g

def test_integration_on_play_trigger(game):
    """Vérifie que jouer une carte déclenche bien son effet ON_PLAY."""
    p1 = game.player1
    p1.hp = 1 
    
    # Carte Soin (Trigger ON_PLAY)
    healer = Card("h1", "Doc", 1, trigger="ON_PLAY", 
                  ability=CardAbility("HEAL", "SELF", 3))
    p1.hand.append(healer)
    
    # 1. P1 joue
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    game.step("PLAY", 0)
    
    # 2. P2 refuse Mindbug
    game.step("PASS")
    
    # Assert
    assert p1.hp == 4 
    assert healer in p1.board

def test_integration_mindbug_steals_effect(game):
    """
    Vérifie que si P2 vole la carte, l'effet ON_PLAY s'applique à P2.
    """
    p1 = game.player1
    p2 = game.player2
    p2.hp = 1 
    
    healer = Card("h1", "Doc", 1, trigger="ON_PLAY", 
                  ability=CardAbility("HEAL", "SELF", 3))
    p1.hand.append(healer)
    
    # 1. P1 joue
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    game.step("PLAY", 0)
    
    # 2. P2 vole ! (Trigger déclenché pour P2)
    game.step("MINDBUG")
    
    # Assert
    assert healer in p2.board
    assert p2.hp == 4 # P2 soigné
    assert p1.hp == 3 

def test_integration_on_death_trigger_with_selection(game):
    """
    Vérifie qu'un Crapaud Bombe qui meurt interrompt le combat pour demander une cible.
    """
    p1 = game.player1
    p2 = game.player2
    
    # P1 a un Crapaud Bombe (Trigger ON_DEATH avec Choix)
    bomb = Card("b1", "Bomb", 1, trigger="ON_DEATH",
                ability=CardAbility("DESTROY_CREATURE", "OPP", 1, "CHOICE_USER"))
    p1.board.append(bomb)
    
    # P2 a un Tueur et une Victime
    killer = Card("k1", "Killer", 10)
    victim = Card("v1", "Victim", 2)
    p2.board = [killer, victim]
    
    # Combat : P2 attaque avec Killer
    game.active_player_idx = 1 
    game.phase = Phase.P2_MAIN
    game.step("ATTACK", 0) # Killer attaque
    
    # P1 bloque avec la Bombe
    # Le moteur attend un BLOCK de P1 (car tour défensif)
    game.step("BLOCK", 0) # Bombe
    
    # À ce stade :
    # 1. Combat résolu -> Bombe meurt.
    # 2. Effet ON_DEATH -> ask_for_selection (CHOICE_USER).
    # 3. Le jeu doit être en PAUSE.
    
    assert bomb in p1.discard
    assert game.phase == Phase.RESOLUTION_CHOICE
    
    # P1 doit choisir qui détruire (la Victime de P2, index 1)
    game.step("SELECT_BOARD_P2", 1)
    
    # Fin du tour
    assert victim in p2.discard
    assert game.active_player == p2 # Nouveau tour P2

def test_integration_dracompost_sequence(game):
    """
    Test complet de la séquence Dracompost (Défausse -> Plateau).
    """
    p1 = game.player1
    # Une carte dans la défausse
    dead = Card("d1", "Dead", 5)
    p1.discard = [dead]
    
    # Dracompost en main
    draco = Card("dc", "Draco", 3, trigger="ON_PLAY",
                 ability=CardAbility("PLAY_FROM_MY_DISCARD", "SELF", 1))
    p1.hand = [draco]
    
    # 1. P1 joue
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    game.step("PLAY", 0)
    
    # 2. P2 refuse
    game.step("PASS")
    
    # 3. Pause : Sélection dans défausse P1
    assert game.phase == Phase.RESOLUTION_CHOICE
    
    # 4. P1 clique sur la carte dans sa défausse (Index 0)
    game.step("SELECT_DISCARD_P1", 0)
    
    # Assert
    assert dead in p1.board
    assert len(p1.discard) == 0
