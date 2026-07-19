# -*- coding: utf-8 -*-
"""
app.py — Wend'Kugri (« Le Lieu de la Connaissance »)
=======================================================
Application Flask principale : routes HTTP, authentification par session,
logique métier du fil "Savoir", modération, gamification, groupes d'étude,
défi du jour et bibliothèque BF.

Pour lancer l'application :
    pip install -r requirements.txt
    python app.py
Puis ouvrir http://127.0.0.1:5000 dans le navigateur.

Copyright by Computer Science Solution-BF
"""

import os
import re
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, jsonify, send_from_directory, abort
)
from werkzeug.utils import secure_filename

from models import (
    db, Utilisateur, Publication, Commentaire, Jaime, Signalement,
    GroupeEtude, MembreGroupe, MessageGroupe, DefiDuJour, ReponseDefi,
    DOMAINES, VILLES_BF, NIVEAUX, TYPES_PUBLICATION,
    SEUIL_SIGNALEMENTS_MASQUAGE,
)
from ia_wendkugri import moderer_publication, resumer_pdf_en_5_points

# ---------------------------------------------------------------------------
# CONFIGURATION DE L'APPLICATION
# ---------------------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
EXTENSIONS_DOC_AUTORISEES = {"pdf", "ppt", "pptx", "doc", "docx"}
EXTENSIONS_VIDEO_AUTORISEES = {"mp4", "webm", "mov"}

app = Flask(__name__)
app.config["SECRET_KEY"] = "wendkugri-cle-secrete-a-changer-en-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "instance", "wendkugri.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024  # 60 Mo max par fichier (vidéos courtes incluses)

db.init_app(app)

os.makedirs(os.path.join(UPLOAD_FOLDER, "cours"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "videos"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)


# ---------------------------------------------------------------------------
# OUTILS D'AUTHENTIFICATION
# ---------------------------------------------------------------------------

def connexion_requise(vue):
    """Décorateur : bloque l'accès à une route si l'utilisateur n'est pas connecté."""
    @wraps(vue)
    def enveloppe(*args, **kwargs):
        if "utilisateur_id" not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "avertissement")
            return redirect(url_for("connexion", suivant=request.path))
        return vue(*args, **kwargs)
    return enveloppe


def utilisateur_courant():
    """Renvoie l'objet Utilisateur connecté, ou None."""
    uid = session.get("utilisateur_id")
    if not uid:
        return None
    return Utilisateur.query.get(uid)


@app.context_processor
def injecter_globales():
    """Rend certaines variables disponibles dans TOUS les templates."""
    return {
        "utilisateur_actuel": utilisateur_courant(),
        "DOMAINES": DOMAINES,
        "VILLES_BF": VILLES_BF,
        "NIVEAUX": NIVEAUX,
        "TYPES_PUBLICATION": TYPES_PUBLICATION,
        "annee_actuelle": datetime.utcnow().year,
    }


def extension_valide(nom_fichier, extensions_autorisees):
    return "." in nom_fichier and nom_fichier.rsplit(".", 1)[1].lower() in extensions_autorisees


def valider_telephone_bf(telephone):
    """Validation simple d'un numéro burkinabè : 8 chiffres, éventuellement préfixés +226."""
    telephone_nettoye = telephone.replace(" ", "").replace("-", "")
    return re.match(r"^(\+226)?\d{8}$", telephone_nettoye) is not None


@app.template_filter("youtube_embed")
def convertir_lien_youtube_embed(lien):
    """Convertit un lien YouTube classique en lien 'embed' utilisable dans un <iframe>."""
    if not lien:
        return ""
    correspondance = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", lien)
    if correspondance:
        return f"https://www.youtube.com/embed/{correspondance.group(1)}"
    return lien


@app.template_filter("temps_ecoule")
def temps_ecoule(date_publication):
    """Affiche une date sous forme relative : 'à l'instant', 'il y a 2 h', etc."""
    if not date_publication:
        return ""
    delta_secondes = (datetime.utcnow() - date_publication).total_seconds()
    if delta_secondes < 60:
        return "à l'instant"
    if delta_secondes < 3600:
        return f"il y a {int(delta_secondes // 60)} min"
    if delta_secondes < 86400:
        return f"il y a {int(delta_secondes // 3600)} h"
    if delta_secondes < 30 * 86400:
        return f"il y a {int(delta_secondes // 86400)} j"
    return date_publication.strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# AUTHENTIFICATION & PROFIL
# ---------------------------------------------------------------------------

