// =============================================================
// app.js — Wend'Kugri
// JavaScript vanille (aucune dépendance) : interactions du fil,
// like/signalement en AJAX, compteur de caractères, sélecteur de
// type de publication, et mode "hors-ligne" (10 cours max, stockés
// localement dans le navigateur).
// Copyright by Computer Science Solution-BF
// =============================================================

document.addEventListener("DOMContentLoaded", function () {
  initialiserLikes();
  initialiserSignalements();
  initialiserCompteurCaracteres();
  initialiserSelecteurType();
  initialiserSauvegardeHorsLigne();
  initialiserRafraichissementDefi();
});

/* -----------------------------------------------------------
   1. LIKES ("Points de Connaissance") en AJAX
----------------------------------------------------------- */
function initialiserLikes() {
  document.querySelectorAll("[data-action='aimer']").forEach(function (bouton) {
    bouton.addEventListener("click", function () {
      const publicationId = bouton.dataset.publicationId;

      fetch(`/publication/${publicationId}/aimer`, { method: "POST" })
        .then((reponse) => reponse.json())
        .then((donnees) => {
          if (!donnees.succes) return;
          const compteur = bouton.querySelector("[data-compteur-likes]");
          if (compteur) compteur.textContent = donnees.nb_likes;
          bouton.classList.toggle("actif", donnees.aime);
        })
        .catch(() => console.error("Impossible d'enregistrer le like pour le moment."));
    });
  });
}

/* -----------------------------------------------------------
   2. SIGNALEMENT (anti-désordre communautaire)
----------------------------------------------------------- */
function initialiserSignalements() {
  document.querySelectorAll("[data-action='signaler']").forEach(function (bouton) {
    bouton.addEventListener("click", function () {
      const confirmation = confirm("Signaler cette publication comme ne respectant pas l'esprit de Wend'Kugri ?");
      if (!confirmation) return;

      const publicationId = bouton.dataset.publicationId;
      const donneesFormulaire = new FormData();
      donneesFormulaire.append("raison", "Contenu jugé hors-sujet par un membre");

      fetch(`/publication/${publicationId}/signaler`, { method: "POST", body: donneesFormulaire })
        .then((reponse) => reponse.json())
        .then((donnees) => {
          if (!donnees.succes) {
            alert(donnees.message || "Une erreur est survenue.");
            return;
          }
          bouton.disabled = true;
          bouton.classList.add("actif");
          if (donnees.masquee) {
            const fiche = bouton.closest(".fiche-savoir");
            if (fiche) {
              fiche.style.opacity = "0.4";
              fiche.insertAdjacentHTML("beforeend",
                '<p class="text-xs text-rouge font-semibold mt-2">Publication masquée après plusieurs signalements.</p>');
            }
          }
        });
    });
  });
}

/* -----------------------------------------------------------
   3. COMPTEUR DE CARACTÈRES (max 500, imposé par le cahier des charges)
----------------------------------------------------------- */
function initialiserCompteurCaracteres() {
  const zoneTexte = document.getElementById("contenu-publication");
  const compteur = document.getElementById("compteur-caracteres");
  if (!zoneTexte || !compteur) return;

  const LIMITE = 500;
  function mettreAJour() {
    const longueur = zoneTexte.value.length;
    compteur.textContent = `${longueur} / ${LIMITE}`;
    compteur.classList.toggle("limite-atteinte", longueur > LIMITE);
  }
  zoneTexte.addEventListener("input", mettreAJour);
  mettreAJour();
}

