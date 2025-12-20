from typing import Optional, Tuple, TYPE_CHECKING
from mindbug_engine.core.models import Card, Player
from mindbug_engine.core.consts import Keyword, Trigger
from mindbug_engine.utils.logger import log_info, log_debug

if TYPE_CHECKING:
    from mindbug_engine.engine import MindbugGame
    from mindbug_engine.managers.effect_manager import EffectManager


class CombatManager:
    """
    Gère la résolution mathématique et logique des combats.

    Responsabilités :
    1. Déterminer le vainqueur d'un duel (Puissance + Poison).
    2. Gérer la survie (Tenace/Tough).
    3. Gérer la mort (Déplacement vers Cimetière + Trigger ON_DEATH).
    4. Appliquer les dégâts aux joueurs.
    """

    def __init__(self, game: 'MindbugGame', effect_manager: Optional['EffectManager'] = None):
        self.game = game
        self.state = game.state
        # Sera injecté par l'Engine après l'init croisé
        self.effect_manager = effect_manager

    def resolve_fight(self, attacker: Card, blocker: Optional[Card]) -> Tuple[bool, bool]:
        """
        Résout le combat.
        Retourne (attacker_died, blocker_died).
        """
        if not attacker:
            return False, False

        att_owner = self._get_owner(attacker)
        # L'adversaire est celui qui défend (propriétaire du bloqueur ou joueur attaqué)
        def_owner = self.state.player2 if att_owner == self.state.player1 else self.state.player1

        # --- CAS 1 : ATTAQUE DIRECTE (Pas de bloqueur) ---
        if not blocker:
            # Vérification Trigger ON_UNBLOCKED (ex: Turboustique)
            if attacker.trigger == Trigger.ON_UNBLOCKED:
                log_info(f"⚡ Trigger {Trigger.ON_UNBLOCKED} activated for {attacker.name}.")
                self.effect_manager.apply_effect(attacker, att_owner, def_owner)

            # Dégâts normaux (si pas d'effet spécifique qui annule l'attaque)
            damage = attacker.power
            # Sécurité : un monstre à 0 power ne fait pas de dégâts (sauf règle spéciale)
            if damage > 0:
                log_info(f"⚔️ Direct Attack! {attacker.name} deals {damage} damage to {def_owner.name}.")
                def_owner.hp -= 1  # Dans Mindbug, c'est souvent 1 PV perdu par attaque non bloquée, peu importe la force ?
                # Note : Les règles standard Mindbug disent "Perd 1 PV". Si vous jouez avec "Dégâts = Puissance", changez en -= damage.
                # Ici je mets -1 PV par défaut comme le jeu physique standard.
                if def_owner.hp < 0: def_owner.hp = 0
            else:
                log_info(f"⚔️ {attacker.name} has 0 power, no damage dealt.")

            return False, False

        # --- CAS 2 : COMBAT DE CRÉATURES ---

        # 1. Trigger ON_BLOCKED (ex: Effet qui tue le bloqueur avant le combat)
        if attacker.trigger == Trigger.ON_BLOCKED:
            log_info(f"⚡ Trigger {Trigger.ON_BLOCKED} activated for {attacker.name}")
            self.effect_manager.apply_effect(attacker, att_owner, def_owner)

            # Si le bloqueur a été retiré par l'effet (ex: détruit), le combat s'arrête
            if blocker not in def_owner.board:
                log_info(f"> Blocker removed by effect. Combat ends.")
                return False, True  # Attaquant vivant, Bloqueur considéré mort/parti

        # 2. Logique de Combat (Puissance & Mots-clés)
        log_info(f"⚔️ Combat : {attacker.name} ({attacker.power}) vs {blocker.name} ({blocker.power})")

        att_poison = Keyword.POISON in attacker.keywords
        blk_poison = Keyword.POISON in blocker.keywords

        att_die = False
        blk_die = False

        # A. Comparaison Puissance
        if attacker.power > blocker.power:
            blk_die = True
        elif blocker.power > attacker.power:
            att_die = True
        else:
            # Égalité
            att_die = True
            blk_die = True

        # B. Application Poison (L'emporte sur la puissance)
        if att_poison: blk_die = True
        if blk_poison: att_die = True

        # C. Sauvegarde Tenace (Tough)
        # Si la créature doit mourir, on check si elle a un bouclier
        att_die = self._apply_tough_save(attacker, att_die)
        blk_die = self._apply_tough_save(blocker, blk_die)

        # 3. Application des Morts (Physique + Triggers)
        if att_die:
            log_info(f"   -> 💀 {attacker.name} is destroyed.")
            self.apply_lethal_damage(attacker, att_owner)

        if blk_die:
            log_info(f"   -> 💀 {blocker.name} is destroyed.")
            blk_owner = self._get_owner(blocker)  # Sécurité si ownership change
            self.apply_lethal_damage(blocker, blk_owner)

        return att_die, blk_die

    def apply_lethal_damage(self, card: Card, owner: Player):
        """
        Gère la destruction d'une carte :
        Retrait du plateau -> Ajout Défausse -> Trigger ON_DEATH.
        """
        # 1. Déplacement physique
        if card in owner.board:
            owner.board.remove(card)
            owner.discard.append(card)

        # 2. Reset (on retire les dégâts, buffs temporaires, etc.)
        card.reset()

        # 3. Trigger ON_DEATH (Dernier Souffle)
        if card.trigger == Trigger.ON_DEATH:
            log_debug(f"⚡ Trigger ON_DEATH activated for {card.name}")

            opponent = self.state.player2 if owner == self.state.player1 else self.state.player1

            if self.effect_manager:
                self.effect_manager.apply_effect(card, owner, opponent)
            else:
                log_debug("⚠️ EffectManager not linked in CombatManager!")

    def _apply_tough_save(self, card: Card, is_dying: bool) -> bool:
        """
        Gère la survie via Tenace (Tough).
        """
        # Si la carte doit mourir ET qu'elle a TOUGH (donc pas encore damaged ou base tough)
        if is_dying and Keyword.TOUGH in card.keywords:
            log_info(f"   🛡️ {card.name} uses TOUGH ! It survives.")

            # On marque le dégât. Le Keyword sera retiré au prochain update_board_states()
            card.is_damaged = True

            return False  # La carte ne meurt pas

        return is_dying

    def calculate_real_power(self, card: Card, owner: Player, opponent: Player) -> int:
        """
        (Obsolète/Helper) Retourne la puissance actuelle.
        Dans l'architecture V3, Engine.update_board_states() met à jour card.power en amont.
        """
        return card.power

    def _get_owner(self, card: Card) -> Player:
        p1 = self.state.player1
        if card in p1.board:
            return p1
        return self.state.player2