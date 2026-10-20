"""Exercise the real smoke workflow with in-memory HTTP and SQL transports only."""
import io
import json
import subprocess
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch
from urllib.parse import urlsplit

import review_findings_smoke as smoke


class Reply:
    def __init__(self, status=200, data=None):
        self.status = status
        self.payload = json.dumps({'code': status, 'data': data}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return self.payload


class Transport:
    prefix = 'r-0123456789'

    def __init__(self, old_runtime=False):
        self.old_runtime = old_runtime
        self.registered = self.uploads = self.delete_attempts = 0
        self.role = 'USER'
        self.deleted = self.soft_deleted = self.created = False
        self.body_error = self.promotion_error = self.demotion_error = None
        self.delete_errors = {}
        self.sql_calls = []

    def http(self, request, timeout):
        assert request.full_url.startswith('http://127.0.0.1:8081/api/')
        path = urlsplit(request.full_url).path.removeprefix('/api')
        method = request.get_method()
        if path == '/auth/register':
            self.registered += 1
            return Reply(data={'userid': self.registered})
        if path == '/auth/login':
            return Reply(data={'token': 'fixture-token'})
        if path == '/file/upload':
            self.uploads += 1
            if self.body_error:
                raise self.body_error
            return Reply(data={'id': 9 if self.uploads == 1 else 10, 'filePath': 'fixture.png'})
        if path == '/music-resources/metadata':
            if self.soft_deleted:
                return Reply(404)
            self.deleted = False
            return Reply(data={})
        if path == '/music-resources/list':
            return Reply(data={'records': [{'musicid': 42}]})
        if path == '/music-resources/42/reject':
            return Reply(data=True)
        if path == '/music-resources/42' and method == 'DELETE':
            self.soft_deleted = True
            return Reply(data=True)
        if path == '/file/download/9':
            return Reply(200 if self.deleted else 404)
        if path == '/music/42' and method == 'DELETE':
            if not request.get_header('Authorization'):
                return Reply(401)
            if self.old_runtime:
                self.deleted = True
                return Reply(204)
            return Reply(410)
        if path == '/users':
            self.created = self.old_runtime
            return Reply(200 if self.old_runtime else 400)
        if path == '/uploads/fixture.png':
            return Reply(200 if self.created else 401)
        raise AssertionError('Unexpected synthetic HTTP route: ' + path)

    def sql(self, command, **kwargs):
        assert '--host=127.0.0.1' in command
        assert '--port=3308' in command
        assert '--database=music_dev_b' in command
        sql = kwargs['input']
        self.sql_calls.append(sql)
        if sql.startswith("UPDATE users SET role='ADMIN'"):
            self.role = 'ADMIN'  # A client error can occur after the DB committed.
            if self.promotion_error:
                raise self.promotion_error
            output = ''
        elif sql.startswith("UPDATE users SET role='USER'"):
            if self.demotion_error:
                raise self.demotion_error
            self.role = 'USER'
            output = ''
        elif sql.startswith('DELETE FROM users'):
            self.delete_attempts += 1
            if self.delete_attempts in self.delete_errors:
                raise self.delete_errors[self.delete_attempts]
            self.created = False
            output = ''
        elif sql.startswith('SELECT COUNT(*) FROM music_resources'):
            output = '0' if self.deleted else '1'
        elif sql.startswith('SELECT is_deleted FROM music_resources'):
            output = '1' if self.soft_deleted else '0'
        elif sql.startswith('SELECT COUNT(*) FROM users'):
            output = '1' if self.created else '0'
        else:
            raise AssertionError('Unexpected synthetic SQL: ' + sql)
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr='')


