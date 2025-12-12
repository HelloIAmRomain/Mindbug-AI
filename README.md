# 🐞 Mindbug Python Implementation

![Build Status](https://img.shields.io/github/actions/workflow/status/HelloIAmRomain/Mindbug-AI/tests.yml?branch=main)
![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)
![Coverage](https://img.shields.io/badge/coverage-81%25-green)
![License](https://img.shields.io/badge/license-MIT-green)

Une implémentation open-source, fidèle et robuste du jeu de cartes **Mindbug : Premier Contact**.

Ce projet a une double vocation :
1.  🎮 **Jeu Jouable (Hotseat) :** Permettre à deux humains de jouer sur le même écran.
2.  🧠 **Laboratoire IA :** Fournir un moteur rigoureux pour entraîner des agents par Renforcement (RL).

---

## ✨ Fonctionnalités (v1.1.1)

Le jeu est **Rules-Complete**. Toutes les mécaniques du set de base sont implémentées :

* **Moteur de Jeu (Backend) :**
    * Machine à états complète (Main, Mindbug, Block, Resolution).
    * Gestion du **Mindbug Replay** (La victime rejoue son tour après un vol).
    * Calculs dynamiques de puissance (Buffs, Debuffs, Auras).
    * Mots-clés dynamiques (ex: *Requin Crabe*).
    * Interruption de combat sur mort (ex: *Crapaud Bombe*).
    * Mécaniques avancées : **Furie** (Double attaque), **Coriace**, **Chasseur**, **Venimeux**.

* **Interface Graphique (Frontend) :**
    * Rendu PyGame fluide (1280x768).
    * **Feedback Visuel :** Surbrillance verte pour les coups légaux.
    * **Gestion Défausse :** Overlay interactif pour consulter ou récupérer des cartes (*Dracompost*).
    * Indicateurs de puissance colorés (Vert=Buff, Rouge=Debuff).

* **Infrastructure :**
    * Compilation automatique en `.exe` (Windows/Linux) via GitHub Actions.
    * Tests unitaires et d'intégration robustes.

---

## 🚀 Installation & Lancement

### Pour les Joueurs (Exécutable)
Pas besoin d'installer Python !
1.  Allez dans la section **[Releases](https://github.com/VOTRE_USERNAME/NOM_DU_REPO/releases)** du dépôt.
2.  Téléchargez la dernière version pour votre OS :
    * Windows : `MindbugAI-Windows.exe`
    * Linux : `MindbugAI-Linux`
3.  Lancez le fichier.

### Pour les Développeurs (Source)

**Pré-requis :** Python 3.12+

1.  **Cloner le dépôt :**
    ```bash
    git clone [https://github.com/VOTRE_USERNAME/NOM_DU_REPO.git](https://github.com/VOTRE_USERNAME/NOM_DU_REPO.git)
    cd mindbug-ai
    ```

2.  **Installer les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Lancer le jeu :**
    ```bash
    python main.py
    ```

---

## 🎮 Contrôles

* **Clic Gauche :** Jouer une carte, Attaquer, Bloquer, Choisir une cible.
* **Clic sur la Défausse (gauche) :** Ouvrir l'overlay pour voir les cartes détruites.
* **Touche `D` :** Activer/Désactiver le **Mode Debug** (Voir les cartes de l'adversaire).
* **Touche `ECHAP` :** Fermer l'overlay de défausse.

---

## 🏗️ Architecture Technique

Le projet respecte une séparation stricte des responsabilités pour faciliter l'intégration future de l'IA.

| Dossier | Description |
| :--- | :--- |
| **`mindbug_engine/`** | **Le Cerveau.** Logique pure, sans aucune dépendance graphique. Contient la machine à états, les règles et les effets. |
| **`mindbug_gui/`** | **Le Visage.** Gère l'affichage PyGame et les inputs souris. Ne prend aucune décision logique. |
| **`data/`** | **Les Données.** Contient `cards.json` (définition des 32 cartes). |
| **`tests/`** | **La Qualité.** Tests unitaires et d'intégration (`pytest`). |

---

## ✅ Tests & Qualité

Le projet maintient une couverture de code élevée (> 80%) pour garantir la non-régression des règles complexes.

Pour lancer les tests :
```bash
pytest tests/
````

Pour générer le rapport de couverture :

```bash
pytest --cov=mindbug_engine --cov-report=html tests/
```

-----

## 📦 Créer une Release (CI/CD)

Le déploiement est automatisé via **GitHub Actions**.

1.  Ne jamais pousser directement sur `main`. Passer par des Pull Requests.
2.  Pour publier une nouvelle version, créez un **Tag** git :
    ```bash
    git tag v1.2.0
    git push origin v1.2.0
    ```
3.  La CI va automatiquement lancer les tests, compiler les exécutables et créer une Release GitHub.

-----

## 🔮 Roadmap

  * [x] Moteur de règles complet (v1.0)
  * [x] Interface graphique jouable (v1.1)
  * [x] Système de sélection interactif & Défausse (v1.1.1)
  * [ ] **Environnement Gym pour IA (Prochaine étape)**
  * [ ] Entraînement d'agents (PPO/DQN)
  * [ ] Animations visuelles (Polish)

-----

## 📄 Crédits

  * **Jeu original :** Mindbug (Conçu par Christian Kudahl, Marvin Hegen, Richard Garfield, Skaff Elias).
  * **Développement :** [Votre Nom]
  * **Licence :** MIT (Voir fichier LICENSE).

