from flask import Flask, request, jsonify
from sqlalchemy import create_engine
import json

app = Flask(__name__)
engine = create_engine("sqlite:///bau_db.sqlite")

@app.route("/paypal/webhook", methods=["POST"])
def paypal_webhook():
    data = request.get_json(force=True)
    event_type = data.get('event_type')
    status = data.get('resource', {}).get('status')
    # Hole den zuletzt angelegten Benutzer
    with engine.begin() as conn:
        user_row = conn.exec_driver_sql(
            "SELECT benutzername FROM benutzer ORDER BY ROWID DESC LIMIT 1"
        ).fetchone()
        benutzername = user_row[0] if user_row else None
        payload_json = json.dumps(data)
        conn.exec_driver_sql(
            "INSERT INTO webhook_log (benutzername, event_type, status, received_at, payload) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)",
            (benutzername, event_type, status, payload_json)
        )
        # Setze payment_status auf ACTIVE für Subscription-Events mit status ACTIVE
        if benutzername and event_type in ["BILLING.SUBSCRIPTION.ACTIVATED", "BILLING.SUBSCRIPTION.UPDATED", "BILLING.SUBSCRIPTION.PAYMENT.COMPLETED"] and status == "ACTIVE":
            conn.exec_driver_sql(
                "UPDATE benutzer SET payment_status = 'ACTIVE' WHERE benutzername = ?",
                (benutzername,)
            )
    print(f"Webhook empfangen: {payload_json}")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
