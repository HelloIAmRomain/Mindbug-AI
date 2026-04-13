"""
Fichier unique de définition des couleurs.
Tout changement ici se répercute sur l'ensemble de l'application.
"""

# =============================================================================
# 1. PALETTE BRUTE (Raw Definitions)
# =============================================================================
_WHITE      = (240, 240, 240)
_BLACK      = (15, 15, 20)
_GREY_DARK  = (40, 44, 52)
_GREY_LIGHT = (171, 178, 191)

# Thème "Cyber Mindbug"
_DEEP_BLUE  = (20, 25, 40)    # Fond principal
_SOFT_BLUE  = (50, 60, 80)    # Fond widgets
_NEON_BLUE  = (97, 175, 239)  # Info / Primary
_NEON_GREEN = (152, 195, 121) # Success / Easy
_NEON_RED   = (224, 108, 117) # Danger / Hard
_NEON_GOLD  = (229, 192, 123) # Warning / Medium
_NEON_PURPLE= (198, 120, 221) # Accent

# =============================================================================
# 2. COULEURS SÉMANTIQUES (Usage Contextuel)
# Utilisez UNIQUEMENT celles-ci dans le code des écrans/widgets
# =============================================================================

# --- GÉNÉRAL ---
BG_COLOR     = _DEEP_BLUE
TEXT_PRIMARY = _WHITE
TEXT_SECONDARY = _GREY_LIGHT
ACCENT       = _NEON_PURPLE

# --- BOUTONS (États) ---
BTN_SURFACE  = _SOFT_BLUE      # Couleur par défaut d'un bouton
BTN_HOVER    = _NEON_BLUE      # Survol (devient bleu électrique)
BTN_BORDER   = _WHITE          # Contour

# --- BOUTONS (Types) ---
BTN_PRIMARY  = _SOFT_BLUE      # Action standard
BTN_INFO     = (60, 90, 140)   # Action informative (Settings) - Variante manuel
BTN_SUCCESS  = (60, 100, 60)   # Validation
BTN_DANGER   = (100, 50, 50)   # Quitter / Retour

# --- INDICATEURS DE JEU (Difficulté, Status) ---
STATUS_OK    = _NEON_GREEN
STATUS_WARN  = _NEON_GOLD
STATUS_CRIT  = _NEON_RED


HIGHLIGHT_GOLD = (255, 215, 0)   # Or brillant pour les actions possibles
BTN_MINDBUG    = (156, 39, 176)  # Violet vibrant pour le Mindbug
BTN_PASS       = (100, 100, 100) # Gris clair mais visible pour Passer

# --- COULEURS MENU ---
BTN_PLAY     = (76, 175, 80)   # Vert
BTN_PVP      = (255, 152, 0)   # Orange (Nouveau)
BTN_SETTINGS = (33, 150, 243)  # Bleu
BTN_QUIT     = (244, 67, 54)   # Rouge