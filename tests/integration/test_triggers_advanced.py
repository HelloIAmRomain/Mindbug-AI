import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card, CardAbility
from mindbug_engine.rules import Phase

@pytest.fixture
def game():
    return MindbugGame()

def test_trigger_unblocked_effect(game):
    """
    Test 'Turboustique' : Une créature avec un effet ON_ATTACK_UNBLOCKED
    ne doit pas infliger 1 dégât standard, mais appliquer son effet.
    """
    p1 = game.player1
    p2 = game.player2
    p2.hp = 3 # PV initiaux

    # Création d'une Turboustique
    mosquito = Card(
        id="m", name="Mosquito", power=4, 
        trigger="ON_ATTACK_UNBLOCKED",
        ability=CardAbility("SET_OPPONENT_HP_TO_ONE", "OPP", 1)
    )
    p1.board = [mosquito]
    
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN

    # P1 Attaque
    game.step("ATTACK", 0)
    
    # P2 ne bloque pas
    game.step("NO_BLOCK", -1)
    
    # VERIFICATION
    # Les PV doivent être à 1 (effet spécial), pas à 2 (dégât standard)
    assert p2.hp == 1

def test_selection_handover_on_death(game):
    """
    Test 'Mamie Harpie' : Si l'attaquant meurt et que son effet de mort
    demande une sélection, le jeu doit redonner la main à l'attaquant
    (même si c'était le tour de défense de l'adversaire).
    """
    p1 = game.player1 # Attaquant
    p2 = game.player2 # Défenseur
    
    # P1 a une Harpie (Voler créature à sa mort)
    harpie = Card(
        "h", "Harpie", 5, trigger="ON_DEATH",
        ability=CardAbility("STEAL_CREATURE", "OPP", 1)
    )
    p1.board = [harpie]
    
    # P2 a un Tueur (Poison) et une Cible
    killer = Card("k", "Killer", 1, keywords=["POISON"])
    target = Card("t", "Target", 3)
    p2.board = [killer, target]
    
    game.active_player_idx = 0
    game.phase = Phase.P1_MAIN
    
    # 1. P1 Attaque
    game.step("ATTACK", 0)
    
    # 2. P2 Bloque avec le Tueur (Phase BLOCK_DECISION, Active=P2)
    assert game.active_player == p2
    game.step("BLOCK", 0) # Index 0 = Killer
    
    # 3. Résolution
    # Harpie meurt (Poison). Son effet se déclenche.
    # Le jeu doit passer en mode SELECTION et redonner la main à P1.
    
    assert harpie in p1.discard
    assert game.phase == Phase.RESOLUTION_CHOICE
    
    # LE TEST CRITIQUE : C'est bien à P1 de choisir, pas à P2 !
    assert game.active_player == p1
    assert game.selection_context["initiator"] == p1
    
    # 4. P1 choisit la cible
    # Target est restée sur le board, c'est la seule carte restante de P2 (index 0)
    # (Killer est morte aussi à cause du combat, mais Target survit)
    # ATTENTION: Si Killer meurt aussi, Target est index 0.
    game.step("SELECT_BOARD_P2", 0)
    
    # Vérif finale
    assert target in p1.board
