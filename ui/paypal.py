
import os
import psycopg2
import re
import requests
import streamlit as st
from sqlalchemy import text
from database import engine
from dotenv import load_dotenv
load_dotenv()  # Lädt die Umgebungsvariablen aus der .env-Datei
PAYPAL_CLIENT_ID     = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_API_BASE      = os.getenv("PAYPAL_API_BASE")
PAYPAL_BASE_URL      = os.getenv("PAYPAL_BASE_URL")
PAYPAL_RETURN_URL    = os.getenv("PAYPAL_RETURN_URL")
PAYPAL_CANCEL_URL    = os.getenv("PAYPAL_CANCEL_URL")
def get_connection():
        return psycopg2.connect(
            client_secret=PAYPAL_CLIENT_SECRET,
            client_id=PAYPAL_CLIENT_ID,
            api_base=PAYPAL_API_BASE,
            base_url=PAYPAL_BASE_URL,
            return_url=PAYPAL_RETURN_URL,
            cancel_url=PAYPAL_CANCEL_URL,

        )


# ============================================================
#  HILFSFUNKTIONEN
# ============================================================

def clean_email(email: str) -> str:
    """E-Mail für PayPal bereinigen (keine Sonderzeichen)."""
    if not email or "@" not in email:
        return "no-email@example.com"
    local, domain = email.split("@", 1)
    for a, b in [("ä","a"),("ö","o"),("ü","u"),("ß","ss")]:
        local  = local.replace(a, b)
        domain = domain.replace(a, b)
    local  = re.sub(r"[^a-zA-Z0-9._-]", "", local)
    domain = re.sub(r"[^a-zA-Z0-9.-]",  "", domain)
    if not local or not domain:
        return "no-email@example.com"
    return f"{local}@{domain}"


def clean_paypal_id(text: str) -> str:
    """Text für PayPal-IDs bereinigen (nur alphanumerisch)."""
    for a, b in [("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss")]:
        text = text.replace(a, b)
    return re.sub(r"[^a-zA-Z0-9]", "", text)


# ============================================================
#  API-FUNKTIONEN
# ============================================================

def get_paypal_access_token() -> str | None:
    """OAuth Access Token von PayPal holen."""
    try:
        response = requests.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
            data={"grant_type": "client_credentials"},
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        st.error(f"PayPal Token Fehler: {response.status_code}")
        print(f"PayPal Fehler: {response.text}")
        return None
    except Exception as e:
        st.error(f"PayPal Verbindungsfehler: {e}")
        return None


def get_paypal_plans() -> list:
    """Alle verfügbaren Billing-Pläne abrufen."""
    token = get_paypal_access_token()
    if not token:
        return []
    try:
        response = requests.get(
            f"{PAYPAL_API_BASE}/v1/billing/plans",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
        )
        if response.status_code == 200:
            return response.json().get("plans", [])
        print(f"Fehler beim Laden der Pläne: {response.status_code} – {response.text}")
        return []
    except Exception as e:
        print(f"Exception beim Laden der Pläne: {e}")
        return []


def get_paypal_plan_details(plan_id: str) -> dict | None:
    """Details zu einem bestimmten Plan abrufen."""
    token = get_paypal_access_token()
    if not token:
        return None
    try:
        response = requests.get(
            f"{PAYPAL_API_BASE}/v1/billing/plans/{plan_id}",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
        )
        if response.status_code == 200:
            return response.json()
        print(f"Fehler beim Laden der Plan-Details: {response.status_code} – {response.text}")
        return None
    except Exception as e:
        print(f"Exception beim Laden der Plan-Details: {e}")
        return None


