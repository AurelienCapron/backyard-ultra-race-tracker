# Système de Chronométrage Multi-Postes — Backyard Ultra

![Language](https://img.shields.io/badge/Language-Python_3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Backend](https://img.shields.io/badge/Backend-Flask_REST_API-000000?style=for-the-badge&logo=flask&logoColor=white)
![Network](https://img.shields.io/badge/Network-Local_LAN_%2F_Ngrok-006699?style=for-the-badge)
![Data](https://img.shields.io/badge/Data-CSV_Export-4caf50?style=for-the-badge)

Application de chronométrage et de pointage de dossards en temps réel conçue pour la course d'endurance au format **Backyard Ultra** (une boucle de 6,706 km à parcourir toutes les 60 minutes). Le système permet à plusieurs opérateurs connectés sur un même réseau local (Wi-Fi / LAN) de saisir simultanément les arrivées sur la ligne sans conflit d'écriture, et aux coureurs de consulter leurs statistiques à distance via un tunnel ngrok.

- **[Consulter le fichier de configuration des participants (CSV)](participants.csv)**
- **[Consulter un exemple de base de données générée en course (CSV)](resultats_backyard.csv)**
- **[Voir le code source du serveur web multi-postes (Python)](app.py)**

---

## Sommaire
1. [Aperçu des interfaces](#aperçu-des-interfaces)
2. [Architecture réseau et fonctionnement](#architecture-réseau-et-fonctionnement)
3. [Règles métier et fonctionnalités](#règles-métier-et-fonctionnalités)
4. [Structure du dépôt](#structure-du-dépôt)
5. [Auteurs et encadrement](#auteurs-et-encadrement)

---

## Aperçu des interfaces

| Pupitre de pointage | Affichage TV (Leaderboard) |
| :---: | :---: |
| ![Interface de pointage](assets/page_pointage.png) | ![Écran TV dynamique](assets/page_tv.png) |
| *Interface de contrôle principale, sécurisée par code PIN.* | *Tableau de bord auto-adaptatif pour affichage sur vidéoprojecteur.* |

| Écran Speaker | Tableau de Classement |
| :---: | :---: |
| ![Écran d'animation Speaker](assets/page_speaker.png) | ![Classement général](assets/page_classement.png) |
| *Vue détaillée de l'état du peloton pour l'animation.* | *Classement en direct avec fonctions d'export Excel.* |

| Borne Coureur | Page Podium |
| :---: | :---: |
| ![Borne d'accès coureur](assets/QRcode_Stats_Backyard.jpg) | ![Affichage des résultats](assets/page_podium.png) |
| *Affiche scannable via QR code menant aux statistiques individuelles via ngrok.* | *Résultats finaux et records absolus de l'épreuve.* |

---

## Architecture réseau et fonctionnement

![Architecture Réseau](assets/network_architecture.svg)

Lors d'une arrivée groupée sur la ligne, un seul opérateur peut difficilement saisir tous les numéros de dossards à la volée. Le projet propose une architecture Client-Serveur en réseau local (`app.py` — Flask) ouverte sur l'extérieur via **ngrok** :

- Un ordinateur principal héberge le serveur Flask sur toutes les interfaces réseau (`0.0.0.0:8000`).
- Plusieurs postes (ordinateurs, tablettes ou smartphones connectés au même réseau) accèdent à l'interface web et valident les dossards en parallèle via l'API REST (`POST /api/submit`).
- Un tunnel **ngrok** est utilisé pour exposer le serveur local sur Internet de manière sécurisée. Cela permet aux coureurs, peu importe où ils se trouvent sur le parcours ou au camp de base, d'accéder à la "Borne Coureur" (`/coureur`) depuis leur propre smartphone en 4G pour consulter leurs statistiques en direct.
- Un **verrou d'exclusion mutuelle (`threading.Lock()`)** protège la section critique pour garantir qu'aucun dossard n'est enregistré en doublon sur une même boucle et que les écritures dans `resultats_backyard.csv` sont strictement sérialisées.

---

## Règles métier et fonctionnalités

### Gestion automatique de la course
- **Calcul automatique des temps :** À chaque validation d'un numéro de dossard, le serveur calcule le **temps de boucle** écoulé depuis le départ de l'heure courante ainsi que le **temps de repos restant** avant le coup d'envoi de la boucle suivante.
- **Période de grâce automatique (*In extremis*) :** Si un coureur franchit la ligne sur le fil et que l'opérateur valide son dossard dans les 60 premières secondes de la nouvelle boucle (`DELAI_DE_GRACE_SECONDES = 60`), l'arrivée est rattachée à la boucle N-1 avec le statut `OK (In extremis)`.
- **Classement dynamique :** Le classement se base en priorité sur le **nombre total de boucles validées** (ordre décroissant). En cas d'égalité, les coureurs sont départagés par leur **temps moyen par boucle** (le plus rapide l'emporte).

### Fonctionnalités techniques implémentées
- [x] Serveur HTTP local multi-postes sous Flask (`host="0.0.0.0"`, port `8000`)
- [x] Accès coureurs via tunnel Internet (ngrok)
- [x] Synchronisation temps réel de l'horloge de course sur tous les écrans connectés
- [x] Protection contre les accès concurrents par mutex (`threading.Lock()`)
- [x] Association automatique `Dossard -> Prénom Nom` depuis `participants.csv`
- [x] Sauvegarde persistante au fil de l'eau dans `resultats_backyard.csv`
- [x] Export avancé des classements et temps individuels au format Excel
- [x] Écran "Speaker" détaillé listant les coureurs sur le parcours et les arrivants en direct (`/speaker`)
- [x] Roulette d'animation (Tirage au sort dynamique parmi les participants en lice) (`/roulette`)
- [x] Reprise sur panne : rechargement automatique de l'état de la course à partir du CSV en cas de redémarrage.

---

## Structure du dépôt

```text
backyard-ultra-race-tracker/
├── .gitignore
├── README.md
├── requirements.txt                # Dépendances Python (Flask, openpyxl)
├── app.py                          # Serveur web multi-postes (Flask + API REST + UIs HTML)
├── participants.csv                # Fichier source des coureurs inscrits
├── resultats_backyard.csv          # Base de données de la course générée automatiquement
├── assets/                         # Dossier contenant les ressources graphiques
│   ├── page_classement.png
│   ├── page_podium.png
│   ├── page_speaker.png
│   ├── page_tv.png
│   ├── page_pointage.png
│   ├── QRcode_Stats_Backyard.jpg
│   └── network_architecture.svg    # Schéma de l'architecture réseau
└── static/
    ├── logo_backyard.png           # Logo de l'événement
    ├── logo_tdr.png                # Logo du partenaire TDR
    └── logo_fitness_park.png       # Logo du partenaire Fitness Park
