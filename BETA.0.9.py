import os
from urllib.parse import quote
import time
from datetime import datetime, time as datetime_time, date, timedelta
from database import get_connection
from ui.login import (
    show_login_page,
    show_login_page,
    get_device_id,
    check_login_lockout,
    record_failed_login,
    reset_login_attempts,
    load_login_attempts,
    hash_password,
    verify_password,
    lade_firmendaten,
    upgrade_password_if_needed,
)
from database import(
engine,
ensure_schema,
)
from ui.pdf_generator import (
generate_pauschal_invoice_pdf,
generate_invoice_pdf_v2,
generate_report_pdf_from_data,
markdown_to_pdf,
)
from ui.paypal import (
    payment_page,
    get_paypal_access_token,
    get_paypal_plans,
    get_paypal_plan_details,
    clean_email,
    clean_paypal_id,
)
from ui.helpers import (
    lade_firmendaten,
    sync_materialien,
    get_projekt_name,
    get_all_mitarbeiter,
    get_mitarbeiter_by_project,
    get_materialien_for_project,
    load_agb,
    load_datenschutz,
    show_agb_with_scrollbar,
    show_datenschutz_with_scrollbar,
    ROLLEN, EINHEITEN, GESELLSCHAFTSFORMEN,
    wetter_optionen, boden_optionen, GGG,
)
from ui.archiv import (
    save_bericht_daten_to_archive,
    load_bericht_daten_from_archive,
    save_pdf_to_archive,
    load_pdf_from_archive,
    auto_generate_pdfs_at_2355,
    init_pdf_scheduler,
    berichtarchiv_page,
    rechnungarchiv_page,
)
from ui.setup import (
    check_firmenprofil_page,
    setup_company_profile_page,
    setup_bank_register_data_page,
    firmenprofil_vollstaendig,
    bankdaten_vollstaendig,
)
from ui.utils import (
    check_access,
    show_tutorial,
    cleanup_expired_test_accounts,
    midnight_material_reset,
    start_app,
    safe_secure_ki_prognose,
)
from pages.agb import agb_akzeptieren_page
from pages.mitarbeiter_auswahl import mitarbeiter_projekt_auswahl_page
from pages.mitarbeiter_page import mitarbeiter_page
from pages.dev import dev_auth_page, dev_test_accounts_page, dev_page
from pages.delete_account import (
    delete_account_password_page,
    delete_account_confirm_page,
    delete_account_survey_page,
)
from pages.projekt_auswahl import projekt_auswahl_page
from pages.fortschritt_page import fortschritt_page
from pages.standardgehalt import standardgehalt_page
from pages.materialplanung import materialplanung_page
from pages.materialuebersicht import materialuebersicht_page
from pages.geraeteuebersicht import geraeteuebersicht_page
from pages.neues_projekt import neues_projekt_page
from pages.vorplanung import vorplanung_page
from pages.profil import profil_page
from pages.settings import settings_page
from pages.lohnabrechnung import lohnabrechnung_page
from pages.projektuebersicht import projektuebersicht_page
from pages.rechnungen import rechnungs_page
from pages.mitarbeiterverwaltung import mitarbeiterverwaltung_page
from pages.projekt_checklisten import projekt_checklisten_page
#from pages.bau_app_page import bau_app_page
# Absolute Pfad für Backups (falls benötigt)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))



# ============================================
# Test Account Auto-Cleanup
# ============================================

def cleanup_expired_test_accounts():
    """Löscht Test-Konten die abgelaufen sind"""
    try:
        with engine.begin() as conn:
            # Finde alle abgelaufenen Test-Konten
            result = conn.exec_driver_sql(
                """SELECT benutzername FROM benutzer 
                   WHERE is_test_account = TRUE 
                   AND test_expiration_time IS NOT NULL 
                   AND test_expiration_time < CURRENT_TIMESTAMP"""
            )
            expired_accounts = [row[0] for row in result.fetchall()]
            
            if expired_accounts:
                # Lösche abgelaufene Test-Konten
                for username in expired_accounts:
                    try:
                        # Lösche zunächst alle zugehörigen Daten (Projekte, etc.)
                        conn.exec_driver_sql("DELETE FROM projekte WHERE benutzername = %s", (username,))
                        conn.exec_driver_sql("DELETE FROM rechnungen WHERE benutzername = %s", (username,))
                        conn.exec_driver_sql("DELETE FROM mitarbeiter WHERE benutzername = %s", (username,))
                        conn.exec_driver_sql("DELETE FROM mitarbeiter_projekte WHERE mitarbeiter_benutzername = %s", (username,))
                        # Lösche den Benutzer selbst
                        conn.exec_driver_sql("DELETE FROM benutzer WHERE benutzername = %s", (username,))
                        print(f"✅ Test-Konto '{username}' gelöscht (abgelaufen)")
                    except Exception as e:
                        print(f"⚠️ Fehler beim Löschen von '{username}': {str(e)}")
    except Exception as e:
        print(f"⚠️ Fehler beim Cleanup von Test-Konten: {str(e)}")


