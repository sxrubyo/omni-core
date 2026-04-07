#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import os

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/tv/command':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            command = data.get('command', '')

            if not command:
                self.send_error(400, 'No command')
                return

            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd='/home/santi21435/.n8n',
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                response = {
                    'success': result.returncode == 0,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        print(f"[TV-Bridge] {args[0]}")

print("Starting TV Bridge on port 3333...")
HTTPServer(('0.0.0.0', 3333), Handler).serve_forever()
