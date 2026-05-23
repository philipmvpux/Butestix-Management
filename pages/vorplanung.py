# ============================================================
#  pages/vorplanung.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.vorplanung import vorplanung_page
# ============================================================
import time
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO
from sqlalchemy import text
from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,
)

def vorplanung_page():
    st.set_page_config(page_title="Vorplanungskalender", layout="centered")
    st.title(" Vorplanungskalender")
    
    # Force refresh bei jedem Load
    if "vorplanung_refresh" not in st.session_state:
        st.session_state.vorplanung_refresh = 0
    
    if st.session_state.get("page") == "vorplanung":
        st.session_state.vorplanung_refresh += 1
    
    if st.session_state.get("nutzer_typ") == "mitarbeiter":
        if st.button("← Zurück zum Hauptmenü"):
            st.session_state.page = "app"
            st.rerun()
    heute = date.today()
    tage = [heute + timedelta(days=i) for i in range(14)]
    # Einzelplanung
    with st.expander("+ Neuen Eintrag hinzufügen"):
        datum = st.date_input("Datum", value=heute, min_value=heute, max_value=heute + timedelta(days=13))
        uhrzeiten = [f"{h:02d}:00" for h in range(6, 21)] + ["ganztägig"]
        col_von, col_bis = st.columns(2)
        with col_von:
            von = st.selectbox("Von", uhrzeiten, index=2)
        with col_bis:
            bis = st.selectbox("Bis", uhrzeiten, index=10)
        zeitraum = "ganztägig" if von == "ganztägig" or bis == "ganztägig" else f"{von} - {bis}"

        # Maschinen aus dem Lager holen
        if st.session_state.get("nutzer_typ") == "mitarbeiter":
            chef_row = pd.read_sql(
                "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
            )
            chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
            df_geraete = pd.read_sql(
                "SELECT geraet, anzahl FROM geraete_lager WHERE benutzername = %s", engine, params=(chefname,)
            )
        else:
            df_geraete = pd.read_sql(
                "SELECT geraet, anzahl FROM geraete_lager WHERE benutzername = %s", engine, params=(st.session_state.user,)
            )

        # Maschinen, die im gewählten Zeitraum schon vergeben sind, herausfiltern
        # PostgreSQL Version: Vereinfachte Query ohne komplexe String-Operationen
        belegte = pd.read_sql(
            "SELECT maschine, COUNT(*) as reserviert FROM vorplanung WHERE datum = %s AND zeitraum = %s GROUP BY maschine",
            engine, params=(datum.strftime("%Y-%m-%d"), zeitraum)
        )
        reserviert_dict = dict(zip(belegte["maschine"], belegte["reserviert"].fillna(0)))

        # Maschinenliste und verfügbare Anzahl berechnen
        maschinen_liste = []
        maschinen_anzahl = {}
        for _, row in df_geraete.iterrows():
            name = row["geraet"]
            gesamt = int(row["anzahl"])
            reserviert = int(reserviert_dict.get(name, 0))
            verfuegbar = gesamt - reserviert
            if verfuegbar > 0:
                maschinen_liste.append(name)
                maschinen_anzahl[name] = verfuegbar

        maschine = st.selectbox("Maschine auswählen", maschinen_liste)
        max_anzahl = maschinen_anzahl.get(maschine, 1)
        anzahl = st.selectbox("Anzahl Geräte", list(range(1, max_anzahl+1)), index=0, key="anzahl_einzel")

        # Projektname/Mitarbeiter wie gehabt
        if st.session_state.get("nutzer_typ") == "mitarbeiter":
            df_proj = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(st.session_state.get("projekt_id"),))
            projektname = df_proj["name"].iloc[0] if not df_proj.empty else ""
            mitarbeiter = st.session_state.user
            st.info(f"Projekt: {projektname}")
            st.info(f"Mitarbeiter: {mitarbeiter}")
        else:
            projektname = st.text_input("Projektname")
            mitarbeiter = st.text_input("Mitarbeiter")

        if st.button("Eintrag speichern"):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO vorplanung (datum, maschine, zeitraum, mitarbeiter, projektname)
                        VALUES (:datum, :maschine, :zeitraum, :mitarbeiter, :projektname)
                    """),
                    {
                        "datum": datum.strftime("%Y-%m-%d"),
                        "maschine": maschine,
                        "zeitraum": zeitraum,
                        "mitarbeiter": mitarbeiter,
                        "projektname": f"{projektname} - {anzahl}"
                    }
                )
            st.success(f"{anzahl} Gerät(e) für {maschine} geplant.")
            time.sleep(0.5)  # Warte kurz damit PostgreSQL die Änderung sieht
            st.rerun()

    # Langzeitplanung
    with st.expander("+ Langzeit-Gerätereservierung"):
        start_datum = st.date_input("Startdatum", value=heute)
        end_datum = st.date_input("Enddatum", value=heute + timedelta(days=13), min_value=start_datum)
        # Maschinen wie oben laden
        maschine_lang = st.selectbox("Gerät für Langzeitreservierung auswählen", maschinen_liste, key="langzeit_maschine")
        max_anzahl_lang = maschinen_anzahl.get(maschine_lang, 1)
        anzahl_lang = st.selectbox("Anzahl Geräte", list(range(1, max_anzahl_lang+1)), index=0, key="anzahl_langzeit")

        # Projektname/Mitarbeiter wie gehabt
        if st.session_state.get("nutzer_typ") == "mitarbeiter":
            df_proj = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(st.session_state.get("projekt_id"),))
            projektname_lang = df_proj["name"].iloc[0] if not df_proj.empty else ""
            mitarbeiter_lang = st.session_state.user
            st.info(f"Projekt: {projektname_lang}")
            st.info(f"Mitarbeiter: {mitarbeiter_lang}")
        else:
            projektname_lang = st.text_input("Projektname für Langzeitreservierung")
            mitarbeiter_lang = st.text_input("Mitarbeiter für Langzeitreservierung")

        if st.button("Langzeitreservierung speichern"):
            tage_lang = (end_datum - start_datum).days + 1
            for j in range(tage_lang):
                reserv_datum = start_datum + timedelta(days=j)
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO vorplanung (datum, maschine, zeitraum, mitarbeiter, projektname)
                            VALUES (:datum, :maschine, :zeitraum, :mitarbeiter, :projektname)
                        """),
                        {
                            "datum": reserv_datum.strftime("%Y-%m-%d"),
                            "maschine": maschine_lang,
                            "zeitraum": "ganztägig",
                            "mitarbeiter": mitarbeiter_lang,
                            "projektname": f"{projektname_lang} - {anzahl_lang}"
                        }
                    )
            st.success(f"{anzahl_lang} Gerät(e) für {maschine_lang} reserviert.")
            time.sleep(0.5)  # Warte kurz damit PostgreSQL die Änderung sieht
            st.rerun()
    # Daten für die nächsten 14 Tage laden - FORCE RELOAD ohne Cache
    df = pd.read_sql(
        "SELECT * FROM vorplanung WHERE datum >= %s AND datum <= %s ORDER BY datum, maschine",
        engine,
        params=(heute.strftime("%Y-%m-%d"), (heute + timedelta(days=13)).strftime("%Y-%m-%d"))
    )

    # Tabelle vorbereiten mit Cache-Buster
    cache_buster = st.session_state.vorplanung_refresh
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
        <th>Datum</th>
        <th>Maschine + Projekt</th>
        <th>Zeitraum</th>
        <th>Mitarbeiter</th>
    </tr>
    </thead>
    <tbody>
    """
    


    # Konvertiere datum zu String falls nötig
    if not df.empty:
        df['datum_str'] = pd.to_datetime(df['datum']).dt.strftime("%Y-%m-%d")
        # Filtere ungültige Einträge aus (wo mitarbeiter "None" oder "none" ist)
        df = df[~df['mitarbeiter'].isin(['None', 'none', None])]
        # Filtere Langzeitreservierungen aus (nur Einzelreservierungen in dieser Tabelle)
        df = df[df['zeitraum'] != 'ganztägig']
    
    # Baue Tabelle direkt aus den Daten auf
    for tag in tage:
        tag_str = tag.strftime("%d.%m.%Y")
        tag_search = tag.strftime("%Y-%m-%d")
        
        # Filtere Einträge für diesen Tag
        if not df.empty:
            eintraege = df[df['datum_str'] == tag_search]
        else:
            eintraege = pd.DataFrame()
        
        if eintraege.empty:
            table_html += f"<tr><td>{tag_str}</td><td colspan='3' style='color:gray'>Keine Einträge</td></tr>"
        else:
            first = True
            for _, row in eintraege.iterrows():
                # Anzahl aus dem Projektname extrahieren
                proj_parts = str(row['projektname']).rsplit(' - ', 1)
                projektname_clean = proj_parts[0]
                anzahl_str = proj_parts[1] if len(proj_parts) > 1 else "1"
                maschine_proj = f"{row['maschine']} ×{anzahl_str} ({projektname_clean})"
                if first:
                    table_html += f"<tr><td rowspan='{len(eintraege)}'><strong>{tag_str}</strong></td>"
                    first = False
                else:
                    table_html += "<tr>"
                table_html += f"<td>{maschine_proj}</td><td>{row['zeitraum']}</td><td>{row['mitarbeiter']}</td></tr>"
    table_html += "</tbody></table></div>"
    
    st.markdown(table_html, unsafe_allow_html=True)
    # Langzeitreservierungen aus der Datenbank laden
    langzeit_df = pd.read_sql(
        """
        SELECT maschine, projektname, MIN(datum) as von, MAX(datum) as bis
        FROM vorplanung
        WHERE zeitraum = 'ganztägig'
        GROUP BY maschine, projektname
        HAVING MAX(datum) >= CURRENT_DATE
        """,
        engine
    )

    if not langzeit_df.empty:
        st.subheader("Aktuelle Langzeit-Gerätereservierungen")
        for _, row in langzeit_df.iterrows():
            # Konvertiere Datum - kann bereits datetime.date sein
            try:
                von = pd.to_datetime(row["von"]).strftime("%d.%m.%Y")
                bis = pd.to_datetime(row["bis"]).strftime("%d.%m.%Y")
            except:
                von = str(row["von"])
                bis = str(row["bis"])
            st.info(f"{row['maschine']} ({row['projektname']}) {von} – {bis}")
