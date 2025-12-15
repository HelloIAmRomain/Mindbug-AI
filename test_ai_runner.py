from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card
from mindbug_ai.agent import MindbugAgent

def run_ai_test():
    print("--- Démarrage du Test IA ---")
    
    # 1. Création d'une partie
    game = MindbugGame()
    
    # 2. Setup d'une situation critique pour aider l'IA
    # L'adversaire (P2) a une carte très forte (10)
    # L'IA (P1) a un Mindbug
    p1 = game.player1
    p2 = game.player2
    
    # On force la main pour le test
    # P1 joue une petite carte
    weak_card = Card("weak", "Weakling", 1)
    p1.hand = [weak_card]
    
    # P2 a un monstre
    monster = Card("monster", "Godzilla", 10)
    p2.hand = [monster]
    
    print("Situation Initiale :")
    print(f"P1 (IA) Hand: {[c.name for c in p1.hand]}")
    print(f"P2 (Opp) Hand: {[c.name for c in p2.hand]}")
    
    # --- TOUR 1 : P1 joue ---
    agent = MindbugAgent(name="Brainiac", level=5) # Niveau bas pour aller vite
    
    print("\n[IA] Réfléchit pour jouer une carte...")
    move = agent.get_move(game)
    print(f"👉 Décision IA : {move}")
    
    # On applique le coup
    game.step(move[0], move[1])
    
    # --- TOUR 2 : P2 joue le Monstre ---
    print(f"\n[Humain] Joue {monster.name}...")
    game.step("PLAY", 0) # P2 joue Godzilla
    
    # --- MOMENT DE VÉRITÉ ---
    # C'est à P1 (IA) de décider : Mindbug ou Pas ?
    # Godzilla est une 10/10, l'IA DOIT utiliser son Mindbug si elle est maligne (ou chanceuse en simu)
    
    print("\n[IA] Réfléchit : Mindbug ou Pas ?")
    move = agent.get_move(game)
    print(f"👉 Décision IA : {move}")
    
    if move and move[0] == "MINDBUG":
        print("✅ SUCCÈS : L'IA a volé le monstre !")
    elif move and move[0] == "PASS":
        print("❌ ECHEC : L'IA a laissé passer (peut arriver si niveau faible)")
    else:
        print(f"⚠️ Bizarre : {move}")

if __name__ == "__main__":
    run_ai_test()
