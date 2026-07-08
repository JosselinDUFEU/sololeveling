import flet as ft
import json
import os
import math
import time
from datetime import datetime, timedelta

FICHIER_SAUVEGARDE = "data_solo_leveling.json"

# --- 1. INITIALISATION GLOBALE DES DONNÉES ---
def charger_donnees():
    default_data = {"niveau": 1, "xp_actuel": 0, "quetes": []}
    if os.path.exists(FICHIER_SAUVEGARDE):
        try:
            with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict): return default_data
                if "niveau" not in data: data["niveau"] = 1
                if "xp_actuel" not in data: data["xp_actuel"] = 0
                if "quetes" not in data: data["quetes"] = []
                
                for q in data["quetes"]:
                    if "streak" not in q:
                        q["streak"] = 0
                return data
        except Exception:
            pass
    return default_data

def sauvegarder_donnees_globales(donnees_a_sauver):
    try:
        with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
            json.dump(donnees_a_sauver, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

donnees = charger_donnees()

def main(page: ft.Page):
    global donnees
    
    page.title = "Solo Leveling Tracker"
    page.bgcolor = "#0B0C10"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    page.window.width = 450       
    page.window.height = 750      
    page.window.resizable = False  
    
    page.index_creation_actif = 0

    # --- 2. LOGIQUE DE CALCUL DE L'XP ---
    def xp_necessaire_pour_niveau(niveau):
        base_xp = 100
        if niveau <= 5: return niveau * base_xp
        elif niveau <= 10: return math.ceil((niveau * base_xp) * 1.2)
        elif niveau <= 15: return math.ceil((niveau * base_xp) * 1.5)
        elif niveau <= 20: return math.ceil((niveau * base_xp) * 1.8)
        elif niveau <= 25: return math.ceil((niveau * base_xp) * 2.0)
        else: return math.ceil((niveau * base_xp) * 2.5)

    def calculer_xp_multi_plateaux(quete, streak_cible):
        base_xp = quete.get("base_xp", 10)
        paliers = quete.get("paliers", [[1, 1], [10, 1.05], [25, 1.01], [999, 1.005]])
        paliers_tries = sorted(paliers, key=lambda x: x[0])
        xp_calculee = float(base_xp)
        
        for jour in range(1, streak_cible + 1):
            facteur_du_jour = 1.0
            for limite, facteur in paliers_tries:
                if jour <= limite:
                    facteur_du_jour = facteur
                    break
            else:
                facteur_du_jour = paliers_tries[-1][1]
            xp_calculee *= facteur_du_jour
            
        return round(xp_calculee, 1)

    def parser_paliers_texte(texte):
        if not texte or not texte.strip():
            return [[1, 1], [10, 1.05], [25, 1.01], [999, 1.005]]
        try:
            paliers = []
            blocs = texte.split(",")
            for b in blocs:
                if ":" in b:
                    limite, facteur = b.split(":")
                    paliers.append([int(limite.strip()), float(facteur.strip())])
            return paliers if paliers else [[1, 1], [10, 1.05], [25, 1.01], [999, 1.005]]
        except Exception:
            return [[1, 1], [10, 1.05], [25, 1.01], [999, 1.005]]

    # --- 3. COMPOSANTS VISUELS DU HEADER ---
    lbl_niveau = ft.Text(f"NIVEAU {donnees['niveau']}", size=20, color="#00FFFF", weight=ft.FontWeight.BOLD)
    lbl_xp_texte = ft.Text("", size=11, color="#A9A9A9")
    barre_xp = ft.ProgressBar(value=0.0, color="#00FFFF", bgcolor="#1F2833", height=10, border_radius=5)

    def rafraichir_header_xp():
        niv = donnees["niveau"]
        xp_actuel = donnees["xp_actuel"]
        xp_max = xp_necessaire_pour_niveau(niv)
        barre_xp.value = min(xp_actuel / xp_max, 1.0)
        
        if niv < 5: titre_rang = "Rang E"
        elif niv < 10: titre_rang = "Rang D"
        elif niv < 15: titre_rang = "Rang C"
        elif niv < 20: titre_rang = "Rang B"
        elif niv < 25: titre_rang = "Rang A"
        else: titre_rang = "Rang S"
            
        lbl_niveau.value = f"{titre_rang} | NIVEAU {niv}"
        lbl_xp_texte.value = f"{round(xp_actuel, 1)} / {xp_max} XP"
        page.update()

    def verifier_level_up():
        while donnees["xp_actuel"] >= xp_necessaire_pour_niveau(donnees["niveau"]):
            donnees["xp_actuel"] -= xp_necessaire_pour_niveau(donnees["niveau"])
            donnees["niveau"] += 1
            page.overlay.append(ft.SnackBar(ft.Text(f"LEVEL UP ! Niveau {donnees['niveau']} ! ⚡"), bgcolor="#4B0082"))
            page.overlay[-1].open = True

    # --- 4. FORMULAIRE DE CRÉATION FIXE ---
    txt_titre = ft.TextField(label="Nom de la quête", border_color="#4B0082", focused_border_color="#00FFFF")

    dropdown_frequence_classique = ft.Dropdown(
        label="Fréquence", border_color="#4B0082",
        options=[ft.dropdown.Option(str(i), "Quotidienne" if i==7 else f"{i}/semaine") for i in range(1, 8)],
        value="7"
    )
    txt_xp_classique = ft.TextField(label="XP de base par validation", value="10", border_color="#4B0082", keyboard_type=ft.KeyboardType.NUMBER)
    text_paliers_hab = ft.TextField(label="Facteur de croissance (Multi-plateaux)", value="1:1, 10:1.05, 25:1.01, 999:1.005", border_color="#4B0082")
    
    container_form_habitude = ft.Column([
        dropdown_frequence_classique,
        txt_xp_classique,
        text_paliers_hab,
        ft.Text("Exemple multiplicateur : 10:1.05, 25:1.01", size=11, color="#A9A9A9", italic=True)
    ], spacing=10)

    dropdown_sport_km = ft.Dropdown(
        label="Discipline", border_color="#4B0082",
        options=[
            ft.dropdown.Option("Course à pied", "🏃‍♂️ Course à pied"),
            ft.dropdown.Option("Vélo", "🚴‍♂️ Vélo")
        ],
        value="Course à pied"
    )
    txt_km_hebdo_cible = ft.TextField(label="Kilomètres à faire cette semaine", value="30", border_color="#4B0082", keyboard_type=ft.KeyboardType.NUMBER)
    txt_xp_bonus_km = ft.TextField(label="XP Bonus de fin d'objectif", value="50", border_color="#4B0082", keyboard_type=ft.KeyboardType.NUMBER)
    text_paliers_km = ft.TextField(label="Facteur de croissance (Multi-plateaux)", value="1:1, 10:1.05, 25:1.01, 999:1.005", border_color="#4B0082")

    container_form_km = ft.Column([
        dropdown_sport_km,
        txt_km_hebdo_cible,
        txt_xp_bonus_km,
        text_paliers_km,
        ft.Text("Exemple multiplicateur : 10:1.05, 25:1.01", size=11, color="#A9A9A9", italic=True)
    ], spacing=10, visible=False)

    def switch_to_habitude(e):
        page.index_creation_actif = 0
        txt_tab_hab.value = "● Habitude"
        txt_tab_hab.color = "#00FFFF"
        txt_tab_km.value = "Objectif Km Semaine"
        txt_tab_km.color = "#A9A9A9"
        container_form_habitude.visible = True
        container_form_km.visible = False
        page.update()

    def switch_to_km(e):
        page.index_creation_actif = 1
        txt_tab_hab.value = "Habitude"
        txt_tab_hab.color = "#A9A9A9"
        txt_tab_km.value = "● Objectif Km Semaine"
        txt_tab_km.color = "#00FFFF"
        container_form_habitude.visible = False
        container_form_km.visible = True
        page.update()

    txt_tab_hab = ft.Text("● Habitude", color="#00FFFF", size=14, weight=ft.FontWeight.BOLD)
    txt_tab_km = ft.Text("Objectif Km Semaine", color="#A9A9A9", size=14, weight=ft.FontWeight.BOLD)

    selecteur_onglets_custom = ft.Row(
        controls=[
            ft.GestureDetector(content=txt_tab_hab, on_tap=switch_to_habitude),
            ft.GestureDetector(content=txt_tab_km, on_tap=switch_to_km)
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=30
    )

    def ajouter_nouvelle_quete(e):
        global donnees
        btn_creer.disabled = True
        page.update()
        
        if not txt_titre.value or not txt_titre.value.strip():
            btn_creer.disabled = False
            page.update()
            return
        
        titre_nettoye = txt_titre.value.strip()
        titre_final_verif = titre_nettoye if page.index_creation_actif == 0 else f"[{dropdown_sport_km.value}] " + titre_nettoye
        
        if any(q["titre"].lower().strip() == titre_final_verif.lower().strip() for q in donnees["quetes"]):
            txt_titre.value = ""
            btn_creer.disabled = False
            changer_onglet_vers_liste(None)
            return  

        if page.index_creation_actif == 0:
            liste_paliers = parser_paliers_texte(text_paliers_hab.value)
            nouvelle_q = {
                "titre": titre_nettoye,
                "type": "Classique",
                "jours_cible": int(dropdown_frequence_classique.value),
                "base_xp": float(txt_xp_classique.value) if txt_xp_classique.value.replace('.', '', 1).isdigit() else 10.0,
                "paliers": liste_paliers,
                "streak": 0,
                "derniere_validation": "", 
                "validations_semaine": 0,  
                "derniere_semaine_annee": datetime.now().isocalendar()[1]
            }
        else:
            try:
                target_km = float(txt_km_hebdo_cible.value.replace(",", "."))
            except Exception:
                target_km = 30.0
                
            liste_paliers = parser_paliers_texte(text_paliers_km.value)
            nouvelle_q = {
                "titre": titre_final_verif,
                "type": "ObjectifKmHebdo",
                "sport": dropdown_sport_km.value,
                "km_cible": target_km,
                "km_actuel": 0.0,
                "base_xp": float(txt_xp_bonus_km.value) if txt_xp_bonus_km.value.replace('.', '', 1).isdigit() else 50.0,
                "paliers": liste_paliers,
                "streak": 0,
                "derniere_semaine_annee": datetime.now().isocalendar()[1],
                "nouveau_km_cible": None,
                "nouveau_base_xp": None
            }
        
        donnees["quetes"].append(nouvelle_q)
        sauvegarder_donnees_globales(donnees)
        
        txt_titre.value = ""
        txt_km_hebdo_cible.value = "30"
        txt_xp_classique.value = "10"
        btn_creer.disabled = False
        
        page.controls.clear() 
        page.add(
            ft.Column([
                espace_encoche,
                header_profil,
                ft.Divider(color="#1F2833", thickness=1),
                barre_onglets,
                zone_dynamique
            ])
        )
        
        changer_onglet_vers_liste(None)

    btn_creer = ft.ElevatedButton(
        content=ft.Text("Créer l'Objectif ⚔️", color="#00FFFF", weight=ft.FontWeight.BOLD),
        bgcolor="#1A1A2E",
        on_click=ajouter_nouvelle_quete
    )

    # --- 5. LOGIQUE DE VALIDATION RAPIDE DE SPORT ---
    txt_sport_run = ft.TextField(label="Course à pied (km)", value="0", border_color="#4B0082", keyboard_type=ft.KeyboardType.NUMBER)
    txt_sport_bike = ft.TextField(label="Vélo (km)", value="0", border_color="#4B0082", keyboard_type=ft.KeyboardType.NUMBER)
    lbl_sport_status = ft.Text("", size=13, color="#00FF88", italic=True)

    def valider_sport(e):
        global donnees
        try:
            km_run = float(txt_sport_run.value) if txt_sport_run.value else 0.0
            km_bike = float(txt_sport_bike.value) if txt_sport_bike.value else 0.0
            xp_gagne = (km_run * 1.0) + (km_bike * 0.25)
            
            if xp_gagne > 0:
                donnees["xp_actuel"] += xp_gagne
                verifier_level_up()
                sauvegarder_donnees_globales(donnees)
                
                lbl_sport_status.value = f"💪 Effort validé ! +{round(xp_gagne, 2)} XP."
                lbl_sport_status.color = "#00FF88"
                txt_sport_run.value = "0"
                txt_sport_bike.value = "0"
                rafraichir_header_xp()
            else:
                lbl_sport_status.value = "Entrez une distance supérieure à 0."
                lbl_sport_status.color = "#FF4C4C"
        except ValueError:
            lbl_sport_status.value = "Saisie incorrecte."
            lbl_sport_status.color = "#FF4C4C"
        page.update()

    colonne_sport = ft.Column([
        ft.Text("QUÊTES ACTIVES : SPORT", size=16, color="#00FFFF", weight=ft.FontWeight.BOLD),
        ft.Text("Ratios : 1 km Course = 1 XP | 4 km Vélo = 1 XP", size=12, color="#A9A9A9", italic=True),
        txt_sport_run,
        txt_sport_bike,
        ft.ElevatedButton(content=ft.Text("Valider l'effort ⚡", color="#00FFFF", weight=ft.FontWeight.BOLD), bgcolor="#1A1A2E", on_click=valider_sport),
        lbl_sport_status
    ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=450, scroll=ft.ScrollMode.AUTO)

    # --- 6. GESTION DES ACTIONS SUR LES QUÊTES ---
    def valider_quete(e, quete):
        global donnees
        aujourdhui = datetime.now()
        date_str = aujourdhui.strftime("%Y-%m-%d")
        semaine_actuelle = aujourdhui.isocalendar()[1]

        if quete.get("derniere_semaine_annee", 0) != semaine_actuelle:
            quete["validations_semaine"] = 0
            if quete.get("nouveau_km_cible") is not None:
                quete["km_cible"] = quete["nouveau_km_cible"]
                quete["base_xp"] = quete["nouveau_base_xp"]
                quete["nouveau_km_cible"] = None
                quete["nouveau_base_xp"] = None
            quete["derniere_semaine_annee"] = semaine_actuelle

        if quete.get("derniere_validation", "") == date_str:
            return

        futur_streak = quete.get("streak", 0) + 1
        xp_gagne = calculer_xp_multi_plateaux(quete, futur_streak)

        quete["streak"] = futur_streak
        quete["derniere_validation"] = date_str
        quete["validations_semaine"] = quete.get("validations_semaine", 0) + 1
        
        donnees["xp_actuel"] += xp_gagne
        verifier_level_up()
        sauvegarder_donnees_globales(donnees)
        rafraichir_header_xp()
        rafraichir_liste_quetes()

    def devalider_quete(e, quete):
        global donnees
        if quete.get("streak", 0) <= 0:
            return

        xp_a_retirer = calculer_xp_multi_plateaux(quete, quete["streak"])
        quete["streak"] -= 1
        quete["derniere_validation"] = "" 
        if quete.get("validations_semaine", 0) > 0:
            quete["validations_semaine"] -= 1

        donnees["xp_actuel"] -= xp_a_retirer
        while donnees["xp_actuel"] < 0:
            if donnees["niveau"] > 1:
                donnees["niveau"] -= 1
                donnees["xp_actuel"] += xp_necessaire_pour_niveau(donnees["niveau"])
            else:
                donnees["xp_actuel"] = 0
                break

        sauvegarder_donnees_globales(donnees)
        rafraichir_header_xp()
        rafraichir_liste_quetes()

    # --- NOVEDADE : POPUP DE MODIFICATION DE L'OBJECTIF HEBDO POUR LA SEMAINE PROCHAINE ---
    def proposer_changement_objectif(quete):
        txt_nouveau_km = ft.TextField(label="Nouveau quota (km)", value=str(quete.get("km_cible", 30.0)), keyboard_type=ft.KeyboardType.NUMBER)
        txt_nouvel_xp = ft.TextField(label="Nouvel XP Bonus", value=str(quete.get("base_xp", 50.0)), keyboard_type=ft.KeyboardType.NUMBER)

        def enregistrer_changement(ev):
            try:
                nouveau_km = float(txt_nouveau_km.value.replace(",", "."))
                nouvel_xp = float(txt_nouvel_xp.value.replace(",", "."))
                if nouveau_km > 0 and nouvel_xp >= 0:
                    quete["nouveau_km_cible"] = nouveau_km
                    quete["nouveau_base_xp"] = nouvel_xp
                    sauvegarder_donnees_globales(donnees)
                    page.overlay.append(ft.SnackBar(ft.Text("⏳ Évolution programmée pour la semaine prochaine !"), bgcolor="#00FF88"))
                    page.overlay[-1].open = True
            except ValueError:
                pass
            dialog_evo.open = False
            page.update()

        dialog_evo = ft.AlertDialog(
            title=ft.Text("Évolution de l'objectif 📈"),
            content=ft.Column([
                ft.Text("Félicitations pour avoir validé ta quête ! Veux-tu ajuster la difficulté pour la semaine prochaine ?", size=13),
                txt_nouveau_km,
                txt_nouvel_xp
            ], spacing=10, height=180),
            actions=[
                ft.TextButton("Garder le même", on_click=lambda _: setattr(dialog_evo, "open", False) or page.update()),
                ft.TextButton("Planifier", on_click=enregistrer_changement)
            ]
        )
        page.overlay.append(dialog_evo)
        dialog_evo.open = True
        page.update()

    def ajouter_km_objectif_hebdo(e, quete):
        txt_ajout = ft.TextField(label="Distance effectuée (km)", keyboard_type=ft.KeyboardType.NUMBER)
        
        def confirmer_ajout(ev):
            global donnees
            try:
                val = float(txt_ajout.value.replace(",", "."))
                if val > 0:
                    ancien_km = quete.get("km_actuel", 0.0)
                    km_c = quete.get("km_cible", 30.0)
                    quete["km_actuel"] = min(ancien_km + val, km_c)
                    
                    ratio = 1.0 if quete.get("sport") == "Course à pied" else 0.25
                    xp_gagne = val * ratio
                    
                    declencher_choix_evolution = False
                    if quete["km_actuel"] >= km_c and ancien_km < km_c:
                        futur_streak = quete.get("streak", 0) + 1
                        quete["streak"] = futur_streak
                        xp_bonus = calculer_xp_multi_plateaux(quete, futur_streak)
                        xp_gagne += xp_bonus
                        declencher_choix_evolution = True
                        
                        page.overlay.append(ft.SnackBar(ft.Text(f"🎯 QUÊTE HEBDO RÉUSSIE ! Série : {futur_streak} sem."), bgcolor="#FF8C00"))
                        page.overlay[-1].open = True
                    
                    donnees["xp_actuel"] += xp_gagne
                    verifier_level_up()
                    sauvegarder_donnees_globales(donnees)
                    rafraichir_header_xp()
                    rafraichir_liste_quetes()
                    
                    if declencher_choix_evolution:
                        proposer_changement_objectif(quete)
            except ValueError:
                pass
            dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Enregistrer une sortie"),
            content=txt_ajout,
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: setattr(dialog, "open", False)),
                ft.TextButton("Ajouter", on_click=confirmer_ajout)
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def supprimer_quete(e, quete):
        def confirmer_suppression(ev):
            global donnees
            donnees["quetes"].remove(quete)
            sauvegarder_donnees_globales(donnees)
            dialog_confirm.open = False
            rafraichir_liste_quetes()
            page.update()

        dialog_confirm = ft.AlertDialog(
            title=ft.Text("Abandonner l'objectif ?"),
            content=ft.Text(f"Es-tu sûr de vouloir supprimer définitivement la quête : \n\"{quete.get('titre')}\" ?"),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: setattr(dialog_confirm, "open", False) or page.update()),
                ft.TextButton("Supprimer", icon=ft.Icons.DELETE_FOREVER, icon_color="#FF4C4C", on_click=confirmer_suppression)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        page.overlay.append(dialog_confirm)
        dialog_confirm.open = True
        page.update()

    def reorganiser_quetes(e):
        global donnees
        quete_deplacee = donnees["quetes"].pop(e.old_index)
        donnees["quetes"].insert(e.new_index, quete_deplacee)
        sauvegarder_donnees_globales(donnees)
        rafraichir_liste_quetes()

    # --- 7. AFFICHAGE DES QUÊTES ACTIVES ---
    liste_visuelle_quetes = ft.ReorderableListView(
        height=450, 
        spacing=10, 
        scroll=ft.ScrollMode.AUTO,
        on_reorder=reorganiser_quetes
    )

    def rafraichir_liste_quetes():
        global donnees
        liste_visuelle_quetes.controls = []
        
        aujourdhui = datetime.now()
        date_aujourdhui_str = aujourdhui.strftime("%Y-%m-%d")
        semaine_actuelle = aujourdhui.isocalendar()[1]
        
        sauvegarde_requise = False
        for q in donnees.get("quetes", []):
            if q.get("type") == "Classique" and q.get("derniere_validation"):
                try:
                    derniere_date = datetime.strptime(q["derniere_validation"], "%Y-%m-%d")
                    if (aujourdhui - derniere_date).days > 1:
                        q["streak"] = 0
                        sauvegarde_requise = True
                except ValueError:
                    pass
                    
        if sauvegarde_requise:
            sauvegarder_donnees_globales(donnees)

        if not donnees.get("quetes") or len(donnees["quetes"]) == 0:
            liste_visuelle_quetes.controls.append(ft.Text("Aucune quête active. Crée-en une !", color="#A9A9A9", italic=True, key="empty_list"))
            page.update()
            return

        nouveaux_controles = []
        titres_vus = set()

        for q in donnees["quetes"]:
            t_key = q.get("titre", "").lower().strip()
            if not t_key or t_key in titres_vus:
                continue
            titres_vus.add(t_key)

            cle_unique = f"key_{t_key}_{q.get('type')}"

            # GESTION DU CHANGEMENT DE SEMAINE ET INTÉGRATION DE LA MODIFICATION PLANIFIÉE
            if q.get("derniere_semaine_annee", 0) != semaine_actuelle:
                if q.get("type") == "ObjectifKmHebdo":
                    if q.get("km_actuel", 0.0) < q.get("km_cible", 30.0):
                        q["streak"] = 0
                    q["km_actuel"] = 0.0
                    
                    # Si une évolution avait été planifiée, on la valide maintenant
                    if q.get("nouveau_km_cible") is not None:
                        q["km_cible"] = q["nouveau_km_cible"]
                        q["base_xp"] = q["nouveau_base_xp"]
                        q["nouveau_km_cible"] = None
                        q["nouveau_base_xp"] = None
                else:
                    q["validations_semaine"] = 0
                q["derniere_semaine_annee"] = semaine_actuelle
                sauvegarder_donnees_globales(donnees)

            if q.get("type") == "ObjectifKmHebdo":
                km_a = q.get("km_actuel", 0.0)
                km_c = q.get("km_cible", 30.0)
                complete = (km_a >= km_c)
                progression = min(km_a / km_c, 1.0) if km_c > 0 else 0.0
                
                streak_actuel = q.get("streak", 0)
                xp_affichage_bonus = calculer_xp_multi_plateaux(q, streak_actuel + 1)
                
                barre_orange = ft.ProgressBar(value=progression, color="#FF8C00", bgcolor="#0B0C10", height=6, border_radius=3)
                icon_sport = "🏃‍♂️" if q.get("sport") == "Course à pied" else "🚴‍♂️"
                
                # Petit indicateur visuel si un changement est en attente
                txt_evo_attente = " ⏳" if q.get("nouveau_km_cible") is not None else ""
                sub_txt = f"{icon_sport} Hebdo : {round(km_a, 1)} / {km_c} km | +{xp_affichage_bonus} XP{txt_evo_attente}"

                nouveaux_controles.append(
                    ft.Container(
                        key=cle_unique,
                        content=ft.Column([
                            ft.Row([
                                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#FF4C4C", on_click=lambda e, quete=q: supprimer_quete(e, quete)),
                                ft.Column([ft.Text(q["titre"], color="#FFFFFF", weight=ft.FontWeight.BOLD), ft.Text(sub_txt, color="#A9A9A9", size=11)], expand=True),
                                ft.Container(content=ft.Text(f"🔥 {streak_actuel}", color="#FF8C00", weight=ft.FontWeight.BOLD, size=12), bgcolor="#0B0C10", padding=5, border_radius=5),
                                ft.ElevatedButton("Fini 🎉" if complete else "+ Km", disabled=complete, on_click=lambda e, quete=q: ajouter_km_objectif_hebdo(e, quete)),
                                ft.Icon(ft.Icons.DRAG_HANDLE, color="#4B0082", size=18)
                            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Container(content=barre_orange, padding=5)
                        ]), bgcolor="#1F2833", padding=12, border_radius=8
                    )
                )
            else:
                cible = q.get("jours_cible", 7)
                val_semaine = q.get("validations_semaine", 0)
                dern_val = q.get("derniere_validation", "")
                streak_actuel = q.get("streak", 0)
                
                xp_affichage = calculer_xp_multi_plateaux(q, streak_actuel + 1)

                deja_fait = (dern_val == date_aujourdhui_str)
                quota_atteint = (val_semaine >= cible and cible != 7)

                if deja_fait:
                    btn_texte, btn_fond, action = "Validé ✓", "#132A13", lambda e, quete=q: devalider_quete(e, quete)
                    bloque = False
                elif quota_atteint:
                    btn_texte, btn_fond, action = "Fini 🎉", "#222222", None
                    bloque = True
                else:
                    btn_texte, btn_fond, action = "Valider ⚔️", "#1A1A2E", lambda e, quete=q: valider_quete(e, quete)
                    bloque = False

                freq_txt = "Chaque jour" if cible == 7 else f"{cible}x/sem ({val_semaine}/{cible})"

                nouveaux_controles.append(
                    ft.Container(
                        key=cle_unique,
                        content=ft.Row([
                            ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#FF4C4C", on_click=lambda e, quete=q: supprimer_quete(e, quete)),
                            ft.Column([ft.Text(q["titre"], color="#FFFFFF", weight=ft.FontWeight.BOLD), ft.Text(f"⏱️ {freq_txt} | 💎 {xp_affichage} XP", color="#A9A9A9", size=11)], expand=True),
                            ft.Container(content=ft.Text(f"🔥 {streak_actuel}", color="#FF8C00", weight=ft.FontWeight.BOLD, size=12), bgcolor="#0B0C10", padding=5, border_radius=5),
                            ft.ElevatedButton(btn_texte, bgcolor=btn_fond, disabled=bloque, on_click=action),
                            ft.Icon(ft.Icons.DRAG_HANDLE, color="#4B0082", size=18)
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER), bgcolor="#1F2833", padding=12, border_radius=8
                    )
                )
        
        liste_visuelle_quetes.controls = nouveaux_controles
        page.update()

    # --- 8. LAYOUT & NAVIGATION ---
    colonne_formulaire = ft.Column([
        ft.Text("CRÉATEUR DE SYSTÈME", size=16, color="#00FFFF", weight=ft.FontWeight.BOLD),
        selecteur_onglets_custom,
        txt_titre,
        container_form_habitude,
        container_form_km,
        ft.Divider(color="#1F2833"),
        btn_creer
    ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=450, scroll=ft.ScrollMode.AUTO)

    zone_dynamique = ft.Container(content=liste_visuelle_quetes)

    def changer_onglet_vers_liste(e):
        btn_onglet_liste.bgcolor = "#1A1A2E"
        btn_onglet_creer.bgcolor = "#0B0C10"
        btn_onglet_sport.bgcolor = "#0B0C10"
        zone_dynamique.content = liste_visuelle_quetes
        rafraichir_liste_quetes()

    def changer_onglet_vers_creer(e):
        btn_onglet_liste.bgcolor = "#0B0C10"
        btn_onglet_creer.bgcolor = "#1A1A2E"
        btn_onglet_sport.bgcolor = "#0B0C10"
        zone_dynamique.content = colonne_formulaire
        page.update()

    def changer_onglet_vers_sport(e):
        btn_onglet_liste.bgcolor = "#0B0C10"
        btn_onglet_creer.bgcolor = "#0B0C10"
        btn_onglet_sport.bgcolor = "#1A1A2E"
        zone_dynamique.content = colonne_sport
        lbl_sport_status.value = ""
        page.update()

    btn_onglet_liste = ft.ElevatedButton(content=ft.Row([ft.Icon(ft.Icons.LIST_ALT, color="#00FFFF", size=16), ft.Text("Quêtes", color="#FFFFFF", size=11)], spacing=4), bgcolor="#1A1A2E", on_click=changer_onglet_vers_liste, expand=True)
    btn_onglet_creer = ft.ElevatedButton(content=ft.Row([ft.Icon(ft.Icons.ADD_BOX, color="#00FFFF", size=16), ft.Text("Créer", color="#FFFFFF", size=11)], spacing=4), bgcolor="#0B0C10", on_click=changer_onglet_vers_creer, expand=True)
    btn_onglet_sport = ft.ElevatedButton(content=ft.Row([ft.Icon(ft.Icons.DIRECTIONS_RUN, color="#00FFFF", size=16), ft.Text("Sport", color="#FFFFFF", size=11)], spacing=4), bgcolor="#0B0C10", on_click=changer_onglet_vers_sport, expand=True)
    barre_onglets = ft.Row(controls=[btn_onglet_liste, btn_onglet_creer, btn_onglet_sport], alignment=ft.MainAxisAlignment.SPACE_EVENLY)

    header_profil = ft.Container(
        content=ft.Column([ft.Row([lbl_niveau, lbl_xp_texte], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), barre_xp], spacing=5),
        padding=12, bgcolor="#1A1A2E", border_radius=10, border=ft.Border.all(width=1, color="#4B0082")
    )

    espace_encoche = ft.Container(height=30, bgcolor=ft.Colors.TRANSPARENT)

    page.add(
        ft.Column([
            espace_encoche,
            header_profil,
            ft.Divider(color="#1F2833", thickness=1),
            barre_onglets,
            zone_dynamique
        ])
    )
    
    rafraichir_header_xp()
    rafraichir_liste_quetes()

if __name__ == "__main__":
    ft.run(main)
