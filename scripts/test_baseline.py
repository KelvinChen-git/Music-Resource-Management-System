"""Guard regressions for native development bootstrap; no real services started."""
import argparse
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import baseline


class BaselineGuardsTest(unittest.TestCase):
    def setUp(self):
        self.env = {'MUSIC_DB_HOST': '127.0.0.1', 'SPRING_PROFILES_ACTIVE': 'local',
                    'MUSIC_DB_NAME': 'music_dev_a', 'MUSIC_DB_USER': 'music_dev_a',
                    'MUSIC_DB_PORT': '3307', 'MUSIC_SERVER_PORT': '8080', 'VITE_DEV_PORT': '5173',
                    'VITE_PROXY_TARGET': 'http://127.0.0.1:8080',
                    'MUSIC_UPLOAD_PATH': str(baseline.ROOT / '.local/a/uploads'),
                    'MUSIC_UPLOAD_TEMP_PATH': str(baseline.ROOT / '.local/a/chunks')}

    def test_valid_slot_and_existing_schema_can_be_reused(self):
        baseline.validate('a', self.env)
        self.assertEqual('reuse_existing', baseline.schema_action(11, ['1', '2']))

    def test_only_completely_empty_schema_can_be_initialized(self):
        self.assertEqual('initialize_empty', baseline.schema_action(0, []))
        for count, versions in [(1, []), (10, ['1']), (11, []), (11, ['2']), (12, ['1']), (11, ['1'])]:
            with self.subTest(count=count, versions=versions):
                with self.assertRaises(RuntimeError):
                    baseline.schema_action(count, versions)

    def test_existing_v001_requires_explicit_migration(self):
        self.assertEqual('migrate_upload_ownership', baseline.schema_action(11, ['1'], migrate=True))
        with self.assertRaises(RuntimeError):
            baseline.schema_action(10, ['1'], migrate=True)

    def test_wrong_database_or_account_is_refused(self):
        for key in ['MUSIC_DB_NAME', 'MUSIC_DB_USER']:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                baseline.validate('a', {**self.env, key: 'production'})

    def test_cross_checkout_upload_directories_are_refused(self):
        for key in ['MUSIC_UPLOAD_PATH', 'MUSIC_UPLOAD_TEMP_PATH']:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                baseline.validate('a', {**self.env, key: '/another-checkout/.local/a/uploads'})

    def test_nonlocal_host_or_profile_is_refused(self):
        for key, value in [('MUSIC_DB_HOST', '192.168.1.2'), ('SPRING_PROFILES_ACTIVE', 'prod')]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                baseline.validate('a', {**self.env, key: value})

    def test_overlapping_ports_or_wrong_proxy_are_refused(self):
        for key, value in [('MUSIC_DB_PORT', '3308'), ('MUSIC_SERVER_PORT', '8081'),
                           ('VITE_DEV_PORT', '5174'), ('VITE_PROXY_TARGET', 'http://127.0.0.1:8081')]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                baseline.validate('a', {**self.env, key: value})

    def test_denied_socket_stops_before_database_or_build_side_effects(self):
        runner = baseline.Baseline.__new__(baseline.Baseline)
        runner.args = argparse.Namespace(slot='a')
        runner.env = self.env
        with patch.object(baseline, 'network_preflight', side_effect=PermissionError(1, 'denied')), \
                patch.object(baseline, 'discover') as discover, \
                patch.object(runner, 'database') as database, \
                patch.object(runner, 'command') as command:
            with self.assertRaises(PermissionError):
                runner.run()
            discover.assert_not_called()
            database.assert_not_called()
            command.assert_not_called()

    def test_shutdown_only_signals_owned_process_groups(self):
        runner = baseline.Baseline.__new__(baseline.Baseline)
        owned = Mock(pid=12345)
        owned.poll.return_value = None
        runner.children, runner.socketdir = [owned], None
        with patch.object(baseline.os, 'killpg') as kill:
            runner.stop()
            kill.assert_called_once_with(12345, baseline.signal.SIGTERM)
            owned.wait.assert_called_once_with(timeout=15)


if __name__ == '__main__':
    unittest.main()
