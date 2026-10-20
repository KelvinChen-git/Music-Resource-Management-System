"""License/download policy guards; no network or database writes."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import import_demo_music as importer
from import_demo_music import eligible


class DemoMusicGuardsTest(unittest.TestCase):
    def setUp(self):
        self.track = dict(id='123', duration=180, audiodownload_allowed=True,
                          license_ccurl='https://creativecommons.org/licenses/by/4.0/',
                          audiodownload='https://prod-1.storage.jamendo.com/download/track/123/mp32/')

    def test_explicit_download_and_cc_by_are_both_required(self):
        self.assertTrue(eligible(self.track))
        for change in [dict(audiodownload_allowed=False), dict(audiodownload_allowed='true'),
                       dict(license_ccurl='https://creativecommons.org/licenses/by-nc/4.0/'),
                       dict(license_ccurl='https://creativecommons.org/licenses/by-nd/4.0/'),
                       dict(license_ccurl='https://creativecommons.org/licenses/by-sa/4.0/')]:
            with self.subTest(change=change):self.assertFalse(eligible({**self.track,**change}))

    def test_download_scheme_and_provider_host_are_checked(self):
        for url in ['http://prod-1.storage.jamendo.com/download/123',
                    'https://jamendo.com.evil.example/a.mp3','https://127.0.0.1/a.mp3','file:///a.mp3']:
            with self.subTest(url=url):self.assertFalse(eligible({**self.track,'audiodownload':url}))

    def test_license_url_cannot_impersonate_creative_commons(self):
        for url in ['https://creativecommons.org.evil.example/licenses/by/4.0/',
                    'https://example.com/licenses/by/4.0/','https://creativecommons.org/licenses/by/unknown/']:
            with self.subTest(url=url):self.assertFalse(eligible({**self.track,'license_ccurl':url}))

    def test_invalid_ids_and_unbounded_duration_are_rejected(self):
        for change in [dict(id='../../other'),dict(duration=None),dict(duration='invalid'),dict(duration=0),dict(duration=36000)]:
            with self.subTest(change=change):self.assertFalse(eligible({**self.track,**change}))

    def test_existing_import_lock_is_preserved_without_network_or_uploads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / '.local/a/music-catalog'
            state.mkdir(parents=True)
            lock = state / 'import.lock'
            lock.write_text('existing owner')
            with patch.object(importer, 'ROOT', root), patch.object(importer, 'read_env'), \
                    patch.object(importer, 'validate'), patch.object(importer, '_run') as run:
                with self.assertRaises(FileExistsError):importer.run('a',20)
                run.assert_not_called()
                self.assertEqual('existing owner',lock.read_text())


if __name__ == '__main__':unittest.main()
