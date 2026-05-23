

import pandas as pd
import streamlit as st

from database import engine
from ui.helpers import GESELLSCHAFTSFORMEN, lade_firmendaten


# ============================================================
#  VOLLSTÄNDIGKEITSPRÜFUNGEN
# ============================================================

def firmenprofil_vollstaendig() -> bool:
    """
    Prüft ob die Pflichtfelder des Firmenprofils ausgefüllt sind.
    Wird nach dem Login aufgerufen um zu entscheiden ob Setup nötig ist.
    """
    pflichtfelder = [
        "firmenname",
        "gesellschaftsform",
        "firmenadresse",
        "firmentelefon",
        "standard_rechnungsnummer",
    ]
    return all(st.session_state.get(f) for f in pflichtfelder)


def bankdaten_vollstaendig() -> bool:
    """
    Prüft ob die Pflichtfelder der Bankdaten ausgefüllt sind.
    Wird vor Rechnungserstellung geprüft.
    """
    pflichtfelder = ["iban", "bic", "bankname"]
    return all(st.session_state.get(f) for f in pflichtfelder)


def _upsert_firmenprofil(felder: dict):
    """
    Firmenprofil-Felder in DB speichern (INSERT oder UPDATE).
    felder = {spaltenname: wert, ...}
    """
    user = st.session_state.user
    with engine.begin() as conn:
        existing = conn.exec_driver_sql(
            "SELECT benutzername FROM firmenprofil WHERE benutzername = %s",
            (user,)
        ).fetchone()

        spalten = list(felder.keys())
        werte   = list(felder.values())

        if existing:
            set_clause = ", ".join(f"{k} = %s" for k in spalten)
            conn.exec_driver_sql(
                f"UPDATE firmenprofil SET {set_clause} WHERE benutzername = %s",
                (*werte, user)
            )
        else:
            cols = ", ".join(["benutzername"] + spalten)
            vals = ", ".join(["%s"] * (len(spalten) + 1))
            conn.exec_driver_sql(
                f"INSERT INTO firmenprofil ({cols}) VALUES ({vals})",
                (user, *werte)
            )


# ============================================================
#  SEITE 1: FIRMENPROFIL
# ============================================================

def setup_company_profile_page():
    """
    Einrichtung des Firmenprofils nach dem ersten Login.
    Pflichtfelder: Firmenname, Gesellschaftsform, Adresse, Telefon, Rechnungsnummer.
    """
    st.set_page_config(page_title="Firmenprofil einrichten", layout="centered")
    st.title("Firmenprofil einrichten")
    st.markdown("---")
    st.info(
        "Bitte geben Sie die erforderlichen Informationen über Ihr Unternehmen ein. "
        "Diese Daten sind essentiell für die Erstellung von Rechnungen und Dokumenten."
    )

    # Fortschrittsanzeige
    st.markdown("**Schritt 1 von 2** – Unternehmensdaten")
    st.progress(0.5)
    st.markdown("")

    with st.form("setup_company_profile_form"):
        st.markdown("### Unternehmensinformation")

        # Firmenname
        st.markdown("**Firmenname** ✱")
        st.caption("Der Name Ihres Unternehmens, wie er auf Rechnungen erscheinen soll.")
        firmenname = st.text_input(
            "Firmenname",
            value=st.session_state.get("firmenname", ""),
            label_visibility="collapsed",
        )

        # Gesellschaftsform
        st.markdown("**Gesellschaftsform** ✱")
        current_gf    = st.session_state.get("gesellschaftsform")
        default_index = GESELLSCHAFTSFORMEN.index(current_gf) if current_gf in GESELLSCHAFTSFORMEN else 0
        gesellschaftsform = st.selectbox(
            "Gesellschaftsform",
            GESELLSCHAFTSFORMEN,
            index=default_index,
            label_visibility="collapsed",
        )

        # Adresse
        st.markdown("**Adresse** ✱")
        st.caption("Ihre Geschäftsadresse (z.B. Hauptstraße 5, 12345 Berlin).")
        col1, col2 = st.columns(2)
        with col1:
            strasse = st.text_input("Straße und Hausnummer", placeholder="Hauptstraße 5")
        with col2:
            plz = st.text_input("Postleitzahl", placeholder="12345", max_chars=5)
        stadt   = st.text_input("Stadt", placeholder="Berlin")
        adresse = f"{strasse}, {plz} {stadt}".strip(", ") if (strasse or plz or stadt) else ""

        # Kontakt
        st.markdown("**Telefon & Fax** ✱")
        col1, col2 = st.columns(2)
        with col1:
            telefon = st.text_input(
                "Telefon", value=st.session_state.get("firmentelefon", ""),
                placeholder="+49 30 123456"
            )
        with col2:
            fax = st.text_input(
                "Fax (optional)", value=st.session_state.get("firmenfax", ""),
                placeholder="+49 30 123457"
            )

        # Rechnungsnummer
        st.markdown("**Rechnungsnummer – Startnummer** ✱")
        st.caption("Wird automatisch mit jedem neuen Projekt erhöht.")
        rechnungsnummer = st.number_input(
            "Rechnungsnummer",
            min_value=1,
            value=st.session_state.get("standard_rechnungsnummer", 100),
            label_visibility="collapsed",
        )

        st.markdown("---")
        col_skip, col_save = st.columns([3, 1])
        with col_skip:
            st.caption("✱ Pflichtfelder")
        submit = st.form_submit_button("Speichern und weiter →", use_container_width=True)

    if not submit:
        return

    # Validierung
    fehler = []
    if not firmenname.strip():
        fehler.append("Firmenname")
    if not adresse.strip() or adresse == ", ":
        fehler.append("Adresse (Straße, PLZ, Stadt)")
    if not gesellschaftsform:
        fehler.append("Gesellschaftsform")
    if not telefon.strip():
        fehler.append("Telefon")

    if fehler:
        st.error(f"Bitte fülle alle Pflichtfelder aus: {', '.join(fehler)}")
        return

    try:
        _upsert_firmenprofil({
            "firmenname":      firmenname.strip(),
            "gesellschaftsform": gesellschaftsform,
            "adresse":         adresse.strip(),
            "telefon":         telefon.strip(),
            "fax":             fax.strip(),
            "rechnungsnummer": int(rechnungsnummer),
        })

        # Session aktualisieren
        st.session_state.firmenname               = firmenname.strip()
        st.session_state.firmenadresse            = adresse.strip()
        st.session_state.firmentelefon            = telefon.strip()
        st.session_state.firmenfax                = fax.strip()
        st.session_state.gesellschaftsform        = gesellschaftsform
        st.session_state.standard_rechnungsnummer = int(rechnungsnummer)

        lade_firmendaten()
        st.success("Firmenprofil gespeichert!")
        st.info("Weiter zu Schritt 2: Bank- und Registerdaten...")
        st.session_state.page = "setup_bank_register"
        st.rerun()

    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")


