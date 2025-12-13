import json
import os
from constants import PATH_SETTINGS, MODE_HOTSEAT, MODE_DEV

DEFAULT_SETTINGS = {
    "game_mode": MODE_HOTSEAT,
    "debug_mode": False,
    "active_sets": [],
    "resolution": [1280, 720],
    "enable_sound": True,
    "enable_effects": True,
    "active_card_ids": []
}

class SettingsManager:
    def __init__(self):
        self.data = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        """Charge les paramètres depuis le JSON."""
        if os.path.exists(PATH_SETTINGS):
            try:
                with open(PATH_SETTINGS, "r") as f:
                    loaded = json.load(f)
                    for k, v in loaded.items():
                        if k in self.data:
                            self.data[k] = v
            except Exception as e:
                print(f"Erreur chargement settings: {e}")

    def save(self):
        """Sauvegarde les paramètres actuels."""
        try:
            with open(PATH_SETTINGS, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Erreur sauvegarde settings: {e}")

    # --- ACCESSEURS ---

    @property
    def game_mode(self): return self.data["game_mode"]
    @game_mode.setter
    def game_mode(self, val): self.data["game_mode"] = val

    @property
    def debug_mode(self): return self.data["debug_mode"]
    @debug_mode.setter
    def debug_mode(self, val): self.data["debug_mode"] = val

    @property
    def active_sets(self): return self.data["active_sets"]
    @active_sets.setter
    def active_sets(self, val): self.data["active_sets"] = val

    @property
    def resolution(self): return self.data["resolution"]
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

    # --- LA PARTIE QUI MANQUAIT ---
    @property
    def active_card_ids(self): 
        return self.data.get("active_card_ids", [])
    
    @active_card_ids.setter
    def active_card_ids(self, val): 
        self.data["active_card_ids"] = val
    # ------------------------------

    # --- UTILITAIRES ---
    def is_dev_mode(self):
        return self.game_mode == MODE_DEV
