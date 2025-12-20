from typing import Tuple, TYPE_CHECKING
from mindbug_engine.core.consts import Keyword

if TYPE_CHECKING:
    from mindbug_engine.core.models import Card


class CombatUtils:
    @staticmethod
    def simulate_combat(attacker: 'Card', blocker: 'Card',
                        override_att_power=None, override_blk_power=None) -> Tuple[bool, bool]:
        p_att = override_att_power if override_att_power is not None else attacker.power
        p_blk = override_blk_power if override_blk_power is not None else blocker.power

        att_dead = False
        blk_dead = False

        if p_att > p_blk:
            blk_dead = True
        elif p_blk > p_att:
            att_dead = True
        else:
            att_dead = True
            blk_dead = True

        return att_dead, blk_dead

    @staticmethod
    def can_block(attacker: 'Card', blocker: 'Card') -> bool:
        if Keyword.SNEAKY.value in attacker.keywords:
            if Keyword.SNEAKY.value not in blocker.keywords:
                return False

        if attacker.effects:
            for eff in attacker.effects:
                if eff.type == "BAN" and eff.params.get("action") == "BLOCK":
                    if CombatUtils._check_ban_condition(blocker, eff.condition):
                        return False
        return True

    @staticmethod
    def _check_ban_condition(card: 'Card', condition: dict) -> bool:
        if not condition: return True
        stat = condition.get("stat")
        op = condition.get("operator")
        val = condition.get("value", 0)

        check_val = card.power if stat == "POWER" else 0

        if op == "LTE": return check_val <= val
        if op == "LT": return check_val < val
        if op == "GTE": return check_val >= val
        if op == "GT": return check_val > val
        if op == "EQ": return check_val == val
        return False