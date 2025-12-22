import pytest
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.models import Card, CardEffect
from mindbug_engine.core.consts import Phase, Trigger, EffectType, Keyword


# =============================================================================
# 01 - Dr Axolotl : Jouer : Gagnez 2PV.
# =============================================================================
def test_01_dr_axolotl(game):
    p1 = game.state.player1
    p1.hp = 1
    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OWNER"},
                        params={"stat": "HP", "amount": 2, "operation": "ADD"})
    card = Card("01", "Axolotl", 4, keywords=[
                "POISON"], trigger=Trigger.ON_PLAY, effects=[effect])

    p1.hand = [card]
    game.state.active_player_idx = 0
    game.step("PLAY", 0)
    assert p1.hp == 3


# =============================================================================
# 02 - Oursabeille : Ne peut pas être bloquée par <= 6.
# =============================================================================
def test_02_oursabeille(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.BAN, target={"group": "ENEMIES"},
                        condition={"stat": "POWER", "operator": "LTE", "value": 6}, params={"action": "BLOCK"})
    card = Card("02", "Ours", 8, trigger=Trigger.PASSIVE, effects=[effect])

    weak = Card("w", "Weak", 6)
    strong = Card("s", "Strong", 7)

    p1.board = [card]
    p2.board = [weak, strong]

    game.state.active_player_idx = 0
    game.step("ATTACK", 0)

    moves = game.get_legal_moves()
    # Weak (idx 0) ne peut pas bloquer, Strong (idx 1) le peut
    assert ("BLOCK", 0) not in moves
    assert ("BLOCK", 1) in moves


# =============================================================================
# 03 - Neuromouche : Jouer : Voler >= 6.
# =============================================================================
def test_03_neuromouche(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.STEAL,
                        target={"group": "ENEMIES", "zone": "BOARD",
                                "count": 1, "select": "CHOICE_USER"},
                        condition={"stat": "POWER", "operator": "GTE", "value": 6})
    card = Card("03", "Mouche", 4, trigger=Trigger.ON_PLAY, effects=[effect])

    small = Card("s", "Small", 5)
    big = Card("b", "Big", 6)
    p2.board = [small, big]
    p1.hand = [card]

    game.state.active_player_idx = 0
    game.step("PLAY", 0)

    # Doit demander une sélection sur Big uniquement
    moves = game.get_legal_moves()
    assert ("SELECT_OPP_BOARD", 0) not in moves  # Small
    assert ("SELECT_OPP_BOARD", 1) in moves  # Big

    game.step("SELECT_OPP_BOARD", 1)
    assert big in p1.board


# =============================================================================
# 04 - Reptireur d'élite : Attaque : Adv -1 PV.
# =============================================================================
def test_04_reptireur(game):
    p1, p2 = game.state.player1, game.state.player2
    p2.hp = 3
    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OPPONENT"},
                        params={"stat": "HP", "amount": 1, "operation": "SUB"})
    card = Card("04", "Reptireur", 1, keywords=[
                "SNEAKY"], trigger=Trigger.ON_ATTACK, effects=[effect])

    p1.board = [card]
    game.state.active_player_idx = 0
    game.step("ATTACK", 0)

    assert p2.hp == 2


# =============================================================================
# 05 - Dracompost : Jouer : Jouer carte défausse.
# =============================================================================
def test_05_dracompost(game):
    p1 = game.state.player1
    effect = CardEffect(EffectType.PLAY,
                        target={"group": "OWNER", "zone": "DISCARD", "count": 1, "select": "CHOICE_USER"})
    card = Card("05", "Dracompost", 3, keywords=[
                "HUNTER"], trigger=Trigger.ON_PLAY, effects=[effect])

    dead = Card("d", "Dead", 5)
    p1.discard = [dead]
    p1.hand = [card]

    game.state.active_player_idx = 0
    game.step("PLAY", 0)
    game.step("SELECT_DISCARD", 0)

    assert dead in p1.board


