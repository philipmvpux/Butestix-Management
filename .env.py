# =========================================
# DATABASE CONFIGURATION
# =========================================


DB_USER = 'Philip'  # Versuche mit Philip - ändere wenn nicht korrekt
DB_PASSWORD = '091009'  # Passwort für Philip
DB_HOST = 'localhost' # Ändere hier wenn nicht lokal
DB_PORT = '5432'      # Ändere hier wenn anderer Port
DB_NAME = 'eta_app'   # Ändere hier wenn anderer DB-Name

# =========================================
# APP CONFIGURATION
# =========================================
APP_NAME = 'butestix'
DEBUG_MODE = False


# =========================================
# PAYPAL CONFIGURATION
# =========================================

PAYPAL_CLIENT_ID     = "AW7r-xOBk6BwvghQbPkHb8eX6THqsTUB0SIPZgo6wx3NWoQ2ErfelfI-Ozn2_mgJM9k1RungRJUzI--_"
PAYPAL_CLIENT_SECRET = "EPUcVR-kLA5VhE33TjyaQe09Yv0mBeqe1aQuW3QQyADUek57Hk7gh-m1hZvPuFeZj56nn_-pM7d0_diG"
PAYPAL_API_BASE      = "https://api-m.sandbox.paypal.com"   # Sandbox → live: api-m.paypal.com
PAYPAL_BASE_URL      = "http://localhost:8501"               # Streamlit App URL
PAYPAL_RETURN_URL    = f"{PAYPAL_BASE_URL}?page=payment_success"
PAYPAL_CANCEL_URL    = f"{PAYPAL_BASE_URL}?page=payment_cancel"