/* -----------------------------------------------------------
   4. SÉLECTEUR DE TYPE DE PUBLICATION
   Affiche les champs adaptés (fichier / vidéo) et bloque le bouton
   Publier tant qu'un domaine n'est pas choisi (règle du cahier des charges).
----------------------------------------------------------- */
function initialiserSelecteurType() {
  const cartes = document.querySelectorAll(".carte-type-choix");
  const champTypeCache = document.getElementById("type-publication-cache");
  const boutonPublier = document.getElementById("bouton-publier");
  const selecteurDomaine = document.getElementById("selecteur-domaine");

  if (!cartes.length) return;

  const sections = {
    astuce: document.getElementById("champs-astuce"),
    cours: document.getElementById("champs-cours"),
    video: document.getElementById("champs-video"),
    question: document.getElementById("champs-question"),
  };

  function selectionnerType(type) {
    cartes.forEach((c) => c.classList.toggle("selectionnee", c.dataset.type === type));
    Object.keys(sections).forEach((cle) => {
      if (sections[cle]) sections[cle].classList.toggle("hidden", cle !== type);
    });
    if (champTypeCache) champTypeCache.value = type;
    verifierFormulaire();
  }

  cartes.forEach((carte) => {
    carte.addEventListener("click", () => selectionnerType(carte.dataset.type));
  });

  function verifierFormulaire() {
    if (!boutonPublier) return;
    const typeChoisi = champTypeCache ? champTypeCache.value : "";
    const domaineChoisi = selecteurDomaine ? selecteurDomaine.value : "";
    // Le bouton Publier reste désactivé tant qu'aucun tag domaine n'est choisi
    boutonPublier.disabled = !typeChoisi || !domaineChoisi;
    boutonPublier.classList.toggle("opacity-40", boutonPublier.disabled);
    boutonPublier.classList.toggle("cursor-not-allowed", boutonPublier.disabled);
  }

  if (selecteurDomaine) selecteurDomaine.addEventListener("change", verifierFormulaire);
  verifierFormulaire();
}

/* -----------------------------------------------------------
   5. MODE HORS-LIGNE — sauvegarde locale de 10 cours maximum
   (fonctionnalité 100% côté navigateur : stockage local uniquement,
   pas de synchronisation serveur dans cette version V1)
----------------------------------------------------------- */
const CLE_STOCKAGE_HORS_LIGNE = "wendkugri_cours_hors_ligne";
const LIMITE_HORS_LIGNE = 10;

function obtenirCoursSauvegardes() {
  try {
    return JSON.parse(localStorage.getItem(CLE_STOCKAGE_HORS_LIGNE)) || [];
  } catch (erreur) {
    return [];
  }
}

function initialiserSauvegardeHorsLigne() {
  document.querySelectorAll("[data-action='sauvegarder-hors-ligne']").forEach(function (bouton) {
    const id = bouton.dataset.publicationId;
    const cours = obtenirCoursSauvegardes();
    if (cours.some((c) => c.id === id)) marquerCommeSauvegarde(bouton);

    bouton.addEventListener("click", function () {
      let liste = obtenirCoursSauvegardes();
      const dejaPresent = liste.some((c) => c.id === id);

      if (dejaPresent) {
        liste = liste.filter((c) => c.id !== id);
        localStorage.setItem(CLE_STOCKAGE_HORS_LIGNE, JSON.stringify(liste));
        bouton.classList.remove("actif");
        bouton.querySelector("[data-libelle]").textContent = "Sauvegarder hors-ligne";
        return;
      }

      if (liste.length >= LIMITE_HORS_LIGNE) {
        alert(`Limite atteinte : vous ne pouvez garder que ${LIMITE_HORS_LIGNE} cours hors-ligne. Retirez-en un avant d'en ajouter un nouveau.`);
        return;
      }

      liste.push({ id: id, titre: bouton.dataset.titre, domaine: bouton.dataset.domaine, url: bouton.dataset.url });
      localStorage.setItem(CLE_STOCKAGE_HORS_LIGNE, JSON.stringify(liste));
      marquerCommeSauvegarde(bouton);
    });
  });
}

function marquerCommeSauvegarde(bouton) {
  bouton.classList.add("actif");
  const libelle = bouton.querySelector("[data-libelle]");
  if (libelle) libelle.textContent = "Sauvegardé ✓";
}

/* -----------------------------------------------------------
   6. Rafraîchissement discret du bandeau "Défi du Jour" (visuel uniquement)
----------------------------------------------------------- */
function initialiserRafraichissementDefi() {
  const bandeau = document.getElementById("bandeau-defi");
  if (bandeau) bandeau.classList.add("opacity-100");
}
