# ============================================================
#  pages/dev.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.dev import dev_auth_page, dev_test_accounts_page, dev_page
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
)
from ui.login import hash_password, verify_password

def dev_auth_page():
    """Developer Authentication Page - Passwort-Check zum Zugriff auf Dev-Page"""
    st.set_page_config(page_title="Developer Auth", layout="centered")
    st.title("🔐 Developer-Authentifizierung")
    
    st.markdown("---")
    st.info("Geben Sie das Developer-Passwort ein, um auf den Developer-Bereich zuzugreifen.")
    
    dev_password = st.text_input("Developer-Passwort", type="password", placeholder="Passwort eingeben")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Zugriff gewähren"):
            if dev_password == "45":  # Dev-Passwort
                st.session_state.dev_authenticated = True
                st.session_state.page = "dev_page"
                st.success("✅ Authentifizierung erfolgreich!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Passwort ist falsch!")
    
    with col2:
        if st.button("← Zurück zur App"):
            st.session_state.page = "login"
            st.rerun()


# === Test Accounts Management Page (DEPRECATED - now integrated into dev_page) ===


def dev_test_accounts_page():
    """Redirect to dev_page - Test-Konten-Verwaltung ist jetzt dort integriert"""
    st.session_state.page = "dev"
    st.rerun()


# === Developer Page ===


