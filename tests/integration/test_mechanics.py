import pytest
from mindbug_engine.models import Card, CardAbility
from mindbug_engine.engine import MindbugGame
from mindbug_engine.rules import Phase, Keyword

@pytest.fixture
def game():
    g = MindbugGame()
    # On vide les mains/boards pour contrôler le test
    g.player1.hand = []
    g.player1.board = []
    g.player2.hand = []
    g.player2.board = []
    return g

# --- TEST MECANIQUE : CORIACE (TOUGH) ---

def test_mechanic_tough_survival(game):
    """Vérifie qu'en jeu, une créature TOUGH survit aux dégâts."""
    p1 = game.player1
    p2 = game.player2
    
    # P1 attaque (5)
    att = Card("a", "Att", 5)
    p1.board = [att]
    
    # P2 défend avec Tough (3) -> Doit perdre le combat mais survivre
    tough = Card("t", "Shield", 3, keywords=["TOUGH"])
    p2.board = [tough]
    
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    
    game.step("ATTACK", 0)
    game.step("BLOCK", 0)
    
    # Résultat : Tough est blessé mais toujours sur le plateau
    assert tough in p2.board
    assert tough.is_damaged is True
    assert tough not in p2.discard

# --- TEST MECANIQUE : MOTS-CLÉS DYNAMIQUES ---

def test_mechanic_dynamic_keywords_shark(game):
    """Vérifie que le Requin Crabe copie les mots-clés ennemis à chaque étape."""
    p1 = game.player1
    p2 = game.player2
    
    # P1 a le Requin Crabe
    shark = Card("s", "Shark", 5, trigger="PASSIVE", 
                 ability=CardAbility("COPY_ALL_KEYWORDS_FROM_ENEMIES", "SELF", 0))
    p1.board = [shark]
    
    # P2 a un Chasseur
    hunter = Card("h", "Hunt", 3, keywords=["HUNTER"])
    p2.board = [hunter]
    
    # On force une mise à jour (via une étape fictive ou appel direct)
    game.update_board_states()
    
    # Vérif : Le requin a gagné HUNTER
    assert "HUNTER" in shark.keywords
    
    # P2 perd son Chasseur
    p2.board = []
    game.update_board_states()
    
    # Vérif : Le requin a perdu HUNTER
    assert "HUNTER" not in shark.keywords

# --- TEST MECANIQUE : FURIE (FRENZY) ---

def test_mechanic_frenzy_double_attack(game):
    """Vérifie l'enchaînement de deux attaques avec Furie (Mode Automatique)."""
    p1 = game.player1
    p2 = game.player2

    # Setup : P1 a une créature Fureur (6), P2 a deux bloqueurs (2)
    frenzy_card = Card("f", "Frenzy", 6, keywords=["FRENZY"])
    p1.board = [frenzy_card]

    m1 = Card("m1", "M1", 2)
    m2 = Card("m2", "M2", 2)
    p2.board = [m1, m2]

    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN

    # --- Attaque 1 ---
    # P1 attaque manuellement la première fois
    game.step("ATTACK", 0)

    # P2 défend
    assert game.active_player == p2
    game.step("BLOCK", 0)  # M1 bloque

    # Résultat Combat 1
    assert m1 in p2.discard
    assert frenzy_card in p1.board  # Fureur survit

    # --- Attaque 2 (Automatique) ---
    # CORRECTION DU TEST ICI :
    # Avec la nouvelle logique, on ne revient PAS à P1.
    # La Fureur a déclenché une nouvelle phase de blocage IMMÉDIATE pour P2.

    assert game.phase == Phase.BLOCK_DECISION
    assert game.active_player == p2  # C'est à P2 de bloquer à nouveau !
    assert game.pending_attacker == frenzy_card

    # P2 défend la seconde attaque
    game.step("BLOCK", 0)  # M2 bloque (l'index 0 car M1 est morte)

    # Résultat Combat 2
    assert m2 in p2.discard

    # --- Fin du tour ---
    # La Fureur ne s'active qu'une fois par tour (logique à vérifier si implémentée,
    # mais ici frenzy_candidate devrait être reset)
    # Le tour devrait être fini -> Main à P2

    assert game.phase == Phase.P2_MAIN
    assert game.active_player == p2