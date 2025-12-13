from dataclasses import dataclass, field
from typing import List

@dataclass
class GameConfig:
    # Général
    debug_mode: bool = False
    enable_sound: bool = True
    enable_effects: bool = True
    
    # Mode de Jeu : "HOTSEAT" (2 joueurs local), "VS_AI", "SOLO"
    game_mode: str = "HOTSEAT" 
    
    # Deck Building
    # Si vide, le moteur chargera tout le deck.
    active_card_ids: List[str] = field(default_factory=list)
