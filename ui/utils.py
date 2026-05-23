# ============================================================
#  utils.py  –  ETA Baumanagement
#  Allgemeine App-Hilfsfunktionen (Tutorial, Zugriffscheck)
#
#  Verwendung:
#      from ui.utils import show_tutorial, check_access
# ============================================================

import time
from datetime import datetime

import streamlit as st

from database import engine


def check_access() -> bool:
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
        st.session_state.last_access_check = datetime.now()
        st.session_state.has_access = True
        return True
    else:
        st.session_state.has_access = False
        st.session_state.last_access_check = datetime.now()
        st.error(f"Zugriff verweigert: Kein aktives Abonnement. Status: {payment_status}")
        time.sleep(2)
        st.session_state.page = "payment"
        st.rerun()
        st.stop()


def show_tutorial(username: str):
    """Zeigt ein interaktives Tutorial für neue Nutzer - unterscheidet zwischen Bauunternehmer und Mitarbeiter."""

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
                    "• Tipp: Passe Standardgehälter im Profil an, damit sie automatisch in Rechnungen und Budgetanalysen einbezogen werden"
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

    if st.session_state.get("nutzer_typ") == "mitarbeiter":
        tutorial_categories = mitarbeiter_tutorial
        beispiel_text = "👉 **Hinweis:** Alle deine Eingaben werden dokumentiert und dein Chef kann sie in der Projektverwaltung einsehen."
    else:
        tutorial_categories = bauunternehmer_tutorial
        beispiel_text = ""

    st.markdown("---")
    st.title("🎓 Willkommen zum Tutorial!")
    st.markdown("""
    Hallo! 👋 Schön, dass du hier bist!

    Dieses Tutorial zeigt dir alle Funktionen der Software. Du kannst es jederzeit schließen.
    """)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📂 Kategorien")
        selected_category = st.radio("Wähle eine Kategorie:", list(tutorial_categories.keys()), key="tutorial_category")

    with col2:
        st.subheader("📌 Features")
        category_features = tutorial_categories[selected_category]
        selected_feature = st.radio("Wähle ein Feature:", list(category_features.keys()), key="tutorial_feature")

        feature_info = category_features[selected_feature]
        st.subheader(f"ℹ️ {selected_feature}")
        st.write(f"**{feature_info['beschreibung']}**")
        st.markdown("**So funktioniert's:**")
        for detail in feature_info['details']:
            st.write(detail)

    st.markdown("---")
    st.write(beispiel_text)
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 1])

    def _mark_done():
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

    with col1:
        if st.button("✅ Tutorial abschließen", use_container_width=True):
            _mark_done()
            st.success("Tutorial abgeschlossen! Weiterleitung zur Anwendung...")
            st.balloons()
            time.sleep(1)
            st.session_state.page = "app"
            st.rerun()

    with col3:
        if st.button("⏭️ Überspringen", use_container_width=True):
            _mark_done()
            st.info("Tutorial übersprungen. Weiterleitung zur Anwendung...")
            time.sleep(1)
            st.session_state.page = "app"
            st.rerun()


# ============================================================
#  SCHEDULER / RESET-FUNKTIONEN
# ============================================================

def cleanup_expired_test_accounts():
    """Löscht Test-Konten die abgelaufen sind."""
    try:
        with engine.begin() as conn:
            result = conn.exec_driver_sql(
                """SELECT benutzername FROM benutzer
                   WHERE is_test_account = TRUE
                   AND test_expiration_time IS NOT NULL
                   AND test_expiration_time < CURRENT_TIMESTAMP"""
            )
            expired_accounts = [row[0] for row in result.fetchall()]

            if expired_accounts:
                for username in expired_accounts:
                    try:
                        conn.exec_driver_sql("DELETE FROM projekte WHERE benutzername = %s", (username,))
                        conn.exec_driver_sql("DELETE FROM rechnungen WHERE benutzername = %s", (username,))
                        conn.exec_driver_sql("DELETE FROM mitarbeiter WHERE benutzername = %s", (username,))
                        conn.exec_driver_sql("DELETE FROM mitarbeiter_projekte WHERE mitarbeiter_benutzername = %s", (username,))
                        conn.exec_driver_sql("DELETE FROM benutzer WHERE benutzername = %s", (username,))
                        print(f"✅ Test-Konto '{username}' gelöscht (abgelaufen)")
                    except Exception as e:
                        print(f"⚠️ Fehler beim Löschen von '{username}': {str(e)}")
    except Exception as e:
        print(f"⚠️ Fehler beim Cleanup von Test-Konten: {str(e)}")


