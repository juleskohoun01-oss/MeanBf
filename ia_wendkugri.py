# -*- coding: utf-8 -*-
"""
ia_wendkugri.py — Le "cerveau" léger de Wend'Kugri
=====================================================
Ce module regroupe les fonctions "intelligentes" de l'application :

1. moderer_publication()   -> vérifie qu'une publication apporte bien de la
                               connaissance (anti-désordre), AVANT publication.
2. resumer_pdf_en_5_points() -> lit un PDF et en extrait un résumé automatique
                               en 5 points clés ("Wend'Kugri IA").
3. traduire_texte()        -> point d'extension pour la traduction Moré/FR/EN.

IMPORTANT — HONNÊTETÉ TECHNIQUE :
Ces fonctions utilisent des méthodes locales, légères, SANS appel à un
service d'IA externe (donc 100% gratuit, fonctionne hors-ligne, aucune clé
API requise). Ce sont des heuristiques (règles + statistiques de mots),
pas un vrai modèle de langage. Elles donnent de bons résultats pour une V1
et une démo, mais peuvent se tromper sur des cas ambigus.

Pour une V2 plus précise, chaque fonction indique en commentaire comment la
brancher sur un vrai LLM (ex: API Anthropic Claude) en utilisant votre
propre clé API — voir les blocs "BRANCHEMENT IA RÉELLE (optionnel)".

Copyright by Computer Science Solution-BF
"""

import re
from collections import Counter

# ---------------------------------------------------------------------------
# 1. MODÉRATION ANTI-DÉSORDRE
# ---------------------------------------------------------------------------

# Formules de "bavardage" pur, sans connaissance, qu'on refuse si le message
# ne contient (quasiment) que ça.
FORMULES_BAVARDAGE = [
    r"^bonjour+\s*[!.]*$", r"^salut+\s*[!.]*$", r"^cc\s*[!.]*$",
    r"^ça va\??\s*[!.]*$", r"^ca va\??\s*[!.]*$", r"^comment (ça|ca) va\??$",
    r"^bonne (journée|soirée|nuit|fête)\s*[!.]*$", r"^bonjour tout le monde\s*[!.]*$",
    r"^coucou+\s*[!.]*$", r"^hello+\s*[!.]*$", r"^bjr\s*[!.]*$",
]

# Mots qui trahissent souvent du "buzz" / ragot plutôt que de la connaissance
MOTS_SUSPECTS_BUZZ = [
    "potin", "ragot", "scandale", "clash", "buzz", "rumeur", "polémique inutile",
]


def moderer_publication(contenu: str, type_publication: str, domaine: str):
    """
    Vérifie qu'une publication respecte l'esprit de Wend'Kugri.

    Retourne un tuple (est_valide: bool, message: str).
    En cas de refus, `message` est le texte à afficher à l'utilisateur.
    """
    texte = (contenu or "").strip()
    texte_normalise = texte.lower()

    # Règle 1 — le tag domaine est OBLIGATOIRE (bouton publier bloqué sinon,
    # mais on revérifie côté serveur par sécurité)
    if not domaine:
        return False, "Désolé, cette publication ne respecte pas l'esprit de Wend'Kugri : le tag domaine est obligatoire."

    # Règle 2 — le type doit être l'un des 4 types autorisés
    if type_publication not in ("astuce", "cours", "video", "question"):
        return False, "Désolé, cette publication ne respecte pas l'esprit de Wend'Kugri : type de contenu non reconnu."

    # Règle 3 — longueur minimale : une vraie astuce/question a un minimum de contenu
    if len(texte) < 15:
        return False, "Désolé, cette publication ne respecte pas l'esprit de Wend'Kugri : le contenu est trop court pour apporter une connaissance utile."

    # Règle 4 — longueur maximale (500 caractères imposés par le cahier des charges)
    if len(texte) > 500:
        return False, "Désolé, cette publication ne respecte pas l'esprit de Wend'Kugri : 500 caractères maximum."

    # Règle 5 — pur bavardage social ("bonjour ça va" etc.)
    for motif in FORMULES_BAVARDAGE:
        if re.match(motif, texte_normalise):
            return False, "Désolé, cette publication ne respecte pas l'esprit de Wend'Kugri : les messages de pure salutation ne sont pas autorisés."

    # Règle 6 — buzz / ragot détecté
    for mot in MOTS_SUSPECTS_BUZZ:
        if mot in texte_normalise:
            return False, "Désolé, cette publication ne respecte pas l'esprit de Wend'Kugri : contenu de type buzz/ragot détecté."

    # Règle 7 — un minimum de "densité de vocabulaire" (évite "aaaaaa test test test")
    mots = re.findall(r"[a-zàâäéèêëïîôöùûüç0-9]+", texte_normalise)
    if len(mots) >= 4 and len(set(mots)) / len(mots) < 0.35:
        return False, "Désolé, cette publication ne respecte pas l'esprit de Wend'Kugri : le contenu ne semble pas apporter d'information claire."

    # BRANCHEMENT IA RÉELLE (optionnel) :
    # Pour une modération sémantique plus fine, on peut ici appeler un LLM
    # (ex: API Anthropic) avec un prompt du type :
    #   "Cette publication apporte-t-elle une connaissance utile (oui/non) ?"
    # et combiner sa réponse avec les règles ci-dessus. Nécessite une clé API
    # et un accès réseau sortant depuis le serveur Flask.

    return True, "Publication conforme à l'esprit de Wend'Kugri."