@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        email = request.form.get("email", "").strip().lower()
        telephone = request.form.get("telephone", "").strip()
        mot_de_passe = request.form.get("mot_de_passe", "")
        domaine_expertise = request.form.get("domaine_expertise", "")
        ville = request.form.get("ville", "")
        niveau = request.form.get("niveau", "Débutant")

        erreurs = []
        if not nom or len(nom) < 2:
            erreurs.append("Le nom est obligatoire.")
        if not email or "@" not in email:
            erreurs.append("Adresse email invalide.")
        if not valider_telephone_bf(telephone):
            erreurs.append("Numéro de téléphone burkinabè invalide (8 chiffres, ex : 70 12 34 56).")
        if len(mot_de_passe) < 6:
            erreurs.append("Le mot de passe doit contenir au moins 6 caractères.")
        if not domaine_expertise or not ville:
            erreurs.append("Domaine d'expertise et ville sont obligatoires.")
        if Utilisateur.query.filter_by(email=email).first():
            erreurs.append("Cet email est déjà utilisé.")
        if Utilisateur.query.filter_by(telephone=telephone).first():
            erreurs.append("Ce numéro de téléphone est déjà utilisé.")

        if erreurs:
            for e in erreurs:
                flash(e, "erreur")
            return render_template("inscription.html", form=request.form)

        nouvel_utilisateur = Utilisateur(
            nom=nom, email=email, telephone=telephone,
            domaine_expertise=domaine_expertise, ville=ville, niveau=niveau,
        )
        nouvel_utilisateur.definir_mot_de_passe(mot_de_passe)
        db.session.add(nouvel_utilisateur)
        db.session.commit()

        session["utilisateur_id"] = nouvel_utilisateur.id
        flash(f"Bienvenue sur Wend'Kugri, {nom} ! Votre compte a été créé.", "succes")
        return redirect(url_for("fil_actualite"))

    return render_template("inscription.html", form={})


@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip().lower()
        mot_de_passe = request.form.get("mot_de_passe", "")

        utilisateur = Utilisateur.query.filter(
            (Utilisateur.email == identifiant) | (Utilisateur.telephone == identifiant)
        ).first()

        if utilisateur and utilisateur.verifier_mot_de_passe(mot_de_passe):
            session["utilisateur_id"] = utilisateur.id
            flash(f"Content de vous revoir, {utilisateur.nom} !", "succes")
            suivant = request.args.get("suivant")
            return redirect(suivant or url_for("fil_actualite"))

        flash("Email/téléphone ou mot de passe incorrect.", "erreur")

    return render_template("connexion.html")


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    flash("Vous êtes déconnecté. À bientôt sur Wend'Kugri !", "succes")
    return redirect(url_for("connexion"))


@app.route("/profil/<int:utilisateur_id>")
@connexion_requise
def profil(utilisateur_id):
    profil_utilisateur = Utilisateur.query.get_or_404(utilisateur_id)
    publications = (Publication.query
                    .filter_by(auteur_id=utilisateur_id, masquee=False)
                    .order_by(Publication.date_publication.desc()).all())
    return render_template("profil.html", profil_utilisateur=profil_utilisateur, publications=publications)


@app.route("/profil/modifier", methods=["GET", "POST"])
@connexion_requise
def modifier_profil():
    u = utilisateur_courant()
    if request.method == "POST":
        u.nom = request.form.get("nom", u.nom).strip()
        u.domaine_expertise = request.form.get("domaine_expertise", u.domaine_expertise)
        u.ville = request.form.get("ville", u.ville)
        u.niveau = request.form.get("niveau", u.niveau)
        db.session.commit()
        flash("Profil mis à jour.", "succes")
        return redirect(url_for("profil", utilisateur_id=u.id))
    return render_template("modifier_profil.html")


# ---------------------------------------------------------------------------
# FIL D'ACTUALITÉ « SAVOIR »
# ---------------------------------------------------------------------------

@app.route("/")
@connexion_requise
def fil_actualite():
    filtre_domaine = request.args.get("domaine", "")
    filtre_ville = request.args.get("ville", "")
    filtre_type = request.args.get("type", "")

    requete = Publication.query.filter_by(masquee=False)
    if filtre_domaine:
        requete = requete.filter_by(domaine=filtre_domaine)
    if filtre_ville:
        requete = requete.filter_by(ville=filtre_ville)
    if filtre_type:
        requete = requete.filter_by(type_publication=filtre_type)

    publications = requete.order_by(Publication.date_publication.desc()).limit(50).all()

    defi_du_jour = DefiDuJour.query.filter_by(date_defi=date.today()).first()

    return render_template(
        "index.html",
        publications=publications,
        defi_du_jour=defi_du_jour,
        filtre_domaine=filtre_domaine, filtre_ville=filtre_ville, filtre_type=filtre_type,
    )


