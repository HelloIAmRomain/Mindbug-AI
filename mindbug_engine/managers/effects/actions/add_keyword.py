from typing import Any, Dict
from mindbug_engine.managers.effects.base import EffectAction
from mindbug_engine.core.consts import Keyword
from mindbug_engine.utils.logger import log_info


class AddKeywordAction(EffectAction):
    """
    Action permettant d'ajouter dynamiquement un ou plusieurs mots-clés à une carte.
    Exemple : Le Yéti solitaire qui gagne Fureur (FRENZY).
    """

    def execute(self, target: Any, params: Dict, source: Any, owner: Any, opponent: Any):
        # On vérifie que la cible peut recevoir des mots-clés (c'est une instance de Card)
        if not hasattr(target, 'keywords'):
            return

        # Récupération des mots-clés à ajouter depuis les paramètres
        kws = params.get("keywords", [])

        # Support pour un seul mot-clé passé en string au lieu d'une liste
        if isinstance(kws, str):
            kws = [kws]

        for kw_str in kws:
            try:
                # Conversion de la string en Enum Keyword pour garantir la validité
                kw = Keyword(kw_str)

                # On ne l'ajoute que s'il n'est pas déjà présent
                if kw not in target.keywords:
                    target.keywords.append(kw)
                    log_info(f"   -> Mot-clé {kw.value} ajouté à {target.name}")
            except ValueError:
                # Log d'erreur si le mot-clé dans le JSON n'existe pas dans l'Enum
                from mindbug_engine.utils.logger import log_error
                log_error(f"⚠️ Mot-clé inconnu dans les paramètres d'effet : {kw_str}")
                continue