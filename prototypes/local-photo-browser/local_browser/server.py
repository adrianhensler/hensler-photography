"""Loopback-only, GET-only server; serves cached derivatives, never source paths."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from .catalog import Catalog

STATIC = Path(__file__).parent / 'static'


def make_server(catalog: Catalog, data: Path, report: dict, port=8080):
    class Handler(BaseHTTPRequestHandler):
        def allowed(self):
            hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            host = self.headers.get('Host', '')
            return (host in hosts
                    and self.headers.get('Origin', f'http://{host}') == f'http://{host}'
                    and self.headers.get('Sec-Fetch-Site', 'none') in ('same-origin', 'none'))

        def send(self, status, body, kind='application/json'):
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def json(self, status, value):
            self.send(status, json.dumps(value).encode())

        def do_GET(self):
            if not self.allowed():
                return self.json(403, {'error': 'Only this local browser may access the catalog'})
            url = urlsplit(self.path)
            try:
                self.route(url)
            except (ValueError, TypeError):
                self.json(400, {'error': 'Invalid query parameters'})
            except FileNotFoundError:
                self.json(404, {'error': 'Preview unavailable; rescan the folder'})

        def route(self, url):
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if url.path in files:
                name, kind = files[url.path]
                return self.send(200, (STATIC / name).read_bytes(), kind)
            if url.path == '/api/photos':
                filters = {k: v[-1] for k, v in parse_qs(url.query).items()}
                result = catalog.query(filters)
                # Paths stay in the catalog; the browser receives relative paths only.
                result['items'] = [{'id': row['id'], **row['metadata']} for row in result['items']]
                return self.json(200, result)
            if url.path == '/api/facets':
                return self.json(200, catalog.facets())
            if url.path == '/api/status':
                return self.json(200, report)
            parts = url.path.strip('/').split('/')
            if len(parts) == 3 and parts[0] == 'image' and parts[2] in ('thumbnail', 'preview'):
                row = catalog.get(parts[1])
                if row and row['present']:
                    key = row['metadata']['cache_key']
                    # Even a future imported catalog cannot inject a filesystem path.
                    if len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
                        raise ValueError('Invalid derivative key')
                    return self.send(200, (data / 'cache' / f'{key}-{parts[2]}.webp').read_bytes(), 'image/webp')
            return self.json(404, {'error': 'Not found'})

        def log_message(self, format, *args):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)