# =============================================================================
# 06 - Veuve noire : Adv ne peut pas résoudre d'effets Jouer.
# =============================================================================
def test_06_veuve_noire(game):
    p1, p2 = game.state.player1, game.state.player2

    # Veuve chez P1
    ban_effect = CardEffect(EffectType.BAN, target={"group": "OPPONENT"}, params={
                            "action": "TRIGGER_ON_PLAY"})
    veuve = Card("06", "Veuve", 2, keywords=[
                 "POISON"], trigger=Trigger.PASSIVE, effects=[ban_effect])
    p1.board = [veuve]

    # P2 joue une carte avec effet
    heal_effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OWNER"},
                             params={"stat": "HP", "amount": 10, "operation": "ADD"})
    healer = Card("h", "Healer", 1, trigger=Trigger.ON_PLAY,
                  effects=[heal_effect])
    p2.hand = [healer]

    # On force le tour à P2
    game.state.active_player_idx = 1
    game.update_board_states()  # Applique le passif de Veuve

    game.step("PLAY", 0)

    # L'effet ne doit PAS se déclencher
    assert p2.hp == 3  # PV initiaux, pas +10


# =============================================================================
# 07 - Pachypoulpe : Ennemis ne peuvent bloquer avec <= 4.
# =============================================================================
def test_07_pachypoulpe(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.BAN, target={"group": "ENEMIES"},
                        condition={"stat": "POWER", "operator": "LTE", "value": 4}, params={"action": "BLOCK"})
    card = Card("07", "Pachy", 7, keywords=[
                "TOUGH"], trigger=Trigger.PASSIVE, effects=[effect])

    weak = Card("w", "Weak", 4)
    strong = Card("s", "Strong", 5)
    p1.board = [card]
    p2.board = [weak, strong]

    game.state.active_player_idx = 0
    game.step("ATTACK", 0)

    moves = game.get_legal_moves()
    assert ("BLOCK", 0) not in moves
    assert ("BLOCK", 1) in moves


