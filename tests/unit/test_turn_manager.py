from types import SimpleNamespace
from mindbug_engine.managers.turn_manager import TurnManager
from mindbug_engine.core.consts import Phase
from mindbug_engine.core.models import Player, Card


class FakeState:
    def __init__(self):
        self.player1 = Player("P1")
        self.player2 = Player("P2")
        self.active_player_idx = 0
        self.turn_count = 0
        self.phase = None
        self.deck = []
        self.winner = None

    @property
    def active_player(self):
        return self.player1 if self.active_player_idx == 0 else self.player2


def make_game_with_state():
    game = SimpleNamespace()
    state = FakeState()
    game.state = state
    return game, state


def test_start_turn_sets_initial_phase_and_turn_count():
    game, state = make_game_with_state()
    tm = TurnManager(game)
    tm.start_turn()
    assert state.turn_count == 1
    assert state.phase == Phase.P1_MAIN


def test_switch_active_player_toggles_index_and_active_player():
    game, state = make_game_with_state()
    tm = TurnManager(game)
    old = state.active_player.name
    tm.switch_active_player()
    assert state.active_player_idx == 1
    assert state.active_player.name != old


def test_refill_hand_draws_up_to_five_from_deck():
    game, state = make_game_with_state()
    tm = TurnManager(game)

    player = state.player1
    player.hand = []

    player.deck = [Card("c1", "C1", 1), Card(
        "c2", "C2", 1), Card("c3", "C3", 1)]

    tm.refill_hand(player)

    assert len(player.hand) == 3
    assert len(player.deck) == 0


def test_end_turn_refills_switches_player_and_updates_phase_and_turncount():
    game, state = make_game_with_state()
    tm = TurnManager(game)

    state.player1.deck = [Card(f"c1_{i}", f"C{i}", 1) for i in range(5)]
    state.player2.deck = [Card(f"c2_{i}", f"C{i}", 1) for i in range(5)]

    state.player1.hand = []
    state.player2.hand = []
    state.active_player_idx = 0
    state.turn_count = 1

    tm.end_turn()
    # after end_turn, active player toggled
    assert state.active_player_idx == 1
    assert state.phase in (Phase.P1_MAIN, Phase.P2_MAIN)
    assert state.turn_count == 2

    # Vérif : les mains ont été remplies
    assert len(state.player1.hand) == 5
    assert len(state.player2.hand) == 5


def test_check_win_condition_sets_winner_and_game_over():
    game, state = make_game_with_state()
    tm = TurnManager(game)
    state.player1.hp = 0
    state.player2.hp = 3
    tm.check_win_condition()
    assert state.winner == state.player2
    assert state.phase == Phase.GAME_OVER