def midnight_material_reset():
    """Um 0:00 Uhr: Addiere heutige Material-Eingaben zum Grundbestand und lösche tägliche Einträge."""
    import pandas as pd
    from datetime import date, timedelta
    today     = date.today()
    yesterday = today - timedelta(days=1)

    try:
        with engine.begin() as conn:
            try:
                conn.exec_driver_sql(
                    "ALTER TABLE materialien ADD COLUMN IF NOT EXISTS verbrauch DECIMAL(10, 2) DEFAULT 0"
                )
            except Exception:
                pass

        gestern_eintraege = pd.read_sql(
            """SELECT projekt_id, material, benutzername, SUM(menge) as menge_summe
               FROM materialien WHERE datum = %s
               GROUP BY projekt_id, material, benutzername""",
            engine, params=(str(yesterday),)
        )

        with engine.begin() as conn:
            for _, row in gestern_eintraege.iterrows():
                conn.exec_driver_sql(
                    """UPDATE materialien
                       SET verbrauch = verbrauch + %s
                       WHERE projekt_id = %s AND material = %s
                         AND benutzername = %s AND datum IS NULL""",
                    (float(row["menge_summe"]), row["projekt_id"],
                     row["material"], row["benutzername"])
                )
            conn.exec_driver_sql(
                "DELETE FROM materialien WHERE datum = %s", (str(yesterday),)
            )
    except Exception:
        pass  # Funktion ist optional


def start_app():
    """Startet die Streamlit-App und öffnet den Browser."""
    import os
    import sys
    import threading
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8501")).start()
    os.system("streamlit run " + sys.argv[0])


# ============================================================
#  KI-PROGNOSE
# ============================================================

