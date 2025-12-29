import pygame
import os
import sys

from mindbug_engine.utils.logger import log_error

# Si on n'a pas de fichier de config global, on hardcode le chemin relatif par défaut
PATH_ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

class ResourceManager:
    """
    Singleton responsable du chargement et du cache des Images et Fontes.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        self.images_cache = {}
        self.fonts_cache = {}
        
        # Image par défaut (Carré violet debug)
        self.missing_img = pygame.Surface((200, 280))
        self.missing_img.fill((255, 0, 255))
        
        # Initialisation Font
        if not pygame.font.get_init():
            pygame.font.init()

    def get_font(self, size: int, bold: bool = False, name: str = "Arial") -> pygame.font.Font:
        key = (name, size, bold)
        if key in self.fonts_cache:
            return self.fonts_cache[key]

        try:
            # Essaie de charger la font système
            font = pygame.font.SysFont(name, size, bold=bold)
        except:
            # Fallback
            font = pygame.font.SysFont(None, size, bold=bold)
        
        self.fonts_cache[key] = font
        return font

    def get_card_image(self, card_model) -> pygame.Surface:
        """Récupère l'image d'une carte (Card object) avec Cache."""
        if not card_model:
            return self.missing_img

        # 1. Identifier l'ID ou le chemin
        # On supporte les objets Card V2
        filename = getattr(card_model, "image_path", None)
        if not filename:
            filename = f"{card_model.id}.jpg"

        # 2. Vérifier le cache
        if filename in self.images_cache:
            return self.images_cache[filename]

        # 3. Construire les chemins potentiels
        candidates = [
            self._resource_path(os.path.join("cards", filename)),
            self._resource_path(os.path.join("cards", filename.replace(".jpg", ".png"))),
            self._resource_path(os.path.join("cards", f"{card_model.id}.jpg")),
        ]

        # 4. Charger
        for path in candidates:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self.images_cache[filename] = img
                    return img
                except Exception as e:
                    log_error(f"ERROR loading {path}: {e}")

        # 5. Échec -> Placeholder
        self.images_cache[filename] = self._create_placeholder_card(card_model.name)
        return self.images_cache[filename]

    def _create_placeholder_card(self, text):
        """Génère une image temporaire avec le nom écrit dessus."""
        surf = self.missing_img.copy()
        surf.fill((100, 100, 100)) # Gris
        pygame.draw.rect(surf, (200, 200, 200), surf.get_rect(), 4)
        
        font = self.get_font(20, bold=True)
        txt = font.render(text[:10], True, (255, 255, 255))
        surf.blit(txt, (10, 10))
        return surf

    def _resource_path(self, relative_path):
        """Gère les chemins pour PyInstaller (exe) ou Dev."""
        try:
            # En mode EXE, PyInstaller décompresse tout dans _MEIPASS.
            # Comme on a inclus le dossier avec "assets;assets", il faut ajouter "assets" au chemin.
            base_path = os.path.join(sys._MEIPASS, "assets")
        except Exception:
            # En mode DEV (non compilé), on utilise le chemin relatif défini plus haut
            base_path = PATH_ASSETS
            
        return os.path.join(base_path, relative_path)
