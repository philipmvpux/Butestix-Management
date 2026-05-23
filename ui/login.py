import hashlib
import json
import time
import streamlit as st
import pandas as pd
import bcrypt

from pathlib import Path
from datetime import datetime
from database import(
engine,
ensure_schema,
)
from ui.helpers import (  
    GESELLSCHAFTSFORMEN
)
# Pfad zur Hauptdatei (für .login_security-Ordner)
BASE_DIR = Path(__file__).resolve().parent.parent
def show_login_page():
    """Login page for bauunternehmen app"""
    st.set_page_config(page_title="Login", layout="centered")
    
    # === KUNDENVERSION: Verstecke Streamlit Buttons ===
    st.markdown("""
    <style>
        [data-testid="stToolbar"] { display: none !important; }
        button[kind="header"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Login")
    
    # Colorless/standard buttons for login page (exclude from global magenta/yellow buttons)
    st.markdown("""
    <style>
        /* Override ALL buttons on login page to be neutral */
        button {
            background-color: transparent !important;
            background-image: none !important;
            color: #333333 !important;
            border: 1px solid #e0e0e0 !important;
            box-shadow: none !important;
            outline: none !important;
        }
        button:hover {
            background-color: rgba(0,0,0,0.04) !important;
            background-image: none !important;
            color: #333333 !important;
        }
        button:focus {
            background-color: transparent !important;
            background-image: none !important;
            color: #333333 !important;
            outline: none !important;
            box-shadow: none !important;
        }
        button:active {
            background-color: transparent !important;
            background-image: none !important;
            color: #333333 !important;
            outline: none !important;
            box-shadow: none !important;
        }
        button p, button span, button div {
            color: #333333 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    
    login_typ = st.radio("Login als", ["Bauunternehmer", "Mitarbeiter"])
    if login_typ == "Bauunternehmer":
        modus = st.radio("Was möchtest du tun?", ["Login", "Konto erstellen"], horizontal=True)
        if modus == "Login":
            # === LOGIN SECURITY CHECK ===
            device_id = get_device_id()
            is_locked_standard, lock_msg_standard = check_login_lockout(device_id, "bauunternehmer")
            is_locked_dev, lock_msg_dev = check_login_lockout(device_id, "dev")
            
            # Zeige Lockout-Warnung falls aktiv
            if is_locked_standard or is_locked_dev:
                st.error(f"{lock_msg_standard or lock_msg_dev}")
                st.stop()
            
            with st.form("login_formular"):
                benutzer = st.text_input("Benutzername")
                passwort = st.text_input("Passwort", type="password")
                login = st.form_submit_button("Einloggen")
            if login:
                # Dev-Login Check (doppelt geschützt: eigener Lockout für Dev-Accounts)
                if benutzer == "Philip" and passwort == "091009":
                    reset_login_attempts(device_id, "dev")
                    st.session_state["page"] = "dev_auth"
                    st.success("Developer Login erfolgreich")
                    st.rerun()
                    return  # Wichtig: Beende die Funktion hier
                elif benutzer == "Philip" and passwort != "091009":
                    # Dev-Login fehlgeschlagen - zähle unter "dev" Login-Versuche
                    record_failed_login(device_id, "dev")
                    is_locked, msg = check_login_lockout(device_id, "dev")
                    st.error("Dev-Passwort falsch.")
                    if is_locked:
                        st.error(f"{msg}")
                    st.stop()
                
                # Standard Login
                try:
                    # Verify user credentials - tables already created by ensure_schema()
                    
                    # Now try to find the user
                    df_users = pd.read_sql("""
                        SELECT benutzername, passwort, account_id, email, payment_status, agb_accepted, datenschutz_accepted
                        FROM benutzer 
                        WHERE benutzername = %s
                    """, engine, params=(benutzer,))
                    
                    
                    if not df_users.empty:
                        stored_password = df_users.iloc[0]["passwort"]
                        if verify_password(passwort, stored_password):
                            # ✅ PASSWORD KORREKT - Prüfe Test-Konto Status
                            # Note: These columns may not exist in DB yet, use defaults
                            is_test_account = False
                            test_expiration_time = None
                            
                            # Prüfe ob Test-Konto abgelaufen ist
                            if is_test_account and test_expiration_time:
                                expiration = test_expiration_time
                                if isinstance(expiration, str):
                                    expiration = pd.to_datetime(expiration)
                                
                                if datetime.now() > expiration:
                                    st.error(f"❌ Test-Konto abgelaufen!")
                                    st.info(f"Dieses Test-Konto ist am {expiration.strftime('%d.%m.%Y %H:%M:%S')} abgelaufen.")
                                    st.stop()
                            
                            # ✅ LOGIN ERFOLGREICH - Reset login attempts
                            reset_login_attempts(device_id, "bauunternehmer")
                            
                            # Upgrade password if it's not hashed
                            with engine.begin() as conn:
                                upgrade_password_if_needed(conn, "benutzer", "benutzername", "passwort", benutzer, passwort)
                            
                            # Set session state
                            st.session_state.user = benutzer
                            st.session_state.account_id = int(df_users.iloc[0]["account_id"])
                            st.session_state.nutzer_typ = "bauunternehmer"
                            st.session_state.email = df_users.iloc[0]["email"]
                            # Load and apply user's theme immediately after login
                            try:
                                df_theme = pd.read_sql("SELECT theme FROM benutzer WHERE benutzername = %s", engine, params=(benutzer,))
                                if not df_theme.empty and pd.notnull(df_theme['theme'].iloc[0]):
                                    st.session_state['theme'] = df_theme['theme'].iloc[0]
                                else:
                                    st.session_state.setdefault('theme', 'white')
                            except Exception:
                                st.session_state.setdefault('theme', 'white')
                            
                            # Apply theme CSS immediately
                            if st.session_state.get('theme') == 'dark':
                                st.markdown("""
                                <style>
                                    * {
                                        background-color: #1a1a1a !important;
                                        color: #ffffff !important;
                                        border-color: #333333 !important;
                                    }
                                    body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stForm"] {
                                        background-color: #1a1a1a !important;
                                        color: #ffffff !important;
                                    }
                                    input, textarea, select, [role="textbox"], [role="option"] {
                                        background-color: #2d2d2d !important;
                                        color: #ffffff !important;
                                        border-color: #444444 !important;
                                    }
                                    .stTextInput > div, .stNumberInput > div, .stSelectbox > div, .stTextArea > div {
                                        background-color: #2d2d2d !important;
                                    }
                                    button, [role="button"] {
                                        background-color: #333333 !important;
                                        color: #ffffff !important;
                                        border-color: #555555 !important;
                                    }
                                    .stDataFrame, table {
                                        background-color: #1a1a1a !important;
                                        color: #ffffff !important;
                                    }
                                </style>
                                """, unsafe_allow_html=True)
                            # payment_status immer frisch aus der DB laden
                            with engine.begin() as conn:
                                status_row = conn.exec_driver_sql(
                                    "SELECT payment_status, paypal_subscription_id FROM benutzer WHERE benutzername = %s",
                                    (benutzer,)
                                ).fetchone()
                                payment_status = status_row[0] if status_row else None
                                subscription_id = status_row[1] if status_row else None
                                

                                
                                st.session_state.payment_status = payment_status
                            
                            # Load company data
                            lade_firmendaten()
                            
                            # ✅ Lade AGB-Status aus DB UND speichere in Session State
                            agb_accepted = df_users.iloc[0].get("agb_accepted", False)
                            datenschutz_accepted = df_users.iloc[0].get("datenschutz_accepted", False)
                            
                            # Speichere in Session State für später
                            st.session_state.agb_accepted = agb_accepted
                            st.session_state.datenschutz_accepted = datenschutz_accepted
                            
                            # Prüfe ob AGB akzeptiert wurden - PRIORITY: BEFORE everything else
                            if not agb_accepted:
                                # AGB nicht akzeptiert - zur AGB-Acceptance-Seite
                                st.session_state.page = "agb_akzeptieren"
                                st.session_state.login_attempted = True
                                st.rerun()
                            
                            # ✅ Prüfe Payment-Status ZUERST (vor Firmenprofil)
                            if payment_status != "ACTIVE":
                                # Payment nicht aktiv - zur Payment-Seite
                                st.session_state.page = "payment"
                                st.session_state.login_attempted = True
                                st.warning(f"⏳ Login erfolgreich. Status: {payment_status} - Weiterleitung zum Payment-Screen...")
                                st.rerun()
                            
                            # ✅ Prüfe ob Firmenprofil-Daten vollständig sind (nach Payment-Check)
                            required_fields = {
                                "firmenname": "Firmenname",
                                "gesellschaftsform": "Gesellschaftsform",
                                "firmenadresse": "Adresse",
                                "firmentelefon": "Telefon",
                                "standard_rechnungsnummer": "Rechnungsnummer"
                            }
                            missing_fields = [field for field in required_fields.keys() if not st.session_state.get(field)]
                            
                            if missing_fields:
                                # Firmendaten unvollständig - zur Setup-Seite
                                st.session_state.page = "setup_company_profile"
                                st.session_state.login_attempted = True
                                st.rerun()
                            else:
                                # Alles OK - zur App
                                st.session_state.page = "app"
                                st.session_state.login_attempted = True
                                st.success("Login erfolgreich. Weiterleitung zur Anwendung...")
                                st.rerun()
                        else:
                            # ❌ LOGIN FEHLGESCHLAGEN - Zähle Versuch
                            record_failed_login(device_id, "bauunternehmer")
                            attempt_data = load_login_attempts()
                            device_key = f"{device_id}_bauunternehmer"
                            failed_count = attempt_data.get(device_key, {}).get('failed_attempts', 0)
                            
                            remaining_attempts = 3 - failed_count
                            if remaining_attempts > 0:
                                st.error(f"Benutzername oder Passwort falsch. Noch {remaining_attempts} Versuche übrig.")
                            else:
                                # Lockout aktiv
                                is_locked, lock_msg = check_login_lockout(device_id, "bauunternehmer")
                                st.error(f"{lock_msg}")
                    else:
                        # ❌ USER NICHT GEFUNDEN - Zähle trotzdem als Versuch (verhindert Username-Enumeration)
                        record_failed_login(device_id, "bauunternehmer")
                        attempt_data = load_login_attempts()
                        device_key = f"{device_id}_bauunternehmer"
                        failed_count = attempt_data.get(device_key, {}).get('failed_attempts', 0)
                        
                        remaining_attempts = 3 - failed_count
                        if remaining_attempts > 0:
                            st.error(f"Benutzername oder Passwort falsch. Noch {remaining_attempts} Versuche übrig.")
                        else:
                            is_locked, lock_msg = check_login_lockout(device_id, "bauunternehmer")
                            st.error(f"{lock_msg}")
                except Exception as e:
                    st.error(f"Fehler beim Login: {str(e)}")
                    st.error("Bitte versuchen Sie es erneut oder kontaktieren Sie den Support.")

        elif modus == "Konto erstellen":
            st.subheader("Registrierungsformular")
            
            # === EINFACHES REGISTRIERUNGSFORMULAR OHNE AGB/DATENSCHUTZ ===
            with st.form("register_formular"):
                neuer_benutzer = st.text_input("Neuer Benutzername", help="Eindeutiger Benutzername")
                email = st.text_input("E-Mail Adresse", 
                                    placeholder="name@beispiel.de",
                                    type="default",
                                    help="Gültige E-Mail Adresse erforderlich")
                neues_passwort = st.text_input("Passwort", type="password", 
                                              help="Mindestens 8 Zeichen")
                
                registrieren = st.form_submit_button("Konto erstellen")
            
            if registrieren:
                # Whitespace entfernen
                neuer_benutzer = neuer_benutzer.strip()
                neues_passwort = neues_passwort.strip()
                email = email.strip()
                
                # ✅ VALIDIERUNG: Alle Felder gefüllt
                if not neuer_benutzer:
                    st.error("Benutzername erforderlich")
                    st.stop()
                
                if len(neues_passwort) < 8:
                    st.error("Das Passwort muss mindestens 8 Zeichen lang sein.")
                    st.stop()
                
                if not "@" in email or not "." in email:
                    st.error("Bitte geben Sie eine gültige E-Mail Adresse ein.")
                    st.stop()
                
                # Prüfen ob Benutzer existiert
                existing = pd.read_sql("SELECT * FROM benutzer WHERE benutzername = %s OR email = %s",
                                     engine, params=(neuer_benutzer, email))
                if not existing.empty:
                    if neuer_benutzer in existing["benutzername"].values:
                        st.error("⚠️ Benutzername existiert bereits.")
                    else:
                        st.error("Diese E-Mail Adresse wird bereits verwendet.")
                else:
                    # Hash the password before storing
                    hashed_password = hash_password(neues_passwort)
                    next_account_id = None
                    
                    try:
                        # Speichere Benutzer OHNE AGB/Datenschutz-Akzeptanz
                        from datetime import datetime
                        
                        with engine.begin() as conn:
                            result = conn.exec_driver_sql("SELECT COALESCE(MAX(account_id), 0) + 1 as next_id FROM benutzer").fetchone()
                            next_account_id = result[0] if result else 1
                            
                            # Insert new user - NUR die grundlegenden Felder
                            conn.exec_driver_sql(
                                """INSERT INTO benutzer 
                                   (benutzername, passwort, account_id, email) 
                                   VALUES (%s, %s, %s, %s)""",
                                (neuer_benutzer, hashed_password, next_account_id, email)
                            )
                        
                        st.success("Konto erfolgreich erstellt!")
                        
                        # Set session state für AGB-Akzeptanz-Seite
                        if next_account_id:
                            st.session_state.user = neuer_benutzer
                            st.session_state.account_id = next_account_id
                            st.session_state.nutzer_typ = "bauunternehmer"
                            st.session_state.email = email
                            st.session_state.payment_status = "PENDING"
                            
                            # redirect auf AGB-Akzeptanz-Seite (NICHT direkt zu payment!)
                            st.session_state.page = "agb_akzeptieren"
                            st.rerun()
                    except Exception as e:
                        error_msg = str(e)
                        if "unique" in error_msg.lower():
                            st.error(f"Dieser Benutzername oder diese E-Mail existiert bereits.")
                        elif "connection" in error_msg.lower():
                            st.error(f"Datenbankverbindung fehlgeschlagen. Bitte später versuchen.")
                        else:
                            st.error(f"Fehler beim Erstellen des Kontos: {error_msg[:100]}")
                        st.info("Bitte versuchen Sie es später erneut oder kontaktieren Sie den Support.")
    elif login_typ == "Mitarbeiter":
        # === LOGIN SECURITY CHECK ===
        device_id = get_device_id()
        is_locked, lock_msg = check_login_lockout(device_id, "mitarbeiter")
        
        if is_locked:
            st.error(f"{lock_msg}")
            st.stop()
        
        with st.form("mitarbeiter_login_formular"):
            benutzer = st.text_input("Mitarbeitername")
            passwort = st.text_input("Passwort", type="password")
            login = st.form_submit_button("Einloggen")
        if login:    
            # Get stored password hash
            df = pd.read_sql("SELECT * FROM mitarbeiter WHERE benutzername = %s", engine, params=(benutzer,))
            if not df.empty:
                stored_password = df.iloc[0]["passwort"]
                if verify_password(passwort, stored_password):
                    # ✅ LOGIN ERFOLGREICH - Reset login attempts
                    reset_login_attempts(device_id, "mitarbeiter")
                    
                    # Upgrade password if it's not hashed
                    with engine.begin() as conn:
                        upgrade_password_if_needed(conn, "mitarbeiter", "benutzername", "passwort", benutzer, passwort)
                    # Get all assigned projects
                    df_projekte = pd.read_sql("""
                        SELECT p.id, p.name 
                        FROM mitarbeiter_projekte mp 
                        JOIN projekte p ON mp.projekt_id = p.id 
                        WHERE mp.mitarbeiter_benutzername = %s
                    """, engine, params=(benutzer,))
                    
                    st.session_state.user = benutzer
                    # account_id für Mitarbeiter (nutze 0 als Fallback wenn nicht gesetzt)
                    account_id_val = df.iloc[0].get("account_id")
                    st.session_state.account_id = int(account_id_val) if pd.notna(account_id_val) else 0
                    st.session_state.nutzer_typ = "mitarbeiter"
                    
                    if df_projekte.empty:
                        st.error("Keine Projekte zugewiesen. Bitte kontaktieren Sie Ihren Vorgesetzten.")
                        return
                    # Alle Mitarbeiter gehen direkt zu Projektauswahl-Seite
                    st.session_state.page = "mitarbeiter_projekt_auswahl"
                    
                    st.success("Login erfolgreich.")
                    st.rerun()
                    return  # Wichtig: Beende die Funktion hier
                else:
                    # ❌ LOGIN FEHLGESCHLAGEN - Zähle Versuch
                    record_failed_login(device_id, "mitarbeiter")
                    attempt_data = load_login_attempts()
                    device_key = f"{device_id}_mitarbeiter"
                    failed_count = attempt_data.get(device_key, {}).get('failed_attempts', 0)
                    
                    remaining_attempts = 3 - failed_count
                    if remaining_attempts > 0:
                        st.error(f"Mitarbeitername oder Passwort falsch. Noch {remaining_attempts} Versuche übrig.")
                    else:
                        is_locked, lock_msg = check_login_lockout(device_id, "mitarbeiter")
                        st.error(f"{lock_msg}")
            else:
                # ❌ USER NICHT GEFUNDEN - Zähle trotzdem als Versuch
                record_failed_login(device_id, "mitarbeiter")
                attempt_data = load_login_attempts()
                device_key = f"{device_id}_mitarbeiter"
                failed_count = attempt_data.get(device_key, {}).get('failed_attempts', 0)
                
                remaining_attempts = 3 - failed_count
                if remaining_attempts > 0:
                    st.error(f"Mitarbeitername oder Passwort falsch. Noch {remaining_attempts} Versuche übrig.")
                else:
                    is_locked, lock_msg = check_login_lockout(device_id, "mitarbeiter")
                    st.error(f"{lock_msg}")
def lade_firmendaten():
    result = pd.read_sql("SELECT * FROM firmenprofil WHERE benutzername = %s", engine, params=(st.session_state.user,))
    if not result.empty:
        st.session_state.firmenname = result["firmenname"].iloc[0] if "firmenname" in result else ""
        st.session_state.firmenadresse = result["adresse"].iloc[0] if "adresse" in result else ""
        st.session_state.firmentelefon = result["telefon"].iloc[0] if "telefon" in result else ""
        st.session_state.firmenfax = result["fax"].iloc[0] if "fax" in result else ""
        st.session_state.gesellschaftsform = result["gesellschaftsform"].iloc[0] if "gesellschaftsform" in result else GESELLSCHAFTSFORMEN[0]
        st.session_state.iban = result["iban"].iloc[0] if "iban" in result else ""
        st.session_state.bic = result["bic"].iloc[0] if "bic" in result else ""
        st.session_state.bankname = result["bankname"].iloc[0] if "bankname" in result else ""
        st.session_state.registergericht = result["registergericht"].iloc[0] if "registergericht" in result else ""
        st.session_state.hrb_nummer = result["hrb_nummer"].iloc[0] if "hrb_nummer" in result else ""
        st.session_state.geschaeftsfuehrer = result["geschaeftsfuehrer"].iloc[0] if "geschaeftsfuehrer" in result else ""
        st.session_state.ustidnr = result["ustidnr"].iloc[0] if "ustidnr" in result else ""
        st.session_state.standard_rechnungsnummer = int(result["rechnungsnummer"].iloc[0]) if "rechnungsnummer" in result and pd.notnull(result["rechnungsnummer"].iloc[0]) else 100
    else:
        st.session_state.firmenname = ""
        st.session_state.firmenadresse = ""
        st.session_state.firmentelefon = ""
        st.session_state.firmenfax = ""
        st.session_state.gesellschaftsform = GESELLSCHAFTSFORMEN[0]
        st.session_state.iban = ""
        st.session_state.bic = ""
        st.session_state.bankname = ""
        st.session_state.registergericht = ""
        st.session_state.hrb_nummer = ""
        st.session_state.geschaeftsfuehrer = ""
        st.session_state.ustidnr = ""
        st.session_state.standard_rechnungsnummer = 100
# --- Password hashing functions ---
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Convert the password string to bytes and generate a salt
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    # Hash the password with the salt
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return the hashed password as a string
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    try:
        # Handle both hashed and unhashed passwords for backward compatibility
        if hashed_password.startswith('$2'):  # bcrypt hash starts with $2
            # Convert both to bytes for comparison
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hashed_bytes)
        else:
            # For legacy passwords, do direct comparison
            return password == hashed_password
    except Exception:
        # If any error occurs during verification, do direct comparison as fallback
        return password == hashed_password

def upgrade_password_if_needed(conn, table: str, username_field: str, password_field: str, username: str, password: str):
    """Upgrade an unhashed password to a hashed one if needed."""
    # Get current password hash
    result = conn.exec_driver_sql(
        f"SELECT {password_field} FROM {table} WHERE {username_field} = %s",
        (username,)
    ).fetchone()
    
    if result and result[0]:
        current_hash = result[0]
        # If current password is not hashed (doesn't start with $2), upgrade it
        if not current_hash.startswith('$2'):
            hashed = hash_password(password)
            conn.exec_driver_sql(
                f"UPDATE {table} SET {password_field} = %s WHERE {username_field} = %s",
                (hashed, username)
            )

   # === LOGIN SECURITY: Device-Level Ban System ===
import hashlib
import json
from pathlib import Path

def get_device_id() -> str:
    """Generate a unique device ID based on Streamlit session."""
    # Nutze Streamlit Session ID als Device-Identifier
    device_id = st.session_state.get('_device_id')
    if not device_id:
        # Fallback: Nutze einen eindeutigen Hash basierend auf Browser-Info
        device_id = hashlib.sha256(str(st.session_state).encode()).hexdigest()[:16]
        st.session_state['_device_id'] = device_id
    return device_id

def get_login_attempts_file() -> Path:
    """Get the path to the login attempts file."""
    attempts_dir = Path(BASE_DIR) / ".login_security"
    attempts_dir.mkdir(exist_ok=True)
    return attempts_dir / "login_attempts.json"

def load_login_attempts() -> dict:
    """Load login attempts from file."""
    attempts_file = get_login_attempts_file()
    if attempts_file.exists():
        try:
            with open(attempts_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_login_attempts(attempts: dict):
    """Save login attempts to file."""
    attempts_file = get_login_attempts_file()
    with open(attempts_file, 'w') as f:
        json.dump(attempts, f)

def check_login_lockout(device_id: str, login_type: str) -> tuple[bool, str]:
    """
    Check if device is locked out from login attempts.
    Returns (is_locked, message)
    """
    attempts = load_login_attempts()
    device_key = f"{device_id}_{login_type}"
    
    if device_key not in attempts:
        return False, ""
    
    attempt_data = attempts[device_key]
    failed_attempts = attempt_data.get('failed_attempts', 0)
    last_attempt_time = attempt_data.get('last_attempt_time', 0)
    
    # Berechne Lockout-Zeit: 20s * (2 ^ (attempts - 3))
    if failed_attempts >= 3:
        lockout_duration = 20 * (2 ** (failed_attempts - 3))
        time_since_last = time.time() - last_attempt_time
        
        if time_since_last < lockout_duration:
            remaining = int(lockout_duration - time_since_last)
            return True, f"Zu viele Login-Versuche. Bitte warten Sie {remaining} Sekunde(n)."
    
    return False, ""

def record_failed_login(device_id: str, login_type: str):
    """Record a failed login attempt."""
    attempts = load_login_attempts()
    device_key = f"{device_id}_{login_type}"
    
    if device_key not in attempts:
        attempts[device_key] = {
            'failed_attempts': 0,
            'last_attempt_time': 0
        }
    
    attempts[device_key]['failed_attempts'] += 1
    attempts[device_key]['last_attempt_time'] = time.time()
    
    save_login_attempts(attempts)

def reset_login_attempts(device_id: str, login_type: str):
    """Reset login attempts after successful login."""
    attempts = load_login_attempts()
    device_key = f"{device_id}_{login_type}"
    
    if device_key in attempts:
        del attempts[device_key]
        save_login_attempts(attempts)