def safe_secure_ki_prognose():
    """KI-gestützte Budget-Prognose mit scikit-learn (LinearRegression)."""
    import gc
    import pandas as pd

    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        st.error("scikit-learn nicht installiert. Bitte 'pip install scikit-learn' ausführen.")
        return

    try:
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

        # Rechnungskosten
        try:
            all_invoices = pd.read_sql(
                "SELECT projekt_id, SUM(nettobetrag) as total_kosten FROM rechnungen GROUP BY projekt_id",
                engine
            )
            invoice_dict = dict(zip(all_invoices['projekt_id'], all_invoices['total_kosten']))
            all_projects['rechnungskosten'] = all_projects['id'].map(invoice_dict).fillna(0)
        except Exception:
            all_projects['rechnungskosten'] = 0

        # Materialkosten
        try:
            all_materials = pd.read_sql(
                "SELECT projekt_id, COUNT(*) as material_count FROM materialplanung WHERE projekt_id IS NOT NULL GROUP BY projekt_id",
                engine
            )
            material_dict = dict(zip(all_materials['projekt_id'], all_materials['material_count']))
            all_projects['materialkosten_count'] = all_projects['id'].map(material_dict).fillna(0)
        except Exception:
            all_projects['materialkosten_count'] = 0

        # Geräte-Stunden
        try:
            geraete_hours = pd.read_sql(
                "SELECT projekt_id, SUM(CAST(nutzungszeit AS FLOAT)) as total_stunden FROM geraete_nutzung WHERE projekt_id IS NOT NULL GROUP BY projekt_id",
                engine
            )
            geraete_dict = dict(zip(geraete_hours['projekt_id'], geraete_hours['total_stunden']))
            all_projects['geraete_stunden'] = all_projects['id'].map(geraete_dict).fillna(0)
        except Exception:
            all_projects['geraete_stunden'] = 0

        # Feature Engineering
        max_mitarbeiter = all_projects['mitarbeiterzahl'].max() + 1
        max_geraete     = all_projects['geraete_stunden'].max() + 1
        max_investi     = (all_projects['rechnungskosten'] + all_projects['materialkosten_count']).max() + 1

        all_projects['komplexitaet'] = (
            (all_projects['mitarbeiterzahl'] / max_mitarbeiter) +
            (all_projects['geraete_stunden'] / max_geraete) +
            ((all_projects['rechnungskosten'] + all_projects['materialkosten_count']) / max_investi)
        ) / 3

        # Modell-Variante wählen
        st.markdown("---")
        st.subheader("KI-Modell-Konfiguration")

        feature_options = {
            "🔷 Basis":    ["dauer", "arbeiter"],
            "🔶 Erweitert":["dauer", "arbeiter", "materialkosten_count"],
            "🟠 Komplett": ["dauer", "arbeiter", "materialkosten_count", "rechnungskosten"],
            "🔴 Premium":  ["dauer", "arbeiter", "mitarbeiterzahl", "materialkosten_count",
                             "rechnungskosten", "geraete_stunden", "komplexitaet"],
        }

        selected_label = st.radio("Modell-Variante:", list(feature_options.keys()), key="secure_ki_features")
        features = feature_options[selected_label]

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
        st.subheader("Prognose-Parameter")

        col1, col2, col3 = st.columns(3)
        with col1:
            dauer_input    = st.slider("Dauer (Monate)", 1, 48, 12, key="secure_dauer")
            arbeiter_input = st.slider("Arbeiteranzahl", 1, 50, 3,  key="secure_arbeiter")
        with col2:
            materialkosten_input  = st.slider("Material-Einträge",  0, 500,    50,    key="secure_material")  if "materialkosten_count" in features else 0
            rechnungskosten_input = st.slider("Rechnungskosten (€)", 0, 500000, 50000, key="secure_rechnung")  if "rechnungskosten"       in features else 0
        with col3:
            mitarbeiterzahl_input  = st.slider("Mitarbeiterzahl",   1, 20,   3,   key="secure_mitarbeiter") if "mitarbeiterzahl"  in features else 0
            geraete_stunden_input  = st.slider("Geräte-Stunden",    0, 1000, 100, key="secure_geraete")     if "geraete_stunden" in features else 0

        komplexitaet_input = (
            (mitarbeiterzahl_input / max_mitarbeiter) +
            (geraete_stunden_input / max_geraete) +
            ((rechnungskosten_input + materialkosten_input) / max_investi)
        ) / 3 if "komplexitaet" in features else 0.5

        input_dict = {
            "dauer":               dauer_input,
            "arbeiter":            arbeiter_input,
            "mitarbeiterzahl":     mitarbeiterzahl_input,
            "materialkosten_count":materialkosten_input,
            "rechnungskosten":     rechnungskosten_input,
            "geraete_stunden":     geraete_stunden_input,
            "komplexitaet":        komplexitaet_input,
        }

        input_vector = [input_dict.get(f, 0) for f in features]
        input_scaled = scaler.transform([input_vector])
        prognose     = max(0, model.predict(input_scaled)[0])

        # Ausgabe
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"**Geschätztes Budget:** €{prognose:,.2f}")
        with col2:
            durchschnitt = df_train['budget'].mean()
            abweichung   = ((prognose - durchschnitt) / durchschnitt * 100) if durchschnitt > 0 else 0
            if abweichung > 0:
                st.info(f"+{abweichung:.1f}% vs. Durchschnitt")
            else:
                st.warning(f"{abweichung:.1f}% vs. Durchschnitt")

        with st.expander("Model-Details"):
            st.dataframe(pd.DataFrame({
                "Feature":     features,
                "Koeffizient": model.coef_,
                "Durchschnitt":[df_train[f].mean() for f in features],
                "Max":         [df_train[f].max()  for f in features],
            }).sort_values("Koeffizient", ascending=False, key=abs))
            st.write(f"**Intercept:** {model.intercept_:,.2f} | **R²:** {r2_score:.4f}")

        # Cleanup
        del scaler, model, X, y, df_train, all_projects
        gc.collect()

        st.success("Abgeschlossen.")
        st.info("Diese Prognose wurde NICHT gespeichert.")

    except Exception as e:
        st.error(f"KI-Fehler: {str(e)}")
