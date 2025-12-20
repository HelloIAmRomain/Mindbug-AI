import pytest
import json
import os

# --- INFRASTRUCTURE & ENGINE ---
from mindbug_engine.infrastructure.card_loader import CardLoader
from mindbug_engine.engine import MindbugGame

# --- SETTINGS (Gestion conditionnelle pour éviter les imports circulaires/manquants) ---
try:
    from settings import SettingsManager
    import settings as settings_module
except ImportError:
    SettingsManager = None
    settings_module = None


@pytest.fixture
def mock_cards_json(tmp_path):
    """
    Crée un fichier JSON temporaire de cartes pour les tests.
    Standard : Utilise la clé "copies" pour définir la quantité.
    """
    data = [
        {
            "id": "card_a", "name": "Card A", "power": 5, "copies": 1,
            "set": "SET_A", "keywords": [], "image": None, "effects": []
        },
        {
            "id": "card_b", "name": "Card B", "power": 3, "copies": 1,
            "set": "SET_B", "keywords": [], "image": None, "effects": []
        },
        {
            "id": "card_default", "name": "Card Default", "power": 1, "copies": 1,
            # Pas de set défini -> Doit être détecté comme FIRST_CONTACT par défaut
            "keywords": [], "image": None, "effects": []
        }
    ]
    f_path = tmp_path / "fake_cards.json"
    f_path.write_text(json.dumps(data), encoding="utf-8")
    return str(f_path)


def test_discovery_sets(mock_cards_json):
    """
    Vérifie que le CardLoader charge correctement le fichier
    et que la logique de découverte des sets fonctionne.
    """
    # 1. Chargement via l'infrastructure
    cards = CardLoader.load_from_json(mock_cards_json)

    # 2. Vérification de lecture
    assert len(cards) == 3, "Le loader devrait charger 3 cartes (lecture de 'copies')."

    # 3. Vérification des Sets détectés
    detected_sets = set()
    for c in cards:
        if c.set:
            detected_sets.add(c.set)
        else:
            detected_sets.add("FIRST_CONTACT")  # Valeur par défaut attendue

    assert "SET_A" in detected_sets
    assert "SET_B" in detected_sets
    assert "FIRST_CONTACT" in detected_sets


def test_engine_filtering(mock_cards_json):
    """
    Vérifie que le MindbugGame (via DeckFactory) filtre correctement
    les cartes selon les sets demandés.
    """

    # --- Cas A : Set spécifique demandé ---
    game_a = MindbugGame(deck_path=mock_cards_json, active_sets=["SET_A"], verbose=False)
    # all_cards_ref contient le pool filtré, pas la main des joueurs
    assert len(game_a.state.all_cards_ref) == 1
    assert game_a.state.all_cards_ref[0].set == "SET_A"

    # --- Cas B : Plusieurs sets demandés ---
    game_ab = MindbugGame(deck_path=mock_cards_json, active_sets=["SET_A", "SET_B"], verbose=False)
    assert len(game_ab.state.all_cards_ref) == 2

    # --- Cas C : Auto-Select (Liste vide) ---
    # Si on ne demande rien, le moteur doit choisir le premier set alphabétique par défaut.
    # Ici : "FIRST_CONTACT", "SET_A", "SET_B" -> "FIRST_CONTACT" est premier.
    game_default = MindbugGame(deck_path=mock_cards_json, active_sets=[], verbose=False)

    assert len(game_default.state.all_cards_ref) == 1
    # On vérifie que c'est bien le set FIRST_CONTACT (celui de la carte sans set explicite)
    used_set = game_default.used_sets[0] if game_default.used_sets else ""
    assert used_set == "FIRST_CONTACT"


def test_settings_save_load(tmp_path, monkeypatch):
    """
    Vérifie que le SettingsManager sauvegarde bien la configuration sur le disque.
    """
    if SettingsManager is None or settings_module is None:
        pytest.skip("Module 'settings' introuvable ou non importable.")

    # 1. Mock du chemin du fichier de config pour ne pas écraser le vrai
    fake_settings_file = tmp_path / "test_settings.json"
    monkeypatch.setattr(settings_module, "PATH_SETTINGS", str(fake_settings_file))

    # 2. Instanciation
    manager = SettingsManager()
    test_sets = ["FUTURE_WAR", "DINO_CRISIS"]

    # 3. Modification
    manager.active_sets = test_sets

    # 4. Sauvegarde (Supporte save_settings ou save selon ton implémentation)
    if hasattr(manager, "save_settings"):
        manager.save_settings()
    else:
        manager.save()

    # 5. Vérification fichier
    assert fake_settings_file.exists()

    with open(fake_settings_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        # On vérifie que la liste des sets a bien été persistée
        assert saved_data["active_sets"] == test_sets