def show_tutorial(username):
    """Zeigt ein interaktives Tutorial für neue Nutzer - unterscheidet zwischen Bauunternehmer und Mitarbeiter."""
    import streamlit as st
    import pandas as pd
    
    # Bauunternehmer Tutorial
    bauunternehmer_tutorial = {
        "📋 Projekte": {
            "Projekt anlegen": {
                "beschreibung": "Erstelle ein neues Projekt mit Budget und Rechnungsnummer.",
                "details": [
                    "• Gib einen aussagekräftigen Projektnamen ein",
                    "• Lege das Budget fest (mindestens €1000)",
                    "• Die Rechnungsnummer wird automatisch vergeben (kann angepasst werden)",
                    "• Alle Materialien aus deinem Lager werden automatisch hinzugefügt"
                ]
            },
            "Projektübersicht": {
                "beschreibung": "Übersicht aller aktiven und abgeschlossenen Projekte.",
                "details": [
                    "• Sieh den Status und Fortschritt aller Projekte",
                    "• Bearbeite oder archiviere Projekte",
                    "• Überblick über Kosten und Mitarbeiterzahl pro Projekt",
                    "• Visualisiere Ausgaben vs. Budget",
                    "• Sehe Material- und Arbeitsaufwand",
                ]
            },
            "Fortschritt": {
                "beschreibung": "Verfolge den Fortschritt deiner Projekte.",
                "details": [
                    "• Sieh tägliche Berichte über Probleme oder Engpässe",
                    "• Schneller Zugriff auf Projektdetails",
                    "• Erstelle tägliche Berichte und Dokumentationen",
                ]
            },
            "Projekt-Checklisten": {
                "beschreibung": "Erstelle Checklisten für deine Projekte.",
                "details": [
                    "• Definiere Meilensteine und Aufgaben",
                    "• Stelle sicher, dass nichts vergessen wird"
                ]
            },
            "Vorplanungs-Kalender": {
                "beschreibung": "Planen zukünftige Einsätze und Ressourcen.",
                "details": [
                    "• Koordiniere Geräteverfügbarkeit mit deinem Team",
                    "• Visualisiere zeitliche Auslastung von Geräten",
                    "• Vermeide Terminüberschneidungen"
                ]
            }
        },
        "🔧 Ressourcen": {
            "Material": {
                "beschreibung": "Verwalte dein Material-Lagerbestand.",
                "details": [
                    "• Füge neue Materialien ein oder änderst bestehende",
                    "• Verwalte Lagerbestände und Einheiten",
                    "• Verfolge Ankaufs- und Verkaufspreise",
                    "• Sehe automatisch Material-Verbrauch pro Projekt"
                ]
            },
            "Geräte": {
                "beschreibung": "Leite deine Geräte und Maschinen.",
                "details": [
                    "• Erfasse neue Geräte mit Kauf- und Marktwert",
                    "• Verbinde Geräte mit Projekten",
                    "• Verfolgung der Geräteauslastung",
                    "• Dokumentiere und Einsatzzeiten"
                ]
            },
            "Material-Planung": {
                "beschreibung": "Plane den Materialeinsatz für kommende Phasen.",
                "details": [
                    "• Erstelle Material-Bestellungen",
                    "• Koordiniere Materiallieferungen",
                    "• Vermeidung von Engpässen und Überbeständen"
                ]
            }
        },
        "👥 Team": {
            "Mitarbeiter": {
                "beschreibung": "Verwalte dein Team und weise sie Projekten zu.",
                "details": [
                    "• Füge neue Mitarbeiter hinzu und definiere Rollen",
                    "• Weise Mitarbeiter Projekten zu",
                    "• Verfolge Mitarbeiterzugehörigkeiten",
                    "• Behalte den Überblick über dein Team"
                ]
            },
            "Löhne": {
                "beschreibung": "Verwalte Löhne und Gehälter deiner Mitarbeiter.",
                "details": [
                    "• Verfolge monatliche Lohn-Ausgaben",
                    "• Passe Zahlungen an Projekte an",
                    "• Finanzielle Kontrolle über Personalkosten",
                    "• Tipp: Passe Standrtgehälter im Profil an, damit sie automatisch in Rechnungen und Budgetanalysen einbezogen werden"
                ]
            }
        },
        "💰 Finanzen": {
            "Rechnungen": {
                "beschreibung": "Erstelle und verwalte Rechnungen für Projekte.",
                "details": [
                    "• Automatische Rechnungserstellung",
                    "• Basis auf tatsächlichen Material- und Lohnkosten",
                    "• PDF-Export für deine Kunden",
                    "• Volle Nachverfolgung aller Facturierungen",
                    "• Alle Rechnungen werden im Archiv automatisch bei der Archivierung von Projekten gespeichert"
                ]
            },
            "Budget": {
                "beschreibung": "KI-gestützte Budget-Prognose und finanzielle Analyse.",
                "details": [
                    "• Intelligente Vorhersage von Budgetverbrauch",
                    "• Vergleich mit historischen Daten",
                ]
            },
            "Dashboard": {
                "beschreibung": "Zentrale Übersicht aller wichtigen Kennzahlen.",
                "details": [
                    "• Aktuelle Finanzlage auf einen Blick",
                    "• Wichtige Metriken und KPIs",
                    "• Schnelleinstieg in alle Funktionen"
                ]
            }
        },
        "📂Archiv": {
            "Projekt-Archiv": {
                "beschreibung": "Speichere und verwalte archivierte Projekte.",
                "details": [
                    "• Alle archivierten Projekte werden zentral gespeichert",
                    "• Einfache Suche und Filterung nach Projektattributen",
                    "• Vollständige Dokumentation aller Projektphasen",
                    "• Zugriff auf alle Berichte, Rechnungen und Materialien vergangener Projekte",
                    "• Alle Daten bleiben sicher gespeichert, auch wenn Projekte archiviert sind",
                    "• Der Zugriff erfolgt über das Profil, damit die Übersicht über aktive Projekte nicht beeinträchtigt wird"
                ]
            }
        }

    }
    
    # Mitarbeiter Tutorial
    mitarbeiter_tutorial = {
        "📝 Eingaben": {
            "Arbeitsbericht": {
                "beschreibung": "Dokumentiere tägliche Arbeitsfortschritte und Einsätze.",
                "details": [
                    "• Schreibe einen Bericht über deine heutigen Tätigkeiten",
                    "• Dokumentiere Wetterbedingungen und Bodenzustände",
                    "• Notiere eingesetzte Materialien und Geräte",
                    "• Berichte über Probleme oder Hindernisse auf der Baustelle"
                ]
            },
            "Material-Verbrauch": {
                "beschreibung": "Erfasse verbrauchte Materialien während des Einsatzes.",
                "details": [
                    "• Gib die Art und Menge des verwendeten Materials ein",
                    "• Dokumentiere die Uhrzeit des Verbrauchs",
                    "• Notiere besondere Umstände (Verschwendung, etc.)",
                    "• Alle Daten werden für Rechnungen und Analysen verwendet"
                ]
            },
            "Geräte-Einsatz": {
                "beschreibung": "Dokumentiere verwendete Geräte und Maschinen.",
                "details": [
                    "• Erfasse welche Geräte du heute eingesetzt hast",
                    "• Notiere Einsatzeiten (von/bis)",
                    "• Dokumentiere technische Probleme oder Beschädigungen",
                    "• Daten helfen deinem Chef die Auslastung zu optimieren"
                ]
            }
        },
        "📅 Vorplanung": {
            "Vorplanungs-Kalender": {
                "beschreibung": "Sieh geplante Einsätze und blockierte Termine im Überblick.",
                "details": [
                    "• Überblick über zukünftige Gerätenutzung",
                    "• Koordination mit Kolleginnen und Kollegen"
                ]
            }
        },
        "🛒 Bestellungen": {
            "Material-Bestellung": {
                "beschreibung": "Beantrage fehlende Materialien für Projekte.",
                "details": [
                    "• Stelle Anforderungen für benötigte Materialien",
                    "• Gib Menge und gewünschte Bestellung an",

                ]
            },
        },
        "🔄 Navigation": {
            "Projekt-Wechsel": {
                "beschreibung": "Wechsle zwischen verschiedenen zugewiesenen Projekten.",
                "details": [
                    "• Im Profil findest du deine Projekte",
                    "• Klicke auf ein Projekt um die Ansicht zu wechseln",
                    "• Alle deine Eingaben werden zum aktuellen Projekt gespeichert",
                    "• Dein Chef hat Überblick über alle Einsätze pro Projekt"
                ]
            }
        }
    }
    
    # Wähle das richtige Tutorial basierend auf nutzer_typ
    if st.session_state.get("nutzer_typ") == "mitarbeiter":
        tutorial_categories = mitarbeiter_tutorial
        beispiel_text = "👉 **Hinweis:** Alle deine Eingaben werden dokumentiert und dein Chef kann sie in der Projektverwaltung einsehen."
    else:
        tutorial_categories = bauunternehmer_tutorial
        beispiel_text = ""  # Kein Hinweis für Bauunternehmer nötig
    
    # Tutorial UI
    st.markdown("---")
    st.title("🎓 Willkommen zum Tutorial!")
    st.markdown("""
    Hallo! 👋 Schön, dass du hier bist! 
    
    Dieses Tutorial zeigt dir alle Funktionen der Software. Du kannst es jederzeit schließen.
    """)
    
    # Tutorial-Spalten
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📂 Kategorien")
        selected_category = st.radio("Wähle eine Kategorie:", list(tutorial_categories.keys()), key="tutorial_category")
    
    with col2:
        st.subheader("📌 Features")
        category_features = tutorial_categories[selected_category]
        selected_feature = st.radio("Wähle ein Feature:", list(category_features.keys()), key="tutorial_feature")
        
        # Zeige ausführliche Details
        feature_info = category_features[selected_feature]
        st.subheader(f"ℹ️ {selected_feature}")
        st.write(f"**{feature_info['beschreibung']}**")
        st.markdown("**So funktioniert's:**")
        for detail in feature_info['details']:
            st.write(detail)
    
    st.markdown("---")
    st.write(beispiel_text)
    st.markdown("---")
    
    # Abschluss des Tutorials
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("✅ Tutorial abschließen", use_container_width=True):
            # Setze tutorial_completed Flag je nach Benutzertyp
            with engine.begin() as conn:
                if st.session_state.get("nutzer_typ") == "mitarbeiter":
                    conn.exec_driver_sql(
                        "UPDATE mitarbeiter SET tutorial_completed = TRUE WHERE benutzername = %s",
                        (username,)
                    )
                else:
                    conn.exec_driver_sql(
                        "UPDATE benutzer SET tutorial_completed = TRUE WHERE benutzername = %s",
                        (username,)
                    )
            st.success("Tutorial abgeschlossen! Weiterleitung zur Anwendung...")
            st.balloons()
            time.sleep(1)
            st.session_state.page = "app"
            st.rerun()
    
    with col3:
        if st.button("⏭️ Überspringen", use_container_width=True):
            # Überspringe das Tutorial
            with engine.begin() as conn:
                if st.session_state.get("nutzer_typ") == "mitarbeiter":
                    conn.exec_driver_sql(
                        "UPDATE mitarbeiter SET tutorial_completed = TRUE WHERE benutzername = %s",
                        (username,)
                    )
                else:
                    conn.exec_driver_sql(
                        "UPDATE benutzer SET tutorial_completed = TRUE WHERE benutzername = %s",
                        (username,)
                    )
            st.info("Tutorial übersprungen. Weiterleitung zur Anwendung...")
            time.sleep(1)
            st.session_state.page = "app"
            st.rerun()


