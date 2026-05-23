# ============================================================
#  pages/materialuebersicht.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.materialuebersicht import materialuebersicht_page
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO

from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,
    sync_materialien,
)

def materialuebersicht_page():
        st.header(" Materialübersicht")
# Daten einmalig laden
        df_projekte = pd.read_sql(
            "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
            engine,
            params=(st.session_state.user,)
        )
        df_lager = pd.read_sql(
            "SELECT * FROM lagerbestand WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        df_material = pd.read_sql(
            "SELECT * FROM materialien WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        alle_materialien_db = pd.read_sql(
            "SELECT DISTINCT material FROM materialien WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        lager_db = pd.read_sql(
            "SELECT DISTINCT material FROM lagerbestand WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        alle_materialien = sorted(set(alle_materialien_db["material"]).union(set(lager_db["material"])))
        # === Initialisierung der Session-States für Reset
        if "materialname_reset" not in st.session_state:
            st.session_state.materialname_reset = ""
        if "lagermenge_reset" not in st.session_state:
            st.session_state.lagermenge_reset = 0.0
        if "material_edit_counter" not in st.session_state:
            st.session_state.material_edit_counter = 0
# Material hinzufügen
        st.subheader("+ Neues Material")
        with st.form("neues_material_formular"):
            neues_material = st.text_input("Neuer Materialname")
            lager_menge = st.number_input("Aktueller Lagerbestand", min_value=0.0, step=1.0)
            einheit = st.selectbox("Einheit auswählen", EINHEITEN)
            preis_ankauf = st.number_input("Ankaufspreis (€)", min_value=0.0, step=0.1)
            preis_verkauf = st.number_input("Verkaufspreis (€)", min_value=0.0, step=0.1)
            hinzu = st.form_submit_button("Hinzufügen")
            if hinzu and neues_material:
                with engine.begin() as conn:
                    # Try INSERT first, update if exists
                    try:
                        conn.exec_driver_sql("""
                             INSERT INTO lagerbestand (material, menge, benutzername, preis_ankauf, preis_verkauf, einheit)
                             VALUES (%s, %s, %s, %s, %s, %s)
                        """, (neues_material, lager_menge, st.session_state.user, preis_ankauf, preis_verkauf, einheit))
                    except:
                        # Material already exists, update it
                        conn.exec_driver_sql("""
                             UPDATE lagerbestand
                             SET menge = menge + %s,
                                 preis_ankauf = %s,
                                 preis_verkauf = %s,
                                 einheit = %s
                             WHERE material = %s AND benutzername = %s
                        """, (lager_menge, preis_ankauf, preis_verkauf, einheit, neues_material, st.session_state.user))
                for _, projekt in df_projekte.iterrows():
                    with engine.begin() as conn:
                        try:
                            conn.exec_driver_sql("""
                        INSERT INTO materialien (projekt_id, material, menge, benutzername, einheit) VALUES (%s, %s, 0, %s, %s)
                    """, (projekt["id"], neues_material, st.session_state.user, einheit))
                        except:
                            # Material already exists for this project, update it
                            conn.exec_driver_sql("""
                        UPDATE materialien SET menge = %s WHERE projekt_id = %s AND material = %s AND benutzername = %s
                    """, (0, projekt["id"], neues_material, st.session_state.user))
                sync_materialien()
                st.success(f"Material '{neues_material}' hinzugefügt.")
                st.session_state.materialname_reset = ""
                st.session_state.lagermenge_reset = 0.0
                st.rerun()
        if "projekt_bearbeiten_offen" not in st.session_state:
            st.session_state.projekt_bearbeiten_offen = True
        with st.expander(" Als Administrator bearbeiten"):
            st.warning("**Admin-Modus aktiviert:** Wenn Sie hier Werte bearbeiten, wird das automatische Tracking der Mitarbeitereingaben gestoppt und die Werte werden als feste Werte festgelegt.")
            # Schritt 1: Projekt zur Bearbeitung auswählen
            df_projekte = pd.read_sql(
                "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
                engine,
                params=(st.session_state.user,)
            )
            df_material = pd.read_sql(
                "SELECT * FROM materialien WHERE benutzername = %s",
                engine,
                params=(st.session_state.user,)
            )
            projekt_namen = df_projekte["name"].tolist()
            if not projekt_namen:
                st.info("Es sind noch keine Projekte vorhanden.")
            else:
                ausgewaehlt = st.selectbox("Wähle ein Projekt zur Bearbeitung", projekt_namen)
                projekt = df_projekte[df_projekte["name"] == ausgewaehlt].iloc[0]
                st.markdown(f"###  Bearbeite: {projekt['name']}")

                # Schritt 2: Alle aktuellen Werte sammeln und anzeigen
                with st.form("projekt_bearbeiten_formular"):    
                    aktuelle_werte = {}
                    bearbeitet_flags = {}
                    for mat in alle_materialien:
                        menge_df = df_material.query("projekt_id == @projekt.id and material == @mat")["menge"]
                        alt_menge = float(menge_df.iloc[0]) if not menge_df.empty else 0.0
                        # Flag für Bauunternehmer-Bearbeitung
                        bearbeitet_df = df_material.query("projekt_id == @projekt.id and material == @mat")["bearbeitet_von_bauunternehmer"]
                        bearbeitet = int(bearbeitet_df.iloc[0]) if not bearbeitet_df.empty else 0
                        neue_menge = st.number_input(
                            f"{mat}", value=alt_menge, step=10.0,
                            key=f"bearbeiten_{projekt['id']}_{mat}_{st.session_state.material_edit_counter}"
                        )
                        aktuelle_werte[mat] = neue_menge
                        bearbeitet_flags[mat] = bearbeitet
                    speichern = st.form_submit_button("Änderungen speichern")
                    # Speichern-Button
                    if speichern:
                        with engine.begin() as conn:
                            for mat, menge in aktuelle_werte.items():
                                # Einheit aus Lagerbestand holen
                                einheit_row = df_lager[df_lager["material"] == mat]
                                einheit = einheit_row["einheit"].iloc[0] if not einheit_row.empty else ""
                                # Setze das Flag bearbeitet_von_bauunternehmer = 1
                                conn.exec_driver_sql("""
                                    INSERT INTO materialien (projekt_id, material, menge, benutzername, einheit, bearbeitet_von_bauunternehmer)
                                    VALUES (%s, %s, %s, %s, %s, 1)
                                    ON CONFLICT(projekt_id, material, benutzername)
                                    DO UPDATE SET menge = excluded.menge, einheit = excluded.einheit, bearbeitet_von_bauunternehmer = 1
                                """, (int(projekt["id"]), str(mat), float(menge), st.session_state.user, einheit))
                        sync_materialien()
                        st.success("Alle Änderungen erfolgreich gespeichert.")
                        st.session_state.material_edit_counter += 1  
                        st.session_state.projekt_bearbeiten_offen = False
                        st.rerun()
# Material-Löschaktion abfangen (wird beim Klick ausgelöst)
            if "delete_material" in st.query_params:
                zu_loeschen = st.query_params["delete_material"][0]
                with engine.begin() as conn:
                    conn.exec_driver_sql("DELETE FROM lagerbestand WHERE material = %s", (zu_loeschen,))
                    conn.exec_driver_sql("DELETE FROM materialien WHERE material = %s", (zu_loeschen,))
                sync_materialien()
                st.success(f"Material '{zu_loeschen}' wurde gelöscht.")
                st.rerun()
# Tabelle anzeigen
        if df_projekte.empty:
            st.info("📭 Noch keine Projekte eingetragen. Bitte erst Projekte anlegen.")
        else:    
            st.subheader("Lager-Tabelle mit Projekten")
            # HTML-Tabelle vorbereiten
            table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;}.scroll-table{border-collapse:collapse;min-width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.5rem 1rem;text-align:center;color:var(--text-color);}.scroll-table th:first-child,.scroll-table td:first-child{position:sticky;left:0;background:var(--table-header-bg);z-index:1;}.scroll-table th{background:var(--table-header-bg);position:sticky;top:0;z-index:2;}</style>"
            table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Projekt</th>"

            #Preise für material hinzufügen
            for mat in alle_materialien:
                preis_row = df_lager[df_lager["material"] == mat]
                einheit = preis_row["einheit"].iloc[0] if not preis_row.empty and "einheit" in preis_row else ""
                ankauf = preis_row["preis_ankauf"].iloc[0] if not preis_row.empty else 0.0
                verkauf = preis_row["preis_verkauf"].iloc[0] if not preis_row.empty else 0.0
                # Fehler vermeiden: None durch 0 ersetzen
                ankauf = ankauf if ankauf is not None else 0.0
                verkauf = verkauf if verkauf is not None else 0.0
                preis_info = f" [{einheit}] ({ankauf:.2f}€/{verkauf:.2f}€)"
                table_html += f"<th>{mat}{preis_info}</th>"
    # Lagerbestand-Zeile
            table_html += "<tr><td><strong>Lagerbestand</strong></td>"
            for mat in alle_materialien:
                lager_wert = df_lager.query("material == @mat")["menge"]
                try:
                    val = float(lager_wert.iloc[0]) if not lager_wert.empty else 0.0
                except:
                    val = 0.0
                table_html += f"<td>{val:.2f}</td>"
            table_html += "</tr>"
    # Projektzeilen
            summen_dict = {mat: 0.0 for mat in alle_materialien}
            heute = date.today().strftime("%Y-%m-%d")
            
            # SQL-Query für Grundbestand + heutige Eingaben (NICHT addiert, nur angezeigt)
            material_query = pd.read_sql(
                """
                SELECT 
                    m.projekt_id,
                    m.material,
                    COALESCE(m.verbrauch, 0) as grundbestand,
                    COALESCE(SUM(CASE WHEN m.datum = %s THEN m.menge ELSE 0 END), 0) as heute_menge
                FROM materialien m
                WHERE m.benutzername = %s
                GROUP BY m.projekt_id, m.material, m.verbrauch
                """,
                engine,
                params=(heute, st.session_state.user)
            )
            
            for _, projekt in df_projekte.iterrows():
                table_html += f"<tr><td>{projekt['name']}</td>"
                for mat in alle_materialien:
                    # Finde Eintrag aus Query
                    mat_data = material_query.query("projekt_id == @projekt.id and material == @mat")
                    
                    if not mat_data.empty:
                        grundbestand = float(mat_data.iloc[0]["grundbestand"])
                        heute_menge = float(mat_data.iloc[0]["heute_menge"])
                    else:
                        grundbestand = 0.0
                        heute_menge = 0.0
                    
                    # Zeige beide Werte (aber noch nicht addiert!)
                    angezeigt = grundbestand + heute_menge
                    table_html += f"<td>{angezeigt:.2f}</td>"
                    summen_dict[mat] += angezeigt
            # Saldo-Zeile mit Farbmarkierung
            table_html += "<tr><td><strong>Saldo</strong></td>"
            for mat in alle_materialien:
                lager_wert = df_lager.query("material == @mat")["menge"]
                try:
                    lager = float(lager_wert.iloc[0]) if not lager_wert.empty else 0.0
                except:
                    lager = 0.0
                rest = lager - summen_dict[mat]
                farbe = "green" if rest >= 0 else "red"
                table_html += f"<td style='color:{farbe}; font-weight:bold'>{rest:.2f}</td>"
            table_html += "</tr></tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
            with st.expander("Materialien löschen"):
                if not alle_materialien:
                    st.info("Keine Materialien vorhanden.")
                else:
                    delete_cols = st.columns(len(alle_materialien))
                    for i, mat in enumerate(alle_materialien):
                        if delete_cols[i].button(f" {mat}", key=f"delete_material_{mat}"):
                            with engine.begin() as conn:
                                conn.exec_driver_sql("DELETE FROM lagerbestand WHERE material = %s", (mat,))
                                conn.exec_driver_sql("DELETE FROM materialien WHERE material = %s", (mat,))
                            sync_materialien()
                            st.success(f"Material **{mat}** wurde gelöscht.")
                            st.rerun()


