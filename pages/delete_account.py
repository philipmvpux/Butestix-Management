# ============================================================
#  pages/delete_account.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.delete_account import delete_account_password_page
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
from ui.login import verify_password
def delete_account_password_page():
    """Account Deletion Password Confirmation Page"""
    st.set_page_config(page_title="Account löschen", layout="centered")
    st.title("Konto löschen - Passwortbestätigung")
    st.warning("Diese Aktion kann nicht rückgängig gemacht werden!")
    st.markdown("Bitte geben Sie Ihr Passwort ein, um das Konto zu löschen.")
    
    password = st.text_input("Passwort eingeben", type="password", key="delete_password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Bestätigen"):
            if password:
                # Hole das aktuelle Passwort aus der DB (erst von benutzer, dann von mitarbeiter)
                df_user = pd.read_sql(
                    "SELECT passwort FROM benutzer WHERE benutzername = %s",
                    engine,
                    params=(st.session_state.user,)
                )
                
                if df_user.empty:
                    # Try mitarbeiter table if benutzer not found
                    df_user = pd.read_sql(
                        "SELECT passwort FROM mitarbeiter WHERE benutzername = %s",
                        engine,
                        params=(st.session_state.user,)
                    )
                
                if not df_user.empty:
                    stored_password = df_user["passwort"].iloc[0]
                    # Nutze verify_password() für sichere Passwort-Überprüfung (mit bcrypt)
                    if verify_password(password, stored_password):
                        st.session_state.page = "delete_account_survey"
                        st.rerun()
                    else:
                        st.error("Passwort ist falsch!")
                else:
                    st.error("Benutzer nicht gefunden!")
            else:
                st.error("Bitte geben Sie Ihr Passwort ein!")
    with col2:
        if st.button("Abbrechen"):
            st.session_state.page = "profil"
            st.rerun()



def delete_account_confirm_page():
    """Account Deletion Confirmation Page (deprecated, use delete_account_password_page)"""
    st.set_page_config(page_title="Account löschen", layout="centered")
    st.title("Konto löschen")
    st.warning("Diese Aktion kann nicht rückgängig gemacht werden!")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, löschen"):
            st.session_state.page = "delete_account_survey"
            st.rerun()
    with col2:
        if st.button("Abbrechen"):
            st.session_state.page = "profil"
            st.rerun()

# === Delete Account Survey ===


def delete_account_survey_page():
    """Account Deletion Survey Page"""
    st.set_page_config(page_title="Feedback", layout="centered")
    st.title("Abschlussfeedback")
    st.markdown("Bevor Ihr Konto gelöscht wird, möchten wir gerne wissen, warum Sie gehen.")
    
    reason = st.text_area("Warum möchten Sie Ihr Konto löschen?", height=150)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Löschen"):
            # Speichere das Feedback in der Datenbank
            deletion_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with engine.begin() as conn:
                try:
                    conn.exec_driver_sql(
                        """INSERT INTO account_deletion_feedback (benutzername, feedback, deletion_date, account_type) 
                           VALUES (%s, %s, %s, %s)""",
                        (st.session_state.user, reason, deletion_date, st.session_state.get("nutzer_typ", "bauunternehmer"))
                    )
                except:
                    pass  # Table might not exist, continue with deletion
            
            # Lösche das Konto aus allen relevanten Tabellen
            with engine.begin() as conn:
                # Delete from benutzer
                conn.exec_driver_sql(
                    "DELETE FROM benutzer WHERE benutzername = %s",
                    (st.session_state.user,)
                )
                # Delete from mitarbeiter if exists
                try:
                    conn.exec_driver_sql(
                        "DELETE FROM mitarbeiter WHERE benutzername = %s OR chefname = %s",
                        (st.session_state.user, st.session_state.user)
                    )
                except:
                    pass
                # Delete from firmenprofil if exists
                try:
                    conn.exec_driver_sql(
                        "DELETE FROM firmenprofil WHERE benutzername = %s",
                        (st.session_state.user,)
                    )
                except:
                    pass
            
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.success("Ihr Konto wurde erfolgreich gelöscht.")
            st.info("Sie werden in Kürze zum Login weitergeleitet...")
            import time
            time.sleep(2)
            st.session_state.page = "login"
            st.rerun()
    
    with col2:
        if st.button("Abbrechen"):
            st.session_state.page = "profil"
            st.rerun()

# === Projekt-Auswahl für Mitarbeiter ===


