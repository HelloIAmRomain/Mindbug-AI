import pytest
from mindbug_engine.core.models import Card
from mindbug_engine.core.consts import Phase, Keyword, Difficulty
from mindbug_ai.factory import AgentFactory

# =============================================================================
# SCÉNARIO 1 : PvP (Humain vs Humain)
# Vérifie que le moteur demande bien à l'attaquant (P2) de choisir sa cible.
# =============================================================================


def test_hunter_pvp_manual_choice(game):
    p1 = game.state.player1
    p2 = game.state.player2

    # Setup : Hunter (P2) vs Victime (P1)
    hunter = Card("h", "Hunter", 5, keywords=[Keyword.HUNTER])
    p2.board = [hunter]

    victim = Card("v", "Victim", 3)
    p1.board = [victim]

    # C'est au tour de P2
    game.state.active_player_idx = 1
    game.state.phase = Phase.P2_MAIN

    # 1. P2 déclare l'attaque
    game.step("ATTACK", 0)

    assert game.state.phase == Phase.RESOLUTION_CHOICE
    assert game.state.active_request.reason == "HUNTER_TARGET"
    assert game.state.active_request.selector == p2  # C'est bien P2 qui choisit

    # Vérification des candidats (La victime + l'option de passer)
    candidates = game.state.active_request.candidates
    assert victim in candidates
    assert "NO_HUNT" in candidates

    # 2. P2 choisit la cible (Action Manuelle)
    # On simule le clic sur la carte adverse
    game.resolve_selection_effect(victim)

    # Le combat 5 vs 3 doit avoir eu lieu immédiatement
    assert victim in p1.discard
    assert hunter in p2.board

    # La main doit être rendue à P1
    assert game.state.active_player == p1
    assert game.state.phase == Phase.P1_MAIN


# =============================================================================
# SCÉNARIO 2 : PvE (IA vs Humain)
# Vérifie que l'IA comprend qu'elle doit choisir une cible.
# =============================================================================
def test_hunter_pve_ai_choice(game):
    # 1. Création de l'IA (MCTS)
    # On lui donne un temps très court pour le test
    agent = AgentFactory.create_agent(Difficulty.HARD, strategy="MCTS")
    agent.simulation_time = 0.2

    p1 = game.state.player1
    p2 = game.state.player2

    # Sinon l'IA pourrait décider de jouer une carte (PLAY) et faire échouer le test
    p2.hand = []

    # Setup : Hunter (IA/P2) vs Victime (Humain/P1)
    hunter = Card("h_ai", "Predator", 5, keywords=[Keyword.HUNTER])
    p2.board = [hunter]

    victim = Card("v_human", "Prey", 1)  # 1 de force -> Kill facile
    p1.board = [victim]

    game.state.active_player_idx = 1  # Tour de l'IA
    game.state.phase = Phase.P2_MAIN

    # --- ETAPE 1 : L'IA décide d'attaquer ---
    # On demande à l'agent ce qu'il veut faire
    action = agent.get_action(game)

    # Elle devrait attaquer (c'est son seul coup légal maintenant)
    assert action[0] == "ATTACK"

    # On joue le coup pour elle
    game.step(action[0], action[1])

    assert game.state.phase == Phase.RESOLUTION_CHOICE

    # --- ETAPE 2 : L'IA choisit sa cible ---
    # On redemande à l'agent (il doit gérer la phase RESOLUTION_CHOICE)
    selection_action = agent.get_action(game)

    assert selection_action is not None
    # L'IA doit sélectionner une carte sur le board adverse
    assert selection_action[0] == "SELECT_OPP_BOARD"

    # On joue la sélection
    game.step(selection_action[0], selection_action[1])

    assert victim in p1.discard

    assert game.state.active_player == p1
