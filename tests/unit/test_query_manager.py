from types import SimpleNamespace
from mindbug_engine.managers.query_manager import QueryManager
from mindbug_engine.core.models import SelectionRequest
from mindbug_engine.core.consts import Phase


def make_game():
    game = SimpleNamespace()
    state = SimpleNamespace()
    state.active_request = None
    state.phase = None
    game.state = state
    return game


def test_start_and_resolve_selection_with_callback():
    game = make_game()
    qm = QueryManager(game)

    called = {"done": False, "sel": None}

    def cb(selection):
        called["done"] = True
        called["sel"] = list(selection)

    candidates = ["a", "b", "c"]
    qm.start_selection_request(
        candidates, "TEST", 2, selector=SimpleNamespace(name="S"), callback=cb)

    assert isinstance(game.state.active_request, SelectionRequest)
    assert game.state.phase == Phase.RESOLUTION_CHOICE

    # Partial selection
    done = qm.resolve_selection(["a"])  # should be incomplete
    assert done is False
    assert not called["done"]

    # Complete selection
    done = qm.resolve_selection(["b"])  # now completes to 2
    assert done is True
    assert called["done"] is True
    assert called["sel"] == ["a", "b"]


def test_resolve_invalid_selection_returns_false_and_logs(monkeypatch):
    game = make_game()
    qm = QueryManager(game)

    # start request
    qm.start_selection_request(
        [1, 2], "X", 1, selector=SimpleNamespace(name="S"), callback=None)

    # invalid item
    res = qm.resolve_selection([3])
    assert res is False
