"""Synthetic imported-corpus checks; byte fixtures are not decodable music."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import research_corpus as research
import review_pack as rp
from test_source_review_pack import Fixture


class ResearchFixture:
    def __init__(self, root):
        self.root = root
        source = root / 'source'; source.mkdir()
        self.f = Fixture(source)
        self.audio = root / 'import' / 'audio'; self.audio.mkdir(parents=True)
        for i, row in enumerate(self.f.baseline['audioTracks']):
            sid = row['sourceId']; raw = ('Original synthetic undecodable bytes ' + str(i)).encode()
            row.update(artist='Synthetic old artist', album='', durationSeconds=60,
                       sourceUrl='https://www.jamendo.com/track/' + sid,
                       licenseUrl='https://creativecommons.org/licenses/by/3.0/',
                       license='CC BY 3.0', changes='Audio file unchanged', sha256=rp.digest(raw),
                       rangeVerified=True, fullBytesVerified=True)
            (self.audio / ('jamendo-' + sid + '.mp3')).write_bytes(raw)
            proof = {'sha256': row['sha256'], 'size': len(raw), 'source': row['sourceUrl'],
                     'license': 'http://creativecommons.org/licenses/by/3.0/'}
            (self.audio / ('jamendo-' + sid + '.download.json')).write_bytes(rp.canonical(proof))
        self.f.catalog['audioTracks'][:20] = [{**row, 'sourceProvider': 'jamendo'} for row in self.f.baseline['audioTracks']]
        self.f.save()
        for row in self.f.tracks:
            for extension in ('.mp3', '.download.json'):
                filename = row['source_id'] + extension
                (self.audio / ('incompetech-' + filename)).write_bytes((source / filename).read_bytes())

    def build(self, **changes):
        f = self.f
        args = dict(catalog=f.paths['catalog'], audio_root=self.audio, source_manifest=f.paths['manifest'],
                    decode_report=f.paths['decode'], baseline_catalog=f.paths['baseline'],
                    selection=f.paths['selection'], queries=f.paths['queries'],
                    catalog_sha256=f.catalog_hash, manifest_sha256=f.manifest_hash, decode_sha256=f.decode_hash,
                    baseline_sha256=f.manifest['baseline_catalog_sha256'],
                    selection_sha256=f.manifest['selection_sha256'], queries_sha256=f.query_hash)
        args.update(changes)
        return research.checked_assets(**args)


class ResearchCorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = ResearchFixture(Path(self.temp.name).resolve())

    def test_forty_assets_in_numeric_java_order_with_two_providers(self):
        rows = self.f.build()
        self.assertEqual(len(rows), 40)
        self.assertEqual([int(r['track_id']) for r in rows], sorted(int(r['track_id']) for r in rows))
        self.assertEqual(sum(r['source_provider'] == 'jamendo' for r in rows), 20)
        self.assertEqual(sum(r['source_provider'] == 'incompetech' for r in rows), 20)
        self.assertEqual(len({(r['source_provider'], r['source_id']) for r in rows}), 40)
        for row in rows:
            self.assertEqual(row['asset_filename'], row['source_provider'] + '-' + row['source_id'] + '.mp3')
            self.assertEqual(row['license_url'], 'https://creativecommons.org/licenses/by/' +
                             ('3.0/' if row['source_provider'] == 'jamendo' else '4.0/'))
            self.assertEqual(row['provider_duration_seconds'], 60)
            self.assertEqual(row['content_sha256'], rp.digest((self.f.audio / row['asset_filename']).read_bytes()))
            self.assertEqual(row['download_proof_sha256'], rp.digest((self.f.audio /
                (row['source_provider'] + '-' + row['source_id'] + '.download.json')).read_bytes()))
            self.assertFalse(any(k in row for k in rp.HUMAN_FIELDS))
            if row['source_provider'] == 'incompetech':
                self.assertEqual(row['recorded_decode'], {'frames': 2880000, 'sample_rate_hz': 48000,
                    'channels': 2, 'format': 'MP3', 'duration_ms': 60000})
            else:
                self.assertNotIn('recorded_decode', row)

    def test_all_six_explicit_pins_required_and_checked(self):
        for key in ('catalog_sha256', 'manifest_sha256', 'decode_sha256', 'baseline_sha256',
                    'selection_sha256', 'queries_sha256'):
            for value in (None, 'bad', '0' * 64):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.f.build(**{key: value})

    def test_original_proof_is_exact_four_field_binding(self):
        path = next(self.f.audio.glob('jamendo-*.download.json'))
        original = json.loads(path.read_bytes())
        for key, value in (('size', original['size'] + 1), ('size', float(original['size'])),
                           ('source', original['source'] + '?secret=1'),
                           ('license', 'https://creativecommons.org/licenses/by/4.0/'),
                           ('sha256', '0' * 64), ('extra', 'unexpected')):
            changed = {**original, key: value}; path.write_bytes(rp.canonical(changed))
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): self.f.build()
        path.write_bytes(rp.canonical(original))
        self.assertEqual(len(self.f.build()), 40)  # Recorded http CC BY3 proof normalizes without mutation.

    def test_new_proof_requires_original_source_bytes_not_only_equivalent_json(self):
        path = next(self.f.audio.glob('incompetech-*.download.json'))
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'proof bytes'):
            self.f.build()

    def test_original_source_and_license_do_not_accept_arbitrary_urls(self):
        original = deepcopy(self.f.f.baseline)
        for key, value in (('sourceUrl', 'https://evil.invalid/track/1001'),
                           ('sourceUrl', 'https://www.jamendo.com/track/1001?token=secret'),
                           ('sourceId', '../1001'), ('licenseUrl', 'https://creativecommons.org/licenses/by-nc/3.0/')):
            self.f.f.baseline = deepcopy(original); self.f.f.baseline['audioTracks'][0][key] = value
            self.f.f.catalog['audioTracks'][:20] = [{**row, 'sourceProvider': 'jamendo'} for row in self.f.f.baseline['audioTracks']]
            self.f.f.save()
            with self.subTest(key=key), self.assertRaises(ValueError): self.f.build()

    def test_changed_audio_is_rejected_for_both_providers(self):
        for provider in ('jamendo', 'incompetech'):
            path = next(self.f.audio.glob(provider + '-*.mp3'))
            before = path.read_bytes(); path.write_bytes(before + b'changed')
            with self.subTest(provider=provider), self.assertRaises(ValueError): self.f.build()
            path.write_bytes(before)

    def test_asset_symlinks_are_rejected_even_when_content_matches(self):
        for pattern in ('jamendo-*.mp3', 'incompetech-*.download.json'):
            path = next(self.f.audio.glob(pattern)); alias = self.f.root / 'same-bytes'
            path.rename(alias); path.symlink_to(alias)
            with self.subTest(pattern=pattern), self.assertRaises(ValueError): self.f.build()
            path.unlink(); alias.rename(path)

    def test_hard_links_are_rejected_for_audio_and_proofs(self):
        for pattern in ('jamendo-*.mp3', 'incompetech-*.download.json'):
            path = next(self.f.audio.glob(pattern)); alias = self.f.root / 'hard-linked'
            os.link(path, alias)
            with self.subTest(pattern=pattern), self.assertRaises(ValueError): self.f.build()
            alias.unlink()

    def test_audio_root_symlink_and_source_batch_reuse_are_rejected(self):
        alias = self.f.root / 'audio-alias'; alias.symlink_to(self.f.audio, target_is_directory=True)
        with self.assertRaises(ValueError): self.f.build(audio_root=alias)
        with self.assertRaises(ValueError): self.f.build(audio_root=self.f.f.root)

    def test_missing_and_oversized_assets_fail_without_repairs(self):
        path = next(self.f.audio.glob('jamendo-*.mp3')); before = path.read_bytes()
        path.unlink()
        with self.assertRaises(OSError): self.f.build()
        with path.open('wb') as handle: handle.truncate(30 * 1024 * 1024 + 1)
        with self.assertRaises(ValueError): self.f.build()
        self.assertEqual(path.stat().st_size, 30 * 1024 * 1024 + 1)
        path.write_bytes(before)

    def test_duplicate_provider_source_music_file_and_content_rejected(self):
        original = deepcopy(self.f.f.catalog)
        for key in ('sourceId', 'musicId', 'fileId', 'sha256'):
            self.f.f.catalog = deepcopy(original)
            self.f.f.catalog['audioTracks'][21][key] = self.f.f.catalog['audioTracks'][20][key]
            self.f.f.save()
            with self.subTest(key=key), self.assertRaises(ValueError): self.f.build()

    def test_unknown_provider_and_old_copy_changes_are_rejected(self):
        original = deepcopy(self.f.f.catalog)
        for index, key, value in ((20, 'sourceProvider', 'other'), (0, 'title', 'Changed old'),
                                  (20, 'sourceId', 'usabc1000000'), (20, 'fullBytesVerified', False)):
            self.f.f.catalog = deepcopy(original); self.f.f.catalog['audioTracks'][index][key] = value
            self.f.f.save()
            with self.subTest(index=index, key=key), self.assertRaises(ValueError): self.f.build()

    def test_changed_copy_during_validation_is_not_accepted(self):
        original = rp.read_json; path = next(self.f.audio.glob('jamendo-*.mp3'))
        def read_then_change(target, *args, **kwargs):
            value = original(target, *args, **kwargs)
            if Path(target).parent == self.f.audio and Path(target).name.startswith('incompetech-'):
                path.write_bytes(b'Changed after first imported audio check')
            return value
        with patch.object(rp, 'read_json', side_effect=read_then_change):
            with self.assertRaisesRegex(ValueError, 'changed during asset validation'):
                self.f.build()

    def test_no_inputs_are_mutated(self):
        before = {p: (p.read_bytes(), p.stat().st_mode) for p in self.f.root.rglob('*') if p.is_file()}
        self.f.build()
        after = {p: (p.read_bytes(), p.stat().st_mode) for p in self.f.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
