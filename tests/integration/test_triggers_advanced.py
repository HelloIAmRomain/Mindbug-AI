import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.models import Card, CardEffect
from mindbug_engine.core.consts import Phase, Trigger, EffectType


@pytest.fixture
def game():
    """Fixture d'un jeu vide pour tester les mécaniques isolées."""
    g = MindbugGame(verbose=False)
    g.state.player1.hand = []
    g.state.player2.hand = []
    g.state.player1.board = []
    g.state.player2.board = []
    g.state.deck = []
    return g


def test_trigger_unblocked_effect(game):
    """
    Test ON_UNBLOCKED (ex: Turboustique qui pique si non bloqué).

    Séquence attendue :
    1. Attaque (Pas d'effet immédiat)
    2. Pas de blocage
    3. Trigger ON_UNBLOCKED -> Set HP à 1
    4. Résolution des dégâts -> 4 dégâts
    5. Résultat : HP = 1 - 4 = 0 (Mort)
    """
    p1 = game.state.player1
    p2 = game.state.player2
    p2.hp = 3

    # Effet : Set HP à 1
    effect = CardEffect(EffectType.MODIFY_STAT,
                        target={"group": "OPPONENT"},
                        params={"stat": "HP", "amount": 1, "operation": "SET"})

    mosquito = Card("m", "Mosquito", 4, trigger=Trigger.ON_UNBLOCKED, effects=[effect])
    p1.board = [mosquito]

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    game.step("ATTACK", 0)
    game.step("NO_BLOCK", -1)

    # CORRECTION : Le joueur meurt.
    # L'effet (HP=1) s'applique juste avant les dégâts (4).
    assert p2.hp == 0
    assert game.state.winner == p1


def test_trigger_on_attack_immediate(game):
    """
    Test ON_ATTACK (Se déclenche dès la déclaration).

    Séquence attendue :
    1. Déclaration Attaque
    2. Trigger ON_ATTACK -> Set HP à 1 (IMMÉDIAT)
    3. Phase de blocage
    """
    p1 = game.state.player1
    p2 = game.state.player2
    p2.hp = 3

    # Effet : Set HP à 1
    effect = CardEffect(EffectType.MODIFY_STAT,
                        target={"group": "OPPONENT"},
                        params={"stat": "HP", "amount": 1, "operation": "SET"})

    # Note : Trigger ON_ATTACK
    turbo = Card("t", "Turbo", 4, trigger=Trigger.ON_ATTACK, effects=[effect])
    p1.board = [turbo]

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # L'action d'attaquer déclenche l'effet IMMÉDIATEMENT (avant que P2 ne réponde)
    game.step("ATTACK", 0)

    # Vérification intermédiaire
    assert p2.hp == 1
    assert game.state.phase == Phase.BLOCK_DECISION

    # Si P2 ne bloque pas, il prend les dégâts
    game.step("NO_BLOCK", -1)

    # Dégâts combat : 1 - 4 = -3 -> 0
    assert p2.hp == 0
    assert game.state.winner == p1