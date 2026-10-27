# Système de Chronométrage Multi-Postes — Backyard Ultra

![Status](https://img.shields.io/badge/Status-Version_Finale-4caf50?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Backend-Flask_REST_API-000000?style=for-the-badge&logo=flask&logoColor=white)

Application de chronométrage et de pointage de dossards en temps réel conçue pour la course d'endurance au format **Backyard Ultra** (une boucle de 6,706 km à parcourir toutes les 60 minutes). Le système permet à plusieurs opérateurs connectés sur un même réseau local (Wi-Fi / LAN) de saisir simultanément les arrivées sur la ligne sans conflit d'écriture.

> **Contexte du projet :** Ce projet a été développé par Aurélien Capron pour l'événement "Backyard de Phelma", organisé les 24 et 25 octobre 2026. L'architecture globale, la logique métier et le code ont été élaborés avec l'assistance d'une Intelligence Artificielle pour garantir un fonctionnement robuste et en temps réel.

---

## Sommaire
1. [Architecture réseau et fonctionnement](#architecture-réseau-et-fonctionnement)
2. [Règles métier gérées automatiquement](#règles-métier-gérées-automatiquement)
3. [Fonctionnalités implémentées](#fonctionnalités-implémentées)
4. [Structure du dépôt](#structure-du-dépôt)
5. [Installation et démarrage rapide](#installation-et-démarrage-rapide)

---

## Architecture réseau et fonctionnement

Lors d'une arrivée groupée sur la ligne, un seul opérateur peut difficilement saisir tous les numéros de dossards à la volée. Le projet propose une architecture Client-Serveur en réseau local (`app.py` — Flask) :

* Un ordinateur principal héberge le serveur Flask sur toutes les interfaces réseau (`0.0.0.0:8000`).
* Plusieurs postes (ordinateurs, tablettes ou smartphones connectés au même réseau Wi-Fi/LAN) accèdent à l'interface web et valident les dossards en parallèle via l'API REST (`POST /api/submit`).
* Un **verrou d'exclusion mutuelle (`threading.Lock()`)** protège la section critique pour garantir qu'aucun dossard n'est enregistré en doublon sur une même boucle et que les écritures dans `resultats_backyard.csv` sont strictement sérialisées.
* Les interfaces clientes se synchronisent toutes les secondes (`GET /api/state`) sur l'horloge centrale du serveur et affichent le compte à rebours avant le départ de la boucle suivante (passage au rouge sous la barre des 3 minutes restantes).

---

## Règles métier gérées automatiquement

- **Calcul automatique des temps :** À chaque validation d'un numéro de dossard, le serveur calcule le **temps de boucle** écoulé depuis le départ de l'heure courante ainsi que le **temps de repos restant** avant le coup d'envoi de la boucle suivante.
- **Période de grâce automatique (*In extremis*) :** Si un coureur franchit la ligne sur le fil et que l'opérateur valide son dossard dans les 60 premières secondes de la nouvelle boucle (`DELAI_DE_GRACE_SECONDES = 60`), le système vérifie si ce coureur avait déjà été pointé sur la boucle précédente. S'il ne l'était pas, l'arrivée est automatiquement rattachée à la boucle N-1 avec le statut `OK (In extremis)`.
- **Repêchage manuel :** Un bouton dédié permet de rattacher manuellement un dossard oublié à la boucle précédente (N-1) sans fausser le pointage de la boucle en cours.
- **Classement dynamique :** Le classement se base en priorité sur le **nombre total de boucles validées** (ordre décroissant). En cas d'égalité, les coureurs sont départagés par leur **temps moyen par boucle** (le plus rapide l'emporte).

---

## Fonctionnalités implémentées

### Fonctionnalités opérationnelles
- [x] Serveur HTTP local multi-postes sous Flask (`host="0.0.0.0"`, port `8000`)
- [x] Synchronisation temps réel de l'horloge de course sur tous les écrans connectés
- [x] Protection contre les accès concurrents par mutex (`threading.Lock()`) et anti-doublon par boucle
- [x] Association automatique `Dossard -> Prénom Nom` depuis `participants.csv`
- [x] Gestion de la période de grâce automatique (60 s) et du repêchage manuel sur la boucle N-1
- [x] Sauvegarde persistante au fil de l'eau dans `resultats_backyard.csv`
- [x] Export avancé des classements et temps individuels au format Excel (fichiers globaux et statuts des éliminations par boucle)
- [x] Tableau de bord interactif par coureur (Borne interactive pour les participants)
- [x] Affichage TV optimisé (Viewport Units) adaptatif pour grand écran (Leaderboard dynamique)
- [x] Écran "Speaker" détaillé listant les coureurs sur le parcours et les arrivants en direct
- [x] Roulette d'animation (Tirage au sort dynamique parmi les participants en lice)
- [x] Reprise sur panne : rechargement automatique de l'état de la course à partir de `resultats_backyard.csv` en cas de redémarrage du script ou restauration depuis un fichier de backup

---

## Structure du dépôt

```text
backyard-ultra-race-tracker/
├── .gitignore
├── README.md
├── requirements.txt                # Dépendances Python (Flask, openpyxl)
├── app.py                          # Serveur web multi-postes (Flask + API REST + UIs HTML)
├── participants.csv                # Fichier source des coureurs inscrits
├── resultats_backyard.csv          # Fichier de base de données de la course généré automatiquement
└── static/
    ├── logo_backyard.png           # Logo de l'événement (24-25 Octobre)
    ├── logo_tdr.png                # Logo du partenaire TDR
    └── logo_fitness_park.png       # Logo du partenaire Fitness Park
