import pytest
import json
from unittest.mock import patch, mock_open
from mindbug_engine.core.models import Card, Player, CardEffect
from mindbug_engine.infrastructure.card_loader import CardLoader


def test_player_initialization():
    p = Player("TestUser")
    assert p.hp == 3
    assert p.mindbugs == 2


def test_card_copy_method():
    # Setup V2
    eff = CardEffect("STEAL", target={"group": "OPPONENT"}, params={"count": 1})
    original = Card(id="01", name="Rat", power=2, keywords=["HUNTER"], effects=[eff])
    original.is_damaged = True

    copy = original.copy()

    assert copy.name == "Rat"
    assert copy.is_damaged is True
    assert len(copy.effects) == 1
    assert copy.effects[0].type == "STEAL"

    # Indépendance
    copy.effects[0].params["count"] = 5
    assert original.effects[0].params["count"] == 1


def test_loader_parses_effects():
    fake_json = json.dumps([{
        "id": "c1", "name": "Mage", "power": 1, "count": 1,
        "effects": [{"type": "MODIFY_STAT", "target": {"group": "OPPONENT"}}]
    }])

    with patch("builtins.open", mock_open(read_data=fake_json)):
        with patch("os.path.exists", return_value=True):
            # FIX : Utilisation du nouveau nom de méthode
            deck = CardLoader.load_from_json("dummy.json")

            assert len(deck) == 1
            card = deck[0]
            assert len(card.effects) == 1
            assert isinstance(card.effects[0], CardEffect)
            assert card.effects[0].type == "MODIFY_STAT"