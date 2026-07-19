# -*- coding: utf-8 -*-
"""
models.py — Wend'Kugri (« Le Lieu de la Connaissance »)
=========================================================
Définition de tous les modèles de données (tables SQLite) de l'application,
via Flask-SQLAlchemy.

Copyright by Computer Science Solution-BF
"""

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ---------------------------------------------------------------------------
# CONSTANTES MÉTIER — domaines, villes, niveaux, types de publication
# Centralisées ici pour être réutilisées par app.py ET par les templates.
# ---------------------------------------------------------------------------

DOMAINES = [
    "Technologie", "Agriculture", "Santé", "Éducation",
    "Entrepreneuriat BF", "Artisanat", "Finance",
    "Langue - Moré", "Langue - Dioula", "Langue - Français", "Langue - Anglais",
]

VILLES_BF = [
    "Ouagadougou", "Bobo-Dioulasso", "Koudougou", "Ouahigouya",
    "Banfora", "Kaya", "Tenkodogo", "Fada N'Gourma", "Dédougou",
    "Ziniaré", "Autre",
]

NIVEAUX = ["Débutant", "Intermédiaire", "Avancé", "Expert"]

# Les 4 SEULS types de publication autorisés sur Wend'Kugri (voir cahier des charges)
TYPES_PUBLICATION = {
    "astuce":  {"label": "Astuce / Texte",   "points": 5,  "max_caracteres": 500},
    "cours":   {"label": "Cours / Document", "points": 15, "max_caracteres": 500},
    "video":   {"label": "Vidéo / Tuto",     "points": 10, "max_caracteres": 500},
    "question":{"label": "Question / Problème", "points": 3, "max_caracteres": 500},
}

# Seuil de points pour l'attribution automatique du badge "Contributeur Vérifié"
SEUIL_CONTRIBUTEUR_VERIFIE = 300

# Nombre de signalements qui masque automatiquement une publication
SEUIL_SIGNALEMENTS_MASQUAGE = 3


class Utilisateur(db.Model):
    """Un membre de la communauté Wend'Kugri."""
    __tablename__ = "utilisateurs"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    telephone = db.Column(db.String(20), unique=True, nullable=False)  # format BF: +226 XX XX XX XX
    mot_de_passe_hash = db.Column(db.String(255), nullable=False)

    domaine_expertise = db.Column(db.String(60), nullable=False)
    ville = db.Column(db.String(60), nullable=False)
    niveau = db.Column(db.String(30), nullable=False, default="Débutant")

    points = db.Column(db.Integer, default=0)
    contributeur_verifie = db.Column(db.Boolean, default=False)
    photo_profil = db.Column(db.String(255), nullable=True)  # chemin optionnel

    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    publications = db.relationship("Publication", backref="auteur", lazy=True,
                                    foreign_keys="Publication.auteur_id")
    commentaires = db.relationship("Commentaire", backref="auteur", lazy=True)

    def definir_mot_de_passe(self, mot_de_passe_clair):
        self.mot_de_passe_hash = generate_password_hash(mot_de_passe_clair)

    def verifier_mot_de_passe(self, mot_de_passe_clair):
        return check_password_hash(self.mot_de_passe_hash, mot_de_passe_clair)

    def ajouter_points(self, quantite):
        """Ajoute des points de Connaissance et met à jour le badge automatiquement."""
        self.points = (self.points or 0) + quantite
        if self.points >= SEUIL_CONTRIBUTEUR_VERIFIE:
            self.contributeur_verifie = True

    def etiquette_profil(self):
        """Ex: 'Développeur, Ouaga, Intermédiaire' comme demandé dans le cahier des charges."""
        return f"{self.domaine_expertise}, {self.ville}, {self.niveau}"

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "domaine_expertise": self.domaine_expertise,
            "ville": self.ville,
            "niveau": self.niveau,
            "points": self.points,
            "contributeur_verifie": self.contributeur_verifie,
        }


