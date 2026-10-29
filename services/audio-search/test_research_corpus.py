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


class ActualEOFSource:
    """Header length and returned EOF are independent; the unused buffer is poisoned."""
    def __init__(self, *, header=31 * 48000, actual=30 * 48000 + 13, rate=48000, channels=2,
                 format='MP3', nonfinite=False, tell_mismatch=False, decoder_error=False):
        self.frames, self.actual, self.samplerate, self.channels, self.format = header, actual, rate, channels, format
        self.position, self.calls, self.buffer_ids = 0, 0, []
        self.nonfinite, self.tell_mismatch, self.decoder_error = nonfinite, tell_mismatch, decoder_error

    def __enter__(self): return self
    def __exit__(self, *args): return False
    def tell(self): return self.position + (1 if self.tell_mismatch and self.calls else 0)
    def read(self, *, frames, out):
        import numpy as np
        assert frames == 65536 and out.shape == (65536, self.channels) and out.dtype == np.float32
        self.buffer_ids.append(id(out)); self.calls += 1
        if self.decoder_error and self.calls == 2: raise RuntimeError('synthetic decoder error')
        count = min(frames, max(0, self.actual - self.position))
        out[:] = np.nan  # Only the returned valid view is audio; never append stale/fill bytes.
        out[:count] = np.float32(self.calls / 100)
        if self.channels == 2: out[:count, 1] += np.float32(0.1)
        if self.nonfinite and count and self.calls == 2: out[0, 0] = np.nan
        self.position += count
        return out[:count]

    def recorded(self):
        return {'frames': self.frames, 'sample_rate_hz': self.samplerate, 'channels': self.channels,
                'format': self.format, 'duration_ms': self.frames * 1000 // self.samplerate}


class SourceEOFDecodeTests(unittest.TestCase):
    def decode(self, source, recorded=None):
        import soundfile as sf
        with patch.object(sf, 'SoundFile', return_value=source):
            return research.decode_source_mono('synthetic-only.mp3', source.recorded() if recorded is None else recorded)

    def test_actual_eof_may_be_shorter_than_header_without_tail_padding(self):
        import numpy as np
        source = ActualEOFSource()
        samples, info = self.decode(source)
        self.assertEqual(research.SOURCE_DECODE_VERSION, 'soundfile-read-out-65536-actual-eof-v1')
        self.assertEqual(len(samples), source.actual)
        self.assertLess(len(samples), source.frames)
        self.assertEqual(info['source_frames'], source.actual)
        self.assertEqual(info['declared_source_frames'], source.frames)
        self.assertEqual(set(info), {'format', 'source_frames', 'declared_source_frames', 'source_sample_rate_hz',
                                    'source_channels', 'sample_rate_hz', 'decoded_samples', 'duration_ms'})
        self.assertEqual(source.position, source.actual)
        self.assertEqual(source.calls, (source.actual + 65535) // 65536 + 1)
        self.assertEqual(len(set(source.buffer_ids)), 1)
        self.assertTrue(np.isfinite(samples).all())
        self.assertEqual(samples.dtype, np.float32)
        self.assertTrue(samples.flags.c_contiguous)
        self.assertAlmostEqual(float(samples[0]), 0.06, places=6)
        self.assertAlmostEqual(float(samples[65536]), 0.07, places=6)
        self.assertNotEqual(samples[0], samples[-1])  # Copies must survive reuse of the same output buffer.

    def test_actual_eof_may_exceed_estimated_header(self):
        source = ActualEOFSource(header=30 * 48000, actual=31 * 48000)
        samples, info = self.decode(source)
        self.assertGreater(info['source_frames'], info['declared_source_frames'])
        self.assertEqual(len(samples), 31 * 48000)
        self.assertEqual(info['duration_ms'], 31000)

    def test_exact_30_second_lower_boundary_and_mono(self):
        source = ActualEOFSource(header=30 * 48000, actual=30 * 48000, channels=1)
        samples, info = self.decode(source)
        self.assertEqual(len(samples), 1440000)
        self.assertEqual(samples.ndim, 1)
        self.assertEqual(info['source_channels'], 1)

    def test_actual_eof_under_30_seconds_or_over_600_seconds_rejected(self):
        for actual in (0, 30 * 8000 - 1, 600 * 8000 + 1):
            source = ActualEOFSource(header=30 * 8000, actual=actual, rate=8000, channels=1)
            with self.subTest(actual=actual), self.assertRaises(ValueError): self.decode(source)

    def test_nonfinite_valid_samples_decoder_error_and_tell_mismatch_rejected(self):
        for options, error in (({'nonfinite': True}, ValueError), ({'decoder_error': True}, RuntimeError),
                               ({'tell_mismatch': True}, ValueError)):
            with self.subTest(options=options), self.assertRaises(error): self.decode(ActualEOFSource(**options))

    def test_historical_header_fields_must_match_before_any_reads(self):
        source = ActualEOFSource(); original = source.recorded()
        for key, value in (('frames', source.frames + 1), ('sample_rate_hz', 44100), ('channels', 1),
                           ('format', 'WAV'), ('duration_ms', original['duration_ms'] + 1),
                           ('frames', float(source.frames)), ('extra', 1)):
            changed = {**original, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError): self.decode(source, changed)
            self.assertEqual(source.calls, 0)

    def test_unsupported_header_bounds_rejected_before_any_reads(self):
        for options in ({'format': 'WAV'}, {'channels': 3}, {'rate': 7999}, {'rate': 192001},
                        {'header': 0}, {'header': 600 * 48000 + 1}):
            source = ActualEOFSource(**options)
            with self.subTest(options=options), self.assertRaises(ValueError): self.decode(source)
            self.assertEqual(source.calls, 0)

    def test_integer_ceiling_resample_uses_actual_length_and_original_dsp(self):
        import librosa
        import numpy as np
        source = ActualEOFSource(header=31 * 44100, actual=30 * 44100 + 1, rate=44100, channels=1)
        expected = (source.actual * 48000 + 44100 - 1) // 44100
        with patch.object(librosa, 'resample', return_value=np.full(expected - 1, 0.25, dtype=np.float32)) as resample:
            samples, info = self.decode(source)
        self.assertEqual(len(resample.call_args.args[0]), source.actual)
        self.assertEqual(resample.call_args.kwargs, {'orig_sr': 44100, 'target_sr': 48000,
                                                   'res_type': 'soxr_hq', 'fix': False})
        self.assertEqual(len(samples), expected)
        self.assertEqual(info['decoded_samples'], expected)
        self.assertEqual(info['duration_ms'], expected * 1000 // 48000)
        self.assertLess(len(samples), 31 * 48000)
        self.assertEqual(samples[-1], 0)  # Only the original DSP's integer-ceiling resample correction.


if __name__ == '__main__':
    unittest.main()
