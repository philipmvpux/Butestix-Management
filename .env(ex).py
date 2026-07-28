# =========================================
# DATABASE CONFIGURATION
# =========================================


DB_USER = 'Nutzer'  # Versuche mit Philip - ändere wenn nicht korrekt
DB_PASSWORD = '******'  # Passwort für Nutzer
DB_HOST = 'localhost' # Ändere hier wenn nicht lokal
DB_PORT = '5432'      # Ändere hier wenn anderer Port
DB_NAME = '*******'   # Ändere hier wenn anderer DB-Name

# =========================================
# APP CONFIGURATION
# =========================================
APP_NAME = 'butestix'
DEBUG_MODE = False


# =========================================
# PAYPAL CONFIGURATION
# =========================================

PAYPAL_CLIENT_ID     = "****"
PAYPAL_CLIENT_SECRET = "****"
PAYPAL_API_BASE      = "https://api-m.sandbox.paypal.com"   # Sandbox → live: api-m.paypal.com
PAYPAL_BASE_URL      = "http://localhost:8501"               # Streamlit App URL
PAYPAL_RETURN_URL    = f"{PAYPAL_BASE_URL}?page=payment_success"
PAYPAL_CANCEL_URL    = f"{PAYPAL_BASE_URL}?page=payment_cancel"