import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card, CardAbility

@pytest.fixture
def game():
    g = MindbugGame()
    # On vide les mains pour injecter nos propres cartes de test
    g.player1.hand = []
    g.player2.hand = []
    g.player1.board = []
    g.player2.board = []
    return g

def test_integration_on_play_trigger(game):
    """Vérifie que jouer une carte déclenche bien son effet ON_PLAY."""
    p1 = game.player1
    p1.hp = 1 # P1 est blessé
    
    # Création d'une carte Soigneuse
    healer = Card(
        id="h1", name="Doc", power=1, 
        trigger="ON_PLAY", 
        ability=CardAbility(code="HEAL", target="SELF", value=3)
    )
    p1.hand.append(healer)
    
    # 1. P1 joue la carte
    game.active_player_idx = 0
    game.phase = game.phase.P1_MAIN
    game.step("PLAY", 0)
    
    # 2. P2 laisse passer (Trigger déclenché ICI)
    game.step("PASS")
    
    # Assert
    assert p1.hp == 4 # La magie a opéré !
    assert healer in p1.board

def test_integration_mindbug_steals_effect(game):
    """
    Vérifie que si P2 vole la carte, l'effet ON_PLAY s'applique à P2.
    C'est crucial pour le gameplay.
    """
    p1 = game.player1
    p2 = game.player2
    p2.hp = 1 # P2 est blessé
    
    healer = Card(
        id="h1", name="Doc", power=1, 
        trigger="ON_PLAY", 
        ability=CardAbility(code="HEAL", target="SELF", value=3)
    )
    p1.hand.append(healer)
    
    # 1. P1 joue
    game.active_player_idx = 0
    game.step("PLAY", 0)
    
    # 2. P2 vole ! (Trigger déclenché ICI pour P2)
    game.step("MINDBUG")
    
    # Assert
    assert healer in p2.board
    assert p2.hp == 4 # P2 soigné
    assert p1.hp == 3 # P1 inchangé (il était à 3, mais le soin n'est pas pour lui)

def test_integration_on_death_trigger(game):
    """Vérifie qu'une carte qui meurt en combat déclenche son effet."""
    p1 = game.player1
    p2 = game.player2
    
    # P1 a un "Baril" qui vole une carte quand il meurt
    # On simule un effet simple : Dégâts à l'adversaire quand il meurt
    bomb = Card(
        id="b1", name="Bomb", power=1,
        trigger="ON_DEATH",
        ability=CardAbility(code="DAMAGE", target="OPP", value=1)
    )
    p1.board.append(bomb)
    
    # P2 a un tueur
    killer = Card(id="k1", name="Killer", power=10)
    p2.board.append(killer)
    
    # Combat : P2 attaque, P1 bloque avec la Bombe
    game.active_player_idx = 1 # P2
    game.pending_attacker = killer
    
    # P1 bloque (Bombe meurt)
    # Note: On appelle _resolve_combat via l'action BLOCK de l'engine normalement
    # Pour le test d'intégration, simulons le step complet
    game.active_player_idx = 0 # C'est à P1 de bloquer
    game.phase = game.phase.BLOCK_DECISION
    
    # On doit s'assurer que l'engine sait qui attaque
    game.pending_attacker = killer 
    
    # Action : BLOQUER
    p2.hp = 3
    game.step("BLOCK", 0) # Index de la bombe
    
    # Assert
    assert bomb in p1.discard # La bombe est morte
    assert p2.hp == 2         # L'effet ON_DEATH a explosé au visage de P2 !
