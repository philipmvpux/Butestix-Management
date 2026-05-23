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

def projekt_checklisten_page():
        st.header("Projekt-Checklisten verwalten")
        projekte = pd.read_sql("SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
        if projekte.empty:
            st.info("Noch keine Projekte vorhanden.")
        else:
            # Nur anzeigen, wenn KEIN Projekt zur Bearbeitung ausgewählt ist:
            if "checklisten_projekt_id" not in st.session_state:
                st.markdown("### Wähle ein Projekt:")
                for _, row in projekte.iterrows():
                    if st.button(row["name"], key=f"checkliste_{row['id']}"):
                        st.session_state["checklisten_projekt_id"] = row["id"]
                        st.session_state["checklisten_projekt_name"] = row["name"]
                        st.rerun()

            # Wenn ein Projekt ausgewählt wurde, nur die Checklisten-Bearbeitung und Zurück-Button anzeigen:
            if "checklisten_projekt_id" in st.session_state:
                # Spalte fortschritt_text in checklisten_allgemeinkommentar wird in database.py erstellt
                pid = st.session_state["checklisten_projekt_id"]
                pname = st.session_state["checklisten_projekt_name"]
                st.markdown(f"## Checkliste für Projekt: **{pname}**")

                
                # Formular für neuen Checklistenpunkt
                with st.form(f"checkliste_hinzufuegen_{pid}"):
                    neuer_punkt = st.text_input("Neuer Checklistenpunkt")
                    hinzufuegen = st.form_submit_button("+ Hinzufügen")
                    if hinzufuegen and neuer_punkt:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO checklistenpunkte (projekt_id, text, erledigt, benutzername)
                                    VALUES (:projekt_id, :text, 0, :benutzername)
                                """), {
                                    "projekt_id": pid,
                                    "text": neuer_punkt,
                                    "benutzername": st.session_state.user
                                })
                        except Exception as e:
                            if "benutzername" in str(e).lower() or "undefinedcolumn" in str(e).lower():
                                # Spalte hinzufügen
                                try:
                                    with engine.begin() as conn:
                                        conn.exec_driver_sql("ALTER TABLE checklistenpunkte ADD COLUMN benutzername TEXT")
                                except:
                                    pass
                                # Warte kurz
                                import time
                                time.sleep(0.5)
                                # Versuche erneut
                                with engine.begin() as conn:
                                    conn.execute(text("""
                                        INSERT INTO checklistenpunkte (projekt_id, text, erledigt, benutzername)
                                        VALUES (:projekt_id, :text, 0, :benutzername)
                                    """), {
                                        "projekt_id": pid,
                                        "text": neuer_punkt,
                                        "benutzername": st.session_state.user
                                    })
                            else:
                                raise
                        st.rerun()

                # Checklistenpunkte anzeigen und löschen
                checklist_df = pd.read_sql(
                    "SELECT id, text, kommentar FROM checklistenpunkte WHERE projekt_id = %s ORDER BY id",
                    engine, params=(pid,)
                )
                for idx, row in checklist_df.iterrows():
                        col1, col2 = st.columns([8, 1])
                        col1.write(row["text"])
                        if col2.button("🗑️", key=f"del_{row['id']}"):
                            with engine.begin() as conn:
                                conn.execute(text("DELETE FROM checklistenpunkte WHERE id = :id"), {"id": row["id"]})
                            st.rerun()
                if st.button("← Zurück zur Projektliste"):
                    del st.session_state["checklisten_projekt_id"]
                    del st.session_state["checklisten_projekt_name"]
                    st.rerun()