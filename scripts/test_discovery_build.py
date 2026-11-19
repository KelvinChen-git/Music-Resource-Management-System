"""Explicit synthetic boundary tests plus generated MP3 decode controls, never a CLAP run."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/audio-search'))
import numpy as np
import discovery_build as producer
import discovery_index as consumer


class SyntheticEncoder:
    calls = 0
    windows = []
    mutate = None
    invalid = False
    cache_fingerprints = {name: '1' * 64 for name in consumer.CACHE_REQUIRED}

    def __init__(self, *args):
        type(self).calls += 1

    def encode_audio(self, waveforms):
        type(self).windows.append(waveforms.copy())
        if type(self).mutate:
            type(self).mutate()
        result = np.zeros((len(waveforms), 512), dtype=np.float32)
        result[:, 0] = 0 if type(self).invalid else 1
        return result

    def verify_assets(self):
        pass


class DiscoveryBuildTest(unittest.TestCase):
    def setUp(self):
        parent = producer.ROOT / '.local/b'
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='explicit-build-test-', dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.audio = self.root / 'audio'; self.audio.mkdir()
        self.cache = self.root / 'cache'; self.cache.mkdir()
        self.checkpoint = self.root / 'explicit-synthetic-checkpoint'; self.checkpoint.write_bytes(b'test double only')
        self.catalog = self.root / 'catalog.json'
        self.row = self.asset('1')
        self.write_catalog([self.row])
        SyntheticEncoder.calls, SyntheticEncoder.windows = 0, []
        SyntheticEncoder.mutate, SyntheticEncoder.invalid = None, False

    def asset(self, tid):
        raw = ('explicit synthetic bytes, decoder is mocked ' + tid).encode()
        name = tid + '.mp3'; (self.audio / name).write_bytes(raw)
        evidence_name = tid + '.html'; (self.audio / evidence_name).write_bytes(b'explicit synthetic evidence')
        row = {'track_id': tid, 'audio_filename': name, 'content_bytes': len(raw),
               'content_md5': hashlib.md5(raw).hexdigest(), 'content_sha256': hashlib.sha256(raw).hexdigest(),
               'proof_filename': tid + '.source.json'}
        proof = {'schema': 'sonora-discovery-source-proof-v1', 'track_id': tid,
                 'source_url': 'https://example.invalid/explicit-test/' + tid,
                 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                 'title': 'Synthetic test', 'artist': 'Test double', 'attribution': 'Test only',
                 'changes': 'Not real music or legal evidence',
                 **{k: row[k] for k in ('content_bytes', 'content_md5', 'content_sha256')},
                 'evidence': [{'filename': evidence_name, 'sha256': consumer.file_hash(self.audio / evidence_name)}]}
        producer.write_json(self.audio / row['proof_filename'], proof)
        row['proof_sha256'] = consumer.file_hash(self.audio / row['proof_filename'])
        return row

    def write_catalog(self, rows):
        self.catalog.write_text(json.dumps({'schema': 'sonora-discovery-catalog-v1', 'tracks': rows}))

    def decoded(self, path):
        samples = np.linspace(-.1, .1, 12 * 48000 + 1, dtype=np.float32)
        return samples, {'source_frames': len(samples), 'declared_source_frames': len(samples) + 91,
                         'source_sample_rate_hz': 48000, 'source_channels': 1,
                         'decoded_samples': len(samples), 'duration_ms': len(samples) * 1000 // 48000,
                         'pcm_sha256': hashlib.sha256(samples.astype('<f4').tobytes()).hexdigest()}

    def build(self, name='result'):
        with patch.object(producer, 'ClapTextEncoder', SyntheticEncoder), patch.object(producer, 'decode_audio', self.decoded):
            return producer.build(self.catalog, self.audio, self.checkpoint, self.cache,
                                  self.root / name, 'explicit-unit-test-index', batch_size=2)

    def manifest(self, name='result'):
        return self.root / name / 'manifest.json'

    def rewrite_proof(self, alter):
        path = self.root / 'result/build-proof.json'
        proof = json.loads(path.read_text()); alter(proof); path.write_text(json.dumps(proof))
        meta = json.loads(self.manifest().read_text()); meta['build_proof_sha256'] = consumer.file_hash(path)
        self.manifest().write_text(json.dumps(meta))

    def test_source_proofs_are_bound_and_raw_files_unchanged(self):
        rows, pins, pin = producer.checked_catalog(self.catalog, self.audio)
        self.assertEqual(rows[0]['track_id'], '1')
        self.assertEqual(pin, consumer.file_hash(self.catalog))
        self.assertEqual(len(pins), 4)

    def test_content_and_proof_hashes_reject_before_model(self):
        for key in ('content_md5', 'content_sha256', 'proof_sha256'):
            row = {**self.row, key: '0' * (32 if key == 'content_md5' else 64)}
            self.write_catalog([row])
            with self.subTest(key=key), self.assertRaises(consumer.DiscoveryError): self.build(key)
        self.assertEqual(SyntheticEncoder.calls, 0)

    def test_evidence_tamper_rejected_before_model(self):
        (self.audio / '1.html').write_text('changed')
        with self.assertRaises(consumer.DiscoveryError): self.build()
        self.assertEqual(SyntheticEncoder.calls, 0)

    def test_duplicate_ids_content_and_unknown_fields_rejected(self):
        for rows in ([self.row, self.row], [{**self.row, 'unexpected': True}], [{**self.row, 'track_id': '01'}]):
            self.write_catalog(rows)
            with self.assertRaises(consumer.DiscoveryError): producer.checked_catalog(self.catalog, self.audio)

    def test_path_escape_symlink_and_hardlink_rejected(self):
        self.write_catalog([{**self.row, 'audio_filename': '../outside.mp3'}])
        with self.assertRaises(consumer.DiscoveryError): producer.checked_catalog(self.catalog, self.audio)
        self.write_catalog([self.row]); original = self.audio / '1.mp3'; moved = self.audio / 'original.mp3'
        original.rename(moved); original.symlink_to(moved)
        with self.assertRaises(consumer.DiscoveryError): producer.checked_catalog(self.catalog, self.audio)
        original.unlink(); original.hardlink_to(moved)
        with self.assertRaises(consumer.DiscoveryError): producer.checked_catalog(self.catalog, self.audio)

    def test_catalog_duplicate_json_fields_rejected(self):
        self.catalog.write_text('{"schema":1,"schema":2,"tracks":[]}')
        with self.assertRaises(consumer.DiscoveryError): self.build()

    def test_build_records_eof_windows_zero_pad_and_identity_mean(self):
        result = self.build(); self.assertEqual((result['tracks'], result['segments']), (1, 2))
        index = consumer.DiscoveryIndex(self.manifest())
        self.assertEqual(index.meta['engine_kind'], 'clap_identity')  # Test double output, not a real model run.
        proof = index.proof['tracks'][0]
        self.assertEqual(proof['source_frames'] + 91, proof['declared_source_frames'])
        self.assertEqual(proof['windows'][-1]['padded_samples'], 143999)
        batch = SyntheticEncoder.windows[0]
        self.assertEqual(batch.shape, (2, 480000)); self.assertTrue(np.all(batch[1, 336001:] == 0))
        np.testing.assert_array_equal(index.whole, index.segments[:1])
        self.assertEqual(stat.S_IMODE(self.manifest().stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.manifest().parent.stat().st_mode), 0o700)

    def test_numeric_id_order_and_multitrack_binding(self):
        second = self.asset('9'); third = self.asset('2'); self.write_catalog([second, third, self.row])
        self.build(); index = consumer.DiscoveryIndex(self.manifest())
        self.assertEqual(list(index.tracks), ['1', '2', '9'])
        self.assertEqual([r['track_id'] for r in index.proof['tracks']], ['1', '2', '9'])

    def test_repeat_and_failed_output_never_reused(self):
        self.build(); before = consumer.file_hash(self.manifest()); calls = SyntheticEncoder.calls
        with self.assertRaises(FileExistsError): self.build()
        self.assertEqual(SyntheticEncoder.calls, calls); self.assertEqual(consumer.file_hash(self.manifest()), before)
        SyntheticEncoder.invalid = True
        with self.assertRaises(consumer.DiscoveryError): self.build('failed')
        self.assertTrue((self.root / 'failed/failure.json').exists()); self.assertFalse(self.manifest('failed').exists())
        with self.assertRaises(FileExistsError): self.build('failed')

    def test_mutation_during_encoding_retained_without_manifest(self):
        SyntheticEncoder.mutate = lambda: self.catalog.write_text(self.catalog.read_text() + ' ')
        with self.assertRaises(consumer.DiscoveryError): self.build()
        self.assertTrue((self.root / 'result/failure.json').exists()); self.assertFalse(self.manifest().exists())

    def test_production_indexes_require_proof(self):
        self.build(); meta = json.loads(self.manifest().read_text()); meta.pop('build_proof_sha256')
        self.manifest().write_text(json.dumps(meta))
        with self.assertRaises(consumer.DiscoveryError): consumer.DiscoveryIndex(self.manifest())

    def test_rehashed_invalid_model_recipe_and_sample_proofs_refused(self):
        changes = [lambda p: p.update(status='partial'), lambda p: p.update(checkpoint_sha256='0' * 64),
                   lambda p: p.update(preprocessing_version='unverified'), lambda p: p.update(offline_cache_files={}),
                   lambda p: p['tracks'][0].update(decoded_samples=42),
                   lambda p: p['tracks'][0]['windows'][0].update(padded_samples=1)]
        for i, change in enumerate(changes):
            if i:
                # Preserve each previous corrupt fixture; create a fresh build.
                (self.root / 'result').rename(self.root / ('corrupt-' + str(i)))
            self.build(); self.rewrite_proof(change)
            with self.subTest(i=i), self.assertRaises(consumer.DiscoveryError): consumer.DiscoveryIndex(self.manifest())

    def test_private_slot_and_output_symlink_guards(self):
        outside = self.root / 'linked'; outside.symlink_to(self.audio, target_is_directory=True)
        with self.assertRaises(consumer.DiscoveryError): producer.private_path(outside, 'b', directory=True)
        with self.assertRaises(consumer.DiscoveryError): producer.private_path(self.root, 'a')
        with self.assertRaises(consumer.DiscoveryError):
            producer.private_path(producer.ROOT / '.local/b/../a/disallowed', 'b')

    def cache_fixture(self):
        for _, repository, revision, required, _, ref in consumer.CACHE_SPECS:
            snapshot = self.cache / repository / 'snapshots' / revision
            snapshot.mkdir(parents=True)
            for name in required: (snapshot / name).write_bytes(b'explicit cache test double')
            if ref:
                aliases = self.cache / repository / 'refs'; aliases.mkdir()
                (aliases / 'main').write_text(revision)
        encoder = consumer.ClapTextEncoder.__new__(consumer.ClapTextEncoder)
        encoder.offline_cache = self.cache
        return encoder

    def test_cache_alias_outside_root_and_wrong_revision_rejected(self):
        encoder = self.cache_fixture()
        alias = self.cache / 'models--bert-base-uncased/refs/main'
        alias.write_text('wrong-revision')
        with self.assertRaises(consumer.DiscoveryError): encoder._cache_identity()
        outside = self.root / 'outside-ref'; outside.write_text(consumer.BERT_TOKENIZER_REVISION)
        alias.unlink(); alias.symlink_to(outside)
        with self.assertRaises(consumer.DiscoveryError): encoder._cache_identity()

    def test_cache_mutation_after_identity_is_refused(self):
        encoder = self.cache_fixture(); encoder.cache_fingerprints = encoder._cache_identity()
        encoder.checkpoint_path = self.checkpoint
        with patch.object(consumer, 'CHECKPOINT_SHA256', consumer.file_hash(self.checkpoint)):
            encoder.verify_assets()
            path = self.cache / 'models--bert-base-uncased/snapshots' / consumer.BERT_TOKENIZER_REVISION / 'vocab.txt'
            path.write_bytes(b'changed after initialization')
            with self.assertRaises(consumer.DiscoveryError): encoder.verify_assets()

    def test_window_policy_short_exact_and_tail(self):
        self.assertEqual(consumer.window_bounds(48), [(0, 48)])
        self.assertEqual(consumer.window_bounds(480000), [(0, 480000)])
        self.assertEqual(consumer.window_bounds(480001), [(0, 480000), (240000, 480001)])
        self.assertEqual(consumer.window_bounds(960001), [(0, 480000), (240000, 720000),
                                                        (480000, 960000), (720000, 960001)])
        with self.assertRaises(consumer.DiscoveryError): consumer.window_bounds(47)

    def test_actual_eof_reads_past_header_and_copies_reused_buffer(self):
        import soundfile as sf
        audio = np.column_stack((np.arange(160001, dtype=np.float32) / 1000000,
                                 -np.arange(160001, dtype=np.float32) / 2000000)).astype(np.float32)
        class Source:
            samplerate, channels, frames, format = 48000, 2, 12000, 'MP3'
            position = 0
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def tell(self): return self.position
            def read(self, *, frames, out):
                n = min(frames, len(audio) - self.position); out[:n] = audio[self.position:self.position+n]
                self.position += n; return out[:n]
        with patch.object(sf, 'SoundFile', return_value=Source()): samples, info = producer.decode_audio('test-double')
        self.assertEqual((info['source_frames'], info['declared_source_frames']), (160001, 12000))
        np.testing.assert_array_equal(samples, audio.mean(axis=1))

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg required for actual decoder control')
    def test_real_generated_short_mp3_resamples_and_pads(self):
        path = self.root / 'generated-control.mp3'
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i',
                        'sine=frequency=440:sample_rate=22050:duration=1.3', '-ac', '2',
                        '-c:a', 'libmp3lame', str(path)], check=True)
        samples, info = producer.decode_audio(path)
        self.assertEqual(info['source_sample_rate_hz'], 22050)
        self.assertEqual(info['source_channels'], 2)
        self.assertEqual(len(samples), (info['source_frames'] * 48000 + 22049) // 22050)
        self.assertTrue(samples.flags.c_contiguous); self.assertEqual(samples.dtype, np.float32)
        self.assertEqual(len(consumer.window_bounds(len(samples))), 1)
        self.assertGreater(consumer.WINDOW_SAMPLES, len(samples))

    def test_invalid_audio_refused(self):
        with self.assertRaises(Exception): producer.decode_audio(self.audio / '1.mp3')


class TextIdentityTest(unittest.TestCase):
    def encoder(self, length=110, corrupt=False):
        raw = [0] + [42] * (length - 2) + [2]
        def tokenize(text, **kwargs):
            if isinstance(text, str): return {'input_ids': raw}
            ids = np.ones((1, 256), dtype=np.int64); mask = np.zeros_like(ids)
            ids[0, :len(raw)] = raw; mask[0, :len(raw)] = 1
            if corrupt: ids[0, 80] = 13
            return {'input_ids': ids, 'attention_mask': mask}
        encoder = consumer.ClapTextEncoder.__new__(consumer.ClapTextEncoder)
        encoder.sdk = SimpleNamespace(tokenize=tokenize)
        return encoder

    def test_over77_text_is_preserved_with_actual_nonpadding_proof(self):
        encoder = self.encoder(); value = encoder._text_input('explicit synthetic token test')
        self.assertEqual(int(value['attention_mask'].sum()), 110)
        self.assertEqual(encoder.last_tokenization['untruncated_tokens'], 110)

    def test_over256_rejected_before_padding_or_model(self):
        with self.assertRaises(consumer.DiscoveryError) as error: self.encoder(257)._text_input('overlong')
        self.assertEqual((error.exception.status, error.exception.kind), (400, 'query_tokens_exceeded'))

    def test_changed_tokens_even_after77_are_refused(self):
        with self.assertRaises(consumer.DiscoveryError): self.encoder(corrupt=True)._text_input('no truncation')

    def test_query_cache_must_match_producer(self):
        encoder = self.encoder(); encoder.cache_fingerprints = {'config.json': '1' * 64}
        index = SimpleNamespace(meta={'engine_kind': 'clap_identity'}, proof={'offline_cache_files': {'config.json': '2' * 64}})
        with self.assertRaises(consumer.DiscoveryError): encoder.verify_index(index)


if __name__ == '__main__':
    unittest.main()
