import pytest
import json
import os
from mindbug_engine.loaders import CardLoader
from mindbug_engine.engine import MindbugGame
from settings import SettingsManager
import settings as settings_module

# --- FIXTURE : CRÉATION D'UN FAUX FICHIER DE CARTES ---
@pytest.fixture
def mock_cards_json(tmp_path):
    data = [
        # Carte du Set A
        {
            "id": "card_a", "name": "Card A", "power": 5, "count": 1, 
            "set": "SET_A", "keywords": [], "image": None
        },
        # Carte du Set B
        {
            "id": "card_b", "name": "Card B", "power": 3, "count": 1, 
            "set": "SET_B", "keywords": [], "image": None
        },
        # Carte sans Set (doit être "FIRST_CONTACT" par défaut)
        {
            "id": "card_default", "name": "Card Default", "power": 1, "count": 1, 
            "keywords": [], "image": None
        }
    ]
    f_path = tmp_path / "fake_cards.json"
    f_path.write_text(json.dumps(data), encoding="utf-8")
    return str(f_path)

# --- TEST 1 : AUTO-DÉCOUVERTE ---
def test_discovery_sets(mock_cards_json):
    detected_sets = CardLoader.get_available_sets(mock_cards_json)
    assert "SET_A" in detected_sets
    assert "SET_B" in detected_sets
    assert "FIRST_CONTACT" in detected_sets
    assert len(detected_sets) == 3

# --- TEST 2 : FILTRAGE MOTEUR (ENGINE) ---
def test_engine_filtering(mock_cards_json):
    """Vérifie que le moteur ne charge QUE les cartes des sets demandés."""
    
    # Cas A : On veut seulement le SET_A
    game_a = MindbugGame(deck_path=mock_cards_json, active_sets=["SET_A"])
    
    assert len(game_a.all_cards_ref) == 1
    assert game_a.all_cards_ref[0].set == "SET_A"
    assert game_a.all_cards_ref[0].name == "Card A"

    # Cas B : On veut SET_A et SET_B
    game_ab = MindbugGame(deck_path=mock_cards_json, active_sets=["SET_A", "SET_B"])
    assert len(game_ab.all_cards_ref) == 2
    sets_loaded = {c.set for c in game_ab.all_cards_ref}
    assert "SET_A" in sets_loaded
    assert "SET_B" in sets_loaded
    assert "FIRST_CONTACT" not in sets_loaded

    # Cas C : On ne donne rien (None ou liste vide) -> Doit tout charger par sécurité
    game_all = MindbugGame(deck_path=mock_cards_json, active_sets=[])
    assert len(game_all.all_cards_ref) == 3

# --- TEST 3 : SAUVEGARDE DES PARAMÈTRES ---
def test_settings_save_load(tmp_path, monkeypatch):
    fake_settings_file = tmp_path / "test_settings.json"
    monkeypatch.setattr(settings_module, "PATH_SETTINGS", str(fake_settings_file))
    
    manager = SettingsManager()
    test_sets = ["FUTURE_WAR", "DINO_CRISIS"]
    manager.active_sets = test_sets
    manager.save()
    
    assert fake_settings_file.exists()
    with open(fake_settings_file, "r") as f:
        saved_data = json.load(f)
        assert saved_data["active_sets"] == test_sets
        
    new_manager = SettingsManager()
    assert new_manager.active_sets == test_sets
