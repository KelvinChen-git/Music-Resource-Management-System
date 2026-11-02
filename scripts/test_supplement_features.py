"""Synthetic fulltext selection, immutable overlay, typed cache, and paired scoring."""
from pathlib import Path
import copy
import csv
import hashlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

import supplement_features as s
import device_calibration as calibration
import expanded_caption_metrics as metrics


class SupplementFeatureTests(unittest.TestCase):
    def ids(self): return [f'track_{i:07}' for i in range(200, 206)]

    def source(self):
        selected = [{'source_track_id': t, 'validated_caption_count': 2 if i == 0 else 1} for i, t in enumerate(self.ids())]
        out = io.StringIO(); writer = csv.writer(out)
        writer.writerow(['track_id', 'caption_id', 'is_valid_subset', 'caption'])
        writer.writerow(['999', 'sealed', 'True', 'UNSELECTED TEXT'])
        for i, row in enumerate(selected):
            for j in range(row['validated_caption_count']):
                writer.writerow([str(200+i), f'{i}-{j}', 'True', '  Full original café text!  '])
        writer.writerow(['200', 'invalid', '', 'NONVALIDATED TEXT'])
        return out.getvalue().encode(), selected

    def test_only_selected_validated_text_is_extracted_and_whitespace_preserved(self):
        raw, selected = self.source(); values = s.queries(raw, selected)
        self.assertEqual(len(values), 7)
        self.assertTrue(all(r['text'] == '  Full original café text!  ' for r in values))
        self.assertNotIn('UNSELECTED', str(values)); self.assertNotIn('NONVALIDATED', str(values))
        self.assertEqual(values[0]['text_sha256'], hashlib.sha256(values[0]['text'].encode()).hexdigest())

    def test_query_order_follows_fixed_plan_then_original_csv_order(self):
        raw, selected = self.source(); selected.reverse()
        values = s.queries(raw, selected)
        self.assertEqual(values[0]['track_id'], self.ids()[-1])
        self.assertEqual([r['caption_id'] for r in values[-2:]], ['0-0', '0-1'])

    def test_missing_caption_or_duplicate_selected_identity_rejected(self):
        raw, selected = self.source(); selected[0]['validated_caption_count'] = 1
        with self.assertRaises(ValueError): s.queries(raw, selected)
        raw, selected = self.source(); selected[-1] = selected[0]
        with self.assertRaises(ValueError): s.queries(raw, selected)

    def fixture(self):
        eye = np.eye(512)
        oldrows = [{'source_track_id': f'track_{i:07}', 'split': 'train' if i < 100 else 'validation' if i < 120 else 'caption_dev',
                    'retrieval_window_indices': list(range(3*i, 3*i+3))} for i in range(140)]
        query_tracks = [f'track_{i:07}' for i in range(120, 140)] + [f'track_{i:07}' for i in range(120, 124)]
        old = {'rows': oldrows, 'query_tracks': query_tracks}
        windows = np.concatenate([np.repeat(eye[:140], 3, axis=0), np.tile(eye[0], (204, 1))])
        text = np.stack([eye[int(t.split('_')[-1])] for t in query_tracks])
        records = [{'source_track_id': tid, 'creator_component': f'g{i}', 'validated_caption_count': 2 if i == 0 else 1,
                    'decode': {'decoded_samples': 121*48000},
                    'audio_preflight': {'retrieval_clip_samples': 120*48000, 'pcm_sha256': 'a'*64}}
                   for i, tid in enumerate(self.ids())]
        rows = s.new_rows({'tracks': records}); nw = np.repeat(eye[140:146], 3, axis=0)
        nt = eye[[140, 140, 141, 142, 143, 144, 145]]
        merged = s.merge(old, eye[:140], windows, text, rows, nw, nt)
        view = {**merged, 'old_query_tracks': query_tracks,
                'new_query_tracks': [self.ids()[0], *self.ids()]}
        return old, eye[:140], windows, text, rows, nw, nt, view

    def test_actual_short_clip_has_three_windows_inside_true_end(self):
        records = [{'source_track_id': t, 'creator_component': t, 'validated_caption_count': 2 if i == 0 else 1,
                    'decode': {'decoded_samples': 87*48000},
                    'audio_preflight': {'retrieval_clip_samples': 87*48000, 'pcm_sha256': 'a'*64}}
                   for i, t in enumerate(self.ids())]
        rows = s.new_rows({'tracks': records})
        self.assertEqual(rows[0]['window_start_samples'], [0, 77*24000, 77*48000])
        records[0]['audio_preflight']['retrieval_clip_samples'] += 1
        with self.assertRaises(ValueError): s.new_rows({'tracks': records})

    def test_overlay_preserves_all_old_values_and_window_indices(self):
        old, whole, windows, text, rows, nw, nt, view = self.fixture()
        self.assertEqual(len(view['rows']), 146); self.assertEqual(view['windows'].shape, (642, 512))
        self.assertEqual(view['whole'][:140].tobytes(), whole.tobytes())
        self.assertEqual(view['windows'][:624].tobytes(), windows.tobytes())
        self.assertEqual(view['old_texts'].tobytes(), text.tobytes())

    def test_overlapping_source_or_nonunit_vectors_rejected(self):
        old, whole, windows, text, rows, nw, nt, view = self.fixture()
        rows[0]['source_track_id'] = old['rows'][0]['source_track_id']
        with self.assertRaises(ValueError): s.merge(old, whole, windows, text, rows, nw, nt)
        rows = self.fixture()[4]; nw[0] = 0
        with self.assertRaises(ValueError): s.merge(old, whole, windows, text, rows, nw, nt)

    def test_scores_use_new6_recording_macro_separately_from_query_macro(self):
        view = self.fixture()[-1]; w = np.eye(512); w[[140, 141]] = w[[141, 140]]
        result = s.evaluate(view, w)
        self.assertAlmostEqual(result['new6']['whole']['recording_macro']['R1'], 4/6)
        self.assertAlmostEqual(result['new6']['whole']['query_macro']['R1'], 4/7)
        self.assertEqual(result['new6']['whole']['candidates'], 146)
        self.assertEqual(result['old20_original140']['whole']['candidates'], 140)
        self.assertEqual(result['old20_control']['whole']['recording_macro']['R1'], 1.)

    def test_bootstrap_resamples6_source_recordings_and_is_deterministic(self):
        view = self.fixture()[-1]; baseline = s.evaluate(view, np.eye(512))['new6']['whole']
        w = np.eye(512); w[[140, 141]] = w[[141, 140]]; candidate = s.evaluate(view, w)['new6']['whole']
        value = metrics.deltas(candidate, baseline, 2000, 20261102064)
        self.assertEqual(value, metrics.deltas(candidate, baseline, 2000, 20261102064))
        self.assertEqual((value['R1']['wins'], value['R1']['ties'], value['R1']['losses']), (0, 4, 2))

    def write(self, path, value):
        path.write_text(json.dumps(value)); return hashlib.sha256(path.read_bytes()).hexdigest()

    def cache_fixture(self, root):
        old, whole, windows, text, rows, nw, nt, view = self.fixture()
        olddir = root/'old'; newdir = root/'new'; olddir.mkdir(); newdir.mkdir()
        np.savez(olddir/'features.npz', retrieval_first120=whole, windows=windows, texts=text)
        old['feature_sha256'] = hashlib.sha256((olddir/'features.npz').read_bytes()).hexdigest()
        oldsha = self.write(olddir/'cache.json', old)
        np.savez(newdir/'features.npz', **{k: view[k] for k in ['whole', 'windows', 'old_texts', 'new_texts']})
        context = {'device': 'mps', 'environment': {'device': 'mps'}, 'model_sha256': 'a'*64,
                   'input_sha256': 'b'*64, 'recipe_sha256': 'c'*64, 'source_sha256': {'test': 'd'*64}}
        key = calibration.cache_key(**context)
        report = {'status': 'passed', 'ready_cache_written': True, 'cache_key_sha256': key,
                  'CPU_controls': {'audio_windows': 18, 'whole': 6, 'texts256': 7, 'short_text77': 7},
                  'vector_parity': {k: {'status': 'passed', 'vectors': n} for k, n in
                      [('all18_windows', 18), ('all6_whole', 6), ('all7_texts256', 7), ('short_CPU77_to256', 7)]}}
        resultsha = self.write(newdir/'result.json', report)
        proof = [{'untruncated_tokens': 2, 'encoded_nonpad_tokens': 2, 'input_ids_sha256': 'f'*64} for _ in range(7)]
        proofsha = self.write(newdir/'token-proof.json', proof)
        meta = {'schema': 'sonora-six-supplement-feature-cache-v1', 'status': 'ready_after_parity', 'counts': s.COUNTS,
                'device': 'mps', 'model_sha256': 'a'*64, 'token_length': 256, 'key_context': context,
                'cache_key_sha256': key, 'old_cache_sha256': oldsha, 'rows': view['rows'],
                'new_query_tracks': view['new_query_tracks'], 'old_query_tracks': view['old_query_tracks'],
                'query_text_sha256': ['e'*64]*7, 'token_lengths': [2]*7, 'token_proof_sha256': proofsha,
                'feature_sha256': hashlib.sha256((newdir/'features.npz').read_bytes()).hexdigest(), 'result_sha256': resultsha}
        return olddir, newdir, oldsha, meta, view

    def load(self, olddir, newdir, oldsha, meta, **kwargs):
        pin = self.write(newdir/'cache.json', meta)
        return s.ready_view(newdir/'cache.json', pin, old_cache=olddir/'cache.json', old_sha256=oldsha,
                            expected_device=kwargs.get('device', 'mps'), expected_model_sha256=kwargs.get('model', 'a'*64))

    def test_ready_consumer_is_cpu_only_and_reuses_old_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, pin, meta, view = self.cache_fixture(Path(tmp).resolve())
            ready = self.load(a, b, pin, meta)
            np.testing.assert_array_equal(ready['whole'], view['whole'])
            self.assertNotIn('text', ready); self.assertEqual(len(ready['new_query_tracks']), 7)

    def test_wrong_device_model_or_partial_status_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, pin, meta, view = self.cache_fixture(Path(tmp).resolve())
            for kw in [{'device': 'cpu'}, {'model': 'b'*64}]:
                with self.assertRaises(ValueError): self.load(a, b, pin, meta, **kw)
            meta['status'] = 'partial'
            with self.assertRaises(ValueError): self.load(a, b, pin, meta)

    def test_failed_or_empty_parity_report_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, pin, meta, view = self.cache_fixture(Path(tmp).resolve()); report = json.loads((b/'result.json').read_text())
            for value in [{}, {'all18_windows': {'status': 'failed', 'vectors': 18}}]:
                report['vector_parity'] = value; meta['result_sha256'] = self.write(b/'result.json', report)
                with self.assertRaises(ValueError): self.load(a, b, pin, meta)

    def test_valid_but_reordered_old_vectors_cannot_replace_originals(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, pin, meta, view = self.cache_fixture(Path(tmp).resolve()); view['whole'][[0, 1]] = view['whole'][[1, 0]]
            np.savez(b/'features.npz', **{k: view[k] for k in ['whole', 'windows', 'old_texts', 'new_texts']})
            meta['feature_sha256'] = hashlib.sha256((b/'features.npz').read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'elementwise'): self.load(a, b, pin, meta)

    def test_required_parity_cannot_be_marked_not_applicable(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, pin, meta, view = self.cache_fixture(Path(tmp).resolve())
            original = json.loads((b/'result.json').read_text())
            for name in original['vector_parity']:
                report = copy.deepcopy(original); report['vector_parity'][name]['status'] = 'not_applicable'
                meta['result_sha256'] = self.write(b/'result.json', report)
                with self.assertRaises(ValueError): self.load(a, b, pin, meta)

    def test_incomplete_token_proof_or_new_window_reuse_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, pin, meta, view = self.cache_fixture(Path(tmp).resolve()); meta['token_lengths'][0] = 300
            with self.assertRaises(ValueError): self.load(a, b, pin, meta)
            meta['token_lengths'][0] = 2; meta['rows'][-1]['retrieval_window_indices'] = meta['rows'][-2]['retrieval_window_indices']
            with self.assertRaises(ValueError): self.load(a, b, pin, meta)

    def test_incorrect_query_recording_counts_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, pin, meta, view = self.cache_fixture(Path(tmp).resolve()); meta['new_query_tracks'][0] = meta['new_query_tracks'][-1]
            with self.assertRaises(ValueError): self.load(a, b, pin, meta)

    def test_persistent_encode_and_evaluate_claims_block_before_new_output(self):
        import run_supplement_retrieval as runner
        cfg = json.loads(Path('docs/evaluation/MUS-064-retrieval-config.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); task = root/cfg['task_directory']; task.mkdir(parents=True)
            for stage in ['encode', 'evaluate']:
                (task/(stage+'-started.json')).write_text('{}')
                with patch.object(runner, 'ROOT', root), patch.object(runner.h.assets, 'document', return_value=cfg):
                    with self.assertRaisesRegex(ValueError, 'already attempted'):
                        runner.initialize(root/'config', '0'*64, task/stage, stage)
                self.assertFalse((task/stage).exists())

    def test_config_forbids_fit_fallback_or_changed_primary(self):
        original = json.loads(Path('docs/evaluation/MUS-064-retrieval-config.json').read_text())
        for kind in ['fit', 'fallback', 'primary']:
            cfg = copy.deepcopy(original)
            if kind == 'fit': cfg['operations']['fits'] = 1
            elif kind == 'fallback': cfg['automatic_fallback'] = True
            else: cfg['primary_metric'] = 'choose_best'
            with self.assertRaises(ValueError): s.validate(cfg)


if __name__ == '__main__': unittest.main()