@app.route("/publier", methods=["GET", "POST"])
@connexion_requise
def publier():
    u = utilisateur_courant()

    if request.method == "POST":
        type_publication = request.form.get("type_publication", "")
        contenu = request.form.get("contenu", "").strip()
        domaine = request.form.get("domaine", "")
        ville = request.form.get("ville", "") or u.ville
        lien_video = request.form.get("lien_video", "").strip()

        # --- 1. MODÉRATION IA ANTI-DÉSORDRE (avant tout enregistrement) ---
        est_valide, message_moderation = moderer_publication(contenu, type_publication, domaine)
        if not est_valide:
            flash(message_moderation, "erreur")
            return render_template("publier.html", form=request.form)

        nouvelle_publication = Publication(
            auteur_id=u.id, type_publication=type_publication,
            contenu=contenu, domaine=domaine, ville=ville, lien_video=lien_video or None,
        )

        # --- 2. GESTION DES FICHIERS SELON LE TYPE ---
        if type_publication == "cours":
            fichier = request.files.get("fichier")
            if not fichier or fichier.filename == "":
                flash("Veuillez joindre un fichier PDF, PPT ou DOC pour un Cours.", "erreur")
                return render_template("publier.html", form=request.form)
            if not extension_valide(fichier.filename, EXTENSIONS_DOC_AUTORISEES):
                flash("Format non autorisé. Formats acceptés : PDF, PPT, PPTX, DOC, DOCX.", "erreur")
                return render_template("publier.html", form=request.form)

            nom_sécurisé = secure_filename(fichier.filename)
            nom_unique = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{nom_sécurisé}"
            chemin_complet = os.path.join(app.config["UPLOAD_FOLDER"], "cours", nom_unique)
            fichier.save(chemin_complet)
            nouvelle_publication.nom_fichier = nom_unique

            # Résumé automatique en 5 points si c'est un PDF (Wend'Kugri IA)
            if nom_unique.lower().endswith(".pdf"):
                points_cles = resumer_pdf_en_5_points(chemin_complet)
                if points_cles:
                    nouvelle_publication.resume_auto = "\n".join(f"• {p}" for p in points_cles)

        elif type_publication == "video":
            fichier_video = request.files.get("fichier_video")
            if fichier_video and fichier_video.filename:
                if not extension_valide(fichier_video.filename, EXTENSIONS_VIDEO_AUTORISEES):
                    flash("Format vidéo non autorisé (MP4, WEBM, MOV uniquement, < 5 min).", "erreur")
                    return render_template("publier.html", form=request.form)
                nom_sécurisé = secure_filename(fichier_video.filename)
                nom_unique = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{nom_sécurisé}"
                chemin_complet = os.path.join(app.config["UPLOAD_FOLDER"], "videos", nom_unique)
                fichier_video.save(chemin_complet)
                nouvelle_publication.nom_fichier_video = nom_unique
            elif not lien_video:
                flash("Veuillez fournir un lien YouTube ou uploader une vidéo (< 5 min).", "erreur")
                return render_template("publier.html", form=request.form)

        db.session.add(nouvelle_publication)

        # --- 3. GAMIFICATION : points de Connaissance ---
        points_gagnes = TYPES_PUBLICATION[type_publication]["points"]
        u.ajouter_points(points_gagnes)

        db.session.commit()
        flash(f"Publication en ligne ! Vous avez gagné {points_gagnes} points de Connaissance.", "succes")
        return redirect(url_for("fil_actualite"))

    return render_template("publier.html", form={})


@app.route("/publication/<int:publication_id>")
@connexion_requise
def detail_publication(publication_id):
    pub = Publication.query.get_or_404(publication_id)
    commentaires = (Commentaire.query.filter_by(publication_id=publication_id)
                     .order_by(Commentaire.date_creation.asc()).all())
    return render_template("detail_publication.html", pub=pub, commentaires=commentaires)


@app.route("/publication/<int:publication_id>/commenter", methods=["POST"])
@connexion_requise
def commenter(publication_id):
    pub = Publication.query.get_or_404(publication_id)
    contenu = request.form.get("contenu", "").strip()
    if not contenu:
        flash("Le commentaire ne peut pas être vide.", "erreur")
        return redirect(url_for("detail_publication", publication_id=publication_id))

    commentaire = Commentaire(publication_id=publication_id, auteur_id=session["utilisateur_id"], contenu=contenu)
    db.session.add(commentaire)

    # Petit bonus de Connaissance pour avoir répondu à une Question
    if pub.type_publication == "question":
        utilisateur_courant().ajouter_points(3)

    db.session.commit()
    flash("Réponse publiée.", "succes")
    return redirect(url_for("detail_publication", publication_id=publication_id))