# ============================================================
#  SEITE 2: BANK- & REGISTERDATEN
# ============================================================

def setup_bank_register_data_page():
    """
    Bank- und Registerdaten einrichten.
    Pflichtfelder: IBAN, BIC, Bankname.
    Optionale Felder: Registergericht, HRB, USt-IdNr., Geschäftsführer.
    """
    st.set_page_config(page_title="Bank- und Registerdaten", layout="centered")
    st.title("Bank- und Registerdaten")
    st.markdown("---")

    # Fortschrittsanzeige
    st.markdown("**Schritt 2 von 2** – Bankverbindung & Registerdaten")
    st.progress(1.0)
    st.markdown("")

    st.error(
        "Diese Daten sind für vollständige Rechnungen erforderlich. "
        "Mindestens IBAN, BIC und Bankname müssen angegeben werden."
    )
    st.markdown("")

    with st.form("setup_bank_register_form"):

        # ── Bankverbindung (Pflicht) ──────────────────────────
        st.markdown("### Bankverbindung ✱")

        st.markdown("**IBAN** ✱")
        st.caption("Internationale Bankkontonummer (z.B. DE89370400440532013000).")
        iban = st.text_input(
            "IBAN", value=st.session_state.get("iban", ""),
            placeholder="DE89370400440532013000",
            label_visibility="collapsed",
        )

        st.markdown("**BIC** ✱")
        st.caption("Internationaler Bankleitzahl-Code (z.B. COBADEFFXXX).")
        bic = st.text_input(
            "BIC", value=st.session_state.get("bic", ""),
            placeholder="COBADEFFXXX",
            label_visibility="collapsed",
        )

        st.markdown("**Bankname** ✱")
        st.caption("Name der Bank oder Sparkasse (z.B. Commerzbank AG).")
        bankname = st.text_input(
            "Bankname", value=st.session_state.get("bankname", ""),
            placeholder="Commerzbank AG",
            label_visibility="collapsed",
        )

        # ── Registerdaten (Optional) ──────────────────────────
        st.markdown("---")
        st.markdown("### Registerdaten (optional)")

        st.markdown("**Registergericht**")
        st.caption("Amtsgericht, bei dem Ihr Unternehmen registriert ist.")
        registergericht = st.text_input(
            "Registergericht", value=st.session_state.get("registergericht", ""),
            placeholder="Amtsgericht Berlin",
            label_visibility="collapsed",
        )

        st.markdown("**HRB-Nummer**")
        st.caption("Ihre Handelsregisternummer (z.B. HRB 123456).")
        hrb_nummer = st.text_input(
            "HRB-Nummer", value=st.session_state.get("hrb_nummer", ""),
            placeholder="HRB 123456",
            label_visibility="collapsed",
        )

        st.markdown("**USt-IdNr.**")
        st.caption("Umsatzsteuer-Identifikationsnummer (z.B. DE123456789).")
        ustidnr = st.text_input(
            "USt-IdNr.", value=st.session_state.get("ustidnr", ""),
            placeholder="DE123456789",
            label_visibility="collapsed",
        )

        st.markdown("**Geschäftsführer / Inhaber**")
        st.caption("Name der Person, die das Unternehmen führt.")
        geschaeftsfuehrer = st.text_input(
            "Geschäftsführer", value=st.session_state.get("geschaeftsfuehrer", ""),
            placeholder="Max Mustermann",
            label_visibility="collapsed",
        )

        st.markdown("---")
        col_back, col_save = st.columns([1, 2])
        with col_back:
            zurueck = st.form_submit_button("← Zurück", use_container_width=True)
        with col_save:
            submit = st.form_submit_button("Speichern und zur App →", use_container_width=True)

    if zurueck:
        st.session_state.page = "setup_company_profile"
        st.rerun()

    if not submit:
        return

    # Validierung
    fehler = []
    if not iban.strip():
        fehler.append("IBAN")
    if not bic.strip():
        fehler.append("BIC")
    if not bankname.strip():
        fehler.append("Bankname")

    if fehler:
        st.error(f"Pflichtfelder fehlen: {', '.join(fehler)}")
        return

    try:
        _upsert_firmenprofil({
            "iban":              iban.strip(),
            "bic":               bic.strip(),
            "bankname":          bankname.strip(),
            "registergericht":   registergericht.strip(),
            "hrb_nummer":        hrb_nummer.strip(),
            "ustidnr":           ustidnr.strip(),
            "geschaeftsfuehrer": geschaeftsfuehrer.strip(),
        })

        # Session aktualisieren
        st.session_state.iban              = iban.strip()
        st.session_state.bic               = bic.strip()
        st.session_state.bankname          = bankname.strip()
        st.session_state.registergericht   = registergericht.strip()
        st.session_state.hrb_nummer        = hrb_nummer.strip()
        st.session_state.ustidnr           = ustidnr.strip()
        st.session_state.geschaeftsfuehrer = geschaeftsfuehrer.strip()

        lade_firmendaten()
        st.success("Bank- und Registerdaten gespeichert!")
        st.session_state.page = "app"
        st.session_state.nav  = "Rechnung erstellen"
        st.rerun()

    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")


