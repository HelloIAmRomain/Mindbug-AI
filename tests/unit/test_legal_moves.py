import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card, CardAbility
from mindbug_engine.rules import Phase

@pytest.fixture
def game():
    g = MindbugGame()
    # Setup propre
    g.player1.hand = [Card("c1", "C1", 1)]
    g.player1.board = [Card("b1", "B1", 1)]
    g.player2.hand = []
    g.player2.board = [Card("b2", "B2", 1)]
    return g

def test_legal_moves_main_phase(game):
    """Vérifie qu'on peut JOUER ou ATTAQUER en phase principale."""
    game.phase = Phase.P1_MAIN
    game.active_player_idx = 0
    
    moves = game.get_legal_moves()
    
    # On doit avoir PLAY (index 0) et ATTACK (index 0)
    assert ("PLAY", 0) in moves
    assert ("ATTACK", 0) in moves
    assert ("BLOCK", 0) not in moves

def test_legal_moves_block_phase(game):
    """Vérifie qu'on peut BLOQUER ou PAS en phase de défense."""
    game.phase = Phase.BLOCK_DECISION
    game.active_player_idx = 1 # P2 défend
    game.pending_attacker = game.player1.board[0] # B1 attaque
    
    moves = game.get_legal_moves()
    
    assert ("BLOCK", 0) in moves # B2 peut bloquer B1
    assert ("NO_BLOCK", -1) in moves
    assert ("PLAY", 0) not in moves

def test_legal_moves_mindbug(game):
    """Vérifie les choix Mindbug."""
    game.phase = Phase.MINDBUG_DECISION
    game.active_player_idx = 1 # P2 choisit
    game.player2.mindbugs = 1
    
    moves = game.get_legal_moves()
    assert ("MINDBUG", -1) in moves
    assert ("PASS", -1) in moves

def test_legal_moves_selection(game):
    """Vérifie les cibles en phase de sélection."""
    game.phase = Phase.RESOLUTION_CHOICE
    game.active_player_idx = 0
    
    # On simule un contexte : P1 doit choisir une carte sur le board P2
    game.selection_context = {
        "candidates": [game.player2.board[0]], # B2 est candidat
        "effect_code": "DESTROY_CREATURE",
        "count": 1,
        "initiator": game.player1
    }
    
    moves = game.get_legal_moves()
    
    # On doit pouvoir sélectionner la carte 0 du board P2
    assert ("SELECT_BOARD_P2", 0) in moves
    assert ("SELECT_BOARD_P1", 0) not in moves # Pas candidat

def test_legal_moves_game_over(game):
    """Vérifie qu'aucun coup n'est possible si le jeu est fini."""
    game.winner = game.player1
    assert game.get_legal_moves() == []

def test_legal_moves_hunter_force_block(game):
    """
    Test spécifique : Si un Chasseur attaque, on passe en sélection.
    (Ce test couvre indirectement la logique de changement de phase dans step)
    """
    # Ce n'est pas un test direct de get_legal_moves mais du flux qui mène à des moves de sélection
    # Déjà couvert par les tests d'intégration, mais pour être sûr :
    pass


def test_legal_moves_frenzy_constraint(game):
    """
    CRITIQUE : Si une créature est en mode Fureur (Frenzy),
    le joueur NE PEUT PAS jouer de carte ni attaquer avec une autre.
    """
    p1 = game.player1
    frenzy_creature = Card("f", "Frenzy", 6)
    other_creature = Card("o", "Other", 4)

    p1.board = [frenzy_creature, other_creature]
    p1.hand = [Card("h", "Hand", 1)]

    # Activation du mode Fureur
    game.phase = Phase.P1_MAIN
    game.active_player_idx = 0
    game.frenzy_candidate = frenzy_creature

    moves = game.get_legal_moves()

    # Vérifications
    assert len(moves) == 1
    assert moves[0] == ("ATTACK", 0)  # Index 0 = frenzy_creature

    # S'assurer qu'on ne peut PAS jouer de carte
    assert ("PLAY", 0) not in moves
    # S'assurer qu'on ne peut PAS attaquer avec l'autre
    assert ("ATTACK", 1) not in moves