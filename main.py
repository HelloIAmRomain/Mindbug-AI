import sys
import os
import pygame
import traceback

# Ajout du chemin racine pour garantir que les imports fonctionnent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports centralisés
from constants import DEFAULT_WIDTH, DEFAULT_HEIGHT, WINDOW_TITLE
from config import GameConfig
from mindbug_gui.menu import MenuScreen, SettingsScreen
from mindbug_gui.window import MindbugGUI

def main():
    """
    Point d'entrée de l'application.
    Gère l'initialisation de la fenêtre redimensionnable et la boucle d'états.
    """
    
    # 1. Initialisation unique de PyGame
    pygame.init()
    
    # 2. Configuration de la Fenêtre (Mode RESIZABLE)
    screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption(WINDOW_TITLE)
    
    # 3. Chargement de la Configuration
    config = GameConfig()
    
    # 4. État initial
    current_state = "MENU"
    
    print(f"Démarrage de {WINDOW_TITLE}...")

    try:
        # 5. Boucle Principale des États
        while current_state != "QUIT":
            
            # --- MENU PRINCIPAL ---
            if current_state == "MENU":
                menu = MenuScreen(screen, config)
                current_state = menu.run()
                
            # --- PARAMÈTRES ---
            elif current_state == "SETTINGS":
                settings = SettingsScreen(screen, config)
                current_state = settings.run()
                
            # --- JEU (Gameplay) ---
            elif current_state == "PLAY":
                print("Lancement du module de jeu (MindbugGUI)...")
                # Le jeu gère dynamiquement le redimensionnement via son Renderer
                game_app = MindbugGUI(config)
                current_state = game_app.run()
                
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
        # 6. Fermeture Propre
        print("Fermeture de l'application...")
        try:
            pygame.quit()
        except Exception:
            pass
        
        os._exit(0)

if __name__ == "__main__":
    main()
