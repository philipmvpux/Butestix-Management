# ============================================================
#  pages/materialplanung.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.materialplanung import materialplanung_page
# ============================================================

import time
import textwrap
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta, time as datetime_time
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import text
from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,
    load_agb, load_datenschutz,
    show_agb_with_scrollbar, show_datenschutz_with_scrollbar,
)
from ui.login import hash_password, verify_password
from ui.archiv import (
    save_bericht_daten_to_archive, load_bericht_daten_from_archive,
    save_pdf_to_archive, load_pdf_from_archive,
)
from ui.pdf_generator import (
    generate_invoice_pdf_v2, generate_pauschal_invoice_pdf,
    generate_fortschritt_pdf, markdown_to_pdf,
)

def materialplanung_page():
    st.set_page_config(page_title="Materialplanung", layout="centered")
    st.title(" Material-Planung")

    if st.session_state.get("nutzer_typ") == "mitarbeiter":
        mitarbeiter = st.session_state.user
        chef_row = pd.read_sql(
            "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(mitarbeiter,)
        )
        chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
        if st.button("← Zurück zum Hauptmenü"):
            st.session_state.page = "app"
            st.rerun()
        with st.expander("+ Material aus Lager auswählen oder hinzufügen"):
            heute_str = date.today().strftime("%Y-%m-%d")
            df_termine = pd.read_sql(
                "SELECT datum FROM materialplanung WHERE datum >= %s ORDER BY datum",
                engine, params=(heute_str,)
            )
            termine_liste = df_termine["datum"].tolist()
            bestellung_auswahl = st.selectbox("Bestelltermin auswählen", termine_liste, key="bestellung_auswahl_mitarbeiter")

            mat_name = st.text_input("Materialname eingeben", key=f"mat_name_{bestellung_auswahl}")
            anzahl = st.number_input("Anzahl", min_value=1, step=1, key=f"anzahl_material_{bestellung_auswahl}")
            if st.button("Material eintragen", key=f"eintragen_{bestellung_auswahl}") and mat_name:
                projekt_id = st.session_state.get("projekt_id")
                df_proj = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(projekt_id,))
                projektname = df_proj["name"].iloc[0] if not df_proj.empty else ""
                rolle_row = pd.read_sql("SELECT rolle FROM mitarbeiter WHERE benutzername = %s", engine, params=(mitarbeiter,))
                rolle = rolle_row["rolle"].iloc[0] if not rolle_row.empty else ""
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO materialplanung (datum, material, menge, benutzername, projekt_id)
                            VALUES (:datum, :material, :menge, :benutzername, :projekt_id)
                        """),
                        {
                            "datum": bestellung_auswahl,
                            "material": mat_name,
                            "menge": anzahl,
                            "benutzername": mitarbeiter,
                            "projekt_id": st.session_state.get("projekt_id")
                        }
                    )
                st.success(f"Material '{mat_name}' ({anzahl}) zur Bestellung am {bestellung_auswahl} hinzugefügt.")
                st.rerun()

                # NUR für Bauunternehmer: Bestellungen hinzufügen (wiederkehrend oder einmalig)
    if st.session_state.get("nutzer_typ") == "bauunternehmer":
        with st.expander(" Bestellung hinzufügen"):
            bestell_typ = st.radio("Bestelltyp wählen", ["Wiederkehrend (Rhythmus in Tagen)", "Einmalig"])
            if bestell_typ == "Wiederkehrend (Rhythmus in Tagen)":
                rhythmus = st.number_input("Rhythmus (Tage)", min_value=1, step=1, value=14, key="rhythmus_bestellung")
                startdatum = st.date_input("Startdatum", value=date.today(), key="startdatum_bestellung")
                anzahl_wdh = st.number_input("Wie oft wiederholen?", min_value=1, step=1, value=10, key="anzahl_wdh_bestellung")
                if st.button("Wiederkehrende Bestellung speichern", key="btn_wiederkehrend_bestellung"):
                    for i in range(anzahl_wdh):
                        bestell_datum = startdatum + timedelta(days=i*rhythmus)
                        with engine.begin() as conn:
                            conn.execute(
                                text("""
                                    INSERT INTO materialplanung (datum, material, menge, benutzername, projekt_id)
                                    VALUES (:datum, :material, :menge, :benutzername, :projekt_id)
                                """),
                                {
                                    "datum": bestell_datum.strftime("%Y-%m-%d"),
                                    "material": '',
                                    "menge": 0,
                                    "benutzername": st.session_state.user,
                                    "projekt_id": st.session_state.get("projekt_id")
                                }
                            )
                    st.success("Wiederkehrende Bestellung(en) gespeichert.")
                    st.rerun()
            else:  # Einmalig
                einmal_datum = st.date_input("Bestelldatum", value=date.today(), key="einmal_datum_bestellung")
                if st.button("Bestellung speichern"):
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                                INSERT INTO materialplanung (datum, material, menge, benutzername, projekt_id)
                                VALUES (:datum, :material, :menge, :benutzername, :projekt_id)
                            """),
                            {
                                "datum": einmal_datum.strftime("%Y-%m-%d"),
                                "material": '',
                                "menge": 0,
                                "benutzername": st.session_state.user,
                                "projekt_id": st.session_state.get("projekt_id")
                            }
                        )
                    st.success("Bestellung gespeichert.")
                    st.rerun()
        # Neuer Expander: Ermöglicht dem Bauunternehmer, konkrete Material-Einträge hinzuzufügen
        with st.expander("+ Material eintragen (Bauunternehmer)"):
            # Datumsauswahl: wähle bestehendes Bestelldatum oder neues Datum
            df_dates = pd.read_sql("SELECT DISTINCT datum FROM materialplanung WHERE datum >= %s ORDER BY datum", engine, params=(date.today().strftime('%Y-%m-%d'),))
            dates_list = df_dates['datum'].tolist()
            use_existing = st.checkbox("Vorhandenes Bestelldatum verwenden", value=True, key="bau_use_existing_date")
            if use_existing and dates_list:
                sel_date = st.selectbox("Bestelldatum auswählen", dates_list, key="bau_sel_date")
            else:
                sel_date_input = st.date_input("Datum auswählen", value=date.today(), key="bau_new_date")
                sel_date = sel_date_input.strftime('%Y-%m-%d')

            # Projekte des Bauunternehmers laden
            projekts = pd.read_sql("SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL ORDER BY name", engine, params=(st.session_state.user,))
            projekt_options = projekts['name'].tolist() if not projekts.empty else [""]
            # Filter nur AKTIVE Projekte
            projekt_options_active = [p for p in projekt_options if p != ""]
            projekt_choice = st.selectbox("Projekt (optional)", projekt_options, index=0 if projekt_options else 0, key="bau_proj_choice")

            mat_name_b = st.text_input("Materialname", key="bau_mat_name")
            anzahl_b = st.number_input("Anzahl", min_value=1, step=1, value=1, key="bau_mat_anzahl")
            # Für Bauunternehmer wird kein Mitarbeiter oder Rolle eingetragen - stattdessen '-' verwenden
            mitarbeiter_b = "-"
            rolle_b = "-"

            if st.button("Material speichern", key="bau_mat_save"):
                if not mat_name_b:
                    st.error("Bitte Materialname eingeben.")
                else:
                    # Finde die projekt_id basierend auf projekt_choice
                    projekt_id = None
                    if projekt_choice and projekt_choice != "":
                        matching_proj = projekts[projekts['name'] == projekt_choice]
                        if not matching_proj.empty:
                            projekt_id = int(matching_proj['id'].iloc[0])
                    
                    # Konvertiere Timestamp zu String für PostgreSQL
                    if isinstance(sel_date, str):
                        datum_str = sel_date
                    else:
                        datum_str = pd.Timestamp(sel_date).strftime("%Y-%m-%d")
                    
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                                INSERT INTO materialplanung (datum, material, menge, benutzername, projekt_id)
                                VALUES (:datum, :material, :menge, :benutzername, :projekt_id)
                            """),
                            {
                                "datum": datum_str,
                                "material": mat_name_b,
                                "menge": int(anzahl_b),
                                "benutzername": st.session_state.user,
                                "projekt_id": projekt_id
                            }
                        )
                    st.success(f"Material '{mat_name_b}' ({anzahl_b}) für {datum_str} gespeichert.")
                    st.rerun()
    # --- Tabelle: Alle Materialplanungen anzeigen ---
    st.subheader("Geplante Materialbestellungen")
    heute_str = date.today().strftime("%Y-%m-%d")
    df_plan = pd.read_sql(
        "SELECT * FROM materialplanung WHERE datum >= %s ORDER BY datum",
        engine,
        params=(heute_str,)
    )
    if df_plan.empty:
        st.info("Keine Materialplanungen vorhanden.")
    else:
        alle_termine = sorted(df_plan["datum"].unique())
        table_html = """
        <style>
        .scroll-table-wrapper {overflow-x: auto; border: 1px solid #ddd; padding: 1rem;}
        .scroll-table {border-collapse: collapse; min-width: 100%;}
        .scroll-table th, .scroll-table td {border: 1px solid #ccc; padding: 0.5rem 1rem; text-align: left;}
        .scroll-table th:first-child, .scroll-table td:first-child {position: sticky; left: 0; background: var(--table-header-bg); z-index: 1;}
        .scroll-table th {background: var(--table-header-bg); position: sticky; top: 0; z-index: 2;} 
        </style>
        <div class="scroll-table-wrapper">
        <table class="scroll-table">
        <thead>
        <tr>
            <th>Bestellung</th>
            <th>Material (Anzahl)</th>
            <th>Mitarbeiter (Rolle)</th>
            <th>Projekt</th>
        </tr>
        </thead>
        <tbody>
        """
        for datum in alle_termine:
            # Konvertiere Timestamp zu date, falls nötig
            if isinstance(datum, str):
                datum_dt = datetime.strptime(datum, "%Y-%m-%d").date()
            else:
                # Pandas Timestamp
                datum_dt = pd.Timestamp(datum).date()
            verbleibend = (datum_dt - date.today()).days
            bestellung = f"{datum_dt.strftime('%d.%m.%Y')} ({verbleibend} Tage)"
            eintraege = df_plan[(df_plan["datum"] == datum) & (df_plan["material"].notnull()) & (df_plan["material"] != "")]
            if eintraege.empty:
                # Platzhalter-Zeile nur, wenn keine Einträge vorhanden sind
                table_html += f"<tr><td><strong>{bestellung}</strong></td><td colspan='3' style='color:gray'>Keine Einträge</td></tr>"
            else:
                first = True
                for _, row in eintraege.iterrows():
                    material_anzahl = f"{row['material']} ({row['menge']})"
                    # Hole Mitarbeiter-Info aus benutzername
                    mitarbeiter_info = pd.read_sql(
                        "SELECT vorname, nachname FROM mitarbeiter WHERE benutzername = %s",
                        engine,
                        params=(row['benutzername'],)
                    )
                    if not mitarbeiter_info.empty:
                        mitarbeiter_rolle = f"{mitarbeiter_info['vorname'].iloc[0]} {mitarbeiter_info['nachname'].iloc[0]}"
                    else:
                        mitarbeiter_rolle = row.get('benutzername', '-')
                    
                    # Hole Projekt-Info aus projekt_id
                    projekt = '-'
                    if pd.notnull(row['projekt_id']) and row['projekt_id'] > 0:
                        projekt_info = pd.read_sql(
                            "SELECT name FROM projekte WHERE id = %s",
                            engine,
                            params=(row['projekt_id'],)
                        )
                        projekt = projekt_info['name'].iloc[0] if not projekt_info.empty else '-'
                    
                    if first:
                        table_html += f"<tr><td rowspan='{len(eintraege)}'><strong>{bestellung}</strong></td>"
                        first = False
                    else:
                        table_html += "<tr>"
                    table_html += f"<td>{material_anzahl}</td><td>{mitarbeiter_rolle}</td><td>{projekt}</td></tr>"
        table_html += "</tbody></table></div>"
        st.markdown(table_html, unsafe_allow_html=True)
        if st.session_state.get("nutzer_typ") == "mitarbeiter":
            if st.button("← Zurück zur Mitarbeiterseite"):
                st.session_state.page = "mitarbeiter"
                st.rerun()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

