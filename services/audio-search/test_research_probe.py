"""Synthetic SDK/decoder boundary tests; no real model, audio, labels or credentials."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import research_probe as driver


class FakeSdk:
    def __init__(self):
        self.audio_batches = []
        self.text_batches = []
        self.token_calls = []
        self.token_count = 12
        self.audio_mode = None
        self.text_mode = None
        self.model = SimpleNamespace(load_state_dict=Mock(return_value=SimpleNamespace(
            missing_keys=[], unexpected_keys=[])), eval=Mock())

    def tokenize(self, text, truncation):
        self.token_calls.append((text, truncation))
        return {'input_ids': list(range(self.token_count))}

    def get_audio_embedding_from_data(self, batch, use_tensor):
        self.audio_batches.append((batch.shape, batch.dtype, use_tensor))
        if self.audio_mode == 'zero':
            return np.zeros((len(batch), 512), dtype=np.float32)
        if self.audio_mode == 'batch':
            return np.ones((len(batch) + 1, 512), dtype=np.float32)
        if self.audio_mode == 'nonfinite':
            return np.full((len(batch), 512), np.nan, dtype=np.float32)
        # Deliberately tied scores exercise the existing numeric-ID tie rule.
        vectors = np.zeros((len(batch), 256 if self.audio_mode == 'dimension' else 512), dtype=np.float32)
        vectors[:, 0] = 1
        return vectors

    def get_text_embedding(self, texts, use_tensor):
        self.text_batches.append((list(texts), use_tensor))
        vectors = np.zeros((7 if self.text_mode == 'batch' else len(texts),
                            256 if self.text_mode == 'dimension' else 512), dtype=np.float32)
        vectors[:, 0] = 1
        return vectors


class ResearchProbeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.private = self.root / '.local/a'
        self.private.mkdir(parents=True, mode=0o700)
        self.output = self.private / 'fresh-run'
        self.audio_root = self.private / 'audio'
        self.audio_root.mkdir(mode=0o700)
        self.paths, self.pins = {}, {}
        for key, pin in driver.INPUT_PINS.items():
            path = self.private / (key + '.json')
            path.write_bytes((driver.SOURCE / 'exploratory_queries.json').read_bytes()
                             if key == 'queries' else json.dumps({'synthetic_input': key}).encode())
            self.paths[key], self.pins[pin] = path, driver.file_hash(path)
        self.checkpoint = self.private / 'synthetic-checkpoint.pt'
        self.checkpoint.write_bytes(b'not real model weights; torch.load is always replaced')
        self.assets = []
        self.infos = {}
        for index in range(40):
            provider = 'jamendo' if index < 20 else 'incompetech'
            sid = str(10000 + index) if provider == 'jamendo' else 'USABC' + str(1000000 + index)
            filename = provider + '-' + sid + '.mp3'
            frames, rate = (16 * 48000 + 17, 48000) if index == 1 else (48000, 48000)
            if index == 20:
                # Exact ceil at 48k represents 30,001ms; source floor is 30,000ms.
                frames, rate = 30 * 44100 + 44, 44100
            count = (frames * 48000 + rate - 1) // rate
            info = {'format': 'MP3', 'source_frames': frames, 'source_sample_rate_hz': rate,
                'source_channels': 2, 'sample_rate_hz': 48000, 'decoded_samples': count,
                'duration_ms': count * 1000 // 48000}
            asset = {'track_id': str(index + 1), 'source_provider': provider, 'source_id': sid,
                'asset_filename': filename, 'content_sha256': ('%064x' % (index + 1)), 'bytes': 128,
                'download_proof_sha256': 'a' * 64, 'source_url': 'https://example.invalid/synthetic',
                'license_url': 'https://creativecommons.org/licenses/by/4.0/',
                'title': 'Synthetic ' + str(index), 'artist': 'Synthetic fixture',
                'provider_duration_seconds': frames // rate}
            if provider == 'incompetech':
                asset['recorded_decode'] = {'frames': frames, 'sample_rate_hz': rate, 'channels': 2,
                    'format': 'MP3', 'duration_ms': frames * 1000 // rate}
            self.assets.append(asset)
            self.infos[filename] = info
        self.decoded = []
        self.sdk = FakeSdk()
        self.loaded_state = {'state_dict': {'module.weight': 1, 'module.text_branch.embeddings.position_ids': [0]}}
        replacements = {
            'ROOT': self.root,
            'CHECKPOINT_SHA256': driver.file_hash(self.checkpoint),
            'checked_assets': Mock(side_effect=lambda **kwargs: deepcopy(self.assets)),
            'create_pinned_model': Mock(return_value=self.sdk),
            'source_hashes': Mock(return_value={name: '1' * 64 for name in driver.SOURCE_FILES}),
            'code_state': Mock(return_value={'code_sha': 'a' * 40, 'working_tree_dirty': False}),
            'version': Mock(return_value='synthetic-test-version'),
            'sf_version': Mock(return_value='synthetic-test-library'),
            'decode_mono': Mock(side_effect=self.decode),
        }
        for name, value in replacements.items():
            item = patch.object(driver, name, value)
            item.start()
            self.addCleanup(item.stop)
        self.git_ignore = patch.object(driver.subprocess, 'run', return_value=SimpleNamespace(returncode=0))
        self.git_ignore.start()
        self.addCleanup(self.git_ignore.stop)
        self.torch_load = patch.object(driver.torch, 'load', return_value=self.loaded_state)
        self.load = self.torch_load.start()
        self.addCleanup(self.torch_load.stop)
        for name in ('manual_seed', 'set_num_threads', 'set_num_interop_threads'):
            item = patch.object(driver.torch, name)
            item.start()
            self.addCleanup(item.stop)

    def decode(self, path):
        self.decoded.append(path.name)
        info = deepcopy(self.infos[path.name])
        return np.zeros(info['decoded_samples'], dtype=np.float32), info

    def run_probe(self, **overrides):
        args = {**self.paths, **self.pins, 'audio_root': self.audio_root,
                'checkpoint': self.checkpoint, 'output': self.output}
        args.update(overrides)
        with redirect_stdout(io.StringIO()):
            return driver.run(**args)

    def failed_without_model(self, message):
        with self.assertRaisesRegex(ValueError, message):
            self.run_probe()
        driver.create_pinned_model.assert_not_called()
        self.load.assert_not_called()
        self.assertTrue((self.output / 'failure.json').is_file())
        self.assertFalse((self.output / 'report.json').exists())

    def test_full_fresh_encoding_and_text_only_artifacts(self):
        report = self.run_probe()
        self.assertEqual(report['schema'], 'sonora-research-probe-v1')
        self.assertEqual(report['status'], 'passed_private_research_pipeline_only')
        self.assertEqual(report['counts']['tracks'], 40)
        self.assertEqual(report['counts']['text_queries'], 8)
        self.assertEqual(report['counts']['reference_queries'], 0)
        self.assertEqual(len(self.decoded), 40)
        self.assertEqual(set(self.decoded), {a['asset_filename'] for a in self.assets})
        self.assertEqual(sum(shape[0] for shape, _, _ in self.sdk.audio_batches), report['counts']['segments'])
        self.assertTrue(all(shape[1] == 480000 and dtype == np.float32 and tensor is False
                            for shape, dtype, tensor in self.sdk.audio_batches))
        self.assertEqual(len(self.sdk.text_batches), 1)
        self.assertTrue(all(truncated is False for _, truncated in self.sdk.token_calls))
        self.assertEqual(driver.checked_assets.call_count, 2)
        self.assertEqual(set(report['input_sha256']), set(driver.INPUT_PINS))
        self.assertEqual(report['model']['dimension'], 512)
        self.assertTrue(report['model']['removed_nonlearned_position_ids'])
        self.sdk.model.load_state_dict.assert_called_once_with({'weight': 1}, strict=True)
        self.load.assert_called_once_with(self.checkpoint, map_location='cpu', weights_only=True, mmap=True)
        with np.load(self.output / 'vectors.npz', allow_pickle=False) as vectors:
            self.assertEqual(vectors['reference_vectors'].shape, (0, 512))
            self.assertEqual(vectors['whole_vectors'].shape, (40, 512))
            self.assertEqual(vectors['text_vectors'].shape, (8, 512))
            np.testing.assert_allclose(np.linalg.norm(vectors['segment_vectors'], axis=1), 1, atol=1e-6)
        rankings = json.loads((self.output / 'rankings.json').read_text())
        self.assertEqual(rankings['judgments'], 'unjudged')
        self.assertEqual(len(rankings['queries']), 8)
        for query in rankings['queries']:
            self.assertEqual(query['kind'], 'text')
            self.assertEqual([r['track_id'] for r in query['whole_track']], ['1', '2', '3', '4', '5'])
            self.assertEqual([r['track_id'] for r in query['segment']], ['1', '2', '3', '4', '5'])
        self.assertEqual(set(report['artifact_sha256']), {'corpus-manifest.json', 'segments.json', 'vectors.npz', 'rankings.json', 'queries.json'})
        for name, value in report['artifact_sha256'].items():
            self.assertEqual(driver.file_hash(self.output / name), value)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all((p.stat().st_mode & 0o777) == 0o600 for p in self.output.iterdir()))

    def test_fractional_resampling_retains_source_duration_and_exact_tail(self):
        self.run_probe()
        manifest = json.loads((self.output / 'corpus-manifest.json').read_text())
        self.assertEqual(manifest['schema'], 'sonora-research-corpus-v1')
        track = manifest['tracks'][20]
        self.assertEqual(track['recorded_decode']['duration_ms'], 30000)
        self.assertEqual(track['duration_ms'], 30001)
        self.assertEqual(track['decoded_samples'], 1440048)
        segments = json.loads((self.output / 'segments.json').read_text())
        tail = [r for r in segments if r['track_id'] == '2'][-1]
        self.assertEqual(tail['start_sample'], 10 * 48000)
        self.assertEqual(tail['end_sample'], 16 * 48000 + 17)
        self.assertEqual(tail['padded_samples'], 4 * 48000 - 17)

    def test_existing_output_is_never_overwritten_or_given_failure_record(self):
        self.output.mkdir(mode=0o700)
        sentinel = self.output / 'sentinel'
        sentinel.write_bytes(b'preserve failed or successful prior run')
        with self.assertRaises(FileExistsError):
            self.run_probe()
        self.assertEqual(sentinel.read_bytes(), b'preserve failed or successful prior run')
        driver.checked_assets.assert_not_called()
        driver.create_pinned_model.assert_not_called()
        self.assertFalse((self.output / 'failure.json').exists())

    def test_output_outside_private_root_is_rejected_without_creation(self):
        outside = self.root / 'public-run'
        with self.assertRaisesRegex(ValueError, 'below this checkout'):
            self.run_probe(output=outside)
        self.assertFalse(outside.exists())
        driver.create_pinned_model.assert_not_called()

    def test_output_symlink_is_rejected(self):
        linked = self.private / 'linked'
        linked.symlink_to(self.audio_root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.run_probe(output=linked / 'run')
        self.assertFalse((self.audio_root / 'run').exists())

    def test_unignored_output_is_rejected_without_creation(self):
        driver.subprocess.run.return_value = SimpleNamespace(returncode=1)
        with self.assertRaisesRegex(ValueError, 'ignored by Git'):
            self.run_probe()
        self.assertFalse(self.output.exists())

    def test_wrong_input_pin_stops_before_model_and_records_failure(self):
        self.pins['decode_sha256'] = '0' * 64
        self.failed_without_model('SHA256 mismatch')

    def test_missing_explicit_input_pin_stops_before_model(self):
        self.pins['selection_sha256'] = None
        self.failed_without_model('explicit input')

    def test_corrupt_adapter_evidence_stops_before_model(self):
        driver.checked_assets.side_effect = ValueError('Synthetic corrupted proof rejected')
        self.failed_without_model('corrupted proof')

    def test_dirty_initial_git_state_stops_before_model(self):
        driver.code_state.return_value = {'code_sha': 'a' * 40, 'working_tree_dirty': True}
        self.failed_without_model('clean committed Git')
        driver.checked_assets.assert_not_called()
        self.assertEqual(self.decoded, [])

    def test_invalid_initial_git_identity_stops_before_model(self):
        for number, value in enumerate(('A' * 40, 'a' * 39, 'not-a-commit', None)):
            driver.code_state.return_value = {'code_sha': value, 'working_tree_dirty': False}
            with self.subTest(identity=value), self.assertRaisesRegex(ValueError, 'clean committed Git'):
                self.run_probe(output=self.private / ('invalid-git-' + str(number)))
        driver.create_pinned_model.assert_not_called()
        self.load.assert_not_called()
        driver.checked_assets.assert_not_called()
        self.assertEqual(self.decoded, [])

    def test_exact_eight_query_fixture_required_even_with_matching_pin(self):
        value = json.loads(self.paths['queries'].read_text())
        value['queries'][0]['text'] = 'Changed query, not the frozen fixture'
        self.paths['queries'].write_text(json.dumps(value))
        self.pins['queries_sha256'] = driver.file_hash(self.paths['queries'])
        self.failed_without_model('eight original')

    def test_checkpoint_hash_precedes_model_construction_and_deserialization(self):
        self.checkpoint.write_bytes(b'changed synthetic weights')
        self.failed_without_model('Checkpoint hash')

    def test_checkpoint_change_during_constructor_prevents_deserialization(self):
        def changed():
            self.checkpoint.write_bytes(b'changed while constructing fake SDK')
            return self.sdk
        driver.create_pinned_model.side_effect = changed
        with self.assertRaisesRegex(ValueError, 'during model construction'):
            self.run_probe()
        self.load.assert_not_called()

    def test_strict_load_mismatch_is_not_a_pass(self):
        self.sdk.model.load_state_dict.return_value = SimpleNamespace(missing_keys=['missing'], unexpected_keys=[])
        with self.assertRaisesRegex(ValueError, 'Strict model load'):
            self.run_probe()
        self.assertEqual(self.decoded, [])
        self.assertFalse((self.output / 'report.json').exists())

    def test_overlong_text_is_rejected_before_audio_encoding(self):
        self.sdk.token_count = 78
        with self.assertRaisesRegex(ValueError, 'truncated'):
            self.run_probe()
        self.assertEqual(self.decoded, [])

    def test_exact_source_decode_identity_rejects_each_changed_field(self):
        info = self.infos[self.assets[20]['asset_filename']]
        samples = np.zeros(info['decoded_samples'], dtype=np.float32)
        for key, value in [('frames', info['source_frames'] + 1), ('sample_rate_hz', 48000),
                           ('channels', 1), ('format', 'WAV'), ('duration_ms', 30001)]:
            asset = deepcopy(self.assets[20])
            asset['recorded_decode'][key] = value
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, 'pinned original'):
                driver.validate_decode(samples, info, asset)

    def test_resampling_cannot_use_one_sample_or_generic_duration_tolerance(self):
        info = self.infos[self.assets[20]['asset_filename']]
        for delta in (-1, 1):
            changed = {**info, 'decoded_samples': info['decoded_samples'] + delta}
            samples = np.zeros(changed['decoded_samples'], dtype=np.float32)
            with self.subTest(delta=delta), self.assertRaisesRegex(ValueError, 'integer-ceiling'):
                driver.validate_decode(samples, changed, self.assets[20])

    def test_incomplete_nonfinite_decode_fails_without_report(self):
        original = self.decode
        def invalid(path):
            samples, info = original(path)
            samples[0] = np.nan
            return samples, info
        driver.decode_mono.side_effect = invalid
        with self.assertRaisesRegex(ValueError, 'integer-ceiling'):
            self.run_probe()
        self.assertFalse((self.output / 'report.json').exists())
        self.assertTrue((self.output / 'failure.json').exists())

    def test_invalid_audio_embedding_zero_nonfinite_and_batch_count(self):
        for mode in ('zero', 'nonfinite', 'batch'):
            self.sdk.audio_mode = mode
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.run_probe(output=self.private / ('invalid-audio-' + mode))

    def test_text_embedding_count_and_dimension_must_match(self):
        for mode in ('batch', 'dimension'):
            self.sdk.text_mode = mode
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'dimension mismatch'):
                self.run_probe(output=self.private / ('invalid-text-' + mode))

    def test_audio_embedding_dimension_is_pinned_to_512(self):
        self.sdk.audio_mode = 'dimension'
        with self.assertRaisesRegex(ValueError, 'must produce 512'):
            self.run_probe()
        self.assertFalse((self.output / 'report.json').exists())

    def test_second_adapter_check_detects_changed_assets(self):
        changed = deepcopy(self.assets)
        changed[0]['download_proof_sha256'] = 'f' * 64
        driver.checked_assets.side_effect = [deepcopy(self.assets), changed]
        with self.assertRaisesRegex(ValueError, 'corpus input changed'):
            self.run_probe()
        self.assertFalse((self.output / 'report.json').exists())

    def test_pinned_file_change_during_encoding_prevents_passing_report(self):
        original = self.sdk.get_text_embedding
        def changed(texts, use_tensor):
            self.paths['selection'].write_bytes(b'changed synthetic selection')
            return original(texts, use_tensor)
        self.sdk.get_text_embedding = changed
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            self.run_probe()
        self.assertFalse((self.output / 'report.json').exists())

    def test_checkpoint_change_during_encoding_prevents_passing_report(self):
        original = self.sdk.get_text_embedding
        def changed(texts, use_tensor):
            self.checkpoint.write_bytes(b'changed synthetic checkpoint during encoding')
            return original(texts, use_tensor)
        self.sdk.get_text_embedding = changed
        with self.assertRaisesRegex(ValueError, 'state changed'):
            self.run_probe()
        self.assertFalse((self.output / 'report.json').exists())
        self.assertTrue((self.output / 'failure.json').exists())

    def test_source_or_git_change_prevents_passing_report(self):
        source = {name: '1' * 64 for name in driver.SOURCE_FILES}
        driver.source_hashes.side_effect = [source, {**source, 'probe.py': '2' * 64}]
        with self.assertRaisesRegex(ValueError, 'state changed'):
            self.run_probe()
        self.assertFalse((self.output / 'report.json').exists())

    def test_failed_run_directory_cannot_be_reused(self):
        self.pins['decode_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.run_probe()
        failure = (self.output / 'failure.json').read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_probe()
        self.assertEqual((self.output / 'failure.json').read_bytes(), failure)


if __name__ == '__main__':
    unittest.main()
