# ============================================================
#  pages/profil.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.profil import profil_page
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

def profil_page():
    st.set_page_config(page_title="Profil", layout="centered")
    
    # === KUNDENVERSION: Verstecke Streamlit Buttons ===
    st.markdown("""
    <style>
        [data-testid="stToolbar"] { display: none !important; }
        button[kind="header"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Benutzerprofil")

    # Load and apply user's theme preference (white by default)
    try:
        df_theme = pd.read_sql("SELECT theme FROM benutzer WHERE benutzername = %s", engine, params=(st.session_state.user,))
        if not df_theme.empty and pd.notnull(df_theme['theme'].iloc[0]):
            st.session_state['theme'] = df_theme['theme'].iloc[0]
        else:
            st.session_state.setdefault('theme', 'white')
    except Exception:
        st.session_state.setdefault('theme', 'white')

    # Apply global CSS for dark mode if selected
    if st.session_state.get('theme') == 'black':
        st.markdown(
            """
            <style>
            /* === HEADER/NAVBAR SCHWARZER MODUS === */
            [data-testid="stHeader"] {
                background-color: #1e1e1e !important;
            }
            html, body, .stApp, .block-container, [data-testid="stMarkdownContainer"] {
                background: #1e1e1e !important;
                color: #e0e0e0 !important;
            }
            a, a:link, a:visited { color: #ffffff !important; }
            .stExpander, .streamlit-expander, details[role="group"] > summary, .stExpander > div, .st-expander, .css-1lcbmhc {
                background: #252525 !important;
                color: #e0e0e0 !important;
                border: 1px solid rgba(255,255,255,0.08) !important;
                box-shadow: none !important;
                border-radius: 8px !important;
            }
            /* Expander opened state */
            details[open], details[open] > summary, .streamlit-expanderContent {
                background: #252525 !important;
                color: #e0e0e0 !important;
                border: 1px solid rgba(255,255,255,0.08) !important;
            }
            .stButton>button, .stDownloadButton>button, button, input[type="button"], input[type="submit"] {
                background: #252525 !important; color: #e0e0e0 !important; border: 1.5px solid #ffffff !important; box-shadow: none !important; border-radius:6px !important; padding:6px 12px !important;
            }
            .stButton>button * , .stDownloadButton>button * { background: transparent !important; color: inherit !important; }
            .stButton>button:hover, .stDownloadButton>button:hover, button:hover, input[type="button"]:hover, input[type="submit"]:hover { background: #2f2f2f !important; border-color: #ffffff !important; box-shadow: 0 2px 8px rgba(255,255,255,0.1) !important; }
            .stButton>button:active, .stDownloadButton>button:active, button:active { transform: translateY(1px) !important; }
            .stButton>button:focus, .stDownloadButton>button:focus, button:focus { outline: none !important; box-shadow: none !important; }
            .stTextInput>div>input, .stNumberInput>div>input, .stTextArea>div>textarea, input, textarea, select, .stSelectbox {
                background: #2a2a2a !important; color: #e0e0e0 !important; border: 1px solid rgba(255,255,255,0.1) !important; box-shadow: none !important; outline: none !important; padding:6px 8px !important; border-radius:6px !important;
            }
            /* Dropdown/Popup-Menü Styling für Black Mode */
            [role="menuitem"], [role="menu"] {
                background-color: #252525 !important;
                color: #e0e0e0 !important;
                border: 1px solid rgba(255,255,255,0.1) !important;
            }
            [role="menuitem"]:hover, [role="menu"]:hover {
                background-color: #2f2f2f !important;
                color: #e0e0e0 !important;
            }
            /* Popmenu und Dropdowns */
            .stPopover [role="dialog"], .stPopover {
                background-color: #252525 !important;
                color: #e0e0e0 !important;
                border: 1px solid rgba(255,255,255,0.1) !important;
            }
            .stPopover button {
                background-color: #252525 !important;
                color: #e0e0e0 !important;
                border: 1.5px solid rgba(255,255,255,0.2) !important;
            }
            .stPopover button:hover {
                background-color: #2f2f2f !important;
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
            table, th, td { border-color: rgba(255,255,255,0.08) !important; color: #e0e0e0 !important; }
            .stCheckbox>div, .stRadio>div { color: #e0e0e0 !important; }
            ::-webkit-scrollbar { width: 10px; height: 10px; }
            ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 8px; }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        # WHITE MODE CSS für Profil-Seite
        st.markdown(
            """
            <style>
            /* === HEADER/NAVBAR WEISSER MODUS === */
            [data-testid="stHeader"] {
                background-color: #ffffff !important;
            }
            html, body, .stApp, .block-container, [data-testid="stMarkdownContainer"] {
                background: #ffffff !important;
                color: #333333 !important;
            }
            a, a:link, a:visited { color: #000000 !important; }
            .stExpander, .streamlit-expander, details[role="group"] > summary, .stExpander > div, .st-expander, .css-1lcbmhc {
                background: #f8f8f8 !important;
                color: #333333 !important;
                border: 1px solid rgba(0,0,0,0.08) !important;
                box-shadow: none !important;
                border-radius: 8px !important;
            }
            .stButton>button, .stDownloadButton>button, button, input[type="button"], input[type="submit"] {
                background: #f8f8f8 !important; color: #333333 !important; border: 1.5px solid #000000 !important; box-shadow: none !important; border-radius:6px !important; padding:6px 12px !important;
            }
            .stButton>button * , .stDownloadButton>button * { background: transparent !important; color: #333333 !important; }
            .stButton>button:hover, .stDownloadButton>button:hover, button:hover, input[type="button"]:hover, input[type="submit"]:hover { background: #f0f0f0 !important; border-color: #000000 !important; box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important; }
            .stButton>button:active, .stDownloadButton>button:active, button:active { transform: translateY(1px) !important; }
            .stButton>button:focus, .stDownloadButton>button:focus, button:focus { outline: none !important; box-shadow: none !important; }
            .stTextInput>div>input, .stNumberInput>div>input, .stTextArea>div>textarea, input, textarea, select, .stSelectbox {
                background: #ffffff !important; color: #333333 !important; border: 1px solid rgba(0,0,0,0.08) !important; box-shadow: none !important; outline: none !important; padding:6px 8px !important; border-radius:6px !important;
            }
            table, th, td { border-color: rgba(0,0,0,0.08) !important; color: #333333 !important; }
            .stCheckbox>div, .stRadio>div { color: #333333 !important; }
            ::-webkit-scrollbar { width: 10px; height: 10px; }
            ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 8px; }
            </style>
            """,
            unsafe_allow_html=True,
        )
    # vollen Namen aus DB holen
    namen_df = pd.read_sql("SELECT benutzername, vorname, nachname FROM mitarbeiter", engine)
    name_map = namen_df.set_index("benutzername").apply(lambda x: f"{x['vorname']} {x['nachname']}", axis=1).to_dict()
    voller_name = name_map.get(st.session_state.user, st.session_state.user)
    st.markdown(f"### Willkommen, {voller_name}")

    
    
    if st.session_state.get("nutzer_typ") == "mitarbeiter":
        # Get all assigned projects for the employee
        df_projekte = pd.read_sql("""
            SELECT p.id, p.name 
            FROM mitarbeiter_projekte mp 
            JOIN projekte p ON mp.projekt_id = p.id 
            WHERE mp.mitarbeiter_benutzername = %s
        """, engine, params=(st.session_state.user,))
        
        # Show current project
        current_project_id = st.session_state.get("projekt_id")
        if current_project_id:
            current_project = df_projekte[df_projekte["id"] == current_project_id]
            if not current_project.empty:
                st.info(f"🏗️ Aktuelles Projekt: {current_project['name'].iloc[0]}")
        
        # Allow project switching
        st.subheader("Projekt wechseln")
        st.write("Wählen Sie ein Projekt aus, an dem Sie arbeiten möchten:")
        
 
        if st.button(f"Projekt wechseln"):
            st.session_state.page = "mitarbeiter_projekt_auswahl"
            st.rerun()
        
        st.markdown("---")
        if st.button("← Zurück "):
            st.session_state.page = "app"
            st.rerun() 
    # Firmennamen laden oder initialisieren
    # NUR für Bauunternehmer anzeigen:
    if st.session_state.get("nutzer_typ") == "bauunternehmer":
        with st.expander("Firmenprofil"):   
            st.caption("Hier können Sie die grundlegenden Informationen über Ihr Unternehmen speichern. Diese werden für die Erstellung von Rechnungen und anderen Geschäftsdokumenten verwendet.")
            
            # Firmenname
            st.markdown("**Firmenname**")
            st.caption("Der Name Ihres Unternehmens, wie er auf Rechnungen und Dokumenten erscheinen soll.")
            firmenname = st.text_input("Firmenname für Rechnungen", value=st.session_state.firmenname, label_visibility="collapsed")
            
            # Gesellschaftsform
            st.markdown("**Gesellschaftsform**")
            current_gesellschaftsform = st.session_state.get("gesellschaftsform")
            default_index = 0
            if current_gesellschaftsform and current_gesellschaftsform in GESELLSCHAFTSFORMEN:
                default_index = GESELLSCHAFTSFORMEN.index(current_gesellschaftsform)
            
            gesellschaftsform = st.selectbox(
                    "Gesellschaftsform",
                    GESELLSCHAFTSFORMEN,
                    index=default_index,
                    label_visibility="collapsed")
            
            # Adresse
            st.markdown("**Adresse**")
            st.caption("Ihre Geschäftsadresse (z.B. Straße 5, 12345 Stadt).")
            adresse = st.text_input("Firmenadresse", value=st.session_state.get("firmenadresse", ""), label_visibility="collapsed")
            
            # Telefon und Fax
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Telefon**")
                telefon = st.text_input("Telefonnummer", value=st.session_state.get("firmentelefon", ""), label_visibility="collapsed")
            with col2:
                st.markdown("**Fax**")
                fax = st.text_input("Faxnummer", value=st.session_state.get("firmenfax", ""), label_visibility="collapsed")

            # Nächste Rechnungsnummer bestimmen (höchste bisher verwendete + 1)
            max_num_row = pd.read_sql("SELECT MAX(rechnungsnummer) as maxnum FROM projekte WHERE benutzername = %s", engine, params=(st.session_state.user,))
            max_num = int(max_num_row["maxnum"].iloc[0]) if not max_num_row.empty and pd.notnull(max_num_row["maxnum"].iloc[0]) else 99
            next_rechnungsnummer = max_num + 1

            st.markdown("**Rechnungsnummer (Startnummer)**")
            st.caption("Die Rechnungsnummer für Ihr nächstes Projekt. Sie wird automatisch mit jedem neuen Projekt erhöht und eindeutig zugewiesen.")
            standard_rechnungsnummer = st.number_input(
                "Rechnungsnummer",
                step=1,
                min_value=1,
                value=next_rechnungsnummer,
                key="profil_rechnungsnummer_input",
                label_visibility="collapsed"
            )

            if st.button("Firmenprofil speichern"):
                st.session_state.firmenname = firmenname
                st.session_state.firmenadresse = adresse
                st.session_state.firmentelefon = telefon
                st.session_state.firmenfax = fax
                st.session_state.gesellschaftsform = gesellschaftsform
                st.session_state.standard_rechnungsnummer = standard_rechnungsnummer
                
                # Add missing columns in separate transactions to avoid transaction abort
                try:
                    with engine.begin() as conn:
                        conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN rechnungsnummer INTEGER")
                except:
                    pass
                
                try:
                    with engine.begin() as conn:
                        conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN gesellschaftsform TEXT")
                except:
                    pass
                
                # Now insert the data in a fresh transaction
                with engine.begin() as conn:
                    conn.exec_driver_sql("""
                        INSERT INTO firmenprofil (benutzername, firmenname, adresse, telefon, fax, rechnungsnummer, gesellschaftsform)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(benutzername) DO UPDATE SET
                            firmenname=excluded.firmenname,
                            adresse=excluded.adresse,
                            telefon=excluded.telefon,
                            fax=excluded.fax,
                            rechnungsnummer=excluded.rechnungsnummer,
                            gesellschaftsform=excluded.gesellschaftsform
                                          """, (st.session_state.user, firmenname, adresse, telefon, fax, standard_rechnungsnummer, gesellschaftsform))
                st.success("Firmenprofil gespeichert.")
        with st.expander("Bank- und Registerdaten"):
            st.caption("Diese Daten werden in Rechnungen und offiziellen Dokumenten verwendet.")
            
            iban = st.text_input("IBAN", value=st.session_state.get("iban", ""))
            bic = st.text_input("BIC", value=st.session_state.get("bic", ""))
            bankname = st.text_input("Name der Sparkasse/Bank", value=st.session_state.get("bankname", ""))
            registergericht = st.text_input("Registergericht", value=st.session_state.get("registergericht", ""))
            hrb_nummer = st.text_input("HRB-Nummer", value=st.session_state.get("hrb_nummer", ""))
            ustidnr = st.text_input("USt-IdNr.", value=st.session_state.get("ustidnr", ""))
            geschaeftsfuehrer = st.text_input("Name des Geschäftsführenden", value=st.session_state.get("geschaeftsfuehrer", ""))
            
            if st.button("Bank- und Registerdaten speichern"):
                st.session_state.iban = iban
                st.session_state.bic = bic
                st.session_state.bankname = bankname
                st.session_state.registergericht = registergericht
                st.session_state.hrb_nummer = hrb_nummer
                st.session_state.geschaeftsfuehrer = geschaeftsfuehrer
                st.session_state.ustidnr = ustidnr
                with engine.begin() as conn:
                    conn.exec_driver_sql("""
                        UPDATE firmenprofil SET
                            iban = %s,
                            bic = %s,
                            bankname = %s,
                            registergericht = %s,
                            hrb_nummer = %s,
                            geschaeftsfuehrer = %s,
                            ustidnr = %s
                        WHERE benutzername = %s
                    """, (iban, bic, bankname, registergericht, hrb_nummer, geschaeftsfuehrer, ustidnr, st.session_state.user))
                st.success("Bank- und Registerdaten gespeichert.")
        with st.expander("Firmenlogo hochladen"):
            logo_file = st.file_uploader("Logo (PNG/JPG)", type=["png", "jpg", "jpeg"], key="logo_upload")
            if logo_file:
                logo_bytes = logo_file.read()
                st.session_state.firmenlogo = logo_bytes
                # Optional: Logo als Datei speichern
                logo_path = f"logo_{st.session_state.user}.png"
                with open(logo_path, "wb") as f:
                    f.write(logo_bytes)
                # Save logo in DB
                with engine.begin() as conn:
                    conn.exec_driver_sql("""
                        UPDATE firmenprofil SET logo = %s WHERE benutzername = %s
                    """, (logo_bytes, st.session_state.user))
                st.image(logo_bytes, caption="Vorschau Firmenlogo", use_column_width=False)
                st.success("Logo gespeichert. Es wird in der Rechnung angezeigt.")
            else:
                # Try to load logo from DB if not in session_state
                if not st.session_state.get("firmenlogo"):
                    df_logo = pd.read_sql("SELECT logo FROM firmenprofil WHERE benutzername = %s", engine, params=(st.session_state.user,))
                    if not df_logo.empty and df_logo["logo"].iloc[0]:
                        st.session_state.firmenlogo = df_logo["logo"].iloc[0]
                if st.session_state.get("firmenlogo"):
                    st.image(st.session_state.firmenlogo, caption="Aktuelles Firmenlogo", use_column_width=False)
                else:
                    st.info("Kein Logo hochgeladen. Es wird der Firmenname angezeigt.")
        
        # === NEW: AGB & Datenschutz Expander ===
        with st.expander("AGB & Datenschutz"):
            st.caption("Hier können Sie Ihre akzeptierten Rechtsdokumente einsehen und herunterladen.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                try:
                    with open("AGB.md", "r", encoding="utf-8") as f:
                        agb_text = f.read()
                    st.download_button(
                        "📥 AGB herunterladen",
                        agb_text,
                        file_name="AGB.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                except:
                    st.error("AGB nicht verfügbar")
            
            with col2:
                try:
                    with open("DATENSCHUTZ.md", "r", encoding="utf-8") as f:
                        ds_text = f.read()
                    st.download_button(
                        "📥 Datenschutz herunterladen",
                        ds_text,
                        file_name="DATENSCHUTZ.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                except:
                    st.error("Datenschutz nicht verfügbar")
        
        with st.expander("Archiv"):
            if st.button("Bericht-Archiv öffnen"):
                st.session_state.page = "berichtarchiv"
                st.rerun()
            if st.button("Rechnungs-Archiv öffnen"):
                st.session_state.page = "rechnungarchiv"
                st.rerun()
            with st.expander("Lohnübersicht Archiv"):
                import calendar
                aktuelles_jahr = datetime.now().year
                aktueller_monat = datetime.now().month
                monate = list(range(1, 13))
                monat = st.selectbox("Monat", monate, index=aktueller_monat-1, format_func=lambda m: calendar.month_name[m], key="archiv_lohn_monat")
                jahr = st.number_input("Jahr", min_value=2020, max_value=aktuelles_jahr+1, value=aktuelles_jahr, step=1, key="archiv_lohn_jahr")
                # Retrieve the last created payroll PDF for the selected month/year
                monat_str = f"{monat:02d}"
                jahr_str = str(jahr)
                df_archiv = pd.read_sql(
                    "SELECT * FROM lohnabrechnung_archiv WHERE monat = %s AND jahr = %s AND benutzername = %s ORDER BY erstellt_am DESC LIMIT 1",
                    engine, params=(int(monat), int(jahr), st.session_state.user)
                )
                if not df_archiv.empty:
                    pdf_bytes = df_archiv["pdf_data"].iloc[0]
                    # Convert memoryview to bytes if necessary
                    if isinstance(pdf_bytes, memoryview):
                        pdf_bytes = bytes(pdf_bytes)
                    erstellt_am = df_archiv["erstellt_am"].iloc[0]
                    st.markdown(f"**Letzte Lohnübersicht für {calendar.month_name[monat]} {jahr}:**")
                    st.markdown(f"Erstellt am: {erstellt_am}")
                    st.download_button(
                        "📥 Lohnübersicht als PDF herunterladen",
                        data=pdf_bytes,
                        file_name=f"Lohnübersicht_{jahr}_{monat}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.info(f"Keine Lohnübersicht für {calendar.month_name[monat]} {jahr} im Archiv gefunden.")
    # Neuer Button für Standardgehalt
        with st.expander("Standardgehalt für Mitarbeiter festlegen"):    
            if st.button("Standardgehalt für Mitarbeiter"):
                st.session_state.page = "standardgehalt"
                st.rerun()
        if st.session_state.get("nutzer_typ") == "bauunternehmer":
            with st.expander("Konto löschen"):
                if st.button("Konto löschen"):
                    st.session_state.page = "delete_account_password"
                    st.rerun()   
        st.markdown("---")
        st.button("Zurück zur App", on_click=lambda: st.session_state.update(page="app"))
        
