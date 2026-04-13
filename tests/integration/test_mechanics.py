import pytest
from mindbug.engine.core.models import Card, CardEffect
from mindbug.engine.engine import MindbugGame
from mindbug.engine.core.consts import Phase, Trigger, EffectType, Keyword


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


# =============================================================================
# TESTS RÉGRESSION BUG-LIST README
# =============================================================================

def test_bug1_frenzy_defender_does_not_attack_twice(game):
    """
    Bug 1 : Défense avec une furie — la carte défenseuse ne doit pas attaquer 2 fois.
    Règle Mindbug : FRENZY ne se déclenche que pour l'attaquant, jamais pour le bloqueur.
    Si la carte défenseuse a FRENZY et survit, c'est son tour normal de jouer ensuite
    (pas une attaque automatique immédiate).
    """
    p1 = game.state.player1
    p2 = game.state.player2

    # P1 attaque avec une créature normale
    attacker = Card("a", "Attacker", 3)
    p1.board = [attacker]

    # P2 bloque avec une créature FRENZY (puissance sup. donc survive)
    frenzy_blocker = Card("f", "FrenzyBlocker", 5, keywords=[Keyword.FRENZY])
    dummy_target = Card("d", "Dummy", 1)  # Victime potentielle pour une 2ème attaque
    p2.board = [frenzy_blocker, dummy_target]

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # P1 attaque
    game.step("ATTACK", 0)
    # P2 bloque avec le FRENZY card
    game.step("BLOCK", 0)

    # Résultat : attacker (3) meurt face à frenzy_blocker (5)
    assert attacker in p1.discard
    assert frenzy_blocker in p2.board  # Survit

    # BUG CHECK : le FRENZY du bloqueur ne doit PAS avoir déclenché une 2ème attaque.
    # dummy_target doit être intact.
    assert dummy_target in p2.board

    # Le tour doit passer normalement à P2 (pas de résolution_choice forcée)
    assert game.state.active_player == p2
    assert game.state.phase == Phase.P2_MAIN


def test_bug2a_crapaud_bombe_tough_survives(game):
    """
    Bug 2a : Crapaud bombe ne doit pas tuer une créature Coriace (TOUGH) à pleine vie.
    L'effet DESTROY via ON_DEATH doit passer par destroy_card, qui respecte TOUGH.
    """
    p1 = game.state.player1
    p2 = game.state.player2

    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ANY", "zone": "BOARD", "count": 1, "select": "CHOICE_USER"})
    toad = Card("08", "Crapaud", 5, keywords=[Keyword.FRENZY],
                trigger=Trigger.ON_DEATH, effects=[effect])

    # Victime Coriace (TOUGH, 2 PV = bouclier intact)
    tough_victim = Card("t", "ToughVictim", 3, keywords=[Keyword.TOUGH])
    p1.board = [toad]
    p2.board = [tough_victim]

    # Le Crapaud bombe meurt
    game.combat_manager.apply_lethal_damage(toad, p1)

    # ON_DEATH déclenche -> Demande de sélection
    assert game.state.phase == Phase.RESOLUTION_CHOICE

    # Le joueur choisit de cibler tough_victim
    game.step("SELECT_OPP_BOARD", 0)

    # TOUGH doit avoir absorbé le coup : la carte reste en vie, juste marquée damaged
    assert tough_victim in p2.board
    assert tough_victim.is_damaged is True
    # Le mot-clé TOUGH est retiré lors du prochain update_board_states()
    game.update_board_states()
    assert Keyword.TOUGH not in tough_victim.keywords  # Bouclier consommé


