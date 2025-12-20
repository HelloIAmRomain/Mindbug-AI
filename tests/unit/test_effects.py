import pytest
from mindbug_engine.core.models import CardEffect
from mindbug_engine.core.consts import Phase, EffectType, Trigger


# Utilisation de game_empty pour éviter les interférences avec le setup automatique
def test_effect_modify_stat_heal(game_empty, create_card):
    game = game_empty
    p1 = game.state.player1
    p1.hp = 1

    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OWNER"},
                        params={"stat": "HP", "amount": 2, "operation": "ADD"})

    # On précise le trigger car certains effets dépendent du contexte
    card = create_card(name="Healer", effects=[effect], trigger=Trigger.ON_PLAY)

    # CORRECTION : La carte doit être quelque part (ici jouée depuis la main ou arrivant sur le board)
    p1.board.append(card)

    game.effect_manager.apply_effect(card, p1, game.state.player2)
    assert p1.hp == 3


def test_effect_modify_stat_damage(game_empty, create_card):
    game = game_empty
    p1 = game.state.player1
    p2 = game.state.player2

    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OPPONENT"},
                        params={"stat": "HP", "amount": 1, "operation": "SUB"})
    card = create_card(name="Sniper", effects=[effect])

    # CORRECTION : La carte doit être sur le plateau
    p1.board = [card]

    game.effect_manager.apply_effect(card, p1, p2)
    assert p2.hp == 2


def test_effect_modify_stat_set(game_empty, create_card):
    game = game_empty
    p1 = game.state.player1
    p2 = game.state.player2

    effect = CardEffect(EffectType.MODIFY_STAT, target={"group": "OPPONENT"},
                        params={"stat": "HP", "amount": 1, "operation": "SET"})
    card = create_card(name="Mosquito", effects=[effect])

    # CORRECTION
    p1.board = [card]

    game.effect_manager.apply_effect(card, p1, p2)
    assert p2.hp == 1


def test_effect_destroy_target_choice(game_empty, create_card):
    game = game_empty
    p1 = game.state.player1
    p2 = game.state.player2

    victim = create_card(name="Victim", power=5)
    p2.board = [victim]

    effect = CardEffect(EffectType.DESTROY,
                        target={"group": "ANY", "zone": "BOARD", "count": 1, "select": "CHOICE_USER"})
    bomb = create_card(name="Bomb", effects=[effect])

    # CORRECTION
    p1.board = [bomb]

    game.state.active_player_idx = 0
    game.effect_manager.apply_effect(bomb, p1, p2)

    assert game.state.phase == Phase.RESOLUTION_CHOICE

    # On simule la résolution du choix
    game.resolve_selection_effect(victim)
    assert victim in p2.discard


def test_effect_destroy_all_conditional(game_empty, create_card):
    game = game_empty
    p1 = game.state.player1
    p2 = game.state.player2

    weak = create_card(name="Weak", power=3)
    strong = create_card(name="Strong", power=8)
    p2.board = [weak, strong]

    effect = CardEffect(EffectType.DESTROY, target={"group": "ENEMIES", "select": "ALL"},
                        condition={"stat": "POWER", "operator": "LTE", "value": 4})
    rex = create_card(name="Rex", effects=[effect])

    # CORRECTION
    p1.board = [rex]

    game.effect_manager.apply_effect(rex, p1, p2)

    assert weak in p2.discard
    assert strong in p2.board


def test_effect_steal_board(game_empty, create_card):
    game = game_empty
    p1 = game.state.player1
    p2 = game.state.player2

    target = create_card(name="Target", power=8)
    p2.board = [target]

    effect = CardEffect(EffectType.STEAL,
                        target={"group": "ENEMIES", "zone": "BOARD", "count": 1, "select": "CHOICE_USER"},
                        condition={"stat": "POWER", "operator": "GTE", "value": 6})
    fly = create_card(name="Fly", effects=[effect])

    # CORRECTION : La mouche est à P1
    p1.board = [fly]

    game.effect_manager.apply_effect(fly, p1, p2)

    game.resolve_selection_effect(target)
    assert target in p1.board


def test_effect_play_from_discard(game_empty, create_card):
    game = game_empty
    p1 = game.state.player1

    dead = create_card(name="Dead", power=10)
    p1.discard = [dead]

    effect = CardEffect(EffectType.PLAY,
                        target={"group": "OWNER", "zone": "DISCARD", "count": 1, "select": "CHOICE_USER"})
    draco = create_card(name="Draco", effects=[effect])

    # CORRECTION
    p1.board = [draco]

    game.effect_manager.apply_effect(draco, p1, game.state.player2)
    game.resolve_selection_effect(dead)

    assert dead in p1.board


def test_effect_discard_random(game_empty, create_card):
    game = game_empty
    p1 = game.state.player1
    p2 = game.state.player2

    c1 = create_card(name="C1")
    c2 = create_card(name="C2")
    p2.hand = [c1, c2]
    game.state.deck = []

    effect = CardEffect(
        EffectType.DISCARD,
        target={"group": "OPPONENT", "zone": "HAND", "count": 1, "select": "RANDOM"}
    )

    elephant = create_card(name="Elephant", effects=[effect])
    p1.board = [elephant]

    game.effect_manager.apply_effect(elephant, p1, p2)

    # 2 cartes - 1 défaussée = 1 restante
    assert len(p2.hand) == 1
    assert len(p2.discard) == 1