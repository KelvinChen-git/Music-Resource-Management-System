"""Synthetic index and real loopback worker checks. Never loads a semantic model."""
import copy
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/audio-search"))

import numpy as np
from discovery_index import DiscoveryError, DiscoveryIndex, FixtureEncoder, strict_json
from discovery_server import make_server
from make_discovery_fixture import write_fixture


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'index'
        self.tracks = [{'track_id': str(i), 'duration_ms': 25000, 'content_bytes': 1000 + i,
                        'content_md5': ('%032x' % i), 'content_sha256': ('%064x' % i)} for i in (1, 2, 3)]
        self.meta = write_fixture(self.root, self.tracks)
        self.index = DiscoveryIndex(self.root / 'manifest.json')
        self.encoder = FixtureEncoder(self.index, enabled=True)

    def body(self, **overrides):
        return {'query_text': 'synthetic tone 440', 'retrieval_mode': 'segment', 'top_k': 3,
                'index_version': self.meta['index_version'], 'model_version': self.meta['model_version'],
                'allowed_tracks': [{k: row[k] for k in ('track_id', 'content_md5', 'content_bytes')}
                                   for row in self.tracks], **overrides}

    def rewrite(self, meta):
        (self.root / 'manifest.json').write_text(json.dumps(meta))

    def test_exact_segment_results_and_nondoverlapping_times(self):
        result = self.index.search(self.body(), self.encoder)
        self.assertEqual([r['track_id'] for r in result['results']], ['1', '2', '3'])
        self.assertEqual(result['results'][0]['score'], 1.)
        self.assertEqual(result['engine_kind'], 'synthetic_fixture')
        for row in result['results']:
            self.assertEqual(len(row['segments']), 3)
            ordered = sorted(row['segments'], key=lambda s: s['start_ms'])
            self.assertEqual([(s['start_ms'], s['end_ms']) for s in ordered], [(0, 10000), (10000, 20000), (20000, 25000)])

    def test_whole_mode_and_numeric_id_tie_order(self):
        result = self.index.search(self.body(retrieval_mode='whole_track', query_text='synthetic tone 660'), self.encoder)
        self.assertEqual([r['track_id'] for r in result['results']], ['2', '1', '3'])

    def test_current_allowed_content_is_filtered_before_topk(self):
        allowed = self.body()['allowed_tracks']
        allowed[0]['content_md5'] = 'f' * 32
        result = self.index.search(self.body(allowed_tracks=allowed, top_k=1), self.encoder)
        self.assertEqual(result['results'][0]['track_id'], '2')
        self.assertNotIn('1', [r['track_id'] for r in result['results']])

    def test_empty_allowed_set_does_not_encode(self):
        result = self.index.search(self.body(allowed_tracks=[], query_text='not in fixture'), self.encoder)
        self.assertEqual(result['results'], [])
        self.assertEqual(result['timings_ms']['query_encoding'], 0)

    def test_version_mismatch_fails_closed(self):
        for key in ('index_version', 'model_version'):
            with self.assertRaises(DiscoveryError) as error:
                self.index.search(self.body(**{key: 'different'}), self.encoder)
            self.assertEqual((error.exception.status, error.exception.kind), (503, 'version_mismatch'))

    def test_invalid_inputs_and_modes_rejected(self):
        for change in ({'query_text': ''}, {'query_text': 'a' * 1001}, {'top_k': True}, {'top_k': 0},
                       {'top_k': 21}, {'retrieval_mode': 'hybrid'}, {'extra': True}):
            with self.subTest(change=change), self.assertRaises(DiscoveryError):
                self.index.search(self.body(**change), self.encoder)

    def test_duplicate_allowed_id_and_noncanonical_id_rejected(self):
        allowed = self.body()['allowed_tracks']
        with self.assertRaises(DiscoveryError): self.index.search(self.body(allowed_tracks=allowed + [allowed[0]]), self.encoder)
        allowed[0]['track_id'] = '01'
        with self.assertRaises(DiscoveryError): self.index.search(self.body(allowed_tracks=allowed), self.encoder)

    def test_fixture_needs_explicit_opt_in_and_has_no_unknown_query_fallback(self):
        with self.assertRaises(DiscoveryError): FixtureEncoder(self.index)
        with self.assertRaises(DiscoveryError) as error:
            self.index.search(self.body(query_text='calm piano'), self.encoder)
        self.assertEqual(error.exception.kind, 'fixture_query_unavailable')

    def test_index_time_duplicate_and_feature_pin_refused(self):
        for change in ('time', 'duplicate', 'pin'):
            meta = copy.deepcopy(self.meta)
            if change == 'time': meta['segments'][0]['end_ms'] = 25001
            if change == 'duplicate': meta['segments'][1] = copy.deepcopy(meta['segments'][0])
            if change == 'pin': meta['feature_sha256'] = '0' * 64
            self.rewrite(meta)
            with self.subTest(change=change), self.assertRaises(DiscoveryError): DiscoveryIndex(self.root / 'manifest.json')

    def test_nonfinite_and_wrong_whole_recipe_refused(self):
        for corrupt in ('nan', 'wrong_whole'):
            with np.load(self.root / 'features.npz', allow_pickle=False) as f:
                segments, whole = f['segments'].copy(), f['whole'].copy()
            if corrupt == 'nan': segments[0, 0] = np.nan
            else: segments[:] = 0; segments[:, 0] = 1; whole[:] = 0; whole[:, 1] = 1
            np.savez(self.root / 'features.npz', segments=segments, whole=whole)
            meta = copy.deepcopy(self.meta)
            meta['feature_sha256'] = hashlib.sha256((self.root / 'features.npz').read_bytes()).hexdigest()
            self.rewrite(meta)
            with self.subTest(corrupt=corrupt), self.assertRaises(DiscoveryError): DiscoveryIndex(self.root / 'manifest.json')

    def test_index_symlinks_and_existing_output_refused(self):
        link = self.root.parent / 'linked.json'; link.symlink_to(self.root / 'manifest.json')
        with self.assertRaises(DiscoveryError): DiscoveryIndex(link)
        with self.assertRaises(FileExistsError): write_fixture(self.root, self.tracks)

    def test_duplicate_and_nonfinite_json_refused(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{'):
            with self.assertRaises(DiscoveryError): strict_json(raw)

    def server(self):
        server = make_server(self.index, self.encoder, 's' * 64, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        return server.server_port

    def request(self, port, raw=None, secret='s' * 64, **headers):
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        try:
            raw = json.dumps(self.body()) if raw is None else raw
            connection.request('POST', '/internal/search', raw,
                               {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + secret, **headers})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_actual_worker_http_requires_private_auth(self):
        port = self.server()
        status, body = self.request(port, secret='wrong')
        self.assertEqual(status, 401)
        self.assertEqual(body['error_type'], 'unauthorized')
        status, body = self.request(port)
        self.assertEqual(status, 200)
        self.assertEqual(body['results'][0]['track_id'], '1')

    def test_actual_worker_http_rejects_duplicate_and_oversized_body(self):
        port = self.server()
        self.assertEqual(self.request(port, raw='{"x":1,"x":2}')[0], 400)
        self.assertEqual(self.request(port, raw='{}', **{'Content-Length': str(2 * 1024 * 1024 + 1)})[0], 413)


if __name__ == '__main__':
    unittest.main()
