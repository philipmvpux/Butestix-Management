Butestix-Management

Eine Streamlit-Anwendung zur Verwaltung von Bauprojekten: Projekte, Rechnungen, Material, Geräte, Mitarbeiter, Zeiterfassung, Checklisten, Berichte und eine ML-gestützte Budget-Prognose. Datenhaltung über PostgreSQL, optionale Bezahlfunktion über PayPal-Abos.

Ursprünglich für den kommerziellen Vertrieb entwickelt, jetzt als Open-Source-Portfolio-Projekt veröffentlicht.

Features
Projektmanagement – Anlage, Budgetplanung, Kostenverfolgung, Archivierung
Rechnungsverwaltung – PDF-Rechnungen, automatische Nettobetrag-Berechnung, Rechnungsnummern mit Duplikatschutz
Materialbewirtschaftung – Lagerbestand, Mengenberechnung, An-/Verkaufspreise
Geräteverwaltung – Inventar, Nutzungsstunden, Kosten pro Gerät/Projekt
Mitarbeiterverwaltung – Rollen (Bauunternehmer / Mitarbeiter), Projektzuweisung
Zeiterfassung & Lohnabrechnung – pro Projekt/Mitarbeiter, mit Archivierung
Checklisten – projektspezifisch, mit Fortschrittsanzeige und Kommentaren
Budget-Prognose (ML) – Schätzung auf Basis historischer Projektdaten (scikit-learn)
Berichte – automatisierter PDF-Export
Bezahlfunktion (optional) – PayPal-Abo-Verwaltung, per Webhook synchronisiert
Tech-Stack
Python 3.11+, Streamlit
PostgreSQL (über psycopg2 + SQLAlchemy)
bcrypt für Passwort-Hashing
reportlab für PDF-Erzeugung, scikit-learn für die Budget-Prognose
Flask (separater PayPal-Webhook-Server)
Voraussetzungen
Python 3.11 oder neuer
PostgreSQL 14 oder neuer
Optional: PayPal-Developer-Account (nur falls ihr die Bezahlfunktion nutzen wollt)
1. Projekt einrichten
bash
git clone https://github.com/philipmvpux/butestix.git
cd butestix
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

Falls keine requirements.txt vorhanden ist, mindestens installieren: pip install streamlit psycopg2-binary sqlalchemy python-dotenv bcrypt requests flask reportlab pandas plotly scikit-learn streamlit-option-menu

2. PostgreSQL aufsetzen
2a. PostgreSQL installieren (falls noch nicht vorhanden)

Windows: Installer von postgresql.org/download/windows herunterladen und ausführen. Der Installer legt automatisch einen Superuser postgres an (Passwort während der Installation festlegen).

macOS:

bash
brew install postgresql@16
brew services start postgresql@16

Linux (Debian/Ubuntu):

bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
2b. Datenbank und Benutzer anlegen

In einem Terminal:

bash
# Als postgres-Systembenutzer einloggen (Linux/macOS):
sudo -u postgres psql

# Windows: einfach "psql" öffnen (aus dem Startmenü, "SQL Shell (psql)")

Dann in der psql-Shell:

sql
CREATE DATABASE eta_app;
CREATE USER eta_user WITH PASSWORD 'dein_sicheres_passwort';
GRANT ALL PRIVILEGES ON DATABASE eta_app TO eta_user;
\q

Das war's – die Anwendung legt beim ersten Start alle Tabellen automatisch an (siehe database.py, Funktion ensure_schema()). Ihr müsst kein Schema manuell einspielen.

2c. Verbindung testen (optional, aber empfohlen)
bash
psql -h localhost -U eta_user -d eta_app

Wenn ihr nach dem Passwort gefragt werdet und danach ein eta_app=>-Prompt seht, funktioniert die Verbindung.

3. .env konfigurieren

Im Projekt-Root liegt eine .env-Datei als Vorlage. Trage dort deine eigenen Werte ein:

ini
# --- Datenbank ---
DB_USER=eta_user
DB_PASSWORD=dein_sicheres_passwort
DB_HOST=localhost
DB_PORT=5432
DB_NAME=eta_app

# --- PayPal (nur nötig, wenn Bezahlfunktion aktiv ist) ---
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_API_BASE=https://api-m.sandbox.paypal.com
PAYPAL_BASE_URL=http://localhost:8501
PAYPAL_RETURN_URL=${PAYPAL_BASE_URL}?page=payment_success
PAYPAL_CANCEL_URL=${PAYPAL_BASE_URL}?page=payment_cancel

⚠️ Committet niemals eure echten Werte – nur die Platzhalter-Version gehört ins Repo.

4. PayPal-API-Keys besorgen (nur falls Bezahlfunktion gewünscht)

Für den reinen Privatgebrauch könnt ihr diesen Schritt komplett überspringen (siehe Abschnitt 6, "PayPal deaktivieren").

Auf developer.paypal.com mit eurem PayPal-Account einloggen (oder neuen anlegen)
Oben ins Dashboard → "Apps & Credentials"
Sicherstellen, dass oben "Sandbox" ausgewählt ist (nicht "Live") – zum Testen reicht Sandbox völlig aus, es fließt kein echtes Geld
Auf "Create App" klicken, einen Namen vergeben (z. B. "butestix-dev")
Ihr bekommt direkt eine Client ID und ein Secret angezeigt → beide in eure .env unter PAYPAL_CLIENT_ID und PAYPAL_CLIENT_SECRET eintragen
Für echte Zahlungen später: im selben Dashboard auf "Live" umschalten, dort eine eigene Live-App mit eigenen Keys anlegen, und PAYPAL_API_BASE in der .env auf https://api-m.paypal.com (ohne sandbox.) ändern