def dev_page():
    """Developer Debug Page"""
    st.set_page_config(page_title="Developer Debug", layout="centered")
    st.title("Developer-Debug")
    if st.button("← Zurück"):
        st.session_state.page = "login"
        st.rerun()
    
    st.markdown("---")
    
    # === EXPANDER 1: TEST-KONTO VERWALTUNG ===
    with st.expander("➕ Test-Konten erstellen und verwalten", expanded=True):
        st.markdown("#### Neues Test-Konto erstellen")
        st.info("Test-Konten haben vollen Zugriff ohne PayPal-Zahlung und verfallen nach der angegebenen Zeit.")
        
        col1, col2 = st.columns(2)
        with col1:
            test_username = st.text_input("Benutzername für Test-Konto", placeholder="z.B. test_kunde_001", key="test_user")
        with col2:
            test_email = st.text_input("E-Mail (optional)", placeholder="test@beispiel.de", key="test_email")
        
        test_password = st.text_input("Passwort", type="password", placeholder="Min. 8 Zeichen", value="TestPass123!", key="test_pass")
        
        col_duration1, col_duration2 = st.columns(2)
        with col_duration1:
            duration_option = st.radio("Test-Dauer:", ["24 Stunden", "7 Tage"], horizontal=True, key="test_duration_radio")
        
        test_duration = 24 if duration_option == "24 Stunden" else 168
        
        if st.button("✅ Test-Konto erstellen", key="create_test_account"):
            # Validierung
            if not test_username or len(test_password) < 8:
                st.error("Benutzername und Passwort (min. 8 Zeichen) erforderlich!")
            else:
                # Prüfen ob bereits vorhanden
                existing = pd.read_sql(
                    "SELECT * FROM benutzer WHERE benutzername = %s",
                    engine,
                    params=(test_username,)
                )
                
                if not existing.empty:
                    st.error(f"Benutzername '{test_username}' existiert bereits!")
                else:
                    try:
                        hashed_password = hash_password(test_password)
                        expiration_time = datetime.now() + timedelta(hours=test_duration)
                        
                        with engine.begin() as conn:
                            result = conn.exec_driver_sql(
                                "SELECT COALESCE(MAX(account_id), 0) + 1 as next_id FROM benutzer"
                            ).fetchone()
                            next_account_id = result[0] if result else 1
                            
                            conn.exec_driver_sql(
                                """INSERT INTO benutzer 
                                   (account_id, benutzername, passwort, email, payment_status, is_test_account, test_expiration_time, test_duration_hours, agb_accepted, datenschutz_accepted, agb_accepted_at, datenschutz_accepted_at) 
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                (next_account_id, test_username, hashed_password, test_email or None, "ACTIVE", True, expiration_time, test_duration, True, True, datetime.now(), datetime.now())
                            )
                        
                        st.success(f"✅ Test-Konto erstellt!")
                        st.info(f"**Benutzername:** {test_username}")
                        st.info(f"**Passwort:** {test_password}")
                        st.info(f"**Verfällt:** {expiration_time.strftime('%d.%m.%Y %H:%M:%S')} ({test_duration}h)")
                        st.warning(f"Nach dieser Zeit wird das Konto automatisch deaktiviert!")
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Fehler beim Erstellen des Kontos: {str(e)}")
        
        st.markdown("---")
        st.markdown("#### Aktive Test-Konten")
        
        try:
            df_test = pd.read_sql(
                """SELECT 
                    benutzername, 
                    email, 
                    registration_timestamp,
                    test_expiration_time
                FROM benutzer 
                WHERE is_test_account = TRUE
                ORDER BY test_expiration_time DESC""",
                engine
            )
            
            if df_test.empty:
                st.info("Keine aktiven Test-Konten vorhanden.")
            else:
                # Tabelle mit HTML für bessere Formatierung
                table_html = """
                <style>
                .test-table {
                    width: 100%;
                    border-collapse: collapse;
                    background: var(--box-bg);
                    border: 1px solid var(--box-border);
                    border-radius: 8px;
                    overflow: hidden;
                }
                .test-table th, .test-table td {
                    padding: 12px;
                    border: 1px solid var(--box-border);
                    text-align: left;
                }
                .test-table th {
                    background: var(--table-header-bg);
                    font-weight: 600;
                    color: var(--text-color);
                }
                .test-table tbody tr:hover {
                    background: rgba(255,255,255,0.05);
                }
                .status-active { color: #4CAF50; font-weight: bold; }
                .status-expiring { color: #FF9800; font-weight: bold; }
                .status-expired { color: #F44336; font-weight: bold; }
                </style>
                <table class="test-table">
                <thead>
                <tr>
                    <th>Benutzername</th>
                    <th>E-Mail</th>
                    <th>Verfällt am</th>
                    <th>Verbleibend</th>
                    <th>Status</th>
                </tr>
                </thead>
                <tbody>
                """
                
                now = datetime.now()
                
                for _, row in df_test.iterrows():
                    expiration = row['test_expiration_time']
                    if isinstance(expiration, str):
                        expiration = pd.to_datetime(expiration)
                    
                    remaining = expiration - now
                    hours_remaining = remaining.total_seconds() / 3600
                    
                    expiration_str = expiration.strftime("%d.%m.%Y %H:%M")
                    
                    if hours_remaining > 0:
                        remaining_str = f"{int(hours_remaining)}h {int((hours_remaining % 1) * 60)}m"
                        if hours_remaining > 12:
                            status = '<span class="status-active">✅ Aktiv</span>'
                        else:
                            status = '<span class="status-expiring">⚠️ Läuft bald ab</span>'
                    else:
                        remaining_str = "Abgelaufen"
                        status = '<span class="status-expired">❌ Verfallen</span>'
                    
                    table_html += f"""
                    <tr>
                        <td><strong>{row['benutzername']}</strong></td>
                        <td>{row['email'] or '-'}</td>
                        <td>{expiration_str}</td>
                        <td>{remaining_str}</td>
                        <td>{status}</td>
                    </tr>
                    """
                
                table_html += "</tbody></table>"
                st.markdown(table_html, unsafe_allow_html=True)
        
        except Exception as e:
            st.error(f"Fehler beim Laden der Test-Konten: {str(e)}")
    
    # === EXPANDER 2: STATISTIKEN ===
    with st.expander("📊 System-Statistiken", expanded=True):
        try:
            # Anzahl Bauunternehmer (distinct benutzername mit Projekten)
            count_bauunternehmer = pd.read_sql(
                "SELECT COUNT(DISTINCT benutzername) as count FROM projekte",
                engine
            )["count"].iloc[0]
            
            # Anzahl Test-Konten (is_test_account column doesn't exist yet)
            count_test_accounts = 0
            
            # Anzahl Bauunternehmer mit Abo (payment_status = PAID)
            count_abo_bezahlte = pd.read_sql(
                "SELECT COUNT(*) as count FROM benutzer WHERE payment_status = 'PAID'",
                engine
            )["count"].iloc[0]
            
            # Anzahl Mitarbeiter-Konten
            count_mitarbeiter = pd.read_sql(
                "SELECT COUNT(DISTINCT benutzername) as count FROM mitarbeiter",
                engine
            )["count"].iloc[0]
            
            # Anzahl Projekte
            count_projekte = pd.read_sql(
                "SELECT COUNT(DISTINCT id) as count FROM projekte",
                engine
            )["count"].iloc[0]
            
            # Metriken anzeigen
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Abo-bezahlte", count_abo_bezahlte)
            
            with col2:
                st.metric("Test-Konten", count_test_accounts)
            
            with col3:
                st.metric("Mitarbeiter-Konten", count_mitarbeiter)
            
            with col4:
                st.metric("Projekte", count_projekte)
            
            st.markdown("---")
            
            # Detaillierte Übersicht
            st.markdown("#### Detaillierte Übersicht")
            
            col_top, col_bottom = st.columns(2)
            
            with col_top:
                st.markdown("**Bauunternehmer mit Abo (Letzte 10)**")
                df_bu = pd.read_sql(
                    """SELECT benutzername, email, payment_status, payment_timestamp, subscription_start_date
                       FROM benutzer 
                       WHERE payment_status = 'PAID'
                       ORDER BY subscription_start_date DESC 
                       LIMIT 10""",
                    engine
                )
                
                if not df_bu.empty:
                    st.dataframe(df_bu, use_container_width=True, hide_index=True)
                else:
                    st.info("Keine Bauunternehmer mit Abo vorhanden.")
            
            with col_bottom:
                st.markdown("**Projekte (Aktiv)**")
                df_proj = pd.read_sql(
                    """SELECT benutzername, name as Projektname, created_at
                       FROM projekte 
                       ORDER BY created_at DESC 
                       LIMIT 10""",
                    engine
                )
                
                if not df_proj.empty:
                    st.dataframe(df_proj, use_container_width=True, hide_index=True)
                else:
                    st.info("Keine Projekte vorhanden.")
        
        except Exception as e:
            st.error(f"Fehler beim Laden der Statistiken: {str(e)}")
    
    # === EXPANDER 3: ALLE BAUUNTERNEHMER ===
    with st.expander("👥 Alle Bauunternehmer (Übersicht)", expanded=True):
        try:
            # Alle Bauunternehmer (Benutzer die Projekte haben)
            df_all_bu = pd.read_sql(
                """SELECT DISTINCT b.benutzername, b.email, b.payment_status, b.subscription_start_date
                   FROM benutzer b
                   WHERE b.benutzername IN (SELECT DISTINCT benutzername FROM projekte)
                   ORDER BY b.subscription_start_date DESC""",
                engine
            )
            
            if not df_all_bu.empty:
                st.markdown("#### Alle registrierten Bauunternehmer")
                st.dataframe(df_all_bu, use_container_width=True, hide_index=True)
                st.info(f"**Gesamt:** {len(df_all_bu)} Bauunternehmer registriert")
            else:
                st.info("Keine Bauunternehmer vorhanden.")
        
        except Exception as e:
            st.error(f"Fehler beim Laden der Bauunternehmer: {str(e)}")

# === Delete Account Confirmation ===


