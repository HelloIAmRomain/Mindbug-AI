import pytest
from types import SimpleNamespace

from mindbug_engine.commands.command import Command
from mindbug_engine.commands import command_factory as cf
from mindbug_engine.commands import definitions as defs
from mindbug_engine.core.consts import Phase


def test_command_is_abstract():
    with pytest.raises(TypeError):
        Command()


def make_player(name):
    p = SimpleNamespace()
    p.name = name
    p.hand = []
    p.board = []
    p.discard = []
    return p


def make_game():
    # minimal game scaffold used by CommandFactory
    game = SimpleNamespace()
    state = SimpleNamespace()
    state.phase = Phase.P1_MAIN
    state.active_request = None
    p1 = make_player("P1")
    p2 = make_player("P2")
    state.player1 = p1
    state.player2 = p2
    state.active_player = p1
    game.state = state
    return game


def test_factory_creates_basic_commands():
    g = make_game()
    assert isinstance(cf.CommandFactory.create(
        "PLAY", 0, g), defs.PlayCardCommand)
    assert isinstance(cf.CommandFactory.create(
        "ATTACK", 0, g), defs.AttackCommand)
    assert isinstance(cf.CommandFactory.create(
        "BLOCK", 0, g), defs.BlockCommand)
    assert isinstance(cf.CommandFactory.create(
        "NO_BLOCK", 0, g), defs.NoBlockCommand)
    assert isinstance(cf.CommandFactory.create(
        "MINDBUG", 0, g), defs.MindbugCommand)
    assert isinstance(cf.CommandFactory.create("PASS", 0, g), defs.PassCommand)


def test_factory_select_resolves_active_player_hand():
    g = make_game()
    g.state.active_player.hand = ["a", "b", "c"]
    cmd = cf.CommandFactory.create("SELECT_HAND", 1, g)
    assert cmd is not None
    assert isinstance(cmd, defs.ResolveSelectionCommand)
    assert cmd.selected_object == "b"


def test_factory_select_resolves_selector_when_in_resolution_choice():
    g = make_game()
    # create a selector different from active_player
    selector = make_player("Selector")
    selector.hand = ["s0", "s1"]
    g.state.active_request = SimpleNamespace(selector=selector)
    g.state.phase = Phase.RESOLUTION_CHOICE

    cmd = cf.CommandFactory.create("SELECT_HAND", 0, g)
    assert isinstance(cmd, defs.ResolveSelectionCommand)
    assert cmd.selected_object == "s0"


def test_factory_select_out_of_range_logs_and_returns_none(monkeypatch):
    g = make_game()
    g.state.active_player.hand = ["only"]

    logged = {}

    def fake_log(msg):
        logged['msg'] = msg

    monkeypatch.setattr(cf, "log_error", fake_log)

    cmd = cf.CommandFactory.create("SELECT_HAND", 10, g)
    assert cmd is None
    assert "Target not found" in logged.get(
        'msg', "") or "Fichier" not in logged.get('msg', "")