@app.route("/publication/<int:publication_id>/aimer", methods=["POST"])
@connexion_requise
def aimer(publication_id):
    """Bascule le like (aimer / retirer). Réponse JSON pour l'appel AJAX du frontend."""
    pub = Publication.query.get_or_404(publication_id)
    uid = session["utilisateur_id"]
    like_existant = Jaime.query.filter_by(publication_id=publication_id, utilisateur_id=uid).first()

    if like_existant:
        db.session.delete(like_existant)
        deja_aime = False
    else:
        db.session.add(Jaime(publication_id=publication_id, utilisateur_id=uid))
        # +1 point de Connaissance pour l'auteur à chaque like reçu
        pub.auteur.ajouter_points(1)
        deja_aime = True

    db.session.commit()
    return jsonify({"succes": True, "aime": deja_aime, "nb_likes": pub.nb_likes()})


@app.route("/publication/<int:publication_id>/signaler", methods=["POST"])
@connexion_requise
def signaler(publication_id):
    pub = Publication.query.get_or_404(publication_id)
    uid = session["utilisateur_id"]

    deja_signale = Signalement.query.filter_by(publication_id=publication_id, utilisateur_id=uid).first()
    if deja_signale:
        return jsonify({"succes": False, "message": "Vous avez déjà signalé cette publication."})

    db.session.add(Signalement(publication_id=publication_id, utilisateur_id=uid,
                                raison=request.form.get("raison", "")))
    pub.nb_signalements += 1

    if pub.nb_signalements >= SEUIL_SIGNALEMENTS_MASQUAGE:
        pub.masquee = True

    db.session.commit()
    return jsonify({"succes": True, "masquee": pub.masquee, "nb_signalements": pub.nb_signalements})


# ---------------------------------------------------------------------------
# WEND'KUGRI IA — Chatbot de résumé de PDF (appelable en AJAX)
# ---------------------------------------------------------------------------

@app.route("/api/resumer-publication/<int:publication_id>")
@connexion_requise
def api_resumer_publication(publication_id):
    """Renvoie (ou génère à la volée) le résumé en 5 points d'un cours PDF."""
    pub = Publication.query.get_or_404(publication_id)
    if pub.type_publication != "cours" or not pub.nom_fichier:
        return jsonify({"succes": False, "message": "Cette publication n'a pas de document à résumer."})

    if not pub.resume_auto:
        chemin = os.path.join(app.config["UPLOAD_FOLDER"], "cours", pub.nom_fichier)
        points_cles = resumer_pdf_en_5_points(chemin)
        if points_cles:
            pub.resume_auto = "\n".join(f"• {p}" for p in points_cles)
            db.session.commit()

    if pub.resume_auto:
        return jsonify({"succes": True, "resume": pub.resume_auto})
    return jsonify({"succes": False, "message": "Impossible de résumer ce document (format non PDF ou texte introuvable)."})


# ---------------------------------------------------------------------------
# BIBLIOTHÈQUE BF — tous les cours/PDF classés par domaine
# ---------------------------------------------------------------------------

@app.route("/bibliotheque")
@connexion_requise
def bibliotheque():
    filtre_domaine = request.args.get("domaine", "")
    requete = Publication.query.filter_by(type_publication="cours", masquee=False)
    if filtre_domaine:
        requete = requete.filter_by(domaine=filtre_domaine)
    cours = requete.order_by(Publication.date_publication.desc()).all()
    return render_template("bibliotheque.html", cours=cours, filtre_domaine=filtre_domaine)


@app.route("/uploads/<sous_dossier>/<nom_fichier>")
@connexion_requise
def fichier_uploade(sous_dossier, nom_fichier):
    """Sert les fichiers uploadés (cours et vidéos) aux utilisateurs connectés uniquement."""
    if sous_dossier not in ("cours", "videos"):
        abort(404)
    return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], sous_dossier), nom_fichier)


# ---------------------------------------------------------------------------
# DÉFI DU JOUR
# ---------------------------------------------------------------------------