def test_bug2b_crapaud_bombe_can_target_ally(game):
    """
    Bug 2b : L'effet du Crapaud bombe doit pouvoir cibler une carte alliée.
    group=ANY = owner.board + opp.board.
    """
    p1 = game.state.player1
    p2 = game.state.player2

    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ANY", "zone": "BOARD", "count": 1, "select": "CHOICE_USER"})
    toad = Card("08", "Crapaud", 5, trigger=Trigger.ON_DEATH, effects=[effect])

    ally = Card("a", "Ally", 2)  # Carte alliée à sacrifier
    p1.board = [toad, ally]
    p2.board = []  # Pas d'adversaires sur le plateau

    # Le Crapaud meurt
    game.combat_manager.apply_lethal_damage(toad, p1)

    # ON_DEATH déclenche -> doit permettre de sélectionner l'allié
    assert game.state.phase == Phase.RESOLUTION_CHOICE

    # Les candidats doivent inclure ally (seule carte sur le board)
    req = game.state.active_request
    assert ally in req.candidates

    # Le joueur sacrifice l'allié
    game.step("SELECT_BOARD", 0)
    assert ally in p1.discard


def test_bug2c_crapaud_bombe_no_target_no_trigger(game):
    """
    Bug 2c : Si aucune créature n'est sur le plateau (allié ou ennemi),
    l'effet du Crapaud bombe ne doit pas se déclencher (aucune cible valide).
    """
    p1 = game.state.player1
    p2 = game.state.player2

    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ANY", "zone": "BOARD", "count": 1, "select": "CHOICE_USER"})
    toad = Card("08", "Crapaud", 5, trigger=Trigger.ON_DEATH, effects=[effect])

    p1.board = [toad]
    p2.board = []  # Aucun ennemi

    # Le crapaud meurt — il est la seule créature, donc après sa mort le board est vide
    game.combat_manager.apply_lethal_damage(toad, p1)

    # Aucune cible -> l'effet ne doit PAS déclencher de sélection
    assert game.state.phase != Phase.RESOLUTION_CHOICE


def test_bug3_hunter_requin_toutou_works(game):
    """
    Bug 3 : Hunter (Chasseur) du Requin Toutou doit fonctionner après le fix Enum.

    Bug 3 : Hunter (Chasseur) du Requin Toutou doit fonctionner après le fix Enum.

    Ce test vérifie le combo complexe : la carte a un effet ON_ATTACK (qui demande une sélection)
    ET le mot-clé HUNTER. L'effet ON_ATTACK doit se résoudre en premier, tuer une cible,
    puis la phase de HUNTER doit s'activer pour choisir la cible de l'attaque parmi
    les survivants.
    """
    p1 = game.state.player1
    p2 = game.state.player2

    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ENEMIES", "zone": "BOARD", "count": 1, "select": "CHOICE_USER"},
                        condition={"stat": "POWER", "operator": "GTE", "value": 6})
    shark_dog = Card("22", "RequinToutou", 4, keywords=[Keyword.HUNTER],
                     trigger=Trigger.ON_ATTACK, effects=[effect])

    weak = Card("w", "Weak", 3)
    strong = Card("s", "Strong", 7)
    p1.board = [shark_dog]
    p2.board = [weak, strong]

    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # 1. Attaque -> ON_ATTACK trigger DESTROY sur >= 6
    game.step("ATTACK", 0)

    # ON_ATTACK déclenche la sélection (seule 'strong' est éligible >= 6)
    assert game.state.phase == Phase.RESOLUTION_CHOICE
    req = game.state.active_request
    assert strong in req.candidates
    assert weak not in req.candidates

    # Sélectionne strong -> elle est détruite
    game.step("SELECT_OPP_BOARD", 1)
    assert strong in p2.discard

    # Après l'effet, le flag hunter_pending déclenche le HUNTER
    assert game.state.phase == Phase.RESOLUTION_CHOICE
    assert game.state.active_request.reason == "HUNTER_TARGET"
    assert weak in game.state.active_request.candidates

    # On utilise resolve_selection_effect pour simuler le choix de la cible Hunter
    game.resolve_selection_effect(weak)

    # 4 Attaque vs 3 Defense -> Weak (3) meurt
    assert weak in p2.discard
    assert shark_dog in p1.board

    # Le tour passe à P2
    assert game.state.phase == Phase.P2_MAIN
    assert game.state.active_player == p2

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
