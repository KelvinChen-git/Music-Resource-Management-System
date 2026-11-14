#!/usr/bin/env python3
"""Loopback-only authenticated worker. Browser authorization stays in Java."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading

from discovery_index import DiscoveryError, DiscoveryIndex, FixtureEncoder, ClapTextEncoder, require, strict_json


def make_server(index, encoder, secret, port=8091):
    require(isinstance(secret, str) and len(secret) >= 32, 'Worker secret must contain at least32 characters', 503)
    gate = threading.BoundedSemaphore(1)

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            pass  # Never log queries or authorization headers.

        def reply(self, status, body):
            raw = (json.dumps(body, allow_nan=False, separators=(',', ':')) + '\n').encode()
            if len(raw) > 65536:
                status, raw = 503, b'{"error_type":"response_too_large","message":"Worker response unavailable"}\n'
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + secret):
                return self.reply(401, {'error_type': 'unauthorized', 'message': 'Worker authentication required'})
            if self.path != '/internal/search':
                return self.reply(404, {'error_type': 'not_found', 'message': 'Unknown worker route'})
            if not gate.acquire(blocking=False):
                return self.reply(503, {'error_type': 'busy', 'message': 'Encoder is busy'})
            try:
                require(self.headers.get_content_type() == 'application/json', 'JSON required')
                require(self.headers.get('Transfer-Encoding') is None, 'Content-Length required')
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    raise DiscoveryError(400, 'invalid_input', 'Content-Length required') from None
                require(0 < length <= 2 * 1024 * 1024, 'Request exceeds worker limit', 413, 'request_too_large')
                raw = self.rfile.read(length)
                require(len(raw) == length, 'Incomplete request')
                self.reply(200, index.search(strict_json(raw), encoder))
            except DiscoveryError as error:
                self.reply(error.status, {'error_type': error.kind, 'message': error.message})
            except Exception:
                self.reply(503, {'error_type': 'worker_unavailable', 'message': 'Search worker unavailable'})
            finally:
                gate.release()

        def do_GET(self):
            self.reply(404, {'error_type': 'not_found', 'message': 'Unknown worker route'})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', type=Path, required=True, help='Private manifest.json')
    parser.add_argument('--port', type=int, default=8091)
    parser.add_argument('--allow-synthetic', action='store_true')
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--offline-cache', type=Path)
    args = parser.parse_args()
    try:
        index = DiscoveryIndex(args.index)
        if index.meta['engine_kind'] == 'synthetic_fixture':
            encoder = FixtureEncoder(index, enabled=args.allow_synthetic)
        else:
            require(not args.allow_synthetic and args.checkpoint and args.offline_cache,
                    'Explicit checkpoint and offline cache required', 503, 'model_unavailable')
            encoder = ClapTextEncoder(args.checkpoint, args.offline_cache)
        server = make_server(index, encoder, os.environ.get('MUSIC_DISCOVERY_SECRET', ''), args.port)
        print(json.dumps({'status': 'listening', 'host': '127.0.0.1', 'port': server.server_port,
                          'engine_kind': index.meta['engine_kind'], 'index_version': index.meta['index_version'],
                          'model_version': index.meta['model_version']}), flush=True)
        server.serve_forever()
    except Exception:
        print(json.dumps({'status': 'blocked', 'error_type': 'index_or_model_unavailable'}), flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