# ---------------------------------------------------------------------------
# 2. RÉSUMÉ AUTOMATIQUE DE PDF — "Wend'Kugri IA"
# ---------------------------------------------------------------------------

# Anti-dictionnaire minimal (mots vides français) pour ne pas les compter
# comme "importants" lors du calcul de fréquence.
MOTS_VIDES_FR = set("""
le la les un une des de du au aux et ou où mais donc or ni car ce cet cette ces
il elle ils elles on nous vous je tu se sa son ses leur leurs mon ma mes ton ta
tes notre votre que qui quoi dont dans sur sous avec sans pour par entre vers
chez est sont était étaient être avoir a ont as ai avons avez plus moins très
tout toute tous toutes comme aussi alors donc ainsi cependant ne pas non oui
""".split())


def extraire_texte_pdf(chemin_fichier: str) -> str:
    """Extrait le texte brut d'un fichier PDF. Nécessite le paquet `pypdf`."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        lecteur = PdfReader(chemin_fichier)
        morceaux = []
        for page in lecteur.pages:
            texte_page = page.extract_text() or ""
            morceaux.append(texte_page)
        return "\n".join(morceaux)
    except Exception:
        return ""


def _decouper_en_phrases(texte: str):
    """Découpage simple en phrases (sans dépendance NLP lourde)."""
    texte = re.sub(r"\s+", " ", texte).strip()
    phrases = re.split(r"(?<=[.!?])\s+", texte)
    # On ignore les phrases trop courtes (souvent des titres/numéros de page isolés)
    return [p.strip() for p in phrases if len(p.strip()) > 25]


def resumer_pdf_en_5_points(chemin_fichier: str, nb_points: int = 5):
    """
    Résume un PDF en `nb_points` phrases clés, via une méthode extractive
    par fréquence de mots (proche de l'algorithme de Luhn).

    Retourne une liste de chaînes (les points clés), ou une liste vide si
    le PDF est illisible / vide.
    """
    texte = extraire_texte_pdf(chemin_fichier)
    if not texte or len(texte.strip()) < 50:
        return []

    phrases = _decouper_en_phrases(texte)
    if not phrases:
        return []

    # Fréquence des mots significatifs (hors mots vides)
    mots = re.findall(r"[a-zàâäéèêëïîôöùûüç]{3,}", texte.lower())
    mots_utiles = [m for m in mots if m not in MOTS_VIDES_FR]
    frequences = Counter(mots_utiles)

    # Score de chaque phrase = somme des fréquences de ses mots
    scores = []
    for i, phrase in enumerate(phrases):
        mots_phrase = re.findall(r"[a-zàâäéèêëïîôöùûüç]{3,}", phrase.lower())
        score = sum(frequences.get(m, 0) for m in mots_phrase)
        # Léger bonus aux phrases situées en début de document (souvent l'intro/objectif)
        score += max(0, 5 - i) * 2
        scores.append((score, i, phrase))

    # On garde les meilleures phrases, puis on les remet dans l'ordre du texte
    meilleures = sorted(scores, key=lambda t: t[0], reverse=True)[:nb_points]
    meilleures_ordonnees = [phrase for _, _, phrase in sorted(meilleures, key=lambda t: t[1])]

    # BRANCHEMENT IA RÉELLE (optionnel) :
    # Remplacer ce bloc par un appel à un LLM avec un prompt du type :
    #   "Résume ce cours en 5 points clés, en français : {texte}"
    # pour un résumé abstractif (reformulé) plutôt qu'extractif.

    return meilleures_ordonnees


# ---------------------------------------------------------------------------
# 3. TRADUCTION AUTOMATIQUE (Moré / Français / Anglais) — point d'extension
# ---------------------------------------------------------------------------

def traduire_texte(texte: str, langue_cible: str) -> str:
    """
    Point d'extension pour la traduction automatique des publications.

    LIMITE HONNÊTE : il n'existe pas aujourd'hui de service de traduction
    automatique fiable et largement disponible pour le Moré (langue peu
    dotée numériquement). Le Français <-> Anglais peut en revanche être
    branché facilement sur une API de traduction (ex: DeepL, Google
    Cloud Translate, ou un LLM) avec votre propre clé API.

    Cette fonction est donc un stub fonctionnel : elle renvoie le texte
    original accompagné d'une mention explicite, plutôt que de simuler une
    fausse traduction qui induirait les utilisateurs en erreur.
    """
    if langue_cible.lower() in ("fr", "français", "francais"):
        return texte  # déjà en français dans la plupart des cas d'usage BF

    return (f"[Traduction automatique non disponible pour '{langue_cible}' dans cette version. "
            f"Texte original : {texte}]")
