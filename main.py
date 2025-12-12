import sys
import os

# Ajout du dossier courant au path pour que les imports fonctionnent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mindbug_gui.window import MindbugGUI

if __name__ == "__main__":
    gui = MindbugGUI()
    gui.run()
