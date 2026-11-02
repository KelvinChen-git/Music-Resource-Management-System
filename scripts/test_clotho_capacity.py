"""Synthetic closure, rights, caption-structure and immutable one-audit checks."""
from pathlib import Path
import copy,csv,io,json,tempfile,unittest
from unittest.mock import patch
import clotho_source_capacity as c
import audit_clotho_capacity as runner

class ClothoCapacityTests(unittest.TestCase):
    def csv(self,rows,fields=c.META_FIELDS,encoding='utf8'):
        f=io.StringIO();w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        return f.getvalue().encode(encoding)
    def row(self,sid,user='a',tags='music',license='by',name=None):
        return dict(zip(c.META_FIELDS,[name or f'{sid}.wav',tags,str(sid),f'https://freesound.org/people/{user}/sounds/{sid}/','[0, 480000]',user,f'http://creativecommons.org/licenses/{license}/3.0/']))
    def captions(self,names):return self.csv([{'file_name':n,**{f'caption_{i}':'ORIGINAL full description' for i in range(1,6)}} for n in names],c.CAPTION_FIELDS)
    def fixture(self):
        dev=[self.row(1,'same','piano'),self.row(2,'solo','music'),self.row(3,'cczero','guitar'),self.row(4,'nc','music',license='by-nc')]
        dev[2]['license']='https://creativecommons.org/publicdomain/zero/1.0/'
        return {'development':self.csv(dev),'validation':self.csv([self.row(5,'same','music')]),'evaluation':self.csv([self.row(6,'test','dog')])},self.captions([r['file_name'] for r in dev])
    def test_cross_split_uploader_excluded_on_both_sides(self):
        raw,cap=self.fixture();v=c.analyze(raw,cap)
        self.assertEqual([r['sound_id'] for r in v['training_candidates']],['2'])
        self.assertEqual(v['cross_split_components'],1);self.assertEqual(v['cross_split_component_clips'],2)
        self.assertEqual(v['split_summary']['validation']['isolated_BY_BYSA_music_tag_clips'],0)
    def test_transitive_sound_id_and_uploader_closure(self):
        raw,cap=self.fixture();raw['validation']=self.csv([self.row(1,'alias',name='other.wav')]);raw['evaluation']=self.csv([self.row(9,'alias')])
        v=c.analyze(raw,cap);self.assertEqual(v['cross_split_component_clips'],3);self.assertEqual(v['cross_split_components'],1)
    def test_whole_tag_matching_not_substring_or_caption_selection(self):
        values=[' MUSIC ','music-box','guitar','acoustic-guitar','noise','PIANO']
        row=[self.row(i+10,str(i),tag) for i,tag in enumerate(values)]
        result,enc=c.metadata(self.csv(row),'development')
        self.assertEqual([bool(r['music_tag_hits']) for r in result],[True,False,True,False,False,True])
        self.assertTrue(result[0]['explicit_music_tag']);self.assertFalse(result[2]['explicit_music_tag'])
    def test_CC0_is_reported_separately_not_mislabeled_as_BY(self):
        raw,cap=self.fixture();v=c.analyze(raw,cap)
        self.assertEqual(v['split_summary']['development']['music_tag_audio_license_families'],{'by':2,'by-nc':1,'cc0':1})
    def test_original_rights_URI_and_unknown_are_preserved(self):
        row=self.row(1);row['license']='https://not-creativecommons.org/licenses/by/4.0/'
        v,_=c.metadata(self.csv([row]),'development');self.assertEqual(v[0]['license_family'],'unknown');self.assertEqual(v[0]['license'],row['license'])
        for kind in ['by','by-sa','by-nc','by-nc-sa','by-nd','by-nc-nd']:
            self.assertEqual(c.license_family(f'https://creativecommons.org/licenses/{kind}/3.0/'),kind)
    def test_all_5_original_nonempty_captions_required_no_bodies_returned(self):
        values,enc=c.caption_structure(self.captions(['x.wav']));self.assertEqual(values,{'x.wav':5});self.assertNotIn('ORIGINAL',str(values))
        with self.assertRaises(ValueError):c.caption_structure(self.captions(['x.wav','x.wav']))
        with self.assertRaises(ValueError):c.caption_structure(self.captions(['x.wav']).replace(b'ORIGINAL full description',b''))
    def test_caption_metadata_binding_cannot_drop_or_add_clips(self):
        raw,cap=self.fixture()
        with self.assertRaises(ValueError):c.analyze(raw,self.captions(['unrelated.wav']))
    def test_latin1_fallback_and_UTF8_captions_join_by_exact_filename(self):
        row=self.row(1,name='caf\u00e9.wav');v,enc=c.metadata(self.csv([row],encoding='latin1'),'development')
        self.assertEqual(enc,'iso-8859-1');self.assertEqual(v[0]['file_name'],'caf\u00e9.wav')
        caps,_=c.caption_structure(self.captions(['caf\u00e9.wav']));self.assertIn(v[0]['file_name'],caps)
    def test_unknown_schema_extra_column_or_bad_source_binding_refused(self):
        row=self.row(1)
        for key,value in [('sound_id','no'),('sound_link','https://freesound.org/people/a/sounds/2'),('file_name','../x'),('manufacturer','')]:
            r={**row,key:value}
            with self.assertRaises(ValueError):c.metadata(self.csv([r]),'development')
        with self.assertRaises(ValueError):c.metadata(self.csv([row]).replace(b'keywords',b'caption'),'development')
    def test_missing_offsets_reported_but_not_invented(self):
        row=self.row(1);row['start_end_samples']='';v,_=c.metadata(self.csv([row]),'development');self.assertIsNone(v[0]['source_sample_offsets'])
        for text in ['[10,0]','[false,1]','[0,1,2]']:
            row['start_end_samples']=text
            with self.assertRaises(ValueError):c.metadata(self.csv([row]),'development')
    def test_duplicates_within_official_split_refused(self):
        with self.assertRaises(ValueError):c.metadata(self.csv([self.row(1),self.row(1)]),'development')
    def test_metadata_candidates_never_claim_audio_training_or_benchmark_ready(self):
        raw,cap=self.fixture();v=c.analyze(raw,cap)
        self.assertFalse(v['audio_ready'] or v['training_ready'] or v['independent_benchmark_ready'] or v['body_semantics_used'])
        self.assertEqual(v['training_candidate_caption_pairs'],5);self.assertTrue(all(n==0 for n in v['operations'].values()))
    def test_all_metadata_splits_required_to_prevent_hidden_uploader_leak(self):
        raw,cap=self.fixture();raw.pop('evaluation')
        with self.assertRaises(ValueError):c.analyze(raw,cap)
    def test_checkpoint_selection_is_not_training_membership_proof(self):
        raw=b'music_audioset_epoch_15_esc_90.14.pt\nThe checkpoints have highest average mAP score on Clotho and AudioCaps.'
        self.assertTrue(runner.selection_proof(raw)['Clotho_in_checkpoint_selection_metric'])
        self.assertFalse(runner.selection_proof(raw)['exact_training_membership_established'])
        with self.assertRaises(ValueError):runner.selection_proof(b'Clotho')
    def test_known_missing_source_retains_uploader_bridge_and_cannot_be_candidate(self):
        missing=self.row(7,'same');missing.update(sound_id='Not found',sound_link='NA')
        raw,cap=self.fixture();raw['validation']=self.csv([missing])
        value=c.analyze(raw,cap)
        self.assertEqual(value['split_summary']['validation']['missing_source_binding_all_clips'],1)
        self.assertEqual(value['split_summary']['validation']['source_bound_BY_BYSA_music_clips'],0)
        self.assertEqual([r['sound_id']for r in value['training_candidates']],['2'])
        self.assertEqual(value['cross_split_component_clips'],2)
    def test_unrelated_missing_source_markers_do_not_merge_components(self):
        a=self.row(1,'x');b=self.row(2,'y')
        for row in [a,b]:row.update(sound_id='Not found',sound_link='NA')
        raw,cap=self.fixture();raw['validation']=self.csv([a]);raw['evaluation']=self.csv([b]);v=c.analyze(raw,cap)
        self.assertEqual(v['cross_split_components'],0)
    def test_missing_ID_without_exact_official_link_marker_is_not_accepted(self):
        row=self.row(1);row['sound_id']='Not found'
        with self.assertRaises(ValueError):c.metadata(self.csv([row]),'development')
    def test_repair_claim_also_blocks_new_directory(self):
        cfg=json.loads(Path('docs/evaluation/MUS-065-source-config.json').read_text());cfg['repair']={}
        # An actual repair descriptor is truthy and only its claim is consulted first.
        cfg['repair']={'policy':'known_Not_found_NA_quarantine_retain_uploader_closure'}
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();task=root/cfg['task_directory'];task.mkdir(parents=True);(task/'repair-started.json').write_text('{}')
            with patch.object(runner,'ROOT',root),patch.object(runner.h.assets,'document',return_value=cfg):
                with self.assertRaisesRegex(ValueError,'already attempted'):runner.run(root/'config','0'*64,task/'new')
            self.assertFalse((task/'new').exists())
    def test_uploader_mismatch_is_quarantined_but_both_keys_bridge_splits(self):
        row=self.row(1,'Jose');row['sound_link']='https://freesound.org/people/José/sounds/1/'
        raw,cap=self.fixture();raw['development']=self.csv([row]);raw['validation']=self.csv([self.row(8,'José')]);cap=self.captions(['1.wav'])
        v=c.analyze(raw,cap);self.assertEqual(v['training_candidates'],[]);self.assertEqual(v['cross_split_component_clips'],2)
        self.assertEqual(v['split_summary']['development']['source_binding_reasons'],{'uploader_field_URL_mismatch':1})
    def test_distinct_uploader_aliases_never_silently_normalize_into_accepted_identity(self):
        row=self.row(1,'Jose');row['sound_link']='https://freesound.org/people/José/sounds/1/'
        values,_=c.metadata(self.csv([row]),'development');self.assertFalse(values[0]['source_resolved']);self.assertTrue(values[0]['source_id_known'])
        self.assertEqual(values[0]['uploader_keys'],['jose','josé'])
    def test_second_repair_claim_cannot_be_reset_by_new_directory(self):
        cfg=json.loads(Path('docs/evaluation/MUS-065-format-repair-v2-config.json').read_text())
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();task=root/cfg['task_directory'];task.mkdir(parents=True);(task/'repair-v2-started.json').write_text('{}')
            with patch.object(runner,'ROOT',root),patch.object(runner.h.assets,'document',return_value=cfg):
                with self.assertRaisesRegex(ValueError,'already attempted'):runner.run(root/'config','0'*64,task/'new')
            self.assertFalse((task/'new').exists())
    def test_two_adjacent_README_lines_preserve_checkpoint_selection_proof(self):
        raw=b'music_audioset_epoch_15_esc_90.14.pt\nThe checkpoints list uses highest average mAP score.\nThe average uses AudioCaps and Clotho.'
        self.assertTrue(runner.selection_proof(raw)['Clotho_in_checkpoint_selection_metric'])
        with self.assertRaises(ValueError):runner.selection_proof(raw.replace(b'\nThe average',b'\nUnrelated paragraph.\nThe average'))
    def test_third_repair_claim_refuses_another_directory(self):
        cfg=json.loads(Path('docs/evaluation/MUS-065-provenance-repair-config.json').read_text())
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();task=root/cfg['task_directory'];task.mkdir(parents=True);(task/'repair-v3-started.json').write_text('{}')
            with patch.object(runner,'ROOT',root),patch.object(runner.h.assets,'document',return_value=cfg):
                with self.assertRaisesRegex(ValueError,'already attempted'):runner.run(root/'config','0'*64,task/'new')
            self.assertFalse((task/'new').exists())
    def test_persistent_claim_refuses_new_directory_before_output(self):
        cfg=json.loads(Path('docs/evaluation/MUS-065-source-config.json').read_text())
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp).resolve();task=root/cfg['task_directory'];task.mkdir(parents=True);(task/'audit-started.json').write_text('{}')
            with patch.object(runner,'ROOT',root),patch.object(runner.h.assets,'document',return_value=cfg):
                with self.assertRaisesRegex(ValueError,'already attempted'):runner.run(root/'config','0'*64,task/'new')
            self.assertFalse((task/'new').exists())
    def test_recipe_forbids_changed_tags_fit_or_semantic_selection(self):
        cfg=json.loads(Path('docs/evaluation/MUS-065-source-config.json').read_text())
        for key,value in [('music_tags',['choose_best']),('role','new_blind_test'),('operations',{'fits':1})]:
            r={**cfg,key:value}
            with self.assertRaises(ValueError):runner.validate(r)

if __name__=='__main__':unittest.main()
