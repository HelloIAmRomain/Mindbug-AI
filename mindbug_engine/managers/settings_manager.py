import json
import os
from typing import Dict, Set, List
from mindbug_engine.core.consts import CardStatus
from mindbug_engine.utils.logger import log_error, log_info

SETTINGS_FILE = "settings.json"

class SettingsManager:
    """
    Gère la persistance des préférences de jeu :
    - Mode Debug
    - Sets actifs (Extensions)
    - Statut individuel des cartes (Ban/Select/Neutral)
    """
    def __init__(self):
        self.debug_mode: bool = False
        self.active_sets: Set[str] = {"FIRST_CONTACT"}
        # Map: card_id -> CardStatus
        self.card_preferences: Dict[str, CardStatus] = {}
        self.load()

    def load(self):
        """Charge les settings depuis le JSON."""
        if not os.path.exists(SETTINGS_FILE):
            return

        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                self.debug_mode = data.get("debug_mode", False)
                # On utilise un set pour éviter les doublons et faciliter la recherche
                self.active_sets = set(data.get("active_sets", ["FIRST_CONTACT"]))

                # Conversion des strings JSON en Enum
                prefs = data.get("card_preferences", {})
                self.card_preferences = {}
                for cid, status_str in prefs.items():
                    try:
                        self.card_preferences[cid] = CardStatus(status_str)
                    except ValueError:
                        self.card_preferences[cid] = CardStatus.NEUTRAL
        except Exception as e:
            log_error(f"⚠️ Erreur chargement settings: {e}")

    def save(self):
        """Sauvegarde l'état actuel."""
        data = {
            "debug_mode": self.debug_mode,
            "active_sets": list(self.active_sets),
            # Conversion Enum -> String pour JSON (On ne sauvegarde pas les NEUTRAL pour alléger)
            "card_preferences": {k: v.value for k, v in self.card_preferences.items() if v != CardStatus.NEUTRAL}
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log_error(f"⚠️ Erreur sauvegarde settings: {e}")

    # --- GESTION DES CARTES ---

    def set_card_status(self, card_id: str, status: CardStatus):
        """Définit le statut d'une carte spécifique."""
        if status == CardStatus.NEUTRAL:
            if card_id in self.card_preferences:
                del self.card_preferences[card_id]
        else:
            self.card_preferences[card_id] = status
        self.save()

    def get_card_status(self, card_id: str) -> CardStatus:
        """Récupère le statut (utile pour l'UI : Bordure verte/rouge)."""
        return self.card_preferences.get(card_id, CardStatus.NEUTRAL)

    def cycle_card_status(self, card_id: str):
        """Gère le cycle : 2 copies -> 0 (BAN) -> 1 copie -> 2 copies."""
        # On peut détourner CardStatus ou utiliser des entiers
        current = self.card_preferences.get(card_id, 2)

        if current == 2:
            new_val = 0
        elif current == 0:
            new_val = 1
        else:
            new_val = 2

        self.card_preferences[card_id] = new_val
        self.save()

    def get_card_copies(self, card_id: str) -> int:
        """Récupère le quota configuré pour cet ID."""
        return self.card_preferences.get(card_id, 2)

    # --- GESTION DES SETS ---

    def toggle_active_set(self, set_name: str):
        """Active ou désactive un set complet."""
        if set_name in self.active_sets:
            # On empêche de désactiver le dernier set (pour éviter d'avoir 0 set actif)
            if len(self.active_sets) > 1:
                self.active_sets.remove(set_name)
        else:
            self.active_sets.add(set_name)
        self.save()
        log_info(f"Set '{set_name}' toggled. Active sets: {self.active_sets}")

    def is_set_active(self, set_name: str) -> bool:
        return set_name in self.active_setss