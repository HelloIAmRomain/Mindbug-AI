from mindbug_engine.core.models import Card, CardEffect
from mindbug_engine.core.consts import Phase


def test_power_boost_my_turn(game):
    """Teste le passif : +6 si c'est mon tour (ex: Goblin-Garou)."""
    effect = CardEffect(
        effect_type="MODIFY_STAT",
        target={"group": "SELF"},
        condition={"context": "MY_TURN"},
        params={"stat": "POWER", "amount": 6, "operation": "ADD"}
    )

    goblin = Card("g", "Gob", 2, trigger="PASSIVE", effects=[effect])
    game.state.player1.board = [goblin]

    # Cas 1 : C'est le tour de P1
    game.state.active_player_idx = 0
    game.state.phase = Phase.P1_MAIN

    # V3 : On met à jour les états
    game.update_board_states()
    assert goblin.power == 8  # 2 + 6

    # Cas 2 : C'est le tour de P2
    game.state.active_player_idx = 1
    game.state.phase = Phase.P2_MAIN

    game.update_board_states()
    assert goblin.power == 2  # Bonus inactif


def test_power_debuff_enemies(game):
    """Teste le passif : -1 aux ennemis (ex: Oursin)."""
    effect = CardEffect(
        effect_type="MODIFY_STAT",
        target={"group": "ENEMIES"},
        params={"stat": "POWER", "amount": 1, "operation": "SUB"}
    )

    oursin = Card("o", "Urchin", 5, trigger="PASSIVE", effects=[effect])
    game.state.player1.board = [oursin]

    enemy = Card("e", "Enemy", 3)
    game.state.player2.board = [enemy]

    game.update_board_states()
    assert enemy.power == 2  # 3 - 1