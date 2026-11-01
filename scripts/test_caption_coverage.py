import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from caption_coverage import Coverage, numeric_id
from audit_caption_coverage import charge


def encoded(**changes):
    return (json.dumps({'id': '12', 'start_time': 0, 'end_time': 30,
                        'caption': 'An existing generated musical description.', **changes})+'\n').encode()


class CaptionCoverageTests(unittest.TestCase):
    def scanner(self, **kwargs):
        return Coverage([{'id': '12', 'split': 'train', 'duration_seconds': 76, 'creator_component': 'a'},
                         {'id': '13', 'split': 'validation', 'duration_seconds': 60, 'creator_component': 'b'}], **kwargs)

    def test_unknown_id_retains_no_text_or_supervision(self):
        s = self.scanner(); self.assertFalse(s.add(encoded(id='99', caption={'not': 'supervision'})))
        r = s.finish(); self.assertEqual(r['candidates'], []); self.assertEqual(r['summary']['allowlisted_rows'], 0)
        self.assertEqual(r['summary']['source_unique_ids'], 1)

    def test_duplicate_is_coalesced_without_increasing_coverage(self):
        s = self.scanner(); s.add(encoded()); s.add(encoded())
        r = s.finish(); self.assertEqual(len(r['candidates']), 1)
        self.assertEqual(r['summary']['exact_duplicate_valid_rows'], 1)
        self.assertEqual(r['summary']['splits']['train']['covered_recordings'], 1)

    def test_same_interval_conflicting_text_quarantines_all_versions(self):
        s = self.scanner(); s.add(encoded()); s.add(encoded(caption='A conflicting generated description.'))
        r = s.finish(); self.assertEqual(r['candidates'], []); self.assertEqual(r['summary']['conflicting_intervals'], 1)
        self.assertEqual(r['summary']['conflict_quarantined_unique_rows'], 2)

    def test_verified_tail_and_both_splits_with_zero_coverage_bucket(self):
        s = self.scanner(); s.add(encoded(start_time=60, end_time=76))
        r = s.finish(); self.assertEqual(r['summary']['accepted_unique_intervals'], 1)
        self.assertEqual(r['summary']['splits']['validation']['intervals_per_recording_histogram'], {0: 1})
        self.assertFalse(r['summary']['training_ready'])
        self.assertEqual(r['candidates'][0]['label_source'], 'model_generated')

    def test_beyond_actual_EOF_not_clamped_or_accepted(self):
        s = self.scanner(); s.add(encoded(start_time=60, end_time=90))
        self.assertEqual(s.finish()['summary']['rejected_rows_by_reason'], {'beyond_verified_EOF': 1})

    def test_invalid_interval_types_direction_and_length(self):
        s = self.scanner()
        for changes in ({'start_time': True}, {'start_time': -1}, {'end_time': 0},
                        {'end_time': 14}, {'end_time': 31}): s.add(encoded(**changes))
        r = s.finish(); self.assertEqual(r['candidates'], [])
        self.assertEqual(sum(r['summary']['rejected_rows_by_reason'].values()), 5)

    def test_nonfinite_json_and_invalid_ids_fail_closed(self):
        for value in (True, 1.5, '-1', '１', None, 0):
            with self.assertRaises(ValueError): numeric_id(value)
        with self.assertRaises(ValueError): self.scanner().add(encoded(start_time=float('nan')))

    def test_line_bound_utf8_json_and_object_validation(self):
        for raw in (b'x'*65537, b'\xff\n', b'not-json\n', b'[]\n', b'{}\n'):
            with self.assertRaises((ValueError, UnicodeError)): self.scanner().add(raw)

    def test_empty_or_oversized_caption_rejected_only_for_allowlisted_record(self):
        s = self.scanner(); s.add(encoded(caption=' ')); s.add(encoded(caption='x'*8193))
        self.assertEqual(s.finish()['summary']['rejected_rows_by_reason'], {'invalid_caption': 2})

    def test_overlapping_intervals_are_disclosed(self):
        s = self.scanner(); s.add(encoded()); s.add(encoded(start_time=15, end_time=45))
        r = s.finish(); self.assertEqual(r['summary']['overlapping_interval_pairs'], 1)
        self.assertFalse(r['summary']['training_ready'])

    def test_allowlist_rejects_duplicates_and_invalid_EOF(self):
        for rows in ([], [{'id': '1', 'split': 'train', 'duration_seconds': float('inf'), 'creator_component': 'a'}],
                     [{'id': '1', 'split': 'train', 'duration_seconds': 30, 'creator_component': 'a'}]*2):
            with self.assertRaises(ValueError): Coverage(rows)

    def test_task_budget_is_persistent_conservative_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'ledger.jsonl'; cfg = {'source': {'bytes': 70, 'sha256': 'a'*64}, 'max_total_body_bytes': 100}
            previous_umask = os.umask(0o777)
            try: charge(p, cfg, 'b'*64)
            finally: os.umask(previous_umask)
            before = p.read_bytes(); self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError): charge(p, cfg, 'b'*64)
            self.assertEqual(p.read_bytes(), before)
            with self.assertRaises(ValueError): charge(p, cfg, 'c'*64)
            self.assertEqual(p.read_bytes(), before)


if __name__ == '__main__': unittest.main()
