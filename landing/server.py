"""
Landing Page Server mit Form-Handling
Speichert Anfragen lokal in applicants.json
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import sys
import json
from urllib.parse import parse_qs
from datetime import datetime

class FormHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve static files normally
        super().do_GET()
    
    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        # Handle form submissions
        if self.path == '/api/signup':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                # Parse JSON data
                data = json.loads(body)
                
                # Add timestamp
                data['timestamp'] = datetime.now().isoformat()
                
                # Save to applicants.json
                applicants_file = os.path.join(os.path.dirname(__file__), 'applicants.json')
                
                # Load existing data or create new
                applicants = []
                if os.path.exists(applicants_file):
                    with open(applicants_file, 'r', encoding='utf-8') as f:
                        try:
                            applicants = json.load(f)
                        except:
                            applicants = []
                
                # Add new applicant
                applicants.append(data)
                
                # Save back
                with open(applicants_file, 'w', encoding='utf-8') as f:
                    json.dump(applicants, f, ensure_ascii=False, indent=2)
                
                # Send success response with CORS headers
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
                
                print(f"✅ Neue Anfrage gespeichert: {data['name']} ({data['company']})")
                
            except Exception as e:
                print(f"❌ Fehler: {str(e)}")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
    
    def end_headers(self):
        # Cache-Kontrolle: Keine Caching für HTML
        self.send_header('Cache-Control', 'no-cache, no-store, max-age=0')
        super().end_headers()

if __name__ == '__main__':
    # Wechsle ins Landing-Page Verzeichnis
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Starte Server auf Port 5000
    server_address = ('', 5000)
    httpd = HTTPServer(server_address, FormHandler)
    
    print("🌐 Landing Page Server läuft auf http://localhost:5000")
    print("📁 Anfragen werden gespeichert in: applicants.json")
    print("\n⏹️  Mit Ctrl+C beenden")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ Server beendet")
        sys.exit(0)
