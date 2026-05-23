# ============================================================
#  pages/standardgehalt.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.standardgehalt import standardgehalt_page
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

def standardgehalt_page():
    st.set_page_config(page_title="Standardgehalt", layout="centered")
    st.title("Standardgehalt für Mitarbeiter")
    st.info("Hier kannst du den Standardgehalt für Mitarbeiter festlegen oder anzeigen.")
    rolle = st.selectbox("Rolle auswählen", ROLLEN)
    gehalt = st.number_input("Standardgehalt (€ pro Std)", min_value=0.0, step=0.1)
    if st.button(" Speichern"):
        with engine.begin() as conn:
            if gehalt == 0.0:
                conn.exec_driver_sql("DELETE FROM standardgehaelter WHERE rolle = %s", (rolle,))
                st.success(f"Standardgehalt für '{rolle}' wurde entfernt.")
            else:
                conn.exec_driver_sql("""
                    INSERT INTO standardgehaelter (rolle, gehalt)
                    VALUES (%s, %s)
                    ON CONFLICT(rolle) DO UPDATE SET gehalt=excluded.gehalt
                """, (rolle, gehalt))
                st.success(f"Standardgehalt für '{rolle}' auf {gehalt:.2f} € gesetzt.")
        st.rerun()
    # Tabelle anzeigen
    df_gehaelter = pd.read_sql("SELECT rolle, gehalt FROM standardgehaelter ORDER BY rolle", engine)
    df_gehaelter["Gehalt"] = df_gehaelter["gehalt"].map(lambda x: f"{x:.2f} €/Std")
    df_gehaelter = df_gehaelter[["Gehalt", "rolle"]]  # Gehalt ganz links
    st.subheader("Aktuelle Standardgehälter")
    table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
    table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Gehalt (€/Std)</th><th>Rolle</th></tr></thead><tbody>"
    for _, row in df_gehaelter.iterrows():
        geh_val = str(row['Gehalt']) if pd.notnull(row['Gehalt']) else "-"
        rolle_val = str(row['rolle']) if pd.notnull(row['rolle']) else "-"
        table_html += f"<tr><td><strong>{geh_val}</strong></td><td>{rolle_val}</td></tr>"
    table_html += "</tbody></table></div>"
    st.markdown(table_html, unsafe_allow_html=True)
    if st.button("← Zurück zum Profil"):
        st.session_state.page = "profil"
        st.rerun()










