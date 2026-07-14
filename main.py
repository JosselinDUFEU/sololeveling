import flet as ft
import json
import os
import math
from datetime import datetime

FICHIER_SAUVEGARDE = "data_solo_leveling.json"

# --- 1. INITIALISATION GLOBALE DES DONNÉES ---
def charger_donnees():
    default_data = {"niveau": 1, "xp_actuel": 0, "quetes": [], "total_quetes_realisees": 0}
    if os.path.exists(FICHIER_SAUVEGARDE):
        try:
            with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict): return default_data
                if "niveau" not in data: data["niveau"] = 1
                if "xp_actuel" not in data: data["xp_actuel"] = 0
                if "quetes" not in data: data["quetes"] = []
                if "total_quetes_realisees" not in data: data["total_quetes_realisees"] = 0
                
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
    page.padding = 20  #espace de 20 pixels entre les boutons et le bords de l'écran

    page.window.width = 450       
    page.window.height = 880      
    page.window.resizable = False  
    
    page.index_creation_actif = 0
    page.mode_epure = True

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
        base_xp = float(quete.get("base_xp", 10))
        paliers = quete.get("paliers", [[1, 1], [10, 1.05], [25, 1.01], [999, 1.005]])
        paliers_tries = sorted(paliers, key=lambda x: x[0])
        
        # Initialisation : le premier jour, la "veille" est la base_xp
        xp_veille = base_xp
        
        # On boucle jour après jour
        for jour in range(1, streak_cible + 1):
            # 1. Déterminer le facteur du jour
            facteur_du_jour = 1.0
            for limite, facteur in paliers_tries:
                if jour <= limite:
                    facteur_du_jour = facteur
                    break
            else:
                facteur_du_jour = paliers_tries[-1][1]
            
            # 2. Calcul avec la variable explicite
            xp_du_jour = xp_veille * facteur_du_jour
            
            # 3. La xp_du_jour devient la xp_veille pour le tour suivant
            xp_veille = xp_du_jour
            
        return round(xp_veille, 1)

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
    lbl_niveau = ft.Text(f"NIVEAU {donnees['niveau']}", size=20, color="#FFBF00", weight=ft.FontWeight.BOLD)
    lbl_xp_texte = ft.Text("", size=11, color="#A9A9A9")
    barre_xp = ft.ProgressBar(value=0.0, color="#FFBF00", bgcolor="#1F2833", height=10, border_radius=5)

    def rafraichir_header_xp():
        niv = donnees["niveau"]
        xp_actuel = donnees["xp_actuel"]
        xp_max = xp_necessaire_pour_niveau(niv)
        barre_xp.value = min(xp_actuel / xp_max, 1.0)
        
        if niv <= 5: titre_rang = ""
        elif niv <= 10: titre_rang = ""
        elif niv <= 15: titre_rang = ""
        elif niv <= 20: titre_rang = ""
        elif niv <= 25: titre_rang = ""
        else: titre_rang = ""
            
        lbl_niveau.value = f"{titre_rang} NIVEAU {niv}"
        lbl_xp_texte.value = f"{round(xp_actuel, 1)} / {xp_max} XP"
        page.update()

    def verifier_level_up():
        while donnees["xp_actuel"] >= xp_necessaire_pour_niveau(donnees["niveau"]):
            donnees["xp_actuel"] -= xp_necessaire_pour_niveau(donnees["niveau"])
            donnees["niveau"] += 1
            page.overlay.append(ft.SnackBar(ft.Text(f"Whouhou ! Niveau {donnees['niveau']} !"), bgcolor="#FFBF00"))
            page.overlay[-1].open = True

    # --- 4. FORMULAIRE DE CRÉATION FIXE ---
    txt_titre = ft.TextField(label="Le nom", border_color="#FFBF00", focused_border_color="#009DFF")

    dropdown_frequence_classique = ft.Dropdown(
        label="Fréquence", border_color="#FFBF00",
        options=[ft.dropdown.Option(str(i), "Quotidienne" if i==7 else f"{i}/semaine") for i in range(1, 8)],
        value="7"
    )
    txt_xp_classique = ft.TextField(label="XP de base", value="10", border_color="#FFBF00", keyboard_type=ft.KeyboardType.NUMBER)
    text_paliers_hab = ft.TextField(label="Facteur de croissance", value="1:1, 10:1.05, 25:1.01, 999:1.005", border_color="#FFBF00")

    container_form_habitude = ft.Column([
        dropdown_frequence_classique,
        txt_xp_classique,
        text_paliers_hab,
        ft.Text("", size=11, color="#A9A9A9", italic=True)
    ], spacing=10)

    dropdown_sport_km = ft.Dropdown(
        label="CAP ou Vélo ?", border_color="#FFBF00",
        options=[
            ft.dropdown.Option("Course à pied", "Course à pied"),
            ft.dropdown.Option("Vélo", "Vélo")
        ],
        value="Course à pied"
    )
    txt_km_hebdo_cible = ft.TextField(label="Km/semaine", value="60", border_color="#FFBF00", keyboard_type=ft.KeyboardType.NUMBER)
    txt_xp_bonus_km = ft.TextField(label="XP Bonus", value="10", border_color="#FFBF00", keyboard_type=ft.KeyboardType.NUMBER)
    text_paliers_km = ft.TextField(label="Facteur de croissance", value="1:1, 10:1.05, 25:1.01, 999:1.005", border_color="#FFBF00")

    container_form_km = ft.Column([
        dropdown_sport_km,
        txt_km_hebdo_cible,
        txt_xp_bonus_km,
        text_paliers_km,
        ft.Text("", size=11, color="#A9A9A9", italic=True)
    ], spacing=10, visible=False)

    def switch_to_habitude(e):
        page.index_creation_actif = 0
        txt_tab_hab.value = "● Habitudes"
        txt_tab_hab.color = "#FFBF00"
        txt_tab_km.value = "Les Km/semaines"
        txt_tab_km.color = "#A9A9A9"
        container_form_habitude.visible = True
        container_form_km.visible = False
        page.update()

    def switch_to_km(e):
        page.index_creation_actif = 1
        txt_tab_hab.value = "Habitudes"
        txt_tab_hab.color = "#A9A9A9"
        txt_tab_km.value = "● Les Km/semaines"
        txt_tab_km.color = "#FFBF00"
        container_form_habitude.visible = False
        container_form_km.visible = True
        page.update()

    txt_tab_hab = ft.Text("● Habitudes", color="#FFBF00", size=14, weight=ft.FontWeight.BOLD)
    txt_tab_km = ft.Text("● Les Km/semaines", color="#FFBF00", size=14, weight=ft.FontWeight.BOLD)

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
                target_km = 60.0
                
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
        txt_km_hebdo_cible.value = "60"
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
        content=ft.Text("Créer la quête ⚔️", color="#FFBF00", weight=ft.FontWeight.BOLD),
        bgcolor="#1A1A2E",
        on_click=ajouter_nouvelle_quete
    )

    # --- 5. GESTION DES ACTIONS SUR LES QUÊTES ---
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
        donnees["total_quetes_realisees"] = donnees.get("total_quetes_realisees", 0) + 1
        
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
        if donnees.get("total_quetes_realisees", 0) > 0:
            donnees["total_quetes_realisees"] -= 1
            
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

    def proposer_changement_objectif(quete):
        txt_nouveau_km = ft.TextField(label="Nouvel objectif", value=str(quete.get("km_cible", 60.0)), keyboard_type=ft.KeyboardType.NUMBER)
        txt_nouvel_xp = ft.TextField(label="Nouvel XP Bonus", value=str(quete.get("base_xp", 10.0)), keyboard_type=ft.KeyboardType.NUMBER)

        def enregistrer_changement(ev):
            try:
                nouveau_km = float(txt_nouveau_km.value.replace(",", "."))
                nouvel_xp = float(txt_nouvel_xp.value.replace(",", "."))
                if nouveau_km > 0 and nouvel_xp >= 0:
                    quete["nouveau_km_cible"] = nouveau_km
                    quete["nouveau_base_xp"] = nouvel_xp
                    sauvegarder_donnees_globales(donnees)
                    page.overlay.append(ft.SnackBar(ft.Text("⏳ En route mauvaise troupe !"), bgcolor="#FFBF00"))
                    page.overlay[-1].open = True
            except ValueError:
                pass
            dialog_evo.open = False
            page.update()

        dialog_evo = ft.AlertDialog(
            title=ft.Text("Évolution de l'objectif 📈"),
            content=ft.Column([
                ft.Text("On augmente ?", size=13),
                txt_nouveau_km,
                txt_nouvel_xp
            ], spacing=10, height=180),
            actions=[
                ft.TextButton("Je suis une salope et je garde le même", on_click=lambda _: setattr(dialog_evo, "open", False) or page.update()),
                ft.TextButton("On fait ça", on_click=enregistrer_changement)
            ]
        )
        page.overlay.append(dialog_evo)
        dialog_evo.open = True
        page.update()

    def ajouter_km_objectif_hebdo(e, quete):
        txt_ajout = ft.TextField(label="Tout ça en plus ?!", keyboard_type=ft.KeyboardType.NUMBER)
        
        def confirmer_ajout(ev):
            global donnees
            try:
                val = float(txt_ajout.value.replace(",", "."))
                if val > 0:
                    ancien_km = quete.get("km_actuel", 0.0)
                    km_c = quete.get("km_cible", 30.0)
                    
                    quete["km_actuel"] = ancien_km + val
                    ratio = 1.0 if quete.get("sport") == "Course à pied" else 0.25
                    xp_gagne = val * ratio
                    
                    donnees["total_quetes_realisees"] = donnees.get("total_quetes_realisees", 0) + 1
                    declencher_choix_evolution = False
                    
                    if quete["km_actuel"] >= km_c and ancien_km < km_c:
                        futur_streak = quete.get("streak", 0) + 1
                        quete["streak"] = futur_streak
                        xp_bonus = calculer_xp_multi_plateaux(quete, futur_streak)
                        xp_gagne += xp_bonus
                        
                        page.overlay.append(ft.SnackBar(ft.Text(f"🎯 QUÊTE HEBDO RÉUSSIE ! Série : {futur_streak} sem."), bgcolor="#FF8C00"))
                        page.overlay[-1].open = True
                    
                    if quete["km_actuel"] >= km_c:
                        declencher_choix_evolution = True
                    
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

    def modifier_quete(e, quete):
        txt_edit_titre = ft.TextField(label="Nom de la quête", value=quete.get("titre", ""), border_color="#FFBF00")
        elements_formulaire = [txt_edit_titre]
        
        if quete.get("type") == "ObjectifKmHebdo":
            txt_edit_km = ft.TextField(label="Quota hebdomadaire", value=str(quete.get("km_cible", 60.0)), keyboard_type=ft.KeyboardType.NUMBER, border_color="#FFBF00")
            txt_edit_xp = ft.TextField(label="XP Bonus de fin", value=str(quete.get("base_xp", 10.0)), keyboard_type=ft.KeyboardType.NUMBER, border_color="#FFBF00")
            elements_formulaire.extend([txt_edit_km, txt_edit_xp])
        else:
            dropdown_edit_freq = ft.Dropdown(
                label="Fréquence", border_color="#FFBF00",
                options=[ft.dropdown.Option(str(i), "Quotidienne" if i==7 else f"{i}/semaine") for i in range(1, 8)],
                value=str(quete.get("jours_cible", 7))
            )
            txt_edit_xp = ft.TextField(label="XP de base", value=str(quete.get("base_xp", 10.0)), keyboard_type=ft.KeyboardType.NUMBER, border_color="#FFBF00")
            elements_formulaire.extend([dropdown_edit_freq, txt_edit_xp])

        def enregistrer_modification(ev):
            if not txt_edit_titre.value or not txt_edit_titre.value.strip():
                return
            quete["titre"] = txt_edit_titre.value.strip()
            try:
                if quete.get("type") == "ObjectifKmHebdo":
                    quete["km_cible"] = float(txt_edit_km.value.replace(",", "."))
                    quete["base_xp"] = float(txt_edit_xp.value.replace(",", "."))
                else:
                    quete["jours_cible"] = int(dropdown_edit_freq.value)
                    quete["base_xp"] = float(txt_edit_xp.value.replace(",", "."))
            except ValueError:
                pass
                
            sauvegarder_donnees_globales(donnees)
            dialog_edit.open = False
            rafraichir_liste_quetes()
            page.update()

        dialog_edit = ft.AlertDialog(
            title=ft.Text("Modifier la quête ⚙️"),
            content=ft.Column(elements_formulaire, spacing=10, height=220, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: setattr(dialog_edit, "open", False) or page.update()),
                ft.TextButton("Enregistrer", on_click=enregistrer_modification)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        page.overlay.append(dialog_edit)
        dialog_edit.open = True
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
            title=ft.Text("Abandonner la quête ?"),
            content=ft.Text(f"On supprime ? Sûr : \n\"{quete.get('titre')}\" ?"),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: setattr(dialog_confirm, "open", False) or page.update()),
                ft.TextButton("Supprimer", icon=ft.Icons.DELETE_FOREVER, icon_color="#6F0000", on_click=confirmer_suppression)
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

    # --- 6. AFFICHAGE DES QUÊTES ACTIVES ---
    liste_visuelle_quetes = ft.ReorderableListView(
        height=540,                     
        spacing=10,                     
        scroll=ft.ScrollMode.AUTO,
        on_reorder=reorganiser_quetes
    )

    def basculer_mode_epure(e):
        page.mode_epure = not page.mode_epure
        btn_switch_epure.icon = ft.Icons.VISIBILITY_OFF if page.mode_epure else ft.Icons.VISIBILITY
        btn_switch_epure.tooltip = "Mode Épuré" if page.mode_epure else "Mode Édition"
        rafraichir_liste_quetes()

    btn_switch_epure = ft.IconButton(
        icon=ft.Icons.VISIBILITY_OFF,
        icon_color="#FFBF00",
        icon_size=20,
        tooltip="Mode Épuré",
        on_click=basculer_mode_epure
    )

    header_section_quetes = ft.Row([
        ft.Text("LISTE DES QUÊTES", size=16, color="#FFBF00", weight=ft.FontWeight.BOLD),
        btn_switch_epure
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

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
            liste_visuelle_quetes.controls.append(ft.Text("Aucune quête crée", color="#A9A9A9", italic=True, key="empty_list"))
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

            if q.get("derniere_semaine_annee", 0) != semaine_actuelle:
                if q.get("type") == "ObjectifKmHebdo":
                    if q.get("km_actuel", 0.0) < q.get("km_cible", 30.0):
                        q["streak"] = 0
                    q["km_actuel"] = 0.0
                    if q.get("nouveau_km_cible") is not None:
                        q["km_cible"] = q["nouveau_km_cible"]
                        q["base_xp"] = q["nouveau_base_xp"]
                        q["nouveau_km_cible"] = None
                        q["nouveau_base_xp"] = None
                else:
                    q["validations_semaine"] = 0
                q["derniere_semaine_annee"] = semaine_actuelle
                sauvegarder_donnees_globales(donnees)

            bloc_actions_admin = ft.Row([
                ft.IconButton(ft.Icons.SETTINGS, icon_color="#ADA1A1", icon_size=16, tooltip="Modifier", on_click=lambda e, quete=q: modifier_quete(e, quete)),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_color="#B10505", icon_size=18, tooltip="Supprimer", on_click=lambda e, quete=q: supprimer_quete(e, quete)),
            ], spacing=0)

            if q.get("type") == "ObjectifKmHebdo":
                km_a = q.get("km_actuel", 0.0)
                km_c = q.get("km_cible", 30.0)
                complete = (km_a >= km_c)
                progression = min(km_a / km_c, 1.0) if km_c > 0 else 0.0
                
                streak_actuel = q.get("streak", 0)
                xp_affichage_bonus = calculer_xp_multi_plateaux(q, streak_actuel + 1)
                
                barre_orange = ft.ProgressBar(value=progression, color="#FF8C00", bgcolor="#0B0C10", height=6, border_radius=3)
                icon_sport = "🏃‍♂️" if q.get("sport") == "Course à pied" else "🚴‍♂️"
                
                txt_evo_attente = " ⏳" if q.get("nouveau_km_cible") is not None else ""
                sub_txt = f"{icon_sport} Hebdo : {round(km_a, 1)} / {km_c} km | +{xp_affichage_bonus} XP{txt_evo_attente}"
                btn_affichage_texte = "Surpassement ⚡" if complete else "+ Km"

                nouveaux_controles.append(
                    ft.Container(
                        key=cle_unique,
                        margin=ft.Margin(0, 0, 0, 10),
                        content=ft.Column([
                            ft.Row([
                                ft.Container(content=bloc_actions_admin, visible=page.mode_epure),
                                ft.Column([ft.Text(q["titre"], color="#FFFFFF", weight=ft.FontWeight.BOLD), ft.Text(sub_txt, color="#A9A9A9", size=11, visible=not page.mode_epure)], expand=True),
                                ft.Container(content=ft.Text(f"🔥 {streak_actuel}", color="#FF8C00", weight=ft.FontWeight.BOLD, size=12), bgcolor="#0B0C10", padding=5, border_radius=5, visible=not page.mode_epure),
                                ft.ElevatedButton(btn_affichage_texte, disabled=False, on_click=lambda e, quete=q: ajouter_km_objectif_hebdo(e, quete), visible=not page.mode_epure),
                                ft.Icon(ft.Icons.DRAG_HANDLE, color="#FFBF00", size=18, visible=not page.mode_epure)
                            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Container(content=barre_orange, padding=5)
                        ]), bgcolor="#000000", padding=12, border_radius=8
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
                        margin=ft.Margin(0, 0, 0, 10),
                        content=ft.Row([
                            ft.Container(content=bloc_actions_admin, visible=page.mode_epure),
                            ft.Column([ft.Text(q["titre"], color="#FFFFFF", weight=ft.FontWeight.BOLD), ft.Text(f"⏱️ {freq_txt} | 💎 {xp_affichage} XP", color="#A9A9A9", size=11, visible=not page.mode_epure)], expand=True),
                            ft.Container(content=ft.Text(f"🔥 {streak_actuel}", color="#FF8C00", weight=ft.FontWeight.BOLD, size=12), bgcolor="#0B0C10", padding=5, border_radius=5, visible=not page.mode_epure),
                            ft.ElevatedButton(btn_texte, bgcolor=btn_fond, disabled=bloque, on_click=action, visible=not page.mode_epure),
                            ft.Icon(ft.Icons.DRAG_HANDLE, color="#FFBF00", size=18, visible=not page.mode_epure)
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER), bgcolor="#000000", padding=12, border_radius=8
                    )
                )
        
        liste_visuelle_quetes.controls = nouveaux_controles
        page.update()

    # --- 7. LOGIQUE & COMPOSANTS DU PANNEAU STATISTIQUES ---
    container_stats_contenu = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO)

    def rafraichir_vue_statistiques():
        container_stats_contenu.controls = []
        
        # 1. Calculs des volumes sportifs
        total_km_course = 0.0
        cible_km_course = 0.0
        total_km_velo = 0.0
        cible_km_velo = 0.0
        
        total_habitudes = 0
        habitudes_reussies = 0

        for q in donnees.get("quetes", []):
            if q.get("type") == "ObjectifKmHebdo":
                if "course" in q.get("sport", "").lower():
                    total_km_course += q.get("km_actuel", 0.0)
                    cible_km_course += q.get("km_cible", 0.0)
                elif "vélo" in q.get("sport", "").lower() or "velo" in q.get("sport", "").lower():
                    total_km_velo += q.get("km_actuel", 0.0)
                    cible_km_velo += q.get("km_cible", 0.0)
            else:
                total_habitudes += q.get("jours_cible", 1)
                habitudes_reussies += q.get("validations_semaine", 0)

        taux_habitudes = round((habitudes_reussies / total_habitudes * 100), 1) if total_habitudes > 0 else 100.0

        # Bloc : Résumé Global
        card_global = ft.Container(
            content=ft.Column([
                ft.Text("STATISTIQUES DE CHASSEUR", size=14, color="#FFBF00", weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Column([ft.Text("Quêtes Validées", size=11, color="#A9A9A9"), ft.Text(str(donnees.get("total_quetes_realisees", 0)), size=20, color="#FFFFFF", weight=ft.FontWeight.BOLD)]),
                    ft.Column([ft.Text("Niveau Actuel", size=11, color="#A9A9A9"), ft.Text(f"Niv. {donnees['niveau']}", size=20, color="#FF8C00", weight=ft.FontWeight.BOLD)]),
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND)
            ]), bgcolor="#000000", padding=15, border_radius=10, border=ft.Border.all(1, "#FFBF00")
        )

        # Bloc : Volume Course à pied
        prog_course = min(total_km_course / cible_km_course, 1.0) if cible_km_course > 0 else 0.0
        card_course = ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("🏃‍♂️ Volume Course à pied", weight=ft.FontWeight.BOLD), ft.Text(f"{round(total_km_course, 1)} / {round(cible_km_course, 1)} km", color="#FFBF00", size=12)]),
                ft.ProgressBar(value=prog_course, color="#FFBF00", bgcolor="#0B0C10", height=8, border_radius=4),
                ft.Text(f"Complété à {round(prog_course*100, 1)}%", size=11, color="#A9A9A9", italic=True)
            ]), bgcolor="#000000", padding=12, border_radius=8
        )

        # Bloc : Volume Vélo
        prog_velo = min(total_km_velo / cible_km_velo, 1.0) if cible_km_velo > 0 else 0.0
        card_velo = ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("🚴‍♂️ Volume Cyclisme", weight=ft.FontWeight.BOLD), ft.Text(f"{round(total_km_velo, 1)} / {round(cible_km_velo, 1)} km", color="#FF8C00", size=12)]),
                ft.ProgressBar(value=prog_velo, color="#FF8C00", bgcolor="#0B0C10", height=8, border_radius=4),
                ft.Text(f"Complété à {round(prog_velo*100, 1)}%", size=11, color="#A9A9A9", italic=True)
            ]), bgcolor="#000000", padding=12, border_radius=8
        )

        # Bloc : Assiduité Habitudes
        card_habitudes = ft.Container(
            content=ft.Column([
                ft.Row([ft.Text("⏱️ Assiduité aux Habitudes", weight=ft.FontWeight.BOLD), ft.Text(f"{taux_habitudes}%", color="#00FF88", size=12)]),
                ft.ProgressBar(value=taux_habitudes/100, color="#00FF88", bgcolor="#0B0C10", height=8, border_radius=4),
                ft.Text(f"{habitudes_reussies} validations réussies cette semaine", size=11, color="#A9A9A9", italic=True)
            ]), bgcolor="#000000", padding=12, border_radius=8
        )

        container_stats_contenu.controls.extend([
            ft.Text("BILAN DE L'ÉVOLUTION", size=16, color="#FFBF00", weight=ft.FontWeight.BOLD),
            card_global,
            card_course,
            card_velo,
            card_habitudes
        ])
        page.update()

    affichage_complet_stats = ft.Column([
        container_stats_contenu
    ], spacing=10)


    # --- 8. LAYOUT & NAVIGATION PRINCIPALE ---
    colonne_formulaire = ft.Column([
        ft.Text("CRÉATEUR DE SYSTÈME", size=16, color="#FFBF00", weight=ft.FontWeight.BOLD),
        selecteur_onglets_custom,
        txt_titre,
        container_form_habitude,
        container_form_km,
        ft.Divider(color="#1F2833"),
        btn_creer
    ], spacing=12, horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=580, scroll=ft.ScrollMode.AUTO)

    affichage_complet_quetes = ft.Column([
        header_section_quetes,
        liste_visuelle_quetes
    ], spacing=10)

    zone_dynamique = ft.Container(content=affichage_complet_quetes, height=580)

    def changer_onglet_vers_liste(e):
        btn_onglet_liste.bgcolor = "#1A1A2E"
        btn_onglet_creer.bgcolor = "#0B0C10"
        btn_onglet_stats.bgcolor = "#0B0C10"
        zone_dynamique.content = affichage_complet_quetes
        rafraichir_liste_quetes()

    def changer_onglet_vers_creer(e):
        btn_onglet_liste.bgcolor = "#0B0C10"
        btn_onglet_creer.bgcolor = "#1A1A2E"
        btn_onglet_stats.bgcolor = "#0B0C10"
        zone_dynamique.content = colonne_formulaire
        page.update()

    def changer_onglet_vers_stats(e):
        btn_onglet_liste.bgcolor = "#0B0C10"
        btn_onglet_creer.bgcolor = "#0B0C10"
        btn_onglet_stats.bgcolor = "#1A1A2E"
        zone_dynamique.content = affichage_complet_stats
        rafraichir_vue_statistiques()

    btn_onglet_liste = ft.ElevatedButton(content=ft.Row([ft.Icon(ft.Icons.LIST_ALT, color="#FFBF00", size=15), ft.Text("Quêtes", color="#FFFFFF", size=11)], spacing=4), bgcolor="#1A1A2E", on_click=changer_onglet_vers_liste, expand=True)
    btn_onglet_creer = ft.ElevatedButton(content=ft.Row([ft.Icon(ft.Icons.ADD_BOX, color="#FFBF00", size=15), ft.Text("Créer", color="#FFFFFF", size=11)], spacing=4), bgcolor="#0B0C10", on_click=changer_onglet_vers_creer, expand=True)
    btn_onglet_stats = ft.ElevatedButton(content=ft.Row([ft.Icon(ft.Icons.BAR_CHART, color="#FFBF00", size=15), ft.Text("Stats", color="#FFFFFF", size=11)], spacing=4), bgcolor="#0B0C10", on_click=changer_onglet_vers_stats, expand=True)
    
    barre_onglets = ft.Row(controls=[btn_onglet_liste, btn_onglet_creer, btn_onglet_stats], alignment=ft.MainAxisAlignment.SPACE_EVENLY, spacing=5)

    header_profil = ft.Container(
        content=ft.Column([ft.Row([lbl_niveau, lbl_xp_texte], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), barre_xp], spacing=5),
        padding=12, bgcolor="#000000", border_radius=10, border=ft.Border.all(width=1, color="#FFBF00")
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
