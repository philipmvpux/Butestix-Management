# ============================================================
#  pages/agb.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.agb import agb_akzeptieren_page
# ============================================================

import time
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO

from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,
    load_agb, load_datenschutz,
    show_agb_with_scrollbar, show_datenschutz_with_scrollbar,
)
from ui.pdf_generator import markdown_to_pdf

def agb_akzeptieren_page():
    """Seite zur Akzeptanz von AGB und Datenschutz nach dem Login - MIT INHALTSANZEIGE"""
    st.set_page_config(page_title="AGB akzeptieren", layout="wide")
    
    st.title("📋 AGB & Datenschutz akzeptieren")
    st.info("Bitte lesen Sie unsere AGB und Datenschutzerklärung sorgfältig durch.")
    
    try:
        with open("AGB.md", "r", encoding="utf-8") as f:
            agb_content = f.read()
    except:
        agb_content = "AGB nicht verfügbar"
    
    try:
        with open("DATENSCHUTZ.md", "r", encoding="utf-8") as f:
            ds_content = f.read()
    except:
        ds_content = "Datenschutzerklärung nicht verfügbar"
    
    col_content, col_accept = st.columns([2, 1])
    
    with col_content:
        with st.expander("📄 Allgemeine Geschäftsbedingungen (AGB)", expanded=True):
            st.markdown(agb_content)
            try:
                pdf_path = markdown_to_pdf(agb_content, "/tmp/AGB.pdf")
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 AGB als PDF herunterladen",
                        data=f.read(),
                        file_name="AGB.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            except Exception as e:
                st.warning(f"PDF nicht verfügbar: {str(e)}")
        
        st.markdown("---")
        
        with st.expander("🔒 Datenschutzerklärung", expanded=True):
            st.markdown(ds_content)
            try:
                pdf_path = markdown_to_pdf(ds_content, "/tmp/DATENSCHUTZ.pdf")
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 Datenschutz als PDF herunterladen",
                        data=f.read(),
                        file_name="DATENSCHUTZ.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            except Exception as e:
                st.warning(f"PDF nicht verfügbar: {str(e)}")
    
    with col_accept:
        st.markdown("### Zustimmung")
        agb_check = st.checkbox("✓ Ich akzeptiere die **AGB**", value=False, key="agb_check_login")
        ds_check = st.checkbox("✓ Ich akzeptiere die **Datenschutzerklärung**", value=False, key="ds_check_login")
        st.markdown("---")
        
        if st.button("✅ AKZEPTIEREN & FORTFAHREN", use_container_width=True, type="primary"):
            if not agb_check:
                st.error("❌ Bitte akzeptieren Sie die AGB!")
                st.stop()
            if not ds_check:
                st.error("❌ Bitte akzeptieren Sie die Datenschutzerklärung!")
                st.stop()
            
            try:
                user = st.session_state.get("user")
                with engine.begin() as conn:
                    conn.exec_driver_sql(
                        """UPDATE benutzer SET agb_accepted = TRUE, agb_accepted_at = CURRENT_TIMESTAMP,
                           datenschutz_accepted = TRUE, datenschutz_accepted_at = CURRENT_TIMESTAMP
                           WHERE benutzername = %s""",
                        (user,)
                    )
                
                # ✅ Speichere Status im Session State damit es gleich erkannt wird
                st.session_state.agb_accepted = True
                st.session_state.datenschutz_accepted = True
                
                st.success("✅ AGB und Datenschutz akzeptiert!")
                time.sleep(0.5)
                st.session_state.page = "check_firmenprofil"
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Speichern: {str(e)}")
        
        if st.button("❌ ABLEHNEN", use_container_width=True):
            st.warning("Sie müssen den AGB und Datenschutz zustimmen.")
            time.sleep(1)
            st.session_state.clear()
            st.session_state.page = "login"
            st.rerun()

# === Mitarbeiter Management Seite ===
