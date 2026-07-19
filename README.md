# Wend'Kugri — « Le Lieu de la Connaissance »

Réseau social éducatif pour le Burkina Faso. Seules les publications qui
apportent une connaissance sont autorisées : pas de buzz, pas de gossip.

Copyright by **Computer Science Solution-BF**

---

## 1. Installation

Prérequis : Python 3.10+

```bash
# 1. Se placer dans le dossier du projet
cd wendkugri

# 2. (Recommandé) Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate        # Sous Windows : venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Initialiser la base de données + comptes/publications de démonstration
python seed.py

# 5. Lancer l'application
python app.py
```

Ouvrir ensuite **http://127.0.0.1:5000** dans le navigateur (idéalement en
mode mobile / responsive dans les outils développeur, l'app est conçue
mobile-first).

> Relancer `python seed.py` à tout moment réinitialise complètement la base
> (elle est effacée puis recréée avec des données propres).

## 2. Comptes de test

| Email                  | Mot de passe   | Profil                                      |
|-------------------------|----------------|----------------------------------------------|
| aicha@wendkugri.bf      | motdepasse123  | Développeur, Ouaga, Avancé — Contributeur Vérifié |
| issa@wendkugri.bf       | motdepasse123  | Agriculture, Bobo-Dioulasso, Expert — Contributeur Vérifié |
| fatim@wendkugri.bf      | motdepasse123  | Santé, Koudougou, Intermédiaire             |

5 publications de démonstration sont créées (une de chaque type, avec un
second exemple de type "Astuce"), plus un Défi du Jour et un Groupe d'Étude.

## 3. Structure du projet

```
wendkugri/
├── app.py                  # Routes Flask, authentification, logique métier
├── models.py                # Modèles SQLAlchemy (tables SQLite)
├── ia_wendkugri.py          # Modération anti-désordre + résumé PDF ("IA" locale)
├── seed.py                  # Script de données de démonstration
├── requirements.txt
├── instance/wendkugri.db    # Base SQLite (créée automatiquement)
├── uploads/
│   ├── cours/                # PDF, PPT, DOC uploadés
│   └── videos/                # Vidéos uploadées (< 5 min)
├── static/
│   ├── style.css              # Styles complémentaires à Tailwind
│   └── app.js                  # Likes AJAX, signalement, hors-ligne, etc.
└── templates/
    ├── base.html, index.html, _fiche_publication.html
    ├── inscription.html, connexion.html
    ├── publier.html, detail_publication.html
    ├── profil.html, modifier_profil.html
    ├── bibliotheque.html, defi.html
    └── groupes.html, detail_groupe.html, classement.html
```

## 4. Fonctionnalités livrées dans cette V1

- Inscription / connexion par email **ou** téléphone burkinabè + mot de passe.
- Profil avec domaine d'expertise, ville, niveau, badge **Contributeur
  Vérifié** (attribué automatiquement à partir de 300 points).
- Fil "Savoir" limité à 4 types de publication (Astuce, Cours, Vidéo,
  Question), tag domaine obligatoire, bouton Publier désactivé tant que le
  domaine n'est pas choisi.
- **Modération IA anti-désordre** : chaque publication passe par des règles
  automatiques (`ia_wendkugri.py`) avant mise en ligne.
- Signalement communautaire : 3 signalements masquent automatiquement une
  publication.
- Filtres par domaine et par ville.
- **Wend'Kugri IA** : résumé automatique d'un PDF en 5 points clés (méthode
  extractive locale, sans dépendance externe).
- Défi du Jour, Groupes d'Étude (salon écrit), Bibliothèque BF (tous les
  cours classés), Classement mensuel des "Maîtres du Savoir".
- Gamification par points de Connaissance (publication, like reçu, réponse
  utile, bonne réponse au défi).
- Sauvegarde "hors-ligne" de 10 cours maximum (voir limite ci-dessous).

## 5. Limites connues de cette V1 (honnêteté technique)

Certaines fonctionnalités du cahier des charges sont volontairement livrées
sous une forme **simplifiée et fonctionnelle**, plutôt que simulées de façon
trompeuse :

- **Modération "IA"** : il s'agit de règles + statistiques de texte, pas
  d'un vrai modèle de langage. Un bloc de code commenté dans
  `ia_wendkugri.py` indique où brancher un vrai LLM (ex. API Anthropic) si
  vous disposez d'une clé API.
- **Traduction Moré/FR/EN** : il n'existe pas aujourd'hui de service de
  traduction automatique fiable pour le Moré. La fonction `traduire_texte()`
  est un point d'extension documenté plutôt qu'une fausse traduction.
- **Mode hors-ligne** : sauvegarde côté navigateur uniquement (`localStorage`,
  limité à 10 cours), pas encore une vraie application installable avec
  synchronisation (PWA + Service Worker) — évolution possible en V2.
- **Groupes d'Étude** : salon **écrit** fonctionnel ; le salon **vocal**
  nécessiterait une brique technique supplémentaire (ex. WebRTC) non incluse
  dans cette V1.

## 6. Déploiement

Pour un déploiement simple (ex. PythonAnywhere, Render, VPS) :
1. Remplacer `app.config["SECRET_KEY"]` par une vraie clé secrète (variable
   d'environnement recommandée).
2. Lancer avec un serveur de production (ex. `gunicorn app:app`), plutôt que
   `python app.py` qui utilise le serveur de développement Flask.
3. SQLite convient pour démarrer ; prévoir PostgreSQL si le nombre
   d'utilisateurs grandit fortement.

---
*Wend'Kugri — Copyright by Computer Science Solution-BF*
