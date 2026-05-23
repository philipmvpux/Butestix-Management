# ============================================================
#  pages/fortschritt_page.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.fortschritt_page import fortschritt_page
# ============================================================

import textwrap
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta, time as datetime_time
from io import BytesIO
from ui.archiv import load_pdf_from_archive, save_pdf_to_archive
from ui.pdf_generator import generate_fortschritt_pdf
from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,
)

def fortschritt_page():
        st.header("Projektfortschritt")
        projekte = pd.read_sql("""
            SELECT DISTINCT p.id, p.name 
            FROM projekte p
            LEFT JOIN mitarbeiter_projekte mp ON p.id = mp.projekt_id
            WHERE (p.benutzername = %s OR mp.mitarbeiter_benutzername = %s) 
            AND p.archiviert_am IS NULL
        """, engine, params=(st.session_state.user, st.session_state.user))
        if projekte.empty:
            st.info("Noch keine Projekte vorhanden.")
        else:
            for _, projekt in projekte.iterrows():
                checklist_df = pd.read_sql(
                    "SELECT id, text, erledigt FROM checklistenpunkte WHERE projekt_id = %s ORDER BY id",
                    engine, params=(projekt["id"],)
                )
                total = len(checklist_df)
                erledigt = checklist_df["erledigt"].sum() if total > 0 else 0
                fortschritt = int(erledigt / total * 100) if total > 0 else 0

                with st.expander(f"{projekt['name']} ({fortschritt}%)", expanded=False):
                    st.progress(fortschritt / 100)
                    st.markdown(f"**{fortschritt}% der Checkliste erledigt**")
                    if checklist_df.empty:
                        st.info("Für dieses Projekt wurde noch keine Checkliste angelegt.")
                    else:
                        for idx, row in checklist_df.iterrows():
                            checked = "✅" if row["erledigt"] else "⬜"
                            st.markdown(f"{checked} {row['text']}")


                    # Zeige ausschließlich den Kommentar aus checklisten_gesamtkommentar und Zeitaufwand
                    kommentare = pd.read_sql(
                        "SELECT benutzername, kommentar, zeitaufwand, datum FROM checklisten_gesamtkommentar WHERE projekt_id = %s",
                        engine, params=(projekt["id"],)
                    )
                    if not kommentare.empty:
                        kommentare = kommentare.sort_values(["benutzername", "datum"], ascending=[True, False])
                        kommentare = kommentare.drop_duplicates(subset=["benutzername"], keep="first")
                    mitarbeiter_df = pd.read_sql("""
                        SELECT m.benutzername, m.vorname, m.nachname 
                        FROM mitarbeiter m
                        JOIN mitarbeiter_projekte mp ON m.benutzername = mp.mitarbeiter_benutzername
                        WHERE mp.projekt_id = %s
                    """, engine, params=(projekt["id"],))
                    name_map = mitarbeiter_df.set_index("benutzername").apply(lambda x: f"{x['vorname']} {x['nachname']}", axis=1).to_dict()
                    st.markdown("**Kommentare & Zeitaufwand der Mitarbeiter:**")
                    max_width = 60
                    daten_vorhanden = False
                    for _, mitarbeiter in mitarbeiter_df.iterrows():
                        eintrag = kommentare[kommentare["benutzername"] == mitarbeiter["benutzername"]]
                        if not eintrag.empty:
                            daten_vorhanden = True
                            break
                    if not daten_vorhanden:
                        st.warning("Keine Daten von den Mitarbeitern eingetragen.")
                    else:
                        for _, mitarbeiter in mitarbeiter_df.iterrows():
                            voller_name = f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}".strip()
                            eintrag = kommentare[kommentare["benutzername"] == mitarbeiter["benutzername"]]
                            kommentar = eintrag["kommentar"].iloc[0] if not eintrag.empty else "–"
                            zeit = eintrag["zeitaufwand"].iloc[0] if not eintrag.empty else "–"
                            datum = eintrag["datum"].iloc[0] if not eintrag.empty else "–"
                            wrapped = textwrap.fill(kommentar if kommentar else "–", width=max_width)
                            st.markdown(f"- {voller_name} ({datum}): {wrapped}")
                            st.markdown(f"  - Benötigte Zeit: {zeit if zeit else '–'} min.")

                    # Spalte fortschritt_text in checklisten_allgemeinkommentar sicherstellen
                    with engine.begin() as conn:
                        try:
                            conn.exec_driver_sql("ALTER TABLE checklisten_allgemeinkommentar ADD COLUMN fortschritt_text TEXT")
                        except Exception:
                            pass  # Column already exists
                    # Separater Block für Fortschritt-Text aus checklisten_allgemeinkommentar
                    allg_row = pd.read_sql(
                        "SELECT fortschritt_text FROM checklisten_allgemeinkommentar WHERE projekt_id = %s",
                        engine, params=(projekt["id"],)
                    )
                    if not allg_row.empty and allg_row["fortschritt_text"].iloc[0].strip():
                        st.markdown("**Fortschritt-Text zur Checkliste:**")
                        st.info(allg_row["fortschritt_text"].iloc[0])
                                    # == Fortschritts-PDF erstellen ==
                    st.subheader("Fortschrittsbericht als PDF exportieren")
                    heute = date.today().strftime("%Y-%m-%d")
                    if st.button("Bericht als PDF erstellen", key=f"pdf_{projekt['id']}"):
                        # Überprüfe: Existiert bereits ein PDF für heute?
                        now = datetime.now().time()
                        is_late_window = now >= datetime_time(23, 50)  # Zwischen 23:50 und Mitternacht
                        
                        # Versuche PDF zu laden (außer wenn zwischen 23:50-Mitternacht)
                        if not is_late_window:
                            existing_pdf = load_pdf_from_archive(st.session_state.user, projekt["id"], heute)
                            if existing_pdf:
                                st.success("PDF von heute gefunden - lädt...")
                                st.download_button(
                                    " PDF herunterladen (gespeichert)",
                                    existing_pdf,
                                    file_name="fortschrittsbericht.pdf",
                                    mime="application/pdf"
                                )
                                st.stop()
                        
                        # PDF existiert nicht oder ist Late-Window: Generiere neu
                        from ui.pdf_generator import generate_fortschritt_pdf
                        buffer = generate_fortschritt_pdf(projekt["id"], projekt["name"])
                        if buffer:
                            st.success("Bericht erfolgreich archiviert!")
                            st.download_button("📄 PDF herunterladen", buffer,
                                            file_name="fortschrittsbericht.pdf",
                                            mime="application/pdf")
                            st.rerun()




