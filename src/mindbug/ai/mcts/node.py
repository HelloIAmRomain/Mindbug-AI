import math
import random


class MCTSNode:
    """
    Nœud de l'arbre MCTS.
    Représente un état du jeu atteint après une séquence d'actions.
    """

    def __init__(self, move=None, parent=None, state=None):
        """
        :param move: Le coup (Action, Index) qui a mené à ce nœud.
        :param parent: Le nœud parent.
        :param state: L'état du jeu (GameState) à ce nœud. 
                      Sert uniquement à l'initialisation des coups possibles (untried_moves).
        """
        self.move = move
        self.parent = parent
        self.children = []

        self.wins = 0.0
        self.visits = 0

        # Qui a joué pour arriver ici ? (Indispensable pour savoir à qui attribuer la victoire)
        # Si state est None (Racine), on l'initialisera manuellement dans l'agent
        self.player_just_moved = state.state.active_player_idx if state else -1

        # Liste des coups légaux possibles depuis cet état
        # On les stocke pour l'étape d'Expansion
        self.untried_moves = state.get_legal_moves() if state else []

    def uct_select_child(self, exploration_weight=1.41):
        """
        Sélectionne l'enfant le plus prometteur selon la formule UCB1.
        Maximise : (WinRate) + C * sqrt(ln(ParentVisits) / ChildVisits)
        """
        # Pour éviter la division par zéro, on peut ajouter un petit epsilon ou s'assurer que c.visits > 0
        # (Dans notre algo, un enfant n'est ajouté que s'il a été visité au moins une fois lors de sa création)
        selected = max(self.children, key=lambda c:
                       (c.wins / c.visits) + exploration_weight *
                       math.sqrt(math.log(self.visits) / c.visits)
                       )
        return selected

    def add_child(self, move, state, player_index):
        """
        Ajoute un enfant correspondant au coup `move`.
        :param state: L'état du jeu APRES avoir joué le coup.
        :param player_index: L'index du joueur QUI A FAIT ce coup.
        """
        child = MCTSNode(move=move, parent=self, state=state)
        child.player_just_moved = player_index
        self.children.append(child)
        return child

    def update(self, result):
        """
        Met à jour les statistiques (Backpropagation).
        :param result: 1 si le joueur de ce nœud a gagné, 0 sinon.
        """
        self.visits += 1
        self.wins += result

    def __repr__(self):
        return f"<Node mv={self.move} w/v={self.wins}/{self.visits} children={len(self.children)}>"