def bauunternehmer_dashboard():
    import plotly.graph_objects as go
    import plotly.express as px
    from datetime import datetime, timedelta

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
                "SELECT geraet, datum, nutzungszeit FROM geraete_nutzung WHERE datum::date >= %s::date AND datum::date <= %s::date",
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
import requests
import re
import os
import subprocess
import sys
import pandas as pd
import plotly.express as px
import calendar
import sqlalchemy
# === Automatische Installation fehlender Pakete ===
from datetime import date, datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
import streamlit as st
from streamlit_option_menu import option_menu

from sklearn.linear_model import LinearRegression
from sqlalchemy import create_engine
from sqlalchemy import text
# from reportlab.lib.pagesizes import A4  # Already imported above
# from reportlab.pdfgen import canvas    # Already imported above
# from io import BytesIO                 # Already imported above


def bau_app_page():
    # Apply theme CSS at the beginning of every page render
    theme = st.session_state.get('theme', 'white')
    if theme == 'black':
        st.markdown("""
        <style>
            /* === HEADER/NAVBAR SCHWARZER MODUS === */
            [data-testid="stHeader"] {
                background-color: #1e1e1e !important;
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
        st.markdown("# butestix")
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
            if st.button("⚙️ Einstellungen", key="menu_settings", use_container_width=True):
                st.session_state["page"] = "einstellungen"
                st.session_state.menu_open = False
                st.rerun()
            
            # Profile Option
            if st.button("👥 Profil", key="menu_profile", use_container_width=True):
                st.session_state["page"] = "profil"
                st.session_state.menu_open = False
                st.rerun()
            
            # Logout Option
            if st.button("🚪 Logout", key="menu_logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.page = "login"
                st.rerun()
    st.markdown("---")
    
    # ===== TUTORIAL CHECK =====
    if st.session_state.get("user"):
        # Überprüfe ob Tutorial für diesen Nutzer abgeschlossen wurde (je nach Typ)
        with engine.begin() as conn:
            if st.session_state.get("nutzer_typ") == "mitarbeiter":
                # Überprüfe in mitarbeiter Tabelle
                result = conn.exec_driver_sql(
                    "SELECT tutorial_completed FROM mitarbeiter WHERE benutzername = %s",
                    (st.session_state.user,)
                )
            else:
                # Überprüfe in benutzer Tabelle (Bauunternehmer)
                result = conn.exec_driver_sql(
                    "SELECT tutorial_completed FROM benutzer WHERE benutzername = %s",
                    (st.session_state.user,)
                )
            row = result.fetchone()
            tutorial_completed = row[0] if row else False
        
        if not tutorial_completed:
            # Zeige Tutorial wenn noch nicht abgeschlossen
            show_tutorial(st.session_state.user)
            return  # Beende hier, damit nur Tutorial gezeigt wird
    
    # === Navigation auslesen ===
    with st.sidebar:
        if st.session_state.get("nutzer_typ") == "bauunternehmer":
            st.title("Navigation")
            
            # Kategorien und ihre Unterpunkte
            categories = {
                "📋 Projekte": [
                    "Projekt anlegen",
                    "Projektübersicht",
                    "Fortschritt",
                    "Projekt-Checklisten",

                ],
                "🔧 Ressourcen": [
                    "Material",
                    "Geräte",
                    "Material-Planung",
                    "Geräte-Vorplanungs-Kalender"
                ],
                "👥 Team": [
                    "Mitarbeiter",
                    "Löhne"
                ],
                "💰 Finanzen": [
                    "Rechnungen",
                    "Budget-Prognose",
                    "Dashboard"
                ]
            }
            
            # Wähle Kategorie
            selected_category = st.selectbox("Kategorie", list(categories.keys()), key="category_nav")
            
            # Wähle Unterpunkt
            selected_option = st.selectbox("Menü", categories[selected_category], key="menu_nav")
            
            # Mapping für interne Namen
            nav_mapping = {
                "Projekt anlegen": "Neues Projekt anlegen",
                "Projektübersicht": "Projektübersicht",
                "Fortschritt": "Fortschritt",
                "Material": "Materialübersicht",
                "Geräte": "Geräteübersicht",
                "Mitarbeiter": "Mitarbeiter",
                "Löhne": "Lohnübersicht",
                "Rechnungen": "Rechnung erstellen",
                "Budget": "Budget-KI-Prognose",
                "Projekt-Checklisten": "Projekt-Checklisten",
                "Geräte-Vorplanungs-Kalender": "Vorplanungs-Kalender",
                "Material-Planung": "Material-Planung",
                "Budget-Prognose": "Budget-KI-Prognose",
                "Dashboard": "Dashboard"
            }
            
            nav = nav_mapping.get(selected_option, selected_option)
        elif st.session_state.get("nutzer_typ") == "mitarbeiter":
            nav = "Mitarbeiterprojekt"  # Fixe Seite, kein Menü
        else:
            st.warning("Bitte zuerst einloggen.")
            st.stop()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# === Seite: Neues Projekt anlegen ===------------------------------------------------------------------------------------------------------------------------------------
    if nav == "Neues Projekt anlegen":
        neues_projekt_page()
# === Seite: Projektübersicht ===----------------------------------------------------------------------------------------------------------------------------------------
    elif nav == "Projektübersicht":
        projektuebersicht_page()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------    
    elif nav == "Vorplanungs-Kalender":
        vorplanung_page()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    elif nav == "Material-Planung":
        materialplanung_page()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
 # === Seite: Materialübersicht ===       
    elif nav == "Materialübersicht":
        materialuebersicht_page()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    elif nav == "Geräteübersicht":
        geraeteuebersicht_page()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------    
    elif nav == "Mitarbeiter":
        mitarbeiterverwaltung_page()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    elif nav == "Lohnübersicht":
        lohnabrechnung_page()
        st.set_page_config(page_title="Bauunternehmen App", layout="centered")
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
    elif nav == "Rechnung erstellen":
        rechnungs_page()
        st.set_page_config(page_title="Bauunternehmen App", layout="centered")
#---------------------------------------------------------------------------------------------------------------------------------------------------------------------
    elif nav == "Dashboard":
       bauunternehmer_dashboard()
       st.set_page_config(page_title="Bauunternehmen App", layout="centered")
# === Seite: Budget-KI-Prognose ===---------------------------------------------------------------------------------------------------------------------------------  
    elif nav == "Budget-KI-Prognose":
        st.header(" Budget-KI-Prognose")
        
        safe_secure_ki_prognose()
#---------------------------------------------------------------------------------------------------------------------------------------------------------------------    
    elif nav == "Projekt-Checklisten":
        projekt_checklisten_page()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------     
    elif nav == "Fortschritt":
        fortschritt_page()
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------       
    elif nav == "Mitarbeiterprojekt":
        mitarbeiter_page()
    st.caption("App-Version 0.1 – © DeineFirma 2025")
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------


def start_app():
    import webbrowser
    import threading
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8501")).start()
    os.system("streamlit run " + sys.argv[0])

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
    
    # Cleanup abgelaufene Test-Konten
    cleanup_expired_test_accounts()
    
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
        show_login_page()
    elif st.session_state.get("page") == "agb_akzeptieren":
        agb_akzeptieren_page()
    elif st.session_state.get("page") == "check_firmenprofil":
        check_firmenprofil_page()
    elif st.session_state.get("page") == "setup_company_profile":
        setup_company_profile_page()
    elif st.session_state.get("page") == "setup_bank_register":
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
    elif st.session_state.get("page") == "rechnung":
        rechnungs_page()
    elif st.session_state.get("page") == "material_uebersicht":
        materialuebersicht_page()
    elif st.session_state.get("page") == "vorplanung":
        vorplanung_page()
    elif st.session_state.get("page") == "materialplanung":
        materialplanung_page()
    elif st.session_state.get("page") == "berichtarchiv":
        berichtarchiv_page()
    elif st.session_state.get("page") == "rechnungarchiv":
        rechnungarchiv_page()
    elif st.session_state.get("page") == "neues_projekt":
        neues_projekt_page()
    elif st.session_state.get("page") == "projektuebersicht":
        projektuebersicht_page()
    elif st.session_state.get("page") == "geraeteuebersicht":
        geraeteuebersicht_page()   
    elif st.session_state.get("page") == "dev_auth":
        try:
            dev_auth_page()
        except NameError:
            st.error("Developer Auth Page nicht implementiert")
            st.session_state.page = "login"
            st.rerun()
    elif st.session_state.get("page") == "dev_page":
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
        # Überprüfe ob Tutorial für diesen Nutzer abgeschlossen wurde
        if st.session_state.get("user"):
            # Direkter DB-Zugriff ohne Cache
            with engine.begin() as conn:
                result = conn.exec_driver_sql(
                    "SELECT tutorial_completed FROM benutzer WHERE benutzername = %s",
                    (st.session_state.user,)
                )
                row = result.fetchone()
                tutorial_completed = row[0] if row else False
            
            if not tutorial_completed:
                # Zeige Tutorial wenn noch nicht abgeschlossen
                show_tutorial(st.session_state.user)
            else:
                # Zeige normales Dashboard
                bauunternehmer_dashboard()
        else:
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
