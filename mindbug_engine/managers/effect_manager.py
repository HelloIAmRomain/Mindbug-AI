import random
from typing import List, Dict, Any, TYPE_CHECKING
from mindbug_engine.core.models import Card, Player, CardEffect
from mindbug_engine.core.consts import Trigger, EffectType
from mindbug_engine.utils.logger import log_info, log_error

# Imports des actions
from mindbug_engine.managers.effects.actions.modify_stat import ModifyStatAction
from mindbug_engine.managers.effects.actions.destroy import DestroyAction
from mindbug_engine.managers.effects.actions.steal import StealAction
from mindbug_engine.managers.effects.actions.play import PlayAction
from mindbug_engine.managers.effects.actions.discard import DiscardAction
from mindbug_engine.managers.effects.actions.move import MoveAction
from mindbug_engine.managers.effects.actions.add_keyword import AddKeywordAction
from mindbug_engine.managers.effects.actions.copy_keywords import CopyKeywordsAction

if TYPE_CHECKING:
    from mindbug_engine.engine import MindbugGame

class EffectManager:
    def __init__(self, game: 'MindbugGame'):
        self.game = game
        self.state = game.state
        self.turn_manager = game.turn_manager

        # Registre des actions modulaires
        self._actions = {
            EffectType.MODIFY_STAT: ModifyStatAction(),
            EffectType.DESTROY: DestroyAction(game.combat_manager),
            EffectType.STEAL: StealAction(self),
            EffectType.PLAY: PlayAction(game),
            EffectType.DISCARD: DiscardAction(game.turn_manager),
            EffectType.MOVE: MoveAction(),
            EffectType.ADD_KEYWORD: AddKeywordAction(),
            EffectType.COPY_KEYWORDS: CopyKeywordsAction(self),
        }

    def apply_effect(self, card: Card, owner: Player, opponent: Player):
        """Point d'entrée principal pour déclencher les effets d'une carte."""
        if not card.effects: return
        for effect in card.effects:
            if self._check_global_conditions(effect.condition, owner, opponent):
                self._process_single_effect(effect, card, owner, opponent)

    def apply_passive_effects(self):
        """
        Recalcule les bonus passifs (Auras). Appelé par Engine.update_board_states().
        """
        p1 = self.state.player1
        p2 = self.state.player2

        all_sources = []
        for c in p1.board: all_sources.append((c, p1, p2))
        for c in p2.board: all_sources.append((c, p2, p1))

        for card, owner, opp in all_sources:
            if card.trigger == Trigger.PASSIVE:
                for effect in card.effects:
                    # On ignore les interdictions (BAN) ici car elles sont gérées par les règles de combat
                    if effect.type == EffectType.BAN: continue

                    if not self._check_global_conditions(effect.condition, owner, opp):
                        continue

                    # Récupération des cibles
                    raw_candidates = self._get_candidates(effect, card, owner, opp)
                    targets = self._filter_targets(raw_candidates, effect.condition)

                    for t in targets:
                        self._dispatch_verb(effect, t, card, owner, opp)

    def _process_single_effect(self, effect: CardEffect, source_card: Card, owner: Player, opponent: Player):
        """Gère la sélection des cibles (Auto, Random, Choix) puis exécute l'action."""
        candidates = self._get_candidates(effect, source_card, owner, opponent)
        valid_targets = self._filter_targets(candidates, effect.condition)
        
        if not valid_targets: return

        select_method = effect.target.get("select", "ALL")
        count = effect.target.get("count", 1)

        # Définition de la callback exécutée une fois les cibles choisies
        def on_selection_complete(selected_targets):
            for target in selected_targets:
                self._dispatch_verb(effect, target, source_card, owner, opponent)

        # Logique de sélection
        if select_method == "ALL":
            on_selection_complete(valid_targets)
        
        elif select_method == "RANDOM":
            nb = len(valid_targets) if count == "ALL" else count
            # random.sample plante si k > len, donc on prend le min
            chosen = random.sample(valid_targets, min(nb, len(valid_targets)))
            on_selection_complete(chosen)
            
        elif select_method in ["CHOICE_USER", "CHOICE_OPP"]:
            chooser = owner if select_method == "CHOICE_USER" else opponent
            self.game.ask_for_selection(valid_targets, effect.type, count, chooser, on_selection_complete)
            
        else:
            # Fallback par défaut (ex: select="NONE" ou malformé)
            on_selection_complete(valid_targets)

    def _dispatch_verb(self, effect, target, source, owner, opp):
        """Délègue l'exécution à la classe d'action appropriée."""
        action_handler = self._actions.get(effect.type)
        if action_handler:
            try:
                action_handler.execute(target, effect.params, source, owner, opp)
            except Exception as e:
                log_error(f"Erreur exécution action {effect.type}: {e}")
        else:
            log_error(f"⚠️ Action non gérée : {effect.type}")

    # =========================================================================
    #  HELPERS DE CIBLAGE ET FILTRAGE
    # =========================================================================

    def _get_candidates(self, effect: CardEffect, source: Card, owner: Player, opp: Player) -> List[Any]:
        target_conf = effect.target
        group = target_conf.get("group", "NONE")
        zone = target_conf.get("zone", "BOARD")

        if group == "OWNER": return [owner] if effect.params.get("stat") == "HP" else self._get_zone_content(owner, zone).copy()
        if group == "OPPONENT": return [opp] if effect.params.get("stat") == "HP" else self._get_zone_content(opp, zone).copy()
        if group == "SELF": return [source]

        collection = []
        if group in ["ALLIES", "ALL_ALLIES"]:
            collection = self._get_zone_content(owner, zone).copy()
        elif group == "ALL_OTHER_ALLIES":
            collection = [c for c in self._get_zone_content(owner, zone) if c != source]
        elif group == "ENEMIES":
            collection = self._get_zone_content(opp, zone).copy()
        elif group == "ANY":
            collection = self._get_zone_content(owner, zone).copy() + self._get_zone_content(opp, zone).copy()
        elif group == "BLOCKER":
             # Cas particulier géré en amont ou via contexte, ici simplifié
             pass

        return collection

    def _get_zone_content(self, player: Player, zone_name: str) -> List[Card]:
        if zone_name == "HAND": return player.hand
        if zone_name == "DISCARD": return player.discard
        return player.board

    def _check_global_conditions(self, condition: Dict, owner: Player, opp: Player) -> bool:
        if not condition: return True
        ctx = condition.get("context")
        if not ctx: return True
        
        if ctx == "MY_TURN": return self.game.state.active_player == owner
        if ctx == "IS_ALONE": return len(owner.board) == 1
        if ctx == "FEWER_ALLIES": return len(owner.board) < len(opp.board)
        return True

    def _filter_targets(self, candidates: List[Any], condition: Dict) -> List[Any]:
        if not condition or not candidates: return candidates
        stat = condition.get("stat")
        if not stat: return candidates

        op = condition.get("operator", "EQ")
        val = condition.get("value", 0)
        valid = []
        for c in candidates:
            if isinstance(c, Player):
                valid.append(c)
                continue
            
            # Check sur Card
            check_val = 0
            if stat == "POWER": check_val = c.power
            
            if self._compare(check_val, op, val):
                valid.append(c)
        return valid

    def _compare(self, a, op, b):
        if op == "EQ": return a == b
        if op == "GTE": return a >= b
        if op == "LTE": return a <= b
        if op == "GT": return a > b
        if op == "LT": return a < b
        return False
    
    def _get_owner(self, card_or_player):
        """Helper utilitaire pour récupérer le propriétaire d'une carte."""
        if isinstance(card_or_player, Player): return card_or_player
        p1 = self.state.player1
        # On vérifie toutes les zones
        if card_or_player in p1.hand + p1.board + p1.discard:
            return p1
        return self.state.player2
