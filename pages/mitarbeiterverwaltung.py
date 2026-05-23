# ============================================================
#  pages/mitarbeiterverwaltung.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.mitarbeiterverwaltung import mitarbeiterverwaltung_page
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO

from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,
)
from ui.login import hash_password
def mitarbeiterverwaltung_page():
        st.header("Mitarbeiterverwaltung")
        st.subheader(" Arbeitszeiterfassungen aller Mitarbeiter")
        # === Daten laden ===
        arbeitszeiten_df = pd.read_sql("SELECT * FROM arbeitszeiten", engine)
        projekte_df = pd.read_sql("SELECT id, name FROM projekte", engine)


        # Projektname zum Projekt ID mappen
        projekt_dict = dict(zip(projekte_df["id"], projekte_df["name"]))
        with st.expander(" Zeiterfassungen anzeigen"):
            # Arbeitszeiten-Tabelle immer anzeigen, auch wenn leer
            if arbeitszeiten_df.empty:
                st.info("Keine Arbeitszeiten erfasst. Es sind keine Einträge vorhanden.")
            else:
                if "projekt_id" in arbeitszeiten_df.columns:
                    arbeitszeiten_df["projektname"] = arbeitszeiten_df["projekt_id"].map(projekt_dict).fillna("Unbekannt")
                else:
                    arbeitszeiten_df["projektname"] = "Unbekannt"
                arbeitszeiten_df["stunden"] = pd.to_numeric(arbeitszeiten_df["stunden"], errors="coerce")
                mitarbeiter_df = pd.read_sql("SELECT benutzername, vorname, nachname FROM mitarbeiter", engine)
                name_map = mitarbeiter_df.set_index("benutzername").apply(lambda x: f"{x['vorname']} {x['nachname']}", axis=1).to_dict()
                arbeitszeiten_df["voller_name"] = arbeitszeiten_df["benutzername"].map(name_map).fillna(arbeitszeiten_df["benutzername"])
                # Berechne Durchschnitt der letzten 13 Wochen pro Mitarbeiter
                arbeitszeiten_df["datum_dt"] = pd.to_datetime(arbeitszeiten_df["datum"], errors="coerce")
                avg_stunden = {}
                def sick_eintrag(row):
                    if row.get("status") == "krank":
                        return f"krank ({avg_stunden.get(row['benutzername'], 0.0)} h)"
                    return f"{row['startzeit']} - {row['endzeit']} ( {row['stunden']:.1f} h)"
                arbeitszeiten_df["eintrag"] = arbeitszeiten_df.apply(sick_eintrag, axis=1)
                arbeitszeiten_df["spalte"] = arbeitszeiten_df["projektname"] + " (" + arbeitszeiten_df["voller_name"] + ")"
                pivot_df = arbeitszeiten_df.pivot_table(index="datum", columns="spalte", values="eintrag", aggfunc="first").fillna("–")
                stunden_summen = arbeitszeiten_df.groupby("spalte")["stunden"].sum().round(1)
                stunden_summen.name = "Gesamtstunden"
                stunden_summen = stunden_summen.astype(str) + " h"
                # Summe als letzte Zeile anhängen
                pivot_df.loc["Gesamtstunden"] = stunden_summen
                pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1)
                st.subheader("Übersicht: Arbeitszeiten nach Projekt und Mitarbeiter")
                # HTML-Tabelle für Arbeitszeiten
                table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
                table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Datum</th>"
                for col in pivot_df.columns:
                    table_html += f"<th>{col}</th>"
                table_html += "</tr></thead><tbody>"
                for idx, row in pivot_df.iterrows():
                    table_html += f"<tr><td><strong>{idx}</strong></td>"
                    for col in pivot_df.columns:
                        val = str(row[col]) if pd.notnull(row[col]) else "-"
                        table_html += f"<td>{val}</td>"
                    table_html += "</tr>"
                table_html += "</tbody></table></div>"
                st.markdown(table_html, unsafe_allow_html=True)
            with st.expander(" Arbeitszeiteintrag löschen"):
                if arbeitszeiten_df.empty:
                    st.info("Es sind keine Arbeitszeiteinträge vorhanden.")
                else:
                    datum_liste = arbeitszeiten_df["datum"].drop_duplicates().sort_values().tolist()
                    datum_zum_loeschen = st.selectbox("Wähle das Datum aus", datum_liste)
                    if st.button("Eintrag(e) für dieses Datum löschen"):
                        with engine.begin() as conn:
                            conn.exec_driver_sql(
                                "DELETE FROM arbeitszeiten WHERE datum = %s",
                                (datum_zum_loeschen,)
                            )
                        st.success(f"Arbeitszeiteintrag(e) für **{datum_zum_loeschen}** wurden gelöscht.")
                        st.rerun()
        st.subheader(" Mitarbeiterkonto anlegen")
        # Projekte dieses Bauunternehmers laden
        with st.expander(" Mitarbeiter anlegen"):    
            df_projekte = pd.read_sql(
                "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
                engine, params=(st.session_state.user,)
            )

            if df_projekte.empty:
                st.info("Bitte zuerst mindestens ein Projekt anlegen.")
            else:
                with st.form("mitarbeiter_anlegen_form"):
                    mitarbeitername = st.text_input("Benutzername des Mitarbeiters")
                    vorname = st.text_input("Vorname des Mitarbeiters")
                    nachname = st.text_input("Nachname des Mitarbeiters")
                    passwort = st.text_input("Passwort", type="password")
                    rolle = st.selectbox("Rolle", ROLLEN)
                    projekt_liste = df_projekte[["id", "name"]].drop_duplicates().sort_values("name")
                    projekt_name = st.selectbox("Projekt zuweisen", projekt_liste["name"].tolist())
                    abschicken = st.form_submit_button("Mitarbeiter anlegen")

                if abschicken:
                    vorhandene = pd.read_sql(
                        "SELECT * FROM mitarbeiter WHERE benutzername = %s",
                        engine,
                        params=(mitarbeitername,)
                    )
                    if not vorhandene.empty:
                        st.warning(f"Benutzername '{mitarbeitername}' ist bereits vergeben. Bitte wähle einen anderen.")
                    else:
                        projekt_id = int(projekt_liste.loc[projekt_liste["name"] == projekt_name, "id"].values[0])
                        try:
                            with engine.begin() as conn:
                                # Hash the password and create the employee
                                hashed_password = hash_password(passwort)
                                conn.exec_driver_sql("""
                                INSERT INTO mitarbeiter (benutzername, vorname, nachname, passwort, chefname, rolle, geraeteverwaltung)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (mitarbeitername, vorname, nachname, hashed_password, st.session_state.user, rolle, 0))
                                
                                # Then assign them to the selected project (include chefname)
                                conn.exec_driver_sql("""
                                INSERT INTO mitarbeiter_projekte (mitarbeiter_benutzername, projekt_id, chefname)
                                VALUES (%s, %s, %s)
                                """, (mitarbeitername, projekt_id, st.session_state.user))
                                
                            st.success(f"Mitarbeiterkonto '{mitarbeitername}' wurde erfolgreich erstellt.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler beim Anlegen: {e}")
        
        # Tabelle mitarbeiter_projekte wird in database.py erstellt
            # PostgreSQL: ensure_schema() already created all tables with correct columns


        
        # Hole Mitarbeiter mit ihren Projekten - bessere Query mit Subselect
        df_mitarbeiter = pd.read_sql(
            """
            SELECT DISTINCT 
                m.benutzername, 
                m.passwort, 
                m.rolle,
                COALESCE(
                    (SELECT STRING_AGG(p.name, ', ')
                     FROM mitarbeiter_projekte mp_sub
                     JOIN projekte p ON mp_sub.projekt_id = p.id
                     WHERE mp_sub.mitarbeiter_benutzername = m.benutzername
                       AND mp_sub.chefname = %s
                    ), 
                    '-'
                ) AS Projektname
            FROM mitarbeiter m
            WHERE m.chefname = %s
            ORDER BY m.benutzername
            """,
            engine,
            params=(st.session_state.user, st.session_state.user)
        )
            # vollen Namen berechnen und als erste Spalte anzeigen
        df_mitarbeiter["voller_name"] = df_mitarbeiter["benutzername"].map(
                lambda bn: f"{bn}"  # Fallback falls Name nicht gefunden
            )
            # Hole Vorname/Nachname aus der DB
        namen_df = pd.read_sql("SELECT benutzername, vorname, nachname FROM mitarbeiter", engine)
        name_map = namen_df.set_index("benutzername").apply(lambda x: f"{x['vorname']} {x['nachname']}", axis=1).to_dict()
        df_mitarbeiter["voller_name"] = df_mitarbeiter["benutzername"].map(name_map).fillna(df_mitarbeiter["benutzername"])
        
        
        # HTML-Tabelle für Mitarbeiter - FIX: Korrekte Spaltennamen verwenden
        table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
        table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Vollständiger Name</th><th>Benutzername</th><th>Rolle</th><th>Projekte</th></tr></thead><tbody>"
        for _, row in df_mitarbeiter.iterrows():
            voller_name = str(row['voller_name']) if pd.notnull(row['voller_name']) else ""
            benutzername = str(row['benutzername']) if pd.notnull(row['benutzername']) else ""
            rolle = str(row['rolle']) if pd.notnull(row['rolle']) else "-"
            # Versuche beide Spaltennamen (Projektname und projektname)
            if 'Projektname' in row.index:
                projektname = str(row['Projektname']) if pd.notnull(row['Projektname']) else "-"
            elif 'projektname' in row.index:
                projektname = str(row['projektname']) if pd.notnull(row['projektname']) else "-"
            else:
                projektname = "-"
            table_html += f"<tr><td><strong>{voller_name}</strong></td><td>{benutzername}</td><td>{rolle}</td><td>{projektname}</td></tr>"
        table_html += "</tbody></table></div>"
        st.markdown(table_html, unsafe_allow_html=True)
        with st.expander(" Mitarbeiterkonto bearbeiten/löschen"):
            if df_mitarbeiter.empty:
                st.info("Es sind keine Mitarbeiter vorhanden.")
            else:
                # Mitarbeiter-Auswahl mit vollem Namen und Rolle
                df_mitarbeiter["anzeige"] = df_mitarbeiter.apply(lambda x: f"{x['voller_name']} ({x['rolle']})", axis=1)
                mitarbeiter_auswahl = st.selectbox("Mitarbeiter auswählen", df_mitarbeiter["anzeige"].tolist())
                mitarbeiter_row = df_mitarbeiter[df_mitarbeiter["anzeige"] == mitarbeiter_auswahl].iloc[0]
                benutzername = mitarbeiter_row["benutzername"]
                # Projekt-Verwaltung
                df_projekte = pd.read_sql("SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
                projekt_liste = df_projekte["name"].tolist()
                
                # Zeige aktuelle Projekt-Zuweisungen
                df_zuweisungen = pd.read_sql(
                    """
                    SELECT p.name as projektname 
                    FROM mitarbeiter_projekte mp 
                    JOIN projekte p ON mp.projekt_id = p.id 
                    WHERE mp.mitarbeiter_benutzername = %s
                    """, 
                    engine, 
                    params=(benutzername,)
                )
                if not df_zuweisungen.empty:
                    st.write("Aktuelle Projekte:")
                    for _, row in df_zuweisungen.iterrows():
                        st.write(f"- {row['projektname']}")
                else:
                    st.write("Keine Projekte zugewiesen")
                
                # Projekt-Auswahl für neue Zuweisung
                projekt_auswahl = st.selectbox(
                    "Projekt auswählen (für Zuweisung)",
                    [""] + projekt_liste,  # Empty option first
                    index=0
                )
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("Löschen", key="mitarbeiter_loeschen"):
                        with engine.begin() as conn:
                            # First remove all project assignments
                            conn.exec_driver_sql(
                                "DELETE FROM mitarbeiter_projekte WHERE mitarbeiter_benutzername = %s",
                                (benutzername,)
                            )
                            # Then delete the employee
                            conn.exec_driver_sql(
                                "DELETE FROM mitarbeiter WHERE benutzername = %s",
                                (benutzername,)
                            )
                        st.success(f"Mitarbeiter **{mitarbeiter_auswahl}** wurde gelöscht.")
                        st.rerun()
                
                with col2:
                    if st.button("+ Projekt zuweisen", key="projekt_zuweisen") and projekt_auswahl:
                        projekt_id = int(df_projekte[df_projekte["name"] == projekt_auswahl]["id"].iloc[0])
                        with engine.begin() as conn:
                            conn.exec_driver_sql(
                                """
                                INSERT INTO mitarbeiter_projekte 
                                (mitarbeiter_benutzername, projekt_id, chefname) 
                                VALUES (%s, %s, %s)
                                ON CONFLICT (mitarbeiter_benutzername, projekt_id) DO NOTHING
                                """,
                                (benutzername, projekt_id, st.session_state.user)
                            )
                        st.success(f"Mitarbeiter **{mitarbeiter_auswahl}** wurde dem Projekt **{projekt_auswahl}** zugewiesen.")
                        st.rerun()
                
                with col3:
                    if st.button("- Projekt entfernen", key="projekt_entfernen") and projekt_auswahl:
                        projekt_id = int(df_projekte[df_projekte["name"] == projekt_auswahl]["id"].iloc[0])
                        with engine.begin() as conn:
                            conn.exec_driver_sql(
                                "DELETE FROM mitarbeiter_projekte WHERE mitarbeiter_benutzername = %s AND projekt_id = %s",
                                (benutzername, projekt_id)
                            )
                        st.success(f"Projekt **{projekt_auswahl}** wurde von Mitarbeiter **{mitarbeiter_auswahl}** entfernt.")
                        st.rerun()
                
                with col4:
                    if st.button("Alle Projekte entfernen", key="alle_projekte_entfernen"):
                        with engine.begin() as conn:
                            conn.exec_driver_sql(
                                "DELETE FROM mitarbeiter_projekte WHERE mitarbeiter_benutzername = %s",
                                (benutzername,)
                            )
                        st.success(f"Alle Projekte wurden von Mitarbeiter **{mitarbeiter_auswahl}** entfernt.")
                        st.rerun()

