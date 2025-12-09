from mindbug_engine.engine import MindbugGame
from mindbug_engine.models import Card

def run_complex_scenario():
    print("🎬 === DÉBUT DU SCÉNARIO COMPLEXE MINDBUG (CORRIGÉ) === 🎬\n")
    
    # 1. SETUP MANUEL
    game = MindbugGame()
    p1 = game.player1
    p2 = game.player2
    
    p1.hand = []
    p2.hand = []
    p1.board = []
    p2.board = []
    
    # CORRECTION ICI : On utilise les arguments nommés (id=..., name=...)
    # pour éviter le décalage des données.
    
    # P1 aura : Poison, Furtif
    card_poison = Card(id="t1", name="Spore Étrange", power=2, keywords=["POISON"])
    card_sneaky = Card(id="t2", name="Chauve-souris", power=4, keywords=["SNEAKY"])
    p1.hand = [card_poison, card_sneaky]
    
    # P2 aura : Un Gros Thon, un Chasseur, un Coriace
    card_big = Card(id="t3", name="Gorillion", power=10, keywords=[])
    card_hunter = Card(id="t4", name="Abeille T.", power=5, keywords=["HUNTER"])
    card_tough = Card(id="t5", name="Ours Blindé", power=6, keywords=["TOUGH"])
    p2.hand = [card_big, card_hunter, card_tough]

    game.render()

    # --- TOUR 1 : LE VOL (MINDBUG) ---
    print("\n--- ACTE 1 : Le Vol du Gorille ---")
    
    game.step("PLAY", 0) # P1 joue Spore
    game.step("PASS")    # P2 pass
    
    game.step("PLAY", 0) # P2 joue Gorillion
    print(">>> P1 décide d'utiliser un Mindbug sur le Gorillion !")
    game.step("MINDBUG") # P1 vole !
    
    if card_big in p1.board:
        print("✅ SUCCÈS : Le Gorillion est chez P1.")
    else:
        print("❌ ÉCHEC : Le Mindbug n'a pas fonctionné.")
        
    game.render()

    # --- TOUR 2 : L'ATTAQUE FURTIVE ---
    print("\n--- ACTE 2 : L'Attaque Furtive ---")
    
    game.step("PLAY", 0) # P1 joue Bat
    game.step("PASS")
    
    game.step("PLAY", 0) # P2 joue Abeille
    game.step("PASS")
    
    # P1 attaque avec Chauve-souris Furtive
    bat_idx = p1.board.index(card_sneaky)
    game.step("ATTACK", bat_idx)
    
    print(">>> P2 essaie de bloquer avec l'Abeille (Non-Furtive)...")
    bee_idx = p2.board.index(card_hunter)
    game.step("BLOCK", bee_idx)
    
    # VERIFICATION : Le blocage doit échouer
    if p2.hp == 2:
        print("✅ SUCCÈS : P2 a perdu 1 PV (Blocage illégal ignoré).")
    elif p2.hp == 3:
         print("❌ ÉCHEC : P2 a toujours 3 PV (Le blocage a fonctionné alors qu'il ne devait pas).")
    
    # L'abeille doit être vivante car le combat n'a pas eu lieu (ou a été ignoré)
    if card_hunter in p2.board:
        print("✅ SUCCÈS : L'abeille est toujours en vie.")
    else:
        print("❌ ÉCHEC : L'abeille est morte (Le combat a eu lieu).")

    game.render()

    # --- TOUR 3 : LE CHASSEUR ---
    print("\n--- ACTE 3 : Le Chasseur devient la proie ---")
    
    # P2 attaque avec Abeille. 
    # IMPORTANT: On réactualise l'index car le board a pu bouger (retrait de cartes, etc)
    if card_hunter in p2.board:
        bee_idx = p2.board.index(card_hunter)
        # Cible le Spore Poison (Index du Spore chez P1)
        spore_idx = p1.board.index(card_poison)
        
        game.step("ATTACK", bee_idx, target_blocker_idx=spore_idx)
        
        if card_hunter not in p2.board and card_poison not in p1.board:
            print("✅ SUCCÈS : Double KO (Force vs Poison).")
        else:
            print("❌ ÉCHEC : Les créatures ne sont pas mortes comme prévu.")
    else:
        print("⛔ CRASH EVITÉ : L'abeille n'est pas sur le plateau (Echec Acte 2).")

    game.render()

    # --- TOUR 4 : LE CORIACE (TOUGH) ---
    print("\n--- ACTE 4 : L'Ours Inamovible ---")
    
    # Vérifions si P2 a survécu pour jouer son Ours
    if game.winner:
        print("Partie déjà finie.")
        return

    # P2 a besoin de poser l'Ours s'il l'a encore en main
    if card_tough in p2.hand:
        # C'est à qui ? Si P2 vient d'attaquer, c'est à P1.
        # P1 attaque avec Gorille.
        gorille_idx = p1.board.index(card_big)
        game.step("ATTACK", gorille_idx)
        
        # P2 prend la claque (pas de bloqueur posé)
        game.step("NO_BLOCK")
        print(">>> P2 prend une claque du Gorillion (-1 PV).")

        # Maintenant P2 pose l'Ours
        game.step("PLAY", 0) 
        game.step("PASS")
    
    # P1 attaque encore avec Gorillion
    if card_big in p1.board:
        gorille_idx = p1.board.index(card_big)
        game.step("ATTACK", gorille_idx)
        
        # P2 bloque avec Ours
        if card_tough in p2.board:
            bear_idx = p2.board.index(card_tough)
            game.step("BLOCK", bear_idx)
            
            if card_tough.is_damaged:
                print("✅ SUCCÈS : L'Ours est blessé mais vivant.")
            else:
                print("❌ ÉCHEC : L'Ours n'est pas marqué blessé.")

    game.render()
    print("\n🏁 === FIN DU SCÉNARIO === 🏁")

if __name__ == "__main__":
    run_complex_scenario()
