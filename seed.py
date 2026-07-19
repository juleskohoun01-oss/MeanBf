# -*- coding: utf-8 -*-
"""
seed.py — Wend'Kugri
=======================
Initialise la base de données SQLite et la remplit avec :
  - 3 comptes utilisateurs de démonstration
  - 5 publications d'exemple (les 4 types représentés)
  - 1 Défi du Jour
  - 1 Groupe d'Étude

Usage :
    python seed.py

Copyright by Computer Science Solution-BF
"""

import os
from datetime import datetime, date, timedelta

from app import app, UPLOAD_FOLDER
from models import (
    db, Utilisateur, Publication, GroupeEtude, MembreGroupe, DefiDuJour, Commentaire, Jaime
)
from ia_wendkugri import resumer_pdf_en_5_points


def creer_pdf_demo(chemin_fichier, titre, paragraphes):
    """Génère un vrai petit fichier PDF de démonstration (via reportlab), pour que le
    résumé automatique Wend'Kugri IA ait un contenu réel à analyser."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(chemin_fichier, pagesize=A4)
    largeur, hauteur = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, hauteur - 2.5 * cm, titre)

    c.setFont("Helvetica", 11)
    y = hauteur - 4 * cm
    for paragraphe in paragraphes:
        lignes = []
        mots = paragraphe.split()
        ligne_courante = ""
        for mot in mots:
            essai = (ligne_courante + " " + mot).strip()
            if c.stringWidth(essai, "Helvetica", 11) > (largeur - 4 * cm):
                lignes.append(ligne_courante)
                ligne_courante = mot
            else:
                ligne_courante = essai
        if ligne_courante:
            lignes.append(ligne_courante)

        for ligne in lignes:
            c.drawString(2 * cm, y, ligne)
            y -= 0.6 * cm
        y -= 0.4 * cm

    c.save()


def creer_video_demo(chemin_fichier, texte):
    """Génère une très courte vidéo MP4 de démonstration (via ffmpeg), pour illustrer
    le type de publication 'Vidéo / Tuto' sans dépendre d'un lien externe."""
    import subprocess
    commande = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "color=c=0x059669:s=640x360:d=4",
        "-vf", f"drawtext=text='{texte}':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-t", "4", "-pix_fmt", "yuv420p", chemin_fichier,
    ]
    subprocess.run(commande, check=True, capture_output=True)


