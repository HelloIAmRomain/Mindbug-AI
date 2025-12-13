import os
import sys

def resource_path(relative_path):
    """
    Permet de trouver les ressources (images/json) aussi bien en dev qu'en .exe (PyInstaller).
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- CONFIGURATION INITIALE ---
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
WINDOW_TITLE = "Mindbug AI - v1.4.0 (Settings & Sets)"
FPS_CAP = 60

# --- PROPORTIONS (Ratios) ---
# Le ratio officiel d'une carte Magic/Poker est env 0.71 (ex: 63x88mm)
CARD_ASPECT_RATIO = 0.714 

# --- CONSTANTES DE JEU (NOUVEAU) ---
# Définir les modes ici permet de les utiliser partout (Settings, Renderer, Window)
MODE_DEV = "DEV"          # Mode Test : Tout est visible, pas de rideau
MODE_HOTSEAT = "HOTSEAT"  # Mode Jeu Local : Rideau + Mains cachées
MODE_PVE = "PVE"          # Mode Contre IA (Futur)

# --- COULEURS ---
COLOR_BG = (34, 139, 34)
COLOR_BG_MENU = (240, 240, 240)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_OVERLAY = (0, 0, 0, 200)

COLOR_BTN_NORMAL = (50, 50, 200)
COLOR_BTN_HOVER = (80, 80, 250)
COLOR_BTN_QUIT = (200, 50, 50)
COLOR_BTN_PLAY = (50, 200, 50)

COLOR_POWER_BUFF = (0, 200, 0)
COLOR_POWER_DEBUFF = (220, 0, 0)
COLOR_POWER_POISON = (140, 0, 140)

COLOR_BORDER_ATTACK = (255, 50, 50)
COLOR_BORDER_LEGAL = (0, 255, 0)
COLOR_BORDER_NORMAL = (0, 0, 0)

# --- CHEMINS ---
PATH_DATA = resource_path(os.path.join("data", "cards.json"))
PATH_ASSETS = resource_path(os.path.join("assets", "cards"))
# Chemin du fichier de sauvegarde (Créé à la racine de l'exécution)
PATH_SETTINGS = "settings.json"
