# ============================================================
#  pages/neues_projekt.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.neues_projekt import neues_projekt_page
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO
from sqlalchemy import text
from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,sync_materialien
)

def neues_projekt_page():
    st.header("Neues Projekt anlegen")
        # Berechne nächste Rechnungsnummer
    max_num_row = pd.read_sql("SELECT MAX(rechnungsnummer) as maxnum FROM projekte WHERE benutzername = %s", engine, params=(st.session_state.user,))
    max_num = int(max_num_row["maxnum"].iloc[0]) if not max_num_row.empty and pd.notnull(max_num_row["maxnum"].iloc[0]) else int(st.session_state.get("standard_rechnungsnummer", 100))
    neue_nummer = max_num + 1
    
    with st.form("projekt_formular"):
        name = st.text_input("Projektname")
        budget = st.number_input("Budget (€)", min_value=1000.0, step=100.0)
        rechnungsnummer = st.text_input("Rechnungsnummer", value=str(neue_nummer))  # Vorausgefüllt, aber editierbar
        speichern = st.form_submit_button("Projekt speichern")
    
        # Speichern des Projekts in der Datenbank
        if speichern and name:
            try:
                rechnungsnummer_int = int(rechnungsnummer)
            except (ValueError, TypeError):
                st.error("Rechnungsnummer muss eine Zahl sein!")
                rechnungsnummer_int = neue_nummer
            
            with engine.begin() as conn:
                # Use RETURNING clause for PostgreSQL to get the inserted ID
                result = conn.execute(text(
                    "INSERT INTO projekte (name, budget, benutzername, rechnungsnummer, datum) VALUES (:name, :budget, :benutzername, :rechnungsnummer, :datum) RETURNING id"
                ), {
                    "name": name,
                    "budget": budget,
                    "benutzername": st.session_state.user,
                    "rechnungsnummer": rechnungsnummer_int,
                    "datum": date.today().strftime("%Y-%m-%d")
                })
                projekt_id = result.scalar()
        # Für jedes Material einen Eintrag in materialien anlegen (mit Einheit!)
                materialien = pd.read_sql("SELECT material, einheit FROM lagerbestand", engine)[["material", "einheit"]].values.tolist()
                for mat, einheit in materialien:
                        conn.exec_driver_sql(
                            "INSERT INTO materialien (projekt_id, material, menge, benutzername, einheit) VALUES (%s, %s, 0, %s, %s)",
                            (projekt_id, mat, st.session_state.user, einheit)
                        )
            sync_materialien()
            st.success(f"Projekt '{name}' wurde erfolgreich gespeichert.")
            st.rerun()