# ============================================================
#  CHECK FIRMENPROFIL (nach AGB-Akzeptanz)
# ============================================================

def check_firmenprofil_page():
    """
    Wird nach AGB-Akzeptanz aufgerufen.
    Reihenfolge: Test-Konto → Payment → Firmenprofil → App
    """
    user = st.session_state.get("user")

    # 1. Test-Konto → direkt zur App
    try:
        df = pd.read_sql(
            "SELECT COALESCE(is_test_account, FALSE) as is_test_account FROM benutzer WHERE benutzername = %s",
            engine, params=(user,)
        )
        if not df.empty and df.iloc[0]["is_test_account"]:
            st.session_state.page = "app"
            st.rerun()
            return
    except Exception:
        pass  # Spalte existiert noch nicht → kein Test-Konto

    # 2. Payment prüfen
    try:
        df = pd.read_sql(
            "SELECT payment_status FROM benutzer WHERE benutzername = %s",
            engine, params=(user,)
        )
        payment_status = df.iloc[0]["payment_status"] if not df.empty else None
        st.session_state.payment_status = payment_status

        if payment_status != "ACTIVE":
            st.session_state.page = "payment"
            st.rerun()
            return
    except Exception as e:
        st.error(f"Fehler beim Payment-Check: {e}")
        st.session_state.page = "payment"
        st.rerun()
        return

    # 3. Firmenprofil prüfen
    try:
        df = pd.read_sql(
            """SELECT
                COALESCE(firmenname, '')        as firmenname,
                COALESCE(gesellschaftsform, '') as gesellschaftsform,
                COALESCE(adresse, '')           as firmenadresse,
                COALESCE(telefon, '')           as firmentelefon,
                COALESCE(rechnungsnummer, 0)    as standard_rechnungsnummer
               FROM firmenprofil WHERE benutzername = %s""",
            engine, params=(user,)
        )

        if df.empty:
            # Noch kein Profil → Setup starten
            st.session_state.missing_fields_info = [
                "Firmenname", "Gesellschaftsform", "Adresse", "Telefon", "Rechnungsnummer"
            ]
            st.session_state.page = "setup_company_profile"
            st.rerun()
            return

        # Fehlende Felder sammeln
        row = df.iloc[0]
        fehlend = [
            label for label, key in [
                ("Firmenname",      "firmenname"),
                ("Gesellschaftsform","gesellschaftsform"),
                ("Adresse",         "firmenadresse"),
                ("Telefon",         "firmentelefon"),
            ]
            if not row.get(key)
        ]
        if row.get("standard_rechnungsnummer", 0) == 0:
            fehlend.append("Rechnungsnummer")

        if fehlend:
            st.session_state.missing_fields_info = fehlend
            st.session_state.page = "setup_company_profile"
        else:
            st.session_state.page = "app"

        st.rerun()

    except Exception:
        # Tabelle existiert noch nicht → Setup
        st.session_state.missing_fields_info = ["Firmenprofil erforderlich"]
        st.session_state.page = "setup_company_profile"
        st.rerun()
