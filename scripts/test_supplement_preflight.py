"""Synthetic bounded-source, exact-content, actual-view and claim checks."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import supplement_preflight as p


class SupplementTests(unittest.TestCase):
    def config(self):
        return json.loads(Path('docs/evaluation/MUS-063-preflight-config.json').read_text())

    def test_fixed_config_blocks_extra_attempts_replacement_and_model_work(self):
        for key, value in [('max_download_attempts_per_track', 2), ('automatic_replacements', True),
                           ('max_total_body_bytes', 2**30), ('fixed_recordings', 7)]:
            cfg = self.config(); cfg[key] = value
            with self.assertRaises(ValueError): p.validate_config(cfg)
        cfg = self.config(); cfg['operations']['encodes'] = 1
        with self.assertRaises(ValueError): p.validate_config(cfg)

    def test_original_and_new_directory_claim_are_not_bypassed(self):
        import preflight_supplement as runner
        cfg = self.config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); task = root/cfg['task_directory']; task.mkdir(parents=True)
            (task/'preflight-started.json').write_text('{}')
            with patch.object(runner, 'ROOT', root), patch.object(runner.h.assets, 'document', return_value=cfg):
                for name in ['old', 'new']:
                    with self.assertRaisesRegex(ValueError, 'already attempted'):
                        runner.run(root/'config', '0'*64, task/name)
                    self.assertFalse((task/name).exists())

    def fixture(self):
        rows = []
        for i in range(6):
            rows.append({'source_track_id': str(i), 'creator_component': 'g'+str(i),
                'work_key': 'w'+str(i), 'audio_sha256': hashlib.sha256(str(i).encode()).hexdigest(),
                'validated_caption_count': 2 if i == 0 else 1,
                'artist_id': 'a'+str(i), 'artist_name': 'Artist'+str(i), 'title': 'W'+str(i),
                'path': f'{i:02}/{i}.mp3', 'official_low_path': f'{i:02}/{i}.low.mp3',
                'duration_metadata_seconds': 60., 'audio_license': {'family': 'by', 'uri': 'pinned'}})
        allowed = rows + [{**rows[0], 'source_track_id': 'extra1'}, {**rows[0], 'source_track_id': 'extra2'}]
        plan = {'role': 'development_metadata_only', 'selected': rows, 'summary': {'validated_caption_queries': 7}}
        base = {r['source_track_id']: {'artist_id': r['artist_id'], 'path': r['path'], 'duration': 60.} for r in rows}
        names = {r['source_track_id']: {'artist_id': r['artist_id'], 'artist': r['artist_name'], 'title': r['title']} for r in rows}
        licenses = {r['path']: r['audio_license'] for r in rows}
        hashes = {r['official_low_path']: r['audio_sha256'] for r in rows}
        return plan, allowed, base, names, licenses, hashes, set(base)

    def test_original_identity_and_all_seven_caption_counts_preserved(self):
        args = self.fixture(); before = copy.deepcopy(args)
        self.assertEqual(len(p.validate_selection(*args)), 6)
        self.assertEqual(args, before)

    def test_license_hash_duration_and_artist_drift_rejected(self):
        for field, value in [('audio_license', {'family': 'by-nc'}), ('audio_sha256', '0'*64),
                             ('duration_metadata_seconds', 99.), ('artist_name', 'Another artist')]:
            args = self.fixture(); args[0]['selected'][0][field] = value
            with self.assertRaises(ValueError): p.validate_selection(*args)

    def test_source_outside_original_official_test_is_rejected(self):
        args = self.fixture(); args[-1].remove('0')
        with self.assertRaises(ValueError): p.validate_selection(*args)

    def test_same_credit_group_cannot_be_two_new_recordings(self):
        args = self.fixture(); args[0]['selected'][1]['creator_component'] = 'g0'
        with self.assertRaises(ValueError): p.validate_selection(*args)

    def test_pinned_low_path_cannot_be_swapped(self):
        args = self.fixture(); args[0]['selected'][0]['official_low_path'] = '../other.mp3'
        with self.assertRaises(ValueError): p.validate_selection(*args)

    def audio(self, seconds=31):
        result = np.full(seconds*48000, .125, dtype=np.float32)
        result[-1] = .5
        return result

    def test_actual_tail_is_included_and_padding_does_not_change_original(self):
        audio = self.audio(); before = audio.copy(); value = p.inspect_audio(audio, 31.)
        self.assertEqual(value['first_tail_checks'][-1], {'start_sample': 1200000,
            'end_sample': 1488000, 'real_samples': 288000, 'padded_samples': 192000})
        self.assertEqual(value['pcm_sha256'], hashlib.sha256(before.astype('<f4').tobytes()).hexdigest())
        np.testing.assert_array_equal(audio, before)

    def test_shorter_than120_view_keeps_actual_end(self):
        value = p.inspect_audio(self.audio(31), 31.)
        self.assertEqual(value['retrieval_clip_samples'], 31*48000)
        self.assertEqual(value['retrieval_clip_pcm_sha256'], value['pcm_sha256'])

    def test_long_recording_view_is_clamped_to120_not_full_song(self):
        audio = self.audio(121); value = p.inspect_audio(audio, 121.)
        self.assertEqual(value['retrieval_clip_samples'], 120*48000)
        self.assertNotEqual(value['retrieval_clip_pcm_sha256'], value['pcm_sha256'])

    def test_silence_nonfinite_wrong_dtype_or_shape_rejected(self):
        for audio in [np.zeros(30*48000, np.float32), self.audio().astype(np.float64), self.audio()[:, None]]:
            with self.assertRaises(ValueError): p.inspect_audio(audio, 31.)
        audio = self.audio(); audio[100] = np.nan
        with self.assertRaises(ValueError): p.inspect_audio(audio, 31.)

    def test_actual_duration_bounds_and_metadata_disagreement_rejected(self):
        with self.assertRaises(ValueError): p.inspect_audio(self.audio()[:30*48000-1], 30.)
        for metadata in [28.9, 34., float('nan'), True]:
            with self.assertRaises(ValueError): p.inspect_audio(self.audio(), metadata)
        p.inspect_audio(self.audio(), 29.)  # Exact2-second bound, no after-the-fact tolerance change.

    def test_different_compressed_bytes_with_same_old_pcm_still_rejected(self):
        with self.assertRaisesRegex(ValueError, 'PCM'):
            p.check_duplicate('new', 'same', {'bytes': {'old'}, 'pcm': {'same'}}, set(), set())

    def test_within_new_batch_byte_or_pcm_duplicate_rejected(self):
        prior = {'bytes': set(), 'pcm': set()}
        for audio, pcm in [('a', 'new'), ('new', 'p')]:
            with self.assertRaises(ValueError): p.check_duplicate(audio, pcm, prior, {'a'}, {'p'})

    def test_prior_reused_references_not_counted_as_distinct_audio(self):
        a, b = 'a'*64, 'b'*64
        docs = {'prior60': {'tracks': [{'audio_sha256': a, 'pcm_sha256': b}]},
            'prior140': {'tracks': [{'audio_sha256': a, 'decode': {'pcm_sha256': b}}]},
            'prior76': {'records': []}, 'pilot_fetched': {'tracks': []}, 'pilot_decoded': {'tracks': []}}
        result = p.prior_content(docs)
        self.assertEqual(result['summary'], {'record_references': 2, 'unique_audio_hashes': 1,
                                            'unique_pcm_hashes': 1, 'reused_references': 1})
        docs['prior140']['tracks'][0]['decode']['pcm_sha256'] = 'c'*64
        with self.assertRaises(ValueError): p.prior_content(docs)


if __name__ == '__main__': unittest.main()
