import json
import os
from enum import Enum
from mindbug_engine.core.consts import Difficulty

CONFIG_PATH = "config.json"


class Config:
    """
    Gère la configuration persistante.
    GARANTIE : Toutes les propriétés publiques sont typées correctement.
    """

    def __init__(self):
        # 1. Valeurs par défaut (Types stricts)
        self.ai_difficulty: Difficulty = Difficulty.MEDIUM
        self.debug_mode: bool = False
        self.game_mode: str = "HOTSEAT"
        self.active_sets: list[str] = ["FIRST_CONTACT"]
        self.resolution: tuple[int, int] = (1280, 720)
        self.fullscreen: bool = False

        # Données volatiles (Runtime uniquement)
        self.available_sets_in_db: list[str] = []

        self.load_settings()

    def load_settings(self):
        if not os.path.exists(CONFIG_PATH):
            return

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

                self.debug_mode = data.get("debug_mode", False)
                self.game_mode = data.get("game_mode", "HOTSEAT")
                self.active_sets = data.get("active_sets", ["First Contact"])
                self.fullscreen = data.get("fullscreen", False)

                # --- SANITIZATION STRICTE ---
                # On essaie de convertir la string en Enum.
                # Si ça échoue (ex: entier legacy, typo, null), on force le défaut.
                raw_diff = data.get("ai_difficulty", "MEDIUM")
                try:
                    self.ai_difficulty = Difficulty(raw_diff)
                except (ValueError, TypeError):
                    print(f"⚠️ Difficulté invalide dans config ({raw_diff}). Reset à MEDIUM.")
                    self.ai_difficulty = Difficulty.MEDIUM

        except Exception as e:
            print(f"⚠️ Erreur lecture config : {e}. Utilisation des valeurs par défaut.")

    def save_settings(self):
        data = {
            "debug_mode": self.debug_mode,
            "game_mode": self.game_mode,
            "active_sets": self.active_sets,
            "fullscreen": self.fullscreen,
            # Sérialisation propre : Enum -> String
            "ai_difficulty": self.ai_difficulty.value
        }

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            print("💾 Config sauvegardée.")
        except Exception as e:
            print(f"❌ Erreur sauvegarde : {e}")