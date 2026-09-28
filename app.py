import csv
import os
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string

# ==========================================
# CONFIGURATION
# ==========================================
FICHIER_RESULTATS = "resultats_backyard.csv"
FICHIER_PARTICIPANTS = "participants.csv"
DUREE_BOUCLE_MINUTES = 60
DELAI_DE_GRACE_SECONDES = 60

app = Flask(__name__)
lock = threading.Lock()  # Protection pour éviter les conflits si 2 ordis valident en même temps

# --- VARIABLES GLOBALES EN MÉMOIRE ---
etat_course = {
    "start_time": None,
    "historique_boucles": {},  # {1: set('42', '7'), 2: set('42')}
    "coureurs": {},            # {'42': 'Jean Dupont'}
    "logs_recents": []         # Liste des dernières arrivées pour l'affichage
}

def charger_participants():
    if not os.path.exists(FICHIER_PARTICIPANTS):
        with open(FICHIER_PARTICIPANTS, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Dossard", "Nom", "Prenom"])
            writer.writerow(["42", "Exemple", "Coureur"])
    else:
        with open(FICHIER_PARTICIPANTS, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 3:
                    etat_course["coureurs"][row[0].strip()] = f"{row[2].strip()} {row[1].strip()}"

def creer_csv_si_inexistant():
    if not os.path.exists(FICHIER_RESULTATS):
        with open(FICHIER_RESULTATS, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Boucle", "Dossard", "Nom", "Heure_Arrivee", "Temps_Boucle", "Temps_Repos", "Statut"])

charger_participants()
creer_csv_si_inexistant()

def obtenir_etat_boucle():
    if not etat_course["start_time"]:
        return 1, None, None
    maintenant = datetime.now()
    secondes_ecoulees = (maintenant - etat_course["start_time"]).total_seconds()
    num_boucle = int(secondes_ecoulees // (DUREE_BOUCLE_MINUTES * 60)) + 1
    debut = etat_course["start_time"] + timedelta(minutes=(num_boucle - 1) * DUREE_BOUCLE_MINUTES)
    fin = debut + timedelta(minutes=DUREE_BOUCLE_MINUTES)
    return num_boucle, debut, fin

# ==========================================
# ROUTES API (Le "Cerveau" du serveur)
# ==========================================

@app.route("/api/state", methods=["GET"])
def get_state():
    """Renvoie l'état actuel de l'horloge et les derniers passages à toutes les pages web connectées."""
    if not etat_course["start_time"]:
        return jsonify({"started": False, "logs": etat_course["logs_recents"]})

    num_boucle, debut_boucle, fin_boucle = obtenir_etat_boucle()
    maintenant = datetime.now()
    temps_restant = int((fin_boucle - maintenant).total_seconds())
    
    if num_boucle not in etat_course["historique_boucles"]:
        etat_course["historique_boucles"][num_boucle] = set()
        etat_course["logs_recents"].insert(0, {"text": f"--- DÉPART BOUCLE {num_boucle} ({debut_boucle.strftime('%H:%M')}) ---", "color": "#f9e2af"})

    return jsonify({
        "started": True,
        "boucle": num_boucle,
        "debut_str": debut_boucle.strftime('%H:%M:%S'),
        "temps_restant": temps_restant,
        "logs": etat_course["logs_recents"][:15] # On envoie juste les 15 derniers pour l'affichage
    })

@app.route("/api/start", methods=["POST"])
def start_race():
    with lock:
        if not etat_course["start_time"]:
            etat_course["start_time"] = datetime.now()
            etat_course["historique_boucles"][1] = set()
            return jsonify({"status": "ok"})
        return jsonify({"status": "already_started"})

@app.route("/api/submit", methods=["POST"])
def submit_dossard():
    dossard = request.json.get("dossard", "").strip()
    is_correction = request.json.get("correction", False)
    
    if not etat_course["start_time"] or not dossard:
        return jsonify({"status": "error", "message": "Course non démarrée ou dossard vide."})

    with lock:
        maintenant = datetime.now()
        num_boucle, debut_boucle, fin_boucle = obtenir_etat_boucle()
        secondes_depuis_debut = (maintenant - debut_boucle).total_seconds()

        # Logique de la période de grâce ou correction manuelle
        boucle_cible = num_boucle
        in_extremis = False

        if is_correction:
            if num_boucle <= 1:
                return jsonify({"status": "error", "message": "Aucune boucle précédente à corriger."})
            boucle_cible = num_boucle - 1
            in_extremis = True
        elif num_boucle > 1 and secondes_depuis_debut <= DELAI_DE_GRACE_SECONDES:
            if dossard not in etat_course["historique_boucles"].get(num_boucle - 1, set()):
                boucle_cible = num_boucle - 1
                in_extremis = True

        return valider_coureur(dossard, boucle_cible, in_extremis)

def valider_coureur(dossard, num_boucle, in_extremis):
    debut_cette_boucle = etat_course["start_time"] + timedelta(minutes=(num_boucle - 1) * DUREE_BOUCLE_MINUTES)
    fin_cette_boucle = debut_cette_boucle + timedelta(minutes=DUREE_BOUCLE_MINUTES)

    if num_boucle not in etat_course["historique_boucles"]:
        etat_course["historique_boucles"][num_boucle] = set()

    if dossard in etat_course["historique_boucles"][num_boucle]:
        return jsonify({"status": "error", "message": f"Dossard {dossard} DÉJÀ enregistré pour la boucle {num_boucle} !"})

    nom_coureur = etat_course["coureurs"].get(dossard, "Inconnu")
    
    if in_extremis:
        heure_arrivee = fin_cette_boucle - timedelta(seconds=1)
        statut = "OK (In extremis)"
    else:
        heure_arrivee = datetime.now()
        statut = "OK"

    temps_boucle = heure_arrivee - debut_cette_boucle
    temps_repos = fin_cette_boucle - heure_arrivee

    b_min, b_sec = divmod(int(temps_boucle.total_seconds()), 60)
    str_temps_boucle = f"{b_min:02d}:{b_sec:02d}"

    if temps_repos.total_seconds() < 0:
        statut = "DNF"
        str_temps_repos = "00:00"
        couleur = "#f38ba8" # Rouge
    else:
        r_min, r_sec = divmod(int(temps_repos.total_seconds()), 60)
        str_temps_repos = f"{r_min:02d}:{r_sec:02d}"
        couleur = "#a6e3a1" # Vert
        if in_extremis: couleur = "#fab387" # Orange

    # Sauvegarde CSV
    with open(FICHIER_RESULTATS, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([num_boucle, dossard, nom_coureur, heure_arrivee.strftime("%H:%M:%S"), str_temps_boucle, str_temps_repos, statut])

    etat_course["historique_boucles"][num_boucle].add(dossard)
    texte_log = f"[B{num_boucle}] {dossard}-{nom_coureur} | Tour: {str_temps_boucle} | Repos: {str_temps_repos} {statut}"
    etat_course["logs_recents"].insert(0, {"text": texte_log, "color": couleur})

    return jsonify({"status": "ok", "message": f"{dossard} validé !"})


# ==========================================
# PAGE WEB (L'interface visuelle)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chrono Backyard Ultra</title>
    <style>
        body { font-family: 'Helvetica', Arial, sans-serif; background-color: #1e1e2e; color: #cdd6f4; text-align: center; margin: 0; padding: 20px; }
        h1 { color: #ffffff; }
        .clock { font-size: 3em; font-weight: bold; margin: 20px 0; color: #f9e2af; }
        .danger { color: #f38ba8 !important; }
        .safe { color: #a6e3a1 !important; }
        input[type="text"] { font-size: 2em; padding: 10px; width: 150px; text-align: center; font-weight: bold; border: 2px solid #313244; border-radius: 8px; background: #11111b; color: white; }
        button { font-size: 1.2em; padding: 10px 20px; margin: 10px; cursor: pointer; border: none; border-radius: 8px; font-weight: bold; }
        .btn-start { background-color: #a6e3a1; color: #11111b; }
        .btn-correction { background-color: #f38ba8; color: #11111b; font-size: 1em; }
        .logs { background-color: #181825; padding: 20px; border-radius: 8px; max-width: 600px; margin: 20px auto; text-align: left; font-family: monospace; font-size: 1.1em; height: 300px; overflow-y: auto; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <h1>Chronométrage Backyard Ultra</h1>
    
    <div id="start-section">
        <button class="btn-start" onclick="startRace()">LANCER LA COURSE (BOUCLE 1)</button>
    </div>

    <div id="race-section" class="hidden">
        <h2 id="loop-info">Boucle -- en cours</h2>
        <div class="clock" id="countdown">--:--</div>

        <form id="chrono-form" onsubmit="submitDossard(event, false)">
            <label style="font-size: 1.5em; display: block; margin-bottom: 10px;">Dossard :</label>
            <input type="text" id="dossard-input" autocomplete="off" autofocus>
            <button type="submit" style="display:none;">Valider</button>
        </form>

        <button class="btn-correction" onclick="promptCorrection()">⚠️ Oubli : Repêcher pour la boucle précédente</button>
    </div>

    <div class="logs" id="logs-container">
        <!-- Les logs apparaitront ici -->
    </div>

    <script>
        const dossardInput = document.getElementById("dossard-input");

        // Fonction pour mettre à jour l'affichage en interrogeant le serveur
        async function fetchState() {
            const res = await fetch("/api/state");
            const data = await res.json();
            
            if (data.started) {
                document.getElementById("start-section").classList.add("hidden");
                document.getElementById("race-section").classList.remove("hidden");
                
                document.getElementById("loop-info").innerText = `Boucle ${data.boucle} en cours | Début : ${data.debut_str}`;
                
                // Formatage de l'horloge
                let sec = data.temps_restant;
                let clockEl = document.getElementById("countdown");
                if (sec > 0) {
                    let m = Math.floor(sec / 60).toString().padStart(2, '0');
                    let s = (sec % 60).toString().padStart(2, '0');
                    clockEl.innerText = `Prochain départ dans : ${m}:${s}`;
                    clockEl.className = sec < 180 ? "clock danger" : "clock"; // Rouge si < 3 minutes
                } else {
                    clockEl.innerText = "TOP DÉPART !";
                    clockEl.className = "clock safe";
                }
            }

            // Mise à jour de la liste des arrivées
            const logsHtml = data.logs.map(log => `<div style="color: ${log.color}; margin-bottom: 5px;">${log.text}</div>`).join('');
            document.getElementById("logs-container").innerHTML = logsHtml;
        }

        async function startRace() {
            if(confirm("Êtes-vous sûr de vouloir démarrer la course maintenant ?")) {
                await fetch("/api/start", { method: "POST" });
                fetchState();
            }
        }

        async function submitDossard(event, isCorrection, overrideDossard = null) {
            if(event) event.preventDefault();
            
            let num = overrideDossard || dossardInput.value;
            if(!num) return;

            const res = await fetch("/api/submit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ dossard: num, correction: isCorrection })
            });
            const result = await res.json();
            
            if (result.status === "error") {
                alert(result.message);
            }

            dossardInput.value = "";
            dossardInput.focus();
            fetchState(); // Actualise immédiatement l'affichage
        }

        function promptCorrection() {
            let num = prompt("⚠️ Oubli : Entrez le dossard à repêcher pour la BOUCLE PRÉCÉDENTE :");
            if (num) {
                submitDossard(null, true, num);
            }
            dossardInput.focus();
        }

        // Interroger le serveur toutes les secondes pour actualiser l'horloge
        setInterval(fetchState, 1000);
        fetchState();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == "__main__":
    # HOST='0.0.0.0' est LA ligne magique qui autorise les autres ordinateurs à se connecter !
    app.run(host="0.0.0.0", port=8000, debug=False)