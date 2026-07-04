import flet as ft
import json
import os
import math
from datetime import datetime

FICHIER_SAUVEGARDE = "data_solo_leveling.json"

def main(page: ft.Page):
    page.title = "Les quêtes là"
    page.bgcolor = "#0B0C10"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # Configuration stricte de la fenêtre (Garantit le Scroll)
    page.window.width = 450       
    page.window.height = 750      
    page.window.resizable = False  

    # --- 1. CHARGEMENT / SAUVEGARDE ---
    def charger_donnees():
        default_data = {"niveau": 1, "xp_actuel": 0, "quetes": []}
        if os.path.exists(FICHIER_SAUVEGARDE):
            try:
                with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "niveau" not in data: data["niveau"] = 1
                    if "xp_actuel" not in data: data["xp_actuel"] = 0
                    if "quetes" not in data: data["quetes"] = []
                    return data
            except Exception:
                pass
        return default_data

    def sauvegarder_donnees():
        with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
            json.dump(donnees, f, indent=4, ensure_ascii=False)

    donnees = charger_donnees()

    # --- 2. LOGIQUE DE CALCUL DE L'XP DYNAMIQUE ---
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
        paliers = quete.get("paliers", [[1,1], [10, 1.05], [25, 1.01], [999, 1.005]])
        
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

        return math.ceil(xp_calculee)

    def parser_paliers_texte(texte):
        paliers = []
        if not text.strip():
            return [[1, 1], [10, 1.05], [25, 1.01], [999, 1.005]]
        try:
            blocs = texte.split(",")
            for b in blocs:
                if ":" in b:
                    limite, facteur = b.split(":")
                    paliers.append([int(limite.strip()), float(facteur.strip())])
            return paliers if paliers else [[1,1], [10, 1.05], [25, 1.01], [999, 1.005]]
        except Exception:
            return [[1,1], [10, 1.05], [25, 1.01], [999, 1.005]]

    # --- 3. COMPOSANTS VISUELS DU HEADER ---
    lbl_niveau = ft.Text(f"NIVEAU {donnees['niveau']}", size=20, color="#00FFFF", weight=ft.FontWeight.BOLD)
    lbl_xp_texte = ft.Text("", size=11, color="#A9A9A9")
    
    barre_xp = ft.ProgressBar(
        value=0.0,
        color="#00FFFF",
        bgcolor="#1F2833",
        height=10,
        border_radius=5
    )

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

    # --- 4. LOGIQUE DE CRÉATION DE QUÊTE ---
    txt_titre = ft.TextField(label="Nom de la quête", border_color="#4B0082", focused_border_color="#00FFFF")
    
    dropdown_jours_cible = ft.Dropdown(
        label="Fréquence",
        border_color="#4B0082",
        options=[
            ft.dropdown.Option("1", "Hebdomadaire"),
            ft.dropdown.Option("2", "2/semaine"),
            ft.dropdown.Option("3", "3/semaine"),
            ft.dropdown.Option("4", "4/semaine"),
            ft.dropdown.Option("5", "5/semaine"),
            ft.dropdown.Option("6", "6/semaine"),
            ft.dropdown.Option("7", "Quotidienne"),
        ],
        value="7"
    )

    txt_xp = ft.TextField(label="XP de base", value="", border_color="#4B0082", keyboard_type=ft.KeyboardType.NUMBER)
    text_paliers = ft.TextField(label="Facteur de croissance", value="1:1, 10:1.05, 25:1.01, 999:1.005", border_color="#4B0082", focused_border_color="#00FFFF")
    lbl_explication_paliers = ft.Text("Exemple: 10:1.05, 25:1.01 -> jusqu'au J10 x1.05, puis jusqu'au J25 x1.01, etc.", size=11, color="#A9A9A9", italic=True)

    def ajouter_nouvelle_quete(e):
        if not txt_titre.value.strip():
            return
        
        liste_paliers = parser_paliers_texte(text_paliers.value)

        nouvelle_q = {
            "titre": txt_titre.value.strip(),
            "jours_cible": int(dropdown_jours_cible.value),
            "base_xp": int(txt_xp.value) if txt_xp.value.isdigit() else 10,
            "paliers": liste_paliers,
            "streak": 0,
            "derniere_validation": "", 
            "validations_semaine": 0,  
            "derniere_semaine_annee": 0 
        }
        
        donnees["quetes"].append(nouvelle_q)
        sauvegarder_donnees()
        
        txt_titre.value = ""
        dropdown_jours_cible.value = "7"
        txt_xp.value = "10"
        text_paliers.value = "1:1, 10:1.05, 25:1.01, 999:1.005"
        page.update() 
        
        changer_onglet_vers_liste(None)

    btn_creer = ft.ElevatedButton(
        content=ft.Text("Créer la Quête ⚔️", color="#00FFFF", weight=ft.FontWeight.BOLD),
        bgcolor="#1A1A2E",
        on_click=ajouter_nouvelle_quete
    )

    # --- 5. LOGIQUE DE VALIDATION / DÉVALIDATION ---
    def verifier_level_up():
        while donnees["xp_actuel"] >= xp_necessaire_pour_niveau(donnees["niveau"]):
            donnees["xp_actuel"] -= xp_necessaire_pour_niveau(donnees["niveau"])
            donnees["niveau"] += 1
            
            page.overlay.append(ft.SnackBar(ft.Text(f"LEVEL UP ! Niveau {donnees['niveau']} ! ⚡"), bgcolor="#4B0082"))
            page.overlay[-1].open = True

    def valider_quete(e, quete):
        aujourdhui = datetime.now()
        date_str = aujourdhui.strftime("%Y-%m-%d")
        semaine_actuelle = aujourdhui.isocalendar()[1]

        if quete.get("derniere_semaine_annee", 0) != semaine_actuelle:
            quete["validations_semaine"] = 0
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

        sauvegarder_donnees()
        rafraichir_header_xp()
        rafraichir_liste_quetes()

    def devalider_quete(e, quete):
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

        sauvegarder_donnees()
        rafraichir_header_xp()
        rafraichir_liste_quetes()

    def supprimer_quete(e, quete):
        donnees["quetes"].remove(quete)
        sauvegarder_donnees()
        rafraichir_liste_quetes()

    # --- 6. FEATURE SPORT (COURSE / VÉLO) ---
    txt_sport_run = ft.TextField(label="Course à pied (km)", value="0", border_color="#4B0082", keyboard_type=ft.KeyboardType.NUMBER)
    txt_sport_bike = ft.TextField(label="Vélo (km)", value="0", border_color="#4B0082", keyboard_type=ft.KeyboardType.NUMBER)
    lbl_sport_status = ft.Text("", size=13, color="#00FF88", italic=True)

    def valider_sport(e):
        try:
            km_run = float(txt_sport_run.value) if txt_sport_run.value else 0.0
            km_bike = float(txt_sport_bike.value) if txt_sport_bike.value else 0.0
            
            # Calcul : 1 XP par km de course | 1 XP tous les 4 km de vélo (donc 0.25 XP / km)
            xp_gagne = (km_run * 1.0) + (km_bike * 0.25)
            
            if xp_gagne > 0:
                donnees["xp_actuel"] += xp_gagne
                verifier_level_up()
                sauvegarder_donnees()
                
                lbl_sport_status.value = f"💪 Entraînement validé ! +{round(xp_gagne, 2)} XP enregistré."
                lbl_sport_status.color = "#00FF88"
                
                # Réinitialisation
                txt_sport_run.value = "0"
                txt_sport_bike.value = "0"
                rafraichir_header_xp()
            else:
                lbl_sport_status.value = "Veuillez entrer une distance valide supérieure à 0."
                lbl_sport_status.color = "#FF4C4C"
        except ValueError:
            lbl_sport_status.value = "Erreur : Saisie incorrecte (Entrez des nombres)."
            lbl_sport_status.color = "#FF4C4C"
        
        page.update()

    colonne_sport = ft.Column([
        ft.Text("QUÊTES ACTIVES : SPORT", size=16, color="#00FFFF", weight=ft.FontWeight.BOLD),
        ft.Text("Ratios : 1 km Course = 1 XP | 4 km Vélo = 1 XP", size=12, color="#A9A9A9", italic=True),
        txt_sport_run,
        txt_sport_bike,
        ft.ElevatedButton(
            content=ft.Text("Valider l'effort ⚡", color="#00FFFF", weight=ft.FontWeight.BOLD),
            bgcolor="#1A1A2E",
            on_click=valider_sport
        ),
        lbl_sport_status
    ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=450, scroll=ft.ScrollMode.AUTO)

    # --- 7. AFFICHAGE DES QUÊTES ---
    liste_visuelle_quetes = ft.ListView(height=450, spacing=10, scroll=ft.ScrollMode.AUTO)

    def rafraichir_liste_quetes():
        liste_visuelle_quetes.controls.clear()
        
        if not donnees["quetes"]:
            liste_visuelle_quetes.controls.append(
                ft.Text("Aucune quête active. Crée-en une !", color="#A9A9A9", italic=True)
            )
            page.update()
            return

        aujourdhui = datetime.now()
        date_str = aujourdhui.strftime("%Y-%m-%d")
        semaine_actuelle = aujourdhui.isocalendar()[1]

        for q in donnees["quetes"]:
            cible = q["jours_cible"]
            
            if q.get("derniere_semaine_annee", 0) != semaine_actuelle:
                q["validations_semaine"] = 0
                q["derniere_semaine_annee"] = semaine_actuelle

            val_semaine = q.get("validations_semaine", 0)
            dern_val = q.get("derniere_validation", "")
            streak_actuel = q.get("streak", 0)

            xp_affichage = calculer_xp_multi_plateaux(q, streak_actuel + 1 if dern_val != date_str else streak_actuel)

            deja_fait_aujourdhui = (dern_val == date_str)
            quota_atteint = (val_semaine >= cible and cible != 7)

            if deja_fait_aujourdhui:
                btn_texte = "Validé ✓"
                btn_couleur_texte = "#00FF88"  
                btn_fond = "#132A13"          
                action_bouton = lambda e, quete=q: devalider_quete(e, quete)
                bouton_bloque = False
            elif quota_atteint:
                btn_texte = "Fini 🎉"
                btn_couleur_texte = "#666666"
                btn_fond = "#222222"
                action_bouton = None
                bouton_bloque = True
            else:
                btn_texte = "Valider ⚔️"
                btn_couleur_texte = "#00FFFF"
                btn_fond = "#1A1A2E"
                action_bouton = lambda e, quete=q: valider_quete(e, quete)
                bouton_bloque = False

            freq_txt = "Chaque jour" if cible == 7 else f"{cible}x/sem ({val_semaine}/{cible})"

            btn_action = ft.ElevatedButton(
                content=ft.Text(btn_texte, color=btn_couleur_texte, size=12, weight=ft.FontWeight.BOLD),
                bgcolor=btn_fond,
                disabled=bouton_bloque,
                on_click=action_bouton
            )

            btn_supprimer = ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE,
                icon_color="#FF4C4C",
                icon_size=20,
                on_click=lambda e, quete=q: supprimer_quete(e, quete)
            )

            liste_visuelle_quetes.controls.append(
                ft.Container(
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column([
                                ft.Text(q["titre"], color="#FFFFFF", weight=ft.FontWeight.BOLD, size=14, max_lines=1),
                                ft.Text(f"⏱️ {freq_txt} | 💎 {xp_affichage} XP", color="#A9A9A9", size=11),
                            ], spacing=3, expand=True),
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(f"🔥 {streak_actuel}", color="#FF8C00", weight=ft.FontWeight.BOLD, size=12),
                                    bgcolor="#0B0C10", padding=5, border_radius=5
                                ),
                                btn_action,
                                btn_supprimer
                            ], spacing=3)
                        ]
                    ),
                    bgcolor="#1F2833",
                    padding=10,
                    border_radius=8
                )
            )
        page.update()

    # --- 8. NAVIGATION ET LAYOUT ---
    colonne_formulaire = ft.Column([
        ft.Text("CRÉATEUR DE QUÊTES", size=16, color="#00FFFF", weight=ft.FontWeight.BOLD),
        txt_titre,
        dropdown_jours_cible,
        txt_xp,
        text_paliers,
        lbl_explication_paliers,
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

    btn_onglet_liste = ft.ElevatedButton(
        content=ft.Row([ft.Icon(ft.Icons.LIST_ALT, color="#00FFFF", size=16), ft.Text("Quêtes", color="#FFFFFF", size=11)], spacing=4),
        bgcolor="#1A1A2E",
        on_click=changer_onglet_vers_liste,
        expand=True
    )

    btn_onglet_creer = ft.ElevatedButton(
        content=ft.Row([ft.Icon(ft.Icons.ADD_BOX, color="#00FFFF", size=16), ft.Text("Créer", color="#FFFFFF", size=11)], spacing=4),
        bgcolor="#0B0C10",
        on_click=changer_onglet_vers_creer,
        expand=True
    )

    btn_onglet_sport = ft.ElevatedButton(
        content=ft.Row([ft.Icon(ft.Icons.DIRECTIONS_RUN, color="#00FFFF", size=16), ft.Text("Sport", color="#FFFFFF", size=11)], spacing=4),
        bgcolor="#0B0C10",
        on_click=changer_onglet_vers_sport,
        expand=True
    )

    barre_onglets = ft.Row(controls=[btn_onglet_liste, btn_onglet_creer, btn_onglet_sport], alignment=ft.MainAxisAlignment.SPACE_EVENLY)

    header_profil = ft.Container(
        content=ft.Column([
            ft.Row([lbl_niveau, lbl_xp_texte], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            barre_xp
        ], spacing=5),
        padding=12,
        bgcolor="#1A1A2E",
        border_radius=10,
        border=ft.Border.all(width=1, color="#4B0082")
    )

    rafraichir_header_xp()
    rafraichir_liste_quetes()

    page.add(
        ft.Column([
            header_profil,
            ft.Divider(color="#1F2833", thickness=1),
            barre_onglets,
            zone_dynamique
        ])
    )

if __name__ == "__main__":
    ft.run(main)