def _create_subscription(token: str, plan_id: str) -> dict | None:
    """PayPal-Subscription erstellen und in DB speichern."""
    user  = st.session_state.get("user", "")
    email = clean_email(st.session_state.get("email", "user@example.com"))

    subscription_data = {
        "plan_id": plan_id,
        "subscriber": {
            "name": {"given_name": user},
            "email_address": email,
        },
        "application_context": {
            "brand_name": "ETA Application",
            "locale": "de-DE",
            "user_action": "SUBSCRIBE_NOW",
            "return_url": PAYPAL_RETURN_URL,
            "cancel_url": PAYPAL_CANCEL_URL,
        },
        "custom_id": user,
    }

    try:
        response = requests.post(
            f"{PAYPAL_API_BASE}/v1/billing/subscriptions",
            json=subscription_data,
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
        )

        if response.status_code not in [200, 201]:
            st.error(f"PayPal Fehler: {response.status_code}")
            st.error(f"Antwort: {response.text}")
            return None

        result = response.json()
        subscription_id = result.get("id")
        st.session_state.paypal_subscription_id = subscription_id

        # Subscription-ID sofort in DB speichern (damit Webhook sie findet)
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE benutzer
                        SET paypal_subscription_id = :sub_id,
                            payment_status = 'PENDING'
                        WHERE benutzername = :user
                    """),
                    {"sub_id": subscription_id, "user": user},
                )
            st.info("Subscription ID in DB gespeichert.")
        except Exception as db_err:
            st.error(f"Fehler beim Speichern der Subscription ID: {db_err}")

        return result

    except Exception as e:
        st.error(f"Fehler: {e}")
        return None


# ============================================================
#  PAYMENT-SEITE (Streamlit UI)
# ============================================================

def payment_page():
    """PayPal Abonnement-Seite."""

    # Bereits aktiv → direkt zur App
    if st.session_state.get("payment_status") == "ACTIVE":
        st.session_state.page = "app"
        st.rerun()
        return

    st.set_page_config(page_title="Zahlung", layout="centered")
    st.markdown("# 💳 Abonnement erforderlich")
    st.write("Um die ETA Anwendung zu nutzen, benötigen Sie ein aktives Abonnement.")

    # Plan laden
    st.info("⏳ Plan wird geladen...")
    plans = get_paypal_plans()
    active_plan = next((p for p in plans if p.get("status") == "ACTIVE"), None)

    if not active_plan:
        st.error("Keine aktiven Abonnement-Pläne verfügbar. Bitte später erneut versuchen.")
        st.stop()

    plan_id     = active_plan.get("id")
    plan_details = get_paypal_plan_details(plan_id)

    if not plan_details:
        st.error("Plan-Details konnten nicht geladen werden.")
        st.stop()

    st.success("Plan geladen")

    # Plan-Infos anzeigen
    plan_name        = plan_details.get("name", "Abonnement-Plan")
    plan_description = plan_details.get("description", "")
    price_per_month  = "N/A"

    for cycle in plan_details.get("billing_cycles", []):
        if cycle.get("frequency", {}).get("interval_unit") == "MONTH":
            price_data = cycle.get("pricing_scheme", {}).get("fixed_price", {})
            if price_data:
                price_per_month = price_data.get("value", "N/A")
                break

    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"## {plan_name}")
            if plan_description:
                st.write(f"_{plan_description}_")
        with col2:
            st.markdown(f"### {price_per_month}€")
            st.markdown("**pro Monat**")

    st.divider()

    # Abonnieren
    if st.button("Jetzt abonnieren", use_container_width=True, key="paypal_subscribe"):
        token = get_paypal_access_token()
        if not token:
            st.error("Fehler beim Verbinden mit der PayPal API.")
        else:
            result = _create_subscription(token, plan_id)
            if result:
                approval_url = next(
                    (l["href"] for l in result.get("links", [])
                     if l.get("rel") == "approve"),
                    None
                )
                if approval_url:
                    st.success("Weiterleitung zum Zahlungsformular...")
                    st.markdown(
                        f'<meta http-equiv="refresh" content="1;url={approval_url}">',
                        unsafe_allow_html=True,
                    )
                    st.link_button("Zum Zahlungsformular", approval_url)
                else:
                    st.error("Keine Approval-URL erhalten.")
                    st.json(result)

    st.divider()

    if st.button("← Zurück zum Login", use_container_width=True, key="back_to_login"):
        st.session_state.page           = "login"
        st.session_state.user           = None
        st.session_state.payment_status = None
        st.session_state.selected_plan_id = None
        st.rerun()
