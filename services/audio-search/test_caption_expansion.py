import json
import unittest

from caption_expansion import isolate, provisional_scanner, choose_candidates, metadata_file, actual_intervals


def row(tid, split='train', group=None, **kw):
    return {'id': str(tid), 'split': split, 'creator_component': group or 'g'+str(tid),
            'work': 'w'+str(tid), 'audio_sha256': 'h'+str(tid),
            'priority_sha256': str(tid).zfill(4), 'original_audio_license_family': 'by', **kw}


class ExpansionTests(unittest.TestCase):
    def clean(self, rows, old=(), ids=(), groups=(), works=(), hashes=()):
        return isolate(rows, list(old), set(ids), set(groups), set(works), set(hashes))

    def test_credit_work_content_cross_split_both_sides(self):
        for key in ('creator_component', 'work', 'audio_sha256'):
            rows = [row(1), row(2, 'validation'), row(3)]
            rows[1][key] = rows[0][key]
            kept, reasons = self.clean(rows)
            self.assertEqual([r['id'] for r in kept], ['3'])
            self.assertEqual(reasons['cross_split_relation'], 2)

    def test_existing_validation_credit_cannot_be_new_train(self):
        kept, _ = self.clean([row(2, group='same'), row(3)], [row(1, 'validation', 'same')])
        self.assertEqual([r['id'] for r in kept], ['3'])

    def test_reserved_filters_are_independent(self):
        kept, reasons = self.clean([row(i) for i in range(1, 7)], ids=['1'], groups=['g2'], works=['w3'], hashes=['h4'])
        self.assertEqual([r['id'] for r in kept], ['5', '6'])
        self.assertEqual(len(reasons), 4)

    def test_same_split_credit_cap_includes_existing(self):
        kept, reasons = self.clean([row(i, group='g') for i in range(4, 7)]+[row(9)], [row(i, group='g') for i in range(1, 4)])
        self.assertEqual([r['id'] for r in kept], ['4', '9'])
        self.assertEqual(reasons['four_recordings_per_creator_cap'], 2)

    def test_new_work_and_byte_duplicates_not_double_counted(self):
        kept, _ = self.clean([row(1), row(2, work='w1'), row(3, audio_sha256='h1'), row(4)])
        self.assertEqual([r['id'] for r in kept], ['1', '4'])

    def test_non_BY_license_quarantined(self):
        kept, _ = self.clean([row(1, original_audio_license_family='by-nc'), row(2)])
        self.assertEqual([r['id'] for r in kept], ['2'])

    def test_candidate_order_independent_of_caption_content(self):
        rows = [row(i, 'train' if i < 8 else 'validation') for i in range(1, 12)]
        a = [{'id': str(i), 'caption': 'arbitrary'} for i in range(1, 12)]
        b = [{'id': r['id'], 'caption': 'different content'} for r in reversed(a)]
        counts = {'train': 3, 'validation': 2}
        self.assertEqual(choose_candidates(rows, a, counts, 'seed'), choose_candidates(list(reversed(rows)), b, counts, 'seed'))

    def test_provisional_does_not_use_provider_duration_as_measured_EOF(self):
        scan = provisional_scanner([row(1, duration=59)])
        scan.add(json.dumps({'id': 1, 'start_time': 40, 'end_time': 60, 'caption': 'complete text'}).encode())
        self.assertEqual(len(scan.finish()['candidates']), 1)
        actual = actual_intervals({**row(1), 'duration_seconds': 59.9},
            [json.dumps({'id': 1, 'start_time': 40, 'end_time': 60, 'caption': 'complete text'}).encode()])
        self.assertEqual(actual['candidates'], [])

    def test_actual_EOF_keeps_original_full_text_and_raw_pin(self):
        caption = 'full original caption '*100
        raw = (json.dumps({'id': 1, 'start_time': 0, 'end_time': 30, 'caption': caption})+'\n').encode()
        result = actual_intervals({**row(1), 'duration_seconds': 31}, [raw])
        self.assertEqual(result['candidates'][0]['caption'], caption)
        self.assertEqual(len(result['candidates'][0]['raw_line_sha256']), 64)

    def test_overlap_fails_closed(self):
        lines = [json.dumps({'id': 1, 'start_time': s, 'end_time': s+30, 'caption': 'text'}).encode() for s in (0, 20)]
        with self.assertRaises(ValueError): actual_intervals({**row(1), 'duration_seconds': 60}, lines)

    def test_metadata_date_buckets(self):
        self.assertEqual(metadata_file('2008-01-01'), '2008-01-01.jsonl')
        self.assertEqual(metadata_file('2008-01-05'), '2008-01-01.jsonl')
        self.assertEqual(metadata_file('2008-01-06'), '2008-01-06.jsonl')
        self.assertEqual(metadata_file('2008-02-29'), '2008-02-25.jsonl')
        with self.assertRaises(ValueError): metadata_file('2007-12-31')


if __name__ == '__main__': unittest.main()
