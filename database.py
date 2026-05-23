import os 
import psycopg2
import atexit
import streamlit as st
from urllib.parse import quote
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
load_dotenv()  # Lädt die Umgebungsvariablen aus der .env-Datei
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
PAYPAL_CLIENT_ID     = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_API_BASE      = os.getenv("PAYPAL_API_BASE")
PAYPAL_BASE_URL      = os.getenv("PAYPAL_BASE_URL")
PAYPAL_RETURN_URL    = os.getenv("PAYPAL_RETURN_URL")
PAYPAL_CANCEL_URL    = os.getenv("PAYPAL_CANCEL_URL")
def get_connection():
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,

            client_secret=PAYPAL_CLIENT_SECRET,
            client_id=PAYPAL_CLIENT_ID,
            api_base=PAYPAL_API_BASE,
            base_url=PAYPAL_BASE_URL,
            return_url=PAYPAL_RETURN_URL,
            cancel_url=PAYPAL_CANCEL_URL,

        )

 
# ── Verbindungs-URL ─────────────────────────────────────────
SAFE_PASSWORD = quote(DB_PASSWORD, safe="")
DATABASE_URL = (
    f"postgresql://{DB_USER}:{SAFE_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
 
 
# ── Engine (gecacht von Streamlit, wird nur einmal erstellt) ─
@st.cache_resource
def get_engine():
    """
    Erstellt die SQLAlchemy-Engine einmalig und cached sie.
    Streamlit sorgt dafür, dass sie nicht bei jedem Reload neu gebaut wird.
    """
    _engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=1,        # Minimal: nur 1 Connection
        max_overflow=2,     # Max 3 Connections insgesamt
        pool_pre_ping=True, # Connection vor Nutzung testen
        pool_recycle=600,   # Recyclen nach 10 Minuten
        echo=False,
    )
 
    # Sauber schließen wenn die App beendet wird
    def _cleanup():
        _engine.dispose()
 
    atexit.register(_cleanup)
    return _engine
 
 