@app.route("/defi", methods=["GET", "POST"])
@connexion_requise
def defi_du_jour():
    defi = DefiDuJour.query.filter_by(date_defi=date.today()).first()
    u = utilisateur_courant()
    ma_reponse = None

    if defi:
        ma_reponse = ReponseDefi.query.filter_by(defi_id=defi.id, utilisateur_id=u.id).first()

        if request.method == "POST" and not ma_reponse:
            texte_reponse = request.form.get("reponse", "").strip()
            if texte_reponse:
                ma_reponse = ReponseDefi(defi_id=defi.id, utilisateur_id=u.id, reponse=texte_reponse,
                                          points_obtenus=True)
                db.session.add(ma_reponse)
                u.ajouter_points(defi.points_recompense)
                db.session.commit()
                flash(f"Réponse envoyée ! +{defi.points_recompense} points de Connaissance.", "succes")
                return redirect(url_for("defi_du_jour"))

    anciens_defis = (DefiDuJour.query.filter(DefiDuJour.date_defi < date.today())
                      .order_by(DefiDuJour.date_defi.desc()).limit(5).all())

    return render_template("defi.html", defi=defi, ma_reponse=ma_reponse, anciens_defis=anciens_defis)


# ---------------------------------------------------------------------------
# GROUPES D'ÉTUDE
# ---------------------------------------------------------------------------

@app.route("/groupes", methods=["GET", "POST"])
@connexion_requise
def groupes():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        domaine = request.form.get("domaine", "")
        description = request.form.get("description", "").strip()

        if not nom or not domaine:
            flash("Le nom et le domaine du groupe sont obligatoires.", "erreur")
        else:
            groupe = GroupeEtude(nom=nom, domaine=domaine, description=description,
                                  createur_id=session["utilisateur_id"])
            db.session.add(groupe)
            db.session.flush()  # pour obtenir groupe.id avant le commit
            db.session.add(MembreGroupe(groupe_id=groupe.id, utilisateur_id=session["utilisateur_id"]))
            db.session.commit()
            flash(f"Groupe « {nom} » créé !", "succes")
            return redirect(url_for("detail_groupe", groupe_id=groupe.id))

    tous_les_groupes = GroupeEtude.query.order_by(GroupeEtude.date_creation.desc()).all()
    return render_template("groupes.html", groupes=tous_les_groupes)


@app.route("/groupes/<int:groupe_id>", methods=["GET", "POST"])
@connexion_requise
def detail_groupe(groupe_id):
    groupe = GroupeEtude.query.get_or_404(groupe_id)
    uid = session["utilisateur_id"]
    est_membre = MembreGroupe.query.filter_by(groupe_id=groupe_id, utilisateur_id=uid).first() is not None

    if request.method == "POST":
        if not est_membre:
            flash("Rejoignez le groupe pour participer à la discussion.", "erreur")
        else:
            contenu = request.form.get("contenu", "").strip()
            if contenu:
                db.session.add(MessageGroupe(groupe_id=groupe_id, auteur_id=uid, contenu=contenu))
                db.session.commit()
        return redirect(url_for("detail_groupe", groupe_id=groupe_id))

    messages = (MessageGroupe.query.filter_by(groupe_id=groupe_id)
                .order_by(MessageGroupe.date_creation.asc()).all())
    return render_template("detail_groupe.html", groupe=groupe, messages=messages, est_membre=est_membre)


@app.route("/groupes/<int:groupe_id>/rejoindre", methods=["POST"])
@connexion_requise
def rejoindre_groupe(groupe_id):
    uid = session["utilisateur_id"]
    if not MembreGroupe.query.filter_by(groupe_id=groupe_id, utilisateur_id=uid).first():
        db.session.add(MembreGroupe(groupe_id=groupe_id, utilisateur_id=uid))
        db.session.commit()
        flash("Vous avez rejoint le groupe d'étude.", "succes")
    return redirect(url_for("detail_groupe", groupe_id=groupe_id))


# ---------------------------------------------------------------------------
# CLASSEMENT — « Maîtres du Savoir »
# ---------------------------------------------------------------------------

@app.route("/classement")
@connexion_requise
def classement():
    filtre_domaine = request.args.get("domaine", "")
    requete = Utilisateur.query
    if filtre_domaine:
        requete = requete.filter_by(domaine_expertise=filtre_domaine)
    meilleurs = requete.order_by(Utilisateur.points.desc()).limit(20).all()
    return render_template("classement.html", meilleurs=meilleurs, filtre_domaine=filtre_domaine)


# ---------------------------------------------------------------------------
# LANCEMENT DE L'APPLICATION
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # crée les tables si elles n'existent pas encore
    app.run(debug=True, host="0.0.0.0", port=5000)
