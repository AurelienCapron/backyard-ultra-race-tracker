import csv
from datetime import datetime, timedelta
import os
import tkinter as tk
from tkinter import messagebox

# ==========================================
# CONFIGURATION
# ==========================================
FICHIER_RESULTATS = "resultats_backyard.csv"
DUREE_BOUCLE_MINUTES = 60


class BackyardTimerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Chronométrage Backyard Ultra")
        self.root.geometry("650x620")
        self.root.configure(bg="#1e1e2e")

        self.start_time = None
        self.enregistrements_boucle_actuelle = set()

        self._creer_csv_si_inexistant()
        self._construire_interface()

    def _creer_csv_si_inexistant(self):
        if not os.path.exists(FICHIER_RESULTATS):
            with open(FICHIER_RESULTATS, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Boucle",
                    "Dossard",
                    "Heure_Arrivee",
                    "Temps_Boucle",
                    "Temps_Repos",
                    "Statut",
                ])

    def _construire_interface(self):
        # 1. En-tête & Lancement
        frame_top = tk.Frame(self.root, bg="#1e1e2e")
        frame_top.pack(pady=15)

        self.btn_start = tk.Button(
            frame_top,
            text="LANCER LA COURSE (BOUCLE 1)",
            bg="#a6e3a1",
            fg="#11111b",
            font=("Helvetica", 12, "bold"),
            command=self.demarrer_course,
            padx=10,
            pady=5,
        )
        self.btn_start.pack()

        self.lbl_info_course = tk.Label(
            self.root,
            text="Course non démarrée",
            font=("Helvetica", 14),
            bg="#1e1e2e",
            fg="#cdd6f4",
        )
        self.lbl_info_course.pack(pady=5)

        # 2. Compte à rebours du départ suivant
        self.lbl_countdown = tk.Label(
            self.root,
            text="Prochain départ : --:--",
            font=("Helvetica", 18, "bold"),
            bg="#1e1e2e",
            fg="#f9e2af",
        )
        self.lbl_countdown.pack(pady=5)

        # 3. Champ de saisie dossard
        frame_input = tk.Frame(self.root, bg="#1e1e2e")
        frame_input.pack(pady=15)

        tk.Label(
            frame_input,
            text="Dossard :",
            font=("Helvetica", 20, "bold"),
            bg="#1e1e2e",
            fg="#ffffff",
        ).pack(side=tk.LEFT, padx=10)

        self.entry_dossard = tk.Entry(
            frame_input,
            font=("Helvetica", 24, "bold"),
            width=8,
            justify="center",
        )
        self.entry_dossard.pack(side=tk.LEFT)
        self.entry_dossard.bind("<Return>", self.enregistrer_dossard)

        # 4. Affichage du dernier passage
        self.lbl_dernier = tk.Label(
            self.root,
            text="En attente du premier arrivant...",
            font=("Helvetica", 14),
            bg="#313244",
            fg="#cdd6f4",
            padx=15,
            pady=15,
            relief="groove",
        )
        self.lbl_dernier.pack(fill="x", padx=30, pady=15)

        # 5. Historique de la boucle
        tk.Label(
            self.root,
            text="Arrivées de la boucle en cours :",
            font=("Helvetica", 11, "bold"),
            bg="#1e1e2e",
            fg="#a6adc8",
        ).pack(anchor="w", padx=30)

        self.listbox = tk.Listbox(
            self.root,
            font=("Consolas", 11),
            bg="#181825",
            fg="#cdd6f4",
            height=8,
        )
        self.listbox.pack(fill="both", expand=True, padx=30, pady=(5, 20))

    def demarrer_course(self):
        self.start_time = datetime.now()
        self.btn_start.config(
            state="disabled", text="COURSE EN COURS", bg="#45475a"
        )
        self.entry_dossard.focus_set()
        self._actualiser_horloge()

    def _obtenir_etat_boucle(self):
        if not self.start_time:
            return 1, None, None

        maintenant = datetime.now()
        secondes_ecoulees = (maintenant - self.start_time).total_seconds()
        numero_boucle = int(secondes_ecoulees // (DUREE_BOUCLE_MINUTES * 60)) + 1

        debut_boucle = self.start_time + timedelta(
            minutes=(numero_boucle - 1) * DUREE_BOUCLE_MINUTES
        )
        fin_boucle = debut_boucle + timedelta(minutes=DUREE_BOUCLE_MINUTES)
        return numero_boucle, debut_boucle, fin_boucle

    def _actualiser_horloge(self):
        if not self.start_time:
            return

        maintenant = datetime.now()
        num_boucle, debut_boucle, fin_boucle = self._obtenir_etat_boucle()

        # Réinitialisation de la liste des arrivés au changement d'heure
        if (
            hasattr(self, "derniere_boucle_vue")
            and self.derniere_boucle_vue != num_boucle
        ):
            self.enregistrements_boucle_actuelle.clear()
            self.listbox.insert(
                0, f"--- DÉPART BOUCLE {num_boucle} ({debut_boucle.strftime('%H:%M')}) ---"
            )
        self.derniere_boucle_vue = num_boucle

        temps_restant = fin_boucle - maintenant
        if temps_restant.total_seconds() > 0:
            m, s = divmod(int(temps_restant.total_seconds()), 60)
            self.lbl_countdown.config(
                text=f"Prochain départ (Boucle {num_boucle+1}) dans : {m:02d}:{s:02d}",
                fg="#f9e2af" if m >= 3 else "#f38ba8",
            )
        else:
            self.lbl_countdown.config(
                text="TOP DÉPART !", fg="#a6e3a1"
            )

        self.lbl_info_course.config(
            text=f"Boucle {num_boucle} en cours | Début : {debut_boucle.strftime('%H:%M:%S')}"
        )
        self.root.after(1000, self._actualiser_horloge)

    def enregistrer_dossard(self, event=None):
        if not self.start_time:
            messagebox.showwarning(
                "Attention", "Veuillez d'abord démarrer la course !"
            )
            return

        dossard = self.entry_dossard.get().strip()
        self.entry_dossard.delete(0, tk.END)

        if not dossard:
            return

        maintenant = datetime.now()
        num_boucle, debut_boucle, fin_boucle = self._obtenir_etat_boucle()

        # Vérification doublon sur la même boucle
        if dossard in self.enregistrements_boucle_actuelle:
            messagebox.showwarning(
                "Doublon",
                f"Le dossard {dossard} a déjà été enregistré sur la boucle {num_boucle} !",
            )
            return

        # Calculs des temps
        temps_boucle = maintenant - debut_boucle
        temps_repos = fin_boucle - maintenant

        total_sec = int(temps_boucle.total_seconds())
        b_min, b_sec = divmod(total_sec, 60)
        str_temps_boucle = f"{b_min:02d}:{b_sec:02d}"

        # Détection DNF (Hors-délai > 60 minutes)
        if temps_repos.total_seconds() < 0:
            statut = "DNF (Hors-délai)"
            str_temps_repos = "00:00"
            couleur = "#f38ba8"  # Rouge
        else:
            statut = "OK"
            r_min, r_sec = divmod(int(temps_repos.total_seconds()), 60)
            str_temps_repos = f"{r_min:02d}:{r_sec:02d}"
            couleur = "#a6e3a1"  # Vert

        # Écriture immédiate dans le CSV
        with open(FICHIER_RESULTATS, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                num_boucle,
                dossard,
                maintenant.strftime("%H:%M:%S"),
                str_temps_boucle,
                str_temps_repos,
                statut,
            ])

        self.enregistrements_boucle_actuelle.add(dossard)

        # Mise à jour de l'affichage
        texte_resultat = (
            f"Dossard {dossard} | Tour : {str_temps_boucle} | "
            f"Repos restant : {str_temps_repos} ({statut})"
        )
        self.lbl_dernier.config(text=texte_resultat, fg=couleur)
        self.listbox.insert(
            0, f"[{maintenant.strftime('%H:%M:%S')}] #{dossard} - Tour: {str_temps_boucle} | Repos: {str_temps_repos}"
        )


if __name__ == "__main__":
    fenetre = tk.Tk()
    app = BackyardTimerApp(fenetre)
    fenetre.mainloop()