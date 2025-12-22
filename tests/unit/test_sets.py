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
    """Crée un fichier JSON temporaire de cartes."""
    data = []
    # On génère 20 cartes pour passer la validation du DeckFactory
    for i in range(20):
        s = "SET_A" if i < 10 else "SET_B"
        data.append({
            "id": f"card_{i}", "name": f"Card {i}", "power": 5,
            "copies": 1, "set": s, "keywords": [], "effects": []
        })

    f_path = tmp_path / "fake_cards.json"
    f_path.write_text(json.dumps(data), encoding="utf-8")
    return str(f_path)


def test_discovery_sets(mock_cards_json):
    cards = CardLoader.load_from_json(mock_cards_json)
    detected_sets = {c.set for c in cards}
    assert "SET_A" in detected_sets
    assert "SET_B" in detected_sets


def test_engine_filtering(mock_cards_json):
    """Vérifie le filtrage via la config injectée."""

    # On patche la référence dans le module engine directement
    with patch("mindbug_engine.engine.PATH_DATA", mock_cards_json):
        # Cas A : Set A uniquement
        cfg_a = MockConfig()
        cfg_a.active_sets = ["SET_A"]
        game_a = MindbugGame(config=cfg_a)

        # On doit avoir filtré pour ne garder que les 10 cartes du SET_A
        assert len(game_a.state.all_cards_ref) == 10
        assert game_a.state.all_cards_ref[0].set == "SET_A"

        # Cas B : Plusieurs sets
        cfg_ab = MockConfig()
        cfg_ab.active_sets = ["SET_A", "SET_B"]
        game_ab = MindbugGame(config=cfg_ab)
        assert len(game_ab.state.all_cards_ref) == 20
