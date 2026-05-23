# ============================================================
#  pages/settings.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.settings import settings_page
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

def settings_page():
    st.set_page_config(page_title="Einstellungen", layout="centered")
    
    # === KUNDENVERSION: Verstecke Streamlit Buttons ===
    st.markdown("""
    <style>
        [data-testid="stToolbar"] { display: none !important; }
        button[kind="header"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Einstellungen")
    import time

    user = st.session_state.get("user")
    if not user:
        st.warning("Bitte zuerst einloggen.")
        return

    # Load current theme from DB (fallback to session state or 'white')
    try:
        df_user = pd.read_sql("SELECT theme FROM benutzer WHERE benutzername = %s", engine, params=(user,))
        current_theme = df_user["theme"].iloc[0] if not df_user.empty and pd.notnull(df_user["theme"].iloc[0]) else st.session_state.get("theme", "white")
    except Exception:
        current_theme = st.session_state.get("theme", "white")

    with st.expander("Farbmodus", expanded=True):
        choice = st.radio("Farbmodus wählen", ["White (Standard)", "Black (Dunkelmodus)"], index=0 if current_theme == "white" else 1)
        selected = "white" if choice.startswith("White") else "black"

        st.markdown("**Vorschau:**")
        # Live preview (no persistence until save)
        if selected == "black":
            st.markdown(
                """
                <style>
                /* === HEADER/NAVBAR SCHWARZER MODUS === */
                [data-testid="stHeader"] {
                    background-color: #1e1e1e !important;
                }
                /* Dark mode preview variables and styles */
                :root {
                    --app-bg: #1e1e1e;
                    --text-color: #e0e0e0;
                    --box-bg: #252525;
                    --box-border: rgba(255,255,255,0.08);
                    --button-bg: #252525;
                    --button-border: #ffffff;
                    --button-text: #e0e0e0;
                    --table-header-bg: #2a2a2a;
                    --breakdown-bg: #2a2a2a;
                    --breakdown-border: rgba(255,255,255,0.15);
                }
                html, body, .stApp, .block-container, [data-testid="stMarkdownContainer"] {
                    background: var(--app-bg) !important;
                    color: var(--text-color) !important;
                }
                /* Dark preview boxes: stronger contrast and elevation */
                .stExpander, .streamlit-expander, details[role="group"] > summary, .stExpander > div, .st-expander {
                    background: var(--box-bg) !important;
                    color: var(--text-color) !important;
                    border: 1px solid var(--box-border) !important;
                    box-shadow: none !important;
                    border-radius: 8px !important;
                }
                /* Expander opened state */
                details[open] > summary, .streamlit-expanderContent, [data-testid="stExpander"][open] {
                    background: var(--box-bg) !important;
                    color: var(--text-color) !important;
                    border: 1px solid var(--box-border) !important;
                }
                details[open] {
                    background: var(--box-bg) !important;
                }
                .stButton>button, .stDownloadButton>button { background: var(--button-bg) !important; color: var(--button-text) !important; border: 1.5px solid var(--button-border) !important; box-shadow: none !important; }
                /* Make inputs boxed and readable in preview */
                .stTextInput>div>input, .stNumberInput>div>input, .stTextArea>div>textarea, input, textarea, select {
                    background: #2a2a2a !important; color: #e0e0e0 !important; border: 1px solid rgba(255,255,255,0.1) !important; box-shadow: none !important; outline: none !important; padding:6px 8px !important; border-radius:6px !important;
                }
                /* === SELECTBOX SPECIFIC STYLING FOR BLACK MODE === */
                [data-testid="selectbox"] {
                    background-color: #2a2a2a !important;
                }
                [data-testid="selectbox"] * {
                    background-color: #2a2a2a !important;
                    color: #e0e0e0 !important;
                }
                [data-testid="selectbox"] div {
                    background-color: #2a2a2a !important;
                }
                [data-testid="selectbox"] input {
                    background-color: #2a2a2a !important;
                    color: #e0e0e0 !important;
                }
                .stSelectbox > div > div {
                    background-color: #2a2a2a !important;
                    color: #e0e0e0 !important;
                }
                .stSelectbox > div > div > div {
                    background-color: #2a2a2a !important;
                    color: #e0e0e0 !important;
                }
                /* === MULTISELECT STYLING FOR BLACK MODE === */
                [data-testid="multiSelect"] {
                    background-color: #2a2a2a !important;
                }
                [data-testid="multiSelect"] * {
                    background-color: #2a2a2a !important;
                    color: #e0e0e0 !important;
                }
                .stCheckbox>div, .stRadio>div { color: #e0e0e0 !important; }
                </style>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <style>
                /* === HEADER/NAVBAR WEISSER MODUS === */
                [data-testid="stHeader"] {
                    background-color: #ffffff !important;
                }
                /* Reset preview to default light mode */
                </style>
                """, 
                unsafe_allow_html=True
            )

        # Ensure buttons on the settings page follow the global button style (avoid black inner rectangles)
        if selected == "black":
            # BLACK MODE - Subtle buttons with white outline
            st.markdown(
                """
                <style>
                /* enforce the application button look inside settings page - BLACK MODE */
                .stButton>button, .stDownloadButton>button, button, input[type="button"], input[type="submit"] {
                    background: #252525 !important;
                    color: #e0e0e0 !important;
                    border: 1.5px solid #ffffff !important;
                    box-shadow: none !important;
                    border-radius: 6px !important;
                    padding: 6px 12px !important;
                }
                .stButton>button *, .stDownloadButton>button *, button *, input[type="button"] *, input[type="submit"] * {
                    color: #e0e0e0 !important;
                    background: transparent !important;
                }
                .stButton>button:hover, .stDownloadButton>button:hover, button:hover, input[type="button"]:hover, input[type="submit"]:hover {
                    background: #2f2f2f !important;
                    border-color: #ffffff !important;
                    box-shadow: 0 2px 8px rgba(255,255,255,0.1) !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
        else:
            # WHITE MODE - Subtle buttons with black outline
            st.markdown(
                """
                <style>
                /* enforce the application button look inside settings page - WHITE MODE */
                .stButton>button, .stDownloadButton>button, button, input[type="button"], input[type="submit"] {
                    background: #f8f8f8 !important;
                    color: #333333 !important;
                    border: 1.5px solid #000000 !important;
                    box-shadow: none !important;
                    border-radius: 6px !important;
                    padding: 6px 12px !important;
                }
                .stButton>button *, .stDownloadButton>button *, button *, input[type="button"] *, input[type="submit"] * {
                    color: #333333 !important;
                    background: transparent !important;
                }
                .stButton>button:hover, .stDownloadButton>button:hover, button:hover, input[type="button"]:hover, input[type="submit"]:hover {
                    background: #f0f0f0 !important;
                    border-color: #000000 !important;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

        if st.button("Speichern"):
            # ALTER TABLE in separate transaction to avoid "transaction aborted" errors
            try:
                with engine.begin() as conn:
                    conn.exec_driver_sql("ALTER TABLE benutzer ADD COLUMN theme TEXT DEFAULT 'white'")
            except Exception:
                pass  # Column might already exist
            
            # Update theme in a fresh transaction
            with engine.begin() as conn:
                conn.exec_driver_sql("UPDATE benutzer SET theme = %s WHERE benutzername = %s", (selected, user))
            st.session_state["theme"] = selected
            # Persist to client immediately and apply the CSS variables so other pages update instantly
            st.markdown(
                "<script>\n"
                "localStorage.setItem('app_theme', '" + selected + "');\n"
                "(function(){\n"
                "    var theme = '" + selected + "';\n"
                "    var root = document.documentElement;\n"
                "    if(theme === 'black') {\n"
                "        root.style.setProperty('--app-bg','#1e1e1e');\n"
                "        root.style.setProperty('--text-color','#e0e0e0');\n"
                "        root.style.setProperty('--box-bg','#252525');\n"
                "        root.style.setProperty('--box-border','rgba(255,255,255,0.08)');\n"
                "        root.style.setProperty('--table-header-bg','#2a2a2a');\n"
                "        root.style.setProperty('--breakdown-bg','#2a2a2a');\n"
                "        root.style.setProperty('--breakdown-border','rgba(255,255,255,0.15)');\n"
                "    } else {\n"
                "        root.style.setProperty('--app-bg','#ffffff');\n"
                "        root.style.setProperty('--text-color','#333333');\n"
                "        root.style.setProperty('--box-bg','#f8f8f8');\n"
                "        root.style.setProperty('--box-border','rgba(0,0,0,0.08)');\n"
                "        root.style.setProperty('--table-header-bg','#f0f0f0');\n"
                "        root.style.setProperty('--breakdown-bg','#f8f8f8');\n"
                "        root.style.setProperty('--breakdown-border','rgba(0,0,0,0.08)');\n"
                "    }\n"
                "    document.body.style.background = 'var(--app-bg)';\n"
                "    document.body.style.color = 'var(--text-color)';\n"
                "})();\n"
                "</script>",
                unsafe_allow_html=True,
            )
            st.success("Einstellung gespeichert. Seite wird neugeladen...")
            time.sleep(1)
            st.rerun()
            st.rerun()

    
    with st.expander("📚 Tutorial"):
        st.markdown("***")
        if st.session_state.get("nutzer_typ") == "mitarbeiter":
            st.markdown("### Mitarbeiter-Tutorial")
            st.write("Lerne die Funktionen zur Dokumentation von Einsätzen, Materialverbrauch und Planung kennen.")
            if st.button("Tutorial neu starten", key="restart_tutorial_mitarbeiter"):
                # Setze tutorial_completed auf FALSE für Mitarbeiter
                with engine.begin() as conn:
                    conn.exec_driver_sql(
                        "UPDATE mitarbeiter SET tutorial_completed = FALSE WHERE benutzername = %s",
                        (user,)
                    )
                st.success("Mitarbeiter-Tutorial wird neu gestartet...")
                time.sleep(1)
                st.session_state.page = "app"
                st.rerun()
        else:
            st.markdown("### Bauunternehmer-Tutorial")
            st.write("Lerne alle Funktionen zur Projektverwaltung, Budgetierung und Teamkoordination kennen.")
            if st.button("Tutorial neu starten", key="restart_tutorial_bauunternehmer"):
                # Setze tutorial_completed auf FALSE für Bauunternehmer
                with engine.begin() as conn:
                    conn.exec_driver_sql(
                        "UPDATE benutzer SET tutorial_completed = FALSE WHERE benutzername = %s",
                        (user,)
                    )
                st.success("Bauunternehmer-Tutorial wird neu gestartet...")
                time.sleep(1)
                st.session_state.page = "app"
                st.rerun()
    

    if st.button(" Zurück"):
        st.session_state.page = "app"
        st.rerun()

