import random
from typing import List, TYPE_CHECKING, Callable, Dict
from .models import Card, Player

if TYPE_CHECKING:
    from .engine import MindbugGame

class EffectManager:
    """
    Gère l'application des effets de cartes via un système de dispatch.
    Remplace les longues chaînes de if/elif par un dictionnaire de fonctions.
    """

    def __init__(self):
        # MAPPING : Code Effet -> Méthode à exécuter
        self._handlers: Dict[str, Callable] = {
            # Soin / Dégâts
            "HEAL": self._handle_heal,
            "DAMAGE": self._handle_damage,
            "DAMAGE_UNBLOCKED": self._handle_damage,
            "SET_HP_EQUAL_OPPONENT": self._handle_set_hp_equal,
            "SET_OPPONENT_HP_TO_ONE": self._handle_set_opp_hp_one,
            
            # Actions sur Créatures (Board)
            "STEAL_CREATURE": self._handle_steal_creature,
            "DESTROY_CREATURE": self._handle_destroy_creature,
            "DESTROY_IF_FEWER_ALLIES": self._handle_destroy_conditional,
            "DESTROY_ALL_ENEMIES": self._handle_destroy_all,
            "OPPONENT_SACRIFICE": self._handle_sacrifice,
            
            # Actions sur Main / Défausse
            "STEAL_CARD_HAND": self._handle_steal_hand,
            "DISCARD_RANDOM": self._handle_discard_random,
            "DISCARD_OPPONENT_CHOICE": self._handle_discard_random, # TODO: Rendre interactif plus tard
            
            # Actions Cimetière (Reclaim / Play)
            "RECLAIM_DISCARD": self._handle_reclaim_discard,
            "RECLAIM_ALL_DISCARD": self._handle_reclaim_all,
            "PLAY_FROM_MY_DISCARD": self._handle_play_my_discard,
            "PLAY_FROM_OPP_DISCARD": self._handle_play_opp_discard,
        }

    def apply_effect(self, game: 'MindbugGame', card: Card, owner: Player, opponent: Player):
        """Point d'entrée unique pour déclencher un effet."""
        if not card.ability: 
            return

        code = card.ability.code
        handler = self._handlers.get(code)

        if handler:
            print(f"✨ EFFET : {code} (Val:{card.ability.value}) pour {card.name}")
            # On passe le contexte complet au handler
            handler(game, card, owner, opponent)
        else:
            print(f"⚠️ AVERTISSEMENT : Effet non implémenté ou code inconnu '{code}'")

    # ==========================================
    #  HANDLERS (Logique Spécifique)
    # ==========================================

    def _handle_heal(self, game, card, owner, opp):
        if card.ability.target == "SELF":
            owner.hp += card.ability.value

    def _handle_damage(self, game, card, owner, opp):
        target = owner if card.ability.target == "SELF" else opp
        target.hp -= card.ability.value

    def _handle_set_hp_equal(self, game, card, owner, opp):
        owner.hp = opp.hp

    def _handle_set_opp_hp_one(self, game, card, owner, opp):
        if opp.hp > 1: opp.hp = 1

    def _handle_steal_creature(self, game, card, owner, opp):
        self._resolve_selection_action(
            game, opp.board, "STEAL_CREATURE", 
            card.ability, initiator=owner
        )

    def _handle_destroy_creature(self, game, card, owner, opp):
        # Note: Le destructeur est toujours le joueur actif
        self._resolve_selection_action(
            game, opp.board, "DESTROY_CREATURE", 
            card.ability, initiator=game.active_player
        )

    def _handle_destroy_conditional(self, game, card, owner, opp):
        # Condition spécifique : Moins d'alliés que l'adversaire
        if len(owner.board) < len(opp.board):
            self._handle_destroy_creature(game, card, owner, opp)

    def _handle_destroy_all(self, game, card, owner, opp):
        targets = self._get_valid_targets(opp.board, card.ability.condition, card.ability.condition_value)
        for target in list(targets):
            game._destroy_card(target, opp)

    def _handle_sacrifice(self, game, card, owner, opp):
        if not opp.board: return
        # Pour l'instant random, TODO: Rendre interactif (Opponent choisit)
        for _ in range(card.ability.value):
            if opp.board:
                target = random.choice(opp.board)
                game._destroy_card(target, opp)

    def _handle_steal_hand(self, game, card, owner, opp):
        if not opp.hand: return
        for _ in range(card.ability.value):
            if opp.hand:
                steal = random.choice(opp.hand)
                opp.hand.remove(steal)
                owner.hand.append(steal)
                game.refill_hand(opp)

    def _handle_discard_random(self, game, card, owner, opp):
        if not opp.hand: return
        for _ in range(card.ability.value):
            if opp.hand:
                discarded = random.choice(opp.hand)
                opp.hand.remove(discarded)
                opp.discard.append(discarded)
                game.refill_hand(opp)

    def _handle_reclaim_discard(self, game, card, owner, opp):
        if not owner.discard: return
        game.ask_for_selection(owner.discard, "RECLAIM_DISCARD", card.ability.value, owner)

    def _handle_play_my_discard(self, game, card, owner, opp):
        if not owner.discard: return
        game.ask_for_selection(owner.discard, "PLAY_FROM_MY_DISCARD", card.ability.value, owner)

    def _handle_play_opp_discard(self, game, card, owner, opp):
        if not opp.discard: return
        game.ask_for_selection(opp.discard, "PLAY_FROM_OPP_DISCARD", card.ability.value, owner)

    def _handle_reclaim_all(self, game, card, owner, opp):
        if not owner.discard: return
        for c in owner.discard:
            c.reset()
            owner.hand.append(c)
        owner.discard = []

    # ==========================================
    #  HELPERS & LOGIQUE COMMUNE
    # ==========================================

    def _resolve_selection_action(self, game, candidates_pool, effect_code, ability, initiator):
        """Filtre les candidats et lance la demande de sélection si nécessaire."""
        candidates = self._get_valid_targets(candidates_pool, ability.condition, ability.condition_value)
        if candidates:
            game.ask_for_selection(candidates, effect_code, ability.value, initiator)

    @staticmethod
    def _get_valid_targets(candidates: List[Card], condition_type: str, threshold: int) -> List[Card]:
        if not candidates: return []
        if not condition_type or condition_type in ["ALWAYS", "NONE", "CHOICE_USER"]: return candidates
        
        filtered = []
        for card in candidates:
            if EffectManager._check_condition(card, condition_type, threshold):
                filtered.append(card)
        return filtered

    @staticmethod
    def _check_condition(card: Card, c_type: str, threshold: int) -> bool:
        if c_type == "MIN_POWER": return card.power >= threshold
        if c_type == "MAX_POWER": return card.power <= threshold
        if c_type == "EXACT_POWER": return card.power == threshold
        return True
