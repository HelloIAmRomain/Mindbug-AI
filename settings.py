import json
import os
from constants import PATH_SETTINGS, MODE_HOTSEAT, MODE_DEV

# Configuration par défaut si le fichier n'existe pas ou est incomplet
DEFAULT_SETTINGS = {
    "game_mode": MODE_HOTSEAT,
    "debug_mode": False,
    "active_sets": [],
    "resolution": [1280, 720],
    "enable_sound": True,
    "enable_effects": True,
    "active_card_ids": [],
    "ai_difficulty": 5  # <--- NOUVEAU (Niveau par défaut)
}

class SettingsManager:
    """
    Gère la sauvegarde et le chargement du fichier settings.json.
    Agit comme une couche d'accès aux données persistantes.
    """
    def __init__(self):
        self.data = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """Charge les paramètres depuis le JSON sur disque."""
        if os.path.exists(PATH_SETTINGS):
            try:
                with open(PATH_SETTINGS, "r") as f:
                    loaded = json.load(f)
                    # On fusionne avec les défauts pour garantir que toutes les clés existent
                    for k, v in loaded.items():
                        if k in self.data:
                            self.data[k] = v
            except Exception as e:
                print(f"⚠️ Erreur chargement settings: {e}")
        # Si le fichier n'existe pas, self.data contient déjà les défauts

    def save(self):
        """Sauvegarde les paramètres actuels sur disque."""
        try:
            with open(PATH_SETTINGS, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde settings: {e}")

    # --- ACCESSEURS (Getters/Setters) ---
    # Permet d'accéder aux settings comme des attributs : manager.ai_difficulty = 8

    @property
    def game_mode(self): return self.data.get("game_mode", MODE_HOTSEAT)
    @game_mode.setter
    def game_mode(self, val): self.data["game_mode"] = val

    @property
    def debug_mode(self): return self.data.get("debug_mode", False)
    @debug_mode.setter
    def debug_mode(self, val): self.data["debug_mode"] = val

    @property
    def active_sets(self): return self.data.get("active_sets", [])
    @active_sets.setter
    def active_sets(self, val): self.data["active_sets"] = val

    @property
    def resolution(self): return self.data.get("resolution", [1280, 720])
    @resolution.setter
    def resolution(self, val): self.data["resolution"] = val

    @property
    def enable_sound(self): return self.data.get("enable_sound", True)
    @enable_sound.setter
    def enable_sound(self, val): self.data["enable_sound"] = val

    @property
    def enable_effects(self): return self.data.get("enable_effects", True)
    @enable_effects.setter
    def enable_effects(self, val): self.data["enable_effects"] = val

    @property
    def active_card_ids(self): return self.data.get("active_card_ids", [])
    @active_card_ids.setter
    def active_card_ids(self, val): self.data["active_card_ids"] = val

    @property
    def ai_difficulty(self): return self.data.get("ai_difficulty", 5)
    @ai_difficulty.setter
    def ai_difficulty(self, val): self.data["ai_difficulty"] = val

    # --- UTILITAIRES ---
    def is_dev_mode(self):
        return self.game_mode == MODE_DEV