# =============================================================================
# 08 - Crapaud bombe : Détruit : Détruisez une créature.
# =============================================================================
def test_08_crapaud_bombe(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ANY", "zone": "BOARD", "count": 1, "select": "CHOICE_USER"})
    card = Card("08", "Crapaud", 5, keywords=[
                "FRENZY"], trigger=Trigger.ON_DEATH, effects=[effect])

    victim = Card("v", "Victim", 2)
    p1.board = [card]
    p2.board = [victim]

    # Simulation mort via combat (Attaque vs monstre 10)
    killer = Card("k", "Killer", 10)
    p2.board.append(killer)

    game.state.active_player_idx = 0
    game.step("ATTACK", 0)
    game.step("BLOCK", 1)  # Killer bloque Crapaud

    # Crapaud meurt -> Trigger
    assert game.state.phase == Phase.RESOLUTION_CHOICE
    game.step("SELECT_OPP_BOARD", 0)  # Détruit Victim

    assert victim in p2.discard


# =============================================================================
# 09 - Furet saboteur : Jouer : Adv défausse 2.
# =============================================================================
def test_09_furet_saboteur(game):
    p1, p2 = game.state.player1, game.state.player2
    # NOTE : Assurez-vous d'avoir ajouté "zone": "HAND" dans le JSON/Card setup si vous n'utilisez pas le loader
    effect = CardEffect(EffectType.DISCARD,
                        target={"group": "OPPONENT", "zone": "HAND", "count": 2, "select": "CHOICE_OPP"})
    card = Card("09", "Furet", 2, keywords=[
                "SNEAKY"], trigger=Trigger.ON_PLAY, effects=[effect])

    c1, c2, c3 = Card("1", "1", 1), Card("2", "2", 1), Card("3", "3", 1)
    p2.hand = [c1, c2, c3]
    p1.hand = [card]

    game.state.active_player_idx = 0
    game.step("PLAY", 0)

    # C'est à l'adversaire (P2) de choisir
    assert game.state.active_request.selector == p2

    # On sélectionne deux indices DIFFÉRENTS
    # (La main ne change pas tant que la sélection n'est pas validée)
    game.step("SELECT_HAND", 0)  # Choisit c1
    game.step("SELECT_HAND", 1)  # Choisit c2

    assert len(p2.hand) == 1
    assert len(p2.discard) == 2


# =============================================================================
# 10 - Giraffodile : Jouer : Piochez défausse.
# =============================================================================
def test_10_giraffodile(game):
    p1 = game.state.player1
    effect = CardEffect(EffectType.MOVE, target={"group": "OWNER", "zone": "DISCARD", "count": "ALL"},
                        params={"destination": "HAND"})
    card = Card("10", "Gira", 7, trigger=Trigger.ON_PLAY, effects=[effect])

    d1, d2 = Card("d1", "D1", 1), Card("d2", "D2", 1)
    p1.discard = [d1, d2]
    p1.hand = [card]

    game.state.active_player_idx = 0
    game.step("PLAY", 0)

    assert len(p1.hand) == 2  # Les 2 cartes récupérées
    assert len(p1.discard) == 0


# =============================================================================
# 11 - Goblin-Garou : +6 si mon tour.
# =============================================================================
def test_11_goblin_garou(game):
    p1 = game.state.player1
    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "SELF"}, condition={"context": "MY_TURN"},
                        params={"stat": "POWER", "amount": 6, "operation": "ADD"})
    card = Card("11", "Gob", 2, keywords=[
                "HUNTER"], trigger=Trigger.PASSIVE, effects=[effect])
    p1.board = [card]

    game.state.active_player_idx = 0  # Tour P1
    game.update_board_states()
    assert card.power == 8

    game.state.active_player_idx = 1  # Tour P2
    game.update_board_states()
    assert card.power == 2


# =============================================================================
# 12 - Gorillion : 10 Power vanilla.
# =============================================================================
def test_12_gorillion(game):
    card = Card("12", "Gorillion", 10)
    assert card.power == 10


# =============================================================================
# 13 - Pilleur de tombes : Jouer : Jouer carte défausse adverse.
# =============================================================================
def test_13_pilleur(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.PLAY,
                        target={"group": "OPPONENT", "zone": "DISCARD", "count": 1, "select": "CHOICE_USER"})
    card = Card("13", "Pilleur", 7, keywords=[
                "TOUGH"], trigger=Trigger.ON_PLAY, effects=[effect])

    dead = Card("d", "Dead", 5)
    p2.discard = [dead]
    p1.hand = [card]

    game.state.active_player_idx = 0
    game.step("PLAY", 0)
    game.step("SELECT_OPP_DISCARD", 0)

    assert dead in p1.board  # Vient chez moi


# =============================================================================
# 14 - Mamie Harpie : Détruit : Voler 2 <= 5.
# =============================================================================
def test_14_mamie_harpie(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.STEAL,
                        target={"group": "ENEMIES", "zone": "BOARD",
                                "count": 2, "select": "CHOICE_USER"},
                        condition={"stat": "POWER", "operator": "LTE", "value": 5})
    card = Card("14", "Mamie", 5, trigger=Trigger.ON_DEATH, effects=[effect])

    c1, c2, c3 = Card("1", "1", 3), Card("2", "2", 5), Card("3", "3", 6)
    p1.board = [card]
    p2.board = [c1, c2, c3]

    game.state.active_player_idx = 0
    game.combat_manager.apply_lethal_damage(card, p1)

    game.step("SELECT_OPP_BOARD", 0)  # c1
    game.step("SELECT_OPP_BOARD", 1)  # c2

    assert c1 in p1.board
    assert c2 in p1.board
    assert c3 in p2.board


