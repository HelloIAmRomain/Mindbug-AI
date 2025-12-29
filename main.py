import os
import sys

from mindbug_gui.core.app import MindbugApp
from mindbug_gui.screens.menu_screen import MenuScreen

if __name__ == "__main__":
    # 1. On instancie l'App (elle va charger Config et ResourceManager toute seule)
    app = MindbugApp()
    
    # 2. On définit l'écran de départ
    app.set_screen(MenuScreen(app))
    
    # 3. Lancement
    app.run()
