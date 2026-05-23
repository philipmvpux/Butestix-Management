# ============================================================
#  pages/mitarbeiter_auswahl.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.mitarbeiter_auswahl import mitarbeiter_projekt_auswahl_page
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

def mitarbeiter_projekt_auswahl_page():
    """Mitarbeiter-Projekt Auswahl - External page shown only once after login"""
    st.title("👷 Projekt auswählen")
    st.info("Bitte wählen Sie ein Projekt aus, an dem Sie arbeiten möchten.")
    
    # Hole alle zugeordneten Projekte
    df_projekte = pd.read_sql("""
        SELECT p.id, p.name 
        FROM mitarbeiter_projekte mp 
        JOIN projekte p ON mp.projekt_id = p.id 
        WHERE mp.mitarbeiter_benutzername = %s
    """, engine, params=(st.session_state.user,))
    
    if df_projekte.empty:
        st.error("Keine Projekte zugewiesen. Bitte kontaktieren Sie Ihren Vorgesetzten.")
        if st.button("Abmelden"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    else:
        st.subheader("Verfügbare Projekte:")
        cols = st.columns(len(df_projekte))
        for idx, (_, row) in enumerate(df_projekte.iterrows()):
            with cols[idx % len(cols)]:
                if st.button(f"{row['name']}", key=f"proj_{row['id']}"):
                    st.session_state.projekt_id = int(row["id"])
                    st.session_state.page = "app"
                    st.session_state.nav = "Mitarbeiterprojekt"
                    st.rerun()