# =============================================================================
# 15 - Kangousaurus Rex : Jouer : Détruire ennemis <= 4.
# =============================================================================
def test_15_kangou(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.DESTROY, target={"group": "ENEMIES", "select": "ALL"},
                        condition={"stat": "POWER", "operator": "LTE", "value": 4})
    card = Card("15", "Kangou", 7, trigger=Trigger.ON_PLAY, effects=[effect])

    weak1, weak2, strong = Card("w1", "1", 3), Card(
        "w2", "2", 4), Card("s", "3", 5)
    p2.board = [weak1, weak2, strong]
    p1.hand = [card]

    game.state.active_player_idx = 0
    game.step("PLAY", 0)

    assert weak1 in p2.discard
    assert weak2 in p2.discard
    assert strong in p2.board


# =============================================================================
# 16 - Abeille tueuse : Jouer : Adv -1 PV.
# =============================================================================
def test_16_abeille(game):
    p1, p2 = game.state.player1, game.state.player2
    p2.hp = 3
    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OPPONENT"},
                        params={"stat": "HP", "amount": 1, "operation": "SUB"})
    card = Card("16", "Abeille", 5, keywords=[
                "HUNTER"], trigger=Trigger.ON_PLAY, effects=[effect])

    p1.hand = [card]
    game.state.active_player_idx = 0
    game.step("PLAY", 0)
    assert p2.hp == 2


# =============================================================================
# 17 - Yéti solitaire : +5/Frenzy si seul.
# =============================================================================
def test_17_yeti(game):
    p1 = game.state.player1
    eff1 = CardEffect(EffectType.MODIFY_STAT, target={"group": "SELF"}, condition={"context": "IS_ALONE"},
                      params={"stat": "POWER", "amount": 5, "operation": "ADD"})
    eff2 = CardEffect(EffectType.ADD_KEYWORD, target={"group": "SELF"}, condition={"context": "IS_ALONE"},
                      params={"keywords": ["FRENZY"]})
    card = Card("17", "Yeti", 5, keywords=[
                "TOUGH"], trigger=Trigger.PASSIVE, effects=[eff1, eff2])

    p1.board = [card]
    game.update_board_states()
    assert card.power == 10
    assert Keyword.FRENZY in card.keywords

    buddy = Card("b", "Buddy", 1)
    p1.board.append(buddy)
    game.update_board_states()
    assert card.power == 5
    assert Keyword.FRENZY not in card.keywords


# =============================================================================
# 18 - Gladiataure : Vanilla 9 Frenzy.
# =============================================================================
def test_18_gladiataure(game):
    card = Card("18", "Glad", 9, keywords=["FRENZY"])
    assert Keyword.FRENZY in card.keywords
    assert card.power == 9


# =============================================================================
# 19 - Sirène mystérieuse : Copie PV adversaire.
# =============================================================================
def test_19_sirene(game):
    p1, p2 = game.state.player1, game.state.player2
    p1.hp = 1
    p2.hp = 3
    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OWNER"},
                        params={"stat": "HP", "operation": "COPY", "source": "OPPONENT"})
    card = Card("19", "Sirene", 7, trigger=Trigger.ON_PLAY, effects=[effect])

    p1.hand = [card]
    game.state.active_player_idx = 0
    game.step("PLAY", 0)
    assert p1.hp == 3


# =============================================================================
# 20 - Scorpion blindé : Tough + Poison.
# =============================================================================
def test_20_scorpion(game):
    card = Card("20", "Scorp", 2, keywords=["TOUGH", "POISON"])
    assert Keyword.TOUGH in card.keywords
    assert Keyword.POISON in card.keywords


# =============================================================================
# 21 - Rhino Tortue : Frenzy + Tough.
# =============================================================================
def test_21_rhino(game):
    card = Card("21", "Rhino", 8, keywords=["FRENZY", "TOUGH"])
    assert Keyword.FRENZY in card.keywords
    assert Keyword.TOUGH in card.keywords


