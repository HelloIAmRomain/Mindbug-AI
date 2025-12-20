import pytest
import json
from unittest.mock import patch
from mindbug_engine.infrastructure.card_loader import CardLoader
from mindbug_engine.engine import MindbugGame
from mindbug_engine.core.consts import Difficulty


class MockConfig:
    def __init__(self):
        self.debug_mode = False
        self.game_mode = "HOTSEAT"
        self.ai_difficulty = Difficulty.MEDIUM
        self.active_sets = ["FIRST_CONTACT"]


@pytest.fixture
def mock_cards_json(tmp_path):
    data = []
    # On crée 20 cartes pour que DeckFactory soit content
    for i in range(20):
        s = "SET_A" if i < 10 else "SET_B"
        data.append({"id": f"c{i}", "name": f"Card {i}", "power": 1, "copies": 1, "set": s, "effects": []})

    f_path = tmp_path / "fake_cards.json"
    f_path.write_text(json.dumps(data), encoding="utf-8")
    return str(f_path)


def test_discovery_sets(mock_cards_json):
    cards = CardLoader.load_from_json(mock_cards_json)
    detected = {c.set for c in cards}
    assert "SET_A" in detected
    assert "SET_B" in detected


def test_engine_filtering(mock_cards_json):
    # On patch 'constants.PATH_DATA' car engine.py fait 'from constants import PATH_DATA'
    with patch("constants.PATH_DATA", mock_cards_json):
        cfg = MockConfig()
        cfg.active_sets = ["SET_A"]

        game = MindbugGame(config=cfg)

        # On doit avoir filtré pour ne garder que les 10 cartes du SET_A
        assert len(game.state.all_cards_ref) == 10
        assert game.state.all_cards_ref[0].set == "SET_A"