def peupler_base():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ---------------------------------------------------------------
        # 3 COMPTES DE TEST
        # ---------------------------------------------------------------
        aicha = Utilisateur(
            nom="Aïcha Sawadogo", email="aicha@wendkugri.bf", telephone="70123456",
            domaine_expertise="Technologie", ville="Ouagadougou", niveau="Avancé",
            contributeur_verifie=True, points=340,
        )
        aicha.definir_mot_de_passe("motdepasse123")

        issa = Utilisateur(
            nom="Issa Ouédraogo", email="issa@wendkugri.bf", telephone="76234567",
            domaine_expertise="Agriculture", ville="Bobo-Dioulasso", niveau="Expert",
            contributeur_verifie=True, points=410,
        )
        issa.definir_mot_de_passe("motdepasse123")

        fatim = Utilisateur(
            nom="Fatimata Kaboré", email="fatim@wendkugri.bf", telephone="78345678",
            domaine_expertise="Santé", ville="Koudougou", niveau="Intermédiaire",
            contributeur_verifie=False, points=45,
        )
        fatim.definir_mot_de_passe("motdepasse123")

        db.session.add_all([aicha, issa, fatim])
        db.session.commit()

        # ---------------------------------------------------------------
        # 5 PUBLICATIONS D'EXEMPLE (les 4 types représentés)
        # ---------------------------------------------------------------

        # 1. ASTUCE — Technologie
        pub1 = Publication(
            auteur_id=aicha.id, type_publication="astuce", domaine="Technologie", ville="Ouagadougou",
            contenu=("Astuce Git : utilisez 'git stash' pour mettre de côté des modifications en cours "
                     "sans les commiter, le temps de corriger un bug urgent sur une autre branche. "
                     "Ensuite 'git stash pop' pour les récupérer."),
            date_publication=datetime.utcnow() - timedelta(hours=5),
        )

        # 2. COURS — Agriculture (avec vrai PDF + résumé automatique)
        chemin_pdf = os.path.join(UPLOAD_FOLDER, "cours", "guide_niebe_cicadelles.pdf")
        creer_pdf_demo(
            chemin_pdf,
            "Guide pratique : lutte contre les cicadelles du niébé",
            [
                "Les cicadelles sont l'un des principaux ravageurs du niébé au Burkina Faso, en particulier "
                "pendant la phase de floraison. Elles provoquent le dessèchement des feuilles et une forte "
                "baisse du rendement si elles ne sont pas maîtrisées à temps.",
                "La première mesure de prévention consiste à semer tôt, dès les premières pluies utiles, "
                "afin que la floraison n'intervienne pas au pic de la population de cicadelles observé "
                "généralement six à huit semaines après les premiers semis de la campagne.",
                "L'utilisation de variétés locales résistantes, associée à une rotation avec le sorgho ou "
                "le mil, réduit fortement la pression parasitaire d'une saison à l'autre.",
                "En traitement naturel, une solution à base de graines de neem pilées et diluées dans l'eau, "
                "pulvérisée tôt le matin sur les deux faces des feuilles, donne de bons résultats et reste "
                "accessible à la majorité des producteurs.",
                "Enfin, un suivi hebdomadaire du champ dès le stade végétatif permet de détecter les premiers "
                "foyers d'infestation et d'intervenir avant que les dégâts ne deviennent irréversibles.",
            ],
        )
        resume_points = resumer_pdf_en_5_points(chemin_pdf)

        pub2 = Publication(
            auteur_id=issa.id, type_publication="cours", domaine="Agriculture", ville="Bobo-Dioulasso",
            contenu="Guide complet (PDF) pour protéger vos champs de niébé contre les cicadelles, avec des solutions accessibles et peu coûteuses.",
            nom_fichier="guide_niebe_cicadelles.pdf",
            resume_auto="\n".join(f"• {p}" for p in resume_points) if resume_points else None,
            date_publication=datetime.utcnow() - timedelta(hours=20),
        )

        # 3. VIDÉO — Entrepreneuriat BF (vraie petite vidéo de démonstration)
        chemin_video = os.path.join(UPLOAD_FOLDER, "videos", "demo_compta_mobile_money.mp4")
        try:
            creer_video_demo(chemin_video, "Demo Wend%27Kugri")
            nom_fichier_video = "demo_compta_mobile_money.mp4"
        except Exception:
            nom_fichier_video = None  # si ffmpeg indisponible sur la machine cible

        pub3 = Publication(
            auteur_id=fatim.id, type_publication="video", domaine="Entrepreneuriat BF", ville="Koudougou",
            contenu="Petit tuto vidéo : comment tenir un cahier de comptes simple avec Mobile Money pour une petite activité (3 min).",
            nom_fichier_video=nom_fichier_video,
            date_publication=datetime.utcnow() - timedelta(hours=30),
        )

        # 4. QUESTION — Finance
        pub4 = Publication(
            auteur_id=aicha.id, type_publication="question", domaine="Finance", ville="Ouagadougou",
            contenu="Je bloque sur le rapprochement de mes reçus Mobile Money avec mon cahier de comptes en fin de mois : quelqu'un a une méthode simple à partager ?",
            date_publication=datetime.utcnow() - timedelta(hours=2),
        )

        # 5. ASTUCE — Langue anglaise
        pub5 = Publication(
            auteur_id=issa.id, type_publication="astuce", domaine="Langue - Anglais", ville="Bobo-Dioulasso",
            contenu=("Pour progresser vite en anglais professionnel : regardez des tutoriels YouTube en "
                     "anglais avec les sous-titres anglais (pas français) activés. Le cerveau associe le son "
                     "à l'écrit dans la même langue, ce qui accélère la compréhension orale."),
            date_publication=datetime.utcnow() - timedelta(hours=45),
        )

        db.session.add_all([pub1, pub2, pub3, pub4, pub5])
        db.session.commit()

        # Quelques likes de démonstration
        db.session.add_all([
            Jaime(publication_id=pub1.id, utilisateur_id=issa.id),
            Jaime(publication_id=pub1.id, utilisateur_id=fatim.id),
            Jaime(publication_id=pub2.id, utilisateur_id=aicha.id),
            Jaime(publication_id=pub5.id, utilisateur_id=fatim.id),
        ])

        # Un commentaire de démonstration sur la Question
        db.session.add(Commentaire(
            publication_id=pub4.id, auteur_id=issa.id,
            contenu="Je note chaque transaction Mobile Money dans un tableau Excel le soir même, avec la référence du reçu. Ça évite l'accumulation en fin de mois.",
        ))

        # ---------------------------------------------------------------
        # DÉFI DU JOUR
        # ---------------------------------------------------------------
        db.session.add(DefiDuJour(
            date_defi=date.today(), domaine="Technologie",
            question="Quelle est la principale différence entre une liste et un tuple en Python ?",
            points_recompense=20,
        ))

        # ---------------------------------------------------------------
        # 1 GROUPE D'ÉTUDE DE DÉMONSTRATION
        # ---------------------------------------------------------------
        groupe = GroupeEtude(
            nom="Révision concours Développeur informatique 2026", domaine="Technologie",
            description="Entraide et partage de ressources pour préparer le concours de la fonction publique.",
            createur_id=aicha.id,
        )
        db.session.add(groupe)
        db.session.commit()
        db.session.add(MembreGroupe(groupe_id=groupe.id, utilisateur_id=aicha.id))
        db.session.add(MembreGroupe(groupe_id=groupe.id, utilisateur_id=issa.id))
        db.session.commit()

        print("Base de données initialisée avec succès.")
        print("Comptes de test créés :")
        print("  - aicha@wendkugri.bf / motdepasse123  (Contributeur Vérifié, Technologie)")
        print("  - issa@wendkugri.bf  / motdepasse123  (Contributeur Vérifié, Agriculture)")
        print("  - fatim@wendkugri.bf / motdepasse123  (Santé)")


if __name__ == "__main__":
    peupler_base()
