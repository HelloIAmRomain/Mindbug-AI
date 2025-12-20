from abc import ABC, abstractmethod

class Command(ABC):
    """
    Classe abstraite de base pour toutes les commandes du jeu (Pattern Command).
    """

    @abstractmethod
    def execute(self, game):
        """
        Exécute la logique de la commande sur l'instance de jeu donnée.
        """
        raise NotImplementedError