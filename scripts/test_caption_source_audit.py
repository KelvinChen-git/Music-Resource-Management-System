"""Synthetic metadata projection, exact offsets, and fixed grouped planning."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import caption_source_audit as c


class SourceTests(unittest.TestCase):
    def wiki(self, rows):
        import csv, io
        out = io.StringIO(); writer = csv.writer(out)
        writer.writerow(['file', 'pageid', 'aspects', 'sentences', 'audio_url', 'page_url'])
        for name, page, url in rows:
            writer.writerow([name, page, 'UNUSED', 'UNUSED', url, 'https://en.wikipedia.org/wiki/Test'])
        return c.wiki_frame(out.getvalue().encode())

    def test_body_fields_are_not_inspected_or_exported(self):
        value = self.wiki([('a', '1', 'https://upload.wikimedia.org/wikipedia/commons/a/a.ogg')])
        self.assertNotIn('UNUSED', str(value))
        self.assertEqual(value['summary']['unique_files'], 1)

    def test_duplicate_rows_not_unique_audio(self):
        row = ('a', '1', 'https://upload.wikimedia.org/wikipedia/commons/a/a.ogg')
        value = self.wiki([row, row])['summary']
        self.assertEqual(value['source_rows'], 2); self.assertEqual(value['unique_files'], 1)
        self.assertEqual(value['duplicate_file_article_url_rows'], 1)

    def test_conflicting_source_url_never_silently_chooses_first(self):
        value = self.wiki([('a', '1', 'https://upload.wikimedia.org/wikipedia/commons/a/a.ogg'),
                           ('a', '2', 'https://upload.wikimedia.org/wikipedia/en/b/a.ogg')])
        self.assertEqual(value['summary']['files_with_conflicting_audio_urls'], 1)

    def test_untrusted_audio_urls_are_quarantined(self):
        for url in ('http://upload.wikimedia.org/wikipedia/commons/a',
                    'https://upload.wikimedia.org.evil.test/wikipedia/commons/a',
                    'https://u:p@upload.wikimedia.org/wikipedia/commons/a',
                    'https://127.0.0.1/wikipedia/commons/a',
                    'https://upload.wikimedia.org/wikipedia/commons/a?q=1'):
            self.assertEqual(self.wiki([('a', '1', url)])['summary']['projected_rows'], 0)

    def test_namespace_not_inferred_as_audio_license(self):
        value = self.wiki([('a', '1', 'https://upload.wikimedia.org/wikipedia/commons/a')])['summary']
        self.assertEqual(value['audio_url_wiki_namespaces'], {'commons': 1})
        self.assertFalse(value['per_audio_rights_established'])

    def test_unknown_schema_rejected(self):
        with self.assertRaises(ValueError): c.wiki_frame(b'file,pageid\na,1\n')

    def test_video_and_exact_clip_overlap_are_distinct(self):
        raw = b'video_id,start,end,text\nabcdefghijk,30,40,UNUSED\n'
        mc = [{'ytid': 'abcdefghijk', 'start_s': '20', 'end_s': '30'}]
        value = c.youtube_frame(raw, mc, {'abcdefghijk'})
        self.assertEqual(value['summary']['musiccaps_video_id_overlap'], 1)
        self.assertEqual(value['summary']['musiccaps_exact_clip_overlap'], 0)
        self.assertNotIn('UNUSED', str(value))

    def test_nonfinite_negative_or_wrong_length_times_rejected(self):
        for start, end in [('NaN', '10'), ('0', 'Infinity'), ('-1', '9'), ('0', '9.9'), ('bad', '10')]:
            with self.assertRaises(ValueError):
                c.youtube_frame(f'video_id,start,end,text\nabcdefghijk,{start},{end},unused\n'.encode(), [], set())

    def test_exact_decimal_ten_seconds_and_duplicate_clip(self):
        raw = b'video_id,start,end,text\nabcdefghijk,0.1,10.1,unused\nabcdefghijk,0.10,10.10,unused\n'
        self.assertEqual(c.youtube_frame(raw, [], set())['summary']['duplicate_clip_rows'], 1)

    def fixture(self):
        rows = [{'source_track_id': str(i), 'creator_component': str(min(i, 5)),
                 'audio_sha256': str(i), 'work_key': str(i), 'validated_caption_count': 1} for i in range(8)]
        source = [{'track_id': str(i), 'validated': True} for i in range(8)]
        return rows, source

    def test_one_per_component_selection_invariant_to_input_order(self):
        rows, source = self.fixture(); before = copy.deepcopy(rows)
        a = c.supplement_plan(rows, source, 'MUS-062-unused-SDD-six-components-v1')
        b = c.supplement_plan(list(reversed(rows)), source, 'MUS-062-unused-SDD-six-components-v1')
        self.assertEqual(a, b); self.assertEqual(rows, before)
        self.assertEqual(len(a['selected']), 6); self.assertEqual(len(a['omitted_same_component_not_fallback']), 2)

    def test_changed_caption_count_cannot_change_selection_silently(self):
        rows, source = self.fixture(); rows[0]['validated_caption_count'] = 2
        with self.assertRaises(ValueError): c.supplement_plan(rows, source, 'MUS-062-unused-SDD-six-components-v1')

    def test_work_conflict_fails_without_fallback(self):
        rows, source = self.fixture(); rows[1]['work_key'] = rows[0]['work_key']
        with self.assertRaises(ValueError): c.supplement_plan(rows, source, 'MUS-062-unused-SDD-six-components-v1')

    def test_changed_seed_or_missing_source_rejected(self):
        rows, source = self.fixture()
        for values, seed in [(rows, 'another-seed'), (rows[:-1], 'MUS-062-unused-SDD-six-components-v1')]:
            with self.assertRaises(ValueError): c.supplement_plan(values, source, seed)

    def test_existing_claim_blocks_new_directory_before_inputs(self):
        import audit_caption_sources as runner
        cfg = json.loads(Path('docs/evaluation/MUS-062-source-config.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); task = root/cfg['task_directory']; task.mkdir(parents=True)
            (task/'audit-started.json').write_text('{}')
            with patch.object(runner, 'ROOT', root), patch.object(runner.h.assets, 'document', return_value=cfg):
                with self.assertRaisesRegex(ValueError, 'already attempted'):
                    runner.run(root/'config', '0'*64, task/'new')
            self.assertFalse((task/'new').exists())

    def test_no_fit_rule_and_frozen_model_comparison_cannot_change(self):
        import audit_caption_sources as runner
        original = json.loads(Path('docs/evaluation/MUS-062-source-config.json').read_text())
        for key in ('model', 'fit'):
            cfg = copy.deepcopy(original)
            if key == 'model': cfg['future_comparison']['models'].append('another')
            else: cfg['operations']['fits'] = 1
            with patch.object(runner.h.assets, 'document', return_value=cfg):
                with self.assertRaisesRegex(ValueError, 'Fixed source-only'):
                    runner.run(Path('unused'), '0'*64, Path('unused'))


if __name__ == '__main__': unittest.main()
