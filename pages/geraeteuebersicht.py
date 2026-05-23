# ============================================================
#  pages/geraeteuebersicht.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.geraeteuebersicht import geraeteuebersicht_page
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

def geraeteuebersicht_page():
        st.header("Geräteübersicht")
        # Tabelle geraete_lager wird in database.py erstellt
        # Geräte aus DB laden (nur eigene Geräte)
        df_geraete = pd.read_sql(
            "SELECT geraet, anzahl, art, dauer FROM geraete_lager WHERE benutzername = %s",
            engine, params=(st.session_state.user,)
        )

        # Expander zum Eintragen neuer Geräte
        with st.expander("+ Neues Gerät/Maschine eintragen"):
            with st.form("geraet_anlegen_formular"):
                geraet = st.text_input("Gerätename")
                anzahl = st.number_input("Anzahl (stk)", min_value=1, step=1)
                art = st.selectbox("Art", GGG)
                dauer = st.number_input("Dauer (Monate)", min_value=1, step=1, value=1, key="dauer_input")
                betriebskosten = st.number_input("Stündliche Betriebskosten (€/h) pro Gerät", min_value=0.0, step=0.1)
                monatliche_kosten = st.number_input("Monatliche Kosten (€/Monat) pro Gerät", min_value=0.0, step=0.1, value=0.0)
                speichern = st.form_submit_button("Gerät speichern")
            if speichern and geraet:
                if art == "Gekauft":
                    dauer = -1
                else:
                    dauer_db = dauer
                with engine.begin() as conn:
                    # Prüfe, ob Gerät bereits existiert
                    existing = conn.execute(
                        text("SELECT anzahl, monatliche_kosten, betriebskosten FROM geraete_lager WHERE geraet = :geraet AND benutzername = :benutzername"),
                        {"geraet": geraet, "benutzername": st.session_state.user}
                    ).fetchone()
                    
                    if existing:
                        # UPDATE: Addiere die Anzahl, aber behalte erste Kosten pro Gerät
                        existing_anzahl = existing[0] if existing[0] else 0
                        new_anzahl = existing_anzahl + anzahl
                        conn.execute(
                            text("""
                                UPDATE geraete_lager
                                SET anzahl = :anzahl, art = :art, dauer = :dauer, 
                                    betriebskosten = :betriebskosten, monatliche_kosten = :monatliche_kosten
                                WHERE geraet = :geraet AND benutzername = :benutzername
                            """),
                            {
                                "geraet": geraet,
                                "anzahl": new_anzahl,
                                "art": art,
                                "dauer": dauer,
                                "benutzername": st.session_state.user,
                                "betriebskosten": betriebskosten,
                                "monatliche_kosten": monatliche_kosten
                            }
                        )
                        st.success(f"Gerät '{geraet}' um {anzahl} Stück erweitert (insgesamt {new_anzahl}).")
                    else:
                        # INSERT: Neues Gerät mit aktuellem Datum
                        conn.execute(
                            text("""
                                INSERT INTO geraete_lager (geraet, anzahl, art, dauer, benutzername, betriebskosten, monatliche_kosten, datum_hinzugefuegt)
                                VALUES (:geraet, :anzahl, :art, :dauer, :benutzername, :betriebskosten, :monatliche_kosten, :datum_hinzugefuegt)
                            """),
                            {
                                "geraet": geraet,
                                "anzahl": anzahl,
                                "art": art,
                                "dauer": dauer,
                                "benutzername": st.session_state.user,
                                "betriebskosten": betriebskosten,
                                "monatliche_kosten": monatliche_kosten,
                                "datum_hinzugefuegt": datetime.now().strftime("%Y-%m-%d")
                            }
                        )
                        st.success(f"Gerät '{geraet}' ({anzahl}x) wurde gespeichert.")
                st.rerun()

        # Geräte-Tabelle anzeigen (Einheit nur im Text)
        df_geraete = pd.read_sql(
            "SELECT geraet, anzahl, art, dauer, betriebskosten, monatliche_kosten FROM geraete_lager WHERE benutzername = %s",
            engine, params=(st.session_state.user,)
        )
        if df_geraete.empty:
            st.info("Noch keine Geräte/Maschinen eingetragen.")
        else:
            st.subheader("Geräte-Lager")
            
            # Berechne Gesamtnutzung für jedes Gerät (auch archivierte Projekte)
            gesamtnutzung = {}
            for geraet in df_geraete['geraet']:
                nutzung_df = pd.read_sql(
                    """SELECT COALESCE(SUM(n.nutzungszeit), 0) as total 
                       FROM geraete_nutzung n
                       LEFT JOIN projekte p ON n.projekt_id = p.id
                       WHERE n.geraet = %s AND p.benutzername = %s""",
                    engine, params=(geraet, st.session_state.user)
                )
                gesamtnutzung[geraet] = float(nutzung_df['total'].iloc[0]) if not nutzung_df.empty else 0.0
            
            # HTML-Tabelle für Geräte-Lager
            table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;min-width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;position:sticky;top:0;z-index:2;}.scroll-table tr:hover{background:rgba(255,255,255,0.05);}</style>"
            table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Gerät</th><th>Anzahl</th><th>Art</th><th>Dauer</th><th>Gesamtnutzung (h)</th><th>Betriebskosten (€)</th><th>Monatliche Kosten (€)</th></tr></thead><tbody>"
            
            for _, row in df_geraete.iterrows():
                geraet = str(row['geraet']) if pd.notnull(row['geraet']) else ""
                anzahl = str(row['anzahl']) if pd.notnull(row['anzahl']) else "0"
                art = str(row['art']) if pd.notnull(row['art']) else "-"
                
                if row["art"] == "Gekauft" or row.get("dauer") == -1:
                    dauer = "-"
                else:
                    try:
                        dauer = f"{int(row['dauer'])} Monate" if pd.notnull(row['dauer']) else "-"
                    except:
                        dauer = "-"
                
                # Gesamtnutzung anzeigen
                gesamt_stunden = gesamtnutzung.get(geraet, 0.0)
                gesamt_str = f"{gesamt_stunden:.1f}h" if gesamt_stunden > 0 else "0h"
                
                betriebskosten = f"{float(row['betriebskosten']):.2f} €/h" if pd.notnull(row['betriebskosten']) and row['betriebskosten'] > 0 else "-"
                monatliche_kosten = f"{float(row['monatliche_kosten']):.2f} €/Monat" if pd.notnull(row['monatliche_kosten']) and row['monatliche_kosten'] > 0 else "-"
                
                table_html += f"<tr><td><strong>{geraet}</strong></td><td>{anzahl}</td><td>{art}</td><td>{dauer}</td><td>{gesamt_str}</td><td>{betriebskosten}</td><td>{monatliche_kosten}</td></tr>"
            
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
        st.subheader("Geräte-Nutzungen")
