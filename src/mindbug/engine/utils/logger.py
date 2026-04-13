import logging
import os
import sys


# Configuration du logger
class GameLogger:
    _instance = None

    @staticmethod
    def get_logger():
        if GameLogger._instance is None:
            GameLogger()
        return GameLogger._instance

    def __init__(self):
        if GameLogger._instance is not None:
            raise Exception("This class is a singleton!")

        self.logger = logging.getLogger("MindbugLogger")
        self.logger.setLevel(logging.DEBUG)

        # Format : [HEURE] [FICHIER] Message
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

        # 1. Handler Console (Ce qu'on voit dans le terminal)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # On garde la console propre
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 2. Handler Fichier (Tout l'historique pour le debug)
        file_handler = logging.FileHandler("game_debug.log", mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # On écrit TOUT dans le fichier
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        GameLogger._instance = self.logger


# Fonction helper pour un accès rapide
def log_info(msg):
    GameLogger.get_logger().info(msg)


def log_debug(msg):
    GameLogger.get_logger().debug(msg)


def log_error(msg):
    GameLogger.get_logger().error(msg)