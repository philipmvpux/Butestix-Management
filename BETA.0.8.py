import os
from urllib.parse import quote
import time
from datetime import datetime, time as datetime_time, date
from config import DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

# Absolute Pfad für Backups (falls benötigt)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# PostgreSQL Connection Configuration (from config.py)
SAFE_PASSWORD = quote(DB_PASSWORD, safe='')
DATABASE_URL = f"postgresql://{DB_USER}:{SAFE_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Zentrale Schema-Prüfung und Migration: sorgt dafür, dass alle erwarteten Tabellen/Spalten existieren
def ensure_schema():
    # WICHTIG: Nutze die bereits gecachte Engine statt neue zu erstellen
    global engine
    
    # Helper function to safely create tables
    def safe_create_table(conn, table_name, sql):
        try:
            conn.exec_driver_sql(sql)
        except Exception as e:
            print(f"Note: Table {table_name} creation had an issue (likely already exists): {str(e)[:100]}")
    
    with engine.begin() as conn:
        # rechnungen
        safe_create_table(conn, "rechnungen", """
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
        # projekte
        safe_create_table(conn, "projekte", """
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
        
        # mitarbeiter
        safe_create_table(conn, "mitarbeiter", """
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
        # mitarbeiter_projekte
        safe_create_table(conn, "mitarbeiter_projekte", """
            CREATE TABLE IF NOT EXISTS mitarbeiter_projekte (
                mitarbeiter_benutzername TEXT,
                projekt_id INTEGER,
                chefname TEXT,
                PRIMARY KEY (mitarbeiter_benutzername, projekt_id)
            )
        """)
        # benutzer
        safe_create_table(conn, "benutzer", """
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
                datenschutz_accepted_at TIMESTAMP
            )
        """)
        
        # === Sicherungsspalten für archiviert_am ===
        try:
            conn.exec_driver_sql("ALTER TABLE projekte ADD COLUMN archiviert_am TEXT DEFAULT NULL")
        except Exception:
            pass  # Column bereits vorhanden
        # payment_transactions
        safe_create_table(conn, "payment_transactions", """
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
        # ausgaben_lohn
        safe_create_table(conn, "ausgaben_lohn", """
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
        
        # sonstige_ausgaben
        safe_create_table(conn, "sonstige_ausgaben", """
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
        
        # firmenprofil - für Unternehmensprofile
        safe_create_table(conn, "firmenprofil", """
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
        
        # Add missing columns if they don't exist (for existing tables)
        try:
            conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN rechnungsnummer INTEGER")
        except:
            pass  # Column already exists
        try:
            conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN gesellschaftsform TEXT")
        except:
            pass  # Column already exists
        try:
            conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN iban TEXT")
        except:
            pass  # Column already exists
        try:
            conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN bic TEXT")
        except:
            pass  # Column already exists
        try:
            conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN bankname TEXT")
        except:
            pass  # Column already exists
        try:
            conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN registergericht TEXT")
        except:
            pass  # Column already exists
        try:
            conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN hrb_nummer TEXT")
        except:
            pass  # Column already exists
        try:
            conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN geschaeftsfuehrer TEXT")
        except:
            pass  # Column already exists
        try:
            conn.exec_driver_sql("ALTER TABLE firmenprofil ADD COLUMN ustidnr TEXT")
        except:
            pass  # Column already exists
        
        # arbeitszeiten - Arbeitszeiterfassung
        safe_create_table(conn, "arbeitszeiten", """
            CREATE TABLE IF NOT EXISTS arbeitszeiten (
                id SERIAL PRIMARY KEY,
                benutzername TEXT,
                projekt_id INTEGER,
                datum TIMESTAMP,
                stunden DECIMAL(5, 2),
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # standardgehaelter - Standard-Gehälter pro Rolle
        safe_create_table(conn, "standardgehaelter", """
            CREATE TABLE IF NOT EXISTS standardgehaelter (
                rolle TEXT PRIMARY KEY,
                gehalt DECIMAL(10, 2),
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # materialverbrauch - Material-Verbrauch tracking
        safe_create_table(conn, "materialverbrauch", """
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
        
        # lagerbestand - Lagerbestände
        safe_create_table(conn, "lagerbestand", """
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
        
        # materialien - Materialien-Planung
        safe_create_table(conn, "materialien", """
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
        
        # geraete_lager - Geräte-Lager
        safe_create_table(conn, "geraete_lager", """
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
        
        # geraete_nutzung - Geräte-Nutzung
        safe_create_table(conn, "geraete_nutzung", """
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
        
        # checklistenpunkte - Checklisten-Punkte
        safe_create_table(conn, "checklistenpunkte", """
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
        
        # checklisten_gesamtkommentar - Gesamtkommentare für Checklisten
        safe_create_table(conn, "checklisten_gesamtkommentar", """
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
        
        # checklisten_allgemeinkommentar - Allgemeinkommentare
        safe_create_table(conn, "checklisten_allgemeinkommentar", """
            CREATE TABLE IF NOT EXISTS checklisten_allgemeinkommentar (
                id SERIAL PRIMARY KEY,
                projekt_id INTEGER,
                fortschritt_text TEXT,
                datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # checklisten_fortschrittkommentar - Fortschrittkommentare
        safe_create_table(conn, "checklisten_fortschrittkommentar", """
            CREATE TABLE IF NOT EXISTS checklisten_fortschrittkommentar (
                id SERIAL PRIMARY KEY,
                projekt_id INTEGER,
                kommentar TEXT,
                datum TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # bericht_daten_archive - Gespeicherte Tagesbericht-DATEN (nicht PDF)
        safe_create_table(conn, "bericht_daten_archive", """
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
        
        # pdf_archive - Gespeicherte Tagesberichte als PDF (deprecated, für Kompatibilität)
        safe_create_table(conn, "pdf_archive", """
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
        
        # nutzerentwicklung_log - Benutzeraktions-Log
        safe_create_table(conn, "nutzerentwicklung_log", """
            CREATE TABLE IF NOT EXISTS nutzerentwicklung_log (
                id SERIAL PRIMARY KEY,
                benutzername TEXT,
                aktion TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # webhook_log - PayPal Webhook Log
        safe_create_table(conn, "webhook_log", """
            CREATE TABLE IF NOT EXISTS webhook_log (
                id SERIAL PRIMARY KEY,
                event_type TEXT,
                body TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # materialplanung - Material-Planung
        safe_create_table(conn, "materialplanung", """
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
        
        # vorplanung - Vorplanungskalender für Geräte
        safe_create_table(conn, "vorplanung", """
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
        
        # PostgreSQL: Alle notwendigen Tabellen sind erstellt

# HINWEIS: ensure_schema() wird später nach Engine-Definition aufgerufen (Zeile ~1850)

# ============================================
# Streamlit & weitere Imports
# ============================================

def bauunternehmer_dashboard():
    import plotly.graph_objects as go
    import plotly.express as px
    import streamlit as st
    import pandas as pd
    from datetime import datetime, timedelta

    # === Stelle sicher, dass sonstige_ausgaben Tabelle existiert ===
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("""
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
    except Exception as e:
        print(f"Note: sonstige_ausgaben table creation: {str(e)[:100]}")
    
    # === Hole den Theme vom User ===
    user = st.session_state.get("user")
    user_theme = "white"  # Default
    try:
        df_theme = pd.read_sql("SELECT theme FROM benutzer WHERE benutzername = %s", engine, params=(user,))
        if not df_theme.empty:
            user_theme = df_theme["theme"].iloc[0] if df_theme["theme"].iloc[0] else "white"
    except Exception:
        pass

    # === CSS für Breakdown-Fenster (Dynamisch basierend auf Theme) ===
    if user_theme == "white":
        # WHITE MODE
        st.markdown("""
        <style>
        /* Allgemeine Styles für alle Breakdown-Fenster */
        [class*="ums_"], [class*="ausg_"], [class*="gew_"] {
            position: relative;
            display: inline-block;
        }
        
        /* Breakdown-Fenster: Hell im White Mode */
        [class*="ums_"] .breakdown,
        [class*="ausg_"] .breakdown,
        [class*="gew_"] .breakdown {
            display: none !important;
            position: absolute;
            left: 0;
            top: 100%;
            transform: translateY(8px);
            background: #f5f5f5 !important;
            border: 2px solid #cccccc !important;
            padding: 12px !important;
            border-radius: 6px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15) !important;
            min-width: 280px;
            z-index: 100000;
            pointer-events: auto;
            color: #000000 !important;
        }
        
        /* Show State für Breakdown */
        [class*="ums_"].show .breakdown,
        [class*="ausg_"].show .breakdown,
        [class*="gew_"].show .breakdown,
        [class*="ums_"] input:checked + .breakdown,
        [class*="ausg_"] input:checked + .breakdown,
        [class*="gew_"] input:checked + .breakdown {
            display: block !important;
        }
        
        /* Rows und Total Styling */
        [class*="ums_"] .row,
        [class*="ausg_"] .row,
        [class*="gew_"] .row {
            display: flex;
            justify-content: space-between;
            margin: 0 0 8px 0;
            padding: 4px 0;
            font-size: 13px;
            line-height: 1.2;
            color: #000000 !important;
        }
        
        [class*="ums_"] .total,
        [class*="ausg_"] .total,
        [class*="gew_"] .total {
            font-weight: 700;
            margin-top: 8px;
            border-top: 1px solid #cccccc !important;
            padding-top: 8px;
            text-align: right;
            color: #000000 !important;
        }
        
        /* Label Styling - WHITE MODE: SCHWARZ */
        [class*="ums_"] .label,
        [class*="ausg_"] .label,
        [class*="gew_"] .label {
            font-size: 12px;
            color: #000000 !important;
            opacity: 0.7;
        }
        
        /* Value/Label Button Styling */
        [class*="ums_"] label.value,
        [class*="ausg_"] label.value,
        [class*="gew_"] label.value {
            white-space: nowrap;
            font-size: clamp(14px, 3vw, 28px);
            font-weight: 600;
            cursor: pointer;
            margin-top: 4px;
            user-select: none;
            display: block;
        }
        
        [class*="ums_"] label.value {
            color: #00DD00 !important;
        }
        
        [class*="ausg_"] label.value {
            color: #FF4444 !important;
        }
        
        [class*="gew_"] label.value {
            color: #4488FF !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        # BLACK MODE
        st.markdown("""
        <style>
        /* Allgemeine Styles für alle Breakdown-Fenster */
        [class*="ums_"], [class*="ausg_"], [class*="gew_"] {
            position: relative;
            display: inline-block;
        }
        
        /* Breakdown-Fenster: Dunkel im Black Mode */
        [class*="ums_"] .breakdown,
        [class*="ausg_"] .breakdown,
        [class*="gew_"] .breakdown {
            display: none !important;
            position: absolute;
            left: 0;
            top: 100%;
            transform: translateY(8px);
            background: #2a2a2a !important;
            border: 2px solid #888 !important;
            padding: 12px !important;
            border-radius: 6px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8) !important;
            min-width: 280px;
            z-index: 100000;
            pointer-events: auto;
            color: #ffffff !important;
        }
        
        /* Show State für Breakdown */
        [class*="ums_"].show .breakdown,
        [class*="ausg_"].show .breakdown,
        [class*="gew_"].show .breakdown,
        [class*="ums_"] input:checked + .breakdown,
        [class*="ausg_"] input:checked + .breakdown,
        [class*="gew_"] input:checked + .breakdown {
            display: block !important;
        }
        
        /* Rows und Total Styling */
        [class*="ums_"] .row,
        [class*="ausg_"] .row,
        [class*="gew_"] .row {
            display: flex;
            justify-content: space-between;
            margin: 0 0 8px 0;
            padding: 4px 0;
            font-size: 13px;
            line-height: 1.2;
            color: #ffffff !important;
        }
        
        [class*="ums_"] .total,
        [class*="ausg_"] .total,
        [class*="gew_"] .total {
            font-weight: 700;
            margin-top: 8px;
            border-top: 1px solid #666 !important;
            padding-top: 8px;
            text-align: right;
            color: #ffffff !important;
        }
        
        /* Label Styling - BLACK MODE: WEISS */
        [class*="ums_"] .label,
        [class*="ausg_"] .label,
        [class*="gew_"] .label {
            font-size: 12px;
            color: #ffffff !important;
            opacity: 0.7;
        }
        
        /* Value/Label Button Styling */
        [class*="ums_"] label.value,
        [class*="ausg_"] label.value,
        [class*="gew_"] label.value {
            white-space: nowrap;
            font-size: clamp(14px, 3vw, 28px);
            font-weight: 600;
            cursor: pointer;
            margin-top: 4px;
            user-select: none;
            display: block;
        }
        
        [class*="ums_"] label.value {
            color: #00DD00 !important;
        }
        
        [class*="ausg_"] label.value {
            color: #FF4444 !important;
        }
        
        [class*="gew_"] label.value {
            color: #4488FF !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # Firmenname und Logo laden
    df_firma = pd.read_sql("SELECT firmenname, logo FROM firmenprofil WHERE benutzername = %s", engine, params=(user,))
    firmenname = df_firma["firmenname"].iloc[0] if not df_firma.empty else ""
    logo = df_firma["logo"].iloc[0] if not df_firma.empty else None

    st.markdown(f"# Übersicht: {firmenname}")
    if logo:
        st.image(logo, width=180)

    # Zeitraum-Auswahl
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Zeitraum von", value=datetime.now().date() - timedelta(days=30), max_value=datetime.now().date(), key="umsatz_start")
    with col2:
        end_date = st.date_input("bis", value=datetime.now().date(), max_value=datetime.now().date(), key="umsatz_ende")

    # ===== SONSTIGE AUSGABEN EXPANDER =====
    with st.expander("Sonstige Ausgaben"):
        import calendar
        
        # Bestimme den frühesten Monat mit Einträgen
        df_erste_ausgabe = pd.read_sql(
            "SELECT MIN(monat) as min_monat FROM sonstige_ausgaben WHERE benutzername = %s",
            engine,
            params=(user,)
        )
        
        if not df_erste_ausgabe.empty and pd.notnull(df_erste_ausgabe["min_monat"].iloc[0]):
            min_monat_str = df_erste_ausgabe["min_monat"].iloc[0]
            min_jahr, min_monat = int(min_monat_str.split('-')[0]), int(min_monat_str.split('-')[1])
        else:
            # Kein Eintrag vorhanden, starte mit aktuellem Monat
            min_jahr, min_monat = datetime.now().year, datetime.now().month

        # --- Einmaliger Testwert für November 2025 einfügen (nur, wenn noch nicht vorhanden) ---
        try:
            if st.session_state.get("user") == "Philip":
                with engine.begin() as conn:
                    exists = conn.exec_driver_sql(
                        "SELECT 1 FROM sonstige_ausgaben WHERE benutzername = %s AND monat = '2025-11'",
                        (user,)
                    ).fetchone()
                    if not exists:
                        conn.exec_driver_sql(
                            "INSERT INTO sonstige_ausgaben (benutzername, monat, betrag, letztes_aenderungsdatum) VALUES (%s, '2025-11', 10.0, '2025-11-01')",
                            (user,)
                        )
        except Exception:
            pass
        
        # Generiere 12 Monats-Paare: starte mit dem aktuellen Monat, zeige für jeden Monat M M (aktuelles Jahr) gefolgt von M (nächstes Jahr)
        start_date_monat = datetime(datetime.now().year, datetime.now().month, 1)
        monate_list = []
        monat_keys = []

        for i in range(12):
            current_monat = start_date_monat + pd.DateOffset(months=i)
            next_year_monat = current_monat + pd.DateOffset(years=1)
            # Aktuelles Jahr
            monat_keys.append(current_monat.strftime("%Y-%m"))
            monate_list.append(f"{calendar.month_name[current_monat.month]} {current_monat.year}")
            # Nächstes Jahr (Paare direkt darunter)
            monat_keys.append(next_year_monat.strftime("%Y-%m"))
            monate_list.append(f"{calendar.month_name[next_year_monat.month]} {next_year_monat.year}")

        # Ergänze historische Monats-Einträge (falls vorhanden) direkt unter dem jeweiligen Monatspaar
        try:
            hist_months = set()
            df_hist = pd.read_sql("SELECT DISTINCT monat FROM sonstige_ausgaben WHERE benutzername = %s", engine, params=(user,))
            if not df_hist.empty:
                hist_months.update(df_hist['monat'].dropna().astype(str).tolist())
            df_hist2 = pd.read_sql("SELECT jahr, monat FROM ausgaben_lohn WHERE benutzername = %s", engine, params=(user,))
            if not df_hist2.empty:
                for _, r in df_hist2.iterrows():
                    try:
                        ym = f"{int(r['jahr']):04d}-{int(r['monat']):02d}"
                        hist_months.add(ym)
                    except Exception:
                        continue

            # Insert historical months (sorted by year desc) under the corresponding month-pair
            for hist in sorted(hist_months, reverse=True):
                if hist in monat_keys:
                    continue
                try:
                    hist_year, hist_mon = int(hist.split('-')[0]), int(hist.split('-')[1])
                except Exception:
                    continue
                # find the position of this month's first occurrence in the pair (month number match)
                pos = None
                for idx_k, k in enumerate(monat_keys):
                    try:
                        k_mon = int(k.split('-')[1])
                        if k_mon == hist_mon:
                            pos = idx_k
                            break
                    except Exception:
                        continue
                if pos is not None:
                    insert_pos = pos + 2  # after the pair
                    label = f"{calendar.month_name[hist_mon]} {hist_year}"
                    monat_keys.insert(insert_pos, hist)
                    monate_list.insert(insert_pos, label)
        except Exception:
            pass
        
        # Aktueller Monat als Default
        aktueller_monat_str = datetime.now().strftime("%Y-%m")
        default_index = monat_keys.index(aktueller_monat_str) if aktueller_monat_str in monat_keys else 0
        
        col_monat, col_betrag, col_speichern = st.columns([2, 2, 1])
        
        with col_monat:
            # Monat-Selector
            selected_index = st.selectbox(
                "Monat",
                range(len(monate_list)),
                index=default_index,
                format_func=lambda idx: monate_list[idx],
                key="sonstige_ausgabe_monat"
            )
            selected_monat_key = monat_keys[selected_index]
        
        with col_betrag:
            # Betrag eingeben
            # Lade aktuellen Betrag für diesen Monat
            current_betrag = 0.0
            df_existing = pd.read_sql(
                "SELECT betrag FROM sonstige_ausgaben WHERE benutzername = %s AND monat = %s",
                engine,
                params=(user, selected_monat_key)
            )
            if not df_existing.empty:
                current_betrag = float(df_existing["betrag"].iloc[0])
            
            betrag = st.number_input(
                "Betrag (€)",
                min_value=0.0,
                step=0.01,
                value=current_betrag,
                key="sonstige_ausgabe_betrag"
            )
        
        with col_speichern:
            st.write("")  # Platzhalter für Alignment
        
        # Speichern-Button
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Speichern", key="save_sonstige_ausgabe"):
                try:
                    heute = datetime.now().date().strftime("%Y-%m-%d")
                    
                    with engine.begin() as conn:
                        # Prüfe, ob bereits ein Eintrag für diesen Monat existiert
                        existing = conn.exec_driver_sql(
                            "SELECT letztes_aenderungsdatum FROM sonstige_ausgaben WHERE benutzername = %s AND monat = %s",
                            (user, selected_monat_key)
                        ).fetchone()
                        
                        if existing:
                            # UPDATE: Aktualisiere nur den Betrag und das Änderungsdatum
                            conn.exec_driver_sql(
                                "UPDATE sonstige_ausgaben SET betrag = %s, letztes_aenderungsdatum = %s WHERE benutzername = %s AND monat = %s",
                                (betrag, heute, user, selected_monat_key)
                            )
                            st.success(f"Ausgabe für {monate_list[selected_index]} aktualisiert: {betrag:.2f} €")
                        else:
                            # INSERT: Neuer Eintrag
                            conn.exec_driver_sql(
                                "INSERT INTO sonstige_ausgaben (benutzername, monat, betrag, letztes_aenderungsdatum) VALUES (%s, %s, %s, %s)",
                                (user, selected_monat_key, betrag, heute)
                            )
                            st.success(f"Ausgabe für {monate_list[selected_index]} gespeichert: {betrag:.2f} €")
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {str(e)}")
        
        with col_btn2:
            if st.button("Löschen", key="delete_sonstige_ausgabe"):
                try:
                    with engine.begin() as conn:
                        conn.exec_driver_sql(
                            "DELETE FROM sonstige_ausgaben WHERE benutzername = %s AND monat = %s",
                            (user, selected_monat_key)
                        )
                    st.success(f"Ausgabe für {monate_list[selected_index]} gelöscht")
                    st.session_state["sonstige_ausgabe_betrag"] = 0.0
                except Exception as e:
                    st.error(f"Fehler beim Löschen: {str(e)}")

    # Rechnungen im Zeitraum laden
    try:
        df_re = pd.read_sql(
            """
            SELECT r.erstellt_am, r.nettobetrag,
                   COALESCE(p.name, r.projekt_name) as projekt_name
            FROM rechnungen r
            LEFT JOIN projekte p ON (p.projekt_name = r.projekt_name OR p.name = r.projekt_name)
            WHERE (
                r.benutzername = %s
                OR (
                    (r.benutzername IS NULL OR r.benutzername = '')
                    AND EXISTS(
                        SELECT 1 FROM projekte p2
                        WHERE (p2.projekt_name = r.projekt_name OR p2.name = r.projekt_name)
                          AND p2.benutzername = %s
                    )
                )
            )
            AND date(r.erstellt_am) BETWEEN %s AND %s
            ORDER BY r.erstellt_am ASC
            """,
            engine,
            params=(user, user, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        )
    except Exception:
        # Legacy DB without rechnungen.benutzername
        df_re = pd.read_sql(
            "SELECT erstellt_am, nettobetrag, projekt_name FROM rechnungen WHERE date(erstellt_am) BETWEEN %s AND %s ORDER BY erstellt_am ASC",
            engine,
            params=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        )
        try:
            df_proj_user = pd.read_sql("SELECT projekt_name, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(user,))
            owned_names = set()
            if not df_proj_user.empty:
                owned_names.update(df_proj_user['projekt_name'].dropna().astype(str).tolist())
                owned_names.update(df_proj_user['name'].dropna().astype(str).tolist())
            if owned_names:
                df_re = df_re[df_re['projekt_name'].isin(owned_names)]
            else:
                df_re = df_re.head(0)
        except Exception:
            df_re = df_re.head(0)

    # If no invoices, still show expenses
    if df_re.empty:
        st.warning("Keine Rechnungen für den gewählten Zeitraum, zeige nur Ausgaben.")
        df_re = pd.DataFrame({"erstellt_am": pd.date_range(start=start_date, end=end_date), "nettobetrag": 0.0})
        # Initialize df_sum even when no invoices exist
        all_days = pd.date_range(start=start_date, end=end_date)
        df_sum = pd.DataFrame({"Datum": all_days, "Umsatz": 0.0})
        df_sum["Umsatz_Kumulativ"] = df_sum["Umsatz"].cumsum()
    else:

        df_re["erstellt_am"] = pd.to_datetime(df_re["erstellt_am"])
        df_sum = df_re.groupby(df_re["erstellt_am"].dt.date)["nettobetrag"].sum().reset_index()
        df_sum = df_sum.rename(columns={"erstellt_am": "Datum", "nettobetrag": "Umsatz"})

        all_days = pd.date_range(start=start_date, end=end_date)
        df_sum = df_sum.set_index("Datum").reindex(all_days, fill_value=0).reset_index().rename(columns={"index": "Datum"})

        df_sum["Umsatz_Kumulativ"] = df_sum["Umsatz"].cumsum()

    # ===== EXPENSES CALCULATION =====
    # Stelle sicher, dass expenses_daily ALL Tage im Zeitraum abdeckt (nicht nur Rechnungstage)
    all_days = pd.date_range(start=start_date, end=end_date)
    expenses_index = all_days.date
    expenses_daily = pd.Series(0.0, index=expenses_index).astype(float)
    df_hours = pd.DataFrame()
    df_mat = pd.DataFrame()
    df_devices = pd.DataFrame()
    lohn_total = 0.0
    mat_total = 0.0
    geraet_total = 0.0
    sonstige_period_total = 0.0
    ausgaben_lohn_period_total = 0.0
    mat_total = 0.0
    device_monthly_total = 0.0
    sonstige_total = 0.0
    
    # 0) Sonstige Ausgaben laden
    try:
        df_sonstige = pd.read_sql(
            "SELECT monat, betrag, letztes_aenderungsdatum FROM sonstige_ausgaben WHERE benutzername = %s",
            engine,
            params=(user,)
        )
        if not df_sonstige.empty:
            for idx, row in df_sonstige.iterrows():
                # Berechne die Ausgabe am Tag des letzten Änderungsdatums
                aenderungsdatum = pd.to_datetime(row["letztes_aenderungsdatum"]).date()
                betrag = float(row["betrag"])
                
                # Nur berechnen, wenn das Änderungsdatum im Zeitraum liegt
                if aenderungsdatum in expenses_daily.index and aenderungsdatum >= pd.to_datetime(start_date).date():
                    expenses_daily.loc[aenderungsdatum] += betrag
                sonstige_total += betrag
    except Exception:
        pass

    # 0b) Ausgaben aus Lohn-PDF (falls vorhanden) einbeziehen
    ausgaben_lohn_total = 0.0
    try:
        df_ausgaben_lohn = pd.read_sql(
            "SELECT jahr, monat, betrag, erstellt_am FROM ausgaben_lohn WHERE benutzername = %s",
            engine,
            params=(user,)
        )
        if not df_ausgaben_lohn.empty:
            for idx, row in df_ausgaben_lohn.iterrows():
                try:
                    erstellt = pd.to_datetime(row["erstellt_am"]).date() if pd.notnull(row["erstellt_am"]) else None
                    betrag = float(row["betrag"])
                    if erstellt and (erstellt in expenses_daily.index) and (erstellt >= pd.to_datetime(start_date).date()):
                        expenses_daily.loc[erstellt] += betrag
                    ausgaben_lohn_total += betrag
                except Exception:
                    continue
    except Exception:
        pass

    # 1) Lohnkosten
    try:
        df_hours = pd.read_sql(
            "SELECT datum, stunden, benutzername FROM arbeitszeiten WHERE date(datum) BETWEEN %s AND %s",
            engine, params=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        )
        if not df_hours.empty:
            df_mitarbeiter = pd.read_sql("SELECT benutzername, rolle FROM mitarbeiter", engine)
            df_gehalt = pd.read_sql("SELECT rolle, gehalt FROM standardgehaelter", engine)
            df_hours = df_hours.merge(df_mitarbeiter, on="benutzername", how="left")
            df_hours = df_hours.merge(df_gehalt, on="rolle", how="left")
            df_hours["gehalt"] = df_hours["gehalt"].fillna(0.0)
            df_hours["kosten"] = df_hours["stunden"].astype(float) * df_hours["gehalt"].astype(float)
            df_hours["datum"] = pd.to_datetime(df_hours["datum"]).dt.date
            lohn_by_date = df_hours.groupby("datum")["kosten"].sum()
            lohn_total = float(lohn_by_date.sum())
            for d, v in lohn_by_date.items():
                if d in expenses_daily.index:
                    expenses_daily.loc[d] += float(v)
    except Exception:
        pass

    # 2) Materialkosten
    try:
        df_mat = pd.read_sql(
            "SELECT datum, material, menge FROM materialverbrauch WHERE date(datum) BETWEEN %s AND %s",
            engine, params=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        )
        if not df_mat.empty:
            df_price = pd.read_sql("SELECT material, preis_ankauf FROM lagerbestand WHERE benutzername = %s", engine, params=(user,))
            df_mat = df_mat.merge(df_price, on="material", how="left")
            df_mat["preis_ankauf"] = df_mat["preis_ankauf"].fillna(0.0)
            df_mat["kosten"] = df_mat["menge"].astype(float) * df_mat["preis_ankauf"].astype(float)
            df_mat["datum"] = pd.to_datetime(df_mat["datum"]).dt.date
            mat_by_date = df_mat.groupby("datum")["kosten"].sum()
            mat_total = float(mat_by_date.sum())
            for d, v in mat_by_date.items():
                if d in expenses_daily.index:
                    expenses_daily.loc[d] += float(v)
    except Exception:
        pass

    # 3) Device monthly costs (charged on the anniversary date each month) + hourly operating costs
    try:
        df_devices = pd.read_sql(
            "SELECT geraet, anzahl, monatliche_kosten, betriebskosten, datum_hinzugefuegt FROM geraete_lager WHERE benutzername = %s", 
            engine, 
            params=(user,)
        )
        if not df_devices.empty:
            # Calculate operating costs (hourly * usage hours)
            df_usage = pd.read_sql(
                "SELECT geraet, datum, nutzungszeit FROM geraete_nutzung WHERE datum BETWEEN %s AND %s",
                engine,
                params=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            )
            
            for idx, row in df_devices.iterrows():
                anzahl = float(row["anzahl"]) if row["anzahl"] else 1.0
                monthly_cost_per_unit = float(row["monatliche_kosten"]) if row["monatliche_kosten"] else 0.0
                monthly_cost_total = anzahl * monthly_cost_per_unit  # Gesamtkosten für alle Geräte dieser Art
                
                operating_cost_per_hour_per_unit = float(row["betriebskosten"]) if row["betriebskosten"] else 0.0
                geraet_name = row["geraet"]
                added_date_str = row["datum_hinzugefuegt"]
                
                device_monthly_total += monthly_cost_total
                
                # 3a) Monthly charges (Anzahl × Kosten pro Gerät)
                # WICHTIG: Erste Abrechnung SOFORT am Hinzufüge-Datum, dann jeden Monat am selben Tag
                if monthly_cost_total > 0 and added_date_str:
                    try:
                        added_date = pd.to_datetime(added_date_str).date()
                        charge_day = added_date.day
                        
                        # ERSTE ABRECHNUNG: Am Hinzufüge-Datum, wenn es im Zeitraum liegt
                        if added_date in expenses_daily.index and added_date >= pd.to_datetime(start_date).date():
                            expenses_daily.loc[added_date] += monthly_cost_total
                        
                        # ZUKÜNFTIGE ABRECHNUNGEN: Jeden Monat am selben Tag
                        current_date = pd.to_datetime(added_date) + pd.DateOffset(months=1)
                        end_datetime = pd.to_datetime(end_date)
                        
                        while current_date <= end_datetime:
                            try:
                                charge_date = current_date.replace(day=charge_day)
                            except ValueError:
                                if current_date.month == 2:
                                    charge_date = current_date.replace(day=28)
                                elif current_date.month in [4, 6, 9, 11]:
                                    charge_date = current_date.replace(day=30)
                                else:
                                    charge_date = current_date.replace(day=31)
                            
                            if charge_date.date() in expenses_daily.index and charge_date.date() >= pd.to_datetime(start_date).date():
                                expenses_daily.loc[charge_date.date()] += monthly_cost_total
                            
                            current_date = current_date + pd.DateOffset(months=1)
                    except Exception:
                        pass
                
                # 3b) Operating costs (hourly * usage * Anzahl)
                if operating_cost_per_hour_per_unit > 0 and not df_usage.empty:
                    geraet_usage = df_usage[df_usage["geraet"] == geraet_name]
                    if not geraet_usage.empty:
                        for usage_idx, usage_row in geraet_usage.iterrows():
                            usage_date = pd.to_datetime(usage_row["datum"]).date()
                            usage_hours = float(usage_row["nutzungszeit"]) if usage_row["nutzungszeit"] else 0.0
                            # Betriebskosten = Stunden × €/h pro Gerät × Anzahl Geräte
                            operating_cost = usage_hours * operating_cost_per_hour_per_unit * anzahl
                            
                            if usage_date in expenses_daily.index and usage_date >= pd.to_datetime(start_date).date():
                                expenses_daily.loc[usage_date] += operating_cost
                                geraet_total += operating_cost
                # Add monthly charges into geraet_total when they are applied above
                try:
                    if monthly_cost_total > 0 and added_date_str:
                        added_date = pd.to_datetime(added_date_str).date()
                        if added_date >= pd.to_datetime(start_date).date() and added_date <= pd.to_datetime(end_date).date():
                            geraet_total += monthly_cost_total

                        current_date = pd.to_datetime(added_date) + pd.DateOffset(months=1)
                        end_datetime = pd.to_datetime(end_date)
                        while current_date <= end_datetime:
                            try:
                                charge_date = current_date.replace(day=charge_day)
                            except Exception:
                                if current_date.month == 2:
                                    charge_date = current_date.replace(day=28)
                                elif current_date.month in [4, 6, 9, 11]:
                                    charge_date = current_date.replace(day=30)
                                else:
                                    charge_date = current_date.replace(day=31)
                            if charge_date.date() >= pd.to_datetime(start_date).date() and charge_date.date() <= pd.to_datetime(end_date).date():
                                geraet_total += monthly_cost_total
                            current_date = current_date + pd.DateOffset(months=1)
                except Exception:
                    pass
    except Exception:
        pass

    df_sum = df_sum.set_index("Datum")
    df_sum["Ausgaben_Tages"] = expenses_daily
    df_sum["Ausgaben_Kumulativ"] = df_sum["Ausgaben_Tages"].cumsum()
    df_sum = df_sum.reset_index()
    
    # Berechne Gewinn (Umsatz - Ausgaben)
    df_sum["Gewinn_Kumulativ"] = df_sum["Umsatz_Kumulativ"] - df_sum["Ausgaben_Kumulativ"]

    col1, col2 = st.columns([2,1])
    with col1:
        df_chart = df_sum[['Datum', 'Umsatz_Kumulativ', 'Ausgaben_Kumulativ', 'Gewinn_Kumulativ']].copy()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_chart["Datum"], y=df_chart["Umsatz_Kumulativ"], name="Umsatz", line=dict(color="#00AA00", width=3), mode='lines+markers', marker=dict(size=8)))
        fig.add_trace(go.Scatter(x=df_chart["Datum"], y=df_chart["Ausgaben_Kumulativ"], name="Ausgaben", line=dict(color="#DD0000", width=3), mode='lines+markers', marker=dict(size=8)))
        fig.add_trace(go.Scatter(x=df_chart["Datum"], y=df_chart["Gewinn_Kumulativ"], name="Gewinn", line=dict(color="#0000CC", width=3), mode='lines+markers', marker=dict(size=8)))
        fig.update_layout(
            height=550, 
            hovermode='x unified', 
            xaxis_title="Datum", 
            yaxis_title="Betrag (€)", 
            font=dict(size=14, color="black"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(gridcolor="lightgray", showgrid=True, zeroline=False),
            yaxis=dict(gridcolor="lightgray", showgrid=True, zeroline=False),
            showlegend=True,
            legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.9)", bordercolor="black", borderwidth=1)
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "responsive": True, "displaylogo": False})

    with col2:
        try:
            mask = (df_sum["Datum"] >= pd.to_datetime(start_date)) & (df_sum["Datum"] <= pd.to_datetime(end_date))
            zeitraum_umsatz = float(df_sum.loc[mask, "Umsatz"].sum())
        except Exception:
            zeitraum_umsatz = 0.0

        zeitraum_ausgaben = 0.0
        try:
            if "Ausgaben_Tages" in df_sum.columns:
                zeitraum_ausgaben = float(df_sum.loc[mask, "Ausgaben_Tages"].sum())
            else:
                s_date = pd.to_datetime(start_date).date()
                e_date = pd.to_datetime(end_date).date()
                zeitraum_ausgaben = float(expenses_daily.loc[(expenses_daily.index >= s_date) & (expenses_daily.index <= e_date)].sum())
        except Exception:
            zeitraum_ausgaben = 0.0
        
        zeitraum_gewinn = zeitraum_umsatz - zeitraum_ausgaben

        with st.container():
            import random as _rand
            # Custom metric rendering to avoid line-wrapping and show full numbers.
            # If space is tight, font-size will shrink (clamp) so the number stays on one line.
            def _render_metric(label, value, color=None):
                color_style = f'color: {color};' if color else ''
                safe_value = str(value).replace(' ', '&nbsp;')
                st.markdown(
                    f"""
                    <div style="padding:6px 0;">
                      <div style="font-size:12px;color:var(--text-secondary,#6c6c6c);">{label}</div>
                      <div style="white-space:nowrap;overflow:visible;font-size:clamp(14px,3vw,28px);font-weight:600;{color_style}">{safe_value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Interactive Umsatz breakdown: shows top projects by revenue on hover/click
            try:
                if not df_re.empty:
                    if 'projekt_name' not in df_re.columns:
                        df_re['projekt_name'] = None
                    df_proj_sum = df_re.groupby('projekt_name', dropna=False)['nettobetrag'].sum().reset_index()
                    df_proj_sum = df_proj_sum.sort_values('nettobetrag', ascending=False)
                    total_umsatz = float(df_proj_sum['nettobetrag'].sum())
                    rows_html = ''
                    topn = df_proj_sum.head(8)
                    for _, r in topn.iterrows():
                        pname = r['projekt_name'] if pd.notnull(r['projekt_name']) and r['projekt_name'] != '' else 'Unbekannt'
                        rows_html += f"<div class=\"row\"><div>{pname}</div><div>{float(r['nettobetrag']):,.2f} €</div></div>"
                    others = df_proj_sum.iloc[8:]['nettobetrag'].sum() if len(df_proj_sum) > 8 else 0.0
                    if others and others > 0:
                        rows_html += f"<div class=\"row\"><div>Weitere</div><div>{others:,.2f} €</div></div>"
                else:
                    rows_html = '<div class="row"><div>Keine Rechnungen</div><div>0.00 €</div></div>'
                    total_umsatz = 0.0
            except Exception:
                rows_html = '<div class="row"><div>Keine Daten</div><div>0.00 €</div></div>'
                total_umsatz = 0.0

            import random as _rand
            unique_id_u = f"ums_{_rand.randint(1000,9999)}"
            html_template_u = f"""<style>
.{unique_id_u}{{position:relative;display:inline-block;width:100%;margin:0;padding:0;}}
.{unique_id_u} .label{{font-size:12px;color:#ffffff;opacity:0.7;}}
.{unique_id_u} .value{{white-space:nowrap;font-size:clamp(14px,3vw,28px);font-weight:600;color:#00DD00;cursor:pointer;margin-top:4px;user-select:none;}}
.{unique_id_u} .breakdown{{display:none;position:absolute;left:0;top:100%;transform:translateY(8px);background:#2a2a2a;border:2px solid #888;padding:12px;border-radius:6px;box-shadow:0 10px 30px rgba(0,0,0,0.5);min-width:280px;z-index:100000;pointer-events:auto;color:#ffffff;}}
.{unique_id_u}.show .breakdown, .{unique_id_u} input:checked + .breakdown{{display:block;}}
.{unique_id_u} .row{{display:flex;justify-content:space-between;margin:0 0 8px 0;padding:4px 0;font-size:13px;line-height:1.2;}}
.{unique_id_u} .total{{font-weight:700;margin-top:8px;border-top:1px solid #666;padding-top:8px;text-align:right;}}
</style>
<div class="{unique_id_u}" id="{unique_id_u}">
<div class="label">Umsatz im gewählten Zeitraum</div>
<label class="value" for="{unique_id_u}_cb">{zeitraum_umsatz:,.2f}&nbsp;€</label>
<input type="checkbox" id="{unique_id_u}_cb" style="display:none;">
<div class="breakdown">{rows_html}<div class="total">Gesamt: {total_umsatz:,.2f} €</div></div>
</div>
<script>
(function(){{
    const cont = document.getElementById('{unique_id_u}');
    const cb = document.getElementById('{unique_id_u}_cb');
    if(!cont || !cb) return;
    const breakdown = cont.querySelector('.breakdown');
    let hideTimeout = null;
    function clearHideTimeout(){{ if(hideTimeout){{ clearTimeout(hideTimeout); hideTimeout = null; }} }}
    function show(){{ clearHideTimeout(); cont.classList.add('show'); }}
    function hide(){{ clearHideTimeout(); if(!cb.checked){{ hideTimeout = setTimeout(function(){{ cont.classList.remove('show'); hideTimeout = null; }}, 150); }} }}
    cont.addEventListener('mouseenter', show);
    cont.addEventListener('mouseleave', hide);
    if(breakdown){{
        breakdown.addEventListener('mouseenter', show);
        breakdown.addEventListener('mouseleave', hide);
    }}
    document.addEventListener('click', function(e){{
        if(!cont.contains(e.target)){{
            cb.checked = false;
            cont.classList.remove('show');
        }} else {{
            if(e.target.tagName.toLowerCase() === 'label' && e.target.getAttribute('for') === '{unique_id_u}_cb'){{
                cb.checked = !cb.checked;
                if(cb.checked){{ show(); }} else {{ cont.classList.remove('show'); }}
            }}
        }}
    }});
}})();
</script>"""
            st.markdown(html_template_u, unsafe_allow_html=True)

            # Build breakdown values (zeitraum-basiert)
            try:
                df_son = pd.read_sql("SELECT betrag, letztes_aenderungsdatum FROM sonstige_ausgaben WHERE benutzername = %s", engine, params=(user,))
                if not df_son.empty:
                    df_son["letztes_aenderungsdatum"] = pd.to_datetime(df_son["letztes_aenderungsdatum"]).dt.date
                    mask_son = (df_son["letztes_aenderungsdatum"] >= pd.to_datetime(start_date).date()) & (df_son["letztes_aenderungsdatum"] <= pd.to_datetime(end_date).date())
                    sonstige_period_total = float(df_son.loc[mask_son, "betrag"].sum())
                else:
                    sonstige_period_total = 0.0
            except Exception:
                sonstige_period_total = 0.0

            try:
                if 'df_ausgaben_lohn' in locals() and not df_ausgaben_lohn.empty:
                    df_ausgaben_lohn["erstellt_am"] = pd.to_datetime(df_ausgaben_lohn["erstellt_am"]).dt.date
                    mask_lohn_pdf = (df_ausgaben_lohn["erstellt_am"] >= pd.to_datetime(start_date).date()) & (df_ausgaben_lohn["erstellt_am"] <= pd.to_datetime(end_date).date())
                    ausgaben_lohn_period_total = float(df_ausgaben_lohn.loc[mask_lohn_pdf, "betrag"].sum())
                else:
                    ausgaben_lohn_period_total = 0.0
            except Exception:
                ausgaben_lohn_period_total = 0.0

            lohn_period_total = float(lohn_total) + float(ausgaben_lohn_period_total)
            try:
                mat_period_total = float(mat_total)
            except Exception:
                mat_period_total = 0.0
            try:
                geraet_period_total = float(geraet_total)
            except Exception:
                geraet_period_total = 0.0

            total_break = sonstige_period_total + mat_period_total + lohn_period_total + geraet_period_total

            unique_id = f"ausg_{_rand.randint(1000,9999)}"
            html_template = f"""<style>
.{unique_id}{{position:relative;display:inline-block;width:100%;margin:0;padding:0;}}
.{unique_id} .label{{font-size:12px;color:#ffffff;opacity:0.7;}}
.{unique_id} .value{{white-space:nowrap;font-size:clamp(14px,3vw,28px);font-weight:600;color:#FF4444;cursor:pointer;margin-top:4px;user-select:none;}}
.{unique_id} .breakdown{{display:none;position:absolute;left:0;top:100%;transform:translateY(8px);background:#2a2a2a;border:2px solid #888;padding:12px;border-radius:6px;box-shadow:0 10px 30px rgba(0,0,0,0.5);min-width:280px;z-index:100000;pointer-events:auto;color:#ffffff;}}
.{unique_id}.show .breakdown, .{unique_id} input:checked + .breakdown{{display:block;}}
.{unique_id} .row{{display:flex;justify-content:space-between;margin:0 0 8px 0;padding:4px 0;font-size:13px;line-height:1.2;}}
.{unique_id} .total{{font-weight:700;margin-top:8px;border-top:1px solid #666;padding-top:8px;text-align:right;}}
</style>
<div class="{unique_id}" id="{unique_id}">
<div class="label">Ausgaben im gewählten Zeitraum</div>
<label class="value" for="{unique_id}_cb">{zeitraum_ausgaben:,.2f}&nbsp;€</label>
<input type="checkbox" id="{unique_id}_cb" style="display:none;">
<div class="breakdown">
<div class="row"><div>Sonstige Ausgaben</div><div>{sonstige_period_total:,.2f} €</div></div>
<div class="row"><div>Materialkosten</div><div>{mat_period_total:,.2f} €</div></div>
<div class="row"><div>Lohn (inkl. Lohn-PDF)</div><div>{lohn_period_total:,.2f} €</div></div>
<div class="row"><div>Gerätekosten</div><div>{geraet_period_total:,.2f} €</div></div>
<div class="total">Gesamt: {total_break:,.2f} €</div>
</div>
</div>
<script>
(function(){{
    const cont = document.getElementById('{unique_id}');
    const cb = document.getElementById('{unique_id}_cb');
    if(!cont || !cb) return;
    const breakdown = cont.querySelector('.breakdown');
    let hideTimeout = null;
    function clearHideTimeout(){{ if(hideTimeout){{ clearTimeout(hideTimeout); hideTimeout = null; }} }}
    function show(){{ clearHideTimeout(); cont.classList.add('show'); }}
    function hide(){{ clearHideTimeout(); if(!cb.checked){{ hideTimeout = setTimeout(function(){{ cont.classList.remove('show'); hideTimeout = null; }}, 150); }} }}
    cont.addEventListener('mouseenter', show);
    cont.addEventListener('mouseleave', hide);
    if(breakdown){{
        breakdown.addEventListener('mouseenter', show);
        breakdown.addEventListener('mouseleave', hide);
    }}
    document.addEventListener('click', function(e){{
        if(!cont.contains(e.target)){{
            cb.checked = false;
            cont.classList.remove('show');
        }} else {{
            if(e.target.tagName.toLowerCase() === 'label' && e.target.getAttribute('for') === '{unique_id}_cb'){{
                cb.checked = !cb.checked;
                if(cb.checked){{ show(); }} else {{ cont.classList.remove('show'); }}
            }}
        }}
    }});
}})();
</script>"""
            st.markdown(html_template, unsafe_allow_html=True)

            unique_id_g = f"gew_{_rand.randint(1000,9999)}"
            html_template_g = f"""<style>
.{unique_id_g}{{position:relative;display:inline-block;width:100%;margin:0;padding:0;}}
.{unique_id_g} .label{{font-size:12px;color:#ffffff;opacity:0.7;}}
.{unique_id_g} .value{{white-space:nowrap;font-size:clamp(14px,3vw,28px);font-weight:600;color:#4488FF;cursor:pointer;margin-top:4px;user-select:none;}}
.{unique_id_g} .breakdown{{display:none;position:absolute;left:0;top:100%;transform:translateY(8px);background:#2a2a2a;border:2px solid #888;padding:12px;border-radius:6px;box-shadow:0 10px 30px rgba(0,0,0,0.5);min-width:280px;z-index:100000;pointer-events:auto;color:#ffffff;}}
.{unique_id_g}.show .breakdown, .{unique_id_g} input:checked + .breakdown{{display:block;}}
.{unique_id_g} .row{{display:flex;justify-content:space-between;margin:0 0 8px 0;padding:4px 0;font-size:13px;line-height:1.2;}}
</style>
<div class="{unique_id_g}" id="{unique_id_g}">
<div class="label">Gewinn im gewählten Zeitraum</div>
<label class="value" for="{unique_id_g}_cb">{zeitraum_gewinn:,.2f}&nbsp;€</label>
<input type="checkbox" id="{unique_id_g}_cb" style="display:none;">
<div class="breakdown">
<div class="row"><div>Umsatz</div><div>{zeitraum_umsatz:,.2f} €</div></div>
<div class="row"><div>Ausgaben</div><div>{zeitraum_ausgaben:,.2f} €</div></div>
</div>
</div>
<script>
(function(){{
    const cont = document.getElementById('{unique_id_g}');
    const cb = document.getElementById('{unique_id_g}_cb');
    if(!cont || !cb) return;
    const breakdown = cont.querySelector('.breakdown');
    let hideTimeout = null;
    function clearHideTimeout(){{ if(hideTimeout){{ clearTimeout(hideTimeout); hideTimeout = null; }} }}
    function show(){{ clearHideTimeout(); cont.classList.add('show'); }}
    function hide(){{ clearHideTimeout(); if(!cb.checked){{ hideTimeout = setTimeout(function(){{ cont.classList.remove('show'); hideTimeout = null; }}, 150); }} }}
    cont.addEventListener('mouseenter', show);
    cont.addEventListener('mouseleave', hide);
    if(breakdown){{
        breakdown.addEventListener('mouseenter', show);
        breakdown.addEventListener('mouseleave', hide);
    }}
    document.addEventListener('click', function(e){{
        if(!cont.contains(e.target)){{
            cb.checked = false;
            cont.classList.remove('show');
        }} else {{
            if(e.target.tagName.toLowerCase() === 'label' && e.target.getAttribute('for') === '{unique_id_g}_cb'){{
                cb.checked = !cb.checked;
                if(cb.checked){{ show(); }} else {{ cont.classList.remove('show'); }}
            }}
        }}
    }});
}})();
</script>"""
            st.markdown(html_template_g, unsafe_allow_html=True)
import sqlite3
import bcrypt
import random
import json
import requests
import re
# PayPal Configuration
PAYPAL_CLIENT_ID = "AW7r-xOBk6BwvghQbPkHb8eX6THqsTUB0SIPZgo6wx3NWoQ2ErfelfI-Ozn2_mgJM9k1RungRJUzI--_"
PAYPAL_CLIENT_SECRET = "EPUcVR-kLA5VhE33TjyaQe09Yv0mBeqe1aQuW3QQyADUek57Hk7gh-m1hZvPuFeZj56nn_-pM7d0_diG"
PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com"  # Sandbox environment
PAYPAL_BASE_URL = "http://localhost:8501"  # Base URL for the Streamlit app
PAYPAL_SUBSCRIPTION_PRICE = "45.99"  # Subscription price in EUR
PAYPAL_RETURN_URL = f"{PAYPAL_BASE_URL}?page=payment_success"  # PayPal will append the subscription ID
PAYPAL_CANCEL_URL = f"{PAYPAL_BASE_URL}?page=payment_cancel"

def clean_email(email: str) -> str:
    """Clean and validate email address for PayPal"""
    if not email or '@' not in email:
        return "no-email@example.com"
    
    # Split email into local and domain parts
    local, domain = email.split('@', 1)
    
    # Clean local part
    local = local.replace('ä', 'a').replace('ö', 'o').replace('ü', 'u').replace('ß', 'ss')
    local = re.sub(r'[^a-zA-Z0-9._-]', '', local)
    
    # Clean domain part
    domain = domain.replace('ä', 'a').replace('ö', 'o').replace('ü', 'u').replace('ß', 'ss')
    domain = re.sub(r'[^a-zA-Z0-9.-]', '', domain)
    
    # If parts are empty after cleaning, return default
    if not local or not domain:
        return "no-email@example.com"
    
    return f"{local}@{domain}"

def clean_paypal_id(text: str) -> str:
    """Clean text for use as PayPal ID by removing special characters and spaces"""
    # Replace German special characters
    text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    # Remove all special characters and spaces, keep only alphanumeric
    text = re.sub(r'[^a-zA-Z0-9]', '', text)
    return text

def get_paypal_access_token():
    """Get PayPal OAuth access token"""
    url = f"{PAYPAL_API_BASE}/v1/oauth2/token"
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en_US"
    }
    data = {"grant_type": "client_credentials"}
    try:
        response = requests.post(url, auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET), 
                               headers=headers, data=data)
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            st.error(f"PayPal Token Error: {response.status_code}")
            print(f"PayPal Error Response: {response.text}")
            return None
    except Exception as e:
        st.error(f"PayPal Connection Error: {str(e)}")
        print(f"PayPal Exception: {str(e)}")
        return None

def get_paypal_plans():
    """List all available billing plans"""
    access_token = get_paypal_access_token()
    if not access_token:
        return []
    
    url = f"{PAYPAL_API_BASE}/v1/billing/plans"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            plans = response.json().get("plans", [])
            return plans
        else:
            print(f"Error fetching plans: {response.status_code}")
            print(f"Response: {response.text}")
            return []
    except Exception as e:
        print(f"Exception fetching plans: {str(e)}")
        return []

def get_paypal_plan_details(plan_id):
    """Get detailed information about a specific plan"""
    access_token = get_paypal_access_token()
    if not access_token:
        return None
    
    url = f"{PAYPAL_API_BASE}/v1/billing/plans/{plan_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching plan details: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"Exception fetching plan details: {str(e)}")
        return None

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

# --- ALTE SQLite-MIGRATIONS-FUNKTIONEN ENTFERNT ---
# Alle Tabellen werden bereits über ensure_schema() erstellt

import os
import subprocess
import sys
import pandas as pd
import plotly.express as px
import calendar
import sqlalchemy
# === Automatische Installation fehlender Pakete ===
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

from datetime import date, datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
try:
    import streamlit as st
    from streamlit_option_menu import option_menu

    from sklearn.linear_model import LinearRegression
    from sqlalchemy import create_engine
    from sqlalchemy import text
    # from reportlab.lib.pagesizes import A4  # Already imported above
    # from reportlab.pdfgen import canvas    # Already imported above
    # from io import BytesIO                 # Already imported above
    from datetime import date, datetime, timedelta
    import textwrap
except ImportError:
    install("streamlit")
    install("pandas")
    install("scikit-learn")
    install("sqlalchemy")
    import streamlit as st

    from sklearn.linear_model import LinearRegression
    from sqlalchemy import create_engine
    from streamlit_option_menu import option_menu
# === Datenbankverbindung ===
from sqlalchemy import create_engine, pool as sqlalchemy_pool
from sqlalchemy.pool import QueuePool
import atexit

@st.cache_resource
def get_engine():
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=1,           # Minimal: nur 1 Connection
        max_overflow=2,        # Max 3 Connections total
        pool_pre_ping=True,    # Teste Connection vor Nutzung  
        pool_recycle=600,      # Recycle nach 10 minuten
        echo=False
    )
    # Cleanup bei App Ende
    def cleanup():
        engine.dispose()
    atexit.register(cleanup)
    return engine

engine = get_engine()

# Schema wird initialisiert nachdem engine gecacht wurde
try:
    ensure_schema()
except Exception as e:
    print(f"Note: Schema initialization hatte einen Fehler: {str(e)[:150]}")
    # App lädt trotzdem, aber wo Tabellen fehlen gibt es Fehler

# Hilfsfunktion um Connections aggressiv freizugeben
def cleanup_connections():
    engine.dispose()

# ====== PERFORMANCE CACHE FUNCTIONS ======
# Häufige Lookups cachen um Datenbankabfragen zu reduzieren

@st.cache_data(ttl=600)
def get_projekt_name(projekt_id):
    """Cache: Projekt-Namen nachschlagen"""
    df = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(projekt_id,))
    return df['name'].iloc[0] if not df.empty else "Unknown"

@st.cache_data(ttl=600)
def get_all_mitarbeiter():
    """Cache: Alle Mitarbeiter laden"""
    return pd.read_sql("SELECT benutzername, vorname, nachname, rolle FROM mitarbeiter", engine)

@st.cache_data(ttl=300)
def get_mitarbeiter_by_project(projekt_id, user):
    """Cache: Mitarbeiter für bestimmtes Projekt"""
    return pd.read_sql(
        "SELECT benutzername FROM mitarbeiter_projekte WHERE projekt_id = %s",
        engine, params=(projekt_id,)
    )

@st.cache_data(ttl=600)
def get_materialien_for_project(projekt_id, user):  
    """Cache: Materialien für Projekt"""
    return pd.read_sql(
        "SELECT material, menge, einheit FROM materialien WHERE projekt_id = %s AND benutzername = %s",
        engine, params=(projekt_id, user)
    )

# --- Migration: nutzerentwicklung_log Tabelle sicherstellen ---
try:
    with engine.begin() as conn:
        conn.exec_driver_sql('''
            CREATE TABLE IF NOT EXISTS nutzerentwicklung_log (
                id SERIAL PRIMARY KEY,
                benutzername TEXT NOT NULL,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
except Exception as e:
    print(f"Note: nutzerentwicklung_log migration skipped: {str(e)[:100]}")

# --- Migration: webhook_log Tabelle sicherstellen ---
try:
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS webhook_log (
                id SERIAL PRIMARY KEY,
                benutzername TEXT,
                event_type TEXT,
                status TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
except Exception as e:
    print(f"Note: webhook_log migration skipped: {str(e)[:100]}")

# === Archivierungs-Spalte sicherstellen ===
try:
    with engine.begin() as conn:
        try:
            conn.exec_driver_sql("ALTER TABLE projekte ADD COLUMN archiviert_am TEXT DEFAULT NULL")
        except Exception:
            pass  # Column bereits vorhanden
except Exception as e:
    print(f"Note: Archivierungs-Spalte migration skipped: {str(e)[:100]}")

# === Datenbankverbindung ===
# PostgreSQL-Tabellen sind bereits in ensure_schema() erstellt
try:
    with engine.begin() as conn:
        # Überprüfe ob lohnabrechnung_archiv Tabelle existiert (für Archivierung von PDF-Daten)
        try:
            conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS lohnabrechnung_archiv (
                    id SERIAL PRIMARY KEY,
                    jahr INTEGER,
                    monat INTEGER,
                    benutzername TEXT,
                    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pdf_data BYTEA
                )
            """)
        except Exception as e:
            print(f"Warnung: lohnabrechnung_archiv existiert möglicherweise bereits: {e}")
        try:
            conn.exec_driver_sql("""
                INSERT INTO checklisten_gesamtkommentar (projekt_id, benutzername, kommentar, zeitaufwand, datum)
                VALUES (1, 'testuser', 'Test-Kommentar', '15', '2025-09-28')
            """)
        except Exception:
            pass
except Exception as e:
    print(f"Note: lohnabrechnung_archiv and checklisten migrations skipped: {str(e)[:100]}")

# ====================================
# ALTE SQLite-CODE (wird übersprungen)
# ====================================
try:
    with engine.begin() as conn:
        # Sicherstellen, dass die Tabelle 'projekte' existiert, bevor darauf zugegriffen wird
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS projekte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                projekt_name TEXT,
                benutzername TEXT,
                erstellt_am TEXT
            )
        """)
except Exception:
    pass

# ==== FORTFÜHRUNG DES PROGRAMS - ALLE ALTEN SQLite CREATE TABLE BEFEHLE WERDEN ÜBERSPRUNGEN ====
# PostgreSQL-Tabellen wurden bereits von ensure_schema() erstellt
# Die folgenden Zeilen sind Teil des alten SQLite-Codes und werden nicht mehr ausgeführt

# ====================================================================
# ALL OLD SQLite MIGRATION CODE REMOVED
# Postgres migration is handled by ensure_schema() at startup
# ====================================================================

# ========== DATENSCHUTZ & AGB FUNKTIONEN ==========
def load_agb():
    """Lädt AGB aus Datei"""
    try:
        with open("AGB.md", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "AGB konnten nicht geladen werden. Bitte kontaktieren Sie den Support."

def load_datenschutz():
    """Lädt Datenschutzerklärung aus Datei"""
    try:
        with open("DATENSCHUTZ.md", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Datenschutzerklärung konnte nicht geladen werden. Bitte kontaktieren Sie den Support."

def show_agb_with_scrollbar():
    """Zeigt AGB mit Scrollbar im Container"""
    agb_content = load_agb()
    st.markdown(
        f"""
        <div style="
            height: 400px; 
            overflow-y: scroll; 
            border: 1px solid #ddd; 
            padding: 15px; 
            border-radius: 5px;
            background-color: #f9f9f9;
        ">
        {agb_content.replace(chr(10), '<br>')}
        </div>
        """, 
        unsafe_allow_html=True
    )

def show_datenschutz_with_scrollbar():
    """Zeigt Datenschutzerklärung mit Scrollbar im Container"""
    ds_content = load_datenschutz()
    st.markdown(
        f"""
        <div style="
            height: 400px; 
            overflow-y: scroll; 
            border: 1px solid #ddd; 
            padding: 15px; 
            border-radius: 5px;
            background-color: #f9f9f9;
        ">
        {ds_content.replace(chr(10), '<br>')}
        </div>
        """, 
        unsafe_allow_html=True
    )

# ========== ENDE DATENSCHUTZ & AGB FUNKTIONEN ==========

def agb_akzeptieren_page():
    """Zwischenseite für AGB/Datenschutz Akzeptanz - ZWISCHEN Konto-Erstellung und Payment"""
    st.set_page_config(page_title="AGB & Datenschutz", layout="centered")
    
    st.title("AGB & Datenschutzerklärung")
    st.info("Bitte lesen und akzeptieren Sie unsere rechtlichen Dokumente, um fortzufahren.")
    
    # Download Buttons
    st.markdown("### 📥 Dokumente herunterladen:")
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            with open("AGB.md", "r", encoding="utf-8") as f:
                agb_text = f.read()
            st.download_button(
                "AGB Download",
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
                "Datenschutz Download",
                ds_text,
                file_name="DATENSCHUTZ.md",
                mime="text/markdown",
                use_container_width=True
            )
        except:
            st.error("Datenschutz nicht verfügbar")
    
    st.markdown("---")
    st.markdown("### 📖 Oder hier mit Scrollbar lesen:")
    
    # Tabs mit Scrollbar
    tab_agb, tab_ds = st.tabs(["AGB", "Datenschutzerklärung"])
    
    with tab_agb:
        show_agb_with_scrollbar()
    
    with tab_ds:
        show_datenschutz_with_scrollbar()
    
    st.markdown("---")
    st.markdown("## Zustimmung erforderlich")
    
    # Checkboxes
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        agb_accepted = st.checkbox("", value=False, key="agb_check")
    with col2:
        st.markdown("Ich habe die **AGB** gelesen und stimme ihnen zu")
    
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        datenschutz_accepted = st.checkbox("", value=False, key="ds_check")
    with col2:
        st.markdown("Ich habe die **Datenschutzerklärung** zur Kenntnis genommen und akzeptiere sie")
    
    st.markdown("---")
    
    # Button zum Akzeptieren
    if st.button("Fortfahren zum Payment", type="primary", use_container_width=True):
        if not agb_accepted:
            st.error("Sie müssen den AGB zustimmen, um fortzufahren.")
            st.stop()
        
        if not datenschutz_accepted:
            st.error("Sie müssen der Datenschutzerklärung zustimmen, um fortzufahren.")
            st.stop()
        
        # Update Database mit Akzeptanz
        try:
            from datetime import datetime
            now = datetime.now()
            
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    """UPDATE benutzer 
                       SET agb_accepted = %s, datenschutz_accepted = %s,
                           agb_accepted_at = %s, datenschutz_accepted_at = %s
                       WHERE account_id = %s""",
                    (True, True, now, now, st.session_state.account_id)
                )
            
            st.session_state.agb_accepted = True
            st.session_state.datenschutz_accepted = True
            
            st.success("Zustimmung gespeichert!")
            st.session_state.page = "payment"
            st.rerun()
        except Exception as e:
            st.error(f"Fehler beim Speichern: {str(e)}")
    
    # Zurück-Button
    if st.button("← Zurück", use_container_width=True):
        st.session_state.page = "login"
        st.session_state.user = None
        st.session_state.account_id = None
        st.rerun()

def login_page():
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
                st.error(f"🔒 {lock_msg_standard or lock_msg_dev}")
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
                        st.error(f"🔒 {msg}")
                    st.stop()
                
                # Standard Login
                try:
                    # Verify user credentials - tables already created by ensure_schema()
                    
                    # Now try to find the user
                    df_users = pd.read_sql("""
                        SELECT benutzername, passwort, account_id, email, payment_status 
                        FROM benutzer 
                        WHERE benutzername = %s
                    """, engine, params=(benutzer,))
                    
                    
                    if not df_users.empty:
                        stored_password = df_users.iloc[0]["passwort"]
                        if verify_password(passwort, stored_password):
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
                            
                            # ✅ Prüfe ob Firmenprofil-Daten vollständig sind
                            required_fields = {
                                "firmenname": "Firmenname",
                                "gesellschaftsform": "Gesellschaftsform",
                                "firmenadresse": "Adresse",
                                "firmentelefon": "Telefon",
                                "standard_rechnungsnummer": "Rechnungsnummer"
                            }
                            missing_fields = [field for field in required_fields.keys() if not st.session_state.get(field)]
                            
                            # Nach Login explizit weiterleiten:
                            if missing_fields and payment_status == "ACTIVE":
                                # Firmendaten unvollständig - zur Setup-Seite
                                st.session_state.page = "setup_company_profile"
                                st.session_state.login_attempted = True
                                st.info("Bitte vervollständigen Sie Ihr Firmenprofil...")
                                st.rerun()
                            elif payment_status == "ACTIVE":
                                st.session_state.page = "app"
                                st.session_state.login_attempted = True
                                st.success("Login erfolgreich. Weiterleitung zur Anwendung...")
                                st.rerun()
                            else:
                                st.session_state.page = "payment"
                                st.session_state.login_attempted = True
                                st.warning(f"⏳ Login erfolgreich. Status: {payment_status} - Weiterleitung zum Payment-Screen...")
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
                                st.error(f"🔒 {lock_msg}")
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
                            st.error(f"🔒 {lock_msg}")
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
            st.error(f"🔒 {lock_msg}")
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
                        st.error(f"🔒 {lock_msg}")
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
                    st.error(f"🔒 {lock_msg}")

# === Mitarbeiter Management Seite ===
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

def mitarbeiter_page():
    """Mitarbeiter-Project Page - Actual project work page"""
    pass  # Content is handled by bau_app_page() with nav="Mitarbeiterprojekt"

# === Developer Auth Page ===
def dev_auth_page():
    """Developer Authentication Page"""
    st.set_page_config(page_title="Developer", layout="centered")
    st.title("Developer-Bereich")
    st.warning("Sie befinden sich im Developer-Modus.")
    if st.button("Weiter zur App"):
        st.session_state.page = "app"
        st.rerun()

# === Developer Page ===
def dev_page():
    """Developer Debug Page"""
    st.set_page_config(page_title="Developer Debug", layout="wide")
    st.title("Developer-Debug")
    st.write("Session State:")
    st.json(dict(st.session_state))
    if st.button("← Zurück"):
        st.session_state.page = "app"
        st.rerun()

# === Delete Account Confirmation ===
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

# === PDF Generator Functions ===
def generate_pauschal_invoice_pdf(projekt_name, empfaenger_name, empfaenger_adresse, pauschalbetrag, rechnungsnummer, leistungszeitraum_start, leistungszeitraum_ende):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Helper: sichere Konvertierung in str (None/bytes -> unicode string)
    def _s(value):
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            try:
                return value.decode("utf-8")
            except Exception:
                try:
                    return value.decode("latin-1", errors="replace")
                except Exception:
                    return str(value)
        return str(value)

    # Firmendaten aus Session State (sicher konvertiert)
    firmenname = _s(st.session_state.get("firmenname"))
    gesellschaftsform = _s(st.session_state.get("gesellschaftsform"))
    adresse = _s(st.session_state.get("firmenadresse"))
    telefon = _s(st.session_state.get("firmentelefon"))
    fax = _s(st.session_state.get("firmenfax"))
    # Stelle sicher, dass übergebene Werte Strings sind
    empfaenger_name = _s(empfaenger_name)
    empfaenger_adresse = _s(empfaenger_adresse)
    projekt_name = _s(projekt_name)
    
    # Logo hinzufügen (wenn vorhanden)
    logo_bytes = st.session_state.get("firmenlogo")
    y = height - 50  # Starting Y position
    if logo_bytes:
        try:
            from PIL import Image
            import io, os
            logo_img = Image.open(io.BytesIO(logo_bytes))
            max_width, max_height = 120, 60
            w, h = logo_img.size
            scale = min(max_width / w, max_height / h, 1.0)
            w_new, h_new = int(w * scale), int(h * scale)
            logo_img = logo_img.resize((w_new, h_new))
            logo_path = "_temp_logo.png"
            logo_img.save(logo_path)
            c.drawImage(logo_path, 50, height - 50 - h_new, width=w_new, height=h_new, mask='auto')
            os.remove(logo_path)
        except Exception as e:
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, height - 50, firmenname)
    else:
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, firmenname)

    # Kontaktdaten rechtsbündig
    right_x = 400
    y = height - 65
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(right_x + 150, y, "Anschrift")
    y -= 15
    c.setFont("Helvetica", 10)
    if gesellschaftsform.strip() == "Einzelunternehmen":
        c.drawRightString(right_x + 150, y, firmenname)
    else:
        c.drawRightString(right_x + 150, y, f"{firmenname} {gesellschaftsform.strip()}")
    y -= 15
    c.drawRightString(right_x + 150, y, adresse)
    y -= 50
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(right_x + 150, y, "Kontakt")
    y -= 15
    c.setFont("Helvetica", 10)
    if telefon:
        c.drawRightString(right_x + 150, y, f"Tel: {telefon}")
        y -= 15
    if fax:
        c.drawRightString(right_x + 150, y, f"Fax: {fax}")
        y -= 15

    # Empfänger
    c.drawString(50, height - 155, empfaenger_name)
    c.drawString(50, height - 170, empfaenger_adresse)

    # Projektinformationen
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 270, f"Projekt:")
    c.setFont("Helvetica", 10)
    c.drawString(125, height - 270, f"{projekt_name}")

    # Rechnungsinformationen
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 290, f"Rechnungsdatum:")
    c.drawString(185, height - 290, f"Rechnungsnummer:")
    c.drawString(350, height - 290, "Leistungszeitraum:")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 310, f"{date.today().strftime('%d.%m.%Y')}")
    c.drawString(185, height - 310, f"{rechnungsnummer}")
    c.drawString(350, height - 310, f"{leistungszeitraum_start.strftime('%d.%m.%Y')} bis {leistungszeitraum_ende.strftime('%d.%m.%Y')}")

    # Trennlinie
    c.setLineWidth(1)
    c.line(50, height - 320, width - 50, height - 320)

    # Pauschalbetrag
    y = height - 370
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Pauschale für die vereinbarten Leistungen zum Projekt {projekt_name}")
    c.drawString(450, y, f"{pauschalbetrag:.2f} €")
    y -= 30
    c.setFont("Helvetica-Bold", 12)
    mwst = pauschalbetrag*0.19
    nettobetrag = pauschalbetrag + mwst  

    c.setFont("Helvetica", 10)
    c.drawString(330, y, "Bruttobetrag:")
    c.drawString(450, y, f"{pauschalbetrag:.2f} €")
    y -= 20
    c.drawString(330, y, "zzgl. 19% MwSt.")
    c.drawString(450, y, f"{mwst:.2f} €")
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(330, y, "Gesamtbetrag:")
    c.drawString(450, y, f"{nettobetrag:.2f} €")

    y = 150
    # Zahlungsaufforderung
    c.setFont("Helvetica", 10)
    aufforderung_text = "Bitte überweisen Sie den Gesamtbetrag innerhalb von 14 Tagen auf das unten angegebene Konto."
    c.drawString(50, y, aufforderung_text)
    y -= 20
    c.drawString(50, y, "Bei Rückfragen stehen wir Ihnen jederzeit gerne zur Verfügung.")
    y -= 20

    # Untere Trennlinie
    c.setLineWidth(1)
    c.line(50, y, width - 50, y)
    y -= 20

    # Bankdaten in der Fußzeile (sicher konvertiert)
    bankname = _s(st.session_state.get("bankname"))
    iban = _s(st.session_state.get("iban"))
    bic = _s(st.session_state.get("bic"))
    geschaeftsfuehrer = _s(st.session_state.get("geschaeftsfuehrer"))
    telefon = _s(st.session_state.get("firmentelefon"))
    registergericht = _s(st.session_state.get("registergericht"))
    hrb_nummer = _s(st.session_state.get("hrb_nummer"))
    ustidnr = _s(st.session_state.get("ustidnr"))

    c.setFont("Helvetica", 7)
    c.drawString(50, y, "Anschrift:")
    if gesellschaftsform.strip() == "Einzelunternehmen":
        c.drawString(50, y-15, firmenname)
    else:
        c.drawString(50, y-15, f"{firmenname} {gesellschaftsform.strip()}")
    c.drawString(50, y-30, adresse)

    c.drawString(180, y, bankname)
    c.drawString(180, y-15, f"IBAN: {iban}")
    c.drawString(180, y-30, f"BIC: {bic}")

    c.drawString(300, y, "Geschäftsführer:")
    c.drawString(300, y-15, geschaeftsfuehrer)
    c.drawString(300, y-30, f"Tel.: {telefon}")

    c.drawString(400, y, registergericht)
    c.drawString(400, y-15, f"HRB: {hrb_nummer}")
    c.drawString(400, y-30, f"UStIdNr.: {ustidnr}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def generate_invoice_pdf_v2(projekt_name, empfaenger_name, empfaenger_adresse, positionen, arbeitsleistungen, rechnungsnummer, leistungszeitraum_start, leistungszeitraum_ende ,geraetepositionen=None):
    # Initialisierung wichtiger Variablen
    total = 0.0
    arbeits_total = 0.0
    geraetekosten_total = 0.0
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    firmenname = st.session_state.get("firmenname", "Böttcher-BAu") or ""
    gesellschaftsform = st.session_state.get("gesellschaftsform", "") or ""  
    adresse = st.session_state.get("firmenadresse", "") or ""
    telefon = st.session_state.get("firmentelefon", "") or ""
    fax = st.session_state.get("firmenfax", "") or ""
    # --- Seitenaufteilung ---
    from math import ceil
    # --- Positionen zusammenstellen: Material, Mitarbeiter, Geräte ---
    # Positionen sortiert und gruppiert
    material_positionen = []
    lohn_positionen = []
    geraet_positionen = []

    # Material positions
    for pos in positionen:
        name, menge, einheit, preis = pos
        if menge > 0:
            material_positionen.append((name, menge, einheit, preis))
    
    # Work services (no longer nested in material loop)
    for leistung in arbeitsleistungen:
        name = leistung["rolle"]
        menge = leistung["stunden"]
        einheit = "Stunden"
        preis = leistung["stundensatz"]
        if menge > 0:
            lohn_positionen.append((name, menge, einheit, preis))

    # Equipment positions
    if geraetepositionen and len(geraetepositionen) > 0:
        for pos in geraetepositionen:
            geraet = pos["geraet"]
            stunden = pos["stunden"]
            kosten = pos["betriebskosten"]
            if stunden > 0:
                geraet_positionen.append((geraet, stunden, "Stunden", kosten))
        # Positionen für Seitenaufteilung vorbereiten
    alle_positionen = []
    def add_block_with_header(header, positions, typ):
            alle_positionen.append((None, None, None, None, f"{typ}-Header"))
            for p in positions:
                alle_positionen.append((*p, typ))
    add_block_with_header("Material", material_positionen, "Material")
    add_block_with_header("Lohnaufwand", lohn_positionen, "Lohn")
    add_block_with_header("Gerätekosten", geraet_positionen, "Geraet")    # NEUE Seitenlogik: seitenweise, keine Dopplung
    max_pos_per_page = 20
    total_positions = len(alle_positionen)
    laufnummer = 1
    pos_index = 0
    page_num = 0
    while pos_index < total_positions:
        # --- HEADER: Draw on every page ---
        logo_bytes = st.session_state.get("firmenlogo")
        logo_ok = False
        if logo_bytes:
            try:
                from PIL import Image
                import io, os
                logo_img = Image.open(io.BytesIO(logo_bytes))
                max_width, max_height = 120, 60
                w, h = logo_img.size
                scale = min(max_width / w, max_height / h, 1.0)
                w_new, h_new = int(w * scale), int(h * scale)
                logo_img = logo_img.resize((w_new, h_new))
                logo_path = "_temp_logo.png"
                logo_img.save(logo_path)
                c.drawImage(logo_path, 50, height - 50 - h_new, width=w_new, height=h_new, mask='auto')
                os.remove(logo_path)
                logo_ok = True
            except Exception as e:
                print(f"Fehler beim Laden des Logos: {e}")
        if not logo_ok:
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, height - 50, firmenname)
        # Seitenzahl oben rechts
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(width - 50, height - 50, f"{str(page_num+1).zfill(2)}")
        # Adresse und Kontakt rechtsbündig
        c.setFont("Helvetica", 10)
        right_x = 400
        y_addr = height - 65
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(right_x + 150, y_addr, "Anschrift")
        y_addr -= 15
        c.setFont("Helvetica", 10)
        if gesellschaftsform.strip()  == "Einzelunternehmen":
            c.drawRightString(right_x + 150, y_addr, firmenname)
        else:
            c.drawRightString(right_x + 150, y_addr, f"{firmenname} {gesellschaftsform.strip()}")
        y_addr -= 15
        c.drawRightString(right_x + 150, y_addr, adresse)
        y_addr -= 50
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(right_x + 150, y_addr, "Kontakt")
        y_addr -= 15
        c.setFont("Helvetica", 10)
        if telefon:
            c.drawRightString(right_x + 150, y_addr, f"Tel: {telefon}")
            y_addr -= 15
        if fax:
            c.drawRightString(right_x + 150, y_addr, f"Fax: {fax}")
            y_addr -= 15
        # Rechnungsempfänger
        c.drawString(50, height - 120, f"")
        c.drawString(50, height - 155, empfaenger_name)
        c.drawString(50, height - 170, empfaenger_adresse)
        # Projekt
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, height - 270, f"Projekt:")
        c.setFont("Helvetica", 10)
        c.drawString(125, height - 270, f"{projekt_name}")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, height - 290, f"Rechnungsdatum:")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 310, f"{date.today().strftime('%d.%m.%Y')}")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(185, height - 290, f"Rechnungsnummer:")
        c.setFont("Helvetica", 10)
        c.drawString(185, height - 310, f"{rechnungsnummer}")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(350, height - 290, "Leistungszeitraum:")
        c.setFont("Helvetica", 10)
        c.drawString(350, height - 310, f"{leistungszeitraum_start.strftime('%d.%m.%Y')} bis {leistungszeitraum_ende.strftime('%d.%m.%Y')}")
        c.setLineWidth(1)
        c.setDash()
        c.line(50, height - 320, width - 50, height - 320)
        # Tabellenkopf
        y = height - 340
        if page_num > 0:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Fortsetzung der Positionen")
            y -= 25
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, "Pos.")
        c.drawString(100, y, "Bezeichnung")
        c.drawString(250, y, "Menge")
        c.drawString(300, y, "/Einheit")
        c.drawString(370, y, "E-Preis €")
        c.drawString(450, y, "Gesamt €")
        y -= 30
        c.setLineWidth(1)
        c.setDash()
        c.line(50, height - 350, width - 50, height - 350)
        c.setFont("Helvetica", 10)
        # Positionen für diese Seite
        count = 0
        while count < max_pos_per_page and pos_index < total_positions:
            name, menge, einheit, preis, typ = alle_positionen[pos_index]
            if typ.endswith("-Header"):
                # Prüfe, ob noch Platz für mindestens eine Position auf dieser Seite
                if count >= max_pos_per_page - 1 or pos_index + 1 >= total_positions or alle_positionen[pos_index + 1][4].endswith("-Header"):
                    break  # Header + Position auf nächste Seite verschieben
                # Header ausgeben
                if typ == "Material-Header":
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(100, y, "Materialaufwand")
                    y -= 20
                    c.setFont("Helvetica", 10)
                elif typ == "Lohn-Header":
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(100, y, "Lohnaufwand")
                    y -= 20
                    c.setFont("Helvetica", 10)
                elif typ == "Geraet-Header":
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(100, y, "Gerätekosten")
                    y -= 20
                    c.setFont("Helvetica", 10)
                pos_index += 1
                count += 1
            else:
                gesamt = menge * preis
                # Akkumuliere die Kosten je nach Typ
                if typ == "Material":
                    total += gesamt
                elif typ == "Geraet":
                    geraetekosten_total += gesamt
                c.drawString(50, y, f"{laufnummer:05d}")
                c.drawString(100, y, name)
                c.drawString(250, y, f"{menge:.2f}")
                c.drawString(300, y, f"{einheit}")
                c.drawString(370, y, f"{preis:.2f}")
                c.drawString(450, y, f"{gesamt:.2f}")
                laufnummer += 1
                y -= 20
                pos_index += 1
                count += 1
        page_num += 1
        # --- Fußzeile nur auf der letzten Seite und direkt nach den letzten Positionen ---
        if pos_index >= total_positions:
            arbeits_total = 0.0
            for leistung in arbeitsleistungen:
                name = leistung["rolle"]
                menge = leistung["stunden"]
                einheit = "Stunden"
                preis = leistung["stundensatz"]
                if menge > 0:
                    arbeits_total += menge * preis
            
            brutto = total + arbeits_total + geraetekosten_total
            mwst = brutto * 0.19
            nettobetrag = brutto + mwst
            y -= 25
            c.setFont("Helvetica", 10)
            c.drawString(330, y, "Bruttobetrag:")
            c.drawString(450, y, f"{brutto:.2f} €")
            y -= 10
            c.drawString(330, y, "zzgl. 19% MwSt.")
            c.drawString(450, y, f"{mwst:.2f} €")
            y -= 20
            c.setFont("Helvetica-Bold", 12)
            c.drawString(330, y, "Gesamtbetrag:")
            c.drawString(450, y, f"{nettobetrag:.2f} €")

            if y > 150:
                y = 150

                aufforderung_text = "Bitte überweisen Sie den Gesamtbetrag innerhalb von 14 Tagen auf das unten angegebene Konto."
                c.setFont("Helvetica", 10)
                c.drawString(50, y, aufforderung_text)
                # Gesamtbetrag bleibt rechts
                # Nächste Zeile für Rückfragen
                y -= 20
                c.drawString(50, y, "Bei Rückfragen stehen wir Ihnen jederzeit gerne zur Verfügung.")
                # Linie erst darunter
                y -= 20
                c.setLineWidth(1)
                c.setDash()
                c.line(50, y, width - 50, y)
                y -= 20
                # Prüfe, ob genug Platz für Fußzeile (ca. 60px)
                # Bankdaten etc. wie gehabt
                firmenname = st.session_state.get("firmenname", "")
                gesellschaftsform = st.session_state.get("gesellschaftsform", "")
                adresse = st.session_state.get("firmenadresse", "")
                bankname = st.session_state.get("bankname", "")
                if bankname is None:
                    bankname = ""
                iban = st.session_state.get("iban", "")
                bic = st.session_state.get("bic", "")
                geschaeftsfuehrer = st.session_state.get("geschaeftsfuehrer", "")
                if geschaeftsfuehrer is None:
                    geschaeftsfuehrer = ""
                telefon = st.session_state.get("firmentelefon", "")
                registergericht = st.session_state.get("registergericht", "")
                hrb_nummer = st.session_state.get("hrb_nummer", "")
                ustidnr = st.session_state.get("ustidnr", "")
                c.setFont("Helvetica", 7)
                c.drawString(50, y, "Anschrift:")
                if gesellschaftsform.strip() == "Einzelunternehmen":
                    c.drawString(50, y-15, firmenname)
                else:
                    c.drawString(50, y-15, f"{firmenname} {gesellschaftsform.strip()}")
                c.drawString(50, y-30, adresse)
                c.setFont("Helvetica", 7)
                c.drawString(180, y, bankname)
                c.drawString(180, y-15, f"IBAN: {iban}")
                c.drawString(180, y-30, f"BIC: {bic}")
                c.setFont("Helvetica", 7)
                c.drawString(300, y, "Geschäftsführer:")
                c.drawString(300, y-15, geschaeftsfuehrer)
                c.drawString(300, y-30, f"Tel.: {telefon}")
                c.setFont("Helvetica", 7)
                c.drawString(400, y, registergericht)
                c.drawString(400, y-15, f"HRB: {hrb_nummer}")
                c.drawString(400, y-30, f"UStIdNr.: {ustidnr}")
            else:
                c.showPage()
                page_num += 1
                y = 150
                aufforderung_text = "Bitte überweisen Sie den Gesamtbetrag innerhalb von 14 Tagen auf das unten angegebene Konto."
                c.setFont("Helvetica", 10)
                c.drawString(50, y, aufforderung_text)
                # Gesamtbetrag bleibt rechts
                # Nächste Zeile für Rückfragen
                y -= 20
                c.drawString(50, y, "Bei Rückfragen stehen wir Ihnen jederzeit gerne zur Verfügung.")
                # Linie erst darunter
                y -= 20
                c.setLineWidth(1)
                c.setDash()
                c.line(50, y, width - 50, y)
                y -= 20
                # Prüfe, ob genug Platz für Fußzeile (ca. 60px)
                # Bankdaten etc. wie gehabt
                firmenname = st.session_state.get("firmenname", "")
                gesellschaftsform = st.session_state.get("gesellschaftsform", "")
                adresse = st.session_state.get("firmenadresse", "")
                bankname = st.session_state.get("bankname", "")
                if bankname is None:
                    bankname = ""
                iban = st.session_state.get("iban", "")
                bic = st.session_state.get("bic", "")
                geschaeftsfuehrer = st.session_state.get("geschaeftsfuehrer", "")
                if geschaeftsfuehrer is None:
                    geschaeftsfuehrer = ""
                telefon = st.session_state.get("firmentelefon", "")
                registergericht = st.session_state.get("registergericht", "")
                hrb_nummer = st.session_state.get("hrb_nummer", "")
                ustidnr = st.session_state.get("ustidnr", "")
                c.setFont("Helvetica", 7)
                c.drawString(50, y, "Anschrift:")
                if gesellschaftsform.strip() == "Einzelunternehmen":
                    c.drawString(50, y-15, firmenname)
                else:
                    c.drawString(50, y-15, f"{firmenname} {gesellschaftsform.strip()}")
                c.drawString(50, y-30, adresse)
                c.setFont("Helvetica", 7)
                c.drawString(180, y, bankname)
                c.drawString(180, y-15, f"IBAN: {iban}")
                c.drawString(180, y-30, f"BIC: {bic}")
                c.setFont("Helvetica", 7)
                c.drawString(300, y, "Geschäftsführer:")
                c.drawString(300, y-15, geschaeftsfuehrer)
                c.drawString(300, y-30, f"Tel.: {telefon}")
                c.setFont("Helvetica", 7)
                c.drawString(400, y, registergericht)
                c.drawString(400, y-15, f"HRB: {hrb_nummer}")
                c.drawString(400, y-30, f"UStIdNr.: {ustidnr}")
        c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# === Payment/Abonnement Seite ===
def payment_page():
    """PayPal Subscription Payment Page"""
    if st.session_state.get("payment_status") == "ACTIVE":
        st.session_state.page = "app"
        st.rerun()
    else:
        # Payment page - show PayPal subscription button
        st.set_page_config(page_title="Zahlung", layout="centered")
        st.markdown("# 💳 Abonnement erforderlich")
        st.write("Um die ETA Anwendung zu nutzen, benötigen Sie ein aktives Abonnement.")
        
        # Get available plans - find first ACTIVE one
        st.info("⏳ Plan wird geladen...")
        plans = get_paypal_plans()
        
        active_plan = None
        for plan in plans:
            if plan.get("status") == "ACTIVE":
                active_plan = plan
                break
        
        if not active_plan:
            st.error("Keine aktiven Abonnement-Pläne verfügbar. Bitte versuchen Sie es später erneut.")
            st.stop()
        
        # Get detailed plan information
        plan_id = active_plan.get("id")
        plan_details = get_paypal_plan_details(plan_id)
        
        if not plan_details:
            st.error("Plan-Details konnten nicht geladen werden.")
            st.stop()
        
        st.success(f"Plan geladen")
        
        # Display plan details
        plan_name = plan_details.get("name", "Abonnement-Plan")
        plan_description = plan_details.get("description", "")
        
        # Get pricing information
        billing_cycles = plan_details.get("billing_cycles", [])
        price_per_month = "N/A"
        
        if billing_cycles:
            for cycle in billing_cycles:
                if cycle.get("frequency", {}).get("interval_unit") == "MONTH":
                    price_data = cycle.get("pricing_scheme", {}).get("fixed_price", {})
                    if price_data:
                        price_per_month = price_data.get("value", "N/A")
                        break
        
        # Display plan in a nice container
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"## {plan_name}")
                if plan_description:
                    st.write(f"_{plan_description}_")
            
            with col2:
                st.markdown(f"### 💰 {price_per_month}€")
                st.markdown("**pro Monat**")
        
        st.divider()
        
        # Subscribe button
        if st.button("Jetzt abonnieren", use_container_width=True, key="paypal_subscribe"):
            access_token = get_paypal_access_token()
            if not access_token:
                st.error("Fehler beim Verbinden mit PayPal API")
            else:
                subscription_data = {
                    "plan_id": plan_id,
                    "subscriber": {
                        "name": {
                            "given_name": st.session_state.get("user", "User")
                        },
                        "email_address": st.session_state.get("email", "user@example.com")
                    },
                    "application_context": {
                        "brand_name": "ETA Application",
                        "locale": "de-DE",
                        "user_action": "SUBSCRIBE_NOW",
                        "return_url": f"{PAYPAL_BASE_URL}?page=payment_success",
                        "cancel_url": f"{PAYPAL_BASE_URL}?page=payment_cancel"
                    },
                    "custom_id": st.session_state.get("user", "")
                }
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                try:
                    response = requests.post(
                        f"{PAYPAL_API_BASE}/v1/billing/subscriptions",
                        json=subscription_data,
                        headers=headers
                    )
                    
                    if response.status_code in [200, 201]:
                        result = response.json()
                        subscription_id = result.get("id")
                        st.session_state.paypal_subscription_id = subscription_id
                        st.success(f"Subscription erstellt: {subscription_id}")
                        
                        # **WICHTIG**: Speichere Subscription-ID sofort in die Datenbank
                        # Damit der Webhook sie später finden kann!
                        try:
                            with engine.begin() as conn:
                                conn.execute(
                                    text("""
                                        UPDATE benutzer 
                                        SET paypal_subscription_id = :sub_id, 
                                            payment_status = 'PENDING'
                                        WHERE benutzername = :user
                                    """),
                                    {"sub_id": subscription_id, "user": st.session_state.get("user")}
                                )
                                st.info(f"Subscription ID in DB gespeichert für Webhook")
                        except Exception as db_error:
                            st.error(f"Fehler beim Speichern der Subscription ID: {str(db_error)}")
                        
                        # Find approval link
                        approval_url = None
                        for link in result.get("links", []):
                            if link.get("rel") == "approve":
                                approval_url = link.get("href")
                                break
                        
                        if approval_url:
                            st.success(f"Weiterleitung zum Zahlungsformular...")
                            st.markdown(f'<meta http-equiv="refresh" content="1;url={approval_url}">', unsafe_allow_html=True)
                            st.link_button("👉 Zum Zahlungsformular", approval_url)
                        else:
                            st.error("Keine Approval-URL erhalten")
                            st.json(result)
                    else:
                        st.error(f"PayPal Error: {response.status_code}")
                        st.error(f"Response: {response.text}")
                except Exception as e:
                    st.error(f"Fehler: {str(e)}")
        
        st.divider()
        
        if st.button("← Zurück zum Login", use_container_width=True, key="back_to_login"):
            st.session_state.page = "login"
            st.session_state.user = None
            st.session_state.payment_status = None
            st.session_state.selected_plan_id = None
            st.rerun()

# === Projekt-Auswahl für Mitarbeiter ===
def projekt_auswahl_page():
    st.title("🏗️ Projekt auswählen")
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
    if st.button("🚪 Abmelden"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# === Streamlit UI ===
def check_access():
    """
    Überprüft ob der Benutzer Zugriff auf die App hat und leitet bei fehlendem Zugriff zur Payment-Seite weiter.
    Mitarbeiter benötigen keine Zahlung - nur Bauunternehmer.
    """
    # Entwickler haben immer Zugriff
    if st.session_state.get("nutzer_typ") == "developer":
        return True
    
    # Mitarbeiter haben immer Zugriff (Zahlung ist Sache des Bauunternehmers)
    if st.session_state.get("nutzer_typ") == "mitarbeiter":
        return True
        
    # Cache-Check für Performance (alle 5 Minuten) - nur für Bauunternehmer
    if "last_access_check" in st.session_state:
        if (datetime.now() - st.session_state.last_access_check).total_seconds() < 300:
            if not st.session_state.get("has_access", False):
                st.session_state.page = "payment"
                st.rerun()
            return st.session_state.get("has_access", False)
    
    # Für Bauunternehmer: payment_status aus der Session prüfen
    payment_status = st.session_state.get("payment_status")
    
    if payment_status == "ACTIVE":
        # Zugriff gewährt
        st.session_state.last_access_check = datetime.now()
        st.session_state.has_access = True
        return True
    else:
        # Kein aktives Abonnement - zur Payment-Seite
        st.session_state.has_access = False
        st.session_state.last_access_check = datetime.now()
        st.error(f"Zugriff verweigert: Kein aktives Abonnement. Status: {payment_status}")
        import time
        time.sleep(2)
        st.session_state.page = "payment"
        st.rerun()
        st.stop()

# ========== SICHERE KI-PROGNOSE FUNKTION ==========
def safe_secure_ki_prognose():
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LinearRegression
        import gc
        
        
        # ALLE Projekte laden (inklusive gelöschter)
        all_projects = pd.read_sql("""
            SELECT 
                p.id, p.name, p.budget, p.dauer, p.arbeiter, p.benutzername, p.archiviert_am,
                COUNT(DISTINCT mp.mitarbeiter_benutzername) as mitarbeiterzahl,
                COALESCE(COUNT(DISTINCT CASE WHEN gn.projekt_id IS NOT NULL THEN gn.id END), 0) as geraete_nutzungen
            FROM projekte p
            LEFT JOIN mitarbeiter_projekte mp ON p.id = mp.projekt_id
            LEFT JOIN geraete_nutzung gn ON p.id = gn.projekt_id
            WHERE p.budget > 0 AND p.dauer > 0 AND p.arbeiter > 0
            GROUP BY p.id, p.name, p.budget, p.dauer, p.arbeiter, p.benutzername, p.archiviert_am
        """, engine)
        
        if all_projects.empty:
            st.warning("Zu wenig Trainingsdaten (min. 3 Projekte)")
            return
        
        # Rechnungskosten laden
        try:
            all_invoices = pd.read_sql("""
                SELECT projekt_id, SUM(nettobetrag) as total_kosten FROM rechnungen GROUP BY projekt_id
            """, engine)
            invoice_dict = dict(zip(all_invoices['projekt_id'], all_invoices['total_kosten']))
            all_projects['rechnungskosten'] = all_projects['id'].map(invoice_dict).fillna(0)
        except:
            all_projects['rechnungskosten'] = 0
        
        # Materialkosten laden
        try:
            all_materials = pd.read_sql("""
                SELECT projekt_id, COUNT(*) as material_count FROM materialplanung 
                WHERE projekt_id IS NOT NULL GROUP BY projekt_id
            """, engine)
            material_dict = dict(zip(all_materials['projekt_id'], all_materials['material_count']))
            all_projects['materialkosten_count'] = all_projects['id'].map(material_dict).fillna(0)
        except:
            all_projects['materialkosten_count'] = 0
        
        # Geräte-Stunden laden
        try:
            geraete_hours = pd.read_sql("""
                SELECT projekt_id, SUM(CAST(nutzungszeit AS FLOAT)) as total_stunden FROM geraete_nutzung 
                WHERE projekt_id IS NOT NULL GROUP BY projekt_id
            """, engine)
            geraete_dict = dict(zip(geraete_hours['projekt_id'], geraete_hours['total_stunden']))
            all_projects['geraete_stunden'] = all_projects['id'].map(geraete_dict).fillna(0)
        except:
            all_projects['geraete_stunden'] = 0
        
        # Feature Engineering
        max_mitarbeiter = all_projects['mitarbeiterzahl'].max() + 1
        max_geraete = all_projects['geraete_stunden'].max() + 1
        max_investi = (all_projects['rechnungskosten'] + all_projects['materialkosten_count']).max() + 1
        
        all_projects['komplexitaet'] = (
            (all_projects['mitarbeiterzahl'] / max_mitarbeiter) +
            (all_projects['geraete_stunden'] / max_geraete) +
            ((all_projects['rechnungskosten'] + all_projects['materialkosten_count']) / max_investi)
        ) / 3
        
        # Feature-Auswahl
        st.markdown("---")
        st.subheader("KI-Modell-Konfiguration")
        
        feature_options = {
            "🔷 Basis": ["dauer", "arbeiter"],
            "🔶 Erweitert": ["dauer", "arbeiter", "materialkosten_count"],
            "🟠 Komplett": ["dauer", "arbeiter", "materialkosten_count", "rechnungskosten"],
            "🔴 Premium": ["dauer", "arbeiter", "mitarbeiterzahl", "materialkosten_count", "rechnungskosten", "geraete_stunden", "komplexitaet"]
        }
        
        selected_features_label = st.radio("Modell-Variante:", list(feature_options.keys()), key="secure_ki_features")
        features = feature_options[selected_features_label]
        
        df_train = all_projects[features + ['budget']].dropna()
        
        if len(df_train) < 3:
            st.warning(f"Zu wenig Trainingsdaten: {len(df_train)}")
            return
        
        scaler = StandardScaler()
        X = scaler.fit_transform(df_train[features])
        y = df_train['budget'].values
        
        model = LinearRegression()
        model.fit(X, y)
        r2_score = model.score(X, y)
        
        # Statistiken
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Trainings-Projekte", len(df_train))
        with col2:
            st.metric("R²-Score", f"{r2_score:.3f}")
        with col3:
            st.metric("Features", len(features))
        
        # Eingabe-Parameter
        st.markdown("---")
        st.subheader("🔮 Prognose-Parameter")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            dauer_input = st.slider("Dauer (Monate)", 1, 48, 12, key="secure_dauer")
            arbeiter_input = st.slider("Arbeiteranzahl", 1, 50, 3, key="secure_arbeiter")
        
        with col2:
            materialkosten_input = st.slider("Material-Einträge", 0, 500, 50, key="secure_material") if "materialkosten_count" in features else 0
            rechnungskosten_input = st.slider("Rechnungskosten (€)", 0, 500000, 50000, key="secure_rechnung") if "rechnungskosten" in features else 0
        
        with col3:
            mitarbeiterzahl_input = st.slider("Mitarbeiterzahl", 1, 20, 3, key="secure_mitarbeiter") if "mitarbeiterzahl" in features else 0
            geraete_stunden_input = st.slider("Geräte-Stunden", 0, 1000, 100, key="secure_geraete") if "geraete_stunden" in features else 0
        
        komplexitaet_input = (
            (mitarbeiterzahl_input / max_mitarbeiter) +
            (geraete_stunden_input / max_geraete) +
            ((rechnungskosten_input + materialkosten_input) / max_investi)
        ) / 3 if "komplexitaet" in features else 0.5
        
        # Prognose berechnen
        input_dict = {
            "dauer": dauer_input,
            "arbeiter": arbeiter_input,
            "mitarbeiterzahl": mitarbeiterzahl_input,
            "materialkosten_count": materialkosten_input,
            "rechnungskosten": rechnungskosten_input,
            "geraete_stunden": geraete_stunden_input,
            "komplexitaet": komplexitaet_input
        }
        
        input_vector = [input_dict.get(feat, 0) for feat in features]
        input_scaled = scaler.transform([input_vector])
        prognose = max(0, model.predict(input_scaled)[0])
        
        # Ausgabe
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.success(f"🔮 **Geschätztes Budget:** €{prognose:,.2f}")
        
        with col2:
            durchschnitt = df_train['budget'].mean()
            abweichung = ((prognose - durchschnitt) / durchschnitt * 100) if durchschnitt > 0 else 0
            if abweichung > 0:
                st.info(f"+{abweichung:.1f}% vs. Durchschnitt")
            else:
                st.warning(f"📉 {abweichung:.1f}% vs. Durchschnitt")
        
        with st.expander("📖 Model-Details"):
            feature_importance_df = pd.DataFrame({
                "Feature": features,
                "Koeffizient": model.coef_,
                "Durchschnitt": [df_train[f].mean() for f in features],
                "Max": [df_train[f].max() for f in features]
            }).sort_values("Koeffizient", ascending=False, key=abs)
            
            st.dataframe(feature_importance_df)
            st.write(f"**Intercept:** {model.intercept_:,.2f} | **R²:** {r2_score:.4f}")
        
        # CLEANUP - Sensitive Daten löschen!
        del scaler, model, X, y, df_train, all_projects
        gc.collect()
        
        st.success("Abgeschlossen. ")
        st.info("📌 Diese Prognose wurde NICHT gespeichert.")
        
    except Exception as e:
        st.error(f"KI-Fehler: {str(e)}")

def bau_app_page():
    # Apply theme CSS at the beginning of every page render
    theme = st.session_state.get('theme', 'white')
    if theme == 'black':
        st.markdown("""
        <style>
            /* === HEADER/NAVBAR SCHWARZER MODUS === */
            [data-testid="stHeader"] {
                background-color: #2b2b2b !important;
            }
            [data-testid="stAppViewContainer"] {
                background-color: #1e1e1e !important;
            }
            
            :root {
                --app-bg: #1e1e1e;
                --text-color: #e0e0e0;
                --box-bg: #252525;
                --box-border: rgba(255,255,255,0.08);
                --table-header-bg: #2a2a2a;
            }
            /* Spezifische Streamlit-Elemente schwarz färben */
            body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stForm"],
            .stTextInput, .stNumberInput, .stSelectbox, .stTextArea {
                background-color: #1e1e1e !important;
                color: #e0e0e0 !important;
            }
            /* ALL TEXT WHITE IN BLACK MODE */
            * {
                color: #e0e0e0 !important;
            }
            /* ALLE ÜBERSCHRIFTEN WEISS IM BLACK MODE */
            h1, h2, h3, h4, h5, h6 {
                color: #ffffff !important;
            }
            input, textarea, select, [role="textbox"], [role="option"],
            [role="button"] {
                background-color: #2a2a2a !important;
                color: #e0e0e0 !important;
                border-color: rgba(255,255,255,0.1) !important;
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
            /* === SUBTLE BUTTONS WITH WHITE OUTLINE FOR BLACK MODE === */
            .stButton>button, .stDownloadButton>button, button, input[type="button"], input[type="submit"] {
                background: #252525 !important;
                color: #e0e0e0 !important;
                border: 1.5px solid #ffffff !important;
                box-shadow: none !important;
                border-radius: 6px !important;
                padding: 6px 12px !important;
            }
            /* SUBTLE HOVER FOR BLACK MODE */
            .stButton>button:hover, .stDownloadButton>button:hover, button:hover, input[type="button"]:hover, input[type="submit"]:hover {
                background: #2f2f2f !important;
                border-color: #ffffff !important;
                box-shadow: 0 2px 8px rgba(255,255,255,0.1) !important;
            }
            .stButton>button *, .stDownloadButton>button *, button *, input[type="button"] *, input[type="submit"] * {
                color: #e0e0e0 !important;
            }
            /* Plotly-Charts: Weiße Hintergründe zulassen */
            svg, svg * {
                background-color: transparent !important;
            }
            [data-testid="plotly-chart"], .plotly-chart {
                background-color: transparent !important;
            }
            .plotly-chart svg {
                background-color: transparent !important;
            }
            .js-plotly-plot {
                background-color: transparent !important;
            }
            /* Breakdown-Fenster - NUR FARBEN */
            .breakdown {
                display: none !important;
                background-color: #2a2a2a !important;
                border-color: rgba(255,255,255,0.15) !important;
                border-width: 1px !important;
                color: #e0e0e0 !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
                padding: 15px !important;
                border-radius: 8px !important;
                position: absolute !important;
                left: 0 !important;
                top: 100% !important;
                transform: translateY(8px) !important;
                min-width: 280px !important;
                z-index: 100000 !important;
                pointer-events: auto !important;
            }
            /* WICHTIG: Show-Klasse für Toggle */
            .show .breakdown {
                display: block !important;
            }
            .breakdown .row,
            .breakdown .total {
                color: #e0e0e0 !important;
                border-color: rgba(255,255,255,0.1) !important;
            }
            body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stForm"] {
                background-color: #1e1e1e !important;
                color: #e0e0e0 !important;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        # WHITE MODE
        st.markdown("""
        <style>
            /* === HEADER/NAVBAR WEISSER MODUS === */
            [data-testid="stHeader"] {
                background-color: #ffffff !important;
            }
            [data-testid="stAppViewContainer"] {
                background-color: #ffffff !important;
            }
            
            :root {
                --app-bg: #ffffff;
                --text-color: #333333;
                --box-bg: #f8f8f8;
                --box-border: rgba(0,0,0,0.08);
                --table-header-bg: #f0f0f0;
            }
            /* SUBTLE BUTTONS WITH BLACK OUTLINE FOR WHITE MODE */
            .stButton>button, .stDownloadButton>button, button, input[type="button"], input[type="submit"] {
                background: #f8f8f8 !important;
                color: #333333 !important;
                border: 1.5px solid #000000 !important;
                box-shadow: none !important;
                border-radius: 6px !important;
                padding: 6px 12px !important;
            }
            /* SUBTLE HOVER FOR WHITE MODE */
            .stButton>button:hover, .stDownloadButton>button:hover, button:hover, input[type="button"]:hover, input[type="submit"]:hover {
                background: #f0f0f0 !important;
                border-color: #000000 !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            }
            .stButton>button *, .stDownloadButton>button *, button *, input[type="button"] *, input[type="submit"] * {
                color: #333333 !important;
            }
        </style>
        """, unsafe_allow_html=True)
    
    # Prüfe Zugriffsberechtigung
    if not check_access():
        return
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------









# Titel und Profilbutton nebeneinander
    nav = None
    col1, col2 = st.columns([8, 2])
    with col1:
        st.markdown("## 🏗️ Projektverwaltung für Bauunternehmen")  # Etwas kleiner als st.title für optische Harmonie
    with col2:
                # === USER MENU - Avatar Button mit Vertical Menü ===
        # Generate popup CSS dynamically based on current theme
        current_theme = st.session_state.get('theme', 'white')
        if current_theme == 'black':
            popup_bg = '#252525'
            popup_border = 'rgba(255,255,255,0.08)'
            button_bg = '#2a2a2a'
            button_text = '#e0e0e0'
            button_border = 'rgba(255,255,255,0.08)'
            button_hover = '#333333'
        else:
            popup_bg = '#f8f8f8'
            popup_border = 'rgba(0,0,0,0.08)'
            button_bg = '#f0f0f0'
            button_text = '#333333'
            button_border = 'rgba(0,0,0,0.08)'
            button_hover = '#e8e8e8'
        
        st.markdown(f"""
        <style>
        /* Avatar Button - Rund wie WhatsApp */
        .menu-avatar-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: 2px solid rgba(255,255,255,0.3) !important;
            width: 44px !important;
            height: 44px !important;
            border-radius: 50% !important;
            cursor: pointer !important;
            font-size: 20px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
            transition: all 0.2s !important;
            padding: 0 !important;
            margin: 0 !important;
        }}
        
        .menu-avatar-btn:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.25) !important;
            transform: scale(1.05) !important;
        }}
        
        .menu-avatar-btn:active {{
            transform: scale(0.95) !important;
        }}
        
        /* Menu Popup - Vertikal */
        .menu-popup-wrapper {{
            position: fixed !important;
            top: 90px !important;
            right: 30px !important;
            z-index: 9999 !important;
            background: {popup_bg} !important;
            border: 1px solid {popup_border} !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2) !important;
            padding: 0 !important;
            display: none;
            flex-direction: column !important;
            gap: 0 !important;
            min-width: 220px !important;
        }}
        
        .menu-popup-wrapper.open {{
            display: flex !important;
        }}
        
        /* Popup Buttons */
        .menu-popup-wrapper button {{
            background: {button_bg} !important;
            color: {button_text} !important;
            border: none !important;
            border-bottom: 1px solid {button_border} !important;
            padding: 12px 16px !important;
            text-align: left !important;
            cursor: pointer !important;
            font-weight: 500 !important;
            font-size: 14px !important;
            transition: all 0.2s !important;
            box-shadow: none !important;
            width: 100% !important;
        }}
        
        .menu-popup-wrapper button:last-child {{
            border-bottom: none !important;
        }}
        
        .menu-popup-wrapper button:hover {{
            background: {button_hover} !important;
        }}
        
        .menu-popup-wrapper button:active {{
            opacity: 0.8 !important;
        }}
        </style>
        
        <div class="menu-popup-wrapper" id="menuPopup"></div>
        
        <script>
        function toggleMenuPopup() {{
            const popup = document.getElementById('menuPopup');
            popup.classList.toggle('open');
        }}
        
        // Close popup when clicking outside
        document.addEventListener('click', function(event) {{
            const popup = document.getElementById('menuPopup');
            const btn = document.querySelector('.menu-avatar-btn');
            if (popup && btn && !popup.contains(event.target) && event.target !== btn) {{
                popup.classList.remove('open');
            }}
        }});
        </script>
        """, unsafe_allow_html=True)
        
        # Avatar Button für Menü Toggle
        col_avatar = st.columns([1])[0]
        with col_avatar:
            if st.button("👤", key="menu_toggle", help="Benutzermenü"):
                st.session_state.menu_open = not st.session_state.get("menu_open", False)
                st.rerun()
        
        # Menü Items wenn offen - VERTIKAL
        if st.session_state.get("menu_open", False):
            st.markdown("---")
            
            # Settings Option
            if st.button("Einstellungen", key="menu_settings", use_container_width=True):
                try:
                    st.session_state["last_open_settings_user"] = st.session_state.get("user")
                    st.session_state["last_open_settings_time"] = datetime.now().isoformat()
                    snapshot = {k: str(st.session_state.get(k)) for k in ['user','page','nutzer_typ','account_id','theme']}
                    st.session_state['open_settings_debug'] = snapshot
                except Exception:
                    st.session_state['open_settings_debug'] = {'error': 'could not capture snapshot'}
                st.session_state["page"] = "einstellungen"
                st.session_state.menu_open = False
                st.rerun()
            
            # Profile Option
            if st.button(" Profil", key="menu_profile", use_container_width=True):
                st.session_state["page"] = "profil"
                st.session_state.menu_open = False
                st.rerun()
            
            # Logout Option
            if st.button(" Logout", key="menu_logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "login"
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    # === Navigation auslesen ===
    with st.sidebar:
        if st.session_state.get("nutzer_typ") == "bauunternehmer":
            nav = option_menu(
                menu_title=None,
                options=["Neues Projekt anlegen", "Projektübersicht", "Materialübersicht","Geräteübersicht", "Mitarbeiter","Lohnübersicht", "Rechnung erstellen", "Projekt-Checklisten","Vorplanungs-Kalender","Material-Planung","Fortschritt", "Budget-KI-Prognose", "Dashboard"],
                menu_icon="cast",
                default_index=0,
                key="nav"
            )
        elif st.session_state.get("nutzer_typ") == "mitarbeiter":
            nav = "Mitarbeiterprojekt"  # Fixe Seite, kein Menü
        else:
            st.warning("Bitte zuerst einloggen.")
            st.stop()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------









# === Seite: Neues Projekt anlegen ===
    if nav == "Neues Projekt anlegen":
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
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------









# === Seite: Projektübersicht ===
    elif nav == "Projektübersicht":
        st.header("Projektübersicht")
        df = pd.read_sql("SELECT id, name, budget, datum FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
        if not df.empty:
            for index, row in df.iterrows():
                # Berechne Zeit seit Erstellung
                project_date = pd.to_datetime(row['datum'])
                days_since = (pd.Timestamp.today() - project_date).days
                if days_since == 0:
                    time_str = "Heute erstellt"
                elif days_since == 1:
                    time_str = "Vor 1 Tag"
                elif days_since < 7:
                    time_str = f"Vor {days_since} Tagen"
                elif days_since < 30:
                    weeks = days_since // 7
                    time_str = f"Vor {weeks} Woche(n)"
                else:
                    months = days_since // 30
                    time_str = f"Vor {months} Monat(en)"
                
                # Zähle Mitarbeiter im Projekt
                mitarbeiter_count = pd.read_sql("SELECT COUNT(*) as count FROM mitarbeiter_projekte WHERE projekt_id = %s", engine, params=(row['id'],))
                worker_count = int(mitarbeiter_count['count'].iloc[0]) if not mitarbeiter_count.empty else 0
                
                # Berechne Kosten für Budget-Vergleich
                rechnungen_kosten = pd.read_sql("SELECT COALESCE(SUM(nettobetrag), 0) as gesamt FROM rechnungen WHERE projekt_name = %s AND benutzername = %s", engine, params=(row['name'], st.session_state.user))
                rechnung_total = float(rechnungen_kosten['gesamt'].iloc[0]) if not rechnungen_kosten.empty else 0.0
                materialien_data = pd.read_sql("SELECT m.menge, m.einheit, l.preis_ankauf FROM materialien m LEFT JOIN lagerbestand l ON m.material = l.material WHERE m.projekt_id = %s AND m.benutzername = %s", engine, params=(row['id'], st.session_state.user))
                material_kosten = 0.0
                if not materialien_data.empty:
                    for _, mat_row in materialien_data.iterrows():
                        menge = float(mat_row['menge']) if pd.notnull(mat_row['menge']) else 0.0
                        preis = float(mat_row['preis_ankauf']) if pd.notnull(mat_row['preis_ankauf']) else 0.0
                        material_kosten += menge * preis
                gesamt_kosten = rechnung_total + material_kosten
                budget_diff = float(row['budget']) - gesamt_kosten
                
                with st.expander(f"{row['name']} – {int(row['budget'])} €"):
                    st.markdown(f"**Zeit seit Erstellung:** {time_str}")
                    st.markdown(f"**Mitarbeiter zugewiesen:** {worker_count}")
                    
                    # Budget-Vergleich mit Textfarbe
                    if budget_diff > 0:
                        st.markdown(f"**Budget noch verfügbar:** <span style='color: #4CAF50;'>{budget_diff:.2f} € </span>", unsafe_allow_html=True)
                    elif budget_diff < 0:
                        st.markdown(f"**Budget überschritten um:** <span style='color: #ff9800;'>{abs(budget_diff):.2f} €</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**Budget:** <span style='color: #2196F3;'>Exakt ausgegeben</span>", unsafe_allow_html=True)

                    col1, col2, col3 = st.columns([2, 6, 2])
                    with col1:
                        if st.button("Abschließen", key=f"archive_{row['id']}", help="Projekt archivieren"):
                            st.session_state[f"confirm_archive_{row['id']}"] = True
                    with col3:
                        if st.button("Löschen", key=f"delete_{row['id']}", help="Projekt löschen"):
                            st.session_state[f"confirm_delete_{row['id']}"] = True
                
                # Archivierungs-Bestätigung (1. Abfrage)
                if st.session_state.get(f"confirm_archive_{row['id']}", False):
                    st.warning(f"Möchtest du das Projekt **{row['name']}** wirklich abschließen und archivieren?")
                    st.markdown("**Diese Aktion:**")
                    st.markdown("- ✓ Archiviert das Projekt und alle Daten")
                    st.markdown("- ✓ Entfernt Mitarbeiter aus dem Projekt")
                    st.markdown("- ✓ Zieht verbrauchte Materialien vom Lagerbestand ab")
                    st.markdown("- ✓ Aktualisiert die Geräte-Nutzung")
                    st.markdown("- ✗ Das Projekt kann nach der Archivierung nicht mehr bearbeitet werden")
                    
                    archive_col1, archive_col2, archive_col3 = st.columns(3)
                    with archive_col1:
                        if st.button("Ja, archivieren", key=f"confirm_archive_yes_{row['id']}"):
                            st.session_state[f"confirm_archive_double_{row['id']}"] = True
                    with archive_col2:
                        if st.button("Abbrechen", key=f"confirm_archive_no_{row['id']}"):
                            del st.session_state[f"confirm_archive_{row['id']}"]
                            st.rerun()
                
                # DOPPELTE BESTÄTIGUNG für Archivierung
                if st.session_state.get(f"confirm_archive_double_{row['id']}", False):
                    st.error(f"⛔ LETZTE BESTÄTIGUNG: Das Projekt **{row['name']}** wird archiviert. Diese Aktion kann nicht rückgängig gemacht werden!")
                    final_col1, final_col2 = st.columns(2)
                    with final_col1:
                        if st.button("🔒 JA, ENDGÜLTIG ARCHIVIEREN", key=f"final_archive_{row['id']}"):
                            # === ARCHIVIERUNGS-LOGIK ===
                            try:
                                with engine.begin() as conn:
                                    # 1. Materialien vom Lagerbestand abziehen
                                    materialien_project = pd.read_sql(
                                        "SELECT material, menge FROM materialien WHERE projekt_id = %s AND benutzername = %s",
                                        engine, params=(row['id'], st.session_state.user)
                                    )
                                    for _, mat in materialien_project.iterrows():
                                        menge = float(mat['menge']) if pd.notnull(mat['menge']) else 0.0
                                        if menge > 0:
                                            conn.exec_driver_sql(
                                                "UPDATE lagerbestand SET menge = menge - %s WHERE material = %s AND benutzername = %s",
                                                (menge, mat['material'], st.session_state.user)
                                            )
                                    
                                    # 2. Mitarbeiter aus Projekt entfernen
                                    conn.exec_driver_sql(
                                        "DELETE FROM mitarbeiter_projekte WHERE projekt_id = %s",
                                        (row['id'],)
                                    )
                                    
                                    # 3. Projekt archivierungsdatum setzen (wird in den 3 archiven gespeichert)
                                    conn.exec_driver_sql(
                                        "UPDATE projekte SET archiviert_am = %s WHERE id = %s",
                                        (date.today().strftime("%Y-%m-%d"), row['id'])
                                    )
                                
                                st.success(f"Projekt **{row['name']}** wurde erfolgreich archiviert!")
                                del st.session_state[f"confirm_archive_{row['id']}"]
                                del st.session_state[f"confirm_archive_double_{row['id']}"]
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Archivieren: {str(e)}")
                    with final_col2:
                        if st.button("ABBRECHEN", key=f"final_archive_no_{row['id']}"):
                            del st.session_state[f"confirm_archive_{row['id']}"]
                            del st.session_state[f"confirm_archive_double_{row['id']}"]
                            st.rerun()
                
                # Lösch-Bestätigung (alte Logik)
                if st.session_state.get(f"confirm_delete_{row['id']}", False):
                    st.warning(f"Möchtest du das Projekt **{row['name']}** wirklich löschen?")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("Ja, löschen", key=f"confirm_yes_{row['id']}"):
                            with engine.begin() as conn:
                                conn.exec_driver_sql("DELETE FROM projekte WHERE id = %s", (row['id'],))
                            st.success(f"Projekt **{row['name']}** wurde gelöscht.")
                            del st.session_state[f"confirm_delete_{row['id']}"]
                            st.rerun()
                            sync_materialien()
                    with confirm_col2:
                        if st.button("Abbrechen", key=f"confirm_no_{row['id']}"):
                            del st.session_state[f"confirm_delete_{row['id']}"]
        
        # Neu abrufen für die HTML-Tabelle
        df = pd.read_sql("SELECT id, name, budget, datum FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
        if not df.empty:
            st.subheader("Projektübersicht - Tabelle")
            # HTML-Tabelle für Projektübersicht
            table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
            table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Projektname</th><th>Budget (€)</th><th>Kosten (€)</th><th>Dauer seit Erstellung</th><th>Mitarbeiter</th></tr></thead><tbody>"
            
            for _, row in df.iterrows():
                budget_formatted = f"{float(row['budget']):.2f}" if pd.notnull(row['budget']) else "0.00"
                
                # Berechne Zeit seit Erstellung
                project_date = pd.to_datetime(row['datum'])
                days_since = (pd.Timestamp.today() - project_date).days
                if days_since == 0:
                    time_str = "Heute"
                elif days_since == 1:
                    time_str = "1 Tag"
                elif days_since < 7:
                    time_str = f"{days_since} Tage"
                elif days_since < 30:
                    weeks = days_since // 7
                    time_str = f"{weeks} Wo."
                else:
                    months = days_since // 30
                    time_str = f"{months} Mo."
                
                # Zähle Mitarbeiter
                mitarbeiter_count = pd.read_sql("SELECT COUNT(*) as count FROM mitarbeiter_projekte WHERE projekt_id = %s", engine, params=(row['id'],))
                worker_count = int(mitarbeiter_count['count'].iloc[0]) if not mitarbeiter_count.empty else 0
                
                # Berechne Kosten aus bereits erstellten Rechnungen + ungefähre Schätzung aus Materialien + Geräte-Nutzung
                # 1. Summe der Netto-Beträge aus abgerechneten Rechnungen
                rechnungen_kosten = pd.read_sql("SELECT COALESCE(SUM(nettobetrag), 0) as gesamt FROM rechnungen WHERE projekt_name = %s AND benutzername = %s", engine, params=(row['name'], st.session_state.user))
                rechnung_total = float(rechnungen_kosten['gesamt'].iloc[0]) if not rechnungen_kosten.empty else 0.0
                
                # 2. Ungefähre Materialkosten aus dem Lagerbestand
                materialien_data = pd.read_sql("SELECT m.menge, m.einheit, l.preis_ankauf FROM materialien m LEFT JOIN lagerbestand l ON m.material = l.material WHERE m.projekt_id = %s", engine, params=(row['id'],))
                material_kosten = 0.0
                if not materialien_data.empty:
                    for _, mat_row in materialien_data.iterrows():
                        menge = float(mat_row['menge']) if pd.notnull(mat_row['menge']) else 0.0
                        preis = float(mat_row['preis_ankauf']) if pd.notnull(mat_row['preis_ankauf']) else 0.0
                        material_kosten += menge * preis
                
                # 3. Geräte-Nutzungskosten
                geraete_nutzung_data = pd.read_sql(
                    """SELECT gn.geraet, gn.nutzungszeit, gl.betriebskosten 
                       FROM geraete_nutzung gn 
                       LEFT JOIN geraete_lager gl ON gn.geraet = gl.geraet 
                       WHERE gn.projekt_id = %s""", 
                    engine, params=(row['id'],))
                geraete_kosten = 0.0
                if not geraete_nutzung_data.empty:
                    for _, geraete_row in geraete_nutzung_data.iterrows():
                        nutzungszeit = float(geraete_row['nutzungszeit']) if pd.notnull(geraete_row['nutzungszeit']) else 0.0
                        betriebskosten = float(geraete_row['betriebskosten']) if pd.notnull(geraete_row['betriebskosten']) else 0.0
                        # Berechne Kosten: nutzungszeit (Stunden) * betriebskosten (€/Stunde)
                        geraete_kosten += nutzungszeit * betriebskosten
                
                # Gesamtkosten (bereits abgerechnet + geschätzte Materialien + Geräte-Nutzung)
                gesamt_kosten = rechnung_total + material_kosten + geraete_kosten
                kosten_formatted = f"≈ {gesamt_kosten:.2f}"  # ≈ zeigt an, dass es ungefähre Werte sind
                
                table_html += f"<tr><td><strong>{row['name']}</strong></td><td>{budget_formatted}</td><td>{kosten_formatted}</td><td>{time_str}</td><td>{worker_count}</td></tr>"
            
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("Noch keine Projekte eingetragen.")
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------    
    
    
    
    
    
    
    
    
    
    elif nav == "Vorplanungs-Kalender":
        vorplanung_page()
    elif nav == "Material-Planung":
        materialplanung_page()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------









 # === Seite: Materialübersicht ===       
    elif nav == "Materialübersicht":
        st.header("Materialübersicht")
# Materialtabelle vorbereiten
# Daten abrufen
        df_projekte = pd.read_sql(
            "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
            engine,
            params=(st.session_state.user,)
        )
        df_lager = pd.read_sql(
            "SELECT * FROM lagerbestand WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        df_material = pd.read_sql(
            "SELECT * FROM materialien WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        alle_materialien_db = pd.read_sql(
            "SELECT DISTINCT material FROM materialien WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        lager_db = pd.read_sql(
            "SELECT DISTINCT material FROM lagerbestand WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        alle_materialien = sorted(set(alle_materialien_db["material"]).union(set(lager_db["material"])))        
        with engine.begin() as conn:
            conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS materialien (
            projekt_id INTEGER,
            material TEXT,
            menge REAL,
            benutzername TEXT,
            PRIMARY KEY (projekt_id, material, benutzername)
            )
            """)
            conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS lagerbestand (
            material TEXT PRIMARY KEY,
            menge REAL,
            benutzername TEXT,
            PRIMARY KEY (material, benutzername)
            )
            """)
# Daten abrufen
        df_projekte = pd.read_sql(
            "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
            engine,
            params=(st.session_state.user,)
        )
        df_lager = pd.read_sql(
            "SELECT * FROM lagerbestand WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        df_material = pd.read_sql(
            "SELECT * FROM materialien WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        alle_materialien_db = pd.read_sql(
            "SELECT DISTINCT material FROM materialien WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        lager_db = pd.read_sql(
            "SELECT DISTINCT material FROM lagerbestand WHERE benutzername = %s",
            engine,
            params=(st.session_state.user,)
        )
        alle_materialien = sorted(set(alle_materialien_db["material"]).union(set(lager_db["material"])))
        # === Initialisierung der Session-States für Reset
        if "materialname_reset" not in st.session_state:
            st.session_state.materialname_reset = ""
        if "lagermenge_reset" not in st.session_state:
            st.session_state.lagermenge_reset = 0.0
        if "material_edit_counter" not in st.session_state:
            st.session_state.material_edit_counter = 0
# Material hinzufügen
        st.subheader("+ Neues Material")
        with st.form("neues_material_formular"):
            neues_material = st.text_input("Neuer Materialname")
            lager_menge = st.number_input("Aktueller Lagerbestand", min_value=0.0, step=1.0)
            einheit = st.selectbox("Einheit auswählen", EINHEITEN)
            preis_ankauf = st.number_input("Ankaufspreis (€)", min_value=0.0, step=0.1)
            preis_verkauf = st.number_input("Verkaufspreis (€)", min_value=0.0, step=0.1)
            hinzu = st.form_submit_button("Hinzufügen")
            if hinzu and neues_material:
                with engine.begin() as conn:
                    # Try INSERT first, update if exists
                    try:
                        conn.exec_driver_sql("""
                             INSERT INTO lagerbestand (material, menge, benutzername, preis_ankauf, preis_verkauf, einheit)
                             VALUES (%s, %s, %s, %s, %s, %s)
                        """, (neues_material, lager_menge, st.session_state.user, preis_ankauf, preis_verkauf, einheit))
                    except:
                        # Material already exists, update it
                        conn.exec_driver_sql("""
                             UPDATE lagerbestand
                             SET menge = menge + %s,
                                 preis_ankauf = %s,
                                 preis_verkauf = %s,
                                 einheit = %s
                             WHERE material = %s AND benutzername = %s
                        """, (lager_menge, preis_ankauf, preis_verkauf, einheit, neues_material, st.session_state.user))
                for _, projekt in df_projekte.iterrows():
                    with engine.begin() as conn:
                        try:
                            conn.exec_driver_sql("""
                        INSERT INTO materialien (projekt_id, material, menge, benutzername, einheit) VALUES (%s, %s, 0, %s, %s)
                    """, (projekt["id"], neues_material, st.session_state.user, einheit))
                        except:
                            # Material already exists for this project, update it
                            conn.exec_driver_sql("""
                        UPDATE materialien SET menge = %s WHERE projekt_id = %s AND material = %s AND benutzername = %s
                    """, (0, projekt["id"], neues_material, st.session_state.user))
                sync_materialien()
                st.success(f"Material '{neues_material}' hinzugefügt.")
                st.session_state.materialname_reset = ""
                st.session_state.lagermenge_reset = 0.0
                st.rerun()
        if "projekt_bearbeiten_offen" not in st.session_state:
            st.session_state.projekt_bearbeiten_offen = True
        with st.expander("Als Administrator bearbeiten"):
            st.warning("**Admin-Modus aktiviert:** Wenn Sie hier Werte bearbeiten, wird das automatische Tracking der Mitarbeitereingaben gestoppt und die Werte werden als feste Werte festgelegt.")
            # Schritt 1: Projekt zur Bearbeitung auswählen
            df_projekte = pd.read_sql(
                "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
                engine,
                params=(st.session_state.user,)
            )
            df_material = pd.read_sql(
                "SELECT * FROM materialien WHERE benutzername = %s",
                engine,
                params=(st.session_state.user,)
            )
            projekt_namen = df_projekte["name"].tolist()
            if not projekt_namen:
                st.info("Es sind noch keine Projekte vorhanden.")
            else:
                ausgewaehlt = st.selectbox("Wähle ein Projekt zur Bearbeitung", projekt_namen)
                projekt = df_projekte[df_projekte["name"] == ausgewaehlt].iloc[0]
                st.markdown(f"### Bearbeite: {projekt['name']}")

                # Schritt 2: Alle aktuellen Werte sammeln und anzeigen
                with st.form("projekt_bearbeiten_formular"):    
                    aktuelle_werte = {}
                    bearbeitet_flags = {}
                    for mat in alle_materialien:
                        menge_df = df_material.query("projekt_id == @projekt.id and material == @mat")["menge"]
                        alt_menge = float(menge_df.iloc[0]) if not menge_df.empty else 0.0
                        # Flag für Bauunternehmer-Bearbeitung
                        bearbeitet_df = df_material.query("projekt_id == @projekt.id and material == @mat")["bearbeitet_von_bauunternehmer"]
                        bearbeitet = int(bearbeitet_df.iloc[0]) if not bearbeitet_df.empty else 0
                        neue_menge = st.number_input(
                            f"{mat}", value=alt_menge, step=10.0,
                            key=f"bearbeiten_{projekt['id']}_{mat}_{st.session_state.material_edit_counter}"
                        )
                        aktuelle_werte[mat] = neue_menge
                        bearbeitet_flags[mat] = bearbeitet
                    speichern = st.form_submit_button("Änderungen speichern")
                    # Speichern-Button
                    if speichern:
                        with engine.begin() as conn:
                            for mat, menge in aktuelle_werte.items():
                                # Einheit aus Lagerbestand holen
                                einheit_row = df_lager[df_lager["material"] == mat]
                                einheit = einheit_row["einheit"].iloc[0] if not einheit_row.empty else ""
                                # Setze das Flag bearbeitet_von_bauunternehmer = 1
                                conn.exec_driver_sql("""
                                    INSERT INTO materialien (projekt_id, material, menge, benutzername, einheit, bearbeitet_von_bauunternehmer)
                                    VALUES (%s, %s, %s, %s, %s, 1)
                                    ON CONFLICT(projekt_id, material, benutzername)
                                    DO UPDATE SET menge = excluded.menge, einheit = excluded.einheit, bearbeitet_von_bauunternehmer = 1
                                """, (int(projekt["id"]), str(mat), float(menge), st.session_state.user, einheit))
                        sync_materialien()
                        st.success("Alle Änderungen erfolgreich gespeichert.")
                        st.session_state.material_edit_counter += 1  
                        st.session_state.projekt_bearbeiten_offen = False
                        st.rerun()
# Material-Löschaktion abfangen (wird beim Klick ausgelöst)
            if "delete_material" in st.query_params:
                zu_loeschen = st.query_params["delete_material"][0]
                with engine.begin() as conn:
                    conn.exec_driver_sql("DELETE FROM lagerbestand WHERE material = %s", (zu_loeschen,))
                    conn.exec_driver_sql("DELETE FROM materialien WHERE material = %s", (zu_loeschen,))
                sync_materialien()
                st.success(f"Material '{zu_loeschen}' wurde gelöscht.")
                st.rerun()
# Tabelle anzeigen
        if df_projekte.empty:
            st.info("📭 Noch keine Projekte eingetragen. Bitte erst Projekte anlegen.")
        else:    
            st.subheader("Lager-Tabelle mit Projekten")
        #DAtA-frames LADEN
            df_projekte = pd.read_sql(
                    "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
                    engine,
                    params=(st.session_state.user,)
            )
            df_lager = pd.read_sql(
                "SELECT * FROM lagerbestand WHERE benutzername = %s",
                engine,
                params=(st.session_state.user,)
            )
            df_material = pd.read_sql(
                "SELECT * FROM materialien WHERE benutzername = %s",
                engine,
                params=(st.session_state.user,)
            )
            alle_materialien_db = pd.read_sql(
                "SELECT DISTINCT material FROM materialien WHERE benutzername = %s",
                engine,
                params=(st.session_state.user,)
            )
            lager_db = pd.read_sql(
                "SELECT DISTINCT material FROM lagerbestand WHERE benutzername = %s",
                engine,
                params=(st.session_state.user,)
            )
            alle_materialien = sorted(set(alle_materialien_db["material"]).union(set(lager_db["material"])))
            # HTML-Tabelle vorbereiten
            table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;}.scroll-table{border-collapse:collapse;min-width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.5rem 1rem;text-align:center;color:var(--text-color);}.scroll-table th:first-child,.scroll-table td:first-child{position:sticky;left:0;background:var(--table-header-bg);z-index:1;}.scroll-table th{background:var(--table-header-bg);position:sticky;top:0;z-index:2;}</style>"
            table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Projekt</th>"

            #Preise für material hinzufügen
            for mat in alle_materialien:
                preis_row = df_lager[df_lager["material"] == mat]
                einheit = preis_row["einheit"].iloc[0] if not preis_row.empty and "einheit" in preis_row else ""
                ankauf = preis_row["preis_ankauf"].iloc[0] if not preis_row.empty else 0.0
                verkauf = preis_row["preis_verkauf"].iloc[0] if not preis_row.empty else 0.0
                # Fehler vermeiden: None durch 0 ersetzen
                ankauf = ankauf if ankauf is not None else 0.0
                verkauf = verkauf if verkauf is not None else 0.0
                preis_info = f" [{einheit}] ({ankauf:.2f}€/{verkauf:.2f}€)"
                table_html += f"<th>{mat}{preis_info}</th>"
    # Lagerbestand-Zeile
            table_html += "<tr><td><strong>Lagerbestand</strong></td>"
            for mat in alle_materialien:
                lager_wert = df_lager.query("material == @mat")["menge"]
                try:
                    val = float(lager_wert.iloc[0]) if not lager_wert.empty else 0.0
                except:
                    val = 0.0
                table_html += f"<td>{val:.2f}</td>"
            table_html += "</tr>"
    # Projektzeilen
            summen_dict = {mat: 0.0 for mat in alle_materialien}
            heute = date.today().strftime("%Y-%m-%d")
            
            # SQL-Query für Grundbestand + heutige Eingaben (NICHT addiert, nur angezeigt)
            material_query = pd.read_sql(
                """
                SELECT 
                    m.projekt_id,
                    m.material,
                    COALESCE(m.verbrauch, 0) as grundbestand,
                    COALESCE(SUM(CASE WHEN m.datum = %s THEN m.menge ELSE 0 END), 0) as heute_menge
                FROM materialien m
                WHERE m.benutzername = %s
                GROUP BY m.projekt_id, m.material, m.verbrauch
                """,
                engine,
                params=(heute, st.session_state.user)
            )
            
            for _, projekt in df_projekte.iterrows():
                table_html += f"<tr><td>{projekt['name']}</td>"
                for mat in alle_materialien:
                    # Finde Eintrag aus Query
                    mat_data = material_query.query("projekt_id == @projekt.id and material == @mat")
                    
                    if not mat_data.empty:
                        grundbestand = float(mat_data.iloc[0]["grundbestand"])
                        heute_menge = float(mat_data.iloc[0]["heute_menge"])
                    else:
                        grundbestand = 0.0
                        heute_menge = 0.0
                    
                    # Zeige beide Werte (aber noch nicht addiert!)
                    angezeigt = grundbestand + heute_menge
                    table_html += f"<td>{angezeigt:.2f}</td>"
                    summen_dict[mat] += angezeigt
    # Saldo-Zeile mit Farbmarkierung
            table_html += "<tr><td><strong>Saldo</strong></td>"
            for mat in alle_materialien:
                lager_wert = df_lager.query("material == @mat")["menge"]
                try:
                    lager = float(lager_wert.iloc[0]) if not lager_wert.empty else 0.0
                except:
                    lager = 0.0
                rest = lager - summen_dict[mat]
                farbe = "green" if rest >= 0 else "red"
                table_html += f"<td style='color:{farbe}; font-weight:bold'>{rest:.2f}</td>"
            table_html += "</tr>"

        # Material-Löschbuttons pro Spalte
            for mat in alle_materialien:
                
                table_html += "</tr>"
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
            with st.expander("Materialien löschen"):
                if not alle_materialien:
                    st.info("Keine Materialien vorhanden.")
                else:
                    delete_cols = st.columns(len(alle_materialien))
                    for i, mat in enumerate(alle_materialien):
                        if delete_cols[i].button(f"🗑️ {mat}", key=f"delete_material_{mat}"):
                            with engine.begin() as conn:
                                conn.exec_driver_sql("DELETE FROM lagerbestand WHERE material = %s", (mat,))
                                conn.exec_driver_sql("DELETE FROM materialien WHERE material = %s", (mat,))
                            sync_materialien()
                            st.success(f"Material **{mat}** wurde gelöscht.")
                            st.rerun()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    
    
    
    
    
    
    
    
    elif nav == "Geräteübersicht":
        st.header("Geräteübersicht")
        # Tabelle für Geräte anlegen (ohne eigene Einheit-Spalte)
        with engine.begin() as conn:
            conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS geraete_lager (
                    geraet TEXT PRIMARY KEY,
                    anzahl INTEGER,
                    art TEXT,
                    dauer INTEGER,
                    benutzername TEXT
                )
            """)
        with engine.begin() as conn:
            try:
                conn.exec_driver_sql("ALTER TABLE geraete_lager ADD COLUMN dauer INTEGER")
            except:
                pass  # Spalte existiert schon
        with engine.begin() as conn:
            try:
                conn.exec_driver_sql("ALTER TABLE geraete_lager ADD COLUMN betriebskosten REAL")
            except:
                pass
        with engine.begin() as conn:
            try:
                conn.exec_driver_sql("ALTER TABLE geraete_lager ADD COLUMN monatliche_kosten REAL")
            except:
                pass
        # Geräte aus DB laden (nur eigene Geräte)
        df_geraete = pd.read_sql(
            "SELECT geraet, anzahl, art, dauer FROM geraete_lager WHERE benutzername = %s",
            engine, params=(st.session_state.user,)
        )

        # Expander zum Eintragen neuer Geräte
        with st.expander("+ Neues Gerät/Maschine eintragen"):
            with st.form("geraet_anlegen_formular"):
                geraet = st.text_input("Gerätename")
                anzahl = st.number_input("Anzahl (stk)", min_value=1, step=1)
                art = st.selectbox("Art", GGG)
                dauer = st.number_input("Dauer (Monate)", min_value=1, step=1, value=1, key="dauer_input")
                betriebskosten = st.number_input("Stündliche Betriebskosten (€/h) pro Gerät", min_value=0.0, step=0.1)
                monatliche_kosten = st.number_input("Monatliche Kosten (€/Monat) pro Gerät", min_value=0.0, step=0.1, value=0.0)
                speichern = st.form_submit_button("Gerät speichern")
            if speichern and geraet:
                if art == "Gekauft":
                    dauer = -1
                else:
                    dauer_db = dauer
                with engine.begin() as conn:
                    # Prüfe, ob Gerät bereits existiert
                    existing = conn.execute(
                        text("SELECT anzahl, monatliche_kosten, betriebskosten FROM geraete_lager WHERE geraet = :geraet AND benutzername = :benutzername"),
                        {"geraet": geraet, "benutzername": st.session_state.user}
                    ).fetchone()
                    
                    if existing:
                        # UPDATE: Addiere die Anzahl, aber behalte erste Kosten pro Gerät
                        existing_anzahl = existing[0] if existing[0] else 0
                        new_anzahl = existing_anzahl + anzahl
                        conn.execute(
                            text("""
                                UPDATE geraete_lager
                                SET anzahl = :anzahl, art = :art, dauer = :dauer, 
                                    betriebskosten = :betriebskosten, monatliche_kosten = :monatliche_kosten
                                WHERE geraet = :geraet AND benutzername = :benutzername
                            """),
                            {
                                "geraet": geraet,
                                "anzahl": new_anzahl,
                                "art": art,
                                "dauer": dauer,
                                "benutzername": st.session_state.user,
                                "betriebskosten": betriebskosten,
                                "monatliche_kosten": monatliche_kosten
                            }
                        )
                        st.success(f"Gerät '{geraet}' um {anzahl} Stück erweitert (insgesamt {new_anzahl}).")
                    else:
                        # INSERT: Neues Gerät mit aktuellem Datum
                        conn.execute(
                            text("""
                                INSERT INTO geraete_lager (geraet, anzahl, art, dauer, benutzername, betriebskosten, monatliche_kosten, datum_hinzugefuegt)
                                VALUES (:geraet, :anzahl, :art, :dauer, :benutzername, :betriebskosten, :monatliche_kosten, :datum_hinzugefuegt)
                            """),
                            {
                                "geraet": geraet,
                                "anzahl": anzahl,
                                "art": art,
                                "dauer": dauer,
                                "benutzername": st.session_state.user,
                                "betriebskosten": betriebskosten,
                                "monatliche_kosten": monatliche_kosten,
                                "datum_hinzugefuegt": datetime.now().strftime("%Y-%m-%d")
                            }
                        )
                        st.success(f"Gerät '{geraet}' ({anzahl}x) wurde gespeichert.")
                st.rerun()

        # Geräte-Tabelle anzeigen (Einheit nur im Text)
        df_geraete = pd.read_sql(
            "SELECT geraet, anzahl, art, dauer, betriebskosten, monatliche_kosten FROM geraete_lager WHERE benutzername = %s",
            engine, params=(st.session_state.user,)
        )
        if df_geraete.empty:
            st.info("Noch keine Geräte/Maschinen eingetragen.")
        else:
            st.subheader("Geräte-Lager")
            
            # Berechne Gesamtnutzung für jedes Gerät (auch archivierte Projekte)
            gesamtnutzung = {}
            for geraet in df_geraete['geraet']:
                nutzung_df = pd.read_sql(
                    """SELECT COALESCE(SUM(n.nutzungszeit), 0) as total 
                       FROM geraete_nutzung n
                       LEFT JOIN projekte p ON n.projekt_id = p.id
                       WHERE n.geraet = %s AND p.benutzername = %s""",
                    engine, params=(geraet, st.session_state.user)
                )
                gesamtnutzung[geraet] = float(nutzung_df['total'].iloc[0]) if not nutzung_df.empty else 0.0
            
            # HTML-Tabelle für Geräte-Lager
            table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;min-width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;position:sticky;top:0;z-index:2;}.scroll-table tr:hover{background:rgba(255,255,255,0.05);}</style>"
            table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Gerät</th><th>Anzahl</th><th>Art</th><th>Dauer</th><th>Gesamtnutzung (h)</th><th>Betriebskosten (€)</th><th>Monatliche Kosten (€)</th></tr></thead><tbody>"
            
            for _, row in df_geraete.iterrows():
                geraet = str(row['geraet']) if pd.notnull(row['geraet']) else ""
                anzahl = str(row['anzahl']) if pd.notnull(row['anzahl']) else "0"
                art = str(row['art']) if pd.notnull(row['art']) else "-"
                
                if row["art"] == "Gekauft" or row.get("dauer") == -1:
                    dauer = "-"
                else:
                    try:
                        dauer = f"{int(row['dauer'])} Monate" if pd.notnull(row['dauer']) else "-"
                    except:
                        dauer = "-"
                
                # Gesamtnutzung anzeigen
                gesamt_stunden = gesamtnutzung.get(geraet, 0.0)
                gesamt_str = f"{gesamt_stunden:.1f}h" if gesamt_stunden > 0 else "0h"
                
                betriebskosten = f"{float(row['betriebskosten']):.2f} €/h" if pd.notnull(row['betriebskosten']) and row['betriebskosten'] > 0 else "-"
                monatliche_kosten = f"{float(row['monatliche_kosten']):.2f} €/Monat" if pd.notnull(row['monatliche_kosten']) and row['monatliche_kosten'] > 0 else "-"
                
                table_html += f"<tr><td><strong>{geraet}</strong></td><td>{anzahl}</td><td>{art}</td><td>{dauer}</td><td>{gesamt_str}</td><td>{betriebskosten}</td><td>{monatliche_kosten}</td></tr>"
            
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
        st.subheader("Geräte-Nutzungen")
# Alle Projekte des Bauunternehmers laden
        # Ensure geraete_nutzung table has projekt_id column
        with engine.begin() as conn:
            try:
                conn.exec_driver_sql("ALTER TABLE geraete_nutzung ADD COLUMN projekt_id INTEGER")
            except:
                pass  # Column already exists
        
        df_projekte = pd.read_sql(
            "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
            engine, params=(st.session_state.user,)
        )
        geraete_nutzung_df = pd.read_sql("""
            SELECT n.datum, n.geraet, n.nutzungszeit, p.name AS projektname
            FROM geraete_nutzung n
            LEFT JOIN projekte p ON n.projekt_id = p.id
            WHERE p.benutzername = %s AND p.archiviert_am IS NULL
            ORDER BY n.datum DESC, p.name, n.geraet
        """, engine, params=(st.session_state.user,))

        if geraete_nutzung_df.empty:
            st.info("Keine Geräte-Nutzungen vorhanden.")
        else:
            # Pivot-Tabelle: Zeilen = Datum, Spalten = Projektname, Inhalt = Maschinen mit Nutzungszeit
            def format_maschinen(gruppe):
                return "<br>".join([f"{row['geraet']} ({row['nutzungszeit']}h)" for _, row in gruppe.iterrows()])

            # Gruppieren nach Datum und Projekt
            grouped = geraete_nutzung_df.groupby(["datum", "projektname"])
            table_data = []
            for (datum, projektname), gruppe in grouped:
                table_data.append({
                    "Datum": datum,
                    "Projekt": projektname,
                    "Maschinen": format_maschinen(gruppe)
                })
            df_anzeige = pd.DataFrame(table_data)
            # Pivot: Zeilen = Datum, Spalten = Projekt, Inhalt = Maschinen
            pivot = df_anzeige.pivot(index="Datum", columns="Projekt", values="Maschinen").fillna("")
            pivot = pivot.applymap(lambda x: x.replace("<br>", "\n") if isinstance(x, str) else x)
            table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
            table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Datum</th>"
            for col in pivot.columns:
                table_html += f"<th>{col}</th>"
            table_html += "</tr></thead><tbody>"
            for idx, row in pivot.iterrows():
                table_html += f"<tr><td><strong>{idx}</strong></td>"
                for col in pivot.columns:
                    val = str(row[col]) if pd.notnull(row[col]) and row[col] != "" else "-"
                    table_html += f"<td>{val}</td>"
                table_html += "</tr>"
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
        # Geräte löschen
        with st.expander("🗑️ Gerät löschen"):
            geraete_liste = df_geraete["geraet"].tolist()
            if not geraete_liste:
                st.info("Keine Geräte vorhanden.")
            else:
                geraet_zum_loeschen = st.selectbox("Gerät auswählen", geraete_liste)
                if st.button("Gerät löschen"):
                    with engine.begin() as conn:
                        conn.execute(
                            text("DELETE FROM geraete_lager WHERE geraet = :geraet AND benutzername = :benutzername"),
                            {"geraet": geraet_zum_loeschen, "benutzername": st.session_state.user}
                        )
                    st.success(f"Gerät '{geraet_zum_loeschen}' wurde gelöscht.")
                    st.rerun()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------    
    
    
    
    
    
    
    
    
    
    elif nav == "Mitarbeiter":
        st.header("Mitarbeiterverwaltung")
        st.subheader("🕒 Arbeitszeiterfassungen aller Mitarbeiter")
        # === Daten laden ===
        arbeitszeiten_df = pd.read_sql("SELECT * FROM arbeitszeiten", engine)
        projekte_df = pd.read_sql("SELECT id, name FROM projekte", engine)


        # Projektname zum Projekt ID mappen
        projekt_dict = dict(zip(projekte_df["id"], projekte_df["name"]))
        with st.expander("🔽 Zeiterfassungen anzeigen"):
            # Arbeitszeiten-Tabelle immer anzeigen, auch wenn leer
            if arbeitszeiten_df.empty:
                st.info("Keine Arbeitszeiten erfasst. Es sind keine Einträge vorhanden.")
            else:
                if "projekt_id" in arbeitszeiten_df.columns:
                    arbeitszeiten_df["projektname"] = arbeitszeiten_df["projekt_id"].map(projekt_dict).fillna("Unbekannt")
                else:
                    arbeitszeiten_df["projektname"] = "Unbekannt"
                arbeitszeiten_df["stunden"] = pd.to_numeric(arbeitszeiten_df["stunden"], errors="coerce")
                mitarbeiter_df = pd.read_sql("SELECT benutzername, vorname, nachname FROM mitarbeiter", engine)
                name_map = mitarbeiter_df.set_index("benutzername").apply(lambda x: f"{x['vorname']} {x['nachname']}", axis=1).to_dict()
                arbeitszeiten_df["voller_name"] = arbeitszeiten_df["benutzername"].map(name_map).fillna(arbeitszeiten_df["benutzername"])
                # Berechne Durchschnitt der letzten 13 Wochen pro Mitarbeiter
                arbeitszeiten_df["datum_dt"] = pd.to_datetime(arbeitszeiten_df["datum"], errors="coerce")
                avg_stunden = {}
                def sick_eintrag(row):
                    if row.get("status") == "krank":
                        return f"krank ({avg_stunden.get(row['benutzername'], 0.0)} h)"
                    return f"{row['startzeit']} - {row['endzeit']} (⏱️ {row['stunden']:.1f} h)"
                arbeitszeiten_df["eintrag"] = arbeitszeiten_df.apply(sick_eintrag, axis=1)
                arbeitszeiten_df["spalte"] = arbeitszeiten_df["projektname"] + " (" + arbeitszeiten_df["voller_name"] + ")"
                pivot_df = arbeitszeiten_df.pivot_table(index="datum", columns="spalte", values="eintrag", aggfunc="first").fillna("–")
                stunden_summen = arbeitszeiten_df.groupby("spalte")["stunden"].sum().round(1)
                stunden_summen.name = "⏳ Gesamtstunden"
                stunden_summen = stunden_summen.astype(str) + " h"
                # Summe als letzte Zeile anhängen
                pivot_df.loc["⏳ Gesamtstunden"] = stunden_summen
                pivot_df = pivot_df.reindex(sorted(pivot_df.columns), axis=1)
                st.subheader("Übersicht: Arbeitszeiten nach Projekt und Mitarbeiter")
                # HTML-Tabelle für Arbeitszeiten
                table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
                table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Datum</th>"
                for col in pivot_df.columns:
                    table_html += f"<th>{col}</th>"
                table_html += "</tr></thead><tbody>"
                for idx, row in pivot_df.iterrows():
                    table_html += f"<tr><td><strong>{idx}</strong></td>"
                    for col in pivot_df.columns:
                        val = str(row[col]) if pd.notnull(row[col]) else "-"
                        table_html += f"<td>{val}</td>"
                    table_html += "</tr>"
                table_html += "</tbody></table></div>"
                st.markdown(table_html, unsafe_allow_html=True)
            with st.expander("🗑️ Arbeitszeiteintrag löschen"):
                if arbeitszeiten_df.empty:
                    st.info("Es sind keine Arbeitszeiteinträge vorhanden.")
                else:
                    datum_liste = arbeitszeiten_df["datum"].drop_duplicates().sort_values().tolist()
                    datum_zum_loeschen = st.selectbox("Wähle das Datum aus", datum_liste)
                    if st.button("Eintrag(e) für dieses Datum löschen"):
                        with engine.begin() as conn:
                            conn.exec_driver_sql(
                                "DELETE FROM arbeitszeiten WHERE datum = %s",
                                (datum_zum_loeschen,)
                            )
                        st.success(f"Arbeitszeiteintrag(e) für **{datum_zum_loeschen}** wurden gelöscht.")
                        st.rerun()
        st.subheader("👷‍♂️ Mitarbeiterkonto anlegen")
        # Projekte dieses Bauunternehmers laden
        with st.expander("🔽 Mitarbeiter anlegen"):    
            df_projekte = pd.read_sql(
                "SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL",
                engine, params=(st.session_state.user,)
            )

            if df_projekte.empty:
                st.info("Bitte zuerst mindestens ein Projekt anlegen.")
            else:
                with st.form("mitarbeiter_anlegen_form"):
                    mitarbeitername = st.text_input("Benutzername des Mitarbeiters")
                    vorname = st.text_input("Vorname des Mitarbeiters")
                    nachname = st.text_input("Nachname des Mitarbeiters")
                    passwort = st.text_input("Passwort", type="password")
                    rolle = st.selectbox("Rolle", ROLLEN)
                    projekt_liste = df_projekte[["id", "name"]].drop_duplicates().sort_values("name")
                    projekt_name = st.selectbox("Projekt zuweisen", projekt_liste["name"].tolist())
                    abschicken = st.form_submit_button("Mitarbeiter anlegen")

                if abschicken:
                    vorhandene = pd.read_sql(
                        "SELECT * FROM mitarbeiter WHERE benutzername = %s",
                        engine,
                        params=(mitarbeitername,)
                    )
                    if not vorhandene.empty:
                        st.warning(f"Benutzername '{mitarbeitername}' ist bereits vergeben. Bitte wähle einen anderen.")
                    else:
                        projekt_id = int(projekt_liste.loc[projekt_liste["name"] == projekt_name, "id"].values[0])
                        try:
                            with engine.begin() as conn:
                                # Hash the password and create the employee
                                hashed_password = hash_password(passwort)
                                conn.exec_driver_sql("""
                                INSERT INTO mitarbeiter (benutzername, vorname, nachname, passwort, chefname, rolle, geraeteverwaltung)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (mitarbeitername, vorname, nachname, hashed_password, st.session_state.user, rolle, 0))
                                
                                # Then assign them to the selected project (include chefname)
                                conn.exec_driver_sql("""
                                INSERT INTO mitarbeiter_projekte (mitarbeiter_benutzername, projekt_id, chefname)
                                VALUES (%s, %s, %s)
                                """, (mitarbeitername, projekt_id, st.session_state.user))
                                
                            st.success(f"Mitarbeiterkonto '{mitarbeitername}' wurde erfolgreich erstellt.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler beim Anlegen: {e}")
        
        # Ensure mitarbeiter_projekte table exists before any JOINs that use it
        with engine.begin() as conn:
            conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS mitarbeiter_projekte (
                    mitarbeiter_benutzername TEXT,
                    projekt_id INTEGER,
                    chefname TEXT,
                    PRIMARY KEY (mitarbeiter_benutzername, projekt_id)
                )
            """)
            # PostgreSQL: ensure_schema() already created all tables with correct columns


        
        # Hole Mitarbeiter mit ihren Projekten - bessere Query mit Subselect
        df_mitarbeiter = pd.read_sql(
            """
            SELECT DISTINCT 
                m.benutzername, 
                m.passwort, 
                m.rolle,
                COALESCE(
                    (SELECT STRING_AGG(p.name, ', ')
                     FROM mitarbeiter_projekte mp_sub
                     JOIN projekte p ON mp_sub.projekt_id = p.id
                     WHERE mp_sub.mitarbeiter_benutzername = m.benutzername
                       AND mp_sub.chefname = %s
                    ), 
                    '-'
                ) AS Projektname
            FROM mitarbeiter m
            WHERE m.chefname = %s
            ORDER BY m.benutzername
            """,
            engine,
            params=(st.session_state.user, st.session_state.user)
        )
            # vollen Namen berechnen und als erste Spalte anzeigen
        df_mitarbeiter["voller_name"] = df_mitarbeiter["benutzername"].map(
                lambda bn: f"{bn}"  # Fallback falls Name nicht gefunden
            )
            # Hole Vorname/Nachname aus der DB
        namen_df = pd.read_sql("SELECT benutzername, vorname, nachname FROM mitarbeiter", engine)
        name_map = namen_df.set_index("benutzername").apply(lambda x: f"{x['vorname']} {x['nachname']}", axis=1).to_dict()
        df_mitarbeiter["voller_name"] = df_mitarbeiter["benutzername"].map(name_map).fillna(df_mitarbeiter["benutzername"])
        
        
        # HTML-Tabelle für Mitarbeiter - FIX: Korrekte Spaltennamen verwenden
        table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
        table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Vollständiger Name</th><th>Benutzername</th><th>Rolle</th><th>Projekte</th></tr></thead><tbody>"
        for _, row in df_mitarbeiter.iterrows():
            voller_name = str(row['voller_name']) if pd.notnull(row['voller_name']) else ""
            benutzername = str(row['benutzername']) if pd.notnull(row['benutzername']) else ""
            rolle = str(row['rolle']) if pd.notnull(row['rolle']) else "-"
            # Versuche beide Spaltennamen (Projektname und projektname)
            if 'Projektname' in row.index:
                projektname = str(row['Projektname']) if pd.notnull(row['Projektname']) else "-"
            elif 'projektname' in row.index:
                projektname = str(row['projektname']) if pd.notnull(row['projektname']) else "-"
            else:
                projektname = "-"
            table_html += f"<tr><td><strong>{voller_name}</strong></td><td>{benutzername}</td><td>{rolle}</td><td>{projektname}</td></tr>"
        table_html += "</tbody></table></div>"
        st.markdown(table_html, unsafe_allow_html=True)
        with st.expander(" Mitarbeiterkonto bearbeiten/löschen"):
            if df_mitarbeiter.empty:
                st.info("Es sind keine Mitarbeiter vorhanden.")
            else:
                # Mitarbeiter-Auswahl mit vollem Namen und Rolle
                df_mitarbeiter["anzeige"] = df_mitarbeiter.apply(lambda x: f"{x['voller_name']} ({x['rolle']})", axis=1)
                mitarbeiter_auswahl = st.selectbox("Mitarbeiter auswählen", df_mitarbeiter["anzeige"].tolist())
                mitarbeiter_row = df_mitarbeiter[df_mitarbeiter["anzeige"] == mitarbeiter_auswahl].iloc[0]
                benutzername = mitarbeiter_row["benutzername"]
                # Projekt-Verwaltung
                df_projekte = pd.read_sql("SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
                projekt_liste = df_projekte["name"].tolist()
                
                # Zeige aktuelle Projekt-Zuweisungen
                df_zuweisungen = pd.read_sql(
                    """
                    SELECT p.name as projektname 
                    FROM mitarbeiter_projekte mp 
                    JOIN projekte p ON mp.projekt_id = p.id 
                    WHERE mp.mitarbeiter_benutzername = %s
                    """, 
                    engine, 
                    params=(benutzername,)
                )
                if not df_zuweisungen.empty:
                    st.write("Aktuelle Projekte:")
                    for _, row in df_zuweisungen.iterrows():
                        st.write(f"- {row['projektname']}")
                else:
                    st.write("Keine Projekte zugewiesen")
                
                # Projekt-Auswahl für neue Zuweisung
                projekt_auswahl = st.selectbox(
                    "Projekt auswählen (für Zuweisung)",
                    [""] + projekt_liste,  # Empty option first
                    index=0
                )
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("Löschen", key="mitarbeiter_loeschen"):
                        with engine.begin() as conn:
                            # First remove all project assignments
                            conn.exec_driver_sql(
                                "DELETE FROM mitarbeiter_projekte WHERE mitarbeiter_benutzername = %s",
                                (benutzername,)
                            )
                            # Then delete the employee
                            conn.exec_driver_sql(
                                "DELETE FROM mitarbeiter WHERE benutzername = %s",
                                (benutzername,)
                            )
                        st.success(f"Mitarbeiter **{mitarbeiter_auswahl}** wurde gelöscht.")
                        st.rerun()
                
                with col2:
                    if st.button("+ Projekt zuweisen", key="projekt_zuweisen") and projekt_auswahl:
                        projekt_id = int(df_projekte[df_projekte["name"] == projekt_auswahl]["id"].iloc[0])
                        with engine.begin() as conn:
                            conn.exec_driver_sql(
                                """
                                INSERT INTO mitarbeiter_projekte 
                                (mitarbeiter_benutzername, projekt_id, chefname) 
                                VALUES (%s, %s, %s)
                                ON CONFLICT (mitarbeiter_benutzername, projekt_id) DO NOTHING
                                """,
                                (benutzername, projekt_id, st.session_state.user)
                            )
                        st.success(f"Mitarbeiter **{mitarbeiter_auswahl}** wurde dem Projekt **{projekt_auswahl}** zugewiesen.")
                        st.rerun()
                
                with col3:
                    if st.button("- Projekt entfernen", key="projekt_entfernen") and projekt_auswahl:
                        projekt_id = int(df_projekte[df_projekte["name"] == projekt_auswahl]["id"].iloc[0])
                        with engine.begin() as conn:
                            conn.exec_driver_sql(
                                "DELETE FROM mitarbeiter_projekte WHERE mitarbeiter_benutzername = %s AND projekt_id = %s",
                                (benutzername, projekt_id)
                            )
                        st.success(f"Projekt **{projekt_auswahl}** wurde von Mitarbeiter **{mitarbeiter_auswahl}** entfernt.")
                        st.rerun()
                
                with col4:
                    if st.button("Alle Projekte entfernen", key="alle_projekte_entfernen"):
                        with engine.begin() as conn:
                            conn.exec_driver_sql(
                                "DELETE FROM mitarbeiter_projekte WHERE mitarbeiter_benutzername = %s",
                                (benutzername,)
                            )
                        st.success(f"Alle Projekte wurden von Mitarbeiter **{mitarbeiter_auswahl}** entfernt.")
                        st.rerun()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------













    elif nav == "Lohnübersicht":
        lohnabrechnung_page()
        st.set_page_config(page_title="Bauunternehmen App", layout="centered")
        with engine.begin() as conn:
        # Einmalige Spaltenerweiterung – sicher ausführen, falls Spalte noch nicht existiert
            try:
                conn.exec_driver_sql("ALTER TABLE projekte ADD COLUMN benutzername TEXT;")
            except:
                pass
            try:    
                conn.exec_driver_sql("ALTER TABLE materialien ADD COLUMN benutzername TEXT;")
            except:
                pass
            try:
                conn.exec_driver_sql("ALTER TABLE lagerbestand ADD COLUMN benutzername TEXT;")
            except:
                pass
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------











    
    
    
    
    
    elif nav == "Rechnung erstellen":
        # ✅ Prüfe ob Bank- und Registerdaten vorhanden sind
        required_bank_fields = {
            "iban": "IBAN",
            "bic": "BIC",
            "bankname": "Bankname"
        }
        missing_bank_fields = [field for field in required_bank_fields.keys() if not st.session_state.get(field)]
        
        if missing_bank_fields:
            # Leite zur Setup-Seite für Bank-Daten um
            st.session_state.page = "setup_bank_register_data"
            st.session_state.return_page = "app"  # Merke dass wir vom Invoice zurückkommen
            st.rerun()
        
        st.header("Rechnung manuell erstellen")

        st.markdown("Hier kannst du eine individuelle Rechnung für ein Projekt erstellen.")
        # 1. Projekt manuell eingeben oder aus Liste auswählen
        # Hole alle Projekte des Benutzers
        df_projekte = pd.read_sql("SELECT name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
        projekt_liste = df_projekte["name"].tolist()
        if not projekt_liste:
            st.warning("Keine aktiven Projekte vorhanden. Bitte zuerst ein Projekt anlegen.")
            projekt_name = ""
        else:
            # Callback: wenn ein Projekt ausgewählt wird, autofülle die zugehörige Rechnungsnummer
            def _update_rechnungsnummer():
                pn = st.session_state.get("projekt_select")
                if not pn:
                    return
                df_p = pd.read_sql("SELECT rechnungsnummer FROM projekte WHERE name = %s AND benutzername = %s", engine, params=(pn, st.session_state.user))
                if not df_p.empty and pd.notnull(df_p["rechnungsnummer"].iloc[0]):
                    st.session_state["rechnungsnummer_input"] = int(df_p["rechnungsnummer"].iloc[0])
                else:
                    st.session_state["rechnungsnummer_input"] = st.session_state.get("standard_rechnungsnummer", 1)

            projekt_name = st.selectbox("Projektname", projekt_liste, index=0, key="projekt_select", on_change=_update_rechnungsnummer)
        empfaenger_name = st.text_input("Empfängername")
        empfaenger_adresse = st.text_area("Empfängeradresse")
        
        leistungszeitraum_start = st.date_input(
            "Leistungszeitraum Beginn",
            value=st.session_state.get("leistungszeitraum_start", date.today()),
            key="leistungszeitraum_start"
        )
        leistungszeitraum_ende = st.date_input("Leistungszeitraum Ende", value=date.today(), key="leistungszeitraum_ende")
    
        
                # Rechnungsnummer bestimmen (nicht im Session-State speichern!)
        df_projekt = pd.read_sql("SELECT id, rechnungsnummer FROM projekte WHERE name = %s AND benutzername = %s", engine, params=(projekt_name, st.session_state.user))
        if not df_projekt.empty and pd.notnull(df_projekt["rechnungsnummer"].iloc[0]):
            autofill_rechnungsnummer = int(df_projekt["rechnungsnummer"].iloc[0])
        else:
            autofill_rechnungsnummer = st.session_state.get("standard_rechnungsnummer", 1)

        # If the input widget has not been set in session state yet, initialize it so the widget shows the project's number
        if "rechnungsnummer_input" not in st.session_state:
            st.session_state["rechnungsnummer_input"] = autofill_rechnungsnummer

        rechnungsnummer = st.number_input(
            "Rechnungsnummer",
            min_value=1,
            step=1,
            key="rechnungsnummer_input"
        )
        # 3. Rechnungsnummer-Widget anzeigen
        # --- Rechnungsmodus auswählen ---
        rechnungsmodus = st.radio(
            "Rechnungsmodus wählen",
            ["Berechnet (automatisch)", "Pauschale (Festpreis)"],
            key="rechnungsmodus"  # Use consistent key for state management
        )
       
       
        # Button zum automatischen Ausfüllen der Positionen
        if rechnungsmodus == "Berechnet (automatisch)":
            if st.button("Formular automatisch mit Projekt-Daten ausfüllen"):
                # ...existing code for automatische Berechnung...
                df_projekt = pd.read_sql("SELECT id, rechnungsnummer FROM projekte WHERE name = %s AND benutzername = %s", engine, params=(projekt_name, st.session_state.user))
                if not df_projekt.empty:             
                    projekt_id = int(df_projekt["id"].iloc[0])
                    # Die Rechnungsnummer wurde bereits durch _update_rechnungsnummer() gesetzt
                    if "datum" in df_projekt.columns and pd.notnull(df_projekt["datum"].iloc[0]):
                        st.session_state.leistungszeitraum_start = datetime.strptime(df_projekt["datum"].iloc[0], "%Y-%m-%d").date()
                    df_material = pd.read_sql("SELECT material, menge, einheit FROM materialien WHERE projekt_id = %s AND benutzername = %s", engine, params=(projekt_id, st.session_state.user))
                    df_lager = pd.read_sql("SELECT material, preis_ankauf, preis_verkauf FROM lagerbestand WHERE benutzername = %s", engine, params=(st.session_state.user,))
                    i = 0
                    for row in df_material.itertuples():
                        menge = float(row.menge) if row.menge is not None else 0.0
                        if menge > 0:
                            st.session_state[f"name_{i}"] = row.material
                            st.session_state[f"menge_{i}"] = menge
                            st.session_state[f"einheit_{i}"] = row.einheit if row.einheit is not None else ""
                            preis_row = df_lager[df_lager["material"] == row.material]
                            preis = preis_row["preis_verkauf"].iloc[0] if not preis_row.empty and preis_row["preis_verkauf"].iloc[0] is not None else 0.0
                            st.session_state[f"preis_{i}"] = preis
                            i += 1
                    st.session_state.rechnungs_positionen = max(i, 1)

                    df_mitarbeiter = pd.read_sql("""
                        SELECT m.benutzername, m.rolle 
                        FROM mitarbeiter m
                        JOIN mitarbeiter_projekte mp ON m.benutzername = mp.mitarbeiter_benutzername
                        WHERE mp.projekt_id = %s AND m.chefname = %s
                    """, engine, params=(projekt_id, st.session_state.user))
                    df_gehalt = pd.read_sql("SELECT rolle, gehalt FROM standardgehaelter", engine)
                    j = 0
                    for row in df_mitarbeiter.itertuples():
                        df_stunden = pd.read_sql(
                            "SELECT SUM(stunden) as gesamtstunden FROM arbeitszeiten WHERE projekt_id = %s AND benutzername = %s",
                            engine, params=(projekt_id, row.benutzername)
                        )
                        gesamtstunden = df_stunden["gesamtstunden"].iloc[0] if not df_stunden.empty and df_stunden["gesamtstunden"].iloc[0] is not None else 0.0
                        if gesamtstunden > 0:
                            st.session_state[f"rolle_{j}"] = row.rolle
                            gehalt_row = df_gehalt[df_gehalt["rolle"] == row.rolle]
                            stundensatz = gehalt_row["gehalt"].iloc[0] if not gehalt_row.empty else 0.0
                            st.session_state[f"lohn_{j}"] = stundensatz
                            st.session_state[f"stunden_{j}"] = gesamtstunden
                            j += 1
                    st.session_state.anzahl_mitarbeiter = max(j, 1)
                    df_geraete_nutzung = pd.read_sql("""
                        SELECT n.geraet, SUM(n.nutzungszeit) as stunden
                        FROM geraete_nutzung n
                        WHERE n.projekt_id = %s
                        GROUP BY n.geraet
                    """, engine, params=(projekt_id,))
                    df_geraete_lager = pd.read_sql(
                        "SELECT geraet, betriebskosten FROM geraete_lager WHERE benutzername = %s",
                        engine, params=(st.session_state.user,)
                    )
                    k = 0
                    for row in df_geraete_nutzung.itertuples():
                        stunden = float(row.stunden) if row.stunden is not None else 0.0
                        if stunden > 0:
                            st.session_state[f"geraet_{k}"] = row.geraet
                            st.session_state[f"geraet_stunden_{k}"] = stunden
                            kosten_row = df_geraete_lager[df_geraete_lager["geraet"] == row.geraet]
                            default_kosten = float(kosten_row["betriebskosten"].iloc[0]) if not kosten_row.empty else 0.0
                            st.session_state[f"geraet_kosten_{k}"] = default_kosten
                            k += 1
                    st.session_state.geraete_positionen = max(k, 1)
                    st.success("Formular wurde automatisch mit Projekt-Daten ausgefüllt.")
                else:
                    st.warning("Projekt nicht gefunden. Bitte korrekten Projektnamen eingeben.")
        # 2. Manuell Positionen hinzufügen (Materialien/Leistungen)
        if rechnungsmodus == "Berechnet (automatisch)":
            st.subheader("Rechnungspositionen hinzufügen")
            positionen = []
            if "rechnungs_positionen" not in st.session_state:
                st.session_state.rechnungs_positionen = 1
            col_add, col_remove = st.columns([1, 1])
            with col_add:
                if st.button("+ Position hinzufügen"):
                    st.session_state.rechnungs_positionen += 1
            with col_remove:
                if st.button("- Position entfernen"):
                    if st.session_state.rechnungs_positionen > 1:
                        st.session_state.rechnungs_positionen -= 1       
            if "anzahl_mitarbeiter" not in st.session_state:
                st.session_state.anzahl_mitarbeiter = 1
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("+ Mitarbeiterposition hinzufügen"):
                    st.session_state.anzahl_mitarbeiter += 1
            with col2:
                if st.button("- Mitarbeiterposition entfernen") and st.session_state.anzahl_mitarbeiter > 1:
                    st.session_state.anzahl_mitarbeiter -= 1
            if "geraete_positionen" not in st.session_state:
                st.session_state.geraete_positionen = 1
            col_add_g, col_remove_g = st.columns([1, 1])
            with col_remove_g:
                if st.button("- Geräteposition entfernen") and st.session_state.geraete_positionen > 1:
                    if st.session_state.geraete_positionen > 1:
                        st.session_state.geraete_positionen -= 1

            with col_add_g:
                if st.button("+ Geräteposition hinzufügen"):
                    st.session_state.geraete_positionen += 1
            # ...existing code für berechnete Positionen...
        else:
            st.subheader("Pauschalbetrag eingeben")
            pauschale = st.number_input("Pauschalbetrag (Brutto, EUR)", min_value=0.0, step=0.01, key="pauschalbetrag")
            st.info("Die Rechnung wird als Pauschale erstellt. Der Betrag wird als Bruttowert übernommen.")
        df_geraete_lager = pd.read_sql(
            "SELECT geraet, betriebskosten FROM geraete_lager WHERE benutzername = %s",
            engine, params=(st.session_state.user,)
        )
        geraete_liste = df_geraete_lager["geraet"].tolist()
        if rechnungsmodus == "Berechnet (automatisch)":
            # Hole alle Materialien aus dem Lagerbestand
            df_materialien = pd.read_sql(
                "SELECT material, einheit, preis_verkauf FROM lagerbestand WHERE benutzername = %s",
                engine,
                params=(st.session_state.user,)
            )
            materialien_liste = [""] + sorted(df_materialien["material"].tolist())
            
            with st.form("rechnungsformular"):
                st.subheader("Matreialkosten")
                positionen = []
                for i in range(st.session_state.rechnungs_positionen):
                    cols = st.columns([4, 2, 2, 2])
                    name = cols[0].selectbox("Bezeichnung", materialien_liste, key=f"name_{i}")
                    menge = cols[1].number_input("Menge", min_value=0.0, step=1.0, key=f"menge_{i}")
                    
                    # Hole Einheit und Verkaufspreis wenn Material ausgewählt
                    if name and name in df_materialien["material"].values:
                        material_row = df_materialien[df_materialien["material"] == name].iloc[0]
                        einheit = material_row["einheit"]
                        default_preis = float(material_row["preis_verkauf"]) if pd.notnull(material_row["preis_verkauf"]) else 0.0
                    else:
                        einheit = EINHEITEN[0]
                        default_preis = 0.0
                    
                    einheit = cols[2].selectbox("Einheit", EINHEITEN, key=f"einheit_{i}", index=EINHEITEN.index(einheit) if einheit in EINHEITEN else 0)
                    preis = cols[3].number_input("Einzelpreis (€)", min_value=0.0, step=0.1, value=default_preis, key=f"preis_{i}")
                    
                    if name and menge > 0:
                        positionen.append({"name": name, "menge": menge, "einheit": einheit, "preis": preis})
                st.subheader("Mitarbeiterleistungen")
                arbeitsleistungen = []
                for j in range(st.session_state.anzahl_mitarbeiter): 
                    cols = st.columns([4, 0.5, 2, 0.5, 2,])
                    rolle = cols[0].selectbox("Rolle", [""] + ROLLEN, key=f"rolle_{j}")
                    stundensatz = cols[2].number_input("Stundenlohn (€)", min_value=0.0, key=f"lohn_{j}")
                    stunden = cols[4].number_input("Geleistete Stunden", min_value=0.0, key=f"stunden_{j}")
                    if rolle and stunden > 0:
                        arbeitsleistungen.append({
                            "rolle": rolle,
                            "stundensatz": stundensatz,
                            "stunden": stunden
                        })
                st.subheader("Gerätekosten")
                geraetepositionen = []
                for k in range(st.session_state.geraete_positionen):
                    cols = st.columns([4, 2, 2])
                    geraet = cols[0].selectbox("Gerät", [""] + geraete_liste, key=f"geraet_{k}")
                    stunden = cols[1].number_input("Nutzungsstunden", min_value=0.0, step=0.1, key=f"geraet_stunden_{k}")
                    default_kosten = float(df_geraete_lager[df_geraete_lager["geraet"] == geraet]["betriebskosten"].iloc[0]) if geraet in geraete_liste else 0.0
                    kosten = cols[2].number_input("Betriebskosten (€ pro Std)", min_value=0.0, step=0.1, value=default_kosten, key=f"geraet_kosten_{k}")
                    if geraet and stunden > 0:
                        geraetepositionen.append({
                            "geraet": geraet,
                            "stunden": stunden,
                            "betriebskosten": kosten
                        })
                erstellen = st.form_submit_button("Rechnung erstellen")
        elif rechnungsmodus == "Pauschale (Festpreis)":
            positionen = [
                {
                    "name": f"{projekt_name} ",
                    "menge": 1,
                    "einheit": "Pauschale",
                    "preis": pauschale,
                    "gesamtpreis": pauschale
                }
            ]
            with st.form("rechnungsformular"):
                erstellen = st.form_submit_button("Rechnung erstellen")
        if erstellen and projekt_name and empfaenger_name:
            num_check = pd.read_sql("SELECT name FROM projekte WHERE rechnungsnummer = %s AND benutzername = %s", engine, params=(rechnungsnummer, st.session_state.user))
            if not num_check.empty and num_check["name"].iloc[0] != projekt_name:
                st.error(f"Rechnungsnummer {rechnungsnummer} ist bereits für Projekt '{num_check['name'].iloc[0]}' vergeben!")
            else:
                rechnungsmodus = st.session_state.rechnungsmodus  # Use the radio button's state directly
                
                # Unterschiedliche PDF-Generierung je nach Modus
                if rechnungsmodus == "Pauschale (Festpreis)":
                    # Im Pauschalmodus keine Positionen, nur den Pauschalbetrag übergeben
                    # Im Pauschalmodus keine Positionen, nur den Pauschalbetrag übergeben
                    pdf_buffer = generate_pauschal_invoice_pdf(
                        projekt_name,
                        empfaenger_name,
                        empfaenger_adresse,
                        pauschale,  # Bruttobetrag für Pauschale
                        rechnungsnummer,
                        leistungszeitraum_start,
                        leistungszeitraum_ende
                    )
                    # ✅ RICHTIG: pauschale ist BRUTTO, nettobetrag = brutto / 1.19
                    nettobetrag = pauschale / 1.19
                else:
                    # Berechnet (automatisch) Modus
                    if 'arbeitsleistungen' not in locals():
                        arbeitsleistungen = []
                    if 'geraetepositionen' not in locals():
                        geraetepositionen = []
                    
                    pdf_buffer = generate_invoice_pdf_v2(
                        projekt_name,
                        empfaenger_name,
                        empfaenger_adresse,
                        [(p["name"], p["menge"],p["einheit"], p["preis"]) for p in positionen],
                        arbeitsleistungen,
                        rechnungsnummer,
                        leistungszeitraum_start,
                        leistungszeitraum_ende,
                        geraetepositionen
                    )
                    # ✅ Berechne Netto aus allen Positionen
                    nettobetrag = 0.0
                    # Material
                    if 'positionen' in locals():
                        for p in positionen:
                            nettobetrag += p.get("preis", 0.0) * p.get("menge", 0.0)
                    # Arbeitsleistungen
                    if arbeitsleistungen:
                        for leistung in arbeitsleistungen:
                            nettobetrag += leistung.get("stundensatz", 0.0) * leistung.get("stunden", 0.0)
                    # Gerätekosten
                    if geraetepositionen:
                        for pos in geraetepositionen:
                            nettobetrag += pos.get("betriebskosten", 0.0) * pos.get("stunden", 0.0)
                
                pdf_buffer.seek(0)
                pdf_bytes = pdf_buffer.getvalue()
                st.markdown(f"**PDF-Größe beim Speichern:** {len(pdf_bytes)} Bytes")
                st.markdown(f"**PDF-Bytes (Hex, erste 100):** {pdf_bytes[:100].hex()}")
                # PDF auch in die Tabelle 'rechnungen' speichern
                benutzername = st.session_state.get("user")
                if not benutzername or benutzername is None:
                    st.error("Kein Benutzername gesetzt! Bitte zuerst einloggen.")
                    return
                
                # Stelle sicher, dass die Spalte benutzername existiert (separate connection)
                try:
                    with engine.begin() as temp_conn:
                        temp_conn.exec_driver_sql("ALTER TABLE rechnungen ADD COLUMN benutzername TEXT")
                except Exception:
                    pass  # Column already exists
                
                # Now use a fresh connection for the INSERT
                with engine.begin() as conn:
                    # Stelle sicher, dass ein Benutzer angemeldet ist und übergebe den Benutzernamen beim Speichern
                    benutzername = st.session_state.get("user")
                    if not benutzername:
                        st.error("Bitte melden Sie sich zuerst an, bevor Sie eine Rechnung speichern.")
                    else:
                        try:
                            # Delete old invoice if exists and insert new one
                            conn.exec_driver_sql(
                                "DELETE FROM rechnungen WHERE projekt_name = %s AND rechnungsnummer = %s",
                                (projekt_name, rechnungsnummer)
                            )
                            conn.exec_driver_sql(
                                "INSERT INTO rechnungen (projekt_name, rechnungsnummer, pdf_data, erstellt_am, nettobetrag, benutzername) VALUES (%s, %s, %s, %s, %s, %s)",
                                (projekt_name, rechnungsnummer, pdf_bytes, date.today().strftime("%Y-%m-%d"), nettobetrag, benutzername)
                            )
                            conn.commit()
                            st.success("Rechnung gespeichert.")
                            try:
                                # Ensure the project row stores this invoice number so it can be autofilled next time
                                conn.exec_driver_sql(
                                    "UPDATE projekte SET rechnungsnummer = %s WHERE name = %s AND benutzername = %s",
                                    (rechnungsnummer, projekt_name, benutzername)
                                )
                                conn.commit()
                            except Exception:
                                conn.rollback()
                                pass
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Fehler beim Speichern der Rechnung: {str(e)}")
                        st.download_button("📥 Rechnung als PDF herunterladen", data=pdf_bytes, file_name=f"Rechnung_{projekt_name}_{rechnungsnummer}.pdf", mime="application/pdf")
        elif erstellen:
            st.warning("Bitte Projektname und Empfängerdaten eingeben.")
#---------------------------------------------------------------------------------------------------------------------------------------------------------------------






    elif nav == "Dashboard":
       bauunternehmer_dashboard()
       st.set_page_config(page_title="Bauunternehmen App", layout="centered")


# === Seite: Budget-KI-Prognose ===    
    elif nav == "Budget-KI-Prognose":
        st.header("🤖 Budget-KI-Prognose")
        
        safe_secure_ki_prognose()
#---------------------------------------------------------------------------------------------------------------------------------------------------------------------    
    
    
    
    elif nav == "Projekt-Checklisten":
        st.header("Projekt-Checklisten verwalten")
        projekte = pd.read_sql("SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
        if projekte.empty:
            st.info("Noch keine Projekte vorhanden.")
        else:
            # Nur anzeigen, wenn KEIN Projekt zur Bearbeitung ausgewählt ist:
            if "checklisten_projekt_id" not in st.session_state:
                st.markdown("### Wähle ein Projekt:")
                for _, row in projekte.iterrows():
                    if st.button(row["name"], key=f"checkliste_{row['id']}"):
                        st.session_state["checklisten_projekt_id"] = row["id"]
                        st.session_state["checklisten_projekt_name"] = row["name"]
                        st.rerun()

            # Wenn ein Projekt ausgewählt wurde, nur die Checklisten-Bearbeitung und Zurück-Button anzeigen:
            if "checklisten_projekt_id" in st.session_state:
                # Spalte fortschritt_text in checklisten_allgemeinkommentar sicherstellen
                with engine.begin() as conn:
                    try:
                        conn.exec_driver_sql("ALTER TABLE checklisten_allgemeinkommentar ADD COLUMN fortschritt_text TEXT")
                    except Exception:
                        pass  # Column already exists
                pid = st.session_state["checklisten_projekt_id"]
                pname = st.session_state["checklisten_projekt_name"]
                st.markdown(f"## Checkliste für Projekt: **{pname}**")

                
                # Formular für neuen Checklistenpunkt
                with st.form(f"checkliste_hinzufuegen_{pid}"):
                    neuer_punkt = st.text_input("Neuer Checklistenpunkt")
                    hinzufuegen = st.form_submit_button("+ Hinzufügen")
                    if hinzufuegen and neuer_punkt:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO checklistenpunkte (projekt_id, text, erledigt, benutzername)
                                    VALUES (:projekt_id, :text, 0, :benutzername)
                                """), {
                                    "projekt_id": pid,
                                    "text": neuer_punkt,
                                    "benutzername": st.session_state.user
                                })
                        except Exception as e:
                            if "benutzername" in str(e).lower() or "undefinedcolumn" in str(e).lower():
                                # Spalte hinzufügen
                                try:
                                    with engine.begin() as conn:
                                        conn.exec_driver_sql("ALTER TABLE checklistenpunkte ADD COLUMN benutzername TEXT")
                                except:
                                    pass
                                # Warte kurz
                                import time
                                time.sleep(0.5)
                                # Versuche erneut
                                with engine.begin() as conn:
                                    conn.execute(text("""
                                        INSERT INTO checklistenpunkte (projekt_id, text, erledigt, benutzername)
                                        VALUES (:projekt_id, :text, 0, :benutzername)
                                    """), {
                                        "projekt_id": pid,
                                        "text": neuer_punkt,
                                        "benutzername": st.session_state.user
                                    })
                            else:
                                raise
                        st.rerun()

                # Checklistenpunkte anzeigen und löschen
                checklist_df = pd.read_sql(
                    "SELECT id, text, kommentar FROM checklistenpunkte WHERE projekt_id = %s ORDER BY id",
                    engine, params=(pid,)
                )
                for idx, row in checklist_df.iterrows():
                        col1, col2 = st.columns([8, 1])
                        col1.write(row["text"])
                        if col2.button("🗑️", key=f"del_{row['id']}"):
                            with engine.begin() as conn:
                                conn.execute(text("DELETE FROM checklistenpunkte WHERE id = :id"), {"id": row["id"]})
                            st.rerun()
                if st.button("← Zurück zur Projektliste"):
                    del st.session_state["checklisten_projekt_id"]
                    del st.session_state["checklisten_projekt_name"]
                    st.rerun()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------    
    
    
    
    
    
    
    
    
    
    elif nav == "Fortschritt":
        st.header("Projektfortschritt")
        projekte = pd.read_sql("SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
        if projekte.empty:
            st.info("Noch keine Projekte vorhanden.")
        else:
            for _, projekt in projekte.iterrows():
                checklist_df = pd.read_sql(
                    "SELECT id, text, erledigt FROM checklistenpunkte WHERE projekt_id = %s ORDER BY id",
                    engine, params=(projekt["id"],)
                )
                total = len(checklist_df)
                erledigt = checklist_df["erledigt"].sum() if total > 0 else 0
                fortschritt = int(erledigt / total * 100) if total > 0 else 0

                with st.expander(f"{projekt['name']} ({fortschritt}%)", expanded=False):
                    st.progress(fortschritt / 100)
                    st.markdown(f"**{fortschritt}% der Checkliste erledigt**")
                    if checklist_df.empty:
                        st.info("Für dieses Projekt wurde noch keine Checkliste angelegt.")
                    else:
                        for idx, row in checklist_df.iterrows():
                            checked = "✅" if row["erledigt"] else "⬜"
                            st.markdown(f"{checked} {row['text']}")


                    # Zeige ausschließlich den Kommentar aus checklisten_gesamtkommentar und Zeitaufwand
                    kommentare = pd.read_sql(
                        "SELECT benutzername, kommentar, zeitaufwand, datum FROM checklisten_gesamtkommentar WHERE projekt_id = %s",
                        engine, params=(projekt["id"],)
                    )
                    if not kommentare.empty:
                        kommentare = kommentare.sort_values(["benutzername", "datum"], ascending=[True, False])
                        kommentare = kommentare.drop_duplicates(subset=["benutzername"], keep="first")
                    mitarbeiter_df = pd.read_sql("""
                        SELECT m.benutzername, m.vorname, m.nachname 
                        FROM mitarbeiter m
                        JOIN mitarbeiter_projekte mp ON m.benutzername = mp.mitarbeiter_benutzername
                        WHERE mp.projekt_id = %s
                    """, engine, params=(projekt["id"],))
                    name_map = mitarbeiter_df.set_index("benutzername").apply(lambda x: f"{x['vorname']} {x['nachname']}", axis=1).to_dict()
                    st.markdown("**Kommentare & Zeitaufwand der Mitarbeiter:**")
                    max_width = 60
                    daten_vorhanden = False
                    for _, mitarbeiter in mitarbeiter_df.iterrows():
                        eintrag = kommentare[kommentare["benutzername"] == mitarbeiter["benutzername"]]
                        if not eintrag.empty:
                            daten_vorhanden = True
                            break
                    if not daten_vorhanden:
                        st.warning("Keine Daten von den Mitarbeitern eingetragen.")
                    else:
                        for _, mitarbeiter in mitarbeiter_df.iterrows():
                            voller_name = f"{mitarbeiter['vorname']} {mitarbeiter['nachname']}".strip()
                            eintrag = kommentare[kommentare["benutzername"] == mitarbeiter["benutzername"]]
                            kommentar = eintrag["kommentar"].iloc[0] if not eintrag.empty else "–"
                            zeit = eintrag["zeitaufwand"].iloc[0] if not eintrag.empty else "–"
                            datum = eintrag["datum"].iloc[0] if not eintrag.empty else "–"
                            wrapped = textwrap.fill(kommentar if kommentar else "–", width=max_width)
                            st.markdown(f"- {voller_name} ({datum}): {wrapped}")
                            st.markdown(f"  - Benötigte Zeit: {zeit if zeit else '–'} min.")

                    # Spalte fortschritt_text in checklisten_allgemeinkommentar sicherstellen
                    with engine.begin() as conn:
                        try:
                            conn.exec_driver_sql("ALTER TABLE checklisten_allgemeinkommentar ADD COLUMN fortschritt_text TEXT")
                        except Exception:
                            pass  # Column already exists
                    # Separater Block für Fortschritt-Text aus checklisten_allgemeinkommentar
                    allg_row = pd.read_sql(
                        "SELECT fortschritt_text FROM checklisten_allgemeinkommentar WHERE projekt_id = %s",
                        engine, params=(projekt["id"],)
                    )
                    if not allg_row.empty and allg_row["fortschritt_text"].iloc[0].strip():
                        st.markdown("**Fortschritt-Text zur Checkliste:**")
                        st.info(allg_row["fortschritt_text"].iloc[0])
                                    # == Fortschritts-PDF erstellen ==
                    st.subheader("Fortschrittsbericht als PDF exportieren")
                    heute = date.today().strftime("%Y-%m-%d")
                    if st.button("Bericht als PDF erstellen", key=f"pdf_{projekt['id']}"):
                        # Überprüfe: Existiert bereits ein PDF für heute?
                        now = datetime.now().time()
                        is_late_window = now >= datetime_time(23, 50)  # Zwischen 23:50 und Mitternacht
                        
                        # Versuche PDF zu laden (außer wenn zwischen 23:50-Mitternacht)
                        if not is_late_window:
                            existing_pdf = load_pdf_from_archive(st.session_state.user, projekt["id"], heute)
                            if existing_pdf:
                                st.success("PDF von heute gefunden - lädt...")
                                st.download_button(
                                    "📥 PDF herunterladen (gespeichert)",
                                    existing_pdf,
                                    file_name="fortschrittsbericht.pdf",
                                    mime="application/pdf"
                                )
                                st.stop()
                        
                        # PDF existiert nicht oder ist Late-Window: Generiere neu
                        buffer = BytesIO()
                        c = canvas.Canvas(buffer, pagesize=A4)
                        c.setFont("Helvetica", 20)
                        y = 800
                        # Kopfzeile
                        firmenname = st.session_state.get("firmenname","")
                        c.line(40, y, 550, y)
                        c.setDash()  # Dash zurücksetzen
                        y -= 20
                        c.setFont("Helvetica", 10)
                        c.drawString(50, y, f"Datum: {date.today().strftime('%d.%m.%Y')}")
                        y -= 30

                        # Wetterdaten für das Projekt und den Tag laden
                        wetter_row = pd.read_sql(
                            "SELECT * FROM wetterdaten WHERE projekt_id = %s AND datum = %s",
                            engine, params=(projekt["id"], heute)
                        )

                        # Dünne Linie oben
                        c.setLineWidth(1)
                        c.setDash()
                        c.line(40, y, 550, y)
                        y -= 20

                        if not wetter_row.empty:
                            wetter1 = wetter_row["wetter1"].iloc[0]
                            wetter2 = wetter_row["wetter2"].iloc[0]
                            boden1 = wetter_row["boden1"].iloc[0]
                            boden2 = wetter_row["boden2"].iloc[0]
                            temperatur = wetter_row["temperatur"].iloc[0]
                            schlecht = wetter_row["schlecht"].iloc[0]

                            # Wetter-Überschrift
                            # Zeile 1: Wetter nebeneinander
                            c.setFont("Helvetica-Bold", 10)
                            c.drawString(50, y, "Wetter:")
                            c.setFont("Helvetica", 10)
                            c.drawString(170, y, str(wetter1))
                            c.drawString(300, y, str(wetter2))
                            c.setFont("Helvetica-Bold", 10)
                            c.drawString(390, y, "Temperatur:")
                            c.setFont("Helvetica", 10)
                            c.drawString(490, y, f"{temperatur} °C")
                            y -= 20
                            # Dünne Linie mitte
                            c.setLineWidth(1)
                            c.setDash()
                            c.line(40, y, 550, y)
                            y -= 20
                            # Bodenverhältnisse-Überschrift
                            c.setFont("Helvetica-Bold", 10)
                            c.drawString(50, y, "Bodenverhältnisse:")
                            c.setFont("Helvetica", 10)
                            c.drawString(170, y, str(boden1))
                            c.drawString(300, y, str(boden2))
                            y-= 20
                            # Dünne Linie mitte 2
                            c.setLineWidth(1)
                            c.setDash()
                            c.line(40, y, 550, y)
                            y -= 20
                            # Schlechtes Wetter
                            c.setFont("Helvetica-Bold", 10)
                            c.drawString(50, y, "Schlechtes Wetter:")
                            c.setFont("Helvetica", 10)
                            c.drawString(170, y, "Ja" if schlecht else "Nein")
                            y -= 20
                        # Dünne Linie mitte 3
                        c.setLineWidth(1)
                        c.setDash()
                        c.line(40, y, 550, y)
                        y -= 20
                        # Anzahl der Arbeitskräfte am Berichtstag
                        arbeitskraefte_df = pd.read_sql(
                            "SELECT COUNT(DISTINCT benutzername) AS anzahl FROM arbeitszeiten WHERE projekt_id = %s AND datum = %s",
                            engine, params=(projekt["id"], heute)
                        )
                        anzahl_arbeitskraefte = arbeitskraefte_df["anzahl"].iloc[0] if not arbeitskraefte_df.empty else 0

                        c.setFont("Helvetica-Bold", 10)
                        c.drawString(50, y, "Anzahl AK:")
                        c.setFont("Helvetica", 10)
                        c.drawString(170, y, str(anzahl_arbeitskraefte))
                        y -= 20
                        # Dünne Linie unten
                        c.setLineWidth(1)
                        c.setDash()
                        c.line(40, y, 550, y)
                        y -= 20
                        df = pd.read_sql(
                            "SELECT * FROM checklistenpunkte WHERE projekt_id = %s AND erledigt = 1 AND erledigt_am = %s ORDER BY id",
                            engine, params=(projekt["id"],heute)
                        )

                        if df.empty:
                            st.warning("Es wurden noch keine Fortschrittsdaten erfasst.")

                        c.setFont("Helvetica-Bold", 10)    
                        c.drawString(50, y, "Ausgeführte Arbeiten:")
                        c.setFont("Helvetica", 10)
                        y -= 20
                        # 1. Erledigte Checklistenpunkte
                        for _, row in df.iterrows():
                            erledigt = "-" if row["erledigt"] else "X"
                            c.drawString(60, y, f"{erledigt} {row['text']}")
                            y -= 15
                            if row.get("kommentar") and row["kommentar"].strip():
                                c.drawString(80, y, f"Kommentar Fortschritt: {row['kommentar']}")
                                y -= 15
                            if y < 100:
                                c.showPage()
                                y = 800
                        # 2. Mitarbeiter-Kommentar aus checklisten_fortschrittkommentar als erledigter Punkt
                        fortschrittkommentar_row = pd.read_sql(
                            "SELECT kommentar FROM checklisten_fortschrittkommentar WHERE projekt_id = %s AND datum = %s",
                            engine, params=(projekt["id"], heute)
                        )
                        if not fortschrittkommentar_row.empty:
                            mitarbeiter_kommentar = fortschrittkommentar_row["kommentar"].iloc[0]
                            if mitarbeiter_kommentar.strip():
                                c.drawString(60, y, f"- {mitarbeiter_kommentar} ")
                                y -= 15
                                if y < 100:
                                    c.showPage()
                                    y = 800
                        y -= 20 
                        # Probleme & Zeitaufwand aus checklisten_gesamtkommentar laden
                        heute = date.today().strftime("%Y-%m-%d")
                        problem_row = pd.read_sql(
                            "SELECT kommentar, zeitaufwand FROM checklisten_gesamtkommentar WHERE projekt_id = %s AND datum = %s",
                            engine, params=(projekt["id"], heute)
                        )
                        
                        # Mitarbeiterstunden (linke Seite) - ALLE Mitarbeiter des Projekts mit ihrer Arbeitszeit heute
                        mitarbeiter_df = pd.read_sql(
                            """
                            SELECT m.benutzername, m.rolle, COALESCE(SUM(a.stunden), 0) as stunden
                            FROM mitarbeiter m
                            INNER JOIN mitarbeiter_projekte mp ON m.benutzername = mp.mitarbeiter_benutzername
                            LEFT JOIN arbeitszeiten a
                                ON m.benutzername = a.benutzername AND a.projekt_id = mp.projekt_id AND a.datum = %s
                            WHERE mp.projekt_id = %s
                            GROUP BY m.benutzername, m.rolle
                            """,
                            engine, params=(heute, projekt["id"])
                        )

                        # Geräte-Nutzungen (rechte Seite) - DIREKT AUS DATENBANK wie Arbeitszeiten!
                        geraete_nutzung_df = pd.read_sql(
                            """
                            SELECT geraet, nutzungszeit
                            FROM geraete_nutzung
                            WHERE projekt_id = %s AND datum = %s
                            """,
                            engine, params=(projekt["id"], heute)
                        )
                        
                        # Materialverbrauch für HEUTE - DIREKT AUS DATENBANK mit DATUM!
                        try:
                            # Stelle sicher dass datum Spalte existiert
                            with engine.begin() as conn:
                                try:
                                    conn.exec_driver_sql("ALTER TABLE materialien ADD COLUMN IF NOT EXISTS datum DATE")
                                except:
                                    pass
                            # Abfrage mit datum
                            material_df = pd.read_sql(
                                """
                                SELECT material, menge, einheit
                                FROM materialien
                                WHERE projekt_id = %s AND datum = %s
                                """,
                                engine, params=(projekt["id"], heute)
                            )
                        except Exception as e:
                            material_df = pd.DataFrame(columns=["material", "menge", "einheit"])
                        
                        # Probleme & Zeitaufwand anzeigen (falls vorhanden)
                        if not problem_row.empty:
                            max_pdf_width = 250  # ca. halbe A4-Seite in Punkten (ReportLab-Einheit)
                            left_margin = 60
                            c.setFont("Helvetica-Bold", 11)
                            c.drawString(left_margin, y, "Problem & Zeitaufwand:")
                            y -= 18
                            for _, row in problem_row.iterrows():
                                kommentar = row["kommentar"] or ""
                                zeit = row["zeitaufwand"] or ""
                                # Kommentar umbrechen (max. 50 Zeichen pro Zeile, keine Worttrennung)
                                wrapped_lines = textwrap.wrap(kommentar, width=50)
                                c.setFont("Helvetica", 10)
                                for i, line in enumerate(wrapped_lines):
                                    c.drawString(left_margin, y, line)
                                    y -= 20
                                c.setFont("Helvetica-Bold", 10)
                                c.drawString(left_margin, y, "Benötigte Zeit:")
                                text_width = c.stringWidth("Benötigte Zeit:", "Helvetica-Bold", 10)
                                c.setFont("Helvetica", 10)
                                c.drawString(left_margin + text_width + 10, y, str(zeit) + "  min.")
                                y -= 15
                                y -= 5  # Abstand zwischen mehreren Einträgen
                        
                        # Kommentare aus erledigten Checklistenpunkten
                        kommentarpunkte = [row["kommentar"] for _, row in df.iterrows() if row.get("kommentar") and row["kommentar"].strip()]
                        if kommentarpunkte:
                            c.setFont("Helvetica-Bold", 11)
                            c.drawString(60, y, "Kommentar Fortschritt:")
                            y -= 18
                            c.setFont("Helvetica", 10)
                            for punkt in kommentarpunkte:
                                wrapped_lines = textwrap.wrap(punkt, width=50)
                                for line in wrapped_lines:
                                    c.drawString(80, y, f"- {line}")
                                    y -= 15
                                    if y < 100:
                                        c.showPage()
                                        y = 800
                            y -= 10
                        
                        # Tabellen nebeneinander auf gleicher Höhe (IMMER anzeigen)
                        y_tabellen = y  # Startposition für beide Tabellen
                        x_mitarbeiter = 40
                        x_geraete = 320

                        # --- Mitarbeiterstunden-Tabelle ---
                        c.setLineWidth(1)
                        c.setDash()
                        c.line(x_mitarbeiter, y_tabellen, x_mitarbeiter + 255, y_tabellen)
                        y_mitarbeiter = y_tabellen - 18
                        c.setFont("Helvetica-Bold", 10)
                        c.drawString(x_mitarbeiter + 10, y_mitarbeiter, "Mitarbeiter")
                        c.drawString(x_mitarbeiter + 205, y_mitarbeiter, "Stunden")
                        y_mitarbeiter -= 10
                        c.setLineWidth(1)
                        c.setDash()
                        c.line(x_mitarbeiter, y_mitarbeiter, x_mitarbeiter + 255, y_mitarbeiter)
                        y_mitarbeiter -= 20
                        c.setFont("Helvetica", 10)
                        # name_map für volle Namen definieren
                        mitarbeiter_namen_df = pd.read_sql("SELECT benutzername, vorname, nachname FROM mitarbeiter", engine)
                        name_map = mitarbeiter_namen_df.set_index("benutzername").apply(lambda x: f"{x['vorname']} {x['nachname']}", axis=1).to_dict()
                        for _, row in mitarbeiter_df.iterrows():
                            voller_name = name_map.get(row["benutzername"], row["benutzername"])
                            rolle = row["rolle"] or "-"
                            stunden = f"{row['stunden']:.2f}"
                            c.drawString(x_mitarbeiter + 10, y_mitarbeiter, f"{voller_name} ({rolle})")
                            c.drawString(x_mitarbeiter + 225, y_mitarbeiter, f"{stunden}")
                            y_mitarbeiter -= 15
                        y_mitarbeiter -= 5

                        # --- Geräte-Nutzungen-Tabelle ---
                        c.setLineWidth(1)
                        c.setDash()
                        c.line(x_geraete, y_tabellen, x_geraete + 255, y_tabellen)
                        y_geraete = y_tabellen - 18
                        c.setFont("Helvetica-Bold", 10)
                        c.drawString(x_geraete + 10, y_geraete, "Geräte")
                        c.drawString(x_geraete + 205, y_geraete, "Stunden")
                        y_geraete -= 10
                        c.setLineWidth(1)
                        c.setDash()
                        c.line(x_geraete, y_geraete, x_geraete + 255, y_geraete)
                        y_geraete -= 20
                        c.setFont("Helvetica", 10)
                        for _, row in geraete_nutzung_df.iterrows():
                            try:
                                geraet = str(row["geraet"])
                                nutzungszeit = float(row["nutzungszeit"]) if pd.notnull(row["nutzungszeit"]) else 0.0
                                c.drawString(x_geraete + 10, y_geraete, f"{geraet}")
                                c.drawString(x_geraete + 225, y_geraete, f"{nutzungszeit:.2f}")
                                y_geraete -= 15
                            except Exception as e:
                                pass  # Zeile überspringen wenn Fehler
                        y_geraete -= 5

                        # --- Nach den Tabellen: y auf das tiefere Ende setzen ---
                        y = min(y_mitarbeiter, y_geraete)
                        
                        # Dünne Linie
                        c.setLineWidth(1)
                        c.setDash()
                        c.line(x_mitarbeiter, y, x_mitarbeiter + 255, y)
                        y_material = y - 18

                        # Überschrift
                        c.setFont("Helvetica-Bold", 10)
                        c.drawString(x_mitarbeiter + 10, y_material, "Material")
                        c.drawString(x_mitarbeiter + 210, y_material, "Menge")
                        y_material -= 10

                        # Dünne Linie
                        c.setLineWidth(1)
                        c.setDash()
                        c.line(x_mitarbeiter, y_material, x_mitarbeiter + 255, y_material)
                        y_material -= 20

                        c.setFont("Helvetica", 10)
                        for _, row in material_df.iterrows():
                            try:
                                material = str(row["material"])
                                menge = float(row["menge"]) if pd.notnull(row["menge"]) else 0.0
                                einheit = str(row["einheit"]) if "einheit" in row and pd.notnull(row["einheit"]) else ""
                                c.drawString(x_mitarbeiter + 10, y_material, f"{material}")
                                c.drawString(x_mitarbeiter + 180, y_material, f"{menge:.2f} {einheit}")
                                y_material -= 15
                            except Exception as e:
                                pass  # Zeile überspringen wenn Fehler

                        # y für weitere Blöcke aktualisieren
                        y = y_material
                        c.save()
                        buffer.seek(0)
                        
                        # Sammle alle Daten für Archive
                        wetter_text = ""
                        boden_text = ""
                        if not wetter_row.empty:
                            wetter_text = f"{wetter_row['wetter1'].iloc[0]}, {wetter_row['wetter2'].iloc[0]} | Temp: {wetter_row['temperatur'].iloc[0]}°C"
                            boden_text = f"{wetter_row['boden1'].iloc[0]}, {wetter_row['boden2'].iloc[0]}"
                        
                        # Mitarbeiter sammeln
                        mitarbeiter_text = ", ".join(mitarbeiter_df["benutzername"].tolist())
                        
                        # Material sammeln
                        material_text = ", ".join([f"{row['material']}: {row['menge']} {row['einheit']}" for _, row in material_df.iterrows() if row['material'] != "-"])
                        
                        # Geräte sammeln
                        geraete_text = ", ".join([f"{row['geraet']}: {row['nutzungszeit']}h" for _, row in geraete_nutzung_df.iterrows() if row['geraet'] != "-"])
                        
                        # Probleme sammeln
                        probleme_text = ""
                        if not problem_row.empty:
                            probleme_text = problem_row["kommentar"].iloc[0]
                        
                        # Speichere in bericht_daten_archive
                        success = save_bericht_daten_to_archive(
                            benutzername=st.session_state.user,
                            projekt_id=projekt["id"],
                            wetter=wetter_text,
                            boden=boden_text,
                            arbeitsbericht="",
                            mitarbeiter=mitarbeiter_text,
                            materialeinsatz=material_text,
                            geraeteeinsatz=geraete_text,
                            probleme=probleme_text,
                            todo="",
                            checklisten_data="",
                            erstellt_von_admin=0
                        )
                        
                        if success:
                            st.success("Bericht erfolgreich archiviert!")
                            # Verifiziere, dass die Daten wirklich gespeichert wurden
                            today = date.today().strftime("%Y-%m-%d")
                            verify_data = pd.read_sql(
                                "SELECT COUNT(*) as cnt FROM bericht_daten_archive WHERE benutzername = %s AND projekt_id = %s AND datum = %s",
                                engine,
                                params=(st.session_state.user, projekt["id"], today)
                            )
                            if verify_data["cnt"].iloc[0] > 0:
                                st.info(f" Daten bestätigt in Datenbank gespeichert")
                            else:
                                st.warning("Daten scheinen nicht gespeichert worden zu sein!")
                            
                            # Zeige Debug-Logs
                            if "archive_debug_logs" in st.session_state and st.session_state.archive_debug_logs:
                                with st.expander("🔍 DEBUG-Logs (Archivierung)"):
                                    st.code("\n".join(st.session_state.archive_debug_logs[-1:]), language="text")
                        else:
                            st.error("Fehler beim Archivieren des Berichts! Siehe Debug-Logs unten.")
                            
                            # Zeige Debug-Logs auch bei Fehler
                            if "archive_debug_logs" in st.session_state and st.session_state.archive_debug_logs:
                                with st.expander("🔍 DEBUG-Logs (Fehler-Details)", expanded=True):
                                    st.code("\n".join(st.session_state.archive_debug_logs[-1:]), language="text")
                        
                        # Speichere PDF in Datenbank BLOB (deprecated)
                        pdf_bytes = buffer.getvalue()
                        if save_pdf_to_archive(st.session_state.user, projekt["id"], pdf_bytes):
                            st.info("📥 PDF ebenfalls als Backup gespeichert")
                        
                        buffer.seek(0)
                        st.download_button("📥 PDF herunterladen", buffer, file_name="fortschrittsbericht.pdf", mime="application/pdf")
                        st.rerun()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------    
    
    
    
    
    
    
    
    
    
    elif nav == "Mitarbeiterprojekt":
        if "projekt_id" in st.session_state:
            projekt_id = st.session_state["projekt_id"]
            df = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(projekt_id,))
            heute = date.today().strftime("%Y-%m-%d")
            # --- Geräteverbrauch-Reset (korrekt, wie bisher) ---
            if st.session_state.get("geraete_eingabe_datum") != heute:
                st.session_state.geraete_expander_unten = False
                st.session_state.geraete_eingabe_gespeichert = []
                st.session_state.geraetezeilen = [{"geraet": "-", "anzahl": 1, "nutzungszeit": 0.0}]
                st.session_state.geraete_eingabe_datum = heute
                st.session_state.geraete_reset_done = False
                st.rerun()
            st.session_state.geraete_reset_done = True
            # --- Materialverbrauch-Reset: Nur Expander um Mitternacht zurücksetzen, keine Daten löschen! ---
            if st.session_state.get("material_eingabe_datum") != heute:
                st.session_state.material_expander_unten = False
                st.session_state.material_eingabe_datum = heute
                st.rerun()
            if not df.empty:
                col_head, col_btn, col_bt = st.columns([6, 2, 2])
                with col_head:
                    st.header(f"Projekt: {df['name'].iloc[0]}")
                with col_btn:
                    if st.button("Vorplanungs-Kalender"):
                        st.session_state.page = "vorplanung"
                        st.rerun()              
                with col_bt:
                    if st.button("Material-Planung"):
                        st.session_state.page = "materialplanung"
                        st.rerun()
                st.subheader("Projekt-Checkliste")
                with st.expander("🔽 Checkliste bearbeiten"):
                    # Checklistenpunkte laden
                    checklist_df = pd.read_sql(
                        "SELECT id, text, kommentar, erledigt FROM checklistenpunkte WHERE projekt_id = %s ORDER BY id",
                        engine, params=(projekt_id,)
                    )

                    if checklist_df.empty:
                        st.info("Für dieses Projekt wurde noch keine Checkliste angelegt.")
                    else:
                        # Fortschrittspunkte: Abhakbar, Kommentarspalte darunter mit Speicher-Button
                        for idx, row in checklist_df.iterrows():
                            if row["text"]:
                                col1, col2, col3 = st.columns([8, 2, 2])
                                col1.write(row["text"])
                                erledigt = bool(row["erledigt"])
                                checked = col2.checkbox("Abgehakt", value=erledigt, key=f"erledigt_{row['id']}")
                                if col3.button("💾", key=f"save_erledigt_{row['id']}"):
                                    erledigt_am = date.today().strftime("%Y-%m-%d") if checked else None
                                    with engine.begin() as conn:
                                        conn.execute(
                                            text("""
                                                UPDATE checklistenpunkte SET erledigt = :erledigt, erledigt_am = :erledigt_am WHERE id = :id
                                            """),
                                            {"erledigt": int(checked), "erledigt_am": erledigt_am, "id": row["id"]}
                                        )
                                    st.success("Fortschritt gespeichert.")
                                    st.rerun()
                        # Zeile hinzufügen-Button wieder am Ende
                        # Separates Textfeld für Checklisten-Kommentar des Mitarbeiters
                        with engine.begin() as conn:
                            conn.exec_driver_sql("""
                                CREATE TABLE IF NOT EXISTS checklisten_fortschrittkommentar (
                                    projekt_id INTEGER,
                                    benutzername TEXT,
                                    kommentar TEXT,
                                    datum TEXT,
                                    PRIMARY KEY (projekt_id, benutzername, datum)
                                )
                            """)
                        fortschritt_kommentar_key = f"fortschritt_kommentar_{projekt_id}"
                        fortschritt_kommentar = st.text_area("zusätzlicher Fortschritt", value=st.session_state.get(fortschritt_kommentar_key, ""), key=fortschritt_kommentar_key, height=40)
                        if st.button("Fortschritt speichern", key="save_fortschritt_kommentar"):
                            # Spalte hinzufügen in separater Transaktion (falls sie nicht existiert)
                            try:
                                with engine.begin() as conn:
                                    conn.exec_driver_sql("ALTER TABLE checklisten_fortschrittkommentar ADD COLUMN benutzername TEXT")
                            except:
                                pass
                            # DELETE und dann INSERT statt ON CONFLICT (da Primary Key möglicherweise nicht gültig ist)
                            with engine.begin() as conn:
                                # Zuerst alten Eintrag löschen
                                conn.execute(
                                    text("""
                                        DELETE FROM checklisten_fortschrittkommentar 
                                        WHERE projekt_id = :projekt_id 
                                        AND benutzername = :benutzername 
                                        AND datum = :datum
                                    """),
                                    {
                                        "projekt_id": projekt_id,
                                        "benutzername": st.session_state.user,
                                        "datum": date.today().strftime("%Y-%m-%d")
                                    }
                                )
                                # Dann neuen Eintrag einfügen
                                conn.execute(
                                    text("""
                                        INSERT INTO checklisten_fortschrittkommentar (projekt_id, benutzername, kommentar, datum)
                                        VALUES (:projekt_id, :benutzername, :kommentar, :datum)
                                    """),
                                    {
                                        "projekt_id": projekt_id,
                                        "benutzername": st.session_state.user,
                                        "kommentar": fortschritt_kommentar,
                                        "datum": date.today().strftime("%Y-%m-%d")
                                    }
                                )
                            st.success("Fortschritt-Kommentar gespeichert.")
                            st.rerun()                     
                        # Button entfernt: Kommentare werden nicht als eigene Checklistenpunkte gespeichert
                    # Wetter- und Bodenverhältnisse (je 2 Felder)
                    # Wetter- und Bodenverhältnisse (je 2 Felder nebeneinander, keine Dopplung möglich)
                heute = date.today().strftime("%Y-%m-%d")
                try:
                    wetter_row = pd.read_sql(
                        "SELECT * FROM wetterdaten WHERE projekt_id = %s AND datum = %s",
                        engine, params=(projekt_id, heute)
                    )
                except Exception:
                    # Tabelle existiert nicht, erstelle sie
                    with engine.begin() as conn:
                        conn.exec_driver_sql("""
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
                    wetter_row = pd.DataFrame()  # Leeres DataFrame
                
                wetter_gespeichert = not wetter_row.empty

                if not wetter_gespeichert:
                    st.subheader("🌤️ Wetter- und Bodenverhältnisse")
                    with st.expander("🌤️ Wetter- und Bodenverhältnisse eintragen"):
                        col_w1, col_w2 = st.columns(2)
                        with col_w1:
                            wetter1 = st.selectbox("Wetter", wetter_optionen, key="wetter1")
                        with col_w2:
                            wetter2 = st.selectbox(
                                "Wetter",
                                [opt for opt in wetter_optionen if opt != wetter1],
                                key="wetter2"
                            )
                        col_b1, col_b2 = st.columns(2)
                        with col_b1:
                            boden1 = st.selectbox("Bodenverhältnisse", boden_optionen, key="boden1")
                        with col_b2:
                            boden2 = st.selectbox(
                                "Bodenverhältnisse",
                                [opt for opt in boden_optionen if opt != boden1],
                                key="boden2"
                            )
                        col_temp, col_schlecht = st.columns([2, 1])
                        with col_temp:
                            temperatur = st.number_input("Temperatur (°C)", min_value=-30.0, max_value=50.0, step=1.0, key="temperatur")
                        with col_schlecht:
                            schlechtes_wetter = st.checkbox("Schlechtes Wetter", key="schlechtes_wetter")
                        if st.button("Wetterdaten speichern"):
                            with engine.begin() as conn:
                                conn.exec_driver_sql("""
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
                                conn.execute(
                                    text("""
                                        INSERT INTO wetterdaten (projekt_id, datum, wetter1, wetter2, boden1, boden2, temperatur, schlecht)
                                        VALUES (:projekt_id, :datum, :wetter1, :wetter2, :boden1, :boden2, :temperatur, :schlecht)
                                        ON CONFLICT(projekt_id, datum) DO UPDATE SET
                                            wetter1=excluded.wetter1,
                                            wetter2=excluded.wetter2,
                                            boden1=excluded.boden1,
                                            boden2=excluded.boden2,
                                            temperatur=excluded.temperatur,
                                            schlecht=excluded.schlecht
                                    """),
                                    {
                                        "projekt_id": projekt_id,
                                        "datum": heute,
                                        "wetter1": wetter1,
                                        "wetter2": wetter2,
                                        "boden1": boden1,
                                        "boden2": boden2,
                                        "temperatur": temperatur,
                                        "schlecht": int(schlechtes_wetter)
                                    }
                                )
                            st.success("Wetterdaten gespeichert.")
                            st.rerun()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------









                   # Geräte-Liste aus dem Lager des Chefs laden
                chef_row = pd.read_sql(
                    "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
                )
                chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
                df_geraete = pd.read_sql(
                    "SELECT geraet, anzahl FROM geraete_lager WHERE benutzername = %s", engine, params=(chefname,)
                )
                geraete_liste = df_geraete["geraet"].tolist()
                geraete_anzahl_dict = dict(zip(df_geraete["geraet"], df_geraete["anzahl"]))

                # Session-State initialisieren
                if "geraete_expander_unten" not in st.session_state:
                    st.session_state.geraete_expander_unten = False
                # Expander oben (Eingabe)
                if not st.session_state.geraete_expander_unten:
                    st.subheader("Geräteverwaltung")
                    if "geraetezeilen" not in st.session_state or not st.session_state.geraetezeilen:
                        st.session_state.geraetezeilen = [{"geraet": "-", "anzahl": 1, "nutzungszeit": 0.0}]
                    with st.expander("Geräte-Verwaltung"):
                        if st.button("+ Neue Gerätezeile hinzufügen", key="add_geraetezeile"):
                            st.session_state.geraetezeilen.append({"geraet": "-", "anzahl": 1, "nutzungszeit": 0.0})
                        to_delete = []
                        for idx, zeile in enumerate(st.session_state.geraetezeilen):
                            cols = st.columns([4, 2, 2, 1])
                            # Gerät auswählen
                            geraet = cols[0].selectbox(
                                "Gerät",
                                ["-"] + geraete_liste,
                                index=(["-"] + geraete_liste).index(zeile["geraet"]) if zeile["geraet"] in geraete_liste else 0,
                                key=f"geraet_select_{idx}"
                            )
                            st.session_state.geraetezeilen[idx]["geraet"] = geraet
                            # Anzahl
                            max_anzahl = int(geraete_anzahl_dict.get(geraet, 1))
                            anzahl = cols[1].number_input(
                                "Anzahl",
                                min_value=1,
                                max_value=max_anzahl,
                                step=1,
                                value=zeile["anzahl"],
                                key=f"anzahl_input_{idx}"
                            )
                            st.session_state.geraetezeilen[idx]["anzahl"] = anzahl
                            # Nutzungszeit
                            nutzungszeit = cols[2].text_input(
                           "Nutzungszeit in h",
                            value=float(zeile["nutzungszeit"]),
                            key=f"nutzungszeit_input_{idx}"
                            )
                            st.session_state.geraetezeilen[idx]["nutzungszeit"] = nutzungszeit
                            # Löschen-Button
                            if cols[3].button("❌", key=f"delete_geraete_{idx}"):
                                to_delete.append(idx)
                        for idx in sorted(to_delete, reverse=True):
                            del st.session_state.geraetezeilen[idx]
                            st.rerun()
                        # Speichern
                        if st.button("Geräte für Projekt speichern", key="save_geraete"):
                            projekt_id = st.session_state.get("projekt_id")
                            heute = date.today().strftime("%Y-%m-%d")
                            with engine.begin() as conn:
                                for zeile in st.session_state.geraetezeilen:
                                    geraet = zeile["geraet"]
                                    anzahl = zeile["anzahl"]
                                    nutzungszeit = zeile["nutzungszeit"]
                                    try:
                                        nutzungszeit_float = float(nutzungszeit)
                                    except (ValueError, TypeError):
                                        nutzungszeit_float = 0.0

                                    if geraet != "-" and anzahl > 0 and nutzungszeit_float > 0:
                                        try:
                                            conn.exec_driver_sql("""
                                                DELETE FROM geraete_nutzung
                                                WHERE benutzername = %s AND projekt_id = %s AND geraet = %s AND datum = %s
                                            """, (st.session_state.user, projekt_id, geraet, heute))
                                            conn.exec_driver_sql("""
                                                INSERT INTO geraete_nutzung (benutzername, projekt_id, geraet, datum, nutzungszeit)
                                                VALUES (%s, %s, %s, %s, %s)
                                            """, (st.session_state.user, projekt_id, geraet, heute, nutzungszeit_float))
                                        except Exception as e:
                                            # Transaktion ist fehlgeschlagen, muss neue Transaktion starten
                                            # Spalte existiert nicht, füge sie in separater Transaktion hinzu
                                            try:
                                                with engine.begin() as new_conn:
                                                    new_conn.exec_driver_sql("ALTER TABLE geraete_nutzung ADD COLUMN benutzername TEXT")
                                            except Exception:
                                                pass
                                            # Versuche erneut zu inserieren in neuer Transaktion
                                            try:
                                                with engine.begin() as new_conn:
                                                    new_conn.exec_driver_sql("""
                                                        DELETE FROM geraete_nutzung
                                                        WHERE benutzername = %s AND projekt_id = %s AND geraet = %s AND datum = %s
                                                    """, (st.session_state.user, projekt_id, geraet, heute))
                                                    new_conn.exec_driver_sql("""
                                                        INSERT INTO geraete_nutzung (benutzername, projekt_id, geraet, datum, nutzungszeit)
                                                        VALUES (%s, %s, %s, %s, %s)
                                                    """, (st.session_state.user, projekt_id, geraet, heute, nutzungszeit_float))
                                            except Exception:
                                                st.error(f"Fehler beim Speichern von {geraet}: {str(e)[:100]}")
                            
                            # Eingabe merken und Expander nach unten verschieben
                            st.session_state.geraete_eingabe_gespeichert = [z.copy() for z in st.session_state.geraetezeilen]
                            st.session_state.geraete_eingabe_datum = heute
                            st.session_state.geraete_expander_unten = True
                            st.session_state.geraetezeilen = [{"geraet": "-", "anzahl": 1, "nutzungszeit": 0.0}]
                            st.success(f"Geräte gespeichert: {len(st.session_state.geraete_eingabe_gespeichert)} Einträge")
                            st.rerun()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------                
                
                
                

                if not st.session_state.get("material_expander_unten", False):    
                    st.subheader("🔩 Materialverwaltung")
                    with st.expander("Materialverwaltung für das Projekt"):
                        if "materialzeilen" not in st.session_state or not st.session_state.materialzeilen:
                            st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                        # Lagerdaten laden
                        chef_row = pd.read_sql(
                            "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
                        )
                        chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
                        df_lager = pd.read_sql(
                            "SELECT material, einheit FROM lagerbestand WHERE benutzername = %s",
                            engine, params=(chefname,)
                        )
                        lager_materialien = df_lager["material"].tolist()
                        einheiten_dict = df_lager.set_index("material")["einheit"].to_dict()
                        # --- Buttons oben: Zeile entfernen links, hinzufügen rechts ---
                        col_add, col_spacer, col_remove= st.columns([2, 6, 2])
                        with col_remove:
                            if st.button("- Zeile entfernen", key="remove_material_row") and len(st.session_state.materialzeilen) > 1:
                                st.session_state.materialzeilen.pop()
                                st.rerun()
                        with col_add:
                            if st.button("+ Zeile hinzufügen", key="add_material_row"):
                                st.session_state.materialzeilen.append({"material": "-", "menge": 0.0, "einheit": ""})
                                st.rerun()
                        # --- Materialauswahl und Eingabe ---
                        to_delete = []
                        for idx, zeile in enumerate(st.session_state.materialzeilen):
                            cols = st.columns([4, 2, 2, 1])
                            mat = cols[0].selectbox(
                                "Material",
                                ["-"] + lager_materialien,
                                index=(["-"] + lager_materialien).index(zeile["material"]) if zeile["material"] in lager_materialien else 0,
                                key=f"material_select_{idx}"
                            )
                            st.session_state.materialzeilen[idx]["material"] = mat
                            einheit = einheiten_dict.get(mat, "")
                            cols[1].write(f"Einheit: {einheit}")
                            menge = cols[2].number_input(
                                "Menge",
                                min_value=0.0,
                                step=1.0,
                                value=zeile["menge"],
                                key=f"menge_input_{idx}"
                            )
                            st.session_state.materialzeilen[idx]["menge"] = menge
                            st.session_state.materialzeilen[idx]["einheit"] = einheit
                        # Speichern-Button
                        if st.button("Materialien für Projekt speichern", key="save_materialien"):
                            projekt_id = st.session_state.get("projekt_id")
                            heute = date.today().strftime("%Y-%m-%d")
                            chef_row = pd.read_sql(
                                "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
                            )
                            chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
                            for zeile in st.session_state.materialzeilen:
                                mat = zeile["material"]
                                menge = zeile["menge"]
                                einheit = einheiten_dict.get(mat, "")
                                with engine.begin() as conn:
                                    try:
                                        conn.exec_driver_sql("ALTER TABLE materialien ADD COLUMN IF NOT EXISTS datum DATE")
                                    except:
                                        pass
                                    result = conn.exec_driver_sql("""
                                        SELECT menge, bearbeitet_von_bauunternehmer FROM materialien
                                        WHERE projekt_id = %s AND material = %s AND benutzername = %s AND datum = %s
                                    """, (projekt_id, mat, chefname, heute)).fetchone()
                                    if result:
                                        alte_menge, bearbeitet = result
                                        if bearbeitet == 1:
                                            pass
                                        else:
                                            neue_menge = float(alte_menge) + menge
                                            conn.exec_driver_sql("""
                                                UPDATE materialien SET menge = %s, einheit = %s, bearbeitet_von_bauunternehmer = 0, datum = %s
                                                WHERE projekt_id = %s AND material = %s AND benutzername = %s AND datum = %s
                                            """, (neue_menge, einheit, heute, projekt_id, mat, chefname, heute))
                                    else:
                                        conn.exec_driver_sql("""
                                            INSERT INTO materialien (projekt_id, material, menge, benutzername, einheit, bearbeitet_von_bauunternehmer, datum)
                                            VALUES (%s, %s, %s, %s, %s, 0, %s)
                                        """, (projekt_id, mat, menge, chefname, einheit, heute))
                            st.success("Materialien für das Projekt wurden gespeichert.")
                            st.session_state.material_eingabe_gespeichert = [z.copy() for z in st.session_state.materialzeilen]
                            st.session_state.material_eingabe_datum = heute
                            st.session_state.material_expander_unten = True
                            st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                            st.success(f"Materialien gespeichert: {len(st.session_state.material_eingabe_gespeichert)} Einträge")
                            st.rerun()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------                
                
                
                
                
                
                
                # Kommentar-Block ersetzen durch eigenen Expander für "Problem"
                st.subheader("Probleme & zusätzlicher Zeitaufwand")
                with st.expander("Problem melden / dokumentieren"):
                    # Robust: projekt_id IMMER als Integer setzen
                    projekt_id_int = int(st.session_state.get("projekt_id", projekt_id))
                    benutzername = str(st.session_state.user)
                    heute = date.today().strftime("%Y-%m-%d")
                    with engine.begin() as conn:
                        try:
                            conn.exec_driver_sql("ALTER TABLE checklisten_gesamtkommentar ADD COLUMN zeitaufwand TEXT")
                        except:
                            pass
                    # Problemtext laden (nur für heute!)
                    problem_row = pd.read_sql(
                        "SELECT kommentar, zeitaufwand FROM checklisten_gesamtkommentar WHERE projekt_id = %s AND benutzername = %s AND datum = %s",
                        engine, params=(projekt_id_int, benutzername, heute)
                    )
                    problem_text = problem_row["kommentar"].iloc[0] if not problem_row.empty else ""
                    zeitaufwand = problem_row["zeitaufwand"].iloc[0] if ("zeitaufwand" in problem_row.columns and not problem_row.empty) else ""

                    neuer_problemtext = st.text_area("Problembeschreibung", value=problem_text, height=150, key="problem_text")
                    neue_zeit = st.text_input("Benötigte Zeit (in min.)", value=zeitaufwand, key="problem_zeit")

                    if st.button("Problem speichern"):
                        # Spalte hinzufügen in separater Transaktion
                        try:
                            with engine.begin() as conn:
                                conn.exec_driver_sql("ALTER TABLE checklisten_gesamtkommentar ADD COLUMN zeitaufwand TEXT")
                        except:
                            pass
                        # DELETE und dann INSERT statt ON CONFLICT (da kein UNIQUE Constraint)
                        with engine.begin() as conn:
                            # Zuerst alten Eintrag löschen
                            conn.execute(
                                text("""
                                    DELETE FROM checklisten_gesamtkommentar 
                                    WHERE projekt_id = :projekt_id 
                                    AND benutzername = :benutzername 
                                    AND datum = :datum
                                """),
                                {
                                    "projekt_id": projekt_id_int,
                                    "benutzername": benutzername,
                                    "datum": heute
                                }
                            )
                            # Dann neuen Eintrag einfügen
                            conn.execute(
                                text("""
                                    INSERT INTO checklisten_gesamtkommentar (projekt_id, benutzername, kommentar, zeitaufwand, datum)
                                    VALUES (:projekt_id, :benutzername, :kommentar, :zeitaufwand, :datum)
                                """),
                                {
                                    "projekt_id": projekt_id_int,
                                    "benutzername": benutzername,
                                    "kommentar": neuer_problemtext,
                                    "zeitaufwand": neue_zeit,
                                    "datum": heute
                                }
                            )
                        st.success("Problem und Zeitaufwand gespeichert.")
                        st.rerun()
                # --- Arbeitszeit erfassen ---
                heute = date.today().strftime("%Y-%m-%d")
                arbeitszeit_row = pd.read_sql(
                    "SELECT * FROM arbeitszeiten WHERE benutzername = %s AND projekt_id = %s AND datum = %s",
                    engine, params=(st.session_state.user, projekt_id, heute)
                )
                arbeitszeit_gespeichert = not arbeitszeit_row.empty

                # Expander oben NUR anzeigen, wenn noch NICHT gespeichert!
                if not arbeitszeit_gespeichert:
                    st.subheader("🕒 Arbeitszeit erfassen")
                    with st.expander("+ Neue Zeiterfassung eintragen"):
                        with st.form(f"zeiterfassung_formular_{projekt_id}_{st.session_state.user}"):
                            datum = st.date_input("📅 Datum", value=date.today())
                            col1, col2, col3 = st.columns([2,2,2])
                            with col1:
                                von = st.time_input("⏱️ Von", value=datetime.strptime("08:00", "%H:%M").time())
                            with col2:
                                bis = st.time_input("⏱️ Bis", value=datetime.strptime("16:00", "%H:%M").time())
                            with col3:
                                krank = st.toggle("Krankmeldung", value=False, key="krankmeldung")
                            speichern = st.form_submit_button("Eintrag speichern")
                        if speichern:
                            if krank:
                                # Durchschnitt der letzten 91 Tage (nur Werte > 0)
                                df_91d = pd.read_sql(
                                    "SELECT stunden FROM arbeitszeiten WHERE benutzername = %s AND projekt_id = %s AND datum >= %s ORDER BY datum DESC",
                                    engine,
                                    params=(st.session_state.user, projekt_id, (date.today() - timedelta(days=91)).strftime('%Y-%m-%d'))
                                )
                                debug_stunden_liste_pos = [v for v in df_91d["stunden"].tolist() if v > 0]
                                if debug_stunden_liste_pos:
                                    stunden = sum(debug_stunden_liste_pos) / len(debug_stunden_liste_pos)
                                else:
                                    stunden = 0.0
                            else:
                                stunden = (datetime.combine(date.today(), bis) - datetime.combine(date.today(), von)).seconds / 3600
                                if stunden > 6: 
                                    stunden -= 0.5
                                if stunden > 8:
                                    stunden -= 0.25
                                if stunden > 10:
                                    st.warning("Arbeitszeit über 10 Stunden. Maximale Tagesarbeitszeit überschritten.")
                            with engine.begin() as conn:
                                try:
                                    conn.exec_driver_sql("""
                                        INSERT INTO arbeitszeiten (benutzername, projekt_id, datum, startzeit, endzeit, stunden)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                    """, (
                                        st.session_state.user,
                                        projekt_id,
                                        datum.strftime("%Y-%m-%d"),
                                        von.strftime("%H:%M"),
                                        bis.strftime("%H:%M"),
                                        stunden
                                    ))
                                except Exception as e:
                                    if "startzeit" in str(e).lower() or "endzeit" in str(e).lower() or "undefinedcolumn" in str(e).lower():
                                        # Spalten hinzufügen
                                        try:
                                            with engine.begin() as new_conn:
                                                new_conn.exec_driver_sql("ALTER TABLE arbeitszeiten ADD COLUMN startzeit TEXT")
                                        except:
                                            pass
                                        try:
                                            with engine.begin() as new_conn:
                                                new_conn.exec_driver_sql("ALTER TABLE arbeitszeiten ADD COLUMN endzeit TEXT")
                                        except:
                                            pass
                       
                                        # Versuche erneut
                                        with engine.begin() as new_conn:
                                            new_conn.exec_driver_sql("""
                                                INSERT INTO arbeitszeiten (benutzername, projekt_id, datum, startzeit, endzeit, stunden)
                                                VALUES (%s, %s, %s, %s, %s, %s)
                                            """, (
                                                st.session_state.user,
                                                projekt_id,
                                                datum.strftime("%Y-%m-%d"),
                                                von.strftime("%H:%M"),
                                                bis.strftime("%H:%M"),
                                                stunden
                                            ))
                                    else:
                                        raise
                            st.success("Arbeitszeit erfolgreich gespeichert.")
                            st.rerun()
                # --- Abgeschlossene Aufgaben ---
                st.markdown("### Abgeschlossene Aufgaben")
                with st.expander("Abgeschlossene Aufgaben anzeigen"):    
                    abgeschlossen_df = checklist_df[checklist_df["erledigt"] == 1]
                    if abgeschlossen_df.empty:
                        st.info("Noch keine Aufgaben abgeschlossen.")
                    else:
                        for _, row in abgeschlossen_df.iterrows():
                            st.markdown(f"- {row['text']}")
                st.markdown ("### Eingetragene Daten")
                if not wetter_gespeichert and not arbeitszeit_gespeichert and not st.session_state.get("geraete_eingabe_gespeichert") and not st.session_state.get("material_eingabe_gespeichert"):
                    st.info("Noch keine Daten für heute eingetragen.")
                # Nach abgeschlossenen Aufgaben, ganz unten im Layout:
                heute = date.today().strftime("%Y-%m-%d")
                wetter_row = pd.read_sql(
                    "SELECT * FROM wetterdaten WHERE projekt_id = %s AND datum = %s",
                    engine, params=(projekt_id, heute)
                )
                wetter_gespeichert = not wetter_row.empty

                    # Wetter-Expander unten NUR anzeigen, wenn Wetterdaten für heute existieren
                if wetter_gespeichert:
                        wetter_title = "Wetter- und Bodenverhältnisse eintragen"
                        with st.expander(wetter_title):
                            st.info("Wetterdaten für heute wurden bereits gespeichert.")
                            st.markdown(
                                "<style>.streamlit-expanderHeader {color: var(--text-color) !important;}</style>",
                                unsafe_allow_html=True
                            )
                            # Werte anzeigen
                            st.write(f"Wetter 1: {wetter_row['wetter1'].iloc[0]}")
                            st.write(f"Wetter 2: {wetter_row['wetter2'].iloc[0]}")
                            st.write(f"Boden 1: {wetter_row['boden1'].iloc[0]}")
                            st.write(f"Boden 2: {wetter_row['boden2'].iloc[0]}")
                            st.write(f"Temperatur: {wetter_row['temperatur'].iloc[0]} °C")
                            st.write(f"Schlechtes Wetter: {'Ja' if wetter_row['schlecht'].iloc[0] else 'Nein'}")
                            col1, col2 = st.columns([8, 2])
                            with col2:
                                if st.button("Wetterdaten überschreiben", key="wetter_edit"):
                                    with engine.begin() as conn:
                                        conn.execute(
                                            text("DELETE FROM wetterdaten WHERE projekt_id = :projekt_id AND datum = :datum"),
                                            {"projekt_id": projekt_id, "datum": heute}
                                        )
                                    st.rerun()
                heute = date.today().strftime("%Y-%m-%d")
                arbeitszeit_row = pd.read_sql(
                    "SELECT * FROM arbeitszeiten WHERE benutzername = %s AND projekt_id = %s AND datum = %s",
                    engine, params=(st.session_state.user, projekt_id, heute)
                )
                arbeitszeit_gespeichert = not arbeitszeit_row.empty

                arbeitszeit_title = "+ Neue Zeiterfassung eintragen"
                if arbeitszeit_gespeichert:
                    arbeitszeit_title += ""
                    with st.expander(arbeitszeit_title):
                        st.info("Arbeitszeit für heute wurde bereits gespeichert.")
                        st.markdown(
                            "<style>.streamlit-expanderHeader {color: var(--text-color) !important;}</style>",
                            unsafe_allow_html=True
                        )
                        # Werte anzeigen
                        row = arbeitszeit_row.iloc[0]
                        st.write(f"Von: {row['startzeit']} Uhr")
                        st.write(f"Bis: {row['endzeit']} Uhr")
                        st.write(f"Stunden: {row['stunden']:.2f}")
                        col1, col2 = st.columns([8, 2])
                        with col2:
                            if st.button("Zeiterfassung überschreiben", key="arbeitszeit_edit"):
                                with engine.begin() as conn:
                                    conn.execute(
                                        text("DELETE FROM arbeitszeiten WHERE benutzername = :benutzername AND projekt_id = :projekt_id AND datum = :datum"),
                                        {"benutzername": st.session_state.user, "projekt_id": projekt_id, "datum": heute}
                                    )
                                st.rerun()
                if st.session_state.geraete_expander_unten:
                    with st.expander("Geräteverwaltung für das Projekt", expanded=True):
                        eingabe = st.session_state.get("geraete_eingabe_gespeichert", [])
                        if not eingabe:
                            st.info("Keine Geräte-Eingabe für heute vorhanden.")
                        else:
                            st.info("Geräte wurden heute bereits eingegeben.")
                            for z in eingabe:
                                geraet = z.get("geraet", "-")
                                anzahl = z.get("anzahl", 0)
                                nutzungszeit = z.get("nutzungszeit", "")
                                # Versuche die Nutzungszeit als Zahl zu interpretieren, sonst als Text anzeigen
                                try:
                                    nutzungszeit_float = float(nutzungszeit)
                                except (ValueError, TypeError):
                                    nutzungszeit_float = None
                                # Zeige nur sinnvolle Einträge
                                if geraet != "-" and int(anzahl) > 0 and nutzungszeit:
                                    st.write(f"{geraet}: {anzahl} Stück, Nutzungszeit: {nutzungszeit} Std.")
                        if st.button("Eingabe bearbeiten", key="edit_geraete"):
                            # Geräte-Nutzungen für heute löschen
                            projekt_id = st.session_state.get("projekt_id")
                            heute = st.session_state.get("geraete_eingabe_datum", date.today().strftime("%Y-%m-%d"))
                            with engine.begin() as conn:
                                for zeile in eingabe:
                                    geraet = zeile.get("geraet", "-")
                                    if geraet != "-":
                                        conn.exec_driver_sql("""
                                            DELETE FROM geraete_nutzung WHERE benutzername = %s AND projekt_id = %s AND geraet = %s AND datum = %s
                                        """, (st.session_state.user, projekt_id, geraet, heute))
                            st.session_state.geraete_expander_unten = False
                            st.session_state.geraetezeilen = eingabe.copy()
                            st.session_state.geraete_eingabe_gespeichert = []
                            st.rerun()
                if st.session_state.get("material_expander_unten", False):
                    # Prüfe, ob die gespeicherten Werte nur '-' und 0.0 sind (Mitternachts-Reset)
                    eingabe = st.session_state.get("material_eingabe_gespeichert", [])
                    mitternacht_reset = (
                        eingabe and all(z.get("material") == "-" and z.get("menge") == 0.0 for z in eingabe)
                    )
                    # Nur zurücksetzen, wenn Expander noch unten ist und Mitternachtsreset erkannt wird
                    if mitternacht_reset and st.session_state.material_expander_unten:
                        st.session_state.material_expander_unten = False
                        st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                        st.session_state.material_eingabe_gespeichert = []
                        st.rerun()
                    else:
                        with st.expander("Materialverwaltung für das Projekt", expanded=True):
                            if not eingabe:
                                st.info("Keine Eingabe für heute vorhanden.")
                            else:
                                st.info("Material wurde heute bereits eingegeben.")
                                for zeile in eingabe:
                                    mat = zeile["material"]
                                    menge = zeile["menge"]
                                    einheit = ""
                                    if "einheiten_dict" in locals():
                                        einheit = einheiten_dict.get(mat, "")
                                    else:
                                        # Fallback: Einheit aus DB holen
                                        df_lager = pd.read_sql(
                                            "SELECT einheit FROM lagerbestand WHERE material = %s",
                                            engine, params=(mat,)
                                        )
                                        einheit = df_lager["einheit"].iloc[0] if not df_lager.empty else ""
                                    st.write(f"{mat}: {menge} {einheit}")
                            if st.button("Eingabe bearbeiten", key="edit_materialien"):
                                # Manuelles Zurücksetzen: Einträge von HEUTE aus materialien löschen
                                projekt_id = st.session_state.get("projekt_id")
                                heute = st.session_state.get("material_eingabe_datum", date.today().strftime("%Y-%m-%d"))
                                chef_row = pd.read_sql(
                                    "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
                                )
                                chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
                                try:
                                    with engine.begin() as conn:
                                        # DELETE heutige Einträge aus materialien (wo datum = heute)
                                        conn.exec_driver_sql(
                                            "DELETE FROM materialien WHERE projekt_id = %s AND benutzername = %s AND datum = %s",
                                            (projekt_id, chefname, heute)
                                        )
                                    st.session_state.material_expander_unten = False
                                    st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                                    st.session_state.material_eingabe_gespeichert = []
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler beim Löschen: {str(e)[:100]}")
                
                if st.session_state.get("material_expander_unten", False):
                    # Prüfe, ob die gespeicherten Werte nur '-' und 0.0 sind (Mitternachts-Reset)
                    eingabe = st.session_state.get("material_eingabe_gespeichert", [])
                    mitternacht_reset = (
                        eingabe and all(z.get("material") == "-" and z.get("menge") == 0.0 for z in eingabe)
                    )
                    # Nur zurücksetzen, wenn Expander noch unten ist und Mitternachtsreset erkannt wird
                    if mitternacht_reset and st.session_state.material_expander_unten:
                        st.session_state.material_expander_unten = False
                        st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                        st.session_state.material_eingabe_gespeichert = []
                        st.rerun()
            
            else:
                st.warning("Projekt nicht gefunden.")
        else:
            st.warning("Kein Projekt zugewiesen.")   
    st.caption("App-Version 0.1 – © DeineFirma 2025")
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------








def standardgehalt_page():
    st.set_page_config(page_title="Standardgehalt", layout="centered")
    st.title("Standardgehalt für Mitarbeiter")
    st.info("Hier kannst du den Standardgehalt für Mitarbeiter festlegen oder anzeigen.")
    rolle = st.selectbox("Rolle auswählen", ROLLEN)
    gehalt = st.number_input("Standardgehalt (€ pro Std)", min_value=0.0, step=0.1)
    if st.button("💾 Speichern"):
        with engine.begin() as conn:
            if gehalt == 0.0:
                conn.exec_driver_sql("DELETE FROM standardgehaelter WHERE rolle = %s", (rolle,))
                st.success(f"Standardgehalt für '{rolle}' wurde entfernt.")
            else:
                conn.exec_driver_sql("""
                    INSERT INTO standardgehaelter (rolle, gehalt)
                    VALUES (%s, %s)
                    ON CONFLICT(rolle) DO UPDATE SET gehalt=excluded.gehalt
                """, (rolle, gehalt))
                st.success(f"Standardgehalt für '{rolle}' auf {gehalt:.2f} € gesetzt.")
        st.rerun()
    # Tabelle anzeigen
    df_gehaelter = pd.read_sql("SELECT rolle, gehalt FROM standardgehaelter ORDER BY rolle", engine)
    df_gehaelter["Gehalt"] = df_gehaelter["gehalt"].map(lambda x: f"{x:.2f} €/Std")
    df_gehaelter = df_gehaelter[["Gehalt", "rolle"]]  # Gehalt ganz links
    st.subheader("Aktuelle Standardgehälter")
    table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
    table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Gehalt (€/Std)</th><th>Rolle</th></tr></thead><tbody>"
    for _, row in df_gehaelter.iterrows():
        geh_val = str(row['Gehalt']) if pd.notnull(row['Gehalt']) else "-"
        rolle_val = str(row['rolle']) if pd.notnull(row['rolle']) else "-"
        table_html += f"<tr><td><strong>{geh_val}</strong></td><td>{rolle_val}</td></tr>"
    table_html += "</tbody></table></div>"
    st.markdown(table_html, unsafe_allow_html=True)
    if st.button("← Zurück zum Profil"):
        st.session_state.page = "profil"
        st.rerun()










def materialplanung_page():
    st.set_page_config(page_title="Materialplanung", layout="centered")
    st.title("Material-Planung")

    if st.session_state.get("nutzer_typ") == "mitarbeiter":
        mitarbeiter = st.session_state.user
        chef_row = pd.read_sql(
            "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(mitarbeiter,)
        )
        chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
        if st.button("← Zurück zum Hauptmenü"):
            st.session_state.page = "app"
            st.rerun()
        with st.expander("+ Material aus Lager auswählen oder hinzufügen"):
            heute_str = date.today().strftime("%Y-%m-%d")
            df_termine = pd.read_sql(
                "SELECT datum FROM materialplanung WHERE datum >= %s ORDER BY datum",
                engine, params=(heute_str,)
            )
            termine_liste = df_termine["datum"].tolist()
            bestellung_auswahl = st.selectbox("Bestelltermin auswählen", termine_liste, key="bestellung_auswahl_mitarbeiter")

            mat_name = st.text_input("Materialname eingeben", key=f"mat_name_{bestellung_auswahl}")
            anzahl = st.number_input("Anzahl", min_value=1, step=1, key=f"anzahl_material_{bestellung_auswahl}")
            if st.button("Material eintragen", key=f"eintragen_{bestellung_auswahl}") and mat_name:
                projekt_id = st.session_state.get("projekt_id")
                df_proj = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(projekt_id,))
                projektname = df_proj["name"].iloc[0] if not df_proj.empty else ""
                rolle_row = pd.read_sql("SELECT rolle FROM mitarbeiter WHERE benutzername = %s", engine, params=(mitarbeiter,))
                rolle = rolle_row["rolle"].iloc[0] if not rolle_row.empty else ""
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO materialplanung (datum, material, menge, benutzername, projekt_id)
                            VALUES (:datum, :material, :menge, :benutzername, :projekt_id)
                        """),
                        {
                            "datum": bestellung_auswahl,
                            "material": mat_name,
                            "menge": anzahl,
                            "benutzername": mitarbeiter,
                            "projekt_id": st.session_state.get("projekt_id")
                        }
                    )
                st.success(f"Material '{mat_name}' ({anzahl}) zur Bestellung am {bestellung_auswahl} hinzugefügt.")
                st.rerun()

                # NUR für Bauunternehmer: Bestellungen hinzufügen (wiederkehrend oder einmalig)
    if st.session_state.get("nutzer_typ") == "bauunternehmer":
        with st.expander("Bestellung hinzufügen"):
            bestell_typ = st.radio("Bestelltyp wählen", ["Wiederkehrend (Rhythmus in Tagen)", "Einmalig"])
            if bestell_typ == "Wiederkehrend (Rhythmus in Tagen)":
                rhythmus = st.number_input("Rhythmus (Tage)", min_value=1, step=1, value=14, key="rhythmus_bestellung")
                startdatum = st.date_input("Startdatum", value=date.today(), key="startdatum_bestellung")
                anzahl_wdh = st.number_input("Wie oft wiederholen?", min_value=1, step=1, value=10, key="anzahl_wdh_bestellung")
                if st.button("Wiederkehrende Bestellung speichern", key="btn_wiederkehrend_bestellung"):
                    for i in range(anzahl_wdh):
                        bestell_datum = startdatum + timedelta(days=i*rhythmus)
                        with engine.begin() as conn:
                            conn.execute(
                                text("""
                                    INSERT INTO materialplanung (datum, material, menge, benutzername, projekt_id)
                                    VALUES (:datum, :material, :menge, :benutzername, :projekt_id)
                                """),
                                {
                                    "datum": bestell_datum.strftime("%Y-%m-%d"),
                                    "material": '',
                                    "menge": 0,
                                    "benutzername": st.session_state.user,
                                    "projekt_id": st.session_state.get("projekt_id")
                                }
                            )
                    st.success("Wiederkehrende Bestellung(en) gespeichert.")
                    st.rerun()
            else:  # Einmalig
                einmal_datum = st.date_input("Bestelldatum", value=date.today(), key="einmal_datum_bestellung")
                if st.button("Bestellung speichern"):
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                                INSERT INTO materialplanung (datum, material, menge, benutzername, projekt_id)
                                VALUES (:datum, :material, :menge, :benutzername, :projekt_id)
                            """),
                            {
                                "datum": einmal_datum.strftime("%Y-%m-%d"),
                                "material": '',
                                "menge": 0,
                                "benutzername": st.session_state.user,
                                "projekt_id": st.session_state.get("projekt_id")
                            }
                        )
                    st.success("Bestellung gespeichert.")
                    st.rerun()
        # Neuer Expander: Ermöglicht dem Bauunternehmer, konkrete Material-Einträge hinzuzufügen
        with st.expander("+ Material eintragen (Bauunternehmer)"):
            # Datumsauswahl: wähle bestehendes Bestelldatum oder neues Datum
            df_dates = pd.read_sql("SELECT DISTINCT datum FROM materialplanung WHERE datum >= %s ORDER BY datum", engine, params=(date.today().strftime('%Y-%m-%d'),))
            dates_list = df_dates['datum'].tolist()
            use_existing = st.checkbox("Vorhandenes Bestelldatum verwenden", value=True, key="bau_use_existing_date")
            if use_existing and dates_list:
                sel_date = st.selectbox("Bestelldatum auswählen", dates_list, key="bau_sel_date")
            else:
                sel_date_input = st.date_input("Datum auswählen", value=date.today(), key="bau_new_date")
                sel_date = sel_date_input.strftime('%Y-%m-%d')

            # Projekte des Bauunternehmers laden
            projekts = pd.read_sql("SELECT id, name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL ORDER BY name", engine, params=(st.session_state.user,))
            projekt_options = projekts['name'].tolist() if not projekts.empty else [""]
            # Filter nur AKTIVE Projekte
            projekt_options_active = [p for p in projekt_options if p != ""]
            projekt_choice = st.selectbox("Projekt (optional)", projekt_options, index=0 if projekt_options else 0, key="bau_proj_choice")

            mat_name_b = st.text_input("Materialname", key="bau_mat_name")
            anzahl_b = st.number_input("Anzahl", min_value=1, step=1, value=1, key="bau_mat_anzahl")
            # Für Bauunternehmer wird kein Mitarbeiter oder Rolle eingetragen - stattdessen '-' verwenden
            mitarbeiter_b = "-"
            rolle_b = "-"

            if st.button("Material speichern", key="bau_mat_save"):
                if not mat_name_b:
                    st.error("Bitte Materialname eingeben.")
                else:
                    # Finde die projekt_id basierend auf projekt_choice
                    projekt_id = None
                    if projekt_choice and projekt_choice != "":
                        matching_proj = projekts[projekts['name'] == projekt_choice]
                        if not matching_proj.empty:
                            projekt_id = int(matching_proj['id'].iloc[0])
                    
                    # Konvertiere Timestamp zu String für PostgreSQL
                    if isinstance(sel_date, str):
                        datum_str = sel_date
                    else:
                        datum_str = pd.Timestamp(sel_date).strftime("%Y-%m-%d")
                    
                    with engine.begin() as conn:
                        conn.execute(
                            text("""
                                INSERT INTO materialplanung (datum, material, menge, benutzername, projekt_id)
                                VALUES (:datum, :material, :menge, :benutzername, :projekt_id)
                            """),
                            {
                                "datum": datum_str,
                                "material": mat_name_b,
                                "menge": int(anzahl_b),
                                "benutzername": st.session_state.user,
                                "projekt_id": projekt_id
                            }
                        )
                    st.success(f"Material '{mat_name_b}' ({anzahl_b}) für {datum_str} gespeichert.")
                    st.rerun()
    # --- Tabelle: Alle Materialplanungen anzeigen ---
    st.subheader("Geplante Materialbestellungen")
    heute_str = date.today().strftime("%Y-%m-%d")
    df_plan = pd.read_sql(
        "SELECT * FROM materialplanung WHERE datum >= %s ORDER BY datum",
        engine,
        params=(heute_str,)
    )
    if df_plan.empty:
        st.info("Keine Materialplanungen vorhanden.")
    else:
        alle_termine = sorted(df_plan["datum"].unique())
        table_html = """
        <style>
        .scroll-table-wrapper {overflow-x: auto; border: 1px solid #ddd; padding: 1rem;}
        .scroll-table {border-collapse: collapse; min-width: 100%;}
        .scroll-table th, .scroll-table td {border: 1px solid #ccc; padding: 0.5rem 1rem; text-align: left;}
        .scroll-table th:first-child, .scroll-table td:first-child {position: sticky; left: 0; background: var(--table-header-bg); z-index: 1;}
        .scroll-table th {background: var(--table-header-bg); position: sticky; top: 0; z-index: 2;} 
        </style>
        <div class="scroll-table-wrapper">
        <table class="scroll-table">
        <thead>
        <tr>
            <th>Bestellung</th>
            <th>Material (Anzahl)</th>
            <th>Mitarbeiter (Rolle)</th>
            <th>Projekt</th>
        </tr>
        </thead>
        <tbody>
        """
        for datum in alle_termine:
            # Konvertiere Timestamp zu date, falls nötig
            if isinstance(datum, str):
                datum_dt = datetime.strptime(datum, "%Y-%m-%d").date()
            else:
                # Pandas Timestamp
                datum_dt = pd.Timestamp(datum).date()
            verbleibend = (datum_dt - date.today()).days
            bestellung = f"{datum_dt.strftime('%d.%m.%Y')} ({verbleibend} Tage)"
            eintraege = df_plan[(df_plan["datum"] == datum) & (df_plan["material"].notnull()) & (df_plan["material"] != "")]
            if eintraege.empty:
                # Platzhalter-Zeile nur, wenn keine Einträge vorhanden sind
                table_html += f"<tr><td><strong>{bestellung}</strong></td><td colspan='3' style='color:gray'>Keine Einträge</td></tr>"
            else:
                first = True
                for _, row in eintraege.iterrows():
                    material_anzahl = f"{row['material']} ({row['menge']})"
                    # Hole Mitarbeiter-Info aus benutzername
                    mitarbeiter_info = pd.read_sql(
                        "SELECT vorname, nachname FROM mitarbeiter WHERE benutzername = %s",
                        engine,
                        params=(row['benutzername'],)
                    )
                    if not mitarbeiter_info.empty:
                        mitarbeiter_rolle = f"{mitarbeiter_info['vorname'].iloc[0]} {mitarbeiter_info['nachname'].iloc[0]}"
                    else:
                        mitarbeiter_rolle = row.get('benutzername', '-')
                    
                    # Hole Projekt-Info aus projekt_id
                    projekt = '-'
                    if pd.notnull(row['projekt_id']) and row['projekt_id'] > 0:
                        projekt_info = pd.read_sql(
                            "SELECT name FROM projekte WHERE id = %s",
                            engine,
                            params=(row['projekt_id'],)
                        )
                        projekt = projekt_info['name'].iloc[0] if not projekt_info.empty else '-'
                    
                    if first:
                        table_html += f"<tr><td rowspan='{len(eintraege)}'><strong>{bestellung}</strong></td>"
                        first = False
                    else:
                        table_html += "<tr>"
                    table_html += f"<td>{material_anzahl}</td><td>{mitarbeiter_rolle}</td><td>{projekt}</td></tr>"
        table_html += "</tbody></table></div>"
        st.markdown(table_html, unsafe_allow_html=True)
        if st.session_state.get("nutzer_typ") == "mitarbeiter":
            if st.button("← Zurück zur Mitarbeiterseite"):
                st.session_state.page = "mitarbeiter"
                st.rerun()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------












def vorplanung_page():
    st.set_page_config(page_title="Vorplanungskalender", layout="centered")
    st.title("📅 Vorplanungskalender (14 Tage)")
    
    # Force refresh bei jedem Load
    if "vorplanung_refresh" not in st.session_state:
        st.session_state.vorplanung_refresh = 0
    
    if st.session_state.get("page") == "vorplanung":
        st.session_state.vorplanung_refresh += 1
    
    if st.session_state.get("nutzer_typ") == "mitarbeiter":
        if st.button("← Zurück zum Hauptmenü"):
            st.session_state.page = "app"
            st.rerun()
    heute = date.today()
    tage = [heute + timedelta(days=i) for i in range(14)]
    # Einzelplanung
    with st.expander("+ Neuen Eintrag hinzufügen"):
        datum = st.date_input("Datum", value=heute, min_value=heute, max_value=heute + timedelta(days=13))
        uhrzeiten = [f"{h:02d}:00" for h in range(6, 21)] + ["ganztägig"]
        col_von, col_bis = st.columns(2)
        with col_von:
            von = st.selectbox("Von", uhrzeiten, index=2)
        with col_bis:
            bis = st.selectbox("Bis", uhrzeiten, index=10)
        zeitraum = "ganztägig" if von == "ganztägig" or bis == "ganztägig" else f"{von} - {bis}"

        # Maschinen aus dem Lager holen
        if st.session_state.get("nutzer_typ") == "mitarbeiter":
            chef_row = pd.read_sql(
                "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
            )
            chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
            df_geraete = pd.read_sql(
                "SELECT geraet, anzahl FROM geraete_lager WHERE benutzername = %s", engine, params=(chefname,)
            )
        else:
            df_geraete = pd.read_sql(
                "SELECT geraet, anzahl FROM geraete_lager WHERE benutzername = %s", engine, params=(st.session_state.user,)
            )

        # Maschinen, die im gewählten Zeitraum schon vergeben sind, herausfiltern
        # PostgreSQL Version: Vereinfachte Query ohne komplexe String-Operationen
        belegte = pd.read_sql(
            "SELECT maschine, COUNT(*) as reserviert FROM vorplanung WHERE datum = %s AND zeitraum = %s GROUP BY maschine",
            engine, params=(datum.strftime("%Y-%m-%d"), zeitraum)
        )
        reserviert_dict = dict(zip(belegte["maschine"], belegte["reserviert"].fillna(0)))

        # Maschinenliste und verfügbare Anzahl berechnen
        maschinen_liste = []
        maschinen_anzahl = {}
        for _, row in df_geraete.iterrows():
            name = row["geraet"]
            gesamt = int(row["anzahl"])
            reserviert = int(reserviert_dict.get(name, 0))
            verfuegbar = gesamt - reserviert
            if verfuegbar > 0:
                maschinen_liste.append(name)
                maschinen_anzahl[name] = verfuegbar

        maschine = st.selectbox("Maschine auswählen", maschinen_liste)
        max_anzahl = maschinen_anzahl.get(maschine, 1)
        anzahl = st.selectbox("Anzahl Geräte", list(range(1, max_anzahl+1)), index=0, key="anzahl_einzel")

        # Projektname/Mitarbeiter wie gehabt
        if st.session_state.get("nutzer_typ") == "mitarbeiter":
            df_proj = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(st.session_state.get("projekt_id"),))
            projektname = df_proj["name"].iloc[0] if not df_proj.empty else ""
            mitarbeiter = st.session_state.user
            st.info(f"Projekt: {projektname}")
            st.info(f"Mitarbeiter: {mitarbeiter}")
        else:
            projektname = st.text_input("Projektname")
            mitarbeiter = st.text_input("Mitarbeiter")

        if st.button("Eintrag speichern"):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO vorplanung (datum, maschine, zeitraum, mitarbeiter, projektname)
                        VALUES (:datum, :maschine, :zeitraum, :mitarbeiter, :projektname)
                    """),
                    {
                        "datum": datum.strftime("%Y-%m-%d"),
                        "maschine": maschine,
                        "zeitraum": zeitraum,
                        "mitarbeiter": mitarbeiter,
                        "projektname": f"{projektname} - {anzahl}"
                    }
                )
            st.success(f"{anzahl} Gerät(e) für {maschine} geplant.")
            time.sleep(0.5)  # Warte kurz damit PostgreSQL die Änderung sieht
            st.rerun()

    # Langzeitplanung
    with st.expander("+ Langzeit-Gerätereservierung"):
        start_datum = st.date_input("Startdatum", value=heute)
        end_datum = st.date_input("Enddatum", value=heute + timedelta(days=13), min_value=start_datum)
        # Maschinen wie oben laden
        maschine_lang = st.selectbox("Gerät für Langzeitreservierung auswählen", maschinen_liste, key="langzeit_maschine")
        max_anzahl_lang = maschinen_anzahl.get(maschine_lang, 1)
        anzahl_lang = st.selectbox("Anzahl Geräte", list(range(1, max_anzahl_lang+1)), index=0, key="anzahl_langzeit")

        # Projektname/Mitarbeiter wie gehabt
        if st.session_state.get("nutzer_typ") == "mitarbeiter":
            df_proj = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(st.session_state.get("projekt_id"),))
            projektname_lang = df_proj["name"].iloc[0] if not df_proj.empty else ""
            mitarbeiter_lang = st.session_state.user
            st.info(f"Projekt: {projektname_lang}")
            st.info(f"Mitarbeiter: {mitarbeiter_lang}")
        else:
            projektname_lang = st.text_input("Projektname für Langzeitreservierung")
            mitarbeiter_lang = st.text_input("Mitarbeiter für Langzeitreservierung")

        if st.button("Langzeitreservierung speichern"):
            tage_lang = (end_datum - start_datum).days + 1
            for j in range(tage_lang):
                reserv_datum = start_datum + timedelta(days=j)
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO vorplanung (datum, maschine, zeitraum, mitarbeiter, projektname)
                            VALUES (:datum, :maschine, :zeitraum, :mitarbeiter, :projektname)
                        """),
                        {
                            "datum": reserv_datum.strftime("%Y-%m-%d"),
                            "maschine": maschine_lang,
                            "zeitraum": "ganztägig",
                            "mitarbeiter": mitarbeiter_lang,
                            "projektname": f"{projektname_lang} - {anzahl_lang}"
                        }
                    )
            st.success(f"{anzahl_lang} Gerät(e) für {maschine_lang} reserviert.")
            time.sleep(0.5)  # Warte kurz damit PostgreSQL die Änderung sieht
            st.rerun()
    # Daten für die nächsten 14 Tage laden - FORCE RELOAD ohne Cache
    df = pd.read_sql(
        "SELECT * FROM vorplanung WHERE datum >= %s AND datum <= %s ORDER BY datum, maschine",
        engine,
        params=(heute.strftime("%Y-%m-%d"), (heute + timedelta(days=13)).strftime("%Y-%m-%d"))
    )

    # Tabelle vorbereiten mit Cache-Buster
    cache_buster = st.session_state.vorplanung_refresh
    table_html = """
    <style>
    .scroll-table-wrapper {overflow-x: auto; border: 1px solid #ddd; padding: 1rem;}
    .scroll-table {border-collapse: collapse; min-width: 100%;}
    .scroll-table th, .scroll-table td {border: 1px solid #ccc; padding: 0.5rem 1rem; text-align: left;}
    .scroll-table th:first-child, .scroll-table td:first-child {position: sticky; left: 0; background: var(--table-header-bg); z-index: 1;}
    .scroll-table th {background: var(--table-header-bg); position: sticky; top: 0; z-index: 2;} 
    </style>
    <div class="scroll-table-wrapper">
    <table class="scroll-table">
    <thead>
    <tr>
        <th>Datum</th>
        <th>Maschine + Projekt</th>
        <th>Zeitraum</th>
        <th>Mitarbeiter</th>
    </tr>
    </thead>
    <tbody>
    """
    


    # Konvertiere datum zu String falls nötig
    if not df.empty:
        df['datum_str'] = pd.to_datetime(df['datum']).dt.strftime("%Y-%m-%d")
        # Filtere ungültige Einträge aus (wo mitarbeiter "None" oder "none" ist)
        df = df[~df['mitarbeiter'].isin(['None', 'none', None])]
        # Filtere Langzeitreservierungen aus (nur Einzelreservierungen in dieser Tabelle)
        df = df[df['zeitraum'] != 'ganztägig']
    
    # Baue Tabelle direkt aus den Daten auf
    for tag in tage:
        tag_str = tag.strftime("%d.%m.%Y")
        tag_search = tag.strftime("%Y-%m-%d")
        
        # Filtere Einträge für diesen Tag
        if not df.empty:
            eintraege = df[df['datum_str'] == tag_search]
        else:
            eintraege = pd.DataFrame()
        
        if eintraege.empty:
            table_html += f"<tr><td>{tag_str}</td><td colspan='3' style='color:gray'>Keine Einträge</td></tr>"
        else:
            first = True
            for _, row in eintraege.iterrows():
                # Anzahl aus dem Projektname extrahieren
                proj_parts = str(row['projektname']).rsplit(' - ', 1)
                projektname_clean = proj_parts[0]
                anzahl_str = proj_parts[1] if len(proj_parts) > 1 else "1"
                maschine_proj = f"{row['maschine']} ×{anzahl_str} ({projektname_clean})"
                if first:
                    table_html += f"<tr><td rowspan='{len(eintraege)}'><strong>{tag_str}</strong></td>"
                    first = False
                else:
                    table_html += "<tr>"
                table_html += f"<td>{maschine_proj}</td><td>{row['zeitraum']}</td><td>{row['mitarbeiter']}</td></tr>"
    table_html += "</tbody></table></div>"
    
    st.markdown(table_html, unsafe_allow_html=True)
    # Langzeitreservierungen aus der Datenbank laden
    langzeit_df = pd.read_sql(
        """
        SELECT maschine, projektname, MIN(datum) as von, MAX(datum) as bis
        FROM vorplanung
        WHERE zeitraum = 'ganztägig'
        GROUP BY maschine, projektname
        HAVING MAX(datum) >= CURRENT_DATE
        """,
        engine
    )

    if not langzeit_df.empty:
        st.subheader("Aktuelle Langzeit-Gerätereservierungen")
        for _, row in langzeit_df.iterrows():
            # Konvertiere Datum - kann bereits datetime.date sein
            try:
                von = pd.to_datetime(row["von"]).strftime("%d.%m.%Y")
                bis = pd.to_datetime(row["bis"]).strftime("%d.%m.%Y")
            except:
                von = str(row["von"])
                bis = str(row["bis"])
            st.info(f"{row['maschine']} ({row['projektname']}) {von} – {bis}")
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
                background-color: #2b2b2b !important;
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
        with st.expander("🏢 Firmenprofil"):   
            st.caption("Hier können Sie die grundlegenden Informationen über Ihr Unternehmen speichern. Diese werden für die Erstellung von Rechnungen und anderen Geschäftsdokumenten verwendet.")
            
            # Firmenname
            st.markdown("**Firmenname**")
            st.caption("Der Name Ihres Unternehmens, wie er auf Rechnungen und Dokumenten erscheinen soll.")
            firmenname = st.text_input("Firmenname für Rechnungen", value=st.session_state.firmenname, label_visibility="collapsed")
            
            # Gesellschaftsform
            st.markdown("**Gesellschaftsform**")
            gesellschaftsform = st.selectbox(
                    "Gesellschaftsform",
                    GESELLSCHAFTSFORMEN,
                    index=GESELLSCHAFTSFORMEN.index(st.session_state.get("gesellschaftsform", GESELLSCHAFTSFORMEN[0]))
                    if st.session_state.get("gesellschaftsform") in GESELLSCHAFTSFORMEN else 0,
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
        with st.expander("🏦 Bank- und Registerdaten"):
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
        with st.expander("🖼️ Firmenlogo hochladen"):
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
                background-color: #2b2b2b !important;
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

    if st.button("💾 Speichern"):
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

    if st.button("↩️ Zurück"):
        st.session_state.page = "app"
        st.rerun()

    # Theme Debug removed from profile — diagnostics are available on Einstellungen.


# Bericht-Archiv Seite
def generate_report_pdf_from_data(projekt_name, datum, report_data):
    """Generiere Report-PDF aus gespeicherten Daten (on-demand)
    
    Args:
        projekt_name: Name des Projekts
        datum: Datum des Berichts (str oder date)
        report_data: Dictionary mit Bericht-Feldern
            - wetter, boden, arbeitsbericht, mitarbeiter, materialeinsatz, 
              geraeteeinsatz, probleme, todo, checklisten_data
    
    Returns:
        BytesIO buffer mit PDF
    """
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from datetime import datetime
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Tagesbericht")
    
    c.setFont("Helvetica", 10)
    y = height - 80
    c.drawString(50, y, f"Projekt: {projekt_name}")
    y -= 20
    
    # Datum formatieren
    if isinstance(datum, str):
        datum_str = datum
    else:
        datum_str = datum.strftime("%d.%m.%Y")
    c.drawString(50, y, f"Datum: {datum_str}")
    y -= 30
    
    # Bericht-Daten
    fields = [
        ("Wetter", report_data.get("wetter", "")),
        ("Bodenzustand", report_data.get("boden", "")),
        ("Arbeitsbericht", report_data.get("arbeitsbericht", "")),
        ("Mitarbeiter", report_data.get("mitarbeiter", "")),
        ("Materialeinsatz", report_data.get("materialeinsatz", "")),
        ("Geräteeinsatz", report_data.get("geraeteeinsatz", "")),
        ("Probleme", report_data.get("probleme", "")),
        ("To-Do", report_data.get("todo", "")),
    ]
    
    for label, value in fields:
        if value:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, f"{label}:")
            y -= 15
            
            c.setFont("Helvetica", 9)
            # Text wrapping für längere Inhalte
            lines = (value or "").split("\n")
            for line in lines:
                if len(line) > 90:
                    # Teile lange Zeilen auf
                    for i in range(0, len(line), 90):
                        c.drawString(60, y, line[i:i+90])
                        y -= 12
                else:
                    c.drawString(60, y, line)
                    y -= 12
            y -= 5
    
    # Footer
    y = 30
    c.setFont("Helvetica", 8)
    c.drawString(50, y, f"Generiert: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    c.drawString(width - 150, y, "[Regeneriert aus Archiv-Daten]")
    
    c.save()
    buffer.seek(0)
    return buffer

def berichtarchiv_page():
    st.set_page_config(page_title="Bericht-Archiv", layout="centered")
    col_head, col_btn = st.columns([8, 2])
    with col_head:
        st.title("Tagesbericht-Archiv")
    with col_btn:
        st.button("Zurück", on_click=lambda: st.session_state.update(page="profil"))
    st.info("Hier kannst du für jedes Projekt und beliebiges Datum einen Tagesbericht als PDF erstellen.")

    # Alle Projekte des Bauunternehmers laden
    projekte = pd.read_sql("SELECT id, name FROM projekte WHERE benutzername = %s", engine, params=(st.session_state.user,))
    if projekte.empty:
        st.info("Noch keine Projekte vorhanden.")
        return

    for _, projekt in projekte.iterrows():
        with st.expander(f"Projekt: {projekt['name']}"):
            # Datum auswählen
            datum = st.date_input(
                f"Berichtsdatum für {projekt['name']}",
                value=date.today(),
                key=f"archiv_datum_{projekt['id']}"
            )
            if st.button(f"Bericht für {datum.strftime('%d.%m.%Y')} erstellen", key=f"archiv_pdf_{projekt['id']}")::
                # PDF wie im Fortschrittsbericht erzeugen, aber mit gewähltem Datum
                heute_str = datum.strftime("%Y-%m-%d")
                
                buffer = BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                c.setFont("Helvetica", 20)
                y = 800
                # Kopfzeile
                firmenname = st.session_state.get("firmenname","")
                c.drawString(50, y, firmenname)
                y -= 25
                # Dicke gestrichelte Linie
                c.setLineWidth(2)
                c.setDash(6, 6)
                c.line(40, y, 550, y)
                c.setDash()
                y -= 20
                c.setFont("Helvetica", 10)
                c.drawString(50, y, f"Datum: {heute_str}")
                y -= 30

                # Wetterdaten für das Projekt und den Tag laden
                wetter_row = pd.read_sql(
                    "SELECT * FROM wetterdaten WHERE projekt_id = %s AND datum = %s",
                    engine, params=(projekt["id"], heute_str)
                )

                # Dünne Linie oben
                c.setLineWidth(1)
                c.setDash()
                c.line(40, y, 550, y)
                y -= 20

                if not wetter_row.empty:
                    wetter1 = wetter_row["wetter1"].iloc[0]
                    wetter2 = wetter_row["wetter2"].iloc[0]
                    boden1 = wetter_row["boden1"].iloc[0]
                    boden2 = wetter_row["boden2"].iloc[0]
                    temperatur = wetter_row["temperatur"].iloc[0]
                    schlecht = wetter_row["schlecht"].iloc[0]

                    # Wetter-Überschrift
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(50, y, "Wetter:")
                    c.setFont("Helvetica", 10)
                    c.drawString(170, y, str(wetter1))
                    c.drawString(300, y, str(wetter2))
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(390, y, "Temperatur:")
                    c.setFont("Helvetica", 10)
                    c.drawString(490, y, f"{temperatur} °C")
                    y -= 20
                    # Dünne Linie mitte
                    c.setLineWidth(1)
                    c.setDash()
                    c.line(40, y, 550, y)
                    y -= 20
                    # Bodenverhältnisse-Überschrift
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(50, y, "Bodenverhältnisse:")
                    c.setFont("Helvetica", 10)
                    c.drawString(170, y, str(boden1))
                    c.drawString(300, y, str(boden2))
                    y-= 20
                    # Dünne Linie mitte 2
                    c.setLineWidth(1)
                    c.setDash()
                    c.line(40, y, 550, y)
                    y -= 20
                    # Schlechtes Wetter
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(50, y, "Schlechtes Wetter:")
                    c.setFont("Helvetica", 10)
                    c.drawString(170, y, "Ja" if schlecht else "Nein")
                    y -= 20
                # Dünne Linie mitte 3
                c.setLineWidth(1)
                c.setDash()
                c.line(40, y, 550, y)
                y -= 20
                # Anzahl der Arbeitskräfte am Berichtstag
                arbeitskraefte_df = pd.read_sql(
                    "SELECT COUNT(DISTINCT benutzername) AS anzahl FROM arbeitszeiten WHERE projekt_id = %s AND datum = %s",
                    engine, params=(projekt["id"], heute_str)
                )
                anzahl_arbeitskraefte = arbeitskraefte_df["anzahl"].iloc[0] if not arbeitskraefte_df.empty else 0

                c.setFont("Helvetica-Bold", 10)
                c.drawString(50, y, "Anzahl AK:")
                c.setFont("Helvetica", 10)
                c.drawString(170, y, str(anzahl_arbeitskraefte))
                y -= 20
                # Dünne Linie unten
                c.setLineWidth(1)
                c.setDash()
                c.line(40, y, 550, y)
                y -= 20
                df = pd.read_sql(
                    "SELECT * FROM checklistenpunkte WHERE projekt_id = %s AND erledigt = 1 AND erledigt_am = %s ORDER BY id",
                    engine, params=(projekt["id"], heute_str)
                )

                if df.empty:
                    st.warning("Es wurden noch keine Fortschrittsdaten erfasst.")

                c.setFont("Helvetica-Bold", 10)    
                c.drawString(50, y, "Ausgeführte Arbeiten:")
                c.setFont("Helvetica", 10)
                y -= 20
                for _, row in df.iterrows():
                    erledigt = "-" if row["erledigt"] else "X"
                    c.drawString(60, y, f"{erledigt} {row['text']}")
                    y -= 15
                    if y < 100:
                        c.showPage()
                        y = 800
                # Mitarbeiter-Kommentar aus checklisten_fortschrittkommentar
                fortschrittkommentar_row = pd.read_sql(
                    "SELECT kommentar FROM checklisten_fortschrittkommentar WHERE projekt_id = %s AND datum = %s",
                    engine, params=(projekt["id"], heute_str)
                )
                if not fortschrittkommentar_row.empty:
                    mitarbeiter_kommentar = fortschrittkommentar_row["kommentar"].iloc[0]
                    if mitarbeiter_kommentar and mitarbeiter_kommentar.strip():
                        c.drawString(60, y, f"- {mitarbeiter_kommentar} ")
                        y -= 15
                        if y < 100:
                            c.showPage()
                            y = 800
                y -= 20 
                # Probleme & Zeitaufwand aus checklisten_gesamtkommentar laden
                problem_row = pd.read_sql(
                    "SELECT kommentar, zeitaufwand FROM checklisten_gesamtkommentar WHERE projekt_id = %s AND kommentar != '' AND datum = %s",
                    engine, params=(projekt["id"], heute_str)
                )
                
                # Mitarbeiterstunden
                mitarbeiter_df = pd.read_sql(
                    """
                    SELECT m.benutzername, m.rolle, COALESCE(SUM(a.stunden), 0) as stunden
                    FROM mitarbeiter m
                    INNER JOIN mitarbeiter_projekte mp ON m.benutzername = mp.mitarbeiter_benutzername
                    LEFT JOIN arbeitszeiten a
                        ON m.benutzername = a.benutzername AND a.projekt_id = mp.projekt_id AND a.datum = %s
                    WHERE mp.projekt_id = %s
                    GROUP BY m.benutzername, m.rolle
                    """,
                    engine, params=(heute_str, projekt["id"])
                )

                # Geräte-Nutzungen
                geraete_nutzung_df = pd.read_sql(
                    """
                    SELECT geraet, nutzungszeit
                    FROM geraete_nutzung
                    WHERE projekt_id = %s AND datum = %s
                    """,
                    engine, params=(projekt["id"], heute_str)
                )
                
                if not problem_row.empty:
                    left_margin = 60
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(left_margin, y, "Problem & Zeitaufwand:")
                    y -= 18
                    for _, row in problem_row.iterrows():
                        kommentar = row["kommentar"] or ""
                        zeit = row["zeitaufwand"] or ""
                        wrapped_lines = textwrap.wrap(kommentar, width=50)
                        c.setFont("Helvetica", 10)
                        for i, line in enumerate(wrapped_lines):
                            c.drawString(left_margin, y, line)
                            y -= 20
                        c.setFont("Helvetica-Bold", 10)
                        c.drawString(left_margin, y, "Benötigte Zeit:")
                        text_width = c.stringWidth("Benötigte Zeit:", "Helvetica-Bold", 10)
                        c.setFont("Helvetica", 10)
                        c.drawString(left_margin + text_width + 10, y, str(zeit) + "  min.")
                        y -= 15
                        y -= 5

                # Tabellen nebeneinander auf gleicher Höhe
                y_tabellen = y
                x_mitarbeiter = 40
                x_geraete = 320

                # --- Mitarbeiterstunden-Tabelle ---
                c.setLineWidth(1)
                c.setDash()
                c.line(x_mitarbeiter, y_tabellen, x_mitarbeiter + 255, y_tabellen)
                y_mitarbeiter = y_tabellen - 18
                c.setFont("Helvetica-Bold", 10)
                c.drawString(x_mitarbeiter + 10, y_mitarbeiter, "Mitarbeiter")
                c.drawString(x_mitarbeiter + 205, y_mitarbeiter, "Stunden")
                y_mitarbeiter -= 10
                c.setLineWidth(1)
                c.setDash()
                c.line(x_mitarbeiter, y_mitarbeiter, x_mitarbeiter + 255, y_mitarbeiter)
                y_mitarbeiter -= 20
                c.setFont("Helvetica", 10)
                mitarbeiter_namen_df = pd.read_sql(
                    """SELECT m.benutzername, m.vorname, m.nachname 
                    FROM mitarbeiter m
                    INNER JOIN mitarbeiter_projekte mp ON m.benutzername = mp.mitarbeiter_benutzername
                    WHERE mp.projekt_id = %s""", 
                    engine, params=(projekt["id"],))
                name_map = mitarbeiter_namen_df.set_index("benutzername").apply(lambda x: f"{x['vorname']} {x['nachname']}", axis=1).to_dict()
                for _, row in mitarbeiter_df.iterrows():
                    voller_name = name_map.get(row["benutzername"], row["benutzername"])
                    rolle = row["rolle"] or "-"
                    stunden = f"{row['stunden']:.2f}"
                    c.drawString(x_mitarbeiter + 10, y_mitarbeiter, f"{voller_name} ({rolle})")
                    c.drawString(x_mitarbeiter + 225, y_mitarbeiter, f"{stunden}")
                    y_mitarbeiter -= 15
                y_mitarbeiter -= 5

                # --- Geräte-Nutzungen-Tabelle ---
                c.setLineWidth(1)
                c.setDash()
                c.line(x_geraete, y_tabellen, x_geraete + 255, y_tabellen)
                y_geraete = y_tabellen - 18
                c.setFont("Helvetica-Bold", 10)
                c.drawString(x_geraete + 10, y_geraete, "Geräte")
                c.drawString(x_geraete + 205, y_geraete, "Stunden")
                y_geraete -= 10
                c.setLineWidth(1)
                c.setDash()
                c.line(x_geraete, y_geraete, x_geraete + 255, y_geraete)
                y_geraete -= 20
                c.setFont("Helvetica", 10)
                for _, row in geraete_nutzung_df.iterrows():
                    try:
                        geraet = str(row["geraet"])
                        nutzungszeit = float(row["nutzungszeit"]) if pd.notnull(row["nutzungszeit"]) else 0.0
                        c.drawString(x_geraete + 10, y_geraete, f"{geraet}")
                        c.drawString(x_geraete + 225, y_geraete, f"{nutzungszeit:.2f}")
                        y_geraete -= 15
                    except Exception as e:
                        pass
                y_geraete -= 5

                # Material
                y_material = min(y_mitarbeiter, y_geraete) - 18
                c.setLineWidth(1)
                c.setDash()
                c.line(x_mitarbeiter, y_material + 18, x_mitarbeiter + 255, y_material + 18)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(x_mitarbeiter + 10, y_material, "Material")
                c.drawString(x_mitarbeiter + 210, y_material, "Menge")
                y_material -= 10
                c.setLineWidth(1)
                c.setDash()
                c.line(x_mitarbeiter, y_material, x_mitarbeiter + 255, y_material)
                y_material -= 20
                
                material_df = pd.read_sql(
                    "SELECT material, menge, einheit FROM materialien WHERE projekt_id = %s AND datum = %s",
                    engine, params=(projekt["id"], heute_str)
                )

                c.setFont("Helvetica", 10)
                for _, row in material_df.iterrows():
                    try:
                        material = str(row["material"])
                        menge = float(row["menge"]) if pd.notnull(row["menge"]) else 0.0
                        einheit = str(row["einheit"]) if "einheit" in row and pd.notnull(row["einheit"]) else ""
                        c.drawString(x_mitarbeiter + 10, y_material, f"{material}")
                        c.drawString(x_mitarbeiter + 180, y_material, f"{menge:.2f} {einheit}")
                        y_material -= 15
                    except Exception as e:
                        pass

                c.save()
                buffer.seek(0)
                
                st.success(f"PDF für {datum.strftime('%d.%m.%Y')} erstellt!")
                st.download_button("📥 PDF herunterladen", buffer, file_name=f"Bericht_{projekt['name']}_{datum.strftime('%Y%m%d')}.pdf", mime="application/pdf")



# === Rechnungs-Archiv ===
def rechnungarchiv_page():
    st.set_page_config(page_title="Rechnungs-Archiv", layout="centered")
    col_head, col_btn = st.columns([8, 2])
    with col_head:
        st.title("Rechnungs-Archiv")
    with col_btn:
        if st.button("← Zurück zum Profil"):
            st.session_state.page = "profil"
            st.rerun()
    
    # Lade nur Rechnungen des aktuell angemeldeten Bauunternehmers
    current_user = st.session_state.get("user")
    if not current_user:
        st.info("Bitte melde dich an, um dein Rechnungs-Archiv zu sehen.")
        return
    # Lade Rechnungen, die dem Benutzer zugeordnet sind oder keine benutzername haben
    # aber zum Projekt des Benutzers gehören (Fallback für alte DBs)
    df_all = pd.read_sql(
        """
        SELECT r.id, r.projekt_name, r.rechnungsnummer, r.erstellt_am
        FROM rechnungen r
        WHERE (
            r.benutzername = %s
            OR (
                (r.benutzername IS NULL OR r.benutzername = '')
                AND EXISTS(
                    SELECT 1 FROM projekte p
                    WHERE (p.projekt_name = r.projekt_name OR p.name = r.projekt_name)
                      AND p.benutzername = %s
                )
            )
        )
        ORDER BY r.erstellt_am DESC
        """,
        engine,
        params=(current_user, current_user)
    )
    # Nur die neueste Rechnung pro Projekt anzeigen
    df_latest = df_all.sort_values("erstellt_am", ascending=False).drop_duplicates(subset=["projekt_name"], keep="first")
    if df_latest.empty:
        st.info("Noch keine Rechnungen vorhanden.")
        return
    auswahl_liste = [f"{row['erstellt_am']} – {row['projekt_name']}" for _, row in df_latest.iterrows()]
    projekt_map = {f"{row['erstellt_am']} – {row['projekt_name']}": row['projekt_name'] for _, row in df_latest.iterrows()}
    projekt_auswahl_label = st.selectbox("Projekt auswählen", auswahl_liste)
    projekt_auswahl = projekt_map.get(projekt_auswahl_label, None)
    if projekt_auswahl:
        # Lade nur die Rechnung für dieses Projekt und den aktuellen Benutzer
        # Versuche erst den normalen Fetch nach benutzername, falls nichts gefunden,
        # versuche Fallback über Projektzugehörigkeit (für Legacy-Zeilen ohne benutzername).
        row = pd.read_sql(
            """
            SELECT rechnungsnummer, erstellt_am, pdf_data FROM rechnungen r
            WHERE r.projekt_name = %s
              AND (
                  r.benutzername = %s
                  OR (r.benutzername IS NULL OR r.benutzername = '')
                      AND EXISTS(
                          SELECT 1 FROM projekte p
                          WHERE (p.projekt_name = r.projekt_name OR p.name = r.projekt_name)
                            AND p.benutzername = %s
                      )
              )
            ORDER BY r.erstellt_am DESC LIMIT 1
            """,
            engine, params=(projekt_auswahl, current_user, current_user)
        )
        if row.empty:
            st.warning("Keine Rechnungen für dieses Projekt gefunden.")
        else:
            erstellt = row["erstellt_am"].iloc[0]
            pdf_bytes = row["pdf_data"].iloc[0]
            
            # Konvertiere memoryview zu bytes
            if isinstance(pdf_bytes, memoryview):
                pdf_bytes = bytes(pdf_bytes)
            
            # Nimm die Rechnungsnummer direkt aus der Tabelle (die tatsächliche Nummer dieser Rechnung)
            nummer = row["rechnungsnummer"].iloc[0]
            
            pdf_size = len(pdf_bytes) if pdf_bytes else 0
            st.markdown(f"---\n**Rechnungsnummer:** {nummer} | **Erstellt am:** {erstellt}")
            st.markdown(f"PDF-Größe: **{pdf_size} Bytes**")
            if pdf_size > 100:
                st.download_button(
                    f"📥 Rechnung {nummer} herunterladen",
                    data=pdf_bytes,
                    file_name=f"Rechnung_{projekt_auswahl}_{nummer}.pdf",
                    mime="application/pdf",
                    key=f"download_{projekt_auswahl}_{nummer}"
                )
            else:
                st.warning("Die PDF ist leer oder beschädigt. Bitte Rechnung neu erstellen.")
                if pdf_bytes:
                    hex_preview = pdf_bytes[:100].hex()
                    st.markdown(f"**PDF-Bytes (Hex, erste 100):** {hex_preview}")

# === Setup Company Profile Page ===
def setup_company_profile_page():
    """Seite zur Einrichtung des Firmenprofils nach dem ersten Login"""
    st.set_page_config(page_title="Firmenprofil einrichten", layout="centered")
    st.title("Firmenprofil einrichten")
    st.markdown("---")
    st.info("Bitte geben Sie die erforderlichen Informationen über Ihr Unternehmen ein. Diese Daten sind essentiell für die Erstellung von Rechnungen und anderen Dokumenten.")
    
    with st.form("setup_company_profile_form"):
        st.markdown("### Unternehmensinformation")
        
        # Firmenname
        st.markdown("**Firmenname**")
        st.caption("Der Name Ihres Unternehmens, wie er auf Rechnungen und Dokumenten erscheinen soll.")
        firmenname = st.text_input(
            "Firmenname",
            value=st.session_state.get("firmenname", ""),
            label_visibility="collapsed"
        )
        
        # Gesellschaftsform
        st.markdown("**Gesellschaftsform**")
        gesellschaftsform = st.selectbox(
            "Gesellschaftsform",
            GESELLSCHAFTSFORMEN,
            index=GESELLSCHAFTSFORMEN.index(st.session_state.get("gesellschaftsform", GESELLSCHAFTSFORMEN[0])),
            label_visibility="collapsed"
        )
        
        # Adresse
        st.markdown("**Adresse**")
        st.caption("Geben Sie Ihre Geschäftsadresse ein (z.B. Straße 5, 12345 Stadt).")
        col1, col2 = st.columns(2)
        with col1:
            strasse = st.text_input("Straße und Hausnummer", placeholder="Beispiel: Hauptstraße 5")
        with col2:
            plz = st.text_input("Postleitzahl", placeholder="Beispiel: 12345", max_chars=5)
        stadt = st.text_input("Stadt", placeholder="Beispiel: Berlin")
        
        adresse = f"{strasse}, {plz} {stadt}" if strasse or plz or stadt else ""
        
        st.markdown("**Telefon & Fax**")
        col1, col2 = st.columns(2)
        with col1:
            telefon = st.text_input("Telefon", value=st.session_state.get("firmentelefon", ""), placeholder="z.B. +49 30 123456")
        with col2:
            fax = st.text_input("Fax", value=st.session_state.get("firmenfax", ""), placeholder="z.B. +49 30 123457")
        
        # Rechnungsnummer
        st.markdown("**Rechnungsnummer (Startnummer)**")
        st.caption("Die Rechnungsnummer für Ihr nächstes Projekt. Sie wird automatisch mit jedem neuen Projekt erhöht.")
        rechnungsnummer = st.number_input(
            "Rechnungsnummer",
            min_value=1,
            value=st.session_state.get("standard_rechnungsnummer", 100),
            label_visibility="collapsed"
        )
        
        submit = st.form_submit_button("Speichern und fortfahren")
    
    if submit:
        if not firmenname or not adresse or not gesellschaftsform:
            st.error("Bitte füllen Sie alle erforderlichen Felder aus (Firmenname, Adresse, Gesellschaftsform).")
        else:
            # Speichere die Daten in der Datenbank
            try:
                with engine.begin() as conn:
                    # Prüfe ob bereits ein Eintrag existiert
                    existing = conn.exec_driver_sql(
                        "SELECT benutzername FROM firmenprofil WHERE benutzername = %s",
                        (st.session_state.user,)
                    ).fetchone()
                    
                    if existing:
                        # Update
                        conn.exec_driver_sql(
                            """UPDATE firmenprofil 
                               SET firmenname = %s, gesellschaftsform = %s, adresse = %s, 
                                   telefon = %s, fax = %s, rechnungsnummer = %s
                               WHERE benutzername = %s""",
                            (firmenname, gesellschaftsform, adresse, telefon, fax, int(rechnungsnummer), st.session_state.user)
                        )
                        st.success("Firmenprofil erfolgreich aktualisiert!")
                    else:
                        # Insert
                        conn.exec_driver_sql(
                            """INSERT INTO firmenprofil 
                               (benutzername, firmenname, gesellschaftsform, adresse, telefon, fax, rechnungsnummer)
                               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state.user, firmenname, gesellschaftsform, adresse, telefon, fax, int(rechnungsnummer))
                        )
                        st.success("Firmenprofil erfolgreich erstellt!")
                
                # ✅ Reload Firmendaten
                lade_firmendaten()
                
                # Stelle sicher dass Session aktualisiert ist
                st.session_state.firmenname = firmenname
                st.session_state.firmenadresse = adresse
                st.session_state.firmentelefon = telefon
                st.session_state.firmenfax = fax
                st.session_state.gesellschaftsform = gesellschaftsform
                st.session_state.standard_rechnungsnummer = int(rechnungsnummer)
                
                st.info("Daten gespeichert! Leite zur Hauptseite weiter...")
                st.session_state.page = "app"
                st.rerun()
            
            except Exception as e:
                st.error(f"Fehler beim Speichern: {str(e)}")
                st.write(f"Debug: {str(e)}")

# === Setup Bank and Register Data Page ===
def setup_bank_register_data_page():
    """Seite zur Einrichtung der Bank- und Registerdaten für Rechnungen"""
    st.set_page_config(page_title="Bank- und Registerdaten", layout="centered")
    st.title("🏦 Bank- und Registerdaten einrichten")
    st.markdown("---")
    st.error("Diese Daten sind essentiell für die Erstellung von vollständigen Rechnungen. Bitte geben Sie mindestens IBAN, BIC und Bankname ein.")
    st.markdown("")
    
    with st.form("setup_bank_register_form"):
        st.markdown("### Bankverbindung (Erforderlich)")
        
        # IBAN
        st.markdown("**IBAN**")
        st.caption("Die internationale Bankkontonummer (z.B. DE89370400440532013000).")
        iban = st.text_input(
            "IBAN",
            value=st.session_state.get("iban", ""),
            placeholder="DE89370400440532013000",
            label_visibility="collapsed"
        )
        
        # BIC
        st.markdown("**BIC**")
        st.caption("Der internationale Bankleitzahl-Code (z.B. COBADEFFXXX).")
        bic = st.text_input(
            "BIC",
            value=st.session_state.get("bic", ""),
            placeholder="COBADEFFXXX",
            label_visibility="collapsed"
        )
        
        # Bankname
        st.markdown("**Bankname**")
        st.caption("Name der Bank oder Sparkasse (z.B. Commerzbank AG).")
        bankname = st.text_input(
            "Bankname",
            value=st.session_state.get("bankname", ""),
            placeholder="z.B. Commerzbank AG",
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### Registerdaten (Optional)")
        
        # Registergericht
        st.markdown("**Registergericht**")
        st.caption("Das Amtsgericht, bei dem Ihr Unternehmen registriert ist (z.B. Amtsgericht Berlin).")
        registergericht = st.text_input(
            "Registergericht",
            value=st.session_state.get("registergericht", ""),
            placeholder="z.B. Amtsgericht Berlin",
            label_visibility="collapsed"
        )
        
        # HRB-Nummer
        st.markdown("**HRB-Nummer**")
        st.caption("Ihre Handelsregisternummer (z.B. HRB 123456).")
        hrb_nummer = st.text_input(
            "HRB-Nummer",
            value=st.session_state.get("hrb_nummer", ""),
            placeholder="z.B. HRB 123456",
            label_visibility="collapsed"
        )
        
        # USt-IdNr
        st.markdown("**USt-IdNr.**")
        st.caption("Ihre Umsatzsteuer-Identifikationsnummer (z.B. DE123456789).")
        ustidnr = st.text_input(
            "USt-IdNr.",
            value=st.session_state.get("ustidnr", ""),
            placeholder="z.B. DE123456789",
            label_visibility="collapsed"
        )
        
        # Geschäftsführer
        st.markdown("**Geschäftsführer/Inhaber**")
        st.caption("Name der Person, die das Unternehmen führt.")
        geschaeftsfuehrer = st.text_input(
            "Geschäftsführer",
            value=st.session_state.get("geschaeftsfuehrer", ""),
            placeholder="z.B. Max Mustermann",
            label_visibility="collapsed"
        )
        
        submit = st.form_submit_button("Speichern und fortfahren")
    
    if submit:
        if not iban or not bic or not bankname:
            st.error("Bitte füllen Sie mindestens die Pflichtfelder aus (IBAN, BIC, Bankname).")
        else:
            # Speichere die Daten in der Datenbank
            try:
                with engine.begin() as conn:
                    # Prüfe ob bereits ein Eintrag existiert
                    existing = conn.exec_driver_sql(
                        "SELECT benutzername FROM firmenprofil WHERE benutzername = %s",
                        (st.session_state.user,)
                    ).fetchone()
                    
                    if existing:
                        # Update
                        conn.exec_driver_sql(
                            """UPDATE firmenprofil 
                               SET iban = %s, bic = %s, bankname = %s, 
                                   registergericht = %s, hrb_nummer = %s, ustidnr = %s, geschaeftsfuehrer = %s
                               WHERE benutzername = %s""",
                            (iban, bic, bankname, registergericht, hrb_nummer, ustidnr, geschaeftsfuehrer, st.session_state.user)
                        )
                        st.success("Bank- und Registerdaten erfolgreich aktualisiert!")
                    else:
                        # Insert (falls noch kein Firmenprofil existiert)
                        conn.exec_driver_sql(
                            """INSERT INTO firmenprofil 
                               (benutzername, iban, bic, bankname, registergericht, hrb_nummer, ustidnr, geschaeftsfuehrer)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (st.session_state.user, iban, bic, bankname, registergericht, hrb_nummer, ustidnr, geschaeftsfuehrer)
                        )
                        st.success("Bank- und Registerdaten erfolgreich erstellt!")
                
                # ✅ Reload Firmendaten
                lade_firmendaten()
                
                # Stelle sicher dass Session aktualisiert ist
                st.session_state.iban = iban
                st.session_state.bic = bic
                st.session_state.bankname = bankname
                st.session_state.registergericht = registergericht
                st.session_state.hrb_nummer = hrb_nummer
                st.session_state.ustidnr = ustidnr
                st.session_state.geschaeftsfuehrer = geschaeftsfuehrer
                
                st.info("Daten gespeichert! Leite zur Rechnungsseite weiter...")
                
                # Gehe zur Rechnungsseite zurück (mit nav schon gesetzt)
                st.session_state.page = "app"
                st.session_state.nav = "Rechnung erstellen"
                st.rerun()
                
            except Exception as e:
                st.error(f"Fehler beim Speichern: {str(e)}")
                st.write(f"Debug: {str(e)}")

# Neue Seite: Lohnabrechnung
def lohnabrechnung_page():
    import calendar
    aktuelles_jahr = datetime.now().year
    aktueller_monat = datetime.now().month
    monate = list(range(1, 13))
    monat = st.selectbox("Monat", monate, index=aktueller_monat-1, format_func=lambda m: calendar.month_name[m])
    jahr = st.number_input("Jahr", min_value=2020, max_value=aktuelles_jahr+1, value=aktuelles_jahr, step=1)
    monat_str = f"{monat:02d}"
    jahr_str = str(jahr)
    st.set_page_config(page_title="Lohnübersicht", layout="centered")
    st.title("Lohnübersicht für Mitarbeiter")
    df_mitarbeiter = pd.read_sql("SELECT benutzername, vorname, nachname, rolle FROM mitarbeiter", engine)
    df_stunden = pd.read_sql(
    "SELECT benutzername, SUM(stunden) as gesamtstunden FROM arbeitszeiten WHERE TO_CHAR(datum, 'MM') = %s AND TO_CHAR(datum, 'YYYY') = %s GROUP BY benutzername",
    engine, params=(monat_str, jahr_str)
    )   
    df_gehalt = pd.read_sql("SELECT rolle, gehalt FROM standardgehaelter", engine)
    df_mitarbeiter["voller_name"] = df_mitarbeiter["vorname"] + " " + df_mitarbeiter["nachname"]
    mitarbeiter_liste = df_mitarbeiter["voller_name"].tolist()
    benutzer_map = dict(zip(df_mitarbeiter["voller_name"], df_mitarbeiter["benutzername"]))
    # Stunden- und Lohnübersicht ganz oben anzeigen
    st.subheader(f"Stunden- und Lohnübersicht für {calendar.month_name[monat]} {jahr}")
    df = df_mitarbeiter.merge(df_stunden, on="benutzername", how="left").merge(df_gehalt, on="rolle", how="left")
    df["gesamtstunden"] = df["gesamtstunden"].fillna(0)
    df["gehalt"] = df["gehalt"].fillna(0)
    df["Bruttolohn (€)"] = df["gesamtstunden"] * df["gehalt"]
    # HTML-Tabelle für Lohnübersicht
    display_cols = ["voller_name", "rolle", "gesamtstunden", "gehalt", "Bruttolohn (€)"]
    table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
    table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Name</th><th>Rolle</th><th>Gesamtstunden</th><th>Gehalt (€/h)</th><th>Bruttolohn (€)</th></tr></thead><tbody>"
    for _, row in df[display_cols].iterrows():
        voller_name = str(row['voller_name']) if pd.notnull(row['voller_name']) else ""
        rolle = str(row['rolle']) if pd.notnull(row['rolle']) else "-"
        gesamtstunden = f"{float(row['gesamtstunden']):.1f}" if pd.notnull(row['gesamtstunden']) else "0.0"
        gehalt = f"{float(row['gehalt']):.2f}" if pd.notnull(row['gehalt']) else "0.00"
        bruttolohn = f"{float(row['Bruttolohn (€)']):.2f}" if pd.notnull(row['Bruttolohn (€)']) else "0.00"
        table_html += f"<tr><td><strong>{voller_name}</strong></td><td>{rolle}</td><td>{gesamtstunden}</td><td>{gehalt}</td><td>{bruttolohn}</td></tr>"
    table_html += "</tbody></table></div>"
    st.markdown(table_html, unsafe_allow_html=True)
    if "lohnabrechnung_zeilen" not in st.session_state:
        st.session_state.lohnabrechnung_zeilen = [
            {"mitarbeiter": "", "betrag_typ": "berechnet", "betrag": 0.0, "sachleistungen": [], "sachwerte": {}, "ueberstunden": 0.0, "praemien": 0.0, "krankheitstage": 0,}
        ]
    st.subheader("Lohnübersicht erfassen")
    col_add, col_remove = st.columns([1,1])
    with col_add:
        if st.button("+ Zeile hinzufügen"):
            st.session_state.lohnabrechnung_zeilen.append({"mitarbeiter": "", "betrag_typ": "berechnet", "betrag": 0.0, "sachleistungen": [], "sachwerte": {}, "ueberstunden": 0.0, "praemien": 0.0, "krankheitstage": 0, "neuanfaenger": False, "abbrecher": False, "unbezahlter_urlaub": 0})
    with col_remove:
        if st.button("- Zeile entfernen") and len(st.session_state.lohnabrechnung_zeilen) > 1:
            st.session_state.lohnabrechnung_zeilen.pop()
    for idx, zeile in enumerate(st.session_state.lohnabrechnung_zeilen):
        st.markdown(f"<div style='border:2px solid #0078D4; border-radius:8px; padding:16px; margin-bottom:20px; background:var(--box-bg)'><h4>Lohnübersicht Zeile {idx+1}</h4></div>", unsafe_allow_html=True)
        zeile["mitarbeiter"] = st.selectbox("Mitarbeiter", ["-"] + mitarbeiter_liste, index=mitarbeiter_liste.index(zeile["mitarbeiter"]) if zeile["mitarbeiter"] in mitarbeiter_liste else 0, key=f"mitarbeiter_{idx}")
        zeile["betrag_typ"] = st.selectbox("Betragstyp", ["berechnet", "manuell"], index=["berechnet", "manuell"].index(zeile["betrag_typ"]), key=f"betragtyp_{idx}")
        # Automatische Berechnung des Betrags
        if zeile["mitarbeiter"] != "-":
            benutzer = benutzer_map.get(zeile["mitarbeiter"], "")
            rolle = df_mitarbeiter[df_mitarbeiter["benutzername"] == benutzer]["rolle"].iloc[0] if benutzer else "-"
            gesamtstunden = df_stunden[df_stunden["benutzername"] == benutzer]["gesamtstunden"].iloc[0] if benutzer in df_stunden["benutzername"].values else 0.0
            gehalt = df_gehalt[df_gehalt["rolle"] == rolle]["gehalt"].iloc[0] if rolle in df_gehalt["rolle"].values else 0.0
            berechnet = float(gesamtstunden) * float(gehalt)
        else:
            berechnet = 0.0
        if zeile["betrag_typ"] == "berechnet":
            zeile["betrag"] = berechnet
            st.markdown(f"<b>Betrag (€):</b> <span style='color:#0078D4;font-weight:bold'>{berechnet:.2f} €</span>", unsafe_allow_html=True)
        else:
            zeile["betrag"] = st.number_input("Betrag (€)", min_value=0.0, value=zeile["betrag"], key=f"betrag_{idx}")
        sachleistungen = ["Geschäftswagen", "Handy", "Laptop", "Essensgutscheine", "Sonstiges"]
        zeile["sachleistungen"] = st.multiselect("Sachleistungen", sachleistungen, default=zeile.get("sachleistungen", []), key=f"sach_{idx}")
        # Sachleistungswerte
        if "sachwerte" not in zeile:
            zeile["sachwerte"] = {}
        for sach in zeile["sachleistungen"]:
            zeile["sachwerte"][sach] = st.number_input(f"Wert für {sach} (€)", min_value=0.0, value=zeile["sachwerte"].get(sach, 0.0), key=f"sachwert_{idx}_{sach}")
        zeile["ueberstunden"] = st.number_input("Überstunden (h)", min_value=0.0, value=zeile["ueberstunden"], key=f"ueberstunden_{idx}")
        zeile["praemien"] = st.number_input("Prämien (€)", min_value=0.0, value=zeile["praemien"], key=f"praemien_{idx}")
        zeile["krankheitstage"] = st.number_input("Krankheitstage", min_value=0, value=zeile["krankheitstage"], key=f"krank_{idx}")
        # Daten für PDF-Export initialisieren
    df_mitarbeiter = pd.read_sql("SELECT benutzername, vorname, nachname, rolle FROM mitarbeiter", engine)
    df_stunden_pdf = pd.read_sql(
    "SELECT benutzername, SUM(stunden) as gesamtstunden FROM arbeitszeiten WHERE TO_CHAR(datum, 'MM') = %s AND TO_CHAR(datum, 'YYYY') = %s GROUP BY benutzername",
    engine, params=(monat_str, jahr_str)
    )
    df_gehalt = pd.read_sql("SELECT rolle, gehalt FROM standardgehaelter", engine)
    df_mitarbeiter["voller_name"] = df_mitarbeiter["vorname"] + " " + df_mitarbeiter["nachname"]
    benutzer_map = dict(zip(df_mitarbeiter["voller_name"], df_mitarbeiter["benutzername"]))
    # PDF-Export Button ganz unten
    st.markdown("---")
    if st.button("📥 Lohnübersicht als PDF exportieren"):
        # Filtere auch für PDF die Daten nach Monat/Jahr
        df_stunden_pdf = pd.read_sql(
            "SELECT benutzername, SUM(stunden) as gesamtstunden FROM arbeitszeiten WHERE TO_CHAR(datum, 'MM') = %s AND TO_CHAR(datum, 'YYYY') = %s GROUP BY benutzername",
            engine, params=(monat_str, jahr_str)
        )
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50
        # Firmenname groß
        firmenname = st.session_state.get("firmenname", "")
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, firmenname)
        y -= 22
        # Lohnabrechnung Monat/Jahr
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, f"Lohn Übersicht: {calendar.month_name[monat]} {jahr}")
        y -= 18
        # Tabellenkopf
        c.setFont("Helvetica-Bold", 8)
        x_pos = [30, 140, 190, 250, 340, 410, 500, 560]
        headers = ["Mitarbeiter (Rolle)", "Grundlohn", "Überstunden", "Überstunden-Prämie", "Krankheitstage", "Sachbezüge", "Gesamt-Brutto"]
        for i, header in enumerate(headers):
            c.drawString(x_pos[i], y, header)
        # Horizontale Linie unter Kopf
        y_line = y - 2
        c.setLineWidth(0.5)
        c.line(x_pos[0], y_line, x_pos[-1], y_line)
        y -= 12
        c.setFont("Helvetica", 7)
        payroll_total = 0.0
        for idx, zeile in enumerate(st.session_state.lohnabrechnung_zeilen):
            benutzer = benutzer_map.get(zeile['mitarbeiter'], '')
            rolle = df_mitarbeiter[df_mitarbeiter['benutzername'] == benutzer]['rolle'].iloc[0] if benutzer in df_mitarbeiter['benutzername'].values else "-"
            gesamtstunden = df_stunden_pdf[df_stunden_pdf['benutzername'] == benutzer]['gesamtstunden'].iloc[0] if benutzer in df_stunden_pdf['benutzername'].values else 0.0
            gehalt = df_gehalt[df_gehalt['rolle'] == rolle]['gehalt'].iloc[0] if rolle in df_gehalt['rolle'].values else 0.0
            grundlohn = float(gesamtstunden) * float(gehalt) if zeile["betrag_typ"] == "berechnet" else zeile["betrag"]
            grundlohn_str = f"{grundlohn:,.2f} €".replace(",", ".")
            ueberstunden = zeile.get("ueberstunden", 0.0)
            ueberstunden_str = f"{ueberstunden:.0f} Std." if ueberstunden else "0"
            praemie = zeile.get("praemien", 0.0)
            praemie_str = f"{praemie:,.2f} €".replace(",", ".")
            krankheitstage = zeile.get("krankheitstage", 0)
            if zeile.get("sachleistungen"):
                sachbezuege = "\n".join([f"{s}: {zeile['sachwerte'].get(s,0):.2f} €" for s in zeile["sachleistungen"]])
            else:
                sachbezuege = "–"
            gesamt_brutto = grundlohn + praemie + sum(zeile['sachwerte'].values())
            payroll_total += gesamt_brutto
            gesamt_brutto_str = f"{gesamt_brutto:,.2f} €".replace(",", ".")
            mitarbeiter_rolle = f"{zeile['mitarbeiter']} ({rolle})"
            cell_padding = 4  # Abstand zu den vertikalen Linien
            # Sachbezüge ggf. mehrzeilig ausgeben
            max_lines = max(1, sachbezuege.count("\n") + 1)
            for line_idx in range(max_lines):
                row_values = []
                for i, val in enumerate([mitarbeiter_rolle, grundlohn_str, ueberstunden_str, praemie_str, str(krankheitstage), sachbezuege, gesamt_brutto_str]):
                    if i == 5:  # Sachbezüge
                        sach_lines = sachbezuege.split("\n") if sachbezuege != "–" else ["–"]
                        val = sach_lines[line_idx] if line_idx < len(sach_lines) else ""
                    elif line_idx > 0:
                        val = ""
                    row_values.append(val)
                for i, val in enumerate(row_values):
                    c.drawString(x_pos[i] + cell_padding, y, val)
                # Vertikale Linien
                c.setLineWidth(0.3)
                for x in x_pos:
                    c.line(x, y+8, x, y-2)
                y -= 10
                if y < 60:
                    c.showPage()
                    y = height - 50
            # Nach jedem Mitarbeiter: dünne horizontale Linie
            c.setLineWidth(0.2)
            c.line(x_pos[0], y+4, x_pos[-1], y+4)
            y -= 10
        c.save()
        buffer.seek(0)
        # Save PDF to lohnabrechnung_archiv
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO lohnabrechnung_archiv (jahr, monat, benutzername, erstellt_am, pdf_data)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (jahr, monat, st.session_state.get("user", ""), datetime.now().isoformat(), buffer.getvalue())
            )
            # Speichere/Upsert die Lohn-Ausgabe zusätzlich in ausgaben_lohn (wird im Dashboard als Ausgabe addiert)
            try:
                existing = conn.exec_driver_sql(
                    "SELECT id FROM ausgaben_lohn WHERE benutzername = %s AND jahr = %s AND monat = %s",
                    (st.session_state.get("user", ""), jahr, monat)
                ).fetchone()
                if existing:
                    conn.exec_driver_sql(
                        "UPDATE ausgaben_lohn SET betrag = %s, erstellt_am = %s WHERE id = %s",
                        (float(payroll_total), datetime.now().isoformat(), existing[0])
                    )
                else:
                    conn.exec_driver_sql(
                        "INSERT INTO ausgaben_lohn (benutzername, jahr, monat, betrag, erstellt_am) VALUES (%s, %s, %s, %s, %s)",
                        (st.session_state.get("user", ""), jahr, monat, float(payroll_total), datetime.now().isoformat())
                    )
            except Exception:
                pass
        # Inform user about stored payroll expense
        st.success(f"Lohnübersicht exportiert. Lohn-Summe {payroll_total:,.2f} € wurde als Ausgaben-Lohn gespeichert.")
        st.download_button("PDF herunterladen", buffer, file_name=f"Lohnübersicht_{jahr}_{monat}.pdf", mime="application/pdf")
    st.markdown("---")
def start_app():
    import webbrowser
    import threading
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8501")).start()
    os.system("streamlit run " + sys.argv[0])
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
def sync_materialien():
    projekte = pd.read_sql("SELECT id FROM projekte", engine)
    materialien = pd.read_sql("SELECT material, einheit FROM lagerbestand", engine)
    for _, projekt in projekte.iterrows():
        for _, mat_row in materialien.iterrows():
            with engine.begin() as conn:
                try:
                    conn.exec_driver_sql("""
                        INSERT INTO materialien (projekt_id, material, menge, benutzername, einheit)
                        VALUES (%s, %s, 0, %s, %s)
                    """, (int(projekt["id"]), mat_row["material"], st.session_state.user, mat_row["einheit"]))
                except:
                    # Material already exists for this project, skip
                    pass
def ensure_projekte_has_id():
    """
    Falls eine alte projekte-Tabelle ohne 'id' existiert, migriere die Daten.
    Diese Funktion ist für PostgreSQL nicht nötig, da ensure_schema() alles automatisch erstellt.
    """
    # PostgreSQL: Migration is handled by ensure_schema()
    pass

# Rufe Migration einmal beim Start auf (DISABLED - PostgreSQL Migration ist via ensure_schema())
# ensure_projekte_has_id()
ROLLEN = [ "-",
    "Abbrucharbeiter", "Abrechner (Bau)", "Abteilungsleiter", "Anlagenmechaniker SHK", "Architekt",
    "Arbeitsvorbereiter", "Ausbilder (Handwerk)", "Auszubildender", "Bauaufseher (Bauüberwacher)",
    "Baucontroller", "Baugeräteführer", "Bauhelfer", "Bauhofleiter", "Bauingenieur", "Baukalkulator",
    "Baukaufmann/-frau", "Bauleiter", "Bauleitungsassistent", "Baulogistiker", "Baumaschinenführer",
    "Baustellenkoordinator", "Baustellenleiter", "Baustellenlogistiker", "Bauüberwacher", "Bauzeichner",
    "Betonbauer", "Betriebsleiter", "Betriebswirt (Bau)", "BIM-Koordinator", "BIM-Manager", "Bodenleger",
    "Buchhalter", "CAD-Zeichner", "Controller", "Dachdecker", "Disponent", "Einkäufer", "Elektriker",
    "Elektroniker für Energie- und Gebäudetechnik", "Elektrohelfer", "Elektromeister", "Energieberater",
    "Energieeffizienz-Experte", "Estrichleger", "Facility-Manager (Bau)", "Fliesenleger", "Fuhrparkleiter",
    "Gerüstbauer", "Geschäftsführer", "Geselle", "HR/Personalreferent", "IT-Administrator", "Kalkulator",
    "Kaufmännischer Leiter", "Klimatechniker", "Kranführer", "Kundendienstleiter", "Kundendienstmonteur",
    "Lagerist", "Leiter Einkauf", "Leiter Kalkulation", "LKW-Fahrer", "Maler und Lackierer", "Maschinist",
    "Maurer", "Meister", "Metallbauer", "Monteur", "Oberbauleiter", "Obermonteur", "Oberpolier",
    "Parkettleger", "Polier", "Praktikant", "Projektassistenz", "Projektcontroller", "Projektkaufmann/-frau",
    "Projektleiter", "Projektsteuerer (Bau)", "Prokurist", "Qualitätsbeauftragter", "Qualitätsmanager",
    "Rohrleitungsbauer", "Sanierungsfacharbeiter", "Sanitärmonteur", "Schlosser", "Schreiner/Tischler",
    "Servicetechniker", "SHK-Meister", "SiGeKo (Sicherheits- und Gesundheitsschutzkoordinator)",
    "Sicherheitsbeauftragter", "Statiker", "Straßenbauer", "Stuckateur", "Teamleiter", "Techniker",
    "TGA-Planer", "Tiefbaufacharbeiter", "Trockenbauer", "Umweltbeauftragter", "Vermessungstechniker",
    "Vorarbeiter", "Werkstudent", "Zimmerer"
]
EINHEITEN = ["stk", "m", "m²", "m³", "kg", "t", "l"]
wetter_optionen = [ "bedeckt", "bewölkt", "dunstig", "diesig", "eisig", "feucht", "frostig", "gewittrig", "grau", "hagelnd",
    "heiß", "klar", "kühl", "mild", "neblig", "nieselig", "nasskalt", "regnerisch", "schauerartig",
    "schneebedeckt", "schneefall", "schwül", "sonnig", "stark bewölkt", "stark windig", "starkregen",
    "stürmisch", "südwind", "tauend", "tiefdruck", "trüb", "trockenkalt", "tropisch", "unauffällig",
    "unbeständig", "unstet", "warm", "wechselhaft", "wehend", "windig", "wolkenlos", "wolkig", "zugig", "-"]
boden_optionen = ["ausgetrocknet", "bewachsen", "bewachsen mit Stoppeln", "blättrig", "bodenbedeckt (z.B. Mulch)",
    "bröckelig", "durchnässt", "eisig", "fest", "feucht", "frisch bearbeitet", "gefrozen", "grasbewachsen",
    "hart", "hartgefroren", "humos", "instabil", "klebrig", "kompakt", "krustig", "leicht feucht", "lehmig",
    "locker", "locker-krümelig", "mehlige", "mineralisch", "moosig", "matschig", "mit Reif bedeckt",
    "mit Unkraut bedeckt", "mit Wurzeln durchzogen", "nadlebedeckt", "nass", "organisch", "plastisch",
    "plastisch-klebrig", "pulvrig", "rissig", "rutschig", "sandig", "schmierig", "schneebedeckt", "sumpfig",
    "staubig", "steinig", "tonig", "torfig", "triefend", "trocken", "überschwemmt", "uneben", "vereist",
    "verdichtet", "weich", "wurzeldurchzogen", "-"
]
GGG = ["Gemietet", "Gekauft", "Geliehen"]
GESELLSCHAFTSFORMEN = [
    "Einzelunternehmen",
    "e.K.",
    "GbR",
    "OHG",
    "KG",
    "GmbH",
    "UG",
    "AG"
]

def save_bericht_daten_to_archive(benutzername, projekt_id, wetter="", boden="", arbeitsbericht="", mitarbeiter="", materialeinsatz="", geraeteeinsatz="", probleme="", todo="", checklisten_data="", erstellt_von_admin=0):
    """Speichere Bericht-DATEN (nicht PDF) in der Datenbank"""
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    
    debug_log = []
    debug_log.append(f"{'='*80}")
    debug_log.append(f"DEBUG: save_bericht_daten_to_archive() GESTARTET")
    debug_log.append(f"  Benutzer: {benutzername}")
    debug_log.append(f"  Projekt-ID: {projekt_id}")
    debug_log.append(f"  Datum: {today}")
    debug_log.append(f"  Daten-Größen: wetter={len(str(wetter))}, probleme={len(str(probleme))}, mitarbeiter={len(str(mitarbeiter))}")
    
    try:
        # Stelle sicher, dass die Tabelle existiert
        debug_log.append(f"  [1] Erstelle Tabelle...")
        with engine.begin() as conn:
            conn.exec_driver_sql("""
                CREATE TABLE IF NOT EXISTS bericht_daten_archive (
                    id SERIAL PRIMARY KEY,
                    benutzername TEXT,
                    projekt_id INTEGER,
                    datum TEXT,
                    wetter TEXT,
                    boden TEXT,
                    arbeitsbericht TEXT,
                    mitarbeiter TEXT,
                    materialeinsatz TEXT,
                    geraeteeinsatz TEXT,
                    probleme TEXT,
                    todo TEXT,
                    checklisten_data TEXT,
                    erstellt_von_admin INTEGER DEFAULT 0,
                    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(benutzername, projekt_id, datum)
                )
            """)
        debug_log.append(f"  [1] ✅ Tabelle OK")
        
        # Speichere die Daten
        debug_log.append(f"  [2] Speichere Daten...")
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO bericht_daten_archive (benutzername, projekt_id, datum, wetter, boden, arbeitsbericht, mitarbeiter, materialeinsatz, geraeteeinsatz, probleme, todo, checklisten_data, erstellt_von_admin, aktualisiert_am)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(benutzername, projekt_id, datum)
                DO UPDATE SET wetter = excluded.wetter, boden = excluded.boden, arbeitsbericht = excluded.arbeitsbericht, mitarbeiter = excluded.mitarbeiter, materialeinsatz = excluded.materialeinsatz, geraeteeinsatz = excluded.geraeteeinsatz, probleme = excluded.probleme, todo = excluded.todo, checklisten_data = excluded.checklisten_data, erstellt_von_admin = excluded.erstellt_von_admin, aktualisiert_am = CURRENT_TIMESTAMP
                """,
                (benutzername, projekt_id, today, wetter, boden, arbeitsbericht, mitarbeiter, materialeinsatz, geraeteeinsatz, probleme, todo, checklisten_data, erstellt_von_admin)
            )
        debug_log.append(f"  [2] ✅ INSERT/UPDATE erfolgreich!")
        debug_log.append(f"{'='*80}\n")
        
        # Drucke Debug-Logs in Konsole UND speichere für UI
        for line in debug_log:
            print(line)
        
        # Speichere Debug-Logs in Session für Anzeige
        if "archive_debug_logs" not in st.session_state:
            st.session_state.archive_debug_logs = []
        st.session_state.archive_debug_logs.append("\n".join(debug_log))
        
        return True
    except Exception as e:
        debug_log.append(f"  [ERROR] ❌ FEHLER beim Speichern!")
        debug_log.append(f"  Exception: {type(e).__name__}: {str(e)}")
        import traceback
        debug_log.append(traceback.format_exc())
        debug_log.append(f"{'='*80}\n")
        
        # Drucke in Konsole
        for line in debug_log:
            print(line)
        
        # Speichere in Session
        if "archive_debug_logs" not in st.session_state:
            st.session_state.archive_debug_logs = []
        st.session_state.archive_debug_logs.append("\n".join(debug_log))
        
        return False

def load_bericht_daten_from_archive(benutzername, projekt_id, datum):
    """Lade Bericht-DATEN aus der Datenbank"""
    try:
        result = pd.read_sql(
            "SELECT wetter, boden, arbeitsbericht, mitarbeiter, materialeinsatz, geraeteeinsatz, probleme, todo, checklisten_data FROM bericht_daten_archive WHERE benutzername = %s AND projekt_id = %s AND datum = %s",
            engine,
            params=(benutzername, projekt_id, datum)
        )
        if not result.empty:
            return result.iloc[0].to_dict()
        return None
    except Exception as e:
        return None

def save_pdf_to_archive(benutzername, projekt_id, pdf_bytes):
    """Speichere PDF-BLOB in der Datenbank (deprecated, nur für Rechnungen)"""
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO pdf_archive (benutzername, projekt_id, datum, pdf_blob, aktualisiert_am)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(benutzername, projekt_id, datum)
                DO UPDATE SET pdf_blob = excluded.pdf_blob, aktualisiert_am = CURRENT_TIMESTAMP
                """,
                (benutzername, projekt_id, today, pdf_bytes)
            )
        return True
    except Exception as e:
        return False

def load_pdf_from_archive(benutzername, projekt_id, datum):
    """Lade PDF-BLOB aus der Datenbank (deprecated)"""
    try:
        result = pd.read_sql(
            "SELECT pdf_blob FROM pdf_archive WHERE benutzername = %s AND projekt_id = %s AND datum = %s",
            engine,
            params=(benutzername, projekt_id, datum)
        )
        if not result.empty:
            pdf_data = result.iloc[0]["pdf_blob"]
            # Konvertiere memoryview zu bytes
            if isinstance(pdf_data, memoryview):
                return bytes(pdf_data)
            return pdf_data
        return None
    except Exception as e:
        return None

def auto_generate_pdfs_at_2355():
    """Um 23:55 Uhr: Speichere automatisch Bericht-DATEN für alle aktiven Projekte
    Diese Funktion läuft automatisch im Hintergrund
    ÄNDERUNG: Speichere nur Daten, kein PDF - PDF wird on-demand regeneriert
    """
    from datetime import date
    
    try:
        # Hole alle Benutzer mit aktiven Projekten
        active_projects = pd.read_sql(
            "SELECT DISTINCT bauunternehmer, id FROM projekte WHERE status = 'aktiv'",
            engine
        )
        
        for _, project in active_projects.iterrows():
            benutzername = project["bauunternehmer"]
            projekt_id = project["id"]
            
            try:
                # Hole die aktuellen Form-Daten aus Streamlit-Session (falls verfügbar)
                # Falls nicht in Session, speichere mit leeren Werten (Platzhalter)
                # Der Nutzer kann später manuell nachtragen
                
                # Placeholder-Daten: Benutzername und Projekt_ID als Marker
                save_bericht_daten_to_archive(
                    benutzername=benutzername,
                    projekt_id=projekt_id,
                    wetter="",
                    boden="",
                    arbeitsbericht="[Automatisch um 23:55 Uhr erstellt]",
                    mitarbeiter="",
                    materialeinsatz="",
                    geraeteeinsatz="",
                    probleme="",
                    todo="",
                    checklisten_data="",
                    erstellt_von_admin=1  # Admin-Flag zeigt automatische Generierung
                )
                
            except Exception as e:
                pass  # Fehler für einzelne Projekte nicht kritisch
                
    except Exception as e:
        pass  # Fehler beim Auto-Save nicht kritisch

# Scheduler für automatische PDF-Generierung
def init_pdf_scheduler():
    """Initialisiere APScheduler für automatische PDF-Generierung um 23:55 Uhr"""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        
        # Überprüfe, ob Scheduler schon läuft
        if not scheduler.running:
            scheduler.add_job(
                auto_generate_pdfs_at_2355,
                'cron',
                hour=23,
                minute=55,
                id='auto_pdf_generation',
                replace_existing=True
            )
            scheduler.start()
            return True
    except Exception as e:
        pass  # Scheduler-Fehler sind nicht kritisch
    return False

@st.cache_resource
def midnight_material_reset():
    """Um 0:00 Uhr: Addiere heutige Material-Eingaben zum Grundbestand und lösche tägliche Einträge"""
    from datetime import date, timedelta
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    try:
        # Stelle sicher, dass verbrauch Spalte existiert
        with engine.begin() as conn:
            try:
                conn.exec_driver_sql("ALTER TABLE materialien ADD COLUMN IF NOT EXISTS verbrauch DECIMAL(10, 2) DEFAULT 0")
            except:
                pass
        
        # Für alle Einträge von gestern: verbrauch += menge, dann DELETE
        with engine.begin() as conn:
            # Finde alle Material-Einträge von gestern
            gestern_eintraege = pd.read_sql(
                "SELECT projekt_id, material, benutzername, SUM(menge) as menge_summe FROM materialien WHERE datum = %s GROUP BY projekt_id, material, benutzername",
                engine, params=(str(yesterday),)
            )
            
            for _, row in gestern_eintraege.iterrows():
                projekt_id = row["projekt_id"]
                material = row["material"]
                benutzername = row["benutzername"]
                menge_summe = row["menge_summe"]
                
                # UPDATE: Addiere zur verbrauch
                conn.exec_driver_sql(
                    "UPDATE materialien SET verbrauch = verbrauch + %s WHERE projekt_id = %s AND material = %s AND benutzername = %s AND datum IS NULL",
                    (float(menge_summe), projekt_id, material, benutzername)
                )
            
            # DELETE alle Einträge von gestern
            conn.exec_driver_sql("DELETE FROM materialien WHERE datum = %s", (str(yesterday),))
    except Exception as e:
        pass  # Fehler ignorieren, Funktion ist optional

if __name__ == "__main__":
    # Initialisiere PDF-Scheduler für automatische Generierung um 23:55 Uhr
    init_pdf_scheduler()
    
    # Midnight Material Reset - einmal pro Session
    midnight_material_reset()
    
    # Check for payment return URL parameters
    if "subscription_id" in st.query_params or "token" in st.query_params:
        if "page" in st.query_params and st.query_params["page"][0] == "payment_success":
            st.session_state.page = "payment_success"
        elif "page" in st.query_params and st.query_params["page"][0] == "payment_cancel":
            st.session_state.page = "payment_cancel"
    
    # Initialize session state variables if not set
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "email" not in st.session_state:
        st.session_state.email = None
    if "user" not in st.session_state:
        st.session_state.user = None
    if "account_id" not in st.session_state:
        st.session_state.account_id = None
    if "nutzer_typ" not in st.session_state:
        st.session_state.nutzer_typ = None
    if "payment_status" not in st.session_state:
        st.session_state.payment_status = None
        
    # Route to appropriate page
    if st.session_state.get("page") == "login":
        login_page()
    elif st.session_state.get("page") == "agb_akzeptieren":
        agb_akzeptieren_page()
    elif st.session_state.get("page") == "setup_company_profile":
        setup_company_profile_page()
    elif st.session_state.get("page") == "setup_bank_register_data":
        setup_bank_register_data_page()
    elif st.session_state.get("page") == "app":
        bau_app_page()
    elif st.session_state.get("page") == "profil":
        profil_page()
    elif st.session_state.get("page") == "standardgehalt":
        standardgehalt_page()
    elif st.session_state.get("page") == "mitarbeiter":
        mitarbeiter_page()
    elif st.session_state.get("page") == "mitarbeiter_projekt_auswahl":
        mitarbeiter_projekt_auswahl_page()
    elif st.session_state.get("page") == "projekt_auswahl":  # Add project selection page routing
        projekt_auswahl_page()
    elif st.session_state.get("page") == "lohnabrechnung":
        lohnabrechnung_page()
    elif st.session_state.get("page") == "vorplanung":
        vorplanung_page()
    elif st.session_state.get("page") == "materialplanung":
        materialplanung_page()
    elif st.session_state.get("page") == "berichtarchiv":
        berichtarchiv_page()
    elif st.session_state.get("page") == "rechnungarchiv":
        rechnungarchiv_page()
    elif st.session_state.get("page") == "dev_auth":
        try:
            dev_auth_page()
        except NameError:
            st.error("Developer Auth Page nicht implementiert")
            st.session_state.page = "login"
            st.rerun()
    elif st.session_state.get("page") == "dev":
        dev_page()
    elif st.session_state.get("page") == "delete_account_password":
        delete_account_password_page()
    elif st.session_state.get("page") == "delete_account_confirm":
        delete_account_confirm_page()
    elif st.session_state.get("page") == "delete_account_survey":
        delete_account_survey_page()
    elif st.session_state.get("page") == "payment":
        payment_page()
    elif st.session_state.get("page") == "payment_success":
        st.success("Zahlung erfolgreich verarbeitet!")
        st.session_state.page = "bauunternehmer_dashboard"
        st.rerun()
    elif st.session_state.get("page") == "payment_cancel":
        st.warning("Zahlung wurde abgebrochen.")
        st.session_state.page = "bauunternehmer_dashboard"
        st.rerun()
    elif st.session_state.get("page") == "bauunternehmer_dashboard":
        bauunternehmer_dashboard()
    elif st.session_state.get("page") == "einstellungen":
        settings_page()
    elif st.session_state.get("page") == "theme_debug":
        # Forward to the central theme debug page defined in main.py (safe import)
        try:
            import main as _main
            _main.theme_debug_page()
        except Exception:
            # As a fallback, ensure the global router handles it
            st.session_state.page = "theme_debug"
            st.rerun()
    else:  # Default to login page if unknown state
        st.session_state.page = "login"
        st.rerun()