# ── Direkt verwendbare engine-Instanz ───────────────────────
engine = get_engine()
def ensure_schema():
    """
    Erstellt alle Tabellen falls sie noch nicht existieren.
    Wird einmal beim App-Start aufgerufen.
    """
 
    def safe_create(name, sql):
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql(sql)
        except Exception as e:
            print(f"Tabelle {name}: {str(e)[:80]}")
 
    def safe_alter(sql):
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql(sql)
        except Exception:
            pass  # Spalte existiert bereits
 
    # ── Tabellen ────────────────────────────────────────────
 
    safe_create("benutzer", """
        CREATE TABLE IF NOT EXISTS benutzer (
            account_id SERIAL PRIMARY KEY,
            benutzername TEXT UNIQUE NOT NULL,
            passwort TEXT NOT NULL,
            email TEXT UNIQUE,
            payment_status TEXT DEFAULT 'PENDING',
            paypal_subscription_id TEXT,
            payment_timestamp TIMESTAMP,
            last_payment_check TIMESTAMP,
            subscription_start_date TIMESTAMP,
            registration_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            theme TEXT DEFAULT 'white',
            agb_accepted BOOLEAN DEFAULT FALSE,
            datenschutz_accepted BOOLEAN DEFAULT FALSE,
            agb_accepted_at TIMESTAMP,
            datenschutz_accepted_at TIMESTAMP,
            is_test_account BOOLEAN DEFAULT FALSE,
            test_expiration_time TIMESTAMP DEFAULT NULL,
            test_duration_hours INTEGER DEFAULT 24
        )
    """)
 
    safe_create("firmenprofil", """
        CREATE TABLE IF NOT EXISTS firmenprofil (
            benutzername TEXT PRIMARY KEY,
            firmenname TEXT,
            adresse TEXT,
            telefon TEXT,
            fax TEXT,
            rechnungsnummer INTEGER,
            gesellschaftsform TEXT,
            logo BYTEA,
            iban TEXT,
            bic TEXT,
            bankname TEXT,
            registergericht TEXT,
            hrb_nummer TEXT,
            geschaeftsfuehrer TEXT,
            ustidnr TEXT,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("projekte", """
        CREATE TABLE IF NOT EXISTS projekte (
            id SERIAL PRIMARY KEY,
            name TEXT,
            projekt_name TEXT,
            budget DECIMAL(10, 2) DEFAULT 0,
            dauer INTEGER DEFAULT 0,
            arbeiter INTEGER DEFAULT 1,
            benutzername TEXT,
            rechnungsnummer INTEGER,
            datum TEXT
        )
    """)
 
    safe_create("mitarbeiter", """
        CREATE TABLE IF NOT EXISTS mitarbeiter (
            benutzername TEXT PRIMARY KEY,
            vorname TEXT,
            nachname TEXT,
            passwort TEXT,
            chefname TEXT,
            rolle TEXT,
            geraeteverwaltung INTEGER DEFAULT 0,
            account_id INTEGER
        )
    """)
 
    safe_create("mitarbeiter_projekte", """
        CREATE TABLE IF NOT EXISTS mitarbeiter_projekte (
            mitarbeiter_benutzername TEXT,
            projekt_id INTEGER,
            chefname TEXT,
            PRIMARY KEY (mitarbeiter_benutzername, projekt_id)
        )
    """)
 
    safe_create("rechnungen", """
        CREATE TABLE IF NOT EXISTS rechnungen (
            id SERIAL PRIMARY KEY,
            projekt_name TEXT,
            rechnungsnummer INTEGER,
            pdf_data BYTEA,
            erstellt_am TIMESTAMP,
            nettobetrag DECIMAL(10, 2),
            benutzername TEXT,
            UNIQUE(projekt_name, rechnungsnummer)
        )
    """)
 
    safe_create("payment_transactions", """
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            paypal_transaction_id TEXT,
            amount DECIMAL(10, 2),
            currency TEXT,
            status TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("ausgaben_lohn", """
        CREATE TABLE IF NOT EXISTS ausgaben_lohn (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            jahr INTEGER,
            monat INTEGER,
            betrag DECIMAL(10, 2),
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (benutzername, jahr, monat)
        )
    """)
 
    safe_create("sonstige_ausgaben", """
        CREATE TABLE IF NOT EXISTS sonstige_ausgaben (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            monat TEXT,
            betrag DECIMAL(10, 2),
            letztes_aenderungsdatum TEXT,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (benutzername, monat)
        )
    """)
 
    safe_create("arbeitszeiten", """
        CREATE TABLE IF NOT EXISTS arbeitszeiten (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            projekt_id INTEGER,
            datum TIMESTAMP,
            stunden DECIMAL(5, 2),
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("standardgehaelter", """
        CREATE TABLE IF NOT EXISTS standardgehaelter (
            rolle TEXT PRIMARY KEY,
            gehalt DECIMAL(10, 2),
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("materialverbrauch", """
        CREATE TABLE IF NOT EXISTS materialverbrauch (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            projekt_id INTEGER,
            datum TIMESTAMP,
            material TEXT,
            menge DECIMAL(10, 2),
            einheit TEXT,
            mitarbeiter TEXT,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("lagerbestand", """
        CREATE TABLE IF NOT EXISTS lagerbestand (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            material TEXT,
            menge DECIMAL(10, 2),
            einheit TEXT,
            preis_ankauf DECIMAL(10, 2),
            preis_verkauf DECIMAL(10, 2),
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (benutzername, material)
        )
    """)
 
    safe_create("materialien", """
        CREATE TABLE IF NOT EXISTS materialien (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            projekt_id INTEGER,
            material TEXT,
            menge DECIMAL(10, 2),
            verbrauch DECIMAL(10, 2) DEFAULT 0,
            einheit TEXT,
            datum DATE,
            bearbeitet_von_bauunternehmer INTEGER DEFAULT 0,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("geraete_lager", """
        CREATE TABLE IF NOT EXISTS geraete_lager (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            geraet TEXT,
            anzahl INTEGER,
            art TEXT,
            dauer INTEGER,
            monatliche_kosten DECIMAL(10, 2),
            betriebskosten DECIMAL(10, 2),
            datum_hinzugefuegt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (benutzername, geraet)
        )
    """)
 
    safe_create("geraete_nutzung", """
        CREATE TABLE IF NOT EXISTS geraete_nutzung (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            projekt_id INTEGER,
            geraet TEXT,
            datum TIMESTAMP,
            nutzungszeit DECIMAL(5, 2),
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("checklistenpunkte", """
        CREATE TABLE IF NOT EXISTS checklistenpunkte (
            id SERIAL PRIMARY KEY,
            projekt_id INTEGER,
            text TEXT,
            kommentar TEXT,
            erledigt INTEGER DEFAULT 0,
            erledigt_am TIMESTAMP,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("checklisten_gesamtkommentar", """
        CREATE TABLE IF NOT EXISTS checklisten_gesamtkommentar (
            id SERIAL PRIMARY KEY,
            projekt_id INTEGER,
            benutzername TEXT,
            kommentar TEXT,
            zeitaufwand DECIMAL(5, 2),
            datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("checklisten_allgemeinkommentar", """
        CREATE TABLE IF NOT EXISTS checklisten_allgemeinkommentar (
            id SERIAL PRIMARY KEY,
            projekt_id INTEGER,
            fortschritt_text TEXT,
            datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("checklisten_fortschrittkommentar", """
        CREATE TABLE IF NOT EXISTS checklisten_fortschrittkommentar (
            id SERIAL PRIMARY KEY,
            projekt_id INTEGER,
            kommentar TEXT,
            datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("bericht_daten_archive", """
        CREATE TABLE IF NOT EXISTS bericht_daten_archive (
            id SERIAL PRIMARY KEY,
            benutzername TEXT NOT NULL,
            projekt_id INTEGER NOT NULL,
            datum DATE NOT NULL,
            wetter TEXT,
            boden TEXT,
            arbeitsbericht TEXT,
            mitarbeiter TEXT,
            materialeinsatz TEXT,
            geraeteeinsatz TEXT,
            probleme TEXT,
            todo TEXT,
            checklisten_data TEXT,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            erstellt_von_admin INTEGER DEFAULT 0,
            UNIQUE(benutzername, projekt_id, datum)
        )
    """)
 
    safe_create("pdf_archive", """
        CREATE TABLE IF NOT EXISTS pdf_archive (
            id SERIAL PRIMARY KEY,
            benutzername TEXT NOT NULL,
            projekt_id INTEGER NOT NULL,
            datum DATE NOT NULL,
            pdf_blob BYTEA NOT NULL,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(benutzername, projekt_id, datum)
        )
    """)
 
    safe_create("nutzerentwicklung_log", """
        CREATE TABLE IF NOT EXISTS nutzerentwicklung_log (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            aktion TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("webhook_log", """
        CREATE TABLE IF NOT EXISTS webhook_log (
            id SERIAL PRIMARY KEY,
            event_type TEXT,
            body TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("materialplanung", """
        CREATE TABLE IF NOT EXISTS materialplanung (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            projekt_id INTEGER,
            datum TIMESTAMP,
            material TEXT,
            menge DECIMAL(10, 2),
            einheit TEXT,
            art TEXT,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    safe_create("vorplanung", """
        CREATE TABLE IF NOT EXISTS vorplanung (
            id SERIAL PRIMARY KEY,
            benutzername TEXT,
            projekt_id INTEGER,
            projektname TEXT,
            maschine TEXT,
            datum DATE,
            zeitraum TEXT,
            mitarbeiter TEXT,
            erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    safe_create("lohnabrechnung_archiv", """
    CREATE TABLE IF NOT EXISTS lohnabrechnung_archiv (
        id SERIAL PRIMARY KEY,
        jahr INTEGER,
        monat INTEGER,
        benutzername TEXT,
        erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        pdf_data BYTEA
    )
    """)
    
    safe_create("wetterdaten", """
    CREATE TABLE IF NOT EXISTS wetterdaten (
        projekt_id INTEGER,
        datum TEXT,
        wetter1 TEXT,
        wetter2 TEXT,
        boden1 TEXT,
        boden2 TEXT,
        temperatur REAL,
        schlecht INTEGER,
        PRIMARY KEY (projekt_id, datum)
    )
    """)
    


    # ── Fehlende Spalten nachrüsten (für bestehende Datenbanken) ──
    safe_alter("ALTER TABLE projekte ADD COLUMN archiviert_am TEXT DEFAULT NULL")
    safe_alter("ALTER TABLE benutzer ADD COLUMN tutorial_completed BOOLEAN DEFAULT FALSE")
    safe_alter("ALTER TABLE mitarbeiter ADD COLUMN tutorial_completed BOOLEAN DEFAULT FALSE")
    safe_alter("ALTER TABLE firmenprofil ADD COLUMN rechnungsnummer INTEGER")
    safe_alter("ALTER TABLE firmenprofil ADD COLUMN gesellschaftsform TEXT")
    safe_alter("ALTER TABLE firmenprofil ADD COLUMN iban TEXT")
    safe_alter("ALTER TABLE firmenprofil ADD COLUMN bic TEXT")
    safe_alter("ALTER TABLE firmenprofil ADD COLUMN bankname TEXT")
    safe_alter("ALTER TABLE firmenprofil ADD COLUMN registergericht TEXT")
    safe_alter("ALTER TABLE firmenprofil ADD COLUMN hrb_nummer TEXT")
    safe_alter("ALTER TABLE firmenprofil ADD COLUMN geschaeftsfuehrer TEXT")
    safe_alter("ALTER TABLE firmenprofil ADD COLUMN ustidnr TEXT")
    safe_alter("ALTER TABLE benutzer ADD COLUMN is_test_account BOOLEAN DEFAULT FALSE")
    safe_alter("ALTER TABLE benutzer ADD COLUMN test_expiration_time TIMESTAMP DEFAULT NULL")
    safe_alter("ALTER TABLE benutzer ADD COLUMN test_duration_hours INTEGER DEFAULT 24")
    safe_alter("ALTER TABLE arbeitszeiten ADD COLUMN startzeit TEXT")
    safe_alter("ALTER TABLE arbeitszeiten ADD COLUMN endzeit TEXT")
    safe_alter("ALTER TABLE geraete_nutzung ADD COLUMN benutzername TEXT")
    safe_alter("ALTER TABLE materialien ADD COLUMN verbrauch DECIMAL(10, 2) DEFAULT 0")
    safe_alter("ALTER TABLE materialien ADD COLUMN datum DATE")
    safe_alter("ALTER TABLE materialien ADD COLUMN benutzername TEXT")
    safe_alter("ALTER TABLE lagerbestand ADD COLUMN benutzername TEXT")
    safe_alter("ALTER TABLE rechnungen ADD COLUMN benutzername TEXT")
    safe_alter("ALTER TABLE benutzer ADD COLUMN theme TEXT DEFAULT 'white'")
    safe_alter("ALTER TABLE geraete_lager ADD COLUMN dauer INTEGER")
    safe_alter("ALTER TABLE geraete_lager ADD COLUMN betriebskosten REAL")
    safe_alter("ALTER TABLE geraete_lager ADD COLUMN monatliche_kosten REAL")
    safe_alter("ALTER TABLE checklisten_allgemeinkommentar ADD COLUMN fortschritt_text TEXT")
    safe_alter("ALTER TABLE checklistenpunkte ADD COLUMN benutzername TEXT")
    safe_alter("ALTER TABLE checklisten_fortschrittkommentar ADD COLUMN benutzername TEXT")
    safe_alter("ALTER TABLE checklisten_gesamtkommentar ADD COLUMN zeitaufwand TEXT")
    safe_alter("ALTER TABLE geraete_nutzung ADD COLUMN projekt_id INTEGER")
 
# ── Beim Import automatisch ausführen ────────────────────────
try:
    ensure_schema()
except Exception as e:
    print(f"Schema-Initialisierung: {str(e)[:150]}")
 