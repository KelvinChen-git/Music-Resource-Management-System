from pathlib import Path
import unittest
import numpy as np
from caption_pair_preflight import reconcile, choose_references, anchor_intervals, sample_bounds, correlation_curve


class PairPreflightTests(unittest.TestCase):
    def original(self):
        return {'id': '12', 'artist_id': '7', 'title': 'A song', 'duration_seconds': 90.2,
                'split': 'train', 'creator_component': 'a'}

    def row(self, **changes):
        return {'id': '12', 'artist_id': '7', 'name': 'A Song', 'duration': 90,
                'license_ccurl': 'http://creativecommons.org/licenses/by/3.0/', 'audiodownload_allowed': True,
                'audiodownload': 'https://prod-1.storage.jamendo.com/download/track/12/mp32/', **changes}

    def test_unanimous_metadata_and_duplicate_rows(self):
        r = self.row(); result = reconcile(self.original(), [r, r.copy()])
        self.assertTrue(result['eligible']); self.assertFalse(result['reference_is_exact_teacher_artifact'])
        self.assertTrue(reconcile(self.original(), [r, self.row(duration=90.0)])['eligible'])

    def test_no_first_row_license_cherry_picking(self):
        r = reconcile(self.original(), [self.row(), self.row(license_ccurl='http://creativecommons.org/licenses/by-nc/3.0/')])
        self.assertFalse(r['eligible']); self.assertIn('conflicting_license_URIs', r['reasons'])

    def test_missing_unknown_and_false_download_flags(self):
        for rows in ([], [self.row(audiodownload_allowed=False)], [self.row(audiodownload_allowed=1)],
                     [self.row(license_ccurl='unknown')]): self.assertFalse(reconcile(self.original(), rows)['eligible'])

    def test_same_family_different_license_versions_remain_conflict(self):
        r = reconcile(self.original(), [self.row(), self.row(license_ccurl='https://creativecommons.org/licenses/by/4.0/')])
        self.assertFalse(r['eligible'])

    def test_identity_and_duration_mismatches_not_repaired(self):
        for change in ({'id': '13'}, {'artist_id': '8'}, {'name': 'new work'}, {'duration': 92}, {'duration': float('nan')}):
            self.assertFalse(reconcile(self.original(), [self.row(**change)])['eligible'])

    def test_download_URL_bound_to_ID_host_and_format(self):
        for url in ('https://evil.com/download/track/12/mp32/', 'https://prod-1.storage.jamendo.com/download/track/13/mp32/',
                    'https://user@prod-1.storage.jamendo.com/download/track/12/mp32/'):
            self.assertFalse(reconcile(self.original(), [self.row(audiodownload=url)])['eligible'])

    def test_reference_selection_training_only_three_intervals_distinct_creators(self):
        records = [self.original(), {**self.original(), 'id': '13'}, {**self.original(), 'id': '14', 'split': 'validation'}]
        verdicts = [{'id': r['id'], 'eligible': True} for r in records]
        captions = [{'id': r['id']} for r in records for _ in range(3)]
        ids = choose_references(records, verdicts, captions, 3, 'fixed')
        self.assertEqual(len(ids), 1); self.assertNotIn('14', ids)

    def test_sample_rounding_and_EOF_fail_closed(self):
        self.assertEqual(sample_bounds(.001, .010, 48000, 480), (48, 480))
        for a,b in ((-1,1),(0,.0101),(0,float('inf'))):
            with self.assertRaises(ValueError): sample_bounds(a,b,48000,480)

    def test_anchor_choice_is_first_middle_last_not_best_sound(self):
        rows = [{'start_time': x*30, 'end_time': (x+1)*30} for x in range(5)]
        self.assertEqual([r['start_time'] for r in anchor_intervals(rows)], [0,60,120])

    def test_normalized_correlation_matches_direct_centered_loops(self):
        rng = np.random.default_rng(52); x=rng.normal(size=25); y=rng.normal(size=45)
        expected=[]
        for i in range(21):
            a=x-x.mean(); b=y[i:i+25]-y[i:i+25].mean(); expected.append(float(a@b/np.sqrt((a@a)*(b@b))))
        np.testing.assert_allclose(correlation_curve(x,y), expected, atol=1e-12)

    def test_known_lag_gain_offset_and_wrong_recording(self):
        rng=np.random.default_rng(53); x=rng.normal(size=100); y=np.r_[rng.normal(size=7),x*2+4,rng.normal(size=9)]
        r=correlation_curve(x,y); self.assertEqual(int(np.argmax(r)),7); self.assertAlmostEqual(float(r[7]),1)
        self.assertLess(float(correlation_curve(x,rng.normal(size=116)).max()), .6)

    def test_silence_and_nonfinite_do_not_pass_alignment(self):
        with self.assertRaises(ValueError): correlation_curve(np.zeros(10),np.zeros(20))
        with self.assertRaises(ValueError): correlation_curve(np.array([1,np.nan]),np.ones(4))


if __name__ == '__main__': unittest.main()
