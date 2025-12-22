import pytest
from mindbug_engine.core.models import Card, CardEffect
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.consts import Phase, Trigger, EffectType, Keyword


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
    """Test Fureur (Frenzy) V2 avec Auto-Attack."""
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

    # M1 bloque
    # C'est ici que tout se joue : La résolution de ce blocage va déclencher
    # la mort de M1 -> Fureur -> Auto-Attack -> Transition vers P2
    game.step("BLOCK", 0)

    assert m1 in p2.discard
    assert frenzy_card in p1.board

    # --- TRANSITION FUREUR (Automatique maintenant) ---

    assert game.state.phase == Phase.BLOCK_DECISION
    assert game.state.active_player == p2
    assert game.state.pending_attacker == frenzy_card

    # --- Attaque 2 (Résolution du blocage) ---
    # M2 bloque (M2 est devenu l'index 0 car M1 est mort)
    game.step("BLOCK", 0)

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


def test_fix_hunter_turn_loop(game):
    """
    Vérifie le correctif du Hunter :
    Après avoir choisi une cible et résolu le combat, le tour DOIT passer à l'adversaire.
    (Avant P1 rejouait immédiatement).
    """
    p1 = game.state.player1
    p2 = game.state.player2

    # Setup : Hunter chez P1 vs Victime chez P2
    hunter = Card("h", "Hunter", 5, keywords=[Keyword.HUNTER])
    p1.board = [hunter]

    victim = Card("v", "Victim", 3)
    p2.board = [victim]

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # 1. P1 Attaque
    game.step("ATTACK", 0)

    # Vérif : On doit être en sélection de cible Hunter
    assert game.state.phase == Phase.RESOLUTION_CHOICE
    assert game.state.active_request.reason == "HUNTER_TARGET"

    # 2. P1 choisit la victime (Simulation du clic sur la carte adverse)
    # Note : resolve_selection_effect prend l'objet, pas l'index
    game.resolve_selection_effect(victim)

    # 3. Résolution automatique du combat (5 vs 3 -> Victime meurt)
    assert victim in p2.discard

    # --- CHECK CRITIQUE ---
    # Le tour de P1 doit être fini. C'est maintenant à P2 de jouer.
    assert game.state.active_player == p2
    assert game.state.phase == Phase.P2_MAIN


def test_fix_hunter_skip_attack(game):
    """
    Vérifie la nouvelle feature "Attaque Normale" (Skip Hunter).
    Si P1 choisit 'NO_HUNT', c'est à P2 de choisir son bloqueur.
    """
    p1 = game.state.player1
    p2 = game.state.player2

    hunter = Card("h", "Hunter", 5, keywords=[Keyword.HUNTER])
    p1.board = [hunter]
    p2.board = [Card("b", "Blocker", 6)]

    game.state.active_player_idx = 0
    game.step("ATTACK", 0)

    # 1. P1 choisit de NE PAS utiliser le pouvoir Hunter
    # (Simulation du clic sur le bouton "Attaque Normale")
    game.resolve_selection_effect("NO_HUNT")

    # --- CHECK ---
    # Le combat n'est PAS résolu. On est passé en phase de blocage standard.
    # C'est à P2 de décider.
    assert game.state.phase == Phase.BLOCK_DECISION
    assert game.state.active_player == p2

    # P2 peut bloquer normalement
    game.step("BLOCK", 0)
    assert hunter in p1.discard  # 5 vs 6 -> Hunter meurt


def test_fix_huissielephant_opponent_choice(game):
    """
    Vérifie que l'effet de défausse est bien un choix de l'adversaire (CHOICE_OPP)
    et non aléatoire ou contrôlé par l'attaquant.
    """
    p1 = game.state.player1
    p2 = game.state.player2

    # Setup : Huissiéléphant (Effet Discard CHOICE_OPP)
    eff = CardEffect(EffectType.DISCARD,
                     target={"group": "OPPONENT", "zone": "HAND", "count": 1, "select": "CHOICE_OPP"})

    eleph = Card("e", "Eleph", 8, trigger=Trigger.ON_ATTACK, effects=[eff])
    p1.board = [eleph]

    # Main de P2
    c1 = Card("1", "C1", 1)
    c2 = Card("2", "C2", 1)
    p2.hand = [c1, c2]

    game.state.active_player_idx = 0

    # 1. P1 Attaque -> Trigger
    game.step("ATTACK", 0)

    # --- CHECK 1 : On est en attente de sélection ---
    assert game.state.phase == Phase.RESOLUTION_CHOICE
    req = game.state.active_request
    assert req is not None

    # --- CHECK 2 : C'est bien P2 (l'Opposant) qui doit choisir ---
    assert req.selector == p2

    # 2. P2 choisit de défausser C1
    game.resolve_selection_effect(c1)

    # --- CHECK 3 : C1 est défaussée ---
    assert c1 in p2.discard
    assert c1 not in p2.hand

    # --- CHECK 4 : La main est complétée (Refill) ---
    # (Si le deck n'est pas vide, P2 repioche)
    if game.state.deck:
        assert len(p2.hand) == 5

    # Le jeu reprend son cours (Phase de Block pour P2)
    assert game.state.phase == Phase.BLOCK_DECISION