Webhook einrichten (damit Zahlungsstatus automatisch aktualisiert wird):

In der App-Konfiguration im PayPal-Dashboard auf "Add Webhook"
Als URL eure erreichbare Webhook-Adresse eintragen, z. B. https://eure-domain.de/webhook/paypal (lokal zum Testen könnt ihr ngrok nutzen, um localhost:5000 öffentlich erreichbar zu machen)
Events auswählen, mindestens: BILLING.SUBSCRIPTION.CREATED, BILLING.SUBSCRIPTION.PAYMENT.CAPTURED, BILLING.SUBSCRIPTION.PAYMENT.FAILED, BILLING.SUBSCRIPTION.CANCELLED, BILLING.SUBSCRIPTION.UPDATED
Den separaten Webhook-Server parallel zur App laufen lassen:
bash
   python paypal_webhook_handler.py

Läuft auf Port 5000 und schreibt Zahlungsstatus-Updates in die benutzer-Tabelle.

5. App starten
bash
streamlit run BETA_0_9.py

Die App öffnet sich automatisch unter http://localhost:8501.

Benötigte Ordnerstruktur (muss vollständig vorhanden sein, sonst ModuleNotFoundError):

database.py
BETA_0_9.py
ui/
  ├── login.py
  ├── pdf_generator.py
  ├── paypal.py
  ├── helpers.py
  ├── archiv.py
  ├── setup.py
  └── utils.py
pages/
  ├── agb.py
  ├── mitarbeiter_auswahl.py
  ├── mitarbeiter_page.py
  ├── dev.py
  ├── delete_account.py
  ├── projekt_auswahl.py
  ├── fortschritt_page.py
  ├── standardgehalt.py
  ├── materialplanung.py
  ├── materialuebersicht.py
  ├── geraeteuebersicht.py
  ├── neues_projekt.py
  ├── vorplanung.py
  ├── profil.py
  ├── settings.py
  ├── lohnabrechnung.py
  ├── projektuebersicht.py
  ├── rechnungen.py
  ├── mitarbeiterverwaltung.py
  └── projekt_checklisten.py
6. PayPal für private Nutzung deaktivieren

Wenn ihr die App nur für euch selbst nutzt (kein Kundengeschäft, kein Abo-Zwang):

Empfohlen – Feature-Flag statt Code löschen:

In der .env:

ini
PAYMENT_REQUIRED=false

Die entscheidende Stelle ist ui/login.py, Zeile 223:

python
if payment_status != "ACTIVE":
    st.session_state.page = "payment"
    ...

Ändert das zu:

python
import os
PAYMENT_REQUIRED = os.getenv("PAYMENT_REQUIRED", "true").lower() == "true"

if PAYMENT_REQUIRED and payment_status != "ACTIVE":
    st.session_state.page = "payment"
    ...

Mit PAYMENT_REQUIRED=false in der .env wird die Payment-Seite dann für niemanden mehr erzwungen.

Alternativ – hart entfernen:

paypal_webhook_handler.py löschen
In database.py die drei PAYPAL_*-Variablen und die tote get_connection()-Funktion (Zeile ~21) entfernen
ui/paypal.py komplett löschen (inkl. der ebenfalls toten, defekten get_connection()-Funktion darin) und den Import/Aufruf von payment_page() aus BETA_0_9.py entfernen
Datenmodell (Kurzüberblick)

Automatisch angelegt durch ensure_schema() in database.py:

Tabelle	Zweck
benutzer	Bauunternehmer-Konten, Login, Zahlungsstatus
mitarbeiter	Mitarbeiterkonten, Zuordnung zu Chef
projekte	Bauprojekte
rechnungen	Rechnungen inkl. PDF-Blob
firmenprofil	Firmendaten fürs Rechnungs-Impressum
geraete_lager / geraete_nutzung	Geräteverwaltung
materialplanung, lagerbestand	Materialwirtschaft
arbeitszeiten, ausgaben_lohn	Zeiterfassung & Lohn
checklistenpunkte u.a.	Projekt-Checklisten
payment_transactions, webhook_log	PayPal-Historie
Bekannte Einschränkungen
get_connection() in database.py und in ui/paypal.py ist aktuell ungenutzter Code mit einem Bug (übergibt PayPal-Parameter an psycopg2.connect(), was crasht) – die App nutzt stattdessen durchgängig die SQLAlchemy-Engine aus get_engine().
Passwort-Prüfung hat einen Klartext-Fallback für ältere Konten (werden beim nächsten Login automatisch zu bcrypt-Hashes migriert).
ui/login.py enthält einen absichtlichen Dev-Login (Benutzername Philip, festes Passwort), der Zugriff auf ein Entwickler-Menü gibt. Das ist bewusst öffentlich dokumentiert – jede eigene Instanz der App hat denselben Zugang. Wer die App als gemeinsam genutzten Dienst für mehrere fremde Nutzer hostet (statt jeder hostet selbst), sollte das Passwort vor dem Deployment ändern.
Lizenz

Apache License 2.0 – siehe LICENSE. Nutzung, Modifikation und auch kommerzielle Weiterverwendung sind erlaubt; Änderungen müssen kenntlich gemacht werden.
