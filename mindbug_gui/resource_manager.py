import pygame
import os
from constants import PATH_ASSETS

class ResourceManager:
    """
    Centralise le chargement des ressources (Images, Polices) pour éviter
    les doublons en mémoire et les accès disques répétés.
    """
    def __init__(self):
        # Caches
        self.images = {}      # {path: Surface}
        self.fonts = {}       # {(name, size, is_bold): Font}
        
        # On définit les polices système par défaut
        self.default_font_name = "Arial"

    def get_image(self, relative_path: str) -> pygame.Surface:
        """Charge une image depuis assets/ ou retourne la version en cache."""
        if not relative_path:
            return None
            
        if relative_path in self.images:
            return self.images[relative_path]
        
        full_path = os.path.join(PATH_ASSETS, relative_path)
        if not os.path.exists(full_path):
            # On pourrait retourner une image "placeholder" ici
            print(f"[ResourceManager] Image introuvable : {relative_path}")
            self.images[relative_path] = None
            return None
            
        try:
            img = pygame.image.load(full_path).convert_alpha()
            self.images[relative_path] = img
            return img
        except Exception as e:
            print(f"[ResourceManager] Erreur chargement {relative_path}: {e}")
            self.images[relative_path] = None
            return None

    def get_font(self, size: int, bold: bool = False, font_name: str = None) -> pygame.font.Font:
        """Retourne une police chargée et cachée."""
        if font_name is None:
            font_name = self.default_font_name
            
        key = (font_name, size, bold)
        if key in self.fonts:
            return self.fonts[key]
            
        # Création de la police
        # Note: SysFont charge depuis le système. Pour des fichiers .ttf locaux, utiliser Font()
        font = pygame.font.SysFont(font_name, size, bold=bold)
        self.fonts[key] = font
        return font
    
    def clear_cache(self):
        self.images.clear()
        self.fonts.clear()
