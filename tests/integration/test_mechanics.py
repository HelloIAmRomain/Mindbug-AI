import pytest
from mindbug_engine.core.models import Card
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.consts import Phase, Trigger, Keyword

@pytest.fixture
def game():
    g = MindbugGame(verbose=False)
    g.state.player1.hand = []
    g.state.player2.hand = []
    g.state.player1.board = []
    g.state.player2.board = []
    return g


def test_mechanic_tough_survival(game):
    p1 = game.state.player1
    p2 = game.state.player2

    att = Card("a", "Att", 5)
    p1.board = [att]

    tough = Card("t", "Shield", 3, keywords=[Keyword.TOUGH])
    p2.board = [tough]

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    game.step("ATTACK", 0)
    game.step("BLOCK", 0)

    # Vérifications
    assert tough in p2.board  # Toujours vivante
    assert tough.is_damaged is True  # Marquée comme endommagée

    # Vérification ultime : Elle a perdu le mot-clé (car update_board_states a tourné)
    assert Keyword.TOUGH not in tough.keywords


def test_mechanic_frenzy_double_attack(game):
    """Test Fureur (Frenzy) V2."""
    p1 = game.state.player1
    p2 = game.state.player2

    frenzy_card = Card("f", "Frenzy", 6, keywords=[Keyword.FRENZY])
    p1.board = [frenzy_card]

    m1 = Card("m1", "M1", 2)
    m2 = Card("m2", "M2", 2)
    p2.board = [m1, m2]

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # --- Attaque 1 ---
    game.step("ATTACK", 0)
    game.step("BLOCK", 0)  # M1 bloque

    assert m1 in p2.discard
    assert frenzy_card in p1.board

    # --- TRANSITION FUREUR ---
    # L'Engine a rendu la main à P1 pour la 2ème attaque
    assert game.state.phase == Phase.P1_MAIN
    assert game.state.active_player == p1
    assert game.state.frenzy_candidate == frenzy_card

    # On vérifie que le seul coup légal est d'attaquer
    moves = game.get_legal_moves()
    assert len(moves) == 1
    assert moves[0] == ("ATTACK", 0)

    # --- Attaque 2 ---
    game.step("ATTACK", 0)  # P1 lance la 2ème attaque

    # Maintenant on est en phase de blocage pour P2
    assert game.state.phase == Phase.BLOCK_DECISION
    assert game.state.active_player == p2
    assert game.state.pending_attacker == frenzy_card

    game.step("BLOCK", 0)  # M2 bloque (Attention : M2 est devenu l'index 0 car M1 est mort)

    assert m2 in p2.discard

    # --- Fin du tour ---
    assert game.state.phase == Phase.P2_MAIN
    assert game.state.active_player == p2

def test_tough_reset_after_death(game):
    """Vérifie qu'une carte Tenace morte récupère son bouclier dans la défausse."""
    p1 = game.state.player1
    # Une carte Tenace
    tank = Card("t", "Tank", 4, keywords=[Keyword.TOUGH])
    p1.board = [tank]

    # 1. Premier coup : Perd le bouclier
    # On simule manuellement ou via combat
    tank.keywords.remove(Keyword.TOUGH)
    assert Keyword.TOUGH not in tank.keywords

    # 2. Mort (via CombatManager)
    game.combat_manager.apply_lethal_damage(tank, p1)

    # 3. Vérification dans la défausse
    assert tank in p1.discard
    # CRUCIAL : Elle doit avoir récupéré Tenace grâce au reset()
    assert Keyword.TOUGH in tank.keywords