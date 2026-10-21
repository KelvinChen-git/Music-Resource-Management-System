"""Exercise the actual importer entry point with synthetic provider/local API transport.

No real network, credentials, MP3 decoder, JVM or database is used here.
"""
import io
import json
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import import_demo_music as importer


class Response(io.BytesIO):
    def __init__(self, value, status=200, url='http://127.0.0.1/fixture'):
        super().__init__(value if isinstance(value, bytes) else json.dumps(value).encode())
        self.status, self.url = status, url


class Transport:
    def __init__(self):
        self.audio = b'ID3 controlled synthetic bytes; not decoded audio'
        self.track = dict(id='123', duration=180, artist_id='7', name='Fixture Song',
                          artist_name='Synthetic', album_name='Fixture Album',
                          license_ccurl='https://creativecommons.org/licenses/by/4.0/',
                          audiodownload_allowed=True,
                          shareurl='https://www.jamendo.com/track/123',
                          audiodownload='https://prod-1.storage.jamendo.com/download/123')
        self.accounts, self.uploads, self.resources = {}, [], []
        self.calls, self.register_fault, self.login_error = [], None, None
        self.provider_calls = 0

    def open(self, request, **kwargs):
        parsed = urlparse(request.full_url)
        if parsed.scheme == 'https':
            assert kwargs['context'].verify_mode == ssl.CERT_REQUIRED
            self.provider_calls += 1
            if parsed.hostname == 'api.jamendo.com':
                return Response({'headers': {'code': 0}, 'results': [self.track]})
            return Response(self.audio, url=self.track['audiodownload'])
        assert parsed.hostname == '127.0.0.1' and parsed.port == 18081
        method, path = request.get_method(), parsed.path.removeprefix('/api')
        body = json.loads(request.data) if request.headers.get('Content-type') == 'application/json' else None
        self.calls.append((method, path))
        def response(data=None, code=200, message='success'):
            return Response({'code': code, 'message': message, 'data': data})
        if path == '/auth/register':
            fault, self.register_fault = self.register_fault, None
            if fault == 'before': raise URLError('fixture before request delivery')
            if fault == 'reject': return response(code=500, message='Fixture registration rejected')
            if body['email'] in self.accounts: return response(code=500, message='Email already registered')
            self.accounts[body['email']] = dict(body)
            if fault == 'after': raise URLError('fixture response lost after registration')
            return response({'userid': 1})
        if path == '/auth/login':
            if self.login_error: return response(code=500, message=self.login_error)
            account = self.accounts.get(body['email'])
            if not account or account['password'] != body['password']:
                return response(code=500, message='Invalid email or password')
            return response({'token': 'synthetic-token'})
        assert request.get_header('Authorization') == 'Bearer synthetic-token'
        if path == '/auth/profile': return response({'userid': 1, 'role': 'USER'})
        if path == '/file/check': return response({'exists': bool(self.uploads), 'fileId': 91})
        if path == '/file/upload':
            self.uploads.append(self.audio)
            return response({'id': 91})
        if path == '/music-resources/metadata':
            assert parse_qs(parsed.query)['fileId'] == ['91']
            self.resources.append({'musicid': 101, **body})
            return response(self.resources[-1])
        if path == '/music-resources/list': return response({'records': self.resources})
        if path == '/music-resources/101/file':
            return Response(self.audio[:64] if request.get_header('Range') else self.audio,
                            status=206 if request.get_header('Range') else 200)
        raise AssertionError('Unexpected fixture endpoint ' + path)


class ImportRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / ".local/a").mkdir(parents=True)
        self.transport = Transport()
        for name, value in [('ROOT', self.root), ('read_env', lambda slot: {'MUSIC_SERVER_PORT': '18081'}),
                            ('validate', lambda slot, env: None), ('urlopen', self.transport.open)]:
            patcher = patch.object(importer, name, value); patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.dict('os.environ', {'JAMENDO_CLIENT_ID': 'SyntheticCanary123'})
        patcher.start(); self.addCleanup(patcher.stop)

    @property
    def state(self): return self.root / '.local/a/music-catalog'

    def run_import(self): return importer.run('a', 1)

    def counts(self):
        return (len(self.transport.accounts), len(self.transport.uploads), len(self.transport.resources))

    def interrupted_registration(self, fault):
        self.transport.register_fault = fault
        with self.assertRaises((RuntimeError, URLError)): self.run_import()
        credentials = (self.state/'demo-account.json').read_bytes()
        self.assertEqual(self.counts(), (0,0,0))
        self.assertFalse((self.state/'import.lock').exists())
        self.assertEqual(self.run_import()['status'], 'passed')
        self.assertEqual((self.state/'demo-account.json').read_bytes(), credentials)
        self.assertEqual(self.counts(), (1,1,1))
        self.assertEqual(sum(path=='/auth/register' for _,path in self.transport.calls), 2)

    def test_register_before_delivery_retries_same_saved_credentials(self):
        self.interrupted_registration('before')

    def test_explicit_registration_rejection_keeps_pending_and_can_retry(self):
        self.interrupted_registration('reject')

    def test_lost_success_response_does_not_create_second_account(self):
        self.transport.register_fault = 'after'
        try: self.run_import()
        except (RuntimeError, URLError): pass
        credentials = (self.state/'demo-account.json').read_bytes()
        self.assertEqual(self.run_import()['status'], 'passed')
        self.assertEqual(self.counts(), (1,1,1))
        self.assertEqual((self.state/'demo-account.json').read_bytes(), credentials)
        self.assertEqual(sum(path=='/auth/register' for _,path in self.transport.calls), 1)

    def test_legacy_credentials_without_new_state_login_without_register(self):
        self.run_import()
        (self.state/'demo-account-state.json').unlink(missing_ok=True)
        self.transport.calls.clear()
        self.run_import()
        self.assertNotIn(('POST','/auth/register'), self.transport.calls)
        self.assertEqual(self.counts(), (1,1,1))

    def test_confirmed_login_failure_never_reregisters(self):
        self.run_import(); self.transport.calls.clear()
        self.transport.login_error = 'Invalid email or password'
        with self.assertRaises(RuntimeError): self.run_import()
        self.assertNotIn(('POST','/auth/register'), self.transport.calls)
        self.assertEqual(self.counts(), (1,1,1))

    def test_pending_server_error_does_not_guess_account_missing(self):
        self.transport.login_error = 'Fixture database unavailable'
        with self.assertRaises(RuntimeError): self.run_import()
        self.assertNotIn(('POST','/auth/register'), self.transport.calls)
        self.assertEqual(self.counts(), (0,0,0))

    def test_cached_proof_binding_fields_reject_and_preserve_mismatch(self):
        self.run_import()
        proof_path=self.state/'123.download.json';original=json.loads(proof_path.read_text())
        for field, value in [('size',1), ('source','https://example.invalid/track/123'),
                             ('license','https://creativecommons.org/licenses/by/3.0/')]:
            with self.subTest(field=field):
                proof_path.write_text(json.dumps({**original,field:value}))
                before=proof_path.read_bytes(); self.transport.calls.clear()
                with self.assertRaises(RuntimeError): self.run_import()
                self.assertEqual(proof_path.read_bytes(),before)
                self.assertEqual(self.transport.calls,[])
                self.assertFalse((self.state/'import.lock').exists())
        proof_path.write_text(json.dumps(original))

    def test_cached_proof_requires_complete_size_field(self):
        self.run_import();proof=self.state/'123.download.json'
        value=json.loads(proof.read_text());del value['size'];proof.write_text(json.dumps(value))
        with self.assertRaises((RuntimeError,ValueError,KeyError)):self.run_import()

    def test_confirmed_state_permissions_and_credential_mismatch_fail_closed(self):
        self.run_import()
        state_path=self.state/'demo-account-state.json'
        state=json.loads(state_path.read_text())
        self.assertEqual(state['status'],'confirmed')
        self.assertEqual(state['user_id'],'1')
        self.assertEqual(state_path.stat().st_mode & 0o777,0o600)
        credentials=self.state/'demo-account.json';value=json.loads(credentials.read_text())
        value['password']='ChangedFixturePassword1!';credentials.write_text(json.dumps(value))
        self.transport.calls.clear()
        before=state_path.read_bytes()
        with self.assertRaises(RuntimeError):self.run_import()
        self.assertEqual(self.transport.calls,[])
        self.assertEqual(state_path.read_bytes(),before)
        self.assertEqual(self.counts(),(1,1,1))

    def test_complete_cache_has_no_new_provider_requests_or_local_objects(self):
        self.run_import();provider_calls=self.transport.provider_calls
        self.run_import()
        self.assertEqual(self.transport.provider_calls,provider_calls)
        self.assertEqual(self.counts(),(1,1,1))

    def test_source_query_canary_never_enters_public_catalog(self):
        self.transport.track['shareurl']+='?client_id=SyntheticCanary123#secret-fragment'
        self.run_import()
        public=(self.root/'web/public/demo-catalog.json').read_text()
        self.assertNotIn('SyntheticCanary123',public)
        self.assertNotIn('secret-fragment',public)
        self.assertEqual(json.loads(public)['audioTracks'][0]['sourceUrl'],'https://www.jamendo.com/track/123')

    def test_bad_source_identity_rejected_before_any_local_api(self):
        for value in ['https://user@www.jamendo.com/track/123','https://www.jamendo.com/track/456',
                      'https://www.jamendo.com:444/track/123','https://example.invalid/track/123']:
            with self.subTest(value=value):
                self.transport.track['shareurl']=value
                with self.assertRaises(RuntimeError):self.run_import()
                self.assertEqual(self.transport.calls,[])


if __name__=='__main__':unittest.main()