# =============================================================================
# 22 - Requin Toutou : Attaque : Détruire >= 6.
# =============================================================================
def test_22_requin_toutou(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ENEMIES", "zone": "BOARD",
                                "count": 1, "select": "CHOICE_USER"},
                        condition={"stat": "POWER", "operator": "GTE", "value": 6})
    card = Card("22", "Toutou", 4, keywords=[
                "HUNTER"], trigger=Trigger.ON_ATTACK, effects=[effect])

    target = Card("t", "Target", 6)
    p1.board = [card]
    p2.board = [target]

    game.state.active_player_idx = 0
    game.step("ATTACK", 0)
    # Trigger -> Selection
    game.step("SELECT_OPP_BOARD", 0)

    assert target in p2.discard


# =============================================================================
# 23 - Requin Crabe : Copie Mots-Clés.
# =============================================================================
def test_23_requin_crabe(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.COPY_KEYWORDS, target={
                        "group": "SELF"}, params={"source": "ENEMIES"})
    card = Card("23", "Crabe", 5, trigger=Trigger.PASSIVE, effects=[effect])

    enemy = Card("e", "Enemy", 5, keywords=["POISON", "FRENZY"])
    p1.board = [card]
    p2.board = [enemy]

    game.update_board_states()
    assert Keyword.POISON in card.keywords
    assert Keyword.FRENZY in card.keywords

    # Dynamique : Ennemi meurt
    p2.board = []
    game.update_board_states()
    assert Keyword.POISON not in card.keywords


# =============================================================================
# 24 - Scarabouclier : Autres alliés +1.
# =============================================================================
def test_24_scarabouclier(game):
    p1 = game.state.player1
    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "ALL_OTHER_ALLIES"},
                        params={"stat": "POWER", "amount": 1, "operation": "ADD"})
    scara = Card("24", "Scara", 4, keywords=[
                 "TOUGH"], trigger=Trigger.PASSIVE, effects=[effect])

    other = Card("o", "Other", 2)
    p1.board = [scara, other]

    game.update_board_states()
    assert scara.power == 4  # Pas self-buff
    assert other.power == 3


# =============================================================================
# 25 - Hydrescargot : Attaque : Si moins alliés -> Détruire.
# =============================================================================
def test_25_hydrescargot(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.DESTROY, target={"group": "ANY", "count": 1, "select": "CHOICE_USER"},
                        condition={"context": "FEWER_ALLIES"})
    card = Card("25", "Hydra", 9, trigger=Trigger.ON_ATTACK, effects=[effect])

    p1.board = [card]
    p2.board = [Card("1", "1", 1), Card("2", "2", 1)
                ]  # 1 vs 2 -> Condition Vraie

    game.state.active_player_idx = 0
    game.step("ATTACK", 0)

    # Doit demander sélection
    assert game.state.phase == Phase.RESOLUTION_CHOICE
    game.step("SELECT_OPP_BOARD", 0)
    assert len(p2.board) == 1


# =============================================================================
# 26 - Lanceur d'escargots : Autres <= 4 gagnent Poison/Hunter.
# =============================================================================
def test_26_lanceur(game):
    p1 = game.state.player1
    effect = CardEffect(EffectType.ADD_KEYWORD, target={"group": "ALL_OTHER_ALLIES"},
                        condition={"stat": "POWER",
                                   "operator": "LTE", "value": 4},
                        params={"keywords": ["HUNTER", "POISON"]})
    lanceur = Card("26", "Lanceur", 1, keywords=[
                   "POISON"], trigger=Trigger.PASSIVE, effects=[effect])

    weak = Card("w", "Weak", 4)
    p1.board = [lanceur, weak]

    game.update_board_states()
    assert Keyword.HUNTER not in lanceur.keywords  # Pas self-buff
    assert Keyword.HUNTER in weak.keywords