# Alle Projekte des Bauunternehmers laden
        # projekt_id Spalte wird in database.py erstellt
        
        df_projekte = pd.read_sql(
            "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
            engine, params=(st.session_state.user,)
        )
        geraete_nutzung_df = pd.read_sql("""
            SELECT n.datum, n.geraet, n.nutzungszeit, p.name AS projektname
            FROM geraete_nutzung n
            LEFT JOIN projekte p ON n.projekt_id = p.id
            WHERE p.benutzername = %s AND p.archiviert_am IS NULL
            ORDER BY n.datum DESC, p.name, n.geraet
        """, engine, params=(st.session_state.user,))

        if geraete_nutzung_df.empty:
            st.info("Keine Geräte-Nutzungen vorhanden.")
        else:
            # Pivot-Tabelle: Zeilen = Datum, Spalten = Projektname, Inhalt = Maschinen mit Nutzungszeit
            def format_maschinen(gruppe):
                return "<br>".join([f"{row['geraet']} ({row['nutzungszeit']}h)" for _, row in gruppe.iterrows()])

            # Gruppieren nach Datum und Projekt
            grouped = geraete_nutzung_df.groupby(["datum", "projektname"])
            table_data = []
            for (datum, projektname), gruppe in grouped:
                table_data.append({
                    "Datum": datum,
                    "Projekt": projektname,
                    "Maschinen": format_maschinen(gruppe)
                })
            df_anzeige = pd.DataFrame(table_data)
            # Pivot: Zeilen = Datum, Spalten = Projekt, Inhalt = Maschinen
            pivot = df_anzeige.pivot(index="Datum", columns="Projekt", values="Maschinen").fillna("")
            pivot = pivot.map(lambda x: x.replace("<br>", "\n") if isinstance(x, str) else x)
            table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
            table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Datum</th>"
            for col in pivot.columns:
                table_html += f"<th>{col}</th>"
            table_html += "</tr></thead><tbody>"
            for idx, row in pivot.iterrows():
                table_html += f"<tr><td><strong>{idx}</strong></td>"
                for col in pivot.columns:
                    val = str(row[col]) if pd.notnull(row[col]) and row[col] != "" else "-"
                    table_html += f"<td>{val}</td>"
                table_html += "</tr>"
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
        # Geräte löschen
        with st.expander(" Gerät löschen"):
            geraete_liste = df_geraete["geraet"].tolist()
            if not geraete_liste:
                st.info("Keine Geräte vorhanden.")
            else:
                geraet_zum_loeschen = st.selectbox("Gerät auswählen", geraete_liste)
                if st.button("Gerät löschen"):
                    with engine.begin() as conn:
                        conn.execute(
                            text("DELETE FROM geraete_lager WHERE geraet = :geraet AND benutzername = :benutzername"),
                            {"geraet": geraet_zum_loeschen, "benutzername": st.session_state.user}
                        )
                    st.success(f"Gerät '{geraet_zum_loeschen}' wurde gelöscht.")
                    st.rerun()

