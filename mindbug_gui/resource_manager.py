import pygame
import os
import sys
from constants import PATH_ASSETS


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class ResourceManager:
    def __init__(self):
        self.images = {}
        self.fonts = {}
        self.default_font_name = "Arial"

        # Carré violet (Debug)
        self.missing_img = pygame.Surface((300, 420))
        self.missing_img.fill((255, 0, 255))

        # On charge une police basique pour écrire sur le carré violet
        pygame.font.init()
        self.debug_font = pygame.font.SysFont("arial", 20)

    def get_font(self, size: int, bold: bool = False, font_name: str = None) -> pygame.font.Font:
        if font_name is None: font_name = self.default_font_name
        key = (font_name, size, bold)
        if key in self.fonts: return self.fonts[key]
        try:
            font = pygame.font.SysFont(font_name, size, bold=bold)
        except:
            font = pygame.font.SysFont("arial", size, bold=bold)
        self.fonts[key] = font
        return font

    def get_image(self, relative_path: str) -> pygame.Surface:
        """Charge une UI ou icone."""
        if not relative_path: return None
        # ... (Code existant pour UI, peu importe ici)
        return self.missing_img

    def get_card_image(self, card_model):
        """
        Cherche l'image de la carte.
        """
        if not card_model: return self.missing_img

        # Nom du fichier (ex: "Axolotl_Healer.jpg")
        filename = card_model.image_path
        if not filename:
            # Fallback sur l'ID si le JSON n'a pas de champ image
            filename = f"{card_model.id}.jpg"

        # On construit la liste des chemins à tester
        # PATH_ASSETS pointe normalement vers ".../assets"

        candidates = [
            # 1. Standard : assets/cards/NomFichier.jpg
            os.path.join(PATH_ASSETS, "cards", filename),

            # 2. Cas où filename contient déjà "assets/cards/"
            resource_path(filename),

            # 3. Fallback PNG
            os.path.join(PATH_ASSETS, "cards", filename.replace(".jpg", ".png")),

            # 4. Fallback ID pur
            os.path.join(PATH_ASSETS, "cards", f"{card_model.id}.jpg")
        ]

        for full_path in candidates:
            # Nettoyage des doubles slashes éventuels
            full_path = os.path.normpath(full_path)

            if full_path in self.images:
                return self.images[full_path]

            if os.path.exists(full_path):
                try:
                    img = pygame.image.load(full_path).convert_alpha()
                    self.images[full_path] = img
                    # print(f"[INFO] Image chargée : {full_path}") # Décommenter pour voir succès
                    return img
                except Exception as e:
                    print(f"[ERREUR] Fichier corrompu {full_path}: {e}")
            else:
                # Décommentez la ligne ci-dessous pour voir où le jeu cherche et échoue
                # print(f"[DEBUG] Pas trouvé ici : {full_path}")
                pass

        # Si on arrive ici, c'est l'échec. On retourne le carré violet avec le nom
        # pour aider au debug visuel
        error_surf = self.missing_img.copy()
        txt = self.debug_font.render(filename[:15], True, (0, 0, 0))
        error_surf.blit(txt, (10, 10))
        return error_surf

    def clear_cache(self):
        self.images.clear()
        self.fonts.clear()