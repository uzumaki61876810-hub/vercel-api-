"""
GET /api/health — quick health check
"""
import json
import os
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({
            'status': 'ok',
            'service': '星と命の金運鑑定局 API',
            'stripe_configured': bool(os.environ.get('STRIPE_SECRET_KEY')),
            'sendgrid_configured': bool(os.environ.get('SENDGRID_API_KEY')),
        }, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass
