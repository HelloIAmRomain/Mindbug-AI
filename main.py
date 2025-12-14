import sys
import os
import pygame
import traceback

# Ajout du chemin racine pour garantir que les imports fonctionnent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from constants import WINDOW_TITLE
from config import GameConfig
from mindbug_gui.screens.menu_screen import MenuScreen
from mindbug_gui.screens.settings_screen import SettingsScreen
from mindbug_gui.window import MindbugGUI
from mindbug_gui.resource_manager import ResourceManager

def main():
    """
    Point d'entrée de l'application.
    Gère l'initialisation de la fenêtre redimensionnable et la boucle d'états.
    """
    
    # 1. Initialisation unique de PyGame
    pygame.init()
    
    # 2. Chargement de la Configuration
    config = GameConfig()
    
    # 3. Configuration de la Fenêtre
    w, h = config.settings.resolution
    screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
    pygame.display.set_caption(WINDOW_TITLE)
    
    # 4. Initialisation du Gestionnaire de Ressources (Pour les menus)
    # Cela permet de charger les polices et images de fond une seule fois
    res_manager = ResourceManager()
    
    # 5. État initial
    current_state = "MENU"
    
    print(f"Démarrage de {WINDOW_TITLE}...")
    print(f"Mode actuel : {config.game_mode}")

    try:
        # 6. Boucle Principale des États
        while current_state != "QUIT":
            
            # --- MENU PRINCIPAL ---
            if current_state == "MENU":
                # On passe le res_manager pour éviter de recharger les fonts à chaque fois
                menu = MenuScreen(screen, config, res_manager)
                current_state = menu.run()
                
            # --- PARAMÈTRES ---
            elif current_state == "SETTINGS":
                settings = SettingsScreen(screen, config, res_manager)
                current_state = settings.run()
                
            # --- JEU (Gameplay) ---
            elif current_state == "PLAY":
                print("Lancement du module de jeu (MindbugGUI)...")
                # Le jeu gère ses propres ressources pour l'instant via son __init__
                game_app = MindbugGUI(config, screen) 
                current_state = game_app.run()
                
                # Petit nettoyage après une partie (optionnel)
                import gc
                gc.collect()
                
            else:
                print(f"⚠️ Erreur critique : État inconnu '{current_state}'.")
                current_state = "QUIT"

    except KeyboardInterrupt:
        print("\nInterruption clavier (Ctrl+C) détectée.")

    except Exception:
        print("\n" + "="*60)
        print("🛑 CRASH DU JEU DÉTECTÉ")
        print("Voici le rapport d'erreur technique :")
        print("="*60)
        traceback.print_exc()
        print("="*60 + "\n")

    finally:
        # 7. Fermeture Propre
        print("Fermeture de l'application...")
        # On vide le cache explicitement avant de quitter
        if 'res_manager' in locals():
            res_manager.clear_cache()
            
        try:
            pygame.quit()
        except Exception:
            pass
        
        os._exit(0)

if __name__ == "__main__":
    main()
