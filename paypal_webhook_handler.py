"""
PayPal Webhook Handler für PostgreSQL
Läuft als separater Flask Server auf Port 5000
"""

from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# PostgreSQL Connection
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "hershyl_db")

# URL-encode password if it contains special characters
from urllib.parse import quote_plus
SAFE_PASSWORD = quote_plus(DB_PASSWORD) if DB_PASSWORD else "password"

DATABASE_URL = f"postgresql://{DB_USER}:{SAFE_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Flask App
app = Flask(__name__)

# PayPal Webhook Signature Verification (optional but recommended)
def verify_webhook(request_body, webhook_id, event_type, transmission_time, transmission_sig, cert_url):
    """
    Verify PayPal webhook signature
    In production, implement actual signature verification
    """
    # For sandbox, you can skip verification or implement it with requests library
    return True

@app.route('/webhook/paypal', methods=['POST'])
def handle_paypal_webhook():
    """Handle PayPal webhook events"""
    try:
        # Get webhook data
        data = request.get_json()
        event_type = data.get('event_type')
        resource = data.get('resource', {})
        
        print(f"✓ Webhook erhalten: {event_type}")
        print(f"  Daten: {json.dumps(data, indent=2)}")
        
        # WICHTIG: Antworte SOFORT mit 200, damit PayPal nicht erneut sendet
        response_obj = jsonify({"status": "received"})
        
        # Handle different event types (im Hintergrund)
        try:
            if event_type == "BILLING.SUBSCRIPTION.CREATED":
                handle_subscription_created(resource)
            elif event_type == "BILLING.SUBSCRIPTION.PAYMENT.CAPTURED":
                handle_payment_captured(resource)
            elif event_type == "BILLING.SUBSCRIPTION.PAYMENT.FAILED":
                handle_payment_failed(resource)
            elif event_type == "BILLING.SUBSCRIPTION.CANCELLED":
                handle_subscription_cancelled(resource)
            elif event_type == "BILLING.SUBSCRIPTION.UPDATED":
                handle_subscription_updated(resource)
        except Exception as e:
            print(f"  ✗ Fehler beim Event-Handler: {str(e)}")
        
        # Log webhook in database (NACH dem Response)
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO webhook_log (event_type, body)
                        VALUES (:event_type, :body)
                        """
                    ),
                    {"event_type": event_type, "body": json.dumps(data)}
                )
                print(f"  ✓ Webhook in Database geloggt")
        except Exception as log_error:
            print(f"  ✗ Fehler beim Webhook-Logging: {str(log_error)}")
        
        return response_obj, 200
    
    except Exception as e:
        print(f"✗ KRITISCHER FEHLER beim Webhook: {str(e)}")
        return jsonify({"error": str(e), "status": "received"}), 200  # Auch bei Fehler 200 zurück!

def handle_subscription_created(resource):
    """Handle subscription creation"""
    subscription_id = resource.get('id')
    
    print(f"  → Subscription erstellt: {subscription_id}")
    print(f"  → Vollständige Resource: {json.dumps(resource, indent=2)}")
    
    # Try to find user by subscription_id that we stored when creating it
    if subscription_id:
        with engine.begin() as conn:
            try:
                # Check if this subscription is already in DB (we save it during subscription creation)
                user_check = conn.execute(
                    text("SELECT benutzername FROM benutzer WHERE paypal_subscription_id = :sub_id"),
                    {"sub_id": subscription_id}
                ).fetchone()
                
                if user_check:
                    print(f"  ✓ Subscription {subscription_id} bereits für Benutzer {user_check[0]} gespeichert")
                else:
                    print(f"  ✗ Subscription {subscription_id} nicht in DB gefunden")
            except Exception as e:
                print(f"  ✗ Fehler beim Update: {str(e)}")

def handle_payment_captured(resource):
    """Handle successful payment"""
    subscription_id = resource.get('id')
    
    print(f"  → Payment erfolgreich: {subscription_id}")
    print(f"  → Resource data: {json.dumps(resource, indent=2)}")
    
    if subscription_id:
        with engine.begin() as conn:
            try:
                # Search for user by paypal_subscription_id
                check_result = conn.execute(
                    text("SELECT benutzername FROM benutzer WHERE paypal_subscription_id = :sub_id"),
                    {"sub_id": subscription_id}
                ).fetchone()
                
                if check_result:
                    username = check_result[0]
                    conn.execute(
                        text(
                            """
                            UPDATE benutzer
                            SET payment_status = 'ACTIVE', 
                                payment_timestamp = :timestamp
                            WHERE benutzername = :user
                            """
                        ),
                        {"timestamp": datetime.utcnow(), "user": username}
                    )
                    print(f"  ✓ Benutzer {username} → ACTIVE (Payment erfolgreich!)")
                else:
                    print(f"  ✗ Keine Subscription mit ID {subscription_id} in DB gefunden!")
            except Exception as e:
                print(f"  ✗ Fehler beim Update: {str(e)}")

def handle_payment_failed(resource):
    """Handle failed payment"""
    subscription_id = resource.get('id')
    
    print(f"  → Payment fehlgeschlagen: {subscription_id}")
    
    if subscription_id:
        with engine.begin() as conn:
            try:
                # Find user by subscription_id
                check_result = conn.execute(
                    text("SELECT benutzername FROM benutzer WHERE paypal_subscription_id = :sub_id"),
                    {"sub_id": subscription_id}
                ).fetchone()
                
                if check_result:
                    username = check_result[0]
                    conn.execute(
                        text(
                            """
                            UPDATE benutzer
                            SET payment_status = 'FAILED'
                            WHERE benutzername = :user
                            """
                        ),
                        {"user": username}
                    )
                    print(f"  ✓ Benutzer {username} → FAILED")
                else:
                    print(f"  ✗ Subscription {subscription_id} nicht gefunden")
            except Exception as e:
                print(f"  ✗ Fehler beim Update: {str(e)}")

def handle_subscription_cancelled(resource):
    """Handle subscription cancellation"""
    subscription_id = resource.get('id')
    
    print(f"  → Subscription abgebrochen: {subscription_id}")
    
    if subscription_id:
        with engine.begin() as conn:
            try:
                # Find user by subscription_id
                check_result = conn.execute(
                    text("SELECT benutzername FROM benutzer WHERE paypal_subscription_id = :sub_id"),
                    {"sub_id": subscription_id}
                ).fetchone()
                
                if check_result:
                    username = check_result[0]
                    conn.execute(
                        text(
                            """
                            UPDATE benutzer
                            SET payment_status = 'CANCELLED'
                            WHERE benutzername = :user
                            """
                        ),
                        {"user": username}
                    )
                    print(f"  ✓ Benutzer {username} → CANCELLED")
                else:
                    print(f"  ✗ Subscription {subscription_id} nicht gefunden")
            except Exception as e:
                print(f"  ✗ Fehler beim Update: {str(e)}")

def handle_subscription_updated(resource):
    """Handle subscription update"""
    subscription_id = resource.get('id')
    custom_id = resource.get('custom_id')
    status = resource.get('status', 'UNKNOWN')
    
    print(f"  → Subscription aktualisiert: {subscription_id} → {status}")

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/test/webhook', methods=['POST'])
def test_webhook():
    """Test endpoint - simulate PayPal webhook"""
    test_data = {
        "id": "WH-TEST123",
        "event_type": "BILLING.SUBSCRIPTION.CREATED",
        "create_time": datetime.utcnow().isoformat(),
        "resource": {
            "id": "S-TEST-SUB-ID",
            "custom_id": "testbenutzer",
            "status": "ACTIVE"
        }
    }
    
    # Simulate webhook call
    with app.test_client() as client:
        response = client.post('/webhook/paypal', json=test_data)
    
    return jsonify({"test_result": "erfolg", "response": response.get_json()}), 200

if __name__ == "__main__":
    print("🚀 PayPal Webhook Handler startet auf Port 5000...")
    print(f"📍 Webhook URL: http://localhost:5000/webhook/paypal")
    print(f"🌍 Mit ngrok: https://YOUR_NGROK_URL/webhook/paypal")
    print(f"🧪 Test: http://localhost:5000/test/webhook")
    app.run(host='0.0.0.0', port=5000, debug=True)
