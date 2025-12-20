import json
import os
from typing import List, Tuple
from mindbug_engine.core.consts import Difficulty

class ConfigurationService:
    """
    Service unique gérant la persistance et la validation des paramètres.
    Remplace SettingsManager, GameConfig et l'ancienne classe Config.
    """
    FILE_PATH = "settings.json"

    def __init__(self):
        # Valeurs par défaut
        self.ai_difficulty: Difficulty = Difficulty.MEDIUM
        self.debug_mode: bool = False
        self.game_mode: str = "HOTSEAT"
        self.active_sets: List[str] = ["FIRST_CONTACT"]
        self.resolution: Tuple[int, int] = (1280, 720)
        self.fullscreen: bool = False
        
        # Données runtime (non sauvegardées)
        self.available_sets_in_db: List[str] = []
        
        self.load()

    def load(self):
        """Charge et valide les paramètres depuis le disque."""
        if not os.path.exists(self.FILE_PATH):
            return

        try:
            with open(self.FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                self.debug_mode = data.get("debug_mode", False)
                self.game_mode = data.get("game_mode", "HOTSEAT")
                self.fullscreen = data.get("fullscreen", False)
                self.resolution = tuple(data.get("resolution", (1280, 720)))
                
                # Validation de la difficulté
                raw_diff = data.get("ai_difficulty", "MEDIUM")
                try:
                    self.ai_difficulty = Difficulty(raw_diff)
                except ValueError:
                    self.ai_difficulty = Difficulty.MEDIUM

                # Validation des sets
                saved_sets = data.get("active_sets", ["FIRST_CONTACT"])
                if saved_sets:
                    self.active_sets = saved_sets
        except Exception as e:
            print(f"⚠️ Erreur lors du chargement des paramètres : {e}")

    def save(self):
        """Persiste les paramètres actuels sur le disque."""
        data = {
            "debug_mode": self.debug_mode,
            "game_mode": self.game_mode,
            "ai_difficulty": self.ai_difficulty.value,
            "active_sets": self.active_sets,
            "resolution": self.resolution,
            "fullscreen": self.fullscreen
        }
        try:
            with open(self.FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde : {e}")
