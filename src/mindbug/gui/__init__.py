"""
Mindbug GUI Package
Architecture V2 : App -> Screens -> Widgets -> Controller
"""

# On expose l'App et le Controller pour faciliter l'accès depuis main.py
from .core.app import MindbugApp
from .controller import InputHandler
