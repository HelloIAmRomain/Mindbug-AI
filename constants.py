import os
import sys

# --- CHEMIN DE BASE ---
# Détection automatique de l'environnement (Dev vs Exe)
if getattr(sys, 'frozen', False):
    # Mode EXE : On prend le dossier où se trouve l'exécutable
    # Cela permet à settings.json d'être créé à côté de MindbugAI.exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Mode DEV : On prend le dossier du script python actuel
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    """
    Permet de trouver les ressources internes (images/json) 
    aussi bien en dev qu'en .exe (PyInstaller).
    """
    try:
        # PyInstaller crée un dossier temporaire et stocke le chemin dans _MEIPASS
        # C'est ici que sont décompressés les assets inclus via --add-data
        base_path = sys._MEIPASS
    except Exception:
        # En dev, on utilise le chemin relatif au projet
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(base_path, relative_path)

# --- CONFIGURATION INITIALE ---
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
WINDOW_TITLE = "Mindbug AI - v1.5.0 (PvE Update)"
FPS_CAP = 60

# --- PROPORTIONS (Ratios) ---
# Le ratio officiel d'une carte Magic/Poker est env 0.71 (ex: 63x88mm)
CARD_ASPECT_RATIO = 0.714

# --- CONSTANTES DE JEU ---
MODE_DEV = "DEV"          # Mode Test : Tout est visible
MODE_HOTSEAT = "HOTSEAT"  # Mode Jeu Local : Rideau + Mains cachées
MODE_PVE = "PVE"          # Mode Contre IA

# --- COULEURS ---
COLOR_BG = (34, 139, 34)
COLOR_BG_MENU = (240, 240, 240)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_OVERLAY = (0, 0, 0, 200)

# Couleurs Boutons Standards
COLOR_BTN_NORMAL = (50, 50, 200)
COLOR_BTN_HOVER = (80, 80, 250)
COLOR_BTN_QUIT = (200, 50, 50)
COLOR_BTN_PLAY = (50, 200, 50)

# Couleurs UI (Settings / Slider)
COLOR_HOVER = (120, 120, 120)      # Gris clair pour survol générique menu
COLOR_ACCENT = (0, 180, 255)       # Cyan/Bleu pour le remplissage du slider

# Couleurs Gameplay
COLOR_POWER_BUFF = (0, 200, 0)
COLOR_POWER_DEBUFF = (220, 0, 0)
COLOR_POWER_POISON = (140, 0, 140)

COLOR_BORDER_ATTACK = (255, 50, 50)
COLOR_BORDER_LEGAL = (0, 255, 0)
COLOR_BORDER_NORMAL = (0, 0, 0)

# --- CHEMINS ---

# Chemin vers le JSON des données (Interne -> resource_path)
PATH_DATA = resource_path(os.path.join("data", "cards.json"))

# Chemin vers le dossier des assets (Interne -> resource_path)
PATH_ASSETS = resource_path("assets")

# Chemin du fichier de sauvegarde (Externe -> BASE_DIR)
# Ceci garantit que le fichier persiste à côté de l'exécutable
PATH_SETTINGS = os.path.join(BASE_DIR, "settings.json")
