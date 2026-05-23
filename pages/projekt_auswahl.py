# ============================================================
#  pages/projekt_auswahl.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.projekt_auswahl import projekt_auswahl_page
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

def projekt_auswahl_page():
    st.title(" Projekt auswählen")
    st.write("Bitte wählen Sie das Projekt, an dem Sie arbeiten möchten.")
    
    projects = st.session_state.get("verfuegbare_projekte", [])
    cols = st.columns(3)
    for i, project in enumerate(projects):
        with cols[i % 3]:
            if st.button(f"{project['name']}", key=f"project_{project['id']}"):
                st.session_state.projekt_id = project['id']
                st.session_state.page = "mitarbeiter"
                st.rerun()
    
    # Add logout button
    st.markdown("---")
    if st.button(" Abmelden"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# === Streamlit UI ===
