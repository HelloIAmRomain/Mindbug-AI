from typing import Any, List
from mindbug_engine.core.consts import Phase
from mindbug_engine.core.models import SelectionRequest, GameState
from mindbug_engine.utils.logger import log_info, log_debug, log_error


class QueryManager:
    """
    Responsable UNIQUE de la gestion des interactions (Questions/Réponses).
    Gère le cycle de vie d'une SelectionRequest.
    """

    def __init__(self, game):
        # On stocke 'game' complet car on a besoin d'accéder à game.state ET parfois game.verbose
        self.game = game

    def start_selection_request(self, candidates, reason, count, selector, callback=None):
        """
        Initie une nouvelle demande de sélection.
        """
        # Vérification de sécurité
        if self.game.state.active_request is not None:
            log_debug(f"⚠️ CRITICAL: Écrasement d'une requête active ! ({self.game.state.active_request})")

        # 1. Création de la requête
        req = SelectionRequest(
            candidates=candidates,
            count=count,
            reason=reason,
            selector=selector,
            callback=callback
        )

        # 2. Mise à jour de l'état
        self.game.state.active_request = req

        # 3. Transition de phase (Flag UI)
        # On force la phase pour que l'UI sache qu'elle doit afficher des choix
        self.game.state.phase = Phase.RESOLUTION_CHOICE

        log_info(f"[QUERY] {selector.name} must choose {count} target(s) for {reason}.")

    def resolve_selection(self, selected_items: List[Any]) -> bool:
        """
        Traite la sélection entrante.
        Retourne True si la requête est COMPLÈTE et FERMÉE (Callback exécuté).
        Retourne False si la sélection est invalide ou incomplète (attente d'autres items).
        """
        req = self.game.state.active_request
        if not req:
            log_error("❌ No active request to resolve.")
            return False

        # 1. Validation & Accumulation
        for item in selected_items:
            # Sécurité : Vérifie si l'item est valide
            if item not in req.candidates:
                log_error(f"❌ Invalid selection: {item} not in candidates.")
                return False

            # Ajout (si pas déjà présent)
            if item not in req.current_selection:
                req.current_selection.append(item)
                log_info(f"   -> Item added: {item}")

        # 2. Vérification de Complétion
        if len(req.current_selection) >= req.count:
            log_info("   -> Selection complete.")

            # On sécurise la liste finale
            final_selection = list(req.current_selection)

            # On ferme la requête AVANT le callback
            # (Car le callback pourrait déclencher une nouvelle requête !)
            self.game.state.active_request = None

            # 3. Exécution du Callback (L'effet réel)
            if req.callback:
                req.callback(final_selection)

            return True  # Indique à l'Engine que c'est FINI

        return False  # Pas encore fini (Multiselect incomplet)