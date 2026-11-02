"""Synthetic isolation/upper-bound checks; no real source data or network."""
import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import human_caption_capacity as c


class CapacityTest(unittest.TestCase):
    def fixture(self):
        names = {
            'track_0000001': {'artist_id': 'a', 'artist': 'Alice', 'title': 'First'},
            'track_0000002': {'artist_id': 'b', 'artist': 'Bob', 'title': 'Second'},
            # This bridge is not a caption candidate, but must still connect Alice/Bob.
            'bridge': {'artist_id': 'c', 'artist': 'Alice & Bob', 'title': 'Bridge'},
            'track_0000003': {'artist_id': 'd', 'artist': 'Carol', 'title': 'Third'},
        }
        base = {k: {'artist_id': n['artist_id'], 'path': k+'.mp3', 'duration': 120}
                for k, n in names.items() if k != 'bridge'}
        rights = {t['path']: {'family': 'by'} for t in base.values()}
        hashes = {t['path'].replace('.mp3', '.low.mp3'): k for k, t in base.items()}
        rows = [{'track_id': k, 'artist_id': n['artist_id'], 'validated': True}
                for k, n in names.items() if k != 'bridge']
        return rows, base, names, rights, hashes, dict.fromkeys(base, 'test')

    def test_projection_never_exports_caption_or_familiarity(self):
        raw = b'caption_id,track_id,caption,is_valid_subset,familiarity,artist_id\n1,track_1,SECRET,true,SECRET,artist_2\n'
        row = c.sdd_metadata(raw)[0]
        self.assertEqual(row, {'track_id': 'track_0000001', 'artist_id': 'artist_000002', 'validated': True})
        self.assertNotIn('SECRET', str(row))

    def test_duplicate_caption_id_rejected(self):
        with self.assertRaises(ValueError):
            c.sdd_metadata(b'caption_id,track_id,is_valid_subset,artist_id\n1,track_1,true,artist_2\n1,track_1,true,artist_2\n')

    def test_unknown_flag_rejected(self):
        with self.assertRaises(ValueError):
            c.sdd_metadata(b'caption_id,track_id,is_valid_subset,artist_id\n1,track_1,maybe,artist_2\n')

    def test_full_metadata_bridge_and_source_id_resolve_components(self):
        out = c.measure(*self.fixture(), {'sealed': [{'source_track_id': 'track_0000001'}]})
        self.assertEqual([r['source_track_id'] for r in out['eligible']], ['track_0000003'])
        self.assertIn('sealed:credit_component', out['excluded']['track_0000002'])

    def test_external_credit_alias_resolves_full_component(self):
        out = c.measure(*self.fixture(), {'old': [{'credits': ['Bob']}]})
        self.assertEqual(out['summary']['eligible_recordings'], 1)

    def test_title_and_audio_hash_reasons_are_both_reported(self):
        out = c.measure(*self.fixture(), {'old': [{'title': 'Third', 'audio_sha256': 'track_0000003'}]})
        self.assertEqual(out['excluded']['track_0000003'], ['old:work_name', 'old:official_audio_sha'])

    def test_no_validated_caption_not_promoted(self):
        args = self.fixture(); args[0][-1]['validated'] = False
        out = c.measure(*args, {})
        self.assertEqual(out['summary']['eligible_validated_captions'], 2)
        self.assertEqual(out['excluded']['track_0000003'], ['no_validated_caption'])

    def test_bounds_rights_hash_and_split_all_fail_closed(self):
        rows, base, names, rights, hashes, splits = self.fixture()
        base['track_0000001']['duration'] = 29.99
        rights['track_0000001.mp3']['family'] = 'by-nc'
        del hashes['track_0000001.low.mp3']; splits['track_0000001'] = 'train'
        out = c.measure(rows, base, names, rights, hashes, splits, {})
        self.assertEqual(len(out['excluded']['track_0000001']), 4)

    def test_missing_name_quarantined(self):
        args = self.fixture(); del args[2]['track_0000003']
        self.assertEqual(c.measure(*args, {})['excluded']['track_0000003'], ['missing_source_metadata'])

    def test_artist_mismatch_rejected(self):
        args = self.fixture(); args[0][-1]['artist_id'] = 'wrong'
        with self.assertRaises(ValueError): c.measure(*args, {})

    def test_component_capacity_is_upper_bound_without_selection(self):
        args = self.fixture(); args[0].append(dict(args[0][0]))
        out = c.measure(*args, {})['summary']
        self.assertEqual(out['eligible_recordings'], 3)
        self.assertEqual(out['independent_credit_components_upper_bound'], 2)
        self.assertEqual(out['captions_if_one_recording_per_component_min'], 2)
        self.assertEqual(out['captions_if_one_recording_per_component_max'], 3)
        self.assertFalse(out['candidate_selection_performed'])

    def test_shared_work_across_components_is_not_independence_proof(self):
        args = self.fixture(); args[2]['track_0000003']['title'] = 'First'
        self.assertEqual(c.measure(*args, {})['summary']['cross_component_shared_work_keys'], 1)

    def test_existing_claim_blocks_new_output_before_source_access(self):
        import audit_human_caption_capacity as runner
        cfg = json.loads(Path('docs/evaluation/MUS-061-capacity-config.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); task = root/cfg['task_directory']; task.mkdir(parents=True)
            (task/'audit-started.json').write_text('{}')
            with patch.object(runner, 'ROOT', root), patch.object(runner.h.assets, 'document', return_value=cfg):
                with self.assertRaisesRegex(ValueError, 'already attempted'):
                    runner.run(root/'config', '0'*64, task/'new-output')
            self.assertFalse((task/'new-output').exists())

    def test_config_cannot_authorize_scoring_or_new_selection(self):
        import audit_human_caption_capacity as runner
        cfg = json.loads(Path('docs/evaluation/MUS-061-capacity-config.json').read_text())
        for change in ('scoring', 'selection'):
            changed = json.loads(json.dumps(cfg))
            if change == 'scoring': changed['operations']['scored_queries'] = 1
            else: changed['policy']['new_partition_selected'] = True
            with patch.object(runner.h.assets, 'document', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'Fixed source-only'):
                    runner.run(Path('unused'), '0'*64, Path('unused'))


if __name__ == '__main__': unittest.main()
