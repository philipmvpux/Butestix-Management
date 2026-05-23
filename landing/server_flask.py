"""
Advanced: Kombinierter Server für Landing Page + Streamlit Redirect
Nutzt Flask um Landing Page zu hosten und zur Streamlit App weiterzuleiten
"""
import flask
from flask import Flask, send_file, redirect
import os

app = Flask(__name__)

# Stelle Landing Page Dateien bereit
LANDING_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def landing():
    """Zeige die Landing Page"""
    return send_file(os.path.join(LANDING_DIR, 'index.html'))

@app.route('/style.css')
def css():
    """Serve CSS"""
    return send_file(os.path.join(LANDING_DIR, 'style.css'), mimetype='text/css')

@app.route('/script.js')
def js():
    """Serve JavaScript"""
    return send_file(os.path.join(LANDING_DIR, 'script.js'), mimetype='application/javascript')

@app.route('/app')
def to_app():
    """Weiterleitung zur Streamlit App"""
    return redirect('http://localhost:8501')

if __name__ == '__main__':
    print("🌐 Server läuft auf http://localhost:5000")
    print("📊 Streamlit App: http://localhost:8501")
    print("⏹️  Mit Ctrl+C beenden\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