# =============================================================================
# 27 - Arachnhibou : Vanilla Sneaky Poison.
# =============================================================================
def test_27_arachnhibou(game):
    card = Card("27", "Ara", 3, keywords=["SNEAKY", "POISON"])
    assert Keyword.SNEAKY in card.keywords
    assert Keyword.POISON in card.keywords


# =============================================================================
# 28 - Baril étrange : Détruit : Voler 2 main hasard.
# =============================================================================
def test_28_baril(game):
    p1, p2 = game.state.player1, game.state.player2

    # SETUP
    # On vide la main de P1 pour que le compte final soit exact (0 + 2 = 2)
    p1.hand = []

    effect = CardEffect(EffectType.STEAL, target={
                        "group": "OPPONENT", "zone": "HAND", "count": 2, "select": "RANDOM"})
    card = Card("28", "Baril", 6, trigger=Trigger.ON_DEATH, effects=[effect])

    p2.hand = [Card("1", "1", 1), Card("2", "2", 1), Card("3", "3", 1)]
    p1.board = [card]

    game.state.active_player_idx = 0
    game.combat_manager.apply_lethal_damage(card, p1)

    assert len(p2.hand) == 1
    assert len(p1.hand) == 2


# =============================================================================
# 29 - Tigrécureuil : Jouer : Détruire >= 7.
# =============================================================================
def test_29_tigrecureuil(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ANY", "zone": "BOARD",
                                "count": 1, "select": "CHOICE_USER"},
                        condition={"stat": "POWER", "operator": "GTE", "value": 7})
    card = Card("29", "Tigre", 3, keywords=[
                "SNEAKY"], trigger=Trigger.ON_PLAY, effects=[effect])

    target = Card("t", "Target", 7)
    p2.board = [target]
    p1.hand = [card]

    game.state.active_player_idx = 0
    game.step("PLAY", 0)
    game.step("SELECT_OPP_BOARD", 0)

    assert target in p2.discard


# =============================================================================
# 30 - Turboustique : Attaque : Set PV 1.
# =============================================================================
def test_30_turboustique(game):
    p1, p2 = game.state.player1, game.state.player2
    p2.hp = 3
    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OPPONENT"},
                        params={"stat": "HP", "operation": "SET", "amount": 1})
    card = Card("30", "Turbo", 4, trigger=Trigger.ON_ATTACK, effects=[effect])

    p1.board = [card]
    game.state.active_player_idx = 0
    game.step("ATTACK", 0)
    assert p2.hp == 1


# =============================================================================
# 31 - Huissiéléphant : Attaque : Défausse 1.
# =============================================================================
def test_31_huisselephant(game):
    p1, p2 = game.state.player1, game.state.player2
    effect = CardEffect(EffectType.DISCARD, target={
                        "group": "OPPONENT", "zone": "HAND", "count": 1, "select": "RANDOM"})
    card = Card("31", "Huissier", 8,
                trigger=Trigger.ON_ATTACK, effects=[effect])

    p2.hand = [Card("1", "1", 1)]
    p1.board = [card]

    game.state.active_player_idx = 0
    game.step("ATTACK", 0)
    assert len(p2.hand) == 0


# =============================================================================
# 32 - Oursins hurleurs : Allies +2 Mon tour.
# =============================================================================
def test_32_oursins(game):
    p1 = game.state.player1
    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "ALLIES"}, condition={"context": "MY_TURN"},
                        params={"stat": "POWER", "amount": 2, "operation": "ADD"})
    card = Card("32", "Oursins", 5, keywords=[
                "HUNTER"], trigger=Trigger.PASSIVE, effects=[effect])

    ally = Card("a", "Ally", 1)
    p1.board = [card, ally]

    game.state.active_player_idx = 0  # P1
    game.update_board_states()
    assert card.power == 7
    assert ally.power == 3

    game.state.active_player_idx = 1  # P2
    game.update_board_states()
    assert card.power == 5
    assert ally.power == 1
