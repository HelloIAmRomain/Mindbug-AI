import random
from typing import List, Dict, Any, Callable, TYPE_CHECKING, Optional

from mindbug_engine.core.models import Card, Player, CardEffect
from mindbug_engine.core.consts import Trigger, EffectType, Keyword
from mindbug_engine.utils.logger import log_info, log_error

if TYPE_CHECKING:
    from mindbug_engine.engine import MindbugGame


class EffectManager:
    """
    Moteur d'effets V3 (Data-Driven).
    Responsable de l'exécution des verbes (MODIFY_STAT, DESTROY, STEAL...)
    et de la gestion des effets passifs (Auras).
    """

    def __init__(self, game: 'MindbugGame'):
        self.game = game
        self.state = game.state
        self.combat_manager = game.combat_manager
        self.turn_manager = game.turn_manager

        # MAPPING : Verbe -> Méthode d'exécution
        self._verb_handlers: Dict[str, Callable] = {
            EffectType.MODIFY_STAT: self._execute_modify_stat,
            EffectType.DESTROY: self._execute_destroy,
            EffectType.STEAL: self._execute_steal,
            EffectType.DISCARD: self._execute_discard,
            EffectType.PLAY: self._execute_play,
            EffectType.MOVE: self._execute_move,
            EffectType.ADD_KEYWORD: self._execute_add_keyword,
            EffectType.COPY_KEYWORDS: self._execute_copy_keywords,
            EffectType.BAN: lambda t, p, s: None,  # Passif géré par Rules ou Engine
        }

    # =========================================================================
    #  A. EFFETS ACTIFS (One-Shot)
    # =========================================================================

    def apply_effect(self, card: Card, owner: Player, opponent: Player):
        """
        Point d'entrée pour les effets déclenchés (ON_PLAY, ON_DEATH...).
        """
        if not card.effects:
            return

        for effect in card.effects:
            # 1. Vérification des conditions globales (Contexte)
            if not self._check_global_conditions(effect.condition, owner, opponent):
                continue

            # 2. Traitement de l'effet
            self._process_single_effect(effect, card, owner, opponent)

    def _process_single_effect(self, effect: CardEffect, source_card: Card, owner: Player, opponent: Player):
        """Pipeline de résolution : Candidats -> Filtres -> Sélection -> Exécution."""

        # 1. IDENTIFICATION DES CANDIDATS
        candidates = self._get_candidates(effect, source_card, owner, opponent)

        # 2. FILTRAGE (Conditions sur les cibles)
        valid_targets = self._filter_targets(candidates, effect.condition)

        # Si pas de cibles valides et que ce n'est pas une sélection forcée, on arrête
        # (Sauf si l'effet ne nécessite pas de cible explicite, mais rare ici)
        if not valid_targets:
            return

        # 3. SÉLECTION (Auto vs Manuel)
        select_method = effect.target.get("select", "ALL")
        count = effect.target.get("count", 1)

        # --- DÉFINITION DU CALLBACK (Logique de suite) ---
        def on_selection_complete(selected_targets):
            for target in selected_targets:
                self._dispatch_verb(effect, target, source_card, owner, opponent)

        # -------------------------------------------------

        if select_method == "ALL":
            # Ex: Kangousaurus Rex (Détruit tout le monde qui correspond)
            on_selection_complete(valid_targets)

        elif select_method == "RANDOM":
            # Ex: Baril étrange, Huissiéléphant
            nb = len(valid_targets) if count == "ALL" else count
            picked = random.sample(valid_targets, min(nb, len(valid_targets)))
            on_selection_complete(picked)

        elif select_method == "CHOICE_USER" or select_method == "CHOICE_OPP":
            chooser = owner if select_method == "CHOICE_USER" else opponent

            # Appel à l'Engine pour gérer l'UI / State
            self.game.ask_for_selection(
                candidates=valid_targets,
                reason=effect.type,
                count=count,
                selector=chooser,
                callback=on_selection_complete
            )
            return

        else:
            # Fallback (AUTO)
            on_selection_complete(valid_targets)

    def _dispatch_verb(self, effect, target, source, owner, opp):
        handler = self._verb_handlers.get(effect.type)
        if handler:
            # On passe owner/opp car certains verbes (Copy Keywords, Modify Stat Copy) en ont besoin
            handler(target, effect.params, source, owner, opp)
        else:
            log_error(f"⚠️ Verbe inconnu : {effect.type}")

    # =========================================================================
    #  B. EFFETS PASSIFS (Auras / Continus)
    # =========================================================================

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
                    if effect.type == EffectType.BAN: continue

                    if not self._check_global_conditions(effect.condition, owner, opp):
                        continue

                    # Récupération des cibles (En passant 'card' comme source pour exclusion SELF)
                    raw_candidates = self._get_candidates(effect, card, owner, opp)
                    targets = self._filter_targets(raw_candidates, effect.condition)

                    for t in targets:
                        self._dispatch_verb(effect, t, card, owner, opp)

    # =========================================================================
    #  C. LOGIQUE DE CIBLAGE (TARGETING)
    # =========================================================================

    def _get_candidates(self, effect: CardEffect, source: Card, owner: Player, opp: Player) -> List[Any]:
        target_conf = effect.target
        group = target_conf.get("group", "NONE")
        zone = target_conf.get("zone", "BOARD")

        # 1. Cibles Joueurs
        target_player = None
        if group == "OWNER":
            target_player = owner
        elif group == "OPPONENT":
            target_player = opp

        if target_player:
            # Si l'effet vise une STAT du joueur (HP), la cible est le Joueur lui-même
            if effect.params.get("stat") == "HP":
                return [target_player]

            # Sinon, c'est le contenu d'une zone du joueur (Hand, Discard...)
            return self._get_zone_content(target_player, zone).copy()

        # 2. Cibles Cartes (Collections)
        collection = []

        if group == "SELF":
            return [source]

        elif group == "ALLIES" or group == "ALL_ALLIES":
            collection = self._get_zone_content(owner, zone).copy()

        elif group == "ALL_OTHER_ALLIES":
            # CRITIQUE : Exclure la source (Scarabouclier ne se buff pas lui-même)
            content = self._get_zone_content(owner, zone)
            collection = [c for c in content if c != source]

        elif group == "ENEMIES":
            collection = self._get_zone_content(opp, zone).copy()

        elif group == "ANY":
            collection = self._get_zone_content(owner, zone).copy() + self._get_zone_content(opp, zone).copy()

        elif group == "BLOCKER":
            if self.state.blocker:
                return [self.state.blocker]

        return collection

    def _get_zone_content(self, player: Player, zone_name: str) -> List[Card]:
        if zone_name == "HAND": return player.hand
        if zone_name == "DISCARD": return player.discard
        return player.board

    # =========================================================================
    #  D. LOGIQUE DE FILTRAGE
    # =========================================================================

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
        # Si la condition porte sur un contexte global (déjà vérifié) et pas sur une stat, on renvoie tout
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
        if op == "NEQ": return a != b
        if op == "GT": return a > b
        if op == "GTE": return a >= b
        if op == "LT": return a < b
        if op == "LTE": return a <= b
        return False

    # =========================================================================
    #  E. HANDLERS (EXÉCUTION)
    # =========================================================================

    def _execute_modify_stat(self, target, params, source, owner, opp):
        stat = params.get("stat", "HP")
        op = params.get("operation", "SUB")
        val = params.get("amount", 0)

        current_val = 0
        is_hp = (stat == "HP" and hasattr(target, "hp"))
        is_power = (stat == "POWER" and hasattr(target, "power"))

        if is_hp:
            current_val = target.hp
        elif is_power:
            current_val = target.power
        else:
            return

        # Gestion COPY (Sirène Mystérieuse)
        if op == "COPY":
            src_str = params.get("source")
            if src_str == "OPPONENT":
                # Si la cible est P1, l'opposant est P2
                opp_player = opp if target == owner else owner
                val = opp_player.hp
                op = "SET"

        # Calcul
        new_val = current_val
        if op == "ADD":
            new_val += val
        elif op == "SUB":
            new_val -= val
        elif op == "SET":
            new_val = val

        # Application
        if is_hp:
            target.hp = max(0, new_val)
            log_info(f"   -> {getattr(target, 'name', 'Player')} HP modified to {target.hp}")
            self.game.check_game_over()
        elif is_power:
            target.power = max(0, new_val)

    def _execute_destroy(self, target, params, source, owner, opp):
        if isinstance(target, Card):
            card_owner = self._get_owner(target)
            # Utilise le combat manager pour gérer trigger de mort et déplacement
            self.combat_manager.apply_lethal_damage(target, card_owner)

    def _execute_steal(self, target, params, source, owner, opp):
        # target est l'objet à voler. 'owner' est le voleur (celui qui joue l'effet)
        thief = owner
        victim = self._get_owner(target)

        if not victim or thief == victim: return  # On ne se vole pas soi-même

        # Voler sur le plateau
        if target in victim.board:
            victim.board.remove(target)
            thief.board.append(target)
            log_info(f"   -> {thief.name} steals {target.name} (Board)")

        # Voler dans la main (Baril)
        elif target in victim.hand:
            victim.hand.remove(target)
            thief.hand.append(target)
            self.turn_manager.refill_hand(victim)
            log_info(f"   -> {thief.name} steals a card from Hand")

    def _execute_discard(self, target, params, source, owner, opp):
        card_owner = self._get_owner(target)
        if target in card_owner.hand:
            card_owner.hand.remove(target)
            card_owner.discard.append(target)
            self.turn_manager.refill_hand(card_owner)
            log_info(f"   -> {target.name} discarded")

    def _execute_play(self, target, params, source, owner, opp):
        # Dracompost / Pilleur de tombes
        # target est la carte dans la défausse
        card_owner = self._get_owner(target)

        # Elle peut être dans la défausse de n'importe qui
        if target in card_owner.discard:
            card_owner.discard.remove(target)
            # Elle arrive sur le plateau de celui qui a joué l'effet (owner)
            self.game.put_card_on_board(owner, target)
            target.reset()
            log_info(f"   -> {target.name} played from discard")

    def _execute_move(self, target, params, source, owner, opp):
        # Giraffodile (Discard -> Hand)
        dest = params.get("destination")
        card_owner = self._get_owner(target)

        if target in card_owner.discard and dest == "HAND":
            card_owner.discard.remove(target)
            target.reset()
            card_owner.hand.append(target)
            log_info(f"   -> {target.name} returned to Hand")

    def _execute_add_keyword(self, target, params, source, owner, opp):
        kws = params.get("keywords", [])
        if isinstance(kws, str): kws = [kws]
        for kw_str in kws:
            try:
                kw = Keyword(kw_str)
                if kw not in target.keywords:
                    target.keywords.append(kw)
            except ValueError:
                pass

    def _execute_copy_keywords(self, target, params, source, owner, opp):
        # Requin Crabe : Copie depuis "ENEMIES" (source défini dans JSON)
        source_group_name = params.get("source")

        if not source_group_name:
            # Fallback: Copie depuis la carte source elle-même (rare)
            sources = [source]
        else:
            # On simule un effet fictif pour récupérer le groupe via _get_candidates
            # On utilise owner/opp passés en paramètres
            fake_effect = CardEffect(EffectType.COPY_KEYWORDS, target={"group": source_group_name})
            sources = self._get_candidates(fake_effect, source, owner, opp)

        for src in sources:
            if isinstance(src, Card):
                for kw in src.keywords:
                    if kw not in target.keywords:
                        target.keywords.append(kw)

    # =========================================================================
    #  HELPERS
    # =========================================================================

    def _get_owner(self, card_or_player):
        if isinstance(card_or_player, Player): return card_or_player
        p1 = self.state.player1
        if card_or_player in p1.hand + p1.board + p1.discard:
            return p1
        return self.state.player2