class CleanupTest(unittest.TestCase):
    def setUp(self):
        root = smoke.ROOT / '.local/b'
        self.env = {
            'SPRING_PROFILES_ACTIVE': 'local', 'MUSIC_DB_HOST': '127.0.0.1',
            'MUSIC_DB_PORT': '3308', 'MUSIC_DB_NAME': 'music_dev_b',
            'MUSIC_DB_USER': 'music_dev_b', 'MUSIC_DB_PASSWORD': 'fixture-only',
            'MUSIC_SERVER_PORT': '8081', 'VITE_DEV_PORT': '5174',
            'VITE_PROXY_TARGET': 'http://127.0.0.1:8081',
            'MUSIC_UPLOAD_PATH': str(root / 'uploads'),
            'MUSIC_UPLOAD_TEMP_PATH': str(root / 'chunks'),
        }
        self.stderr = io.StringIO()

    def run_fixture(self, transport, mode='verify'):
        with patch.object(smoke, 'read_env', return_value=self.env), \
             patch.object(smoke.secrets, 'token_hex', return_value='0123456789'), \
             patch.object(smoke, 'urlopen', side_effect=transport.http), \
             patch.object(smoke.subprocess, 'run', side_effect=transport.sql), \
             redirect_stderr(self.stderr):
            return smoke.run('b', mode, mysql='/synthetic/nonexecuted/mysql')

    def assert_demoted(self, transport):
        self.assertEqual('USER', transport.role)
        self.assertEqual(
            "UPDATE users SET role='USER' WHERE userid=3 AND email='r-0123456789-admin@example.invalid';",
            transport.sql_calls[-1])

    def test_verify_success_keeps_eleven_checks_and_limits_cleanup_to_its_fixtures(self):
        t = Transport()
        result = self.run_fixture(t)
        self.assertEqual(('passed', 11), (result['status'], result['check_count']))
        self.assertEqual(11, len(result['checks']))
        self.assertEqual(2, t.delete_attempts)
        deletes = [s for s in t.sql_calls if s.startswith('DELETE FROM users')]
        self.assertEqual(["DELETE FROM users WHERE email='r-0123456789-created@example.invalid';"] * 2, deletes)
        self.assert_demoted(t)

    def test_observe_success_remains_observed_with_three_checks(self):
        t = Transport(old_runtime=True)
        result = self.run_fixture(t, 'observe')
        self.assertEqual(('observed', 3), (result['status'], result['check_count']))
        self.assertTrue(result['observations']['R1']['rebind_succeeded'])
        self.assertFalse(t.created)
        self.assert_demoted(t)

    def test_body_error_is_preserved_when_cleanup_succeeds(self):
        t = Transport()
        t.body_error = RuntimeError('HTTP failed')
        with self.assertRaises(RuntimeError) as caught:
            self.run_fixture(t)
        self.assertIs(t.body_error, caught.exception)
        self.assertEqual(1, t.delete_attempts)
        self.assert_demoted(t)

    def test_cleanup_delete_failure_still_demotes_and_preserves_body_error(self):
        t = Transport()
        t.body_error = RuntimeError('HTTP failed')
        t.delete_errors[1] = RuntimeError('delete failed')
        with self.assertRaises(RuntimeError) as caught:
            self.run_fixture(t)
        self.assert_demoted(t)
        self.assertIs(t.body_error, caught.exception)
        self.assertIn('bypass account deletion', self.stderr.getvalue())

    def test_demotion_failure_is_reported_without_hiding_body_error(self):
        t = Transport()
        t.body_error = RuntimeError('HTTP failed')
        t.demotion_error = RuntimeError('demotion failed')
        with self.assertRaises(RuntimeError) as caught:
            self.run_fixture(t)
        self.assertIs(t.body_error, caught.exception)
        self.assertIn('administrator demotion', self.stderr.getvalue())
        self.assertIn('r-0123456789', self.stderr.getvalue())

    def test_both_cleanup_errors_are_reported_and_primary_error_is_preserved(self):
        t = Transport()
        t.body_error = RuntimeError('HTTP failed')
        t.delete_errors[1] = RuntimeError('delete failed')
        t.demotion_error = RuntimeError('demotion failed')
        with self.assertRaises(RuntimeError) as caught:
            self.run_fixture(t)
        self.assertIs(t.body_error, caught.exception)
        self.assertIn('bypass account deletion', self.stderr.getvalue())
        self.assertIn('administrator demotion', self.stderr.getvalue())

    def test_ambiguous_promotion_failure_is_also_inside_cleanup_scope(self):
        t = Transport()
        t.promotion_error = RuntimeError('promotion response lost')
        with self.assertRaises(RuntimeError) as caught:
            self.run_fixture(t)
        self.assert_demoted(t)
        self.assertEqual(1, t.delete_attempts)
        self.assertIs(t.promotion_error, caught.exception)

    def test_cleanup_failure_overrides_success_instead_of_returning_passed(self):
        t = Transport()
        t.delete_errors[2] = RuntimeError('delete failed')
        with self.assertRaisesRegex(RuntimeError, 'cleanup incomplete') as caught:
            self.run_fixture(t)
        self.assert_demoted(t)
        self.assertIs(t.delete_errors[2], caught.exception.__cause__)

    def test_demotion_failure_after_success_cannot_return_passed(self):
        t = Transport()
        t.demotion_error = RuntimeError('demotion failed')
        with self.assertRaisesRegex(RuntimeError, 'administrator demotion'):
            self.run_fixture(t)
        self.assertEqual(2, t.delete_attempts)
        self.assertEqual('ADMIN', t.role)  # Explicit failure; never claim cleanup succeeded.

    def test_body_interrupt_is_preserved_after_cleanup(self):
        t = Transport()
        t.body_error = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.run_fixture(t)
        self.assert_demoted(t)
        self.assertIs(t.body_error, caught.exception)

    def test_interrupt_during_delete_still_attempts_demotion(self):
        t = Transport()
        t.delete_errors[2] = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_fixture(t)
        self.assert_demoted(t)


if __name__ == '__main__':
    unittest.main()