class Publication(db.Model):
    """
    Une publication du fil « Savoir ».
    type_publication doit être l'une des clés de TYPES_PUBLICATION (astuce, cours, video, question).
    """
    __tablename__ = "publications"

    id = db.Column(db.Integer, primary_key=True)
    auteur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)

    type_publication = db.Column(db.String(20), nullable=False)
    contenu = db.Column(db.Text, nullable=False)          # texte / description (≤ 500 caractères)
    domaine = db.Column(db.String(60), nullable=False)    # tag domaine OBLIGATOIRE
    ville = db.Column(db.String(60), nullable=True)

    # Champs spécifiques selon le type
    nom_fichier = db.Column(db.String(255), nullable=True)     # PDF / PPT / DOC pour type "cours"
    resume_auto = db.Column(db.Text, nullable=True)            # résumé généré par Wend'Kugri IA
    lien_video = db.Column(db.String(500), nullable=True)      # lien YouTube pour type "video"
    nom_fichier_video = db.Column(db.String(255), nullable=True)  # vidéo uploadée (< 5 min)

    date_publication = db.Column(db.DateTime, default=datetime.utcnow)

    nb_signalements = db.Column(db.Integer, default=0)
    masquee = db.Column(db.Boolean, default=False)  # masquée après 3 signalements
    resolue = db.Column(db.Boolean, default=False)   # pour les questions : marquée comme résolue

    # Relations
    commentaires = db.relationship("Commentaire", backref="publication", lazy=True,
                                    cascade="all, delete-orphan")
    likes = db.relationship("Jaime", backref="publication", lazy=True,
                             cascade="all, delete-orphan")
    signalements = db.relationship("Signalement", backref="publication", lazy=True,
                                    cascade="all, delete-orphan")

    def nb_likes(self):
        return len(self.likes)

    def infos_type(self):
        return TYPES_PUBLICATION.get(self.type_publication, {})


class Commentaire(db.Model):
    """Réponse / commentaire sous une publication (utile notamment pour les Questions)."""
    __tablename__ = "commentaires"

    id = db.Column(db.Integer, primary_key=True)
    publication_id = db.Column(db.Integer, db.ForeignKey("publications.id"), nullable=False)
    auteur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    marque_utile = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)


class Jaime(db.Model):
    """Un 'like' de Connaissance sur une publication. Unique par (publication, utilisateur)."""
    __tablename__ = "jaime"

    id = db.Column(db.Integer, primary_key=True)
    publication_id = db.Column(db.Integer, db.ForeignKey("publications.id"), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)

    __table_args__ = (db.UniqueConstraint("publication_id", "utilisateur_id", name="uniq_like"),)


class Signalement(db.Model):
    """Signalement d'une publication jugée hors-sujet par un membre."""
    __tablename__ = "signalements"

    id = db.Column(db.Integer, primary_key=True)
    publication_id = db.Column(db.Integer, db.ForeignKey("publications.id"), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    raison = db.Column(db.String(255), nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("publication_id", "utilisateur_id", name="uniq_signal"),)


class GroupeEtude(db.Model):
    """Un salon de Groupe d'Étude (écrit) pour réviser un concours / projet."""
    __tablename__ = "groupes_etude"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    domaine = db.Column(db.String(60), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    createur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    membres = db.relationship("MembreGroupe", backref="groupe", lazy=True,
                               cascade="all, delete-orphan")
    messages = db.relationship("MessageGroupe", backref="groupe", lazy=True,
                                cascade="all, delete-orphan")

    def nb_membres(self):
        return len(self.membres)


class MembreGroupe(db.Model):
    __tablename__ = "membres_groupe"

    id = db.Column(db.Integer, primary_key=True)
    groupe_id = db.Column(db.Integer, db.ForeignKey("groupes_etude.id"), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    date_adhesion = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("groupe_id", "utilisateur_id", name="uniq_membre"),)


class MessageGroupe(db.Model):
    __tablename__ = "messages_groupe"

    id = db.Column(db.Integer, primary_key=True)
    groupe_id = db.Column(db.Integer, db.ForeignKey("groupes_etude.id"), nullable=False)
    auteur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)


class DefiDuJour(db.Model):
    """Une question du Défi du Jour, associée à une date et un domaine."""
    __tablename__ = "defis_du_jour"

    id = db.Column(db.Integer, primary_key=True)
    date_defi = db.Column(db.Date, default=date.today, unique=True)
    domaine = db.Column(db.String(60), nullable=False)
    question = db.Column(db.Text, nullable=False)
    points_recompense = db.Column(db.Integer, default=20)

    reponses = db.relationship("ReponseDefi", backref="defi", lazy=True,
                                cascade="all, delete-orphan")


class ReponseDefi(db.Model):
    """Réponse d'un utilisateur à un Défi du Jour."""
    __tablename__ = "reponses_defi"

    id = db.Column(db.Integer, primary_key=True)
    defi_id = db.Column(db.Integer, db.ForeignKey("defis_du_jour.id"), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    reponse = db.Column(db.Text, nullable=False)
    points_obtenus = db.Column(db.Boolean, default=False)  # attribués une seule fois
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("defi_id", "utilisateur_id", name="uniq_reponse_defi